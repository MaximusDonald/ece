"""Tests for the project-level compliance audit synchronization barrier."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.database import async_engine, async_session_maker
from app.models.document import Document, DocumentAnalysis, DocumentExtraction, DocumentStatus
from app.models.legal import ReportVersion
from app.models.user import Organization, Project
from app.services.compliance_auditor import (
    AuditExecutionResult,
    ProjectDossier,
    get_project_analysis_readiness,
)
from app.workers import legal_research, pipeline_tracker, semantic, task_dispatch


class FakeRedisClient:
    """Minimal Redis stub supporting get/set/delete/expire/eval for worker tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.store:
            return False
        self.store[key] = str(value)
        return True

    def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    def expire(self, key: str, ttl: int) -> bool:
        return key in self.store

    def eval(self, script: str, numkeys: int, key: str, claim: str) -> int:
        if self.store.get(key) == claim:
            del self.store[key]
            return 1
        return 0


class StubSemanticLLM:
    async def chat_completion(self, prompt: str, response_format: str | None = None, **kwargs) -> str:
        if "entités" in prompt.lower() or "extraction" in prompt.lower():
            return json.dumps({"entities": [{"text": "CNIL", "label": "ORG"}]})
        return json.dumps({"vague_zones": [{"text": "durée raisonnable", "reason": "Imprécis"}]})


@pytest.mark.asyncio(loop_scope="module")
async def test_barrier_waits_for_all_non_failed_documents():
    await async_engine.dispose()
    async with async_session_maker() as session:
        org = Organization(name=f"Barrier Org {uuid4().hex[:6]}")
        session.add(org)
        await session.flush()

        project = Project(
            org_id=org.id,
            name="Projet Multi-Docs",
            country_code="BJ",
            sector="Finance",
        )
        session.add(project)
        await session.flush()

        doc1 = Document(
            project_id=project.id,
            filename="doc1.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            minio_bucket="documents",
            minio_object=f"test/{uuid4()}.pdf",
            status=DocumentStatus.EXTRACTED,
        )
        doc2 = Document(
            project_id=project.id,
            filename="doc2.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            minio_bucket="documents",
            minio_object=f"test/{uuid4()}.pdf",
            status=DocumentStatus.EXTRACTING,
        )
        doc3_failed = Document(
            project_id=project.id,
            filename="doc3_corrupt.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            minio_bucket="documents",
            minio_object=f"test/{uuid4()}.pdf",
            status=DocumentStatus.FAILED,
        )
        session.add_all([doc1, doc2, doc3_failed])
        await session.flush()

        ext1 = DocumentExtraction(document_id=doc1.id, markdown="# Doc 1")
        session.add(ext1)
        await session.flush()
        session.add(DocumentAnalysis(extraction_id=ext1.id, entities=[], vague_zones=[]))
        await session.commit()

        ready, pending = await get_project_analysis_readiness(session, project.id)
        assert ready == [doc1.id]
        assert pending == [doc2.id]

        # Complete doc2 extraction + analysis -> barrier opens, failed doc3 does not block
        doc2.status = DocumentStatus.EXTRACTED
        ext2 = DocumentExtraction(document_id=doc2.id, markdown="# Doc 2")
        session.add(ext2)
        await session.flush()
        session.add(DocumentAnalysis(extraction_id=ext2.id, entities=[], vague_zones=[]))
        await session.commit()

        ready, pending = await get_project_analysis_readiness(session, project.id)
        assert set(ready) == {doc1.id, doc2.id}
        assert pending == []


