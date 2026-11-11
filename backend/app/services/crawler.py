"""Intelligent legal web crawler with recursive discovery, document streaming, and MinIO archiving."""

import asyncio
import hashlib
import html
import ipaddress
import logging
import mimetypes
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List, Optional, Set, Tuple
from urllib.parse import unquote, urljoin, urlparse

import fitz
import httpx

from app.services.minio_client import ensure_bucket_exists, get_minio_client, upload_file

logger = logging.getLogger(__name__)

LEGAL_KEYWORDS = {
    "loi", "lois", "decret", "décret", "decrets", "décrets", "arrete", "arrêté",
    "reglement", "règlement", "directive", "deliberation", "délibération", "decision",
    "décision", "guide", "documentation", "juridique", "legal", "textes", "corpus",
    "donnees", "données", "personnelles", "conformite", "conformité", "telecharger",
    "download", "recueil", "code", "numerique", "numérique"
}

MAX_DOWNLOAD_BYTES = 35 * 1024 * 1024  # 35 MB per document
MAX_PAGES_PER_CRAWL = 35
MINIO_BUCKET_LEGAL = "legal-sources"


class _HTMLLinkAndTextExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: List[Tuple[str, str]] = []  # (absolute_url, anchor_text)
        self.current_href: Optional[str] = None
        self.current_anchor_text: List[str] = []
        self._skip_depth = 0
        self.visible_text_parts: List[str] = []
        self._ignored_tags = {"script", "style", "noscript", "svg"}

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
                            abs_url = urljoin(self.base_url, clean_val)
                            self.current_href = abs_url
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


def is_same_or_subdomain(target_host: str, root_host: str) -> bool:
    """Verify target_host is equal to or a subdomain of root_host."""
    t = target_host.lower().strip()
    r = root_host.lower().strip()
    return t == r or t.endswith(f".{r}")


def score_link_priority(url: str, anchor_text: str) -> int:
    """Give higher priority to links matching legal documentation keywords."""
    combined = f"{url.lower()} {anchor_text.lower()}"
    score = 0
    if ".pdf" in url.lower():
        score += 50
    for kw in LEGAL_KEYWORDS:
        if kw in combined:
            score += 10
    return score


@dataclass
class DiscoveredDocument:
    download_url: str
    original_filename: str
    content_type: str
    content_hash: str
    content_text: str
    minio_path: str
    source_page_url: str
    anchor_text: str
    file_size_bytes: int


