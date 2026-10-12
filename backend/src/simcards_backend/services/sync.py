"""Offline sync services for conflict handling and data synchronization."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.models import (
    BrandAmbassador,
    Role,
    SaleEvent,
    SimCard,
    StockTransfer,
    User,
)
from simcards_backend.services.sales import record_sale


def _extract_sale_fields(event: dict[str, Any]) -> dict[str, Any]:
    """Extract sale fields from either the nested payload schema
    (``{"type": "sale", "data": {...}}``) or the flat mobile schema
    (``{"type": "SALE", "serial_number": ..., ...}``)."""
    data = event.get("data")
    if isinstance(data, dict):
        return data
    return event


def process_sync_events(
    db: Session,
    *,
    actor: User,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Process offline sync events from a client.

    Handles:
    - Sale events with client event IDs for idempotency
    - Conflict detection and resolution
    - Sequential processing in creation order

    Args:
        db: Database session
        actor: The user syncing events
        events: List of client events to process

    Returns:
        Dict with processing results including conflicts
    """
    if actor.role != Role.BA or actor.ba_profile_id is None:
        # Non-BA clients (Branch/HQ) must not push sale events; they may still
        # pull server changes through the same endpoint.
        return {
            "processed_count": 0,
            "failed_count": len(events),
            "conflicts": [],
        }

    processed_count = 0
    failed_count = 0
    conflicts: list[dict[str, Any]] = []

    # Sort events by timestamp to process in order
    sorted_events = sorted(events, key=lambda e: e.get("timestamp", datetime.min))

    for event in sorted_events:
        event_type = str(event.get("type", "")).lower()

        if event_type == "sale":
            try:
                sale_data = _extract_sale_fields(event)
                serial_number = sale_data.get("serial_number")
                sold_at = sale_data.get("sold_at")
                client_event_id = sale_data.get("client_event_id")

                if not serial_number or not sold_at:
                    failed_count += 1
                    continue

                # Convert string timestamp to datetime if needed
                if isinstance(sold_at, str):
                    sold_at = datetime.fromisoformat(sold_at)

                record_sale(
                    db,
                    actor=actor,
                    serial_number=serial_number,
                    sold_at=sold_at,
                    client_event_id=client_event_id,
                )
                processed_count += 1

            except HTTPException as exc:
                # Check if this is a conflict (e.g., SIM already sold)
                if exc.status_code == status.HTTP_409_CONFLICT:
                    sale_data = _extract_sale_fields(event)
                    conflicts.append(
                        {
                            "event": event,
                            "client_event_id": sale_data.get("client_event_id"),
                            "reason": exc.detail,
                            "type": "conflict",
                        }
                    )
                    failed_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

    return {
        "processed_count": processed_count,
        "failed_count": failed_count,
        "conflicts": conflicts,
    }


def _sim_change(sim: SimCard) -> dict[str, Any]:
    return {
        "type": "sim_update",
        "data": {
            "id": sim.id,
            "dealer_id": sim.dealer_id,
            "serial_number": sim.serial_number,
            "status": sim.status.value,
            "current_branch_id": sim.current_branch_id,
            "current_ba_id": sim.current_ba_id,
            "expiry_date": sim.expiry_date.isoformat() if sim.expiry_date else None,
            "updated_at": sim.updated_at.isoformat(),
        },
    }


def _sale_confirmed_change(sale: SaleEvent, *, include_scope: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": sale.id,
        "sim_card_id": sale.sim_card_id,
        "ba_id": sale.ba_id,
        "branch_id": sale.branch_id,
        "sold_at": sale.sold_at.isoformat(),
        "synced_at": sale.synced_at.isoformat(),
        "commission_amount": str(sale.commission_amount)
        if sale.commission_amount is not None
        else None,
    }
    if not include_scope:
        data.pop("ba_id", None)
        data.pop("branch_id", None)
    return {"type": "sale_confirmed", "data": data}


def _ba_change(ba: BrandAmbassador, email: str | None = None) -> dict[str, Any]:
    return {
        "type": "ba_update",
        "data": {
            "id": ba.id,
            "dealer_id": ba.dealer_id,
            "branch_id": ba.branch_id,
            "name": ba.name,
            "email": email,
            "phone_msisdn": ba.phone_msisdn,
            "id_number": ba.id_number,
            "photo_url": ba.photo_url,
            "status": ba.status.value,
            "updated_at": ba.updated_at.isoformat(),
        },
    }