@pytest.mark.asyncio(loop_scope="module")
async def test_semantic_and_legal_research_barrier_and_shared_report_propagation(monkeypatch):
    await async_engine.dispose()
    fake_redis = FakeRedisClient()
    monkeypatch.setattr(pipeline_tracker.celery_app.backend, "client", fake_redis)
    monkeypatch.setattr(task_dispatch.celery_app.backend, "client", fake_redis)
    monkeypatch.setattr(semantic, "SyncSession", async_session_maker)
    monkeypatch.setattr(legal_research, "SyncSession", async_session_maker)
    monkeypatch.setattr(semantic, "get_llm_client", lambda *a, **kw: StubSemanticLLM())

    queued_project_audits: list[tuple] = []
    queued_doc_tasks: list[tuple] = []

    def spy_project_audit(task, project_id, trigger_doc_id):
        queued_project_audits.append((task, project_id, trigger_doc_id))
        return "audit-task-1", True

    def spy_doc_task(task, target_id, stage):
        queued_doc_tasks.append((task, target_id, stage))
        return f"{stage}-task-1", True

    monkeypatch.setattr(semantic, "enqueue_project_audit_task", spy_project_audit)
    monkeypatch.setattr(legal_research, "enqueue_document_task", spy_doc_task)

    async def fake_holistic_audit(session, project_id, focus_document_id=None):
        return AuditExecutionResult(
            dossier=ProjectDossier(
                project_id=project_id,
                project_name="Projet Complet",
                country_code="SN",
                sector="Santé",
                project_treatments=[],
                documents=[],
            ),
            facets=[],
            articles_map={},
            findings=[],
            report1_markdown="# Rapport 1",
            report2_markdown="# Rapport 2",
        )

    monkeypatch.setattr(legal_research, "run_holistic_compliance_audit", fake_holistic_audit)

    async with async_session_maker() as session:
        org = Organization(name=f"Pipeline Org {uuid4().hex[:6]}")
        session.add(org)
        await session.flush()

        project = Project(
            org_id=org.id,
            name="Projet Complet",
            country_code="SN",
            sector="Santé",
        )
        session.add(project)
        await session.flush()

        doc1 = Document(
            project_id=project.id,
            filename="contrat.pdf",
            mime_type="application/pdf",
            size_bytes=120,
            minio_bucket="documents",
            minio_object=f"test/{uuid4()}.pdf",
            status=DocumentStatus.EXTRACTED,
        )
        doc2 = Document(
            project_id=project.id,
            filename="politique.pdf",
            mime_type="application/pdf",
            size_bytes=150,
            minio_bucket="documents",
            minio_object=f"test/{uuid4()}.pdf",
            status=DocumentStatus.EXTRACTING,
        )
        session.add_all([doc1, doc2])
        await session.flush()
        session.add(DocumentExtraction(document_id=doc1.id, markdown="# Contrat"))
        await session.commit()

        pipeline_tracker.start_step(doc1.id, 1, "Extraction")
        pipeline_tracker.start_step(doc2.id, 1, "Extraction")

    # 1. Doc1 finishes semantic while Doc2 is still extracting -> must wait, no audit queued
    await semantic.run_semantic_analysis(doc1.id)
    assert queued_project_audits == []
    doc1_state = pipeline_tracker.get_pipeline_state(doc1.id)
    assert doc1_state is not None
    assert doc1_state["steps"][2]["status"] == "running"
    assert "En attente" in doc1_state["steps"][2]["message"]

    # 2. Doc2 finishes extraction and semantic -> barrier opens, 1 project audit queued
    async with async_session_maker() as session:
        db_doc2 = await session.get(Document, doc2.id)
        assert db_doc2 is not None
        db_doc2.status = DocumentStatus.EXTRACTED
        session.add(DocumentExtraction(document_id=doc2.id, markdown="# Politique"))
        await session.commit()

    await semantic.run_semantic_analysis(doc2.id)
    assert len(queued_project_audits) == 1
    assert queued_project_audits[0][1] == project.id
    assert queued_project_audits[0][2] == doc2.id

    # 3. Legal research runs once from scratch and propagates report_version_id to both docs
    await legal_research.run_legal_research(doc2.id)

    async with async_session_maker() as session:
        reports = (
            await session.execute(select_reports_for_project(project.id))
        ).scalars().all()
        assert len(reports) == 1
        report_id = reports[0].id

    bound_docs = pipeline_tracker.get_documents_for_report(report_id)
    assert set(bound_docs) == {str(doc1.id), str(doc2.id)}

    for did in (doc1.id, doc2.id):
        state = pipeline_tracker.get_pipeline_state(did)
        assert state is not None
        assert state["report_version_id"] == str(report_id)
        assert state["steps"][2]["status"] == "completed"
        assert state["steps"][3]["status"] == "running"

    assert len(queued_doc_tasks) == 1
    assert queued_doc_tasks[0][1] == report_id
    assert queued_doc_tasks[0][2] == "scoring"


def select_reports_for_project(project_id):
    from sqlmodel import select

    return select(ReportVersion).where(ReportVersion.project_id == project_id)


def test_enqueue_project_audit_task_deduplicates_per_project(monkeypatch):
    fake_redis = FakeRedisClient()
    monkeypatch.setattr(task_dispatch.celery_app.backend, "client", fake_redis)
    monkeypatch.setattr(
        task_dispatch.celery_app,
        "AsyncResult",
        lambda task_id: SimpleNamespace(state="PENDING"),
    )

    calls: list[str] = []

    class DummyTask:
        def delay(self, arg: str):
            calls.append(arg)
            return SimpleNamespace(id=f"celery-{len(calls)}")

    project_id = uuid4()
    doc1_id = uuid4()
    doc2_id = uuid4()

    task_id_1, created_1 = task_dispatch.enqueue_project_audit_task(DummyTask(), project_id, doc1_id)
    task_id_2, created_2 = task_dispatch.enqueue_project_audit_task(DummyTask(), project_id, doc2_id)

    assert created_1 is True
    assert created_2 is False
    assert task_id_1 == task_id_2 == "celery-1"
    assert calls == [str(doc1_id)]
