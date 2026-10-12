"""Login-inactivity flags and HQ in-app notification routes (Phase 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from simcards_backend.api.dependencies import require_hq
from simcards_backend.core.database import get_db
from simcards_backend.core.security import now_utc
from simcards_backend.models import AccountFlag, LoginEvent, Notification, User
from simcards_backend.schemas.flags import AccountFlagResponse
from simcards_backend.schemas.notifications import NotificationResponse

router = APIRouter(prefix="/flags", tags=["flags"])


@router.get("", response_model=list[AccountFlagResponse])
def list_flags(
    resolved: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """List login-inactivity flags for the dealer, optionally filtered by resolution state."""
    query = select(AccountFlag).where(AccountFlag.dealer_id == current_user.dealer_id)
    if resolved is not None:
        if resolved:
            query = query.where(AccountFlag.resolved_at.is_not(None))
        else:
            query = query.where(AccountFlag.resolved_at.is_(None))
    flags = list(db.scalars(query.order_by(AccountFlag.flagged_at.desc())))
    if not flags:
        return []

    user_ids = list({flag.user_id for flag in flags})
    last_login_rows = db.execute(
        select(LoginEvent.user_id, func.max(LoginEvent.logged_in_at))
        .where(
            LoginEvent.dealer_id == current_user.dealer_id,
            LoginEvent.user_id.in_(user_ids),
        )
        .group_by(LoginEvent.user_id)
    ).all()
    last_login_by_user = {user_id: logged_in_at for user_id, logged_in_at in last_login_rows}

    responses = []
    for flag in flags:
        response = AccountFlagResponse.model_validate(flag)
        response.last_login_at = last_login_by_user.get(flag.user_id)
        responses.append(response)
    return responses


@router.post("/{flag_id}/acknowledge", response_model=AccountFlagResponse)
def acknowledge_flag(
    flag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Acknowledge a flag (records the acknowledging HQ user, keeps the flag listed)."""
    flag = db.scalar(
        select(AccountFlag).where(
            AccountFlag.dealer_id == current_user.dealer_id,
            AccountFlag.id == flag_id,
        )
    )
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found.")
    flag.acknowledged_by_id = current_user.id
    db.commit()
    db.refresh(flag)
    return flag


@router.post("/{flag_id}/resolve", response_model=AccountFlagResponse)
def resolve_flag(
    flag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Manually resolve a flag (sets resolved_at)."""
    flag = db.scalar(
        select(AccountFlag).where(
            AccountFlag.dealer_id == current_user.dealer_id,
            AccountFlag.id == flag_id,
        )
    )
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found.")
    flag.resolved_at = now_utc()
    if flag.acknowledged_by_id is None:
        flag.acknowledged_by_id = current_user.id
    db.commit()
    db.refresh(flag)
    return flag


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """List the current HQ user's in-app notification feed."""
    query = select(Notification).where(
        Notification.dealer_id == current_user.dealer_id,
        Notification.user_id == current_user.id,
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    return list(db.scalars(query.order_by(Notification.created_at.desc()).limit(100)))


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    """Mark a notification as read."""
    notification = db.scalar(
        select(Notification).where(
            Notification.dealer_id == current_user.dealer_id,
            Notification.user_id == current_user.id,
            Notification.id == notification_id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification