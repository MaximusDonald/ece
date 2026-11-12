"""Tests for Phase 7 Regulatory Sentinel & Alert Review endpoints."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from sqlmodel import delete, select

from app.core.database import async_engine, async_session_maker
from app.core.security import create_access_token
from app.main import app
from app.models.corpus import RegulatoryAlert, RegulatoryAlertStatus
from app.models.legal import AuditLog, LegalLevel, LegalSource, SourceCollectionRun, SourceStatus
from app.models.user import User, UserRole
from app.services.crawler import (
    LegalCrawlerEngine,
    RegulatorySentinel,
    classify_normative_candidate,
    compute_text_diff_summary,
)
from app.workers.source_collection import run_sentinel_check


def test_classify_normative_candidate_filtering():
    """R1.3 strict normative filter accepts laws/decrees/deliberations and rejects noise."""
    ok_decree, _ = classify_normative_candidate(
        "https://sgg.gouv.bj/documents/decret-2026-101-donnees.pdf",
        "Décret n° 2026-101 fixant les modalités de transfert des données",
    )
    ok_delib, _ = classify_normative_candidate(
        "https://service.apdp.bj/uploads/deliberation-2026-04-sanction.pdf",
        "Délibération n° 2026-04 portant sanction pécuniaire",
    )
    bad_form, reason_form = classify_normative_candidate(
        "https://service.apdp.bj/uploads/formulaire-declaration-dpo.docx",
        "Formulaire de déclaration de traitement",
    )
    bad_speech, reason_speech = classify_normative_candidate(
        "https://www.ecowas.int/news/discours-ouverture-sommet.pdf",
        "Discours du Président à l'occasion du sommet annuel",
    )
    bad_report, _ = classify_normative_candidate(
        "https://service.apdp.bj/uploads/rapport-annuel-activites-2025.pdf",
        "Rapport annuel d'activités 2025",
    )

    assert ok_decree is True
    assert ok_delib is True
    assert bad_form is False and reason_form
    assert bad_speech is False and reason_speech
    assert bad_report is False


@pytest.mark.asyncio
async def test_blind_crawler_engine_is_retired():
    """Legacy blind spider crawl() is retired and returns no documents."""
    engine = LegalCrawlerEngine("https://service.apdp.bj/documentation", max_depth=2)
    docs = await engine.crawl()
    assert docs == []


@pytest.mark.asyncio
async def test_regulatory_sentinel_etag_304_and_diff():
    """RegulatorySentinel detects new normative links, honors 304 Not Modified, and diffs changes."""
    html_v1 = """
    <html><body>
      <h1>Délibérations APDP</h1>
      <a href="/docs/deliberation-2026-01.pdf">Délibération n° 2026-01 portant avertissement</a>
      <a href="/docs/formulaire-demande.pdf">Formulaire de demande d'avis</a>
      <a href="/docs/communique-presse.pdf">Communiqué de presse forum</a>
    </body></html>
    """
    html_v2 = """
    <html><body>
      <h1>Délibérations APDP</h1>
      <a href="/docs/deliberation-2026-01.pdf">Délibération n° 2026-01 portant avertissement</a>
      <a href="/docs/decret-2026-99-cyber.pdf">Décret n° 2026-99 sur la cybersécurité</a>
      <a href="/docs/formulaire-demande.pdf">Formulaire de demande d'avis</a>
    </body></html>
    """
    state = {"phase": 1}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["phase"] == 1:
            return httpx.Response(
                200,
                text=html_v1,
                headers={"ETag": '"v1-etag"', "Last-Modified": "Wed, 11 Nov 2026 10:00:00 GMT"},
            )
        if state["phase"] == 2:
            assert request.headers.get("If-None-Match") == '"v1-etag"'
            return httpx.Response(304)
        return httpx.Response(
            200,
            text=html_v2,
            headers={"ETag": '"v2-etag"', "Last-Modified": "Thu, 12 Nov 2026 10:00:00 GMT"},
        )

    sentinel = RegulatorySentinel("https://service.apdp.bj/documentation")
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        # 1. Initial check -> detects normative candidate only (filters out formulaire & communiqué)
        res1 = await sentinel.check_for_updates(client=client)
        assert res1.changed is True
        assert res1.status_code == 200
        assert res1.etag == '"v1-etag"'
        urls_1 = [c.url for c in res1.candidates]
        assert "https://service.apdp.bj/docs/deliberation-2026-01.pdf" in urls_1
        assert all("formulaire" not in u and "communique" not in u for u in urls_1)

        # 2. HTTP 304 Not Modified -> unchanged
        state["phase"] = 2
        res2 = await sentinel.check_for_updates(
            client=client,
            previous_etag=res1.etag,
            previous_last_modified=res1.last_modified,
            previous_hash=res1.new_hash,
            previous_snapshot=res1.page_snapshot,
            known_urls=set(urls_1),
        )
        assert res2.changed is False
        assert res2.status_code == 304

        # 3. Updated page with new decree -> changed + unified diff + new candidate only
        state["phase"] = 3
        res3 = await sentinel.check_for_updates(
            client=client,
            previous_etag=res1.etag,
            previous_last_modified=res1.last_modified,
            previous_hash=res1.new_hash,
            previous_snapshot=res1.page_snapshot,
            known_urls=set(urls_1),
        )
        assert res3.changed is True
        assert res3.etag == '"v2-etag"'
        assert any("decret-2026-99-cyber.pdf" in c.url for c in res3.candidates)
        assert "Décret n° 2026-99" in res3.change_summary or "decret-2026-99" in compute_text_diff_summary(
            res1.page_snapshot, res3.page_snapshot
        ).lower() or "+" in res3.change_summary


async def _get_admin_token() -> str:
    async with async_session_maker() as session:
        admin = (
            await session.execute(
                select(User).where(User.is_active.is_(True), User.role == UserRole.PLATFORM_ADMIN)
            )
        ).scalars().first()
        if not admin:
            admin = (
                await session.execute(select(User).where(User.is_active.is_(True)))
            ).scalars().first()
        assert admin is not None, "Expected at least one active user in database"
        return create_access_token(data={"sub": str(admin.id), "role": admin.role.value})


@pytest.mark.asyncio(loop_scope="module")
async def test_sentinel_worker_and_alert_review_workflow():
    """run_sentinel_check creates pending_review alerts and admin endpoints approve/dismiss them cleanly."""
    await async_engine.dispose()
    token = await _get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    source_id = uuid4()
    run_id = uuid4()
    created_alert_ids: list = []

    html_payload = """
    <html><body>
      <h2>Nouvelles publications normatives</h2>
      <a href="/actes/arrete-2026-12-dpo.pdf">Arrêté n° 2026-12 relatif à la certification DPO</a>
      <a href="/actes/decret-2026-15-securite.pdf">Décret n° 2026-15 sur la sécurité des systèmes</a>
    </body></html>
    """

    class _MockSentinel(RegulatorySentinel):
        async def check_for_updates(self, **kwargs):
            transport = httpx.MockTransport(
                lambda req: httpx.Response(
                    200,
                    text=html_payload,
                    headers={"ETag": '"test-sentinel-etag"'},
                )
            )
            async with httpx.AsyncClient(transport=transport) as client:
                return await super().check_for_updates(client=client, **kwargs)

    try:
        async with async_session_maker() as session:
            session.add(
                LegalSource(
                    id=source_id,
                    title="Test Watch Feed Sentinel",
                    authority="APDP Test",
                    country_code="BJ",
                    level=LegalLevel.DECISION,
                    article_ref=f"VEILLE-TEST-{str(source_id)[:8]}",
                    url_official="https://service.apdp.bj/test-watch",
                    content_hash="0" * 64,
                    content_text="",
                    embedding=[0.0] * 1536,
                    status=SourceStatus.VERIFIED,
                    is_portal=True,
                    collection_enabled=True,
                )
            )
            session.add(
                SourceCollectionRun(
                    id=run_id,
                    source_id=source_id,
                    status="running",
                )
            )
            await session.commit()

        created_count = await run_sentinel_check(
            run_id,
            source_id,
            session_factory=async_session_maker,
            sentinel_override=_MockSentinel("https://service.apdp.bj/test-watch"),
        )
        assert created_count == 2

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            res_list = await client.get(
                "/api/admin/alerts",
                params={"source_id": str(source_id), "status": "pending_review"},
                headers=headers,
            )
            assert res_list.status_code == 200
            alerts = res_list.json()
            assert len(alerts) == 2
            created_alert_ids = [a["id"] for a in alerts]
            assert all(a["status"] == RegulatoryAlertStatus.PENDING_REVIEW.value for a in alerts)

            # Approve first alert
            res_approve = await client.post(
                f"/api/admin/alerts/{alerts[0]['id']}/review",
                json={"action": "approve", "note": "Validé pour ingestion Phase 3"},
                headers=headers,
            )
            assert res_approve.status_code == 200
            assert res_approve.json()["status"] == RegulatoryAlertStatus.APPROVED.value
            assert res_approve.json()["review_note"] == "Validé pour ingestion Phase 3"

            # Dismiss second alert
            res_dismiss = await client.post(
                f"/api/admin/alerts/{alerts[1]['id']}/review",
                json={"action": "dismiss", "note": "Doublon hors périmètre"},
                headers=headers,
            )
            assert res_dismiss.status_code == 200
            assert res_dismiss.json()["status"] == RegulatoryAlertStatus.DISMISSED.value
    finally:
        async with async_session_maker() as session:
            if created_alert_ids:
                await session.execute(
                    delete(AuditLog).where(
                        AuditLog.entity_type == "regulatory_alert",
                        AuditLog.entity_id.in_(created_alert_ids),
                    )
                )
            await session.execute(
                delete(AuditLog).where(
                    AuditLog.entity_type == "legal_source",
                    AuditLog.entity_id == source_id,
                )
            )
            await session.execute(delete(RegulatoryAlert).where(RegulatoryAlert.source_id == source_id))
            await session.execute(delete(SourceCollectionRun).where(SourceCollectionRun.source_id == source_id))
            await session.execute(delete(LegalSource).where(LegalSource.id == source_id))
            await session.commit()
