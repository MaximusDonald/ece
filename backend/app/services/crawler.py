"""Regulatory Sentinel: targeted official feed monitoring via ETag, Last-Modified, and SHA-256 diffing.

Blind multi-page site spidering was retired in Phase 7; the sentinel monitors
explicitly registered regulatory watch URLs and emits pending alerts for
human admin review before any corpus ingestion.
"""

from __future__ import annotations

import difflib
import hashlib
import html
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import List, Optional, Set, Tuple
from urllib.parse import unquote, urljoin, urlparse

import fitz
import httpx

logger = logging.getLogger(__name__)

LEGAL_KEYWORDS = {
    "loi", "lois", "decret", "décret", "decrets", "décrets", "arrete", "arrêté",
    "reglement", "règlement", "directive", "deliberation", "délibération", "decision",
    "décision", "sanction", "ordonnance", "acte additionnel", "circulaire",
    "donnees", "données", "personnelles", "conformite", "conformité", "code", "numerique", "numérique",
}

NON_NORMATIVE_NOISE_KEYWORDS = {
    "formulaire", "formulaires", "discours", "rapport annuel", "communique", "communiqué",
    "agenda", "actualite", "actualité", "interview", "evenement", "événement",
    "galerie", "newsletter", "contact", "mention legale", "mentions légales", "brochure",
}

MAX_WATCH_BYTES = 15 * 1024 * 1024  # 15 MB safeguard


class _HTMLLinkAndTextExtractor(HTMLParser):
    """Extract visible text and anchor links cleanly from a single watched HTML page."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: List[Tuple[str, str]] = []
        self.current_href: Optional[str] = None
        self.current_anchor_text: List[str] = []
        self._skip_depth = 0
        self.visible_text_parts: List[str] = []
        self._ignored_tags = {"script", "style", "noscript", "svg", "footer", "nav"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in self._ignored_tags:
            self._skip_depth += 1
            return

        if tag_lower == "a":
            for attr_name, attr_val in attrs:
                if attr_name.lower() == "href" and attr_val:
                    clean_val = attr_val.strip()
                    if clean_val and not clean_val.startswith(("javascript:", "mailto:", "tel:", "#")):
                        try:
                            self.current_href = urljoin(self.base_url, clean_val).split("#")[0]
                            self.current_anchor_text = []
                        except Exception:
                            self.current_href = None

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self._ignored_tags and self._skip_depth:
            self._skip_depth -= 1
            return

        if tag_lower == "a" and self.current_href:
            anchor_text = " ".join(self.current_anchor_text).strip()
            self.links.append((self.current_href, anchor_text))
            self.current_href = None
            self.current_anchor_text = []

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if not clean:
            return
        if not self._skip_depth:
            self.visible_text_parts.append(clean)
        if self.current_href is not None:
            self.current_anchor_text.append(clean)


def validate_public_https_url(url: str) -> None:
    """Ensure URL is HTTPS and does not resolve to private/local network (SSRF defense)."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"URL non autorisée ({url}) : HTTPS public obligatoire.")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".local", ".internal", ".localhost")):
        raise ValueError(f"Hôte local interdit : {hostname}")
    try:
        addresses = {ipaddress.ip_address(hostname)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            }
        except OSError as exc:
            raise ValueError(f"Domaine impossible à résoudre : {hostname}") from exc
    if not addresses or any(not addr.is_global for addr in addresses):
        raise ValueError("L'URL doit pointer exclusivement vers une adresse IP publique routable.")


def get_base_domain(host: str) -> str:
    parts = host.lower().strip().split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host.lower().strip()


def is_same_or_subdomain(target_host: str, root_host: str) -> bool:
    t = target_host.lower().strip()
    r = root_host.lower().strip()
    if t == r or t.endswith(f".{r}") or r.endswith(f".{t}"):
        return True
    base_target = get_base_domain(t)
    base_root = get_base_domain(r)
    return base_target == base_root and bool(base_root)


