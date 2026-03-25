from celery import Celery
from celery.schedules import crontab
from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sre",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "fetch-new-papers-daily": {
            "task": "workers.tasks.fetch_new_papers",
            "schedule": crontab(hour=2, minute=0),
        },
        "rebuild-faiss-index": {
            "task": "workers.tasks.rebuild_faiss_index",
            "schedule": crontab(hour=3, minute=0),
        },
        "compute-gap-detection": {
            "task": "workers.tasks.compute_research_gaps",
            "schedule": crontab(hour=4, minute=0),
        },
    },
)
