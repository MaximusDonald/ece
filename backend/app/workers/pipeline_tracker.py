"""Redis-backed, document-level progress for the asynchronous audit pipeline."""

import json
from datetime import datetime, timezone
from uuid import UUID

from app.workers.celery_app import celery_app


PIPELINE_TTL_SECONDS = 60 * 60 * 24 * 30
STAGES = [
    (1, "extraction", "Extraction du document"),
    (2, "semantic", "Analyse du contenu"),
    (3, "legal_research", "Recherche dans le corpus juridique"),
    (4, "scoring", "Évaluation des risques"),
    (5, "report", "Préparation des rapports"),
]


def _key(document_id: UUID | str) -> str:
    return f"ece:document-pipeline:{document_id}"


def _read(document_id: UUID | str) -> dict | None:
    value = celery_app.backend.client.get(_key(document_id))
    if not value:
        return None
    return json.loads(value)


def get_pipeline_state(document_id: UUID | str) -> dict | None:
    return _read(document_id)


def bind_report(document_id: UUID | str, report_version_id: UUID | str) -> None:
    client = celery_app.backend.client
    client.set(
        f"ece:report-document:{report_version_id}",
        str(document_id),
        ex=PIPELINE_TTL_SECONDS,
    )
    state = _read(document_id)
    if state:
        state["report_version_id"] = str(report_version_id)
        _write(document_id, state)


def get_document_for_report(report_version_id: UUID | str) -> str | None:
    value = celery_app.backend.client.get(f"ece:report-document:{report_version_id}")
    if isinstance(value, bytes):
        return value.decode()
    return str(value) if value else None


def _write(document_id: UUID | str, state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    celery_app.backend.client.set(
        _key(document_id), json.dumps(state), ex=PIPELINE_TTL_SECONDS
    )


def initialize_pipeline(document_id: UUID | str, filename: str) -> None:
    state = {
        "document_id": str(document_id),
        "filename": filename,
        "status": "queued",
        "current_step": 1,
        "progress": 0,
        "steps": [
            {"step": n, "key": key, "label": label, "status": "pending", "message": "En attente"}
            for n, key, label in STAGES
        ],
        "error": None,
        "warnings": [],
        "report_version_id": None,
    }
    _write(document_id, state)


def start_step(document_id: UUID | str, step_number: int, message: str | None = None) -> None:
    state = _read(document_id) or {
        "document_id": str(document_id), "status": "queued", "progress": 0,
        "steps": [
            {"step": n, "key": key, "label": label, "status": "pending", "message": "En attente"}
            for n, key, label in STAGES
        ], "warnings": [], "error": None, "report_version_id": None,
    }
    state["status"] = "running"
    state["current_step"] = step_number
    state["error"] = None
    step = next(item for item in state["steps"] if item["step"] == step_number)
    step.update(status="running", message=message or "Traitement en cours")
    _write(document_id, state)


def complete_step(
    document_id: UUID | str,
    step_number: int,
    message: str = "Étape terminée",
    report_version_id: UUID | str | None = None,
) -> None:
    state = _read(document_id)
    if not state:
        start_step(document_id, step_number)
        state = _read(document_id)
    step = next(item for item in state["steps"] if item["step"] == step_number)
    step.update(status="completed", message=message)
    state["progress"] = round(step_number * 100 / len(STAGES))
    state["report_version_id"] = str(report_version_id) if report_version_id else state.get("report_version_id")
    if step_number == len(STAGES):
        state["status"] = "completed"
        state["current_step"] = None
        state["progress"] = 100
        state["error"] = None
    else:
        state["current_step"] = step_number + 1
        state["status"] = "running"
    _write(document_id, state)


def fail_step(document_id: UUID | str, step_number: int, retrying: bool = False) -> None:
    state = _read(document_id)
    if not state:
        start_step(document_id, step_number)
        state = _read(document_id)
    step = next(item for item in state["steps"] if item["step"] == step_number)
    if retrying:
        step.update(status="retrying", message="Nouvelle tentative automatique")
        state["status"] = "running"
        state["error"] = None
    else:
        step.update(status="failed", message="Cette étape n’a pas abouti")
        state["status"] = "failed"
        state["error"] = f"{step['label']} a échoué. Vous pouvez relancer cette étape."
    state["current_step"] = step_number
    _write(document_id, state)


def add_warning(document_id: UUID | str, warning: str) -> None:
    state = _read(document_id)
    if not state:
        return
    warnings = state.setdefault("warnings", [])
    if warning not in warnings:
        warnings.append(warning)
    _write(document_id, state)
