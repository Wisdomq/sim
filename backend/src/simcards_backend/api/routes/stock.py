"""Stock intake and lifecycle routes."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.api.dependencies import (
    get_current_user,
    require_branch,
    require_ba,
    require_hq,
    require_hq_or_branch,
)
from simcards_backend.core.config import settings
from simcards_backend.core.database import get_db
from simcards_backend.models import ReturnEvent, ReturnStatus, Role, SimCard, SimStatus, User
from simcards_backend.schemas.stock import (
    AssignToBrandAmbassadorRequest,
    BoxScanIntakeRequest,
    BulkActionResponse,
    DistributeStockRequest,
    PickListUploadResponse,
    RequestReturnRequest,
    ReturnEventResponse,
    ReturnToBranchRequest,
    SaleRequest,
    SimCardResponse,
    StockIntakeResult,
    SyncRequest,
    SyncResponse,
)
from simcards_backend.services.sales import get_ba_sales, record_sale
from simcards_backend.services.stock import (
    assign_sims_to_ba,
    distribute_stock_to_branch,
    fulfill_return_request,
    intake_box_scan,
    list_sim_cards,
    request_stock_return,
    return_sims_to_branch,
)
from simcards_backend.services.sync import get_server_changes, process_sync_events
from simcards_backend.tasks.pdf_parser import parse_pick_list_pdf

router = APIRouter(prefix="/stock", tags=["stock"])


def _intake_response(outcome) -> StockIntakeResult:
    return StockIntakeResult(
        batch_id=outcome.batch_id or 0,
        source_reference=outcome.source_reference,
        inserted_count=outcome.inserted_count,
        duplicate_count=outcome.duplicate_count,
        duplicates=outcome.duplicates,
    )


@router.post("/intake/box-scan", response_model=StockIntakeResult, status_code=status.HTTP_201_CREATED)
def box_scan_intake(
    payload: BoxScanIntakeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    outcome = intake_box_scan(
        db,
        actor=current_user,
        box_barcode=payload.box_barcode,
        serials=payload.serials,
        first_serial=payload.first_serial,
        quantity=payload.quantity,
        expiry_date=payload.expiry_date,
    )
    return _intake_response(outcome)


@router.post("/intake/pick-list-pdf", response_model=PickListUploadResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_pick_list_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(require_hq),
):
    upload_dir = Path(settings.UPLOAD_DIR) / "pick-lists" / str(current_user.dealer_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "pick-list.pdf").suffix or ".pdf"
    file_path = upload_dir / f"{uuid.uuid4()}{suffix}"
    with file_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    task = parse_pick_list_pdf.delay(str(file_path), current_user.dealer_id, current_user.id)
    return PickListUploadResponse(task_id=task.id, file_reference=str(file_path))


@router.post("/distribute", response_model=list[SimCardResponse])
def distribute_stock(
    payload: DistributeStockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    return distribute_stock_to_branch(
        db,
        actor=current_user,
        branch_id=payload.branch_id,
        quantity=payload.quantity,
        serial_numbers=payload.serial_numbers,
    )


@router.post("/assign-to-ba", response_model=list[SimCardResponse])
def assign_to_ba(
    payload: AssignToBrandAmbassadorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_branch),
):
    return assign_sims_to_ba(
        db,
        actor=current_user,
        ba_id=payload.ba_id,
        serial_numbers=payload.serial_numbers,
    )


@router.post("/return-to-branch", response_model=BulkActionResponse)
def return_to_branch(
    payload: ReturnToBranchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_branch),
):
    sims = return_sims_to_branch(
        db,
        actor=current_user,
        serial_numbers=payload.serial_numbers,
        reason=payload.reason,
    )
    return BulkActionResponse(
        processed_count=len(sims),
        serial_numbers=[sim.serial_number for sim in sims],
    )


@router.post("/return-requests", response_model=list[ReturnEventResponse], status_code=status.HTTP_201_CREATED)
def create_return_request(
    payload: RequestReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    return request_stock_return(
        db,
        actor=current_user,
        branch_id=payload.branch_id,
        serial_numbers=payload.serial_numbers,
        reason=payload.reason,
    )


@router.get("/return-requests")
def list_return_requests(
    branch_id: int | None = None,
    status_filter: ReturnStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    """List stock return requests scoped to the caller's branch."""
    query = select(ReturnEvent).where(ReturnEvent.dealer_id == current_user.dealer_id)
    if current_user.role == Role.BRANCH:
        query = query.where(ReturnEvent.branch_id == current_user.branch_id)
    elif branch_id is not None:
        query = query.where(ReturnEvent.branch_id == branch_id)
    if status_filter is not None:
        query = query.where(ReturnEvent.status == status_filter)

    events = db.scalars(query.order_by(ReturnEvent.return_date.desc())).all()
    results = []
    for event in events:
        sim = db.scalar(
            select(SimCard).where(
                SimCard.id == event.sim_card_id,
                SimCard.dealer_id == current_user.dealer_id,
            )
        )
        results.append(
            {
                "id": event.id,
                "dealer_id": event.dealer_id,
                "sim_card_id": event.sim_card_id,
                "serial_number": sim.serial_number if sim else None,
                "requested_by_id": event.requested_by_id,
                "branch_id": event.branch_id,
                "return_date": event.return_date.isoformat(),
                "reason": event.reason,
                "status": event.status.value,
            }
        )
    return results


