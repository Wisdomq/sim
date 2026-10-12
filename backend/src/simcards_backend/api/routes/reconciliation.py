"""Safaricom import & reconciliation routes (Phase 8)."""

from __future__ import annotations

import shutil
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.api.dependencies import require_hq
from simcards_backend.core.config import settings
from simcards_backend.core.database import get_db
from simcards_backend.models import (
    ReconciliationLineDetail,
    ReconciliationMatchStatus,
    ReconciliationResult,
    SafaricomImport,
    SafaricomImportStatus,
    User,
)
from simcards_backend.schemas.reconciliation import (
    ReconciliationLineDetailResponse,
    ReconciliationResultResponse,
    SafaricomImportResponse,
    SafaricomImportUploadResponse,
)
from simcards_backend.services.audit import write_audit_log
from simcards_backend.services.reconciliation import list_activated_serials_for_month
from simcards_backend.tasks.reconciliation import run_reconciliation

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


def _get_import_for_dealer(db: Session, *, dealer_id: int, import_id: int) -> SafaricomImport:
    safaricom_import = db.scalar(
        select(SafaricomImport).where(
            SafaricomImport.dealer_id == dealer_id,
            SafaricomImport.id == import_id,
        )
    )
    if safaricom_import is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safaricom import not found.")
    return safaricom_import


@router.post("/imports", response_model=SafaricomImportUploadResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_safaricom_report(
    file: UploadFile = File(...),
    report_date: date = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Upload a Safaricom line-connection xlsx report and start reconciliation (FR-HQ-06)."""
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only .xlsx files are supported.",
        )

    upload_dir = Path(settings.UPLOAD_DIR) / "safaricom" / str(current_user.dealer_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix or ".xlsx"
    file_path = upload_dir / f"{uuid.uuid4()}{suffix}"
    with file_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    safaricom_import = SafaricomImport(
        dealer_id=current_user.dealer_id,
        uploaded_by_id=current_user.id,
        file_reference=str(file_path),
        report_date=report_date,
        status=SafaricomImportStatus.PROCESSING,
    )
    db.add(safaricom_import)
    db.flush()
    write_audit_log(
        db,
        dealer_id=current_user.dealer_id,
        actor_user_id=current_user.id,
        action="SAFARICOM_IMPORT_UPLOADED",
        entity_type="SafaricomImport",
        entity_id=safaricom_import.id,
        metadata={"file_reference": str(file_path), "report_date": report_date.isoformat()},
    )
    db.commit()
    db.refresh(safaricom_import)

    task = run_reconciliation.delay(safaricom_import.id)
    return SafaricomImportUploadResponse(
        import_id=safaricom_import.id,
        task_id=task.id,
        file_reference=str(file_path),
    )


@router.get("/activated", response_model=list[ReconciliationLineDetailResponse])
def get_activated_serials_by_month(
    month: str = Query(..., description="Calendar month in YYYY-MM format"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Serials activated in a calendar month across all imports, separated by activation
    month (FR-REC-06 / B-08-07). HQ only."""
    try:
        year, month_num = (int(part) for part in month.split("-"))
        month_start = date(year, month_num, 1)
        year_end = year + (1 if month_num == 12 else 0)
        month_end = date(year_end, 1 if month_num == 12 else month_num + 1, 1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="month must be in YYYY-MM format.",
        )

    rows = list_activated_serials_for_month(
        db,
        dealer_id=current_user.dealer_id,
        month_start=month_start,
        month_end=month_end,
    )
    return rows[offset : offset + limit]


@router.get("/imports", response_model=list[SafaricomImportResponse])
def list_safaricom_imports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """List Safaricom report imports for the dealer."""
    query = select(SafaricomImport).where(SafaricomImport.dealer_id == current_user.dealer_id)
    return list(db.scalars(query.order_by(SafaricomImport.uploaded_at.desc())))


@router.get("/imports/{import_id}", response_model=ReconciliationResultResponse)
def get_safaricom_import_summary(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Reconciliation headline numbers for an import (no per-serial detail, FR-REC-03)."""
    _get_import_for_dealer(db, dealer_id=current_user.dealer_id, import_id=import_id)
    result = db.scalar(
        select(ReconciliationResult).where(
            ReconciliationResult.safaricom_import_id == import_id,
            ReconciliationResult.dealer_id == current_user.dealer_id,
        )
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reconciliation has not completed for this import yet.",
        )
    return result


@router.get("/imports/{import_id}/detail", response_model=list[ReconciliationLineDetailResponse])
def get_safaricom_import_detail(
    import_id: int,
    match_status: ReconciliationMatchStatus | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Drill-down per-SIM reconciliation detail, exposed only via this endpoint (B-08-04)."""
    safaricom_import = _get_import_for_dealer(db, dealer_id=current_user.dealer_id, import_id=import_id)
    result = db.scalar(
        select(ReconciliationResult).where(
            ReconciliationResult.safaricom_import_id == safaricom_import.id,
            ReconciliationResult.dealer_id == current_user.dealer_id,
        )
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reconciliation has not completed for this import yet.",
        )

    query = select(ReconciliationLineDetail).where(
        ReconciliationLineDetail.reconciliation_result_id == result.id,
        ReconciliationLineDetail.dealer_id == current_user.dealer_id,
    )
    if match_status is not None:
        query = query.where(ReconciliationLineDetail.match_status == match_status)
    return list(db.scalars(query.order_by(ReconciliationLineDetail.id).limit(limit).offset(offset)))