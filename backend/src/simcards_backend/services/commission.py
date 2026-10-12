"""Commission, targets, and performance tracking services."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from simcards_backend.models import (
    AccountStatus,
    Branch,
    BrandAmbassador,
    CommissionRule,
    PeriodType,
    PerformanceSnapshot,
    Role,
    SaleEvent,
    SubjectType,
    SimCard,
    SimStatus,
    Target,
    User,
)
from simcards_backend.services.audit import write_audit_log


def create_commission_rule(
    db: Session,
    *,
    actor: User,
    name: str,
    amount_per_sim: Decimal,
    effective_from: datetime,
    effective_to: datetime | None = None,
) -> CommissionRule:
    """
    Create a new commission rule for the dealer.

    Args:
        db: Database session
        actor: The HQ user creating the rule
        name: Rule name
        amount_per_sim: Commission amount per SIM sold
        effective_from: When the rule becomes effective
        effective_to: Optional end date for the rule

    Returns:
        The created CommissionRule
    """
    if actor.role != Role.HQ:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HQ users can create commission rules.",
        )

    # Validate date range
    if effective_to and effective_to <= effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be after effective_from",
        )

    rule = CommissionRule(
        dealer_id=actor.dealer_id,
        name=name.strip(),
        amount_per_sim=amount_per_sim,
        effective_from=effective_from,
        effective_to=effective_to,
        created_by_id=actor.id,
    )
    db.add(rule)
    db.flush()

    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="COMMISSION_RULE_CREATED",
        entity_type="CommissionRule",
        entity_id=rule.id,
        metadata={
            "name": name,
            "amount_per_sim": str(amount_per_sim),
            "effective_from": effective_from.isoformat(),
            "effective_to": effective_to.isoformat() if effective_to else None,
        },
    )

    db.commit()
    db.refresh(rule)
    return rule


def list_commission_rules(db: Session, *, actor: User) -> list[CommissionRule]:
    """List all commission rules for the dealer."""
    return list(
        db.scalars(
            select(CommissionRule)
            .where(CommissionRule.dealer_id == actor.dealer_id)
            .order_by(CommissionRule.effective_from.desc())
        )
    )


def create_target(
    db: Session,
    *,
    actor: User,
    branch_id: int,
    period_type: PeriodType,
    quantity: int,
    effective_from: datetime,
    effective_to: datetime | None = None,
) -> Target:
    """
    Create a performance target for a branch.

    Args:
        db: Database session
        actor: The HQ user creating the target
        branch_id: The branch to set the target for
        period_type: DAILY, WEEKLY, or MONTHLY
        quantity: Target quantity of SIMs
        effective_from: When the target becomes effective
        effective_to: Optional end date for the target

    Returns:
        The created Target
    """
    if actor.role != Role.HQ:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HQ users can create targets.",
        )

    # Validate branch exists
    branch = db.scalar(
        select(Branch).where(
            Branch.dealer_id == actor.dealer_id,
            Branch.id == branch_id,
        )
    )
    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    # Validate date range
    if effective_to and effective_to <= effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be after effective_from",
        )

    target = Target(
        dealer_id=actor.dealer_id,
        branch_id=branch_id,
        period_type=period_type,
        quantity=quantity,
        effective_from=effective_from,
        effective_to=effective_to,
        set_by_id=actor.id,
    )
    db.add(target)
    db.flush()

    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="TARGET_CREATED",
        entity_type="Target",
        entity_id=target.id,
        metadata={
            "branch_id": branch_id,
            "period_type": period_type.value,
            "quantity": quantity,
            "effective_from": effective_from.isoformat(),
        },
    )

    db.commit()
    db.refresh(target)
    return target


def list_targets(db: Session, *, actor: User, branch_id: int | None = None) -> list[Target]:
    """List targets, optionally filtered by branch."""
    query = select(Target).where(Target.dealer_id == actor.dealer_id)
    if branch_id is not None:
        query = query.where(Target.branch_id == branch_id)
    return list(db.scalars(query.order_by(Target.effective_from.desc())))


def calculate_ba_daily_target(db: Session, *, dealer_id: int, branch_id: int, as_of: date | None = None) -> int:
    """
    Calculate the daily target for each BA in a branch.

    Formula: Branch daily target ÷ current number of active BAs

    Args:
        db: Database session
        dealer_id: The dealer ID for tenant scoping
        branch_id: The branch to calculate for
        as_of: Optional date to calculate for (defaults to today)

    Returns:
        The daily target per BA
    """
    effective_date = as_of or date.today()

    # A target is effective for the calendar day on (or before) which its
    # effective_from falls; compare against the window for the as-of date
    # rather than the bare date to avoid SQLite string-boundary issues.
    window_end = datetime.combine(effective_date + timedelta(days=1), datetime.min.time())

    # Get the active daily target for the branch
    target = db.scalar(
        select(Target)
        .where(
            Target.dealer_id == dealer_id,
            Target.branch_id == branch_id,
            Target.period_type == PeriodType.DAILY,
            Target.effective_from < window_end,
        )
        .order_by(Target.effective_from.desc())
        .limit(1)
    )

    if target is None:
        return 0

    # Count active BAs in the branch
    active_ba_count = db.scalar(
        select(func.count(BrandAmbassador.id))
        .where(
            BrandAmbassador.dealer_id == dealer_id,
            BrandAmbassador.branch_id == branch_id,
            BrandAmbassador.status == AccountStatus.ACTIVE,
        )
    )

    if active_ba_count is None or active_ba_count == 0:
        return 0

    return target.quantity // active_ba_count


def update_performance_snapshot(
    db: Session,
    *,
    dealer_id: int,
    subject_type: SubjectType,
    subject_id: int,
    period_type: PeriodType,
    period_start: date,
    period_end: date,
) -> PerformanceSnapshot:
    """
    Update or create a performance snapshot for a subject.

    Calculates actual sold quantity and percentage achieved vs target.

    Args:
        db: Database session
        dealer_id: The dealer ID
        subject_type: BA, BRANCH, or DEALER
        subject_id: The ID of the subject
        period_type: DAILY, WEEKLY, or MONTHLY
        period_start: Start of the period
        period_end: End of the period

    Returns:
        The updated or created PerformanceSnapshot
    """
    # Get target quantity
    target_quantity = 0
    period_end_dt = datetime.combine(period_start + timedelta(days=1), datetime.min.time())
    if subject_type == SubjectType.BRANCH:
        target = db.scalar(
            select(Target)
            .where(
                Target.branch_id == subject_id,
                Target.period_type == period_type,
                Target.effective_from < period_end_dt,
            )
            .order_by(Target.effective_from.desc())
            .limit(1)
        )
        if target:
            target_quantity = target.quantity
    elif subject_type == SubjectType.DEALER:
        # Sum of all branch targets
        target_quantity = (
            db.scalar(
                select(func.sum(Target.quantity))
                .where(
                    Target.dealer_id == dealer_id, 
                    Target.period_type == period_type,
                    Target.effective_from < period_end_dt,
                )
            )
            or 0
        )
    elif subject_type == SubjectType.BA:
        # BA target is derived from branch target divided by active BAs
        ba = db.scalar(
            select(BrandAmbassador).where(
                BrandAmbassador.id == subject_id,
                BrandAmbassador.dealer_id == dealer_id,
            )
        )
        if ba:
            target_quantity = calculate_ba_daily_target(
                db, dealer_id=dealer_id, branch_id=ba.branch_id, as_of=period_start
            )

    # Calculate actual sold quantity
    actual_sold = 0
    if subject_type == SubjectType.BA:
        # Count sales recorded by this BA via SaleEvent.
        # record_sale() clears SimCard.current_ba_id, so we query SaleEvent instead.
        actual_sold = (
            db.scalar(
                select(func.count(SaleEvent.id)).where(
                    SaleEvent.dealer_id == dealer_id,
                    SaleEvent.ba_id == subject_id,
                    SaleEvent.sold_at >= datetime.combine(period_start, datetime.min.time()),
                    SaleEvent.sold_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
            or 0
        )
    elif subject_type == SubjectType.BRANCH:
        actual_sold = (
            db.scalar(
                select(func.count(SaleEvent.id))
                .where(
                    SaleEvent.dealer_id == dealer_id,
                    SaleEvent.branch_id == subject_id,
                    SaleEvent.sold_at >= datetime.combine(period_start, datetime.min.time()),
                    SaleEvent.sold_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
            or 0
        )
    elif subject_type == SubjectType.DEALER:
        actual_sold = (
            db.scalar(
                select(func.count(SaleEvent.id))
                .where(
                    SaleEvent.dealer_id == dealer_id,
                    SaleEvent.sold_at >= datetime.combine(period_start, datetime.min.time()),
                    SaleEvent.sold_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
            or 0
        )

    # Calculate percentage
    percentage = (
        (actual_sold / target_quantity * 100) if target_quantity > 0 else 0
    )

    # Check if snapshot exists
    snapshot = db.scalar(
        select(PerformanceSnapshot).where(
            PerformanceSnapshot.dealer_id == dealer_id,
            PerformanceSnapshot.subject_type == subject_type,
            PerformanceSnapshot.subject_id == subject_id,
            PerformanceSnapshot.period_type == period_type,
            PerformanceSnapshot.period_start == period_start,
            PerformanceSnapshot.period_end == period_end,
        )
    )

    if snapshot:
        snapshot.target_quantity = target_quantity
        snapshot.actual_sold_quantity = actual_sold
        snapshot.percentage_achieved = percentage
        snapshot.computed_at = datetime.now()
    else:
        snapshot = PerformanceSnapshot(
            dealer_id=dealer_id,
            subject_type=subject_type,
            subject_id=subject_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            target_quantity=target_quantity,
            actual_sold_quantity=actual_sold,
            percentage_achieved=percentage,
        )
        db.add(snapshot)

    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_branch_summary(db: Session, *, actor: User, branch_id: int | None = None) -> dict:
    """
    Get summary statistics for a branch or all branches.

    Includes SIM counts by status and sales information.

    Args:
        db: Database session
        actor: The current user
        branch_id: Optional branch ID to filter by

    Returns:
        Dict with summary statistics
    """
    query = select(Branch).where(Branch.dealer_id == actor.dealer_id)
    if branch_id is not None:
        query = query.where(Branch.id == branch_id)

    branches = db.scalars(query).all()
    summaries = []

    for branch in branches:
        # Get SIM counts by status for this branch
        sim_counts = db.execute(
            select(SimCard.status, func.count(SimCard.id))
            .where(SimCard.current_branch_id == branch.id)
            .group_by(SimCard.status)
        ).all()

        count_by_status = {status: 0 for status in SimStatus}
        for status, count in sim_counts:
            count_by_status[status] = count

        summaries.append(
            {
                "branch_id": branch.id,
                "branch_name": branch.name,
                "total_sims": sum(count_by_status.values()),
                "sold_count": count_by_status[SimStatus.SOLD],
                "unsold_count": sum(
                    count_by_status[s]
                    for s in [
                        SimStatus.IN_HQ_STOCK,
                        SimStatus.WITH_BRANCH,
                        SimStatus.WITH_BA,
                    ]
                ),
                "with_ba_count": count_by_status[SimStatus.WITH_BA],
                "with_branch_count": count_by_status[SimStatus.WITH_BRANCH],
                "expired_count": count_by_status[SimStatus.EXPIRED],
            }
        )

    if not summaries:
        return {"branches": []}
    return {"branches": summaries} if len(summaries) > 1 else summaries[0]
