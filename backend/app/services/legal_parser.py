"""Deterministic parser for Francophone African legal texts (zero normative loss)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class MasterTextMetadata:
    """Authoritative metadata for a curated Master Corpus instrument."""

    code: str
    title: str
    jurisdiction: str
    authority: str
    level: str
    publication_date: Optional[date]
    official_url: str
    pdf_filename: str
    text_filename: str
    skip_toc: bool = True


MASTER_CORPUS_CATALOG: List[MasterTextMetadata] = [
    MasterTextMetadata(
        code="BJ-NUM-2017",
        title="Loi n° 2017-20 portant Code du Numérique en République du Bénin",
        jurisdiction="BJ",
        authority="Assemblée Nationale / APDP / ANSSI Bénin",
        level="loi",
        publication_date=date(2018, 4, 20),
        official_url="https://service.apdp.bj/documentations/lois",
        pdf_filename="BJ_CODE_NUMERIQUE_2017_20.pdf",
        text_filename="BJ_CODE_NUMERIQUE_2017_20.txt",
    ),
    MasterTextMetadata(
        code="BJ-NUM-2021",
        title="Loi n° 2020-35 du 06 janvier 2021 modifiant la loi n° 2017-20 portant Code du Numérique",
        jurisdiction="BJ",
        authority="Présidence de la République du Bénin",
        level="loi",
        publication_date=date(2021, 1, 6),
        official_url="https://sgg.gouv.bj/doc/loi-2020-35/",
        pdf_filename="BJ_LOI_2020_35_MODIF_CODE_NUMERIQUE.pdf",
        text_filename="BJ_LOI_2020_35_MODIF_CODE_NUMERIQUE.txt",
        skip_toc=False,
    ),
    MasterTextMetadata(
        code="UA-MAL-2014",
        title="Convention de l'Union Africaine sur la Cybersécurité et la Protection des Données à Caractère Personnel (Convention de Malabo)",
        jurisdiction="UA",
        authority="Union Africaine",
        level="convention",
        publication_date=date(2014, 6, 27),
        official_url="https://au.int/fr/treaties/convention-lunion-africaine-sur-la-cybersecurite-et-la-protection-des-donnees-caractere",
        pdf_filename="UA_CONVENTION_MALABO_2014.pdf",
        text_filename="UA_CONVENTION_MALABO_2014.txt",
        skip_toc=False,
    ),
    MasterTextMetadata(
        code="CED-DAT-2010",
        title="Acte Additionnel A/SA.1/01/10 relatif à la protection des données à caractère personnel dans l'espace de la CEDEAO",
        jurisdiction="CEDEAO",
        authority="CEDEAO",
        level="acte_additionnel",
        publication_date=date(2010, 2, 16),
        official_url="https://ecowas.int/",
        pdf_filename="CEDEAO_ACTE_ADDITIONNEL_DONNEES_2010.pdf",
        text_filename="CEDEAO_ACTE_ADDITIONNEL_DONNEES_2010.txt",
        skip_toc=False,
    ),
    MasterTextMetadata(
        code="CED-TRA-2010",
        title="Acte Additionnel A/SA.2/01/10 portant transactions électroniques dans l'espace de la CEDEAO",
        jurisdiction="CEDEAO",
        authority="CEDEAO",
        level="acte_additionnel",
        publication_date=date(2010, 2, 16),
        official_url="https://ecowas.int/",
        pdf_filename="CEDEAO_ACTE_ADDITIONNEL_TRANSACTIONS_2010.pdf",
        text_filename="CEDEAO_ACTE_ADDITIONNEL_TRANSACTIONS_2010.txt",
        skip_toc=False,
    ),
    MasterTextMetadata(
        code="CED-CYB-2011",
        title="Directive C/DIR.1/08/11 portant lutte contre la cybercriminalité dans l'espace de la CEDEAO",
        jurisdiction="CEDEAO",
        authority="CEDEAO",
        level="directive",
        publication_date=date(2011, 8, 19),
        official_url="https://ecowas.int/",
        pdf_filename="CEDEAO_DIRECTIVE_CYBERCRIMINALITE_2011.pdf",
        text_filename="CEDEAO_DIRECTIVE_CYBERCRIMINALITE_2011.txt",
        skip_toc=False,
    ),
    MasterTextMetadata(
        code="OAPI-BAN-2015",
        title="Accord de Bangui instituant une Organisation Africaine de la Propriété Intellectuelle (Acte révisé du 14 décembre 2015)",
        jurisdiction="OAPI",
        authority="OAPI",
        level="accord",
        publication_date=date(2015, 12, 14),
        official_url="https://www.oapi.int/",
        pdf_filename="OAPI_ACCORD_BANGUI_2015.pdf",
        text_filename="OAPI_ACCORD_BANGUI_2015.txt",
        skip_toc=False,
    ),
    MasterTextMetadata(
        code="UEM-PAY-REC",
        title="Recueil des textes légaux et réglementaires régissant l'activité bancaire et financière — Chapitre V : Systèmes et moyens de paiement",
        jurisdiction="UEMOA",
        authority="UEMOA / BCEAO",
        level="recueil",
        publication_date=date(2002, 9, 19),
        official_url="https://www.bceao.int/",
        pdf_filename="UEMOA_BCEAO_RECUEIL_PAIEMENT.pdf",
        text_filename="UEMOA_BCEAO_RECUEIL_PAIEMENT.txt",
    ),
    MasterTextMetadata(
        code="BCEAO-EME-2015",
        title="Instruction n° 008-05-2015 régissant les conditions et modalités d'exercice des activités des émetteurs de monnaie électronique",
        jurisdiction="UEMOA",
        authority="BCEAO",
        level="instruction",
        publication_date=date(2015, 5, 21),
        official_url="https://www.bceao.int/",
        pdf_filename="BCEAO_INSTRUCTION_008_05_2015_EME.pdf",
        text_filename="BCEAO_INSTRUCTION_008_05_2015_EME.txt",
    ),
    MasterTextMetadata(
        code="OHADA-AUDCG",
        title="Acte Uniforme OHADA révisé portant sur le Droit Commercial Général (AUDCG 2010)",
        jurisdiction="OHADA",
        authority="OHADA",
        level="acte_uniforme",
        publication_date=date(2010, 12, 15),
        official_url="https://www.ohada.org/",
        pdf_filename="OHADA_AUDCG_2010.pdf",
        text_filename="OHADA_AUDCG_2010.txt",
    ),
]


@dataclass
class ParsedSection:
    order_index: int
    rank: int
    level_name: str
    title: str
    breadcrumb: str
    parent_order_index: Optional[int] = None


@dataclass
class ParsedArticle:
    order_index: int
    article_number: str
    title: Optional[str]
    full_text: str
    section_order_index: Optional[int] = None


@dataclass
class ParsedLegalDocument:
    sha256_hash: str
    sections: List[ParsedSection] = field(default_factory=list)
    articles: List[ParsedArticle] = field(default_factory=list)
    preamble_text: str = ""


_TOC_DOTTED_RE = re.compile(r"[\.\x08]{4,}\s*\d+\s*$")
_SYNTHETIC_PAGE_RE = re.compile(r"^---\s*PAGES?\s+\d+(?:\s*-\s*\d+)?\s*---\s*$", re.I)

_RUNNING_BOILERPLATE_PATTERNS = [
    re.compile(r"^\[\d+\]\s*$"),
    re.compile(r"^-\s*\d{1,3}\s*-\s*$"),
    re.compile(r"^\d{1,3}\s*$"),
    re.compile(r"^www\.droit-afrique\.com\s*$", re.I),
    re.compile(r"^OAPI\s*$"),
    re.compile(r"^Accord de Bangui révisé 2015\s*$", re.I),
    re.compile(r"^OHADA\s*$"),
    re.compile(r"^Droit commercial général\s*$", re.I),
    re.compile(r"^Acte uniforme OHADA portant sur le droit commercial général\s*$", re.I),
    re.compile(r"^LOI\s+N°\s*2017\s*-?\s*20\s+DU\s+20\s+AVRIL\s+2018\s*$", re.I),
    re.compile(r"^PORTANT\s+CODE\s+DU\s+NUMERIQUE\s+EN\s+REPUBLIQUE\s+DU\s+BENIN\s*$", re.I),
    re.compile(r"^REPUBLIQUE\s+DU\s+BENIN\s*$", re.I),
    re.compile(r"^Fraternité\s*[–-]\s*Justice\s*[–-]\s*Travail\s*$", re.I),
    re.compile(r"^RECUEIL\s+DES\s+TEXTES\s+LEGAUX\s+ET\s+REGLEMENTAIRES\s*$", re.I),
    re.compile(r"^REGISSANT\s+L['’]ACTIVITE\s+BANCAIRE\s+ET\s+FINANCIERE\s*$", re.I),
    re.compile(r"^DANS\s+L['’]UNION\s+MONETAIRE\s+OUEST\s+AFRICAINE\s*$", re.I),
    re.compile(r"^ANNEXES\s*$"),
    re.compile(r"^-{3,}\s*$"),
]

# Rank mapping for legal hierarchy (lower number = higher level)
_SECTION_RULES: List[Tuple[int, str, re.Pattern[str]]] = [
    (
        1,
        "Partie",
        re.compile(
            r"^(?:\*{1,2}|#{1,6}\s*)*"
            r"((?:PREMI[ÈE]RE|DEUXI[ÈE]ME|TROISI[ÈE]ME|QUATRI[ÈE]ME|CINQUI[ÈE]ME|SIXI[ÈE]ME)\s+PARTIE"
            r"|PARTIE\s+(?:[IVX]+|\d+))"
            r"(?:\s*[:\-–—]\s*(.*))?$",
            re.I,
        ),
    ),
    (
        1,
        "Livre",
        re.compile(
            r"^(?:\*{1,2}|#{1,6}\s*)*"
            r"(LIVRE\s+(?:PR[ÉE]LIMINAIRE|PREMIER|DEUXI[ÈE]ME|TROISI[ÈE]ME|QUATRI[ÈE]ME|CINQUI[ÈE]ME|SIXI[ÈE]ME|SEPTI[ÈE]ME|1er|[IVX]+|\d+))"
            r"(?:\s*[:\-–—]\s*(.*))?$",
            re.I,
        ),
    ),
    (
        1,
        "Annexe",
        re.compile(
            r"^(?:\*{1,2}|#{1,6}\s*)*"
            r"(ANNEXE\s*(?:UNIQUE|[IVX]+|\d+)?)"
            r"(?:\s*[:\-–—]\s*(.*))?$",
            re.I,
        ),
    ),
    (
        2,
        "Titre",
        re.compile(
            r"^(?:\*{1,2}|#{1,6}\s*)*"
            r"(TITRE\s+(?:PR[ÉE]LIMINAIRES?|PREMIER|DEUXI[ÈE]ME|TROISI[ÈE]ME|1er|[IVX]+|\d+))"
            r"(?:\s*[:\-–—]\s*(.*))?$",
            re.I,
        ),
    ),
    (
        3,
        "Chapitre",
        re.compile(
            r"^(?:\*{1,2}|#{1,6}\s*)*"
            r"(CHAPITRE\s+(?:PR[ÉE]LIMINAIRE|UNIQUE|PREMIER|DEUXI[ÈE]ME|TROISI[ÈE]ME|1er|[IVX]+|\d+))"
            r"(?:\s*[:\-–—]\s*(.*))?$",
            re.I,
        ),
    ),
    (
        4,
        "Section",
        re.compile(
            r"^(?:\*{1,2}|#{1,6}\s*)*"
            r"(SECTION\s+(?:UNIQUE|PREMI[ÈE]RE|1[èe]re|[IVX]+|\d+))"
            r"(?:\s*[:\-–—]\s*(.*))?$",
            re.I,
        ),
    ),
    (
        5,
        "Sous-section",
        re.compile(
            r"^(?:\*{1,2}|#{1,6}\s*)*"
            r"(SOUS-SECTION\s+(?:UNIQUE|[IVX]+|\d+))"
            r"(?:\s*[:\-–—]\s*(.*))?$",
            re.I,
        ),
    ),
]

# Top-level embedded legal instruments inside compendiums (e.g. UEMOA Recueil)
_INSTRUMENT_RE = re.compile(
    r"^(R[èe]glement|Directive|Instruction|D[ée]cision)\s+n°\s*[A-Z0-9/\.-]+\s+(?:du\s+\d+.*)?$",
    re.I,
)

# Article boundary regexes
_ARTICLE_STD_RE = re.compile(
    r"^(?:\*{1,2}|#{1,6}\s*)*"
    r"(Articles?)\s*"
    r"(Premier|1er|\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies))?(?:[\.\-]\d+)*(?:\s+nouveau)?)"
    r"(?:\s*[:.\-–—]\s*(.*)|\s+([^\d\W].*))?$",
    re.I,
)

_ARTICLE_DOT_RE = re.compile(
    r"^(?:\*{1,2}|#{1,6}\s*)*"
    r"Art\.\s*"
    r"(\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies))?(?:[\.\-]\d+)*)"
    r"\s*\.\-\s*(.*)$",
    re.I,
)

_FIRST_ARTICLE_1_RE = re.compile(
    r"^(?:\*{1,2}|#{1,6}\s*)*(?:Articles?\s*(?:Premier|1er|1\b)|Art\.\s*1\s*\.\-)",
    re.I,
)

_NON_TITLE_PREFIXES = (
    "au sens",
    "toute personne",
    "tout commerçant",
    "tout ",
    "toutes ",
    "nul ne peut",
    "les dispositions",
    "les actes",
    "est ",
    "sont ",
    "lorsqu",
    "dans ",
    "pour ",
    "nonobstant",
    "sauf ",
    "sans préjudice",
    "quiconque",
    "la présente",
    "le présent",
    "l'ensemble",
    "il est ",
    "en cas ",
)


def _strip_markdown(text: str) -> str:
    cleaned = text.replace("\xa0", " ").replace("\x08", " ").strip()
    cleaned = re.sub(r"^[#>\s]+", "", cleaned)
    cleaned = cleaned.strip("*").strip()
    return re.sub(r"\s{2,}", " ", cleaned)


def _clean_lines(raw_text: str) -> List[str]:
    """Normalize raw extracted text: strip synthetic page markers and running page headers."""
    # First pass: basic whitespace & synthetic markers, keeping isolated numbers so 'Article\n247' merges cleanly
    pre_cleaned: List[str] = []
    for raw in raw_text.splitlines():
        line = raw.replace("\xa0", " ").replace("\x08", " ").strip()
        if _SYNTHETIC_PAGE_RE.match(line):
            continue
        # Fix glued leading page numbers before LIVRE/TITRE/CHAPITRE/SECTION (e.g. '7LIVRE PRELIMINAIRE')
        line = re.sub(
            r"^\d{1,3}(?=(?:LIVRE|TITRE|CHAPITRE|SECTION|Article)\b)",
            "",
            line,
            flags=re.I,
        )
        pre_cleaned.append(line)

    # Second pass: rejoin justified-PDF broken headers where 'Article' is alone on one line and '<num>' is next
    merged: List[str] = []
    i = 0
    while i < len(pre_cleaned):
        cur = pre_cleaned[i]
        if re.match(r"^(?:\*{1,2}|#{1,6}\s*)*Articles?$", cur, re.I):
            j = i + 1
            while j < len(pre_cleaned) and not pre_cleaned[j]:
                j += 1
            if j < len(pre_cleaned) and re.match(
                r"^(?:Premier|1er|\d+(?:\s*(?:bis|ter|quater))?)\b",
                pre_cleaned[j],
                re.I,
            ):
                parts = [cur, pre_cleaned[j]]
                k = j + 1
                if k < len(pre_cleaned) and pre_cleaned[k] == ":":
                    parts.append(":")
                    k += 1
                merged.append(" ".join(parts).replace(" :", " :"))
                i = k
                continue
        merged.append(cur)
        i += 1

    # Third pass: remove running page headers & standalone page numbers
    return [
        line for line in merged
        if not any(pat.match(line) for pat in _RUNNING_BOILERPLATE_PATTERNS)
    ]


def _find_body_start_index(lines: List[str], skip_toc: bool) -> int:
    """Locate the first line after any front-matter Table of Contents."""
    if not skip_toc:
        return 0

    first_art_idx: Optional[int] = None
    for idx, line in enumerate(lines):
        if _TOC_DOTTED_RE.search(line):
            continue
        if _FIRST_ARTICLE_1_RE.match(line):
            first_art_idx = idx
            break

    if first_art_idx is None:
        return 0

    # Look backwards from first_art_idx for the last dotted TOC line
    last_toc_idx = -1
    for idx in range(first_art_idx - 1, -1, -1):
        if _TOC_DOTTED_RE.search(lines[idx]):
            last_toc_idx = idx
            break

    if last_toc_idx == -1:
        return 0

    # Advance past the last TOC line (keeping any section header right above Article 1)
    return last_toc_idx + 1


def _looks_like_section_title_cont(line: str) -> bool:
    if not line or len(line) > 140:
        return False
    if _ARTICLE_STD_RE.match(line) or _ARTICLE_DOT_RE.match(line):
        return False
    for _, _, pat in _SECTION_RULES:
        if pat.match(line):
            return False
    if _TOC_DOTTED_RE.search(line):
        return False
    if line.startswith(("«", '"', "-", "•", "1.", "2.")):
        return False
    # Typically uppercase or short noun phrase without ending period
    if line.endswith("."):
        return False
    return True


def _match_section(line: str, is_compendium: bool) -> Optional[Tuple[int, str, str]]:
    """Return (rank, level_name, inline_title) if line is a normative division heading."""
    if not line or _TOC_DOTTED_RE.search(line):
        return None
    if line.startswith(("«", '"')):
        return None

    plain = _strip_markdown(line)
    # Reject lines that clearly belong to sentence prose
    if len(plain) > 220 or plain.endswith(";") or plain.endswith(","):
        return None

    if is_compendium and _INSTRUMENT_RE.match(plain):
        # Avoid 'vu le Règlement...' preambles
        if not re.match(r"^(?:vu|considérant|conformément|en application)\b", plain, re.I):
            return (0, plain[:120], "")

    for rank, _, pat in _SECTION_RULES:
        m = pat.match(line)
        if not m:
            continue
        level_name = _strip_markdown(m.group(1))
        inline_title = _strip_markdown(m.group(2) or "")
        # Guard against prose mentions like "Annexe V. Les dispositions suivantes s'appliquent..."
        if inline_title.lower().startswith(_NON_TITLE_PREFIXES):
            return None
        # Guard against cross-references like "Section 3 ci-dessus prévoit..."
        if any(
            kw in inline_title.lower()
            for kw in ("ci-dessus", "ci-après", "du présent", "est applicable", "sont applicables", "prévoit que")
        ):
            return None
        return (rank, level_name, inline_title)

    return None


def _match_article(line: str) -> Optional[Tuple[str, Optional[str], str]]:
    """Return (article_number, optional_title, inline_body) if line starts an article."""
    if not line or _TOC_DOTTED_RE.search(line):
        return None
    # Do not split quoted amendments inside an amending article (e.g. Loi 2020-35 Art. 1er)
    if line.lstrip().startswith(("«", '"', "“")):
        return None

    m_dot = _ARTICLE_DOT_RE.match(line)
    if m_dot:
        num = re.sub(r"\s+", " ", m_dot.group(1).strip())
        rest = _strip_markdown(m_dot.group(2) or "")
        article_number = f"Article {num}"
        if rest and len(rest) <= 120 and not rest.lower().startswith(_NON_TITLE_PREFIXES) and "." not in rest[:-1]:
            return (article_number, rest, "")
        return (article_number, None, rest)

    m_std = _ARTICLE_STD_RE.match(line)
    if m_std:
        num = re.sub(r"\s+", " ", m_std.group(2).strip())
        raw_rest = m_std.group(3) if m_std.group(3) is not None else (m_std.group(4) or "")
        rest = _strip_markdown(raw_rest)
        article_number = f"Article {num}"
        # Special guard: avoid prose lines like "Article 12 du présent code dispose..."
        if rest.lower().startswith(("du présent", "de la présente", "dispose ", "prévoit ", "précédent", "susvisé", "ci-dessus")):
            return None
        if rest and len(rest) <= 130 and not rest.lower().startswith(_NON_TITLE_PREFIXES):
            return (article_number, rest, "")
        return (article_number, None, rest)

    return None


def _normalize_article_body(lines: List[str]) -> str:
    """Cleanly join article lines, removing mid-word soft hyphen wraps while preserving structure."""
    # Trim leading/trailing blank lines
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    if not lines:
        return ""

    text = "\n".join(lines)
    # Rejoin obvious mid-word line-break hyphenation from PDF columns (e.g. 'commercia-\nles')
    text = re.sub(r"([a-zàâäéèêëïîôöùûüç])-\n([a-zàâäéèêëïîôöùûüç])", r"\1\2", text)
    # Collapse excessive blank lines to at most 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_legal_text(raw_text: str, metadata: MasterTextMetadata) -> ParsedLegalDocument:
    """Parse a clean UTF-8 legal document deterministically into hierarchical sections & articles."""
    sha256_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    lines = _clean_lines(raw_text)
    start_idx = _find_body_start_index(lines, skip_toc=metadata.skip_toc)

    is_compendium = metadata.level == "recueil"
    sections: List[ParsedSection] = []
    articles: List[ParsedArticle] = []

    # Stack of active sections for hierarchical breadcrumbs: [(rank, ParsedSection)]
    section_stack: List[Tuple[int, ParsedSection]] = []
    preamble_lines: List[str] = []

    current_article_num: Optional[str] = None
    current_article_title: Optional[str] = None
    current_article_lines: List[str] = []
    current_article_section_idx: Optional[int] = None
    current_annexe_lines: List[str] = []
    current_annexe_has_articles = False

    def flush_article() -> None:
        nonlocal current_article_num, current_article_title, current_article_lines, current_article_section_idx
        nonlocal current_annexe_has_articles
        if current_article_num is None:
            return
        body = _normalize_article_body(current_article_lines)
        full_header = current_article_num
        if current_article_title:
            full_header = f"{current_article_num} : {current_article_title}"
        full_text = f"{full_header}\n{body}".strip() if body else full_header
        articles.append(
            ParsedArticle(
                order_index=len(articles) + 1,
                article_number=current_article_num,
                title=current_article_title,
                full_text=full_text,
                section_order_index=current_article_section_idx,
            )
        )
        current_annexe_has_articles = True
        current_article_num = None
        current_article_title = None
        current_article_lines = []
        current_article_section_idx = None

    def flush_annexe_if_needed() -> None:
        nonlocal current_annexe_lines, current_annexe_has_articles
        if (
            not current_annexe_has_articles
            and current_annexe_lines
            and section_stack
            and section_stack[-1][1].level_name.upper().startswith("ANNEXE")
        ):
            sec = section_stack[-1][1]
            body = _normalize_article_body(current_annexe_lines)
            if len(body) >= 40:
                articles.append(
                    ParsedArticle(
                        order_index=len(articles) + 1,
                        article_number=sec.level_name,
                        title=sec.title,
                        full_text=f"{sec.level_name} : {sec.title}\n{body}".strip(),
                        section_order_index=sec.order_index,
                    )
                )
        current_annexe_lines = []
        current_annexe_has_articles = False

    i = start_idx
    while i < len(lines):
        line = lines[i]

        # 1. Check Article start
        art_match = _match_article(line)
        if art_match:
            flush_article()
            art_num, art_title, inline_body = art_match
            current_article_num = art_num
            current_article_title = art_title
            current_article_section_idx = section_stack[-1][1].order_index if section_stack else None
            if inline_body:
                current_article_lines.append(inline_body)
            i += 1
            continue

        # 2. Check Section heading
        sec_match = _match_section(line, is_compendium=is_compendium)
        if sec_match:
            rank, level_name, inline_title = sec_match
            norm_level = re.sub(r"\s+", " ", level_name.upper()).strip()
            # Ignore running page headers repeating a currently active section
            is_repeated_header = any(
                r == rank and re.sub(r"\s+", " ", s.level_name.upper()).strip() == norm_level
                for r, s in section_stack
            )
            if is_repeated_header:
                i += 1
                continue

            flush_article()
            flush_annexe_if_needed()
            title_parts = [inline_title] if inline_title else []

            # Consume up to 2 continuation lines if title wraps (and next line isn't an article/section)
            look = i + 1
            while look < len(lines) and len(title_parts) < 3:
                nxt = lines[look].strip()
                if not nxt:
                    break
                if _match_article(nxt) or _match_section(nxt, is_compendium=is_compendium):
                    break
                if _looks_like_section_title_cont(nxt):
                    title_parts.append(_strip_markdown(nxt))
                    look += 1
                    continue
                break

            sec_title = " ".join(p for p in title_parts if p).strip() or level_name
            while section_stack and section_stack[-1][0] >= rank:
                section_stack.pop()

            parent_idx = section_stack[-1][1].order_index if section_stack else None
            parent_crumbs = [
                s.level_name + (f" ({s.title})" if s.title and s.title != s.level_name else "")
                for _, s in section_stack
            ]
            cur_crumb = level_name + (f" : {sec_title}" if sec_title and sec_title != level_name else "")
            breadcrumb = " > ".join([*parent_crumbs, cur_crumb])[:990]

            sec = ParsedSection(
                order_index=len(sections) + 1,
                rank=rank,
                level_name=level_name[:120],
                title=sec_title[:500],
                breadcrumb=breadcrumb,
                parent_order_index=parent_idx,
            )
            sections.append(sec)
            section_stack.append((rank, sec))
            current_annexe_has_articles = False
            i = look
            continue

        if current_article_num is not None:
            current_article_lines.append(line)
        elif section_stack and section_stack[-1][1].level_name.upper().startswith("ANNEXE"):
            current_annexe_lines.append(line)
        elif line.strip():
            preamble_lines.append(line.strip())

        i += 1

    flush_article()
    flush_annexe_if_needed()

    # Special case: Annexes in BCEAO Instruction 008-05-2015 after Article 42 have no 'Article' headers.
    # Preserve any uncaptured substantive Annexes as dedicated normative entries under their Annexe section.
    return ParsedLegalDocument(
        sha256_hash=sha256_hash,
        sections=sections,
        articles=articles,
        preamble_text="\n".join(preamble_lines[:40]),
    )


def load_master_text_file(corpus_dir: Path, meta: MasterTextMetadata) -> str:
    """Load clean UTF-8 text from local corpus directory."""
    txt_path = corpus_dir / meta.text_filename
    return txt_path.read_text(encoding="utf-8")
