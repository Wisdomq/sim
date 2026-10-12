"""Safaricom import & reconciliation schemas (Phase 8)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from simcards_backend.models import ReconciliationMatchStatus, SafaricomImportStatus


class SafaricomImportUploadResponse(BaseModel):
    import_id: int
    task_id: str
    file_reference: str


class SafaricomImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    uploaded_by_id: int | None
    file_reference: str
    report_date: date
    uploaded_at: datetime
    row_count: int
    status: SafaricomImportStatus


class ReconciliationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    safaricom_import_id: int
    total_sold_in_app: int
    total_confirmed_activated_by_safaricom: int
    total_topped_up: int
    total_cumulative_commission: Decimal
    total_fraud_flagged: int
    unmatched_sold_not_in_safaricom_count: int
    unmatched_in_safaricom_not_sold_in_app_count: int
    generated_at: datetime


class ReconciliationLineDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reconciliation_result_id: int
    sim_card_id: int | None
    serial_number: str | None
    top_up_date: date | None
    top_up_amount: Decimal | None
    cumulative_commission: Decimal | None
    fraud_flagged: bool
    fraud_reason: str | None
    match_status: ReconciliationMatchStatus