"""Reporting and export routes (Phase 9, FR-RPT-01/02/03, B-09-01/02/03)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from simcards_backend.api.dependencies import get_current_user, require_hq_or_branch
from simcards_backend.core.config import settings
from simcards_backend.core.database import get_db
from simcards_backend.models import User
from simcards_backend.schemas.reports import (
    ReportExportRequest,
    ReportExportResponse,
    ReportRequest,
    ReportResponse,
)
from simcards_backend.services.reports import generate_report, get_report_context
from simcards_backend.tasks.report_generation import generate_report_export

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportResponse)
def get_report(
    payload: ReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    """
    Generate and return report data for the specified period.

    Access: Branch (own data only), HQ (all branches or specific branch)
    """
    try:
        context = get_report_context(
            current_user,
            branch_filter=payload.branch_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    report_data = generate_report(
        db,
        context=context,
        period_type=payload.period_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )

    return ReportResponse(**report_data)


@router.post("/export", response_model=ReportExportResponse, status_code=status.HTTP_202_ACCEPTED)
def request_report_export(
    payload: ReportExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    """
    Request a report export (PDF or Excel) for the specified period.

    The export is generated asynchronously by a Celery worker; the response
    carries the task id and the destination file path. The finished file is
    discovered via ``GET /reports/list``.

    Access: Branch (own data only), HQ (all branches or specific branch)
    """
    # Validate export format
    export_format = payload.export_format.upper()
    if export_format not in ["PDF", "XLSX"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="export_format must be either PDF or XLSX",
        )

    try:
        context = get_report_context(
            current_user,
            branch_filter=payload.branch_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    # Determine file path and extension
    upload_dir = Path(settings.UPLOAD_DIR) / "reports" / str(current_user.dealer_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_extension = ".pdf" if export_format == "PDF" else ".xlsx"
    file_name = f"{payload.period_type}_{payload.period_start}_{payload.period_end}_{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / file_name

    # Dispatch the export to the background worker
    task = generate_report_export.delay(
        dealer_id=current_user.dealer_id,
        actor_user_id=current_user.id,
        branch_filter=context.branch_filter,
        period_type=payload.period_type,
        period_start=payload.period_start.isoformat(),
        period_end=payload.period_end.isoformat(),
        export_format=export_format,
        file_path=str(file_path),
    )

    return ReportExportResponse(
        task_id=task.id,
        export_format=export_format,
        file_reference=str(file_path),
        status="PROCESSING",
    )


@router.get("/download/{file_path:path}")
def download_report(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    """
    Download a previously generated report file.

    The file path must be within the dealer's report directory.
    """
    # Security check: ensure the file path is within the dealer's directory
    dealer_reports_dir = Path(settings.UPLOAD_DIR) / "reports" / str(current_user.dealer_id)
    requested_file = Path(file_path).resolve()

    # Ensure the requested file is within the dealer's reports directory
    try:
        requested_file.relative_to(dealer_reports_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this file is not authorized",
        )

    # Check if file exists
    if not requested_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    # Return the file
    from fastapi.responses import FileResponse

    return FileResponse(
        path=str(requested_file),
        filename=requested_file.name,
        media_type="application/pdf" if requested_file.suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/list")
def list_available_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    """
    List available report files for the current dealer.

    Returns metadata about available report files without downloading them.
    """
    dealer_reports_dir = Path(settings.UPLOAD_DIR) / "reports" / str(current_user.dealer_id)

    if not dealer_reports_dir.exists():
        return {"reports": []}

    reports = []
    for file_path in dealer_reports_dir.glob("*"):
        if file_path.is_file() and file_path.suffix in [".pdf", ".xlsx"]:
            reports.append({
                "filename": file_path.name,
                "file_path": str(file_path),
                "size_bytes": file_path.stat().st_size,
                "created_at": file_path.stat().st_ctime,
                "format": "PDF" if file_path.suffix == ".pdf" else "XLSX",
            })

    # Sort by creation time, newest first
    reports.sort(key=lambda x: x["created_at"], reverse=True)

    return {"reports": reports}