def score_link_priority(url: str, anchor_text: str) -> int:
    combined = f"{url.lower()} {anchor_text.lower()}"
    score = 0
    if ".pdf" in url.lower():
        score += 50
    for kw in LEGAL_KEYWORDS:
        if kw in combined:
            score += 10
    return score


def classify_normative_candidate(url: str, title: str) -> tuple[bool, str]:
    """Filter out non-normative noise (forms, speeches, press releases, annual reports)."""
    combined = f"{url.lower()} {title.lower()}"
    for bad in NON_NORMATIVE_NOISE_KEYWORDS:
        if bad in combined:
            return False, f"Exclu (document non normatif : '{bad}')"

    normative_markers = (
        "loi", "decret", "décret", "arrete", "arrêté", "deliberation", "délibération",
        "decision", "décision", "sanction", "reglement", "règlement", "directive",
        "ordonnance", "acte", "code", "journal officiel",
    )
    if any(m in combined for m in normative_markers) or url.lower().endswith(".pdf"):
        return True, "Texte ou acte normatif candidat"
    return False, "Lien hors périmètre normatif"


def compute_text_diff_summary(previous_text: Optional[str], current_text: str, max_lines: int = 18) -> str:
    """Build a concise French diff summary showing newly added regulatory lines."""
    if not previous_text:
        preview = "\n".join(line for line in current_text.splitlines()[:8] if line.strip())
        return f"Empreinte initiale enregistrée ({len(current_text)} car.). Aperçu :\n{preview[:700]}"

    prev_lines = [l.strip() for l in previous_text.splitlines() if l.strip()]
    curr_lines = [l.strip() for l in current_text.splitlines() if l.strip()]
    diff_iter = difflib.unified_diff(prev_lines, curr_lines, lineterm="", n=0)

    added_lines: List[str] = []
    removed_lines: List[str] = []
    for line in diff_iter:
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+"):
            added_lines.append(line[1:].strip())
        elif line.startswith("-"):
            removed_lines.append(line[1:].strip())

    parts: List[str] = []
    if added_lines:
        parts.append("Ajouts détectés :\n" + "\n".join(f"+ {l[:220]}" for l in added_lines[:max_lines]))
    if removed_lines:
        parts.append("Suppressions / modifications :\n" + "\n".join(f"- {l[:220]}" for l in removed_lines[:6]))
    return "\n\n".join(parts) if parts else "Modification structurelle ou métadonnée détectée (ETag / empreinte modifiée)."


@dataclass
class NormativeCandidate:
    """Single normative publication or link discovered on a watched page."""

    url: str
    title: str
    filename: Optional[str] = None
    reason: str = ""


@dataclass
class SentinelCheckResult:
    """Outcome of a single targeted regulatory watch check."""

    changed: bool
    status_code: int
    new_hash: str
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    change_summary: str = ""
    page_snapshot: str = ""
    candidates: List[NormativeCandidate] = field(default_factory=list)


@dataclass
class DiscoveredDocument:
    """Legacy dataclass preserved for backwards compatibility."""

    download_url: str
    original_filename: str
    content_type: str
    content_hash: str
    content_text: str
    minio_path: str
    source_page_url: str
    anchor_text: str
    file_size_bytes: int


