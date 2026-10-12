"""Stock intake, transfer, return, and listing schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from simcards_backend.models import ReturnStatus, SimStatus, StockBatchSource


class StockBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    source: StockBatchSource
    source_reference: str
    quantity: int
    imported_by_id: int | None
    imported_at: datetime


class SimCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    serial_number: str
    stock_batch_id: int
    status: SimStatus
    current_branch_id: int | None
    current_ba_id: int | None
    expiry_date: date | None
    created_at: datetime
    updated_at: datetime


class StockIntakeResult(BaseModel):
    batch_id: int
    source_reference: str
    inserted_count: int
    duplicate_count: int
    duplicates: list[str] = []


class BoxScanIntakeRequest(BaseModel):
    box_barcode: str = Field(min_length=1, max_length=255)
    serials: list[str] | None = None
    first_serial: str | None = None
    quantity: int = Field(default=100, ge=1, le=100)
    expiry_date: date | None = None

    @model_validator(mode="after")
    def require_serial_source(self) -> "BoxScanIntakeRequest":
        if not self.serials and not self.first_serial:
            raise ValueError("Provide either serials or first_serial for the 100-SIM box mapping.")
        return self


class PickListUploadResponse(BaseModel):
    task_id: str
    file_reference: str


class DistributeStockRequest(BaseModel):
    branch_id: int
    quantity: int | None = Field(default=None, ge=1)
    serial_numbers: list[str] | None = None

    @model_validator(mode="after")
    def require_quantity_or_serials(self) -> "DistributeStockRequest":
        if bool(self.quantity) == bool(self.serial_numbers):
            raise ValueError("Provide either quantity or serial_numbers, but not both.")
        return self


class AssignToBrandAmbassadorRequest(BaseModel):
    ba_id: int
    serial_numbers: list[str] = Field(min_length=1)


class ReturnToBranchRequest(BaseModel):
    serial_numbers: list[str] = Field(min_length=1)
    reason: str | None = None


class RequestReturnRequest(BaseModel):
    branch_id: int
    serial_numbers: list[str] = Field(min_length=1)
    reason: str | None = None


class ReturnEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    sim_card_id: int
    requested_by_id: int | None
    branch_id: int
    return_date: datetime
    reason: str | None
    status: ReturnStatus


class BulkActionResponse(BaseModel):
    processed_count: int
    serial_numbers: list[str]


class SaleRequest(BaseModel):
    serial_number: str = Field(min_length=1, max_length=64)
    sold_at: datetime
    client_event_id: str | None = Field(default=None, max_length=64)


class SyncRequest(BaseModel):
    events: list[dict]
    last_synced_at: datetime | None = None


class SyncResponse(BaseModel):
    processed_count: int
    failed_count: int
    conflicts: list[dict]
    server_changes: list[dict]
    new_sync_cursor: str
