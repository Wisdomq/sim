"""Commission, targets, and performance tracking routes."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.api.dependencies import get_current_user, require_hq, require_hq_or_branch
from simcards_backend.core.database import get_db
from simcards_backend.models import BrandAmbassador, PeriodType, Role, SubjectType, User
from simcards_backend.schemas.commission import (
    CommissionRuleCreateRequest,
    TargetCreateRequest,
)
from simcards_backend.services.commission import (
    calculate_ba_daily_target,
    create_commission_rule,
    create_target,
    get_branch_summary,
    list_commission_rules,
    list_targets,
    update_performance_snapshot,
)
from simcards_backend.services.sales import get_commission_earned

router = APIRouter(prefix="/commission", tags=["commission"])


@router.post("/rules", status_code=201)
def create_rule(
    payload: CommissionRuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Create a new commission rule."""
    rule = create_commission_rule(
        db,
        actor=current_user,
        name=payload.name,
        amount_per_sim=payload.amount_per_sim,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    return {
        "id": rule.id,
        "dealer_id": rule.dealer_id,
        "name": rule.name,
        "amount_per_sim": str(rule.amount_per_sim),
        "effective_from": rule.effective_from,
        "effective_to": rule.effective_to,
        "created_by_id": rule.created_by_id,
        "created_at": rule.created_at,
    }


@router.get("/rules")
def get_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    """List all commission rules for the dealer."""
    rules = list_commission_rules(db, actor=current_user)
    return [
        {
            "id": rule.id,
            "dealer_id": rule.dealer_id,
            "name": rule.name,
            "amount_per_sim": str(rule.amount_per_sim),
            "effective_from": rule.effective_from,
            "effective_to": rule.effective_to,
            "created_by_id": rule.created_by_id,
            "created_at": rule.created_at,
        }
        for rule in rules
    ]


@router.post("/targets", status_code=201)
def create_target_endpoint(
    payload: TargetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Create a performance target for a branch."""
    target = create_target(
        db,
        actor=current_user,
        branch_id=payload.branch_id,
        period_type=payload.period_type,
        quantity=payload.quantity,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    return {
        "id": target.id,
        "dealer_id": target.dealer_id,
        "branch_id": target.branch_id,
        "period_type": target.period_type.value,
        "quantity": target.quantity,
        "effective_from": target.effective_from,
        "effective_to": target.effective_to,
        "set_by_id": target.set_by_id,
        "created_at": target.created_at,
    }


@router.get("/targets")
def get_targets(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    """List targets, optionally filtered by branch."""
    targets = list_targets(db, actor=current_user, branch_id=branch_id)
    return [
        {
            "id": target.id,
            "dealer_id": target.dealer_id,
            "branch_id": target.branch_id,
            "period_type": target.period_type.value,
            "quantity": target.quantity,
            "effective_from": target.effective_from,
            "effective_to": target.effective_to,
            "set_by_id": target.set_by_id,
            "created_at": target.created_at,
        }
        for target in targets
    ]


def _assert_performance_scope(
    db: Session,
    actor: User,
    subject_type: SubjectType,
    subject_id: int,
) -> None:
    """Enforce the §5 performance-visibility rows: BA self only, Branch
    own branch + its BAs, HQ everything (incl. org rollup)."""
    if actor.role == Role.HQ:
        return
    if actor.role == Role.BA:
        if subject_type != SubjectType.BA or subject_id != actor.ba_profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return
    # Branch role.
    if subject_type == SubjectType.DEALER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this action",
        )
    if subject_type == SubjectType.BRANCH:
        if subject_id != actor.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return
    ba = db.scalar(
        select(BrandAmbassador).where(
            BrandAmbassador.dealer_id == actor.dealer_id,
            BrandAmbassador.id == subject_id,
        )
    )
    if ba is None or ba.branch_id != actor.branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this action",
        )


@router.get("/performance")
def get_performance(
    subject_type: SubjectType,
    subject_id: int,
    period_type: PeriodType,
    period_start: date,
    period_end: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get or update performance snapshot for a subject."""
    _assert_performance_scope(db, current_user, subject_type, subject_id)

    snapshot = update_performance_snapshot(
        db,
        dealer_id=current_user.dealer_id,
        subject_type=subject_type,
        subject_id=subject_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
    )

    return {
        "id": snapshot.id,
        "dealer_id": snapshot.dealer_id,
        "subject_type": snapshot.subject_type.value,
        "subject_id": snapshot.subject_id,
        "period_type": snapshot.period_type.value,
        "period_start": snapshot.period_start.isoformat(),
        "period_end": snapshot.period_end.isoformat(),
        "target_quantity": snapshot.target_quantity,
        "actual_sold_quantity": snapshot.actual_sold_quantity,
        "percentage_achieved": str(snapshot.percentage_achieved),
        "computed_at": snapshot.computed_at,
    }


@router.get("/earned")
def get_commission(
    ba_id: int | None = None,
    branch_id: int | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get commission earned for a given scope, enforced per role (matrix §5)."""
    if current_user.role == Role.BA:
        if ba_id is not None and ba_id != current_user.ba_profile_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this action")
        if branch_id is not None and branch_id != current_user.branch_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this action")
        ba_id = current_user.ba_profile_id
    elif current_user.role == Role.BRANCH:
        if branch_id is not None and branch_id != current_user.branch_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this action")
        if ba_id is not None:
            ba = db.scalar(
                select(BrandAmbassador).where(
                    BrandAmbassador.dealer_id == current_user.dealer_id,
                    BrandAmbassador.id == ba_id,
                )
            )
            if ba is None or ba.branch_id != current_user.branch_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this action")
        branch_id = current_user.branch_id

    total = get_commission_earned(
        db,
        dealer_id=current_user.dealer_id,
        ba_id=ba_id,
        branch_id=branch_id,
        from_date=from_date,
        to_date=to_date,
    )

    return {
        "total_commission": str(total),
        "period_start": from_date,
        "period_end": to_date,
    }


@router.get("/branch-summary")
def get_branch_summary_endpoint(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    """Get summary statistics for branches."""
    summary = get_branch_summary(db, actor=current_user, branch_id=branch_id)
    return summary


@router.get("/ba-daily-target")
def get_ba_daily_target_endpoint(
    branch_id: int,
    as_of: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate the daily target per BA for a branch.

    BA role may read only its own branch (FR-BA-05); HQ and Branch keep
    their existing scope for own-branch targets.
    """
    if current_user.role == Role.BA and branch_id != current_user.branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this action",
        )
    daily_target = calculate_ba_daily_target(
        db, dealer_id=current_user.dealer_id, branch_id=branch_id, as_of=as_of
    )

    return {
        "branch_id": branch_id,
        "daily_target_per_ba": daily_target,
        "as_of": (as_of or date.today()).isoformat(),
    }