@router.post("/return-requests/{return_event_id}/fulfill", response_model=ReturnEventResponse)
def fulfill_return(
    return_event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_branch),
):
    return fulfill_return_request(db, actor=current_user, return_event_id=return_event_id)


@router.get("/sim-cards", response_model=list[SimCardResponse])
def get_sim_cards(
    status_filter: SimStatus | None = None,
    branch_id: int | None = None,
    ba_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_sim_cards(
        db,
        actor=current_user,
        status_filter=status_filter,
        branch_id=branch_id,
        ba_id=ba_id,
    )


@router.post("/sales", status_code=status.HTTP_201_CREATED)
def record_sim_sale(
    payload: SaleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ba),
):
    """Record a BA sale of a SIM card."""
    sale = record_sale(
        db,
        actor=current_user,
        serial_number=payload.serial_number,
        sold_at=payload.sold_at,
        client_event_id=payload.client_event_id,
    )
    return {
        "id": sale.id,
        "dealer_id": sale.dealer_id,
        "sim_card_id": sale.sim_card_id,
        "ba_id": sale.ba_id,
        "branch_id": sale.branch_id,
        "sold_at": sale.sold_at,
        "scanned_via": sale.scanned_via.value,
        "synced_at": sale.synced_at,
        "commission_amount": str(sale.commission_amount) if sale.commission_amount else None,
    }


@router.get("/sales")
def get_sales(
    ba_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get sales for the current user's scope."""
    sales = get_ba_sales(
        db,
        actor=current_user,
        ba_id=ba_id,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": sale.id,
            "dealer_id": sale.dealer_id,
            "sim_card_id": sale.sim_card_id,
            "ba_id": sale.ba_id,
            "branch_id": sale.branch_id,
            "sold_at": sale.sold_at,
            "scanned_via": sale.scanned_via.value,
            "synced_at": sale.synced_at,
            "commission_amount": str(sale.commission_amount) if sale.commission_amount else None,
        }
        for sale in sales
    ]


@router.post("/sync")
def sync_data(
    payload: SyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Offline sync endpoint for mobile clients.

    Processes client events and returns server changes since last sync.
    """
    from datetime import datetime, timezone

    # Process client events
    sync_result = process_sync_events(
        db,
        actor=current_user,
        events=payload.events,
    )

    # Get server changes
    server_changes = get_server_changes(
        db,
        actor=current_user,
        last_synced_at=payload.last_synced_at,
    )

    # Return new sync cursor
    new_sync_cursor = datetime.now(timezone.utc)

    return {
        "processed_count": sync_result["processed_count"],
        "failed_count": sync_result["failed_count"],
        "conflicts": sync_result["conflicts"],
        "server_changes": server_changes,
        "new_sync_cursor": new_sync_cursor.isoformat(),
    }
