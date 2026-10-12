"""Scheduled login-inactivity flagging task (design §6.10, B-07-01)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from simcards_backend.celery_app import celery_app
from simcards_backend.core.database import SessionLocal, set_tenant_context
from simcards_backend.models import Dealer
from simcards_backend.services.inactivity import default_cutoff, flag_inactive_accounts


@celery_app.task(bind=True)
def flag_inactive_accounts_scheduled(self, as_of: str | None = None) -> dict:
    """
    Daily job that flags Branch/BA accounts with no login for 3+ consecutive days.

    Args:
        as_of: Optional ISO datetime to run as (for testing); defaults to now.

    Returns:
        Dict with the number of freshly flagged accounts per dealer.
    """
    as_of_dt, cutoff_dt = default_cutoff(datetime.fromisoformat(as_of) if as_of else None)
    total_flagged = 0
    results: list[dict] = []

    with SessionLocal() as db:
        dealer_ids = db.scalars(select(Dealer.id).order_by(Dealer.id)).all()
        for dealer_id in dealer_ids:
            set_tenant_context(db, dealer_id)
            outcome = flag_inactive_accounts(
                db,
                dealer_id=dealer_id,
                cutoff_dt=cutoff_dt,
                as_of_dt=as_of_dt,
            )
            db.commit()
            total_flagged += outcome.freshly_flagged_count
            results.append(
                {
                    "dealer_id": dealer_id,
                    "flagged_count": outcome.freshly_flagged_count,
                    "already_flagged_count": outcome.already_flagged_count,
                }
            )

    return {
        "status": "completed",
        "as_of": as_of_dt.isoformat(),
        "total_flagged": total_flagged,
        "results": results,
    }