class LegalCrawlerEngine:
    def __init__(
        self,
        root_url: str,
        max_depth: int = 2,
        country_code: Optional[str] = None,
        existing_filenames: Optional[Set[str]] = None,
    ):
        validate_public_https_url(root_url)
        self.root_url = root_url
        self.root_host = urlparse(root_url).hostname or ""
        self.max_depth = min(max(1, max_depth), 3)
        self.country_code = (country_code or "bj").lower()
        self.existing_filenames: Set[str] = {
            f.strip().lower() for f in (existing_filenames or set()) if f and f.strip()
        }
        self.visited_urls: Set[str] = set()
        self.discovered_documents: List[DiscoveredDocument] = []
        self.skipped_duplicates_count: int = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ECO-Compliance-Engine-Crawler/2.0; +https://ece.gov)",
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
        }

    async def crawl(self) -> List[DiscoveredDocument]:
        """Execute recursive crawl and return discovered, downloaded and archived legal documents."""
        minio_client = get_minio_client()
        ensure_bucket_exists(minio_client, MINIO_BUCKET_LEGAL)

        # Queue items: (url, current_depth, referrer_url, anchor_text)
        queue: List[Tuple[str, int, str, str]] = [(self.root_url, 0, "", "Accueil")]
        pages_crawled = 0

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
            while queue and pages_crawled < MAX_PAGES_PER_CRAWL:
                # Sort queue by priority score
                queue.sort(key=lambda item: score_link_priority(item[0], item[3]), reverse=True)
                current_url, current_depth, referrer, anchor = queue.pop(0)

                # Normalize URL (strip fragment)
                clean_url = current_url.split("#")[0]
                if clean_url in self.visited_urls:
                    continue
                self.visited_urls.add(clean_url)

                try:
                    validate_public_https_url(clean_url)
                    parsed = urlparse(clean_url)
                    if not is_same_or_subdomain(parsed.hostname or "", self.root_host):
                        continue

                    # Stream head or small get to check content-type
                    async with client.stream("GET", clean_url, headers=self.headers) as resp:
                        if resp.status_code >= 400:
                            continue

                        raw_content_type = resp.headers.get("content-type", "").lower()
                        content_type = raw_content_type.split(";")[0].strip()
                        is_pdf = "pdf" in content_type or clean_url.lower().endswith(".pdf")

                        # If it is a PDF or document
                        if is_pdf:
                            filename = self._extract_filename(resp, clean_url)
                            # Dedup check: If filename already exists under this source, skip downloading
                            if filename.strip().lower() in self.existing_filenames:
                                logger.info(
                                    "PDF '%s' déjà collecté pour cette source parent. Téléchargement ignoré.",
                                    filename,
                                )
                                self.skipped_duplicates_count += 1
                                continue

                            doc = await self._process_pdf_document(
                                resp, clean_url, referrer, anchor, minio_client, filename=filename
                            )
                            if doc:
                                self.discovered_documents.append(doc)
                                self.existing_filenames.add(doc.original_filename.strip().lower())
                            continue

                        # If it is an HTML page and depth < max_depth
                        if ("html" in content_type or "xhtml" in content_type) and current_depth < self.max_depth:
                            pages_crawled += 1
                            body = bytearray()
                            async for chunk in resp.aiter_bytes():
                                body.extend(chunk)
                                if len(body) > 10 * 1024 * 1024:  # 10 MB max for HTML
                                    break

                            html_text = body.decode("utf-8", errors="replace")
                            parser = _HTMLLinkAndTextExtractor(clean_url)
                            parser.feed(html_text)

                            # Enqueue child links
                            for child_url, child_anchor in parser.links:
                                child_clean = child_url.split("#")[0]
                                if child_clean not in self.visited_urls:
                                    queue.append((child_clean, current_depth + 1, clean_url, child_anchor))

                except Exception as exc:
                    logger.warning("Crawler encountered an error on %s: %s", clean_url, exc)
                    continue

        return self.discovered_documents

    async def _process_pdf_document(
        self,
        response: httpx.Response,
        url: str,
        referrer: str,
        anchor: str,
        minio_client,
        filename: Optional[str] = None,
    ) -> Optional[DiscoveredDocument]:
        """Download binary PDF, compute SHA-256, extract text, and archive to MinIO."""
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > MAX_DOWNLOAD_BYTES:
                logger.warning("PDF exceeds size limit: %s", url)
                return None

        if len(body) < 500:
            return None

        content_bytes = bytes(body)
        sha256 = hashlib.sha256(content_bytes).hexdigest()

        # Extract original filename if not provided
        if not filename:
            filename = self._extract_filename(response, url)

        # Extract text via PyMuPDF
        try:
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            try:
                text_parts = [page.get_text("text") for page in doc]
                full_text = "\n".join(text_parts).strip()
            finally:
                doc.close()
        except Exception as exc:
            logger.warning("Failed to extract text from PDF %s: %s", url, exc)
            return None

        # Clean text
        normalized_text = "\n".join(re.sub(r"\s+", " ", line).strip() for line in html.unescape(full_text).splitlines())
        normalized_text = re.sub(r"\n{3,}", "\n\n", normalized_text).strip()

        if len(normalized_text) < 100:
            return None

        # Archive to MinIO: legal-sources/{country}/{sha256[:12]}_{filename}
        minio_obj_name = f"{self.country_code}/{sha256[:12]}_{filename}"
        upload_file(minio_client, MINIO_BUCKET_LEGAL, minio_obj_name, content_bytes, "application/pdf")

        return DiscoveredDocument(
            download_url=url,
            original_filename=filename,
            content_type="application/pdf",
            content_hash=sha256,
            content_text=normalized_text,
            minio_path=f"{MINIO_BUCKET_LEGAL}/{minio_obj_name}",
            source_page_url=referrer or self.root_url,
            anchor_text=anchor,
            file_size_bytes=len(content_bytes),
        )

    def _extract_filename(self, response: httpx.Response, url: str) -> str:
        """Extract filename from Content-Disposition header or fallback to URL path segment."""
        cd = response.headers.get("content-disposition", "")
        if "filename=" in cd:
            match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', cd, re.IGNORECASE)
            if match:
                raw_name = unquote(match.group(1).strip())
                if raw_name:
                    return re.sub(r'[\\/*?:"<>|]', "_", raw_name)

        # Fallback to URL path
        path = unquote(urlparse(url).path)
        last_segment = path.split("/")[-1].strip()
        if last_segment:
            if not last_segment.lower().endswith(".pdf"):
                last_segment = f"{last_segment}.pdf"
            return re.sub(r'[\\/*?:"<>|]', "_", last_segment)

        return "document_juridique.pdf"