def get_server_changes(
    db: Session,
    *,
    actor: User,
    last_synced_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Get server changes since the last sync for the user's scope.

    Returns changes relevant to the user:
    - For BAs: their SIM assignments, sales, and reassignments
    - For Branches: their BAs' activities, branch stock, and banch record
    - For HQ: branch and BA records as well as recent sales

    Args:
        db: Database session
        actor: The user requesting changes
        last_synced_at: Optional last sync timestamp cursor

    Returns:
        List of change events
    """
    changes: list[dict[str, Any]] = []

    if actor.role == Role.BA and actor.ba_profile_id:
        # BAs get changes to their assigned SIMs and their sales
        sim_query = select(SimCard).where(
            SimCard.dealer_id == actor.dealer_id,
            SimCard.current_ba_id == actor.ba_profile_id,
        )
        if last_synced_at:
            sim_query = sim_query.where(SimCard.updated_at >= last_synced_at)

        sims = db.scalars(sim_query).all()
        for sim in sims:
            changes.append(_sim_change(sim))

        # BA record for the current BA so the app can mirror it locally
        ba = db.scalar(
            select(BrandAmbassador).where(
                BrandAmbassador.dealer_id == actor.dealer_id,
                BrandAmbassador.id == actor.ba_profile_id,
            )
        )
        if ba is not None:
            user = db.get(User, ba.user_id)
            changes.append(_ba_change(ba, email=user.email if user else None))

        # Get recent sales for this BA
        sales_query = select(SaleEvent).where(
            SaleEvent.dealer_id == actor.dealer_id,
            SaleEvent.ba_id == actor.ba_profile_id,
        )
        if last_synced_at:
            sales_query = sales_query.where(SaleEvent.synced_at >= last_synced_at)

        sales = db.scalars(sales_query).all()
        for sale in sales:
            changes.append(_sale_confirmed_change(sale))

    elif actor.role == Role.BRANCH and actor.branch_id:
        # Branches get changes for their BAs and branch stock
        ba_query = select(BrandAmbassador).where(
            BrandAmbassador.dealer_id == actor.dealer_id,
            BrandAmbassador.branch_id == actor.branch_id,
        )
        if last_synced_at:
            ba_query = ba_query.where(BrandAmbassador.updated_at >= last_synced_at)

        bas = db.scalars(ba_query).all()
        for ba in bas:
            user = db.get(User, ba.user_id)
            changes.append(_ba_change(ba, email=user.email if user else None))

        # The branch's own record
        from simcards_backend.models import Branch

        branch = db.scalar(
            select(Branch).where(
                Branch.dealer_id == actor.dealer_id,
                Branch.id == actor.branch_id,
            )
        )
        if branch is not None:
            changes.append(
                {
                    "type": "branch_update",
                    "data": {
                        "id": branch.id,
                        "dealer_id": branch.dealer_id,
                        "name": branch.name,
                        "type": branch.type.value,
                        "id_number": branch.id_number,
                        "photo_url": branch.photo_url,
                        "created_at": branch.created_at.isoformat(),
                    },
                }
            )

        # SIMs in the branch pool or assigned to the branch's BAs
        sim_query = select(SimCard).where(
            SimCard.dealer_id == actor.dealer_id,
            (SimCard.current_branch_id == actor.branch_id)
            | (
                SimCard.current_ba_id.in_(
                    select(BrandAmbassador.id).where(
                        BrandAmbassador.dealer_id == actor.dealer_id,
                        BrandAmbassador.branch_id == actor.branch_id,
                    )
                )
            ),
        )
        if last_synced_at:
            sim_query = sim_query.where(SimCard.updated_at >= last_synced_at)

        for sim in db.scalars(sim_query).all():
            changes.append(_sim_change(sim))

        # Get stock transfers involving this branch
        transfer_query = select(StockTransfer).where(
            StockTransfer.dealer_id == actor.dealer_id,
            (StockTransfer.to_owner_id == actor.branch_id)
            | (StockTransfer.from_owner_id == actor.branch_id),
        )
        if last_synced_at:
            transfer_query = transfer_query.where(StockTransfer.created_at >= last_synced_at)

        transfers = db.scalars(transfer_query).all()
        for transfer in transfers:
            changes.append(
                {
                    "type": "stock_transfer",
                    "data": {
                        "id": transfer.id,
                        "sim_card_id": transfer.sim_card_id,
                        "from_owner_type": transfer.from_owner_type.value,
                        "to_owner_type": transfer.to_owner_type.value,
                        "transfer_type": transfer.transfer_type.value,
                        "created_at": transfer.created_at.isoformat(),
                    },
                }
            )

    elif actor.role == Role.HQ:
        # HQ gets branch and BA records plus recent sales
        from simcards_backend.models import Branch

        branches = db.scalars(
            select(Branch).where(Branch.dealer_id == actor.dealer_id)
        ).all()
        for branch in branches:
            changes.append(
                {
                    "type": "branch_update",
                    "data": {
                        "id": branch.id,
                        "dealer_id": branch.dealer_id,
                        "name": branch.name,
                        "type": branch.type.value,
                        "id_number": branch.id_number,
                        "photo_url": branch.photo_url,
                        "created_at": branch.created_at.isoformat(),
                    },
                }
            )

        bas = db.scalars(
            select(BrandAmbassador).where(BrandAmbassador.dealer_id == actor.dealer_id)
        ).all()
        for ba in bas:
            user = db.get(User, ba.user_id)
            changes.append(_ba_change(ba, email=user.email if user else None))

        sales_query = select(SaleEvent).where(SaleEvent.dealer_id == actor.dealer_id)
        if last_synced_at:
            sales_query = sales_query.where(SaleEvent.synced_at >= last_synced_at)

        sales = db.scalars(sales_query.order_by(SaleEvent.synced_at.desc()).limit(100)).all()
        for sale in sales:
            changes.append(_sale_confirmed_change(sale, include_scope=True))

    return changes