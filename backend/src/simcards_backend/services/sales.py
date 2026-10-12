"""Sales and sync-related services."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.models import (
    BrandAmbassador,
    CommissionRule,
    Role,
    SaleEvent,
    ScannedVia,
    SimCard,
    SimStatus,
    User,
)
from simcards_backend.services.audit import write_audit_log


def record_sale(
    db: Session,
    *,
    actor: User,
    serial_number: str,
    sold_at: datetime,
    client_event_id: str | None = None,
) -> SaleEvent:
    """
    Record a BA sale of a SIM card.

    Validates that:
    - The SIM exists and belongs to the dealer
    - The SIM is currently WITH_BA and owned by this BA
    - The SIM hasn't already been sold

    Args:
        db: Database session
        actor: The BA user making the sale
        serial_number: The SIM serial number being sold
        sold_at: When the sale occurred (client timestamp)
        client_event_id: Optional client-generated UUID for idempotency

    Returns:
        The created SaleEvent

    Raises:
        HTTPException: If validation fails
    """
    if actor.role != Role.BA or actor.ba_profile_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only brand ambassadors can record sales.",
        )

    # Check for duplicate client event (idempotency)
    if client_event_id:
        existing = db.scalar(
            select(SaleEvent).where(
                SaleEvent.dealer_id == actor.dealer_id,
                SaleEvent.client_event_id == client_event_id,
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This sale has already been recorded.",
            )

    # Find the SIM card
    sim = db.scalar(
        select(SimCard).where(
            SimCard.dealer_id == actor.dealer_id,
            SimCard.serial_number == serial_number,
        )
    )
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIM card not found.",
        )

    # Validate SIM state and ownership
    if sim.status != SimStatus.WITH_BA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"SIM is not currently assigned to a BA. Current status: {sim.status.value}",
        )

    if sim.current_ba_id != actor.ba_profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This SIM is not assigned to you.",
        )

    # Get the applicable commission rule at the time of sale
    commission_rule = db.scalar(
        select(CommissionRule)
        .where(
            CommissionRule.dealer_id == actor.dealer_id,
            CommissionRule.effective_from <= sold_at,
        )
        .order_by(CommissionRule.effective_from.desc())
        .limit(1)
    )

    commission_amount = None
    commission_rule_id = None
    if commission_rule:
        commission_amount = commission_rule.amount_per_sim
        commission_rule_id = commission_rule.id

    # Create the sale event
    sale_event = SaleEvent(
        dealer_id=actor.dealer_id,
        sim_card_id=sim.id,
        ba_id=actor.ba_profile_id,
        branch_id=actor.branch_id,
        sold_at=sold_at,
        scanned_via=ScannedVia.CAMERA,
        commission_rule_id=commission_rule_id,
        commission_amount=commission_amount,
        client_event_id=client_event_id,
    )
    db.add(sale_event)

    # Update SIM status
    sim.status = SimStatus.SOLD
    sim.current_ba_id = None

    # Write audit log
    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="SIM_SOLD",
        entity_type="SimCard",
        entity_id=sim.id,
        metadata={
            "serial_number": serial_number,
            "ba_id": actor.ba_profile_id,
            "sold_at": sold_at.isoformat(),
            "client_event_id": client_event_id,
        },
    )

    db.commit()
    db.refresh(sale_event)
    return sale_event


def get_ba_sales(
    db: Session,
    *,
    actor: User,
    ba_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SaleEvent]:
    """
    Get sales for a BA (or the current user's BA profile).

    Args:
        db: Database session
        actor: The current user
        ba_id: Optional BA ID to filter by (must be in scope)
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of SaleEvents
    """
    query = select(SaleEvent).where(SaleEvent.dealer_id == actor.dealer_id)

    if actor.role == Role.BA:
        # BAs can only see their own sales
        query = query.where(SaleEvent.ba_id == actor.ba_profile_id)
    elif actor.role == Role.BRANCH:
        # Branches can see sales from their BAs
        query = query.where(SaleEvent.branch_id == actor.branch_id)
        if ba_id is not None:
            query = query.where(SaleEvent.ba_id == ba_id)
    elif actor.role == Role.HQ:
        # HQ can see all sales, optionally filtered by BA
        if ba_id is not None:
            query = query.where(SaleEvent.ba_id == ba_id)

    return list(
        db.scalars(query.order_by(SaleEvent.sold_at.desc()).limit(limit).offset(offset))
    )


def get_commission_earned(
    db: Session,
    *,
    dealer_id: int,
    ba_id: int | None = None,
    branch_id: int | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> Decimal:
    """
    Calculate total commission earned for a given scope.

    Args:
        db: Database session
        dealer_id: The dealer ID
        ba_id: Optional BA ID to filter by
        branch_id: Optional branch ID to filter by
        from_date: Optional start date for filtering
        to_date: Optional end date for filtering

    Returns:
        Total commission amount
    """
    query = select(SaleEvent).where(SaleEvent.dealer_id == dealer_id)

    if ba_id is not None:
        query = query.where(SaleEvent.ba_id == ba_id)
    if branch_id is not None:
        query = query.where(SaleEvent.branch_id == branch_id)
    if from_date is not None:
        query = query.where(SaleEvent.sold_at >= from_date)
    if to_date is not None:
        query = query.where(SaleEvent.sold_at <= to_date)

    sales = db.scalars(query).all()
    total = Decimal("0")
    for sale in sales:
        if sale.commission_amount:
            total += sale.commission_amount
    return total
