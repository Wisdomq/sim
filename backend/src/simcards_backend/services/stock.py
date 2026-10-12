"""Stock intake, distribution, reassignment, returns, and expiry services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.models import (
    Branch,
    BrandAmbassador,
    OwnerType,
    ReturnEvent,
    ReturnStatus,
    Role,
    SimCard,
    SimStatus,
    StockBatch,
    StockBatchSource,
    StockTransfer,
    TransferType,
    User,
)
from simcards_backend.services.audit import write_audit_log


@dataclass(frozen=True)
class StockIntakeOutcome:
    batch_id: int | None
    source_reference: str
    inserted_count: int
    duplicate_count: int
    duplicates: list[str]


def normalize_serials(serials: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for serial in serials:
        value = str(serial).strip()
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def derive_serial_range(first_serial: str, quantity: int = 100) -> list[str]:
    first = first_serial.strip()
    if not first.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="first_serial must be numeric to derive a serial-range mapping.",
        )
    start = int(first)
    width = len(first)
    return [str(start + offset).zfill(width) for offset in range(quantity)]


def ensure_branch_in_dealer(db: Session, *, dealer_id: int, branch_id: int) -> Branch:
    branch = db.scalar(select(Branch).where(Branch.dealer_id == dealer_id, Branch.id == branch_id))
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found.")
    return branch


def ensure_ba_in_branch(db: Session, *, dealer_id: int, branch_id: int, ba_id: int) -> BrandAmbassador:
    ba = db.scalar(
        select(BrandAmbassador).where(
            BrandAmbassador.dealer_id == dealer_id,
            BrandAmbassador.branch_id == branch_id,
            BrandAmbassador.id == ba_id,
        )
    )
    if ba is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand ambassador not found in this branch.",
        )
    return ba


def create_stock_batch_with_serials(
    db: Session,
    *,
    dealer_id: int,
    source: StockBatchSource,
    source_reference: str,
    serials: Iterable[str],
    imported_by_id: int | None,
    expiry_date: date | None = None,
) -> StockIntakeOutcome:
    normalized_serials = normalize_serials(serials)
    if not normalized_serials:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one SIM serial number is required.",
        )

    existing = db.scalars(
        select(SimCard).where(
            SimCard.dealer_id == dealer_id,
            SimCard.serial_number.in_(normalized_serials),
        )
    ).all()
    existing_by_serial = {sim.serial_number: sim for sim in existing}
    duplicates = [serial for serial in normalized_serials if serial in existing_by_serial]
    new_serials = [serial for serial in normalized_serials if serial not in existing_by_serial]

    batch_id: int | None = None
    if new_serials:
        batch = StockBatch(
            dealer_id=dealer_id,
            source=source,
            source_reference=source_reference.strip(),
            quantity=len(new_serials),
            imported_by_id=imported_by_id,
        )
        db.add(batch)
        db.flush()
        batch_id = batch.id

        for serial in new_serials:
            sim = SimCard(
                dealer_id=dealer_id,
                serial_number=serial,
                stock_batch_id=batch.id,
                status=SimStatus.IN_HQ_STOCK,
                expiry_date=expiry_date,
            )
            db.add(sim)
            db.flush()
            write_audit_log(
                db,
                dealer_id=dealer_id,
                actor_user_id=imported_by_id,
                action="SIM_STOCK_INTAKE",
                entity_type="SimCard",
                entity_id=sim.id,
                metadata={"serial_number": serial, "source": source.value, "batch_id": batch.id},
            )
    elif existing:
        batch_id = existing[0].stock_batch_id

    return StockIntakeOutcome(
        batch_id=batch_id,
        source_reference=source_reference.strip(),
        inserted_count=len(new_serials),
        duplicate_count=len(duplicates),
        duplicates=duplicates,
    )


def intake_box_scan(
    db: Session,
    *,
    actor: User,
    box_barcode: str,
    serials: list[str] | None,
    first_serial: str | None,
    quantity: int,
    expiry_date: date | None,
) -> StockIntakeOutcome:
    serial_list = normalize_serials(serials) if serials else derive_serial_range(first_serial or "", quantity)
    outcome = create_stock_batch_with_serials(
        db,
        dealer_id=actor.dealer_id,
        source=StockBatchSource.BOX_SCAN,
        source_reference=box_barcode,
        serials=serial_list,
        imported_by_id=actor.id,
        expiry_date=expiry_date,
    )
    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="BOX_SCAN_INTAKE",
        entity_type="StockBatch",
        entity_id=outcome.batch_id,
        metadata={
            "box_barcode": box_barcode,
            "inserted_count": outcome.inserted_count,
            "duplicate_count": outcome.duplicate_count,
        },
    )
    db.commit()
    return outcome


def _select_hq_stock(
    db: Session,
    *,
    dealer_id: int,
    quantity: int | None,
    serial_numbers: list[str] | None,
) -> list[SimCard]:
    if serial_numbers:
        serials = normalize_serials(serial_numbers)
        sims = db.scalars(
            select(SimCard).where(
                SimCard.dealer_id == dealer_id,
                SimCard.serial_number.in_(serials),
            )
        ).all()
        by_serial = {sim.serial_number: sim for sim in sims}
        missing = [serial for serial in serials if serial not in by_serial]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Some serials were not found.", "serials": missing},
            )
        invalid = [sim.serial_number for sim in sims if sim.status != SimStatus.IN_HQ_STOCK]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Some serials are not in HQ stock.", "serials": invalid},
            )
        return [by_serial[serial] for serial in serials]

    sims = db.scalars(
        select(SimCard)
        .where(
            SimCard.dealer_id == dealer_id,
            SimCard.status == SimStatus.IN_HQ_STOCK,
        )
        .order_by(SimCard.id)
        .limit(quantity or 0)
    ).all()
    if len(sims) < (quantity or 0):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Not enough HQ stock.")
    return sims


def distribute_stock_to_branch(
    db: Session,
    *,
    actor: User,
    branch_id: int,
    quantity: int | None,
    serial_numbers: list[str] | None,
) -> list[SimCard]:
    ensure_branch_in_dealer(db, dealer_id=actor.dealer_id, branch_id=branch_id)
    sims = _select_hq_stock(
        db,
        dealer_id=actor.dealer_id,
        quantity=quantity,
        serial_numbers=serial_numbers,
    )

    for sim in sims:
        sim.status = SimStatus.WITH_BRANCH
        sim.current_branch_id = branch_id
        sim.current_ba_id = None
        db.add(
            StockTransfer(
                dealer_id=actor.dealer_id,
                sim_card_id=sim.id,
                from_owner_type=OwnerType.HQ,
                from_owner_id=None,
                to_owner_type=OwnerType.BRANCH,
                to_owner_id=branch_id,
                transfer_type=TransferType.DISTRIBUTION,
                initiated_by_id=actor.id,
            )
        )
        write_audit_log(
            db,
            dealer_id=actor.dealer_id,
            actor_user_id=actor.id,
            action="SIM_DISTRIBUTED_TO_BRANCH",
            entity_type="SimCard",
            entity_id=sim.id,
            metadata={"serial_number": sim.serial_number, "branch_id": branch_id},
        )

    db.commit()
    for sim in sims:
        db.refresh(sim)
    return sims


def assign_sims_to_ba(
    db: Session,
    *,
    actor: User,
    ba_id: int,
    serial_numbers: list[str],
) -> list[SimCard]:
    if actor.role != Role.BRANCH or actor.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only branch users can assign or reassign SIMs to BAs.",
        )
    ensure_ba_in_branch(db, dealer_id=actor.dealer_id, branch_id=actor.branch_id, ba_id=ba_id)
    serials = normalize_serials(serial_numbers)
    sims = db.scalars(
        select(SimCard).where(
            SimCard.dealer_id == actor.dealer_id,
            SimCard.serial_number.in_(serials),
        )
    ).all()
    by_serial = {sim.serial_number: sim for sim in sims}
    missing = [serial for serial in serials if serial not in by_serial]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Some serials were not found.", "serials": missing},
        )

    allowed_statuses = {SimStatus.WITH_BRANCH, SimStatus.RETURNED_TO_BRANCH, SimStatus.WITH_BA}
    invalid = [
        sim.serial_number
        for sim in sims
        if sim.current_branch_id != actor.branch_id or sim.status not in allowed_statuses
    ]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Some SIMs are not assignable by this branch.", "serials": invalid},
        )

    for sim in [by_serial[serial] for serial in serials]:
        from_owner_type = OwnerType.BA if sim.current_ba_id else OwnerType.BRANCH
        from_owner_id = sim.current_ba_id or actor.branch_id
        sim.status = SimStatus.WITH_BA
        sim.current_branch_id = actor.branch_id
        sim.current_ba_id = ba_id
        db.add(
            StockTransfer(
                dealer_id=actor.dealer_id,
                sim_card_id=sim.id,
                from_owner_type=from_owner_type,
                from_owner_id=from_owner_id,
                to_owner_type=OwnerType.BA,
                to_owner_id=ba_id,
                transfer_type=TransferType.REASSIGNMENT,
                initiated_by_id=actor.id,
            )
        )
        write_audit_log(
            db,
            dealer_id=actor.dealer_id,
            actor_user_id=actor.id,
            action="SIM_ASSIGNED_TO_BA",
            entity_type="SimCard",
            entity_id=sim.id,
            metadata={"serial_number": sim.serial_number, "ba_id": ba_id},
        )

    db.commit()
    for sim in sims:
        db.refresh(sim)
    return [by_serial[serial] for serial in serials]


def return_sims_to_branch(
    db: Session,
    *,
    actor: User,
    serial_numbers: list[str],
    reason: str | None,
) -> list[SimCard]:
    if actor.role != Role.BRANCH or actor.branch_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only branch users can return SIMs.")
    serials = normalize_serials(serial_numbers)
    sims = db.scalars(
        select(SimCard).where(
            SimCard.dealer_id == actor.dealer_id,
            SimCard.serial_number.in_(serials),
        )
    ).all()
    by_serial = {sim.serial_number: sim for sim in sims}
    missing = [serial for serial in serials if serial not in by_serial]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Some serials were not found.", "serials": missing},
        )
    invalid = [
        sim.serial_number
        for sim in sims
        if sim.status != SimStatus.WITH_BA or sim.current_branch_id != actor.branch_id
    ]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Some SIMs are not with a BA in this branch.", "serials": invalid},
        )

    for sim in [by_serial[serial] for serial in serials]:
        from_ba_id = sim.current_ba_id
        sim.status = SimStatus.RETURNED_TO_BRANCH
        sim.current_ba_id = None
        db.add(
            StockTransfer(
                dealer_id=actor.dealer_id,
                sim_card_id=sim.id,
                from_owner_type=OwnerType.BA,
                from_owner_id=from_ba_id,
                to_owner_type=OwnerType.BRANCH,
                to_owner_id=actor.branch_id,
                transfer_type=TransferType.RETURN,
                initiated_by_id=actor.id,
            )
        )
        db.add(
            ReturnEvent(
                dealer_id=actor.dealer_id,
                sim_card_id=sim.id,
                branch_id=actor.branch_id,
                reason=reason,
                status=ReturnStatus.COMPLETED,
            )
        )
        write_audit_log(
            db,
            dealer_id=actor.dealer_id,
            actor_user_id=actor.id,
            action="SIM_RETURNED_TO_BRANCH",
            entity_type="SimCard",
            entity_id=sim.id,
            metadata={"serial_number": sim.serial_number, "from_ba_id": from_ba_id},
        )

    db.commit()
    for sim in sims:
        db.refresh(sim)
    return [by_serial[serial] for serial in serials]


def request_stock_return(
    db: Session,
    *,
    actor: User,
    branch_id: int,
    serial_numbers: list[str],
    reason: str | None,
) -> list[ReturnEvent]:
    ensure_branch_in_dealer(db, dealer_id=actor.dealer_id, branch_id=branch_id)
    serials = normalize_serials(serial_numbers)
    sims = db.scalars(
        select(SimCard).where(
            SimCard.dealer_id == actor.dealer_id,
            SimCard.serial_number.in_(serials),
        )
    ).all()
    by_serial = {sim.serial_number: sim for sim in sims}
    missing = [serial for serial in serials if serial not in by_serial]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Some serials were not found.", "serials": missing},
        )
    invalid = [
        sim.serial_number
        for sim in sims
        if sim.current_branch_id != branch_id
        or sim.status
        not in {SimStatus.WITH_BRANCH, SimStatus.WITH_BA, SimStatus.RETURNED_TO_BRANCH}
    ]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Some SIMs cannot be requested for return.", "serials": invalid},
        )

    return_events: list[ReturnEvent] = []
    for sim in [by_serial[serial] for serial in serials]:
        return_event = ReturnEvent(
            dealer_id=actor.dealer_id,
            sim_card_id=sim.id,
            requested_by_id=actor.id,
            branch_id=branch_id,
            reason=reason,
            status=ReturnStatus.REQUESTED,
        )
        db.add(return_event)
        db.flush()
        return_events.append(return_event)
        write_audit_log(
            db,
            dealer_id=actor.dealer_id,
            actor_user_id=actor.id,
            action="STOCK_RETURN_REQUESTED",
            entity_type="ReturnEvent",
            entity_id=return_event.id,
            metadata={"serial_number": sim.serial_number, "branch_id": branch_id},
        )

    db.commit()
    for return_event in return_events:
        db.refresh(return_event)
    return return_events


def fulfill_return_request(db: Session, *, actor: User, return_event_id: int) -> ReturnEvent:
    if actor.role != Role.BRANCH or actor.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only branch users can fulfill return requests.",
        )
    return_event = db.scalar(
        select(ReturnEvent).where(
            ReturnEvent.dealer_id == actor.dealer_id,
            ReturnEvent.id == return_event_id,
            ReturnEvent.branch_id == actor.branch_id,
        )
    )
    if return_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found.")
    if return_event.status != ReturnStatus.REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Return request is already completed.",
        )

    sim = db.scalar(
        select(SimCard).where(
            SimCard.dealer_id == actor.dealer_id,
            SimCard.id == return_event.sim_card_id,
        )
    )
    if sim is None or sim.current_branch_id != actor.branch_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SIM is no longer held by this branch.",
        )
    if sim.status in {SimStatus.SOLD, SimStatus.EXPIRED, SimStatus.RETURNED_TO_HQ}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SIM cannot be returned to HQ from its current state.",
        )

    from_owner_type = OwnerType.BA if sim.current_ba_id else OwnerType.BRANCH
    from_owner_id = sim.current_ba_id or actor.branch_id
    sim.status = SimStatus.RETURNED_TO_HQ
    sim.current_branch_id = None
    sim.current_ba_id = None
    return_event.status = ReturnStatus.COMPLETED
    db.add(
        StockTransfer(
            dealer_id=actor.dealer_id,
            sim_card_id=sim.id,
            from_owner_type=from_owner_type,
            from_owner_id=from_owner_id,
            to_owner_type=OwnerType.HQ,
            to_owner_id=None,
            transfer_type=TransferType.RETURN,
            initiated_by_id=actor.id,
        )
    )
    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="STOCK_RETURN_FULFILLED",
        entity_type="ReturnEvent",
        entity_id=return_event.id,
        metadata={"serial_number": sim.serial_number, "sim_card_id": sim.id},
    )
    db.commit()
    db.refresh(return_event)
    return return_event


def mark_expired_sim_cards(db: Session, *, as_of: date | None = None) -> int:
    today = as_of or date.today()
    sims = db.scalars(
        select(SimCard).where(
            SimCard.expiry_date.is_not(None),
            SimCard.expiry_date < today,
            SimCard.status.not_in([SimStatus.SOLD, SimStatus.RETURNED_TO_HQ, SimStatus.EXPIRED]),
        )
    ).all()
    for sim in sims:
        sim.status = SimStatus.EXPIRED
        write_audit_log(
            db,
            dealer_id=sim.dealer_id,
            actor_user_id=None,
            action="SIM_EXPIRED",
            entity_type="SimCard",
            entity_id=sim.id,
            metadata={"serial_number": sim.serial_number, "expiry_date": sim.expiry_date.isoformat()},
        )
    db.commit()
    return len(sims)


def list_sim_cards(
    db: Session,
    *,
    actor: User,
    status_filter: SimStatus | None = None,
    branch_id: int | None = None,
    ba_id: int | None = None,
) -> list[SimCard]:
    query = select(SimCard).where(SimCard.dealer_id == actor.dealer_id)
    if actor.role == Role.BRANCH:
        query = query.where(SimCard.current_branch_id == actor.branch_id)
    elif actor.role == Role.BA:
        query = query.where(SimCard.current_ba_id == actor.ba_profile_id)
    else:
        if branch_id is not None:
            query = query.where(SimCard.current_branch_id == branch_id)
        if ba_id is not None:
            query = query.where(SimCard.current_ba_id == ba_id)
    if status_filter is not None:
        query = query.where(SimCard.status == status_filter)
    return list(db.scalars(query.order_by(SimCard.id)))
