"""Reporting and export schemas (Phase 9, FR-RPT-01/02/03)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

_ALLOWED_PERIOD_TYPES = {"DAILY", "WEEKLY", "MONTHLY"}


def _validate_period_type(value: str) -> str:
    normalized = value.upper()
    if normalized not in _ALLOWED_PERIOD_TYPES:
        raise ValueError("period_type must be one of: DAILY, WEEKLY, MONTHLY")
    return normalized


class ReportRequest(BaseModel):
    """Request model for generating reports."""

    period_type: str = Field(min_length=1, description="DAILY, WEEKLY, or MONTHLY")
    period_start: date = Field(description="Start date of the reporting period")
    period_end: date = Field(description="End date of the reporting period")
    branch_id: int | None = Field(default=None, description="Optional branch filter (HQ only)")

    @field_validator("period_type")
    @classmethod
    def _normalize_period_type(cls, value: str) -> str:
        return _validate_period_type(value)


class StockCountsByStatus(BaseModel):
    """Stock counts broken down by status."""

    in_hq_stock: int = 0
    with_branch: int = 0
    with_ba: int = 0
    sold: int = 0
    returned_to_branch: int = 0
    returned_to_hq: int = 0
    expired: int = 0


class BASalesSummary(BaseModel):
    """Sales summary for an individual BA."""

    ba_id: int
    ba_name: str
    sales_count: int
    commission_owed: Decimal
    performance_percentage: Decimal


class BranchReportData(BaseModel):
    """Report data for a single branch."""

    branch_id: int
    branch_name: str
    stock_counts: StockCountsByStatus
    total_sales_count: int
    total_commission_owed: Decimal
    performance_percentage: Decimal
    ba_summaries: list[BASalesSummary]


class ReconciliationHeadlines(BaseModel):
    """Reconciliation headline numbers to include in reports (FR-RPT-03)."""

    total_confirmed_activated_by_safaricom: int = 0
    total_cumulative_commission: Decimal = Decimal("0")
    total_fraud_flagged: int = 0
    unmatched_sold_not_in_safaricom_count: int = 0
    unmatched_in_safaricom_not_sold_in_app_count: int = 0


class ReportResponse(BaseModel):
    """Response model for report data (API view)."""

    period_type: str
    period_start: date
    period_end: date
    total_stock_counts: StockCountsByStatus
    total_sales_count: int
    total_commission_owed: Decimal
    overall_performance_percentage: Decimal
    branch_reports: list[BranchReportData]
    reconciliation_headlines: ReconciliationHeadlines | None = None
    generated_at: str


class ReportExportRequest(BaseModel):
    """Request model for exporting reports."""

    period_type: str = Field(min_length=1, description="DAILY, WEEKLY, or MONTHLY")
    period_start: date = Field(description="Start date of the reporting period")
    period_end: date = Field(description="End date of the reporting period")
    branch_id: int | None = Field(default=None, description="Optional branch filter (HQ only)")
    export_format: str = Field(description="PDF or XLSX")

    @field_validator("period_type")
    @classmethod
    def _normalize_period_type(cls, value: str) -> str:
        return _validate_period_type(value)


class ReportExportResponse(BaseModel):
    """Response model for report export requests."""

    task_id: str
    export_format: str
    file_reference: str | None = None
    status: str = "PROCESSING"
