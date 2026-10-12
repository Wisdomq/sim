"""Reconciliation tasks for matching internal sales with Safaricom data."""

from __future__ import annotations

from datetime import datetime

from simcards_backend.celery_app import celery_app
from simcards_backend.core.database import SessionLocal, set_tenant_context
from simcards_backend.models import SafaricomImport, SafaricomImportStatus
from simcards_backend.services.reconciliation import reconcile_safaricom_import
from simcards_backend.tasks.xlsx_parser import parse_safaricom_report_file


@celery_app.task(bind=True)
def run_reconciliation(self, safaricom_import_id: int, as_of: str | None = None) -> dict:
    """
    Parse the uploaded Safaricom xlsx report and reconcile it against internal
    app sales (design §6.6, B-08-02/03/04/05).

    Args:
        safaricom_import_id: ID of the SafaricomImport record
        as_of: Optional ISO datetime for the generated_at timestamp (testing)

    Returns:
        Dict with the reconciliation outcome and SafaricomImport status
    """
    as_of_dt = datetime.fromisoformat(as_of) if as_of else None

    with SessionLocal() as db:
        safaricom_import = db.get(SafaricomImport, safaricom_import_id)
        if safaricom_import is None:
            return {"status": "failed", "message": "SafaricomImport not found."}
        set_tenant_context(db, safaricom_import.dealer_id)

        try:
            rows = parse_safaricom_report_file(safaricom_import.file_reference)
            reconcile_safaricom_import(
                db,
                safaricom_import=safaricom_import,
                rows=rows,
                as_of=as_of_dt,
            )
            safaricom_import.status = SafaricomImportStatus.COMPLETED
            safaricom_import.row_count = len(rows)
            db.commit()
            return {
                "status": "completed",
                "safaricom_import_id": safaricom_import_id,
                "row_count": len(rows),
            }
        except Exception as exc:
            db.rollback()
            safaricom_import = db.get(SafaricomImport, safaricom_import_id)
            if safaricom_import is not None:
                safaricom_import.status = SafaricomImportStatus.FAILED
                db.commit()
            return {"status": "failed", "message": str(exc)}