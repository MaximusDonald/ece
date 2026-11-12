"""Read & explore endpoints for the hierarchical Master Legal Corpus (Codes -> Sections -> Articles)."""

from __future__ import annotations

import io
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import get_current_active_user
from app.models.corpus import ComplianceRuleType, LegalArticle, LegalSection, LegalText
from app.models.user import User
from app.schemas.corpus import (
    CorpusArticleDetail,
    CorpusArticlePage,
    CorpusSectionNode,
    CorpusSummary,
    LegalTextRead,
)
from app.services.article_rag import hybrid_search_articles
from app.services.minio_client import download_file, get_minio_client

router = APIRouter(prefix="/corpus", tags=["corpus"])


def _collect_descendant_section_ids(
    sections: List[LegalSection],
    root_section_id: UUID,
) -> Set[UUID]:
    """Return root_section_id plus all nested child section IDs within the same text."""
    children_map: Dict[Optional[UUID], List[UUID]] = {}
    for sec in sections:
        children_map.setdefault(sec.parent_section_id, []).append(sec.id)

    collected: Set[UUID] = set()
    stack = [root_section_id]
    while stack:
        current = stack.pop()
        if current in collected:
            continue
        collected.add(current)
        stack.extend(children_map.get(current, []))
    return collected


def _build_article_detail(
    art: LegalArticle,
    text_obj: LegalText,
    section_obj: Optional[LegalSection],
    *,
    prev_article_id: Optional[UUID] = None,
    next_article_id: Optional[UUID] = None,
    score: Optional[float] = None,
) -> CorpusArticleDetail:
    return CorpusArticleDetail(
        id=art.id,
        text_id=art.text_id,
        section_id=art.section_id,
        article_number=art.article_number,
        order_index=art.order_index,
        title=art.title,
        full_text=art.full_text,
        topics=list(art.topics or []),
        actors=list(art.actors or []),
        has_sanction=bool(art.has_sanction),
        sanction_details=art.sanction_details,
        compliance_rule_type=art.compliance_rule_type,
        ai_tagged=bool(art.ai_tagged),
        created_at=art.created_at,
        updated_at=art.updated_at,
        text_code=text_obj.code,
        text_title=text_obj.title,
        jurisdiction=text_obj.jurisdiction,
        authority=text_obj.authority,
        section_breadcrumb=section_obj.breadcrumb if section_obj else "",
        official_url=text_obj.official_url,
        prev_article_id=prev_article_id,
        next_article_id=next_article_id,
        score=score,
    )


@router.get("/summary", response_model=CorpusSummary)
async def get_corpus_summary(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return high-level counts of the sovereign Master Legal Corpus."""
    total_texts = (await session.execute(select(func.count(LegalText.id)))).scalar_one()
    total_sections = (await session.execute(select(func.count(LegalSection.id)))).scalar_one()
    total_articles = (await session.execute(select(func.count(LegalArticle.id)))).scalar_one()
    sanctioned_articles = (
        await session.execute(
            select(func.count(LegalArticle.id)).where(LegalArticle.has_sanction.is_(True))
        )
    ).scalar_one()
    ai_tagged_articles = (
        await session.execute(
            select(func.count(LegalArticle.id)).where(LegalArticle.ai_tagged.is_(True))
        )
    ).scalar_one()
    jur_rows = (
        await session.execute(
            select(LegalText.jurisdiction).distinct().order_by(LegalText.jurisdiction.asc())
        )
    ).all()
    return CorpusSummary(
        total_texts=total_texts,
        total_sections=total_sections,
        total_articles=total_articles,
        sanctioned_articles=sanctioned_articles,
        ai_tagged_articles=ai_tagged_articles,
        jurisdictions=[r[0] for r in jur_rows if r[0]],
    )


@router.get("/texts", response_model=List[LegalTextRead])
async def list_corpus_texts(
    jurisdiction: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List the Master Corpus legal texts ordered by jurisdiction and code."""
    stmt = select(LegalText)
    if jurisdiction and jurisdiction.strip().lower() not in ("all", ""):
        stmt = stmt.where(LegalText.jurisdiction == jurisdiction.strip().upper())
    stmt = stmt.order_by(LegalText.jurisdiction.asc(), LegalText.code.asc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.get("/texts/{text_id}/sections", response_model=List[CorpusSectionNode])
async def list_text_sections(
    text_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return hierarchical Table of Contents sections for one LegalText with article counts."""
    text_obj = await session.get(LegalText, text_id)
    if not text_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Texte juridique introuvable")

    sec_res = await session.execute(
        select(LegalSection)
        .where(LegalSection.text_id == text_id)
        .order_by(LegalSection.order_index.asc())
    )
    sections = list(sec_res.scalars().all())

    counts_res = await session.execute(
        select(LegalArticle.section_id, func.count(LegalArticle.id))
        .where(LegalArticle.text_id == text_id)
        .group_by(LegalArticle.section_id)
    )
    direct_counts: Dict[Optional[UUID], int] = {row[0]: row[1] for row in counts_res.all()}

    nodes: List[CorpusSectionNode] = []
    for sec in sections:
        desc_ids = _collect_descendant_section_ids(sections, sec.id)
        total_under = sum(direct_counts.get(sid, 0) for sid in desc_ids)
        node = CorpusSectionNode.model_validate(sec)
        node.article_count = total_under
        nodes.append(node)
    return nodes


@router.get("/articles", response_model=CorpusArticlePage)
async def list_corpus_articles(
    text_id: Optional[UUID] = Query(None),
    section_id: Optional[UUID] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    has_sanction: Optional[bool] = Query(None),
    compliance_rule_type: Optional[ComplianceRuleType] = Query(None),
    q: Optional[str] = Query(None),
    mode: str = Query("keyword", pattern="^(keyword|hybrid)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Browse or search statutory articles with hierarchical section & metadata filters."""
    clean_q = q.strip() if q else ""

    # Semantic + BM25 Hybrid Article-RAG mode when a natural-language query is supplied
    if mode == "hybrid" and clean_q:
        text_codes: Optional[List[str]] = None
        if text_id:
            t_obj = await session.get(LegalText, text_id)
            if t_obj:
                text_codes = [t_obj.code]
        jur_list = (
            [jurisdiction.strip().upper()]
            if jurisdiction and jurisdiction.strip().lower() not in ("all", "")
            else None
        )
        rag_hits = await hybrid_search_articles(
            clean_q,
            jurisdictions=jur_list,
            text_codes=text_codes,
            has_sanction=has_sanction,
            limit=min(limit + skip, 40),
        )
        hit_ids = [h.article_id for h in rag_hits]
        score_by_id = {h.article_id: h.score for h in rag_hits}
        if not hit_ids:
            return CorpusArticlePage(items=[], total=0, skip=skip, limit=limit, mode="hybrid")

        rows = (
            await session.execute(
                select(LegalArticle, LegalText, LegalSection)
                .join(LegalText, LegalArticle.text_id == LegalText.id)
                .outerjoin(LegalSection, LegalArticle.section_id == LegalSection.id)
                .where(LegalArticle.id.in_(hit_ids))
            )
        ).all()
        row_map = {art.id: (art, t, sec) for art, t, sec in rows}
        ordered_items: List[CorpusArticleDetail] = []
        for aid in hit_ids:
            pair = row_map.get(aid)
            if not pair:
                continue
            art, t, sec = pair
            if compliance_rule_type and art.compliance_rule_type != compliance_rule_type.value:
                continue
            ordered_items.append(_build_article_detail(art, t, sec, score=score_by_id.get(aid)))
        total = len(ordered_items)
        return CorpusArticlePage(
            items=ordered_items[skip : skip + limit],
            total=total,
            skip=skip,
            limit=limit,
            mode="hybrid",
        )

    # Deterministic hierarchical + keyword browse mode
    filters = []
    if text_id:
        filters.append(LegalArticle.text_id == text_id)
    if section_id:
        target_sec = await session.get(LegalSection, section_id)
        if target_sec:
            sec_rows = (
                await session.execute(
                    select(LegalSection).where(LegalSection.text_id == target_sec.text_id)
                )
            ).scalars().all()
            allowed_sec_ids = _collect_descendant_section_ids(list(sec_rows), section_id)
            filters.append(LegalArticle.section_id.in_(allowed_sec_ids))
        else:
            filters.append(LegalArticle.section_id == section_id)
    if jurisdiction and jurisdiction.strip().lower() not in ("all", ""):
        filters.append(LegalText.jurisdiction == jurisdiction.strip().upper())
    if has_sanction is not None:
        filters.append(LegalArticle.has_sanction.is_(has_sanction))
    if compliance_rule_type:
        filters.append(LegalArticle.compliance_rule_type == compliance_rule_type.value)
    if clean_q:
        pattern = f"%{clean_q}%"
        filters.append(
            or_(
                LegalArticle.article_number.ilike(pattern),
                LegalArticle.title.ilike(pattern),
                LegalArticle.full_text.ilike(pattern),
                LegalArticle.sanction_details.ilike(pattern),
            )
        )

    count_stmt = (
        select(func.count(LegalArticle.id))
        .select_from(LegalArticle)
        .join(LegalText, LegalArticle.text_id == LegalText.id)
    )
    data_stmt = (
        select(LegalArticle, LegalText, LegalSection)
        .join(LegalText, LegalArticle.text_id == LegalText.id)
        .outerjoin(LegalSection, LegalArticle.section_id == LegalSection.id)
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
        data_stmt = data_stmt.where(*filters)

    total = (await session.execute(count_stmt)).scalar_one()
    data_stmt = (
        data_stmt.order_by(LegalText.code.asc(), LegalArticle.order_index.asc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await session.execute(data_stmt)).all()
    items = [_build_article_detail(art, t, sec) for art, t, sec in rows]

    return CorpusArticlePage(items=items, total=total, skip=skip, limit=limit, mode="keyword")


@router.get("/articles/{article_id}", response_model=CorpusArticleDetail)
async def get_corpus_article(
    article_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Fetch full official verbatim details of a single LegalArticle with prev/next pointers."""
    row = (
        await session.execute(
            select(LegalArticle, LegalText, LegalSection)
            .join(LegalText, LegalArticle.text_id == LegalText.id)
            .outerjoin(LegalSection, LegalArticle.section_id == LegalSection.id)
            .where(LegalArticle.id == article_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")

    art, text_obj, section_obj = row

    prev_id = (
        await session.execute(
            select(LegalArticle.id)
            .where(
                LegalArticle.text_id == art.text_id,
                LegalArticle.order_index < art.order_index,
            )
            .order_by(LegalArticle.order_index.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    next_id = (
        await session.execute(
            select(LegalArticle.id)
            .where(
                LegalArticle.text_id == art.text_id,
                LegalArticle.order_index > art.order_index,
            )
            .order_by(LegalArticle.order_index.asc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return _build_article_detail(
        art,
        text_obj,
        section_obj,
        prev_article_id=prev_id,
        next_article_id=next_id,
    )


@router.get("/texts/{text_id}/pdf")
async def download_corpus_pdf(
    text_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Stream the official archived PDF for a Master Corpus LegalText from MinIO."""
    text_obj = await session.get(LegalText, text_id)
    if not text_obj or not text_obj.pdf_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF officiel introuvable")

    minio_client = get_minio_client()
    try:
        pdf_bytes = download_file(minio_client, text_obj.minio_bucket, text_obj.pdf_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Impossible de récupérer le fichier PDF ({exc})",
        ) from exc

    filename = f"{text_obj.code}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
