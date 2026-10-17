"""Small Redis-backed deduplication for document pipeline tasks."""

from uuid import UUID, uuid4

from app.workers.celery_app import celery_app


LOCK_TTL_SECONDS = 300


def enqueue_document_task(task, document_id: UUID, stage: str) -> tuple[str, bool]:
    """Queue a task once while its Celery result is pending or active."""
    client = celery_app.backend.client
    key = f"ece:document-task:{stage}:{document_id}"
    current = client.get(key)

    if current:
        current_id = current.decode() if isinstance(current, bytes) else str(current)
        state = celery_app.AsyncResult(current_id).state
        if state in {"PENDING", "RETRY"}:
            return current_id, False
        if state == "STARTED":
            active = celery_app.control.inspect(timeout=1).active() or {}
            if any(
                request.get("id") == current_id
                for requests in active.values()
                for request in requests
            ):
                client.expire(key, LOCK_TTL_SECONDS)
                return current_id, False
        client.delete(key)

    claim = str(uuid4())
    if not client.set(key, claim, nx=True, ex=30):
        return "", False

    try:
        result = task.delay(str(document_id))
        client.set(key, result.id, ex=LOCK_TTL_SECONDS)
        return result.id, True
    except Exception:
        # Delete only our short-lived claim; do not remove another request's task ID.
        client.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
            1,
            key,
            claim,
        )
        raise
