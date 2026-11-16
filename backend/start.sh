#!/bin/sh
set -e

python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db())"
alembic upgrade head
python -m app.scripts.ingest_master_corpus --codes BJ-NUM-2017

if [ "${RUN_CELERY_IN_PROCESS:-false}" = "true" ]; then
  celery -A app.workers.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-1}" &
  if [ "${RUN_CELERY_BEAT:-true}" = "true" ]; then
    celery -A app.workers.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule &
  fi
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}" --proxy-headers --forwarded-allow-ips="*"