class RegulatorySentinel:
    """Targeted watch engine checking ETag, Last-Modified, and SHA-256 on one official URL."""

    def __init__(self, target_url: str) -> None:
        validate_public_https_url(target_url)
        self.target_url = target_url
        self.target_host = urlparse(target_url).hostname or ""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ECO-Compliance-Sentinel/3.0; +https://ece.gov)",
            "Accept": "text/html,application/xhtml+xml,application/pdf,application/json,*/*",
        }

    async def check_for_updates(
        self,
        *,
        client: Optional[httpx.AsyncClient] = None,
        previous_etag: Optional[str] = None,
        previous_last_modified: Optional[str] = None,
        previous_hash: Optional[str] = None,
        previous_snapshot: Optional[str] = None,
        known_urls: Optional[Set[str]] = None,
    ) -> SentinelCheckResult:
        """Fetch only the monitored page/feed, compare fingerprints, and emit diff + candidates."""
        req_headers = dict(self.headers)
        if previous_etag:
            req_headers["If-None-Match"] = previous_etag
        if previous_last_modified:
            req_headers["If-Modified-Since"] = previous_last_modified

        owns_client = client is None
        http_client = client or httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True)
        try:
            resp = await http_client.get(self.target_url, headers=req_headers)
            if resp.status_code == 304:
                return SentinelCheckResult(
                    changed=False,
                    status_code=304,
                    new_hash=previous_hash or "",
                    etag=previous_etag,
                    last_modified=previous_last_modified,
                    change_summary="Aucun changement (HTTP 304 Not Modified).",
                )
            resp.raise_for_status()

            etag = resp.headers.get("etag") or previous_etag
            last_modified = resp.headers.get("last-modified") or previous_last_modified
            content_type = (resp.headers.get("content-type") or "").lower().split(";")[0].strip()

            raw_bytes = resp.content[:MAX_WATCH_BYTES]
            candidates: List[NormativeCandidate] = []
            known = {u.strip() for u in (known_urls or set()) if u}

            if "pdf" in content_type or self.target_url.lower().endswith(".pdf"):
                new_hash = hashlib.sha256(raw_bytes).hexdigest()
                snapshot = self._extract_pdf_preview(raw_bytes)
                filename = self._extract_filename(resp, self.target_url)
                if previous_hash and new_hash == previous_hash:
                    return SentinelCheckResult(
                        changed=False,
                        status_code=resp.status_code,
                        new_hash=new_hash,
                        etag=etag,
                        last_modified=last_modified,
                        change_summary="Empreinte SHA-256 du document inchangée.",
                    )
                candidates.append(
                    NormativeCandidate(
                        url=self.target_url,
                        title=filename,
                        filename=filename,
                        reason="PDF officiel modifié ou nouvellement surveillé",
                    )
                )
            else:
                html_text = raw_bytes.decode("utf-8", errors="replace")
                parser = _HTMLLinkAndTextExtractor(self.target_url)
                parser.feed(html_text)
                visible_text = "\n".join(re.sub(r"\s+", " ", line).strip() for line in parser.visible_text_parts if line.strip())

                # Inspect links on the watched page only (no recursive spidering!)
                for link_url, anchor in parser.links:
                    parsed_link = urlparse(link_url)
                    if parsed_link.scheme != "https":
                        continue
                    if not is_same_or_subdomain(parsed_link.hostname or "", self.target_host):
                        continue
                    ok, reason = classify_normative_candidate(link_url, anchor)
                    if not ok:
                        continue
                    fname = self._guess_filename_from_url(link_url) if ".pdf" in link_url.lower() else None
                    candidates.append(
                        NormativeCandidate(
                            url=link_url,
                            title=(anchor or fname or link_url)[:480],
                            filename=fname,
                            reason=reason,
                        )
                    )

                # If watching APDP Benin portal, query its official documentation feed without spidering
                if "apdp.bj" in self.target_host:
                    candidates.extend(await self._check_apdp_feed(http_client))

                # Deduplicate candidates & keep canonical snapshot deterministic
                deduped: List[NormativeCandidate] = []
                seen_urls: Set[str] = set()
                for cand in candidates:
                    if cand.url not in seen_urls:
                        seen_urls.add(cand.url)
                        deduped.append(cand)
                candidates = deduped[:25]

                fingerprint_payload = visible_text + "\n" + "\n".join(
                    sorted(f"{c.url}|{c.title}" for c in candidates)
                )
                new_hash = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
                snapshot = fingerprint_payload

                if previous_hash and new_hash == previous_hash:
                    return SentinelCheckResult(
                        changed=False,
                        status_code=resp.status_code,
                        new_hash=new_hash,
                        etag=etag,
                        last_modified=last_modified,
                        change_summary="Empreinte SHA-256 de la page surveillée inchangée.",
                    )

            new_candidates = [c for c in candidates if c.url not in known]
            diff_summary = compute_text_diff_summary(previous_snapshot, snapshot)

            return SentinelCheckResult(
                changed=True,
                status_code=resp.status_code,
                new_hash=new_hash,
                etag=etag,
                last_modified=last_modified,
                change_summary=diff_summary,
                page_snapshot=snapshot[:60000],
                candidates=new_candidates if new_candidates else candidates[:5],
            )
        finally:
            if owns_client:
                await http_client.aclose()

    async def _check_apdp_feed(self, client: httpx.AsyncClient) -> List[NormativeCandidate]:
        """Targeted check on Benin APDP official documentation endpoints (no formulaires/discours)."""
        discovered: List[NormativeCandidate] = []
        api_base = "https://apiprod.apdp.bj/api/v1"
        for slug in ("lois", "code_du_numerique", "decrets_et_arretes", "decisions"):
            try:
                resp = await client.get(
                    f"{api_base}/articles?slug={slug}&page=1&categorie=&section=",
                    headers={"Accept": "application/json"},
                    timeout=12.0,
                )
                if resp.status_code != 200:
                    continue
                for item in resp.json().get("data", []):
                    title = str(item.get("title") or slug)
                    doc_urls = item.get("document_url") or []
                    if isinstance(doc_urls, str):
                        doc_urls = [doc_urls]
                    for u in doc_urls:
                        if not isinstance(u, str) or not u.startswith("https://"):
                            continue
                        ok, reason = classify_normative_candidate(u, title)
                        if ok:
                            discovered.append(
                                NormativeCandidate(
                                    url=u,
                                    title=title[:480],
                                    filename=self._guess_filename_from_url(u),
                                    reason=f"Flux APDP ({slug}) : {reason}",
                                )
                            )
            except Exception as exc:
                logger.warning("Sentinel APDP feed check warning (%s): %s", slug, exc)
        return discovered

    @staticmethod
    def _extract_pdf_preview(raw_bytes: bytes) -> str:
        try:
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
            try:
                text = "\n".join(page.get_text("text") for page in doc[:10])
            finally:
                doc.close()
            return "\n".join(re.sub(r"\s+", " ", line).strip() for line in html.unescape(text).splitlines() if line.strip())
        except Exception:
            return ""

    @staticmethod
    def _guess_filename_from_url(url: str) -> str:
        last = unquote(urlparse(url).path).split("/")[-1].strip()
        if not last:
            return "acte_normatif.pdf"
        return re.sub(r'[\\/*?:"<>|]', "_", last)

    @classmethod
    def _extract_filename(cls, response: httpx.Response, url: str) -> str:
        cd = response.headers.get("content-disposition", "")
        match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', cd, re.IGNORECASE)
        if match:
            raw = unquote(match.group(1).strip())
            if raw:
                return re.sub(r'[\\/*?:"<>|]', "_", raw)
        return cls._guess_filename_from_url(url)


class LegalCrawlerEngine:
    """Legacy symbol retained for compatibility; blind multi-level crawling is permanently disabled."""

    def __init__(
        self,
        root_url: str,
        max_depth: int = 1,
        country_code: Optional[str] = None,
        existing_filenames: Optional[Set[str]] = None,
    ) -> None:
        validate_public_https_url(root_url)
        self.root_url = root_url
        self.root_host = urlparse(root_url).hostname or ""
        self.max_depth = 1  # Blind multi-level exploration disabled in Phase 7
        self.country_code = (country_code or "bj").lower()
        self.existing_filenames: Set[str] = {
            f.strip().lower() for f in (existing_filenames or set()) if f and f.strip()
        }
        self.sentinel = RegulatorySentinel(root_url)

    async def crawl(self) -> List[DiscoveredDocument]:
        """Blind crawling is retired; use RegulatorySentinel.check_for_updates() instead."""
        logger.warning("LegalCrawlerEngine.crawl() appelé alors que l'aspiration aveugle est désactivée.")
        return []
