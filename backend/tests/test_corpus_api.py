"""Tests for Phase 6 /api/corpus hierarchical explorer endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import async_engine, async_session_maker
from app.core.security import create_access_token
from app.main import app
from app.models.user import User


async def _get_or_create_test_token() -> str:
    """Mint a valid bearer token for an active user without altering existing accounts."""
    from uuid import uuid4
    from sqlmodel import select

    async with async_session_maker() as session:
        user = (await session.execute(select(User).where(User.is_active.is_(True)))).scalars().first()
        if not user:
            from app.core.security import get_password_hash
            user = User(
                email=f"corpus_test_{uuid4().hex[:8]}@example.org",
                hashed_password=get_password_hash("TestPass123!"),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return create_access_token(data={"sub": str(user.id), "role": user.role.value})


@pytest.mark.asyncio(loop_scope="module")
async def test_corpus_explorer_endpoints():
    await async_engine.dispose()
    token = await _get_or_create_test_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Summary
        res_sum = await client.get("/api/corpus/summary", headers=headers)
        assert res_sum.status_code == 200
        summary = res_sum.json()
        assert summary["total_texts"] == 10
        assert summary["total_articles"] == 2142
        assert summary["sanctioned_articles"] >= 170

        # 2. Texts list
        res_texts = await client.get("/api/corpus/texts", headers=headers)
        assert res_texts.status_code == 200
        texts = res_texts.json()
        bj_code = next(t for t in texts if t["code"] == "BJ-NUM-2017")
        assert bj_code["total_articles"] == 661

        # 3. Sections tree
        res_secs = await client.get(f"/api/corpus/texts/{bj_code['id']}/sections", headers=headers)
        assert res_secs.status_code == 200
        sections = res_secs.json()
        assert len(sections) > 20
        livre_v = next(
            s for s in sections
            if "livre" in s["level_name"].lower() and s["article_count"] > 50
        )
        assert livre_v["article_count"] > 50

        # 4. Descendant-aware section filtering + keyword search
        res_sec_arts = await client.get(
            "/api/corpus/articles",
            params={"text_id": bj_code["id"], "section_id": livre_v["id"], "limit": 5},
            headers=headers,
        )
        assert res_sec_arts.status_code == 200
        assert res_sec_arts.json()["total"] == livre_v["article_count"]

        res_arts = await client.get(
            "/api/corpus/articles",
            params={"text_id": bj_code["id"], "q": "391", "limit": 10},
            headers=headers,
        )
        assert res_arts.status_code == 200
        art_page = res_arts.json()
        assert art_page["total"] >= 1
        art_391 = next(a for a in art_page["items"] if a["article_number"] == "Article 391")

        # 5. Single article detail with prev/next navigation
        res_one = await client.get(f"/api/corpus/articles/{art_391['id']}", headers=headers)
        assert res_one.status_code == 200
        detail = res_one.json()
        assert detail["text_code"] == "BJ-NUM-2017"
        assert detail["prev_article_id"] is not None
        assert detail["next_article_id"] is not None

        # 6. Official PDF download from MinIO
        res_pdf = await client.get(f"/api/corpus/texts/{bj_code['id']}/pdf", headers=headers)
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"].startswith("application/pdf")
        assert len(res_pdf.content) > 10000

    await async_engine.dispose()
