"""Celery application configuration for background tasks."""

from celery import Celery

from simcards_backend.core.config import settings

# Create Celery app
celery_app = Celery(
    "simcards_backend",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "simcards_backend.tasks.inactivity",
        "simcards_backend.tasks.pdf_parser",
        "simcards_backend.tasks.xlsx_parser",
        "simcards_backend.tasks.reconciliation",
        "simcards_backend.tasks.report_generation",
        "simcards_backend.tasks.stock",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        "expire-unsold-sim-cards-daily": {
            "task": "simcards_backend.tasks.stock.expire_unsold_sim_cards",
            "schedule": 60 * 60 * 24,
        },
        "flag-inactive-accounts-daily": {
            "task": "simcards_backend.tasks.inactivity.flag_inactive_accounts_scheduled",
            "schedule": 60 * 60 * 24,
        },
    },
)
