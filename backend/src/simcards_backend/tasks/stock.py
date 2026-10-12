"""Scheduled stock maintenance tasks."""

from __future__ import annotations

from datetime import date

from simcards_backend.celery_app import celery_app
from simcards_backend.core.database import SessionLocal
from simcards_backend.services.stock import mark_expired_sim_cards


@celery_app.task(bind=True)
def expire_unsold_sim_cards(self, as_of: str | None = None) -> dict:
    effective_date = date.fromisoformat(as_of) if as_of else date.today()
    with SessionLocal() as db:
        expired_count = mark_expired_sim_cards(db, as_of=effective_date)
    return {"status": "completed", "expired_count": expired_count, "as_of": effective_date.isoformat()}
