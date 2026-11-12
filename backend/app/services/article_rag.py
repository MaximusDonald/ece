"""Article-level vectorization (TPM-throttled) and Hybrid Search (HNSW + French GIN FTS)."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import text
from sqlmodel import select

from app.core.database import async_session_maker
from app.models.corpus import LegalArticle, LegalSection, LegalText
from app.services.llm_client import GeminiClient

logger = logging.getLogger(__name__)

_UEMOA_COUNTRIES = {"BJ", "BF", "CI", "GW", "ML", "NE", "SN", "TG"}
_CEDEAO_COUNTRIES = _UEMOA_COUNTRIES | {"CV", "GH", "GM", "GN", "LR", "NG", "SL"}
_OAPI_COUNTRIES = {"BJ", "BF", "CF", "CG", "CI", "CM", "GA", "GN", "GQ", "GW", "KM", "ML", "MR", "NE", "SN", "TD", "TG"}
_OHADA_COUNTRIES = _OAPI_COUNTRIES | {"CD"}

_PRIORITY_ORDER = [
    "BJ-NUM-2017",
    "BJ-NUM-2021",
    "CED-DAT-2010",
    "CED-TRA-2010",
    "CED-CYB-2011",
    "UA-MAL-2014",
    "BCEAO-EME-2015",
    "OHADA-AUDCG",
    "UEM-PAY-REC",
    "OAPI-BAN-2015",
]

_FR_STOPWORDS = {
    "les", "des", "une", "pour", "dans", "sur", "avec", "par", "aux", "est", "sont",
    "qui", "que", "quoi", "dont", "vers", "chez", "sous", "sans", "tout", "tous",
    "toute", "toutes", "etre", "être", "avoir", "faire", "fait", "entre", "selon",
}

_LEGAL_CONCEPT_EXPANSIONS: List[Tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(france|paris|europe|ue|usa|etats-unis|états-unis|aws|azure|gcp|ovh|cloud|"
            r"étranger|etranger|hors\s+b[ée]nin|hors\s+cedeao|pays\s+tiers|[ée]tat\s+tiers)\b",
            re.I,
        ),
        "transfert données caractère personnel État tiers pays tiers niveau protection adéquat autorisation APDP",
    ),
    (
        re.compile(r"\b(sant[ée]|m[ée]dical|patient|biom[ée]tri\w*|g[ée]n[ée]tique|mineur|enfant)\b", re.I),
        "données sensibles catégories particulières consentement explicite intérêt public",
    ),
    (
        re.compile(r"\b(fuite|violation|intrusion|piratage|ransomware|ran[çc]ongiciel|incident)\b", re.I),
        "violation données sécurité notification autorité protection accès illégal maintien frauduleux",
    ),
    (
        re.compile(r"\b(mobile\s+money|momo|fintech|wallet|portefeuille|paiement|monnaie\s+[ée]lectronique)\b", re.I),
        "monnaie électronique émetteur prestataire services paiement agrément BCEAO",
    ),
    (
        re.compile(r"\b(code\s+source|logiciel|saas|algorithme|brevet|marque|propri[ée]t[ée]\s+intellectuelle)\b", re.I),
        "programme ordinateur logiciel œuvre protection propriété littéraire artistique industrielle OAPI",
    ),
]


def expand_legal_query(query: str) -> str:
    """Enrich factual technical queries with West African statutory legal terminology."""
    expansions = [extra for pat, extra in _LEGAL_CONCEPT_EXPANSIONS if pat.search(query)]
    if not expansions:
        return query
    return f"{query} — {' ; '.join(expansions)}"


@dataclass
class ArticleSearchResult:
    """Ranked result returned by Hybrid Article-RAG retrieval."""

    article_id: UUID
    text_id: UUID
    text_code: str
    text_title: str
    jurisdiction: str
    authority: str
    section_breadcrumb: str
    article_number: str
    title: Optional[str]
    full_text: str
    topics: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    has_sanction: bool = False
    sanction_details: Optional[str] = None
    compliance_rule_type: Optional[str] = None
    dense_score: float = 0.0
    bm25_score: float = 0.0
    score: float = 0.0


def jurisdictions_for_country(country_code: Optional[str]) -> List[str]:
    """Resolve national + applicable regional/continental jurisdictions for a project country."""
    if not country_code:
        return ["BJ", "CEDEAO", "UEMOA", "OHADA", "OAPI", "UA"]
    cc = country_code.strip().upper()
    scopes = [cc, "UA"]
    if cc in _CEDEAO_COUNTRIES:
        scopes.append("CEDEAO")
    if cc in _UEMOA_COUNTRIES:
        scopes.append("UEMOA")
    if cc in _OHADA_COUNTRIES:
        scopes.append("OHADA")
    if cc in _OAPI_COUNTRIES:
        scopes.append("OAPI")
    return scopes


def build_article_embedding_text(
    text_code: str,
    jurisdiction: str,
    breadcrumb: str,
    article: LegalArticle,
    max_chars: int = 1800,
) -> str:
    """Build canonical article embedding representation (Metadata + Section + Number + Title + Verbatim Body)."""
    header = f"[{jurisdiction} | {text_code}]"
    if breadcrumb:
        header += f" {breadcrumb}"
    title_line = f"{article.article_number} : {article.title}" if article.title else article.article_number
    body = article.full_text[:max_chars]
    return f"{header}\n{title_line}\n{body}".strip()


def _estimate_tokens(text_str: str) -> int:
    # Conservative token estimate for accented French text (~2 chars/token in Gemini tokenizer)
    return max(1, (len(text_str) + 1) // 2)


def _build_or_tsquery(query: str) -> str:
    """Convert natural language French query into a safe OR-ed lexeme query for to_tsquery."""
    tokens = re.findall(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+", query.lower())
    filtered = [t for t in tokens if (len(t) >= 3 or t.isdigit()) and t not in _FR_STOPWORDS]
    if not filtered:
        filtered = [t for t in tokens if len(t) >= 2]
    # Deduplicate preserving order
    unique: List[str] = []
    seen = set()
    for t in filtered[:16]:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return " | ".join(unique)


class _RollingWindowRateLimiter:
    """Respect Gemini Embedding 2 strict 30K TPM & RPM limits using a 62s rolling window."""

    def __init__(self, max_tpm: int = 24000, max_rpm: int = 60):
        self.max_tpm = max_tpm
        self.max_rpm = max_rpm
        self._events: Deque[Tuple[float, int]] = deque()

    async def acquire(self, est_tokens: int) -> None:
        while True:
            now = time.monotonic()
            while self._events and now - self._events[0][0] >= 62.0:
                self._events.popleft()

            used_tokens = sum(tok for _, tok in self._events)
            used_reqs = len(self._events)

            if (used_tokens + est_tokens <= self.max_tpm or used_reqs == 0) and used_reqs + 1 <= self.max_rpm:
                self._events.append((now, est_tokens))
                return

            oldest_ts = self._events[0][0]
            wait_sec = max(0.5, 62.5 - (now - oldest_ts))
            logger.info(
                "Embedding TPM throttle: used=%d/%d tokens in 60s window; sleeping %.1fs.",
                used_tokens,
                self.max_tpm,
                wait_sec,
            )
            await asyncio.sleep(wait_sec)


async def vectorize_articles(
    text_codes: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    max_batch_tokens: int = 5500,
    max_batch_items: int = 20,
    max_tpm: int = 24000,
) -> int:
    """Compute and persist 1536-d embeddings for LegalArticle rows where embedding IS NULL."""
    client = GeminiClient(timeout=40.0)
    limiter = _RollingWindowRateLimiter(max_tpm=max_tpm, max_rpm=60)
    total_embedded = 0

    try:
        async with async_session_maker() as session:
            text_rows = (await session.execute(select(LegalText))).scalars().all()
            texts_by_id = {t.id: t for t in text_rows}
            sec_rows = (await session.execute(select(LegalSection))).scalars().all()
            breadcrumbs = {s.id: s.breadcrumb for s in sec_rows}

            priority_map = {code: idx for idx, code in enumerate(_PRIORITY_ORDER)}
            ordered_texts = sorted(
                [t for t in text_rows if not text_codes or t.code in text_codes],
                key=lambda t: (priority_map.get(t.code, 999), t.code),
            )

            for ltext in ordered_texts:
                query = (
                    select(LegalArticle)
                    .where(LegalArticle.text_id == ltext.id, LegalArticle.embedding.is_(None))
                    .order_by(LegalArticle.order_index)
                )
                articles = (await session.execute(query)).scalars().all()
                if not articles:
                    continue

                if limit is not None:
                    remaining = max(0, limit - total_embedded)
                    if remaining == 0:
                        break
                    articles = articles[:remaining]

                logger.info("Vectorizing %s: %d pending articles...", ltext.code, len(articles))

                idx = 0
                while idx < len(articles):
                    batch: List[LegalArticle] = []
                    batch_inputs: List[str] = []
                    batch_tokens = 0

                    while idx < len(articles) and len(batch) < max_batch_items:
                        art = articles[idx]
                        bc = breadcrumbs.get(art.section_id, "") if art.section_id else ""
                        payload = build_article_embedding_text(ltext.code, ltext.jurisdiction, bc, art)
                        est_tok = _estimate_tokens(payload)
                        if batch and batch_tokens + est_tok > max_batch_tokens:
                            break
                        batch.append(art)
                        batch_inputs.append(payload)
                        batch_tokens += est_tok
                        idx += 1

                    await limiter.acquire(batch_tokens)

                    vectors: Optional[List[List[float]]] = None
                    for attempt in range(5):
                        try:
                            vectors = await client.get_embeddings(batch_inputs, task_type="RETRIEVAL_DOCUMENT")
                            break
                        except Exception as exc:
                            err_str = str(exc)
                            backoff = min(65.0, 5.0 * (2 ** attempt))
                            logger.warning(
                                "Embedding batch error on %s (attempt %d/5): %s -> retry in %.1fs",
                                ltext.code,
                                attempt + 1,
                                err_str[:180],
                                backoff,
                            )
                            await asyncio.sleep(backoff)

                    if not vectors or len(vectors) != len(batch):
                        raise RuntimeError(f"Failed to embed batch for {ltext.code} after retries.")

                    for art, vec in zip(batch, vectors):
                        art.embedding = vec
                        session.add(art)
                    await session.commit()
                    total_embedded += len(batch)
                    logger.info(
                        "Embedded %d/%d total (%s batch=%d, ~%d tokens)",
                        total_embedded,
                        total_embedded + (len(articles) - idx),
                        ltext.code,
                        len(batch),
                        batch_tokens,
                    )
    finally:
        await client.aclose()

    return total_embedded


async def hybrid_search_articles(
    query: str,
    *,
    jurisdictions: Optional[Sequence[str]] = None,
    text_codes: Optional[Sequence[str]] = None,
    has_sanction: Optional[bool] = None,
    limit: int = 8,
    alpha: float = 0.65,
) -> List[ArticleSearchResult]:
    """
    Hybrid Article-RAG retrieval combining HNSW cosine similarity and PostgreSQL French GIN FTS:
        score = alpha * dense_score + (1 - alpha) * bm25_score
    """
    query_clean = query.strip()
    if not query_clean:
        return []

    expanded_query = expand_legal_query(query_clean)
    is_definition_query = bool(re.search(r"\b(d[ée]finition|d[ée]finir|sens\s+de|signifie)\b", query_clean, re.I))

    query_vec_str: Optional[str] = None
    effective_alpha = max(0.0, min(1.0, alpha))
    if effective_alpha > 0.0:
        client = GeminiClient(timeout=15.0)
        try:
            vecs = await client.get_embeddings([expanded_query[:4000]], task_type="RETRIEVAL_QUERY")
            if vecs and len(vecs[0]) == 1536:
                query_vec_str = "[" + ",".join(f"{x:.6f}" for x in vecs[0]) + "]"
        except Exception as exc:
            logger.warning("Query embedding failed, falling back to sparse FTS only: %s", exc)
            effective_alpha = 0.0
        finally:
            await client.aclose()

    ts_query = _build_or_tsquery(expanded_query)
    if not ts_query and not query_vec_str:
        return []

    where_clauses = ["t.status = 'in_force'"]
    params: Dict[str, Any] = {
        "limit": max(1, min(limit, 50)),
        "alpha": effective_alpha if query_vec_str else 0.0,
        "def_penalty": 1.0 if is_definition_query else 0.80,
    }

    if jurisdictions:
        where_clauses.append("t.jurisdiction = ANY(:jurisdictions)")
        params["jurisdictions"] = [j.upper() for j in jurisdictions]
    if text_codes:
        where_clauses.append("t.code = ANY(:text_codes)")
        params["text_codes"] = list(text_codes)
    if has_sanction is not None:
        where_clauses.append("a.has_sanction = :has_sanction")
        params["has_sanction"] = has_sanction

    if query_vec_str:
        dense_expr = "CASE WHEN a.embedding IS NOT NULL THEN GREATEST(0.0, 1.0 - (a.embedding <=> CAST(:qvec AS vector))) ELSE 0.0 END"
        params["qvec"] = query_vec_str
    else:
        dense_expr = "0.0"

    if ts_query:
        # Normalization flag 33 = 1 (divide by 1 + log(doc length)) | 32 (scale rank into [0, 1))
        bm25_expr = (
            "ts_rank_cd(to_tsvector('french', coalesce(a.title, '') || ' ' || a.article_number || ' ' || a.full_text), "
            "to_tsquery('french', :tsq), 33)"
        )
        params["tsq"] = ts_query
    else:
        bm25_expr = "0.0"

    # Require either an embedding or a non-zero FTS match so non-vectorized sparse misses don't pollute top results
    if query_vec_str and ts_query:
        where_clauses.append(
            "(a.embedding IS NOT NULL OR to_tsvector('french', coalesce(a.title, '') || ' ' || a.article_number || ' ' || a.full_text) @@ to_tsquery('french', :tsq))"
        )
    elif ts_query:
        where_clauses.append(
            "to_tsvector('french', coalesce(a.title, '') || ' ' || a.article_number || ' ' || a.full_text) @@ to_tsquery('french', :tsq)"
        )
    else:
        where_clauses.append("a.embedding IS NOT NULL")

    where_sql = " AND ".join(where_clauses)
    sql = text(
        f"""
        WITH scored AS (
            SELECT
                a.id AS article_id,
                a.text_id,
                t.code AS text_code,
                t.title AS text_title,
                t.jurisdiction,
                t.authority,
                coalesce(s.breadcrumb, '') AS section_breadcrumb,
                a.article_number,
                a.title,
                a.full_text,
                a.topics,
                a.actors,
                a.has_sanction,
                a.sanction_details,
                a.compliance_rule_type,
                ({dense_expr}) AS dense_score,
                ({bm25_expr}) AS bm25_score
            FROM legal_article a
            JOIN legal_text t ON t.id = a.text_id
            LEFT JOIN legal_section s ON s.id = a.section_id
            WHERE {where_sql}
        )
        SELECT
            *,
            ((:alpha * dense_score + (1.0 - :alpha) * bm25_score)
             * CASE WHEN compliance_rule_type = 'definition' THEN :def_penalty ELSE 1.0 END) AS final_score
        FROM scored
        ORDER BY final_score DESC, dense_score DESC, bm25_score DESC
        LIMIT :limit
        """
    )

    async with async_session_maker() as session:
        rows = (await session.execute(sql, params)).mappings().all()

    return [
        ArticleSearchResult(
            article_id=row["article_id"],
            text_id=row["text_id"],
            text_code=row["text_code"],
            text_title=row["text_title"],
            jurisdiction=row["jurisdiction"],
            authority=row["authority"],
            section_breadcrumb=row["section_breadcrumb"],
            article_number=row["article_number"],
            title=row["title"],
            full_text=row["full_text"],
            topics=list(row["topics"] or []),
            actors=list(row["actors"] or []),
            has_sanction=bool(row["has_sanction"]),
            sanction_details=row["sanction_details"],
            compliance_rule_type=row["compliance_rule_type"],
            dense_score=float(row["dense_score"] or 0.0),
            bm25_score=float(row["bm25_score"] or 0.0),
            score=float(row["final_score"] or 0.0),
        )
        for row in rows
    ]
