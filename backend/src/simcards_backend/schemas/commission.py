"""Commission and performance-related schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from simcards_backend.models import PeriodType


class CommissionRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    amount_per_sim: Decimal = Field(gt=0, decimal_places=2)
    effective_from: datetime
    effective_to: datetime | None = None


class CommissionRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    name: str
    amount_per_sim: Decimal
    effective_from: datetime
    effective_to: datetime | None
    created_by_id: int | None
    created_at: datetime


class TargetCreateRequest(BaseModel):
    branch_id: int
    period_type: PeriodType  # DAILY, WEEKLY, MONTHLY
    quantity: int = Field(gt=0)
    effective_from: datetime
    effective_to: datetime | None = None


class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    branch_id: int
    period_type: str
    quantity: int
    effective_from: datetime
    effective_to: datetime | None
    set_by_id: int | None
    created_at: datetime


class PerformanceSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    subject_type: str
    subject_id: int
    period_type: str
    period_start: str
    period_end: str
    target_quantity: int
    actual_sold_quantity: int
    percentage_achieved: str
    computed_at: datetime


class CommissionSummaryResponse(BaseModel):
    total_commission: str
    sales_count: int
    period_start: str | None
    period_end: str | None


class BranchSummaryResponse(BaseModel):
    branch_id: int
    branch_name: str
    total_sims: int
    sold_count: int
    unsold_count: int
    with_ba_count: int
    with_branch_count: int
    expired_count: int
