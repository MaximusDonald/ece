from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ece_workers",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.extraction",
        "app.workers.semantic",
        "app.workers.legal_research",
        "app.workers.scoring",
        "app.workers.report",
        "app.workers.incremental",
        "app.workers.source_collection",
    ],
    broker_connection_retry_on_startup = True
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    beat_schedule={
        "weekly-official-source-collection": {
            "task": "app.workers.source_collection.collect_enabled_sources",
            "schedule": crontab(day_of_week="mon", hour=2, minute=0),
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
