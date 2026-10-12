"""Login-inactivity flagging services (design §6.10, FR-LOGIN-02/03)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from simcards_backend.core.security import now_utc
from simcards_backend.models import (
    AccountFlag,
    AccountFlagType,
    AccountStatus,
    Branch,
    LoginEvent,
    Notification,
    NotificationType,
    Role,
    User,
)
from simcards_backend.services.audit import write_audit_log

INACTIVITY_THRESHOLD_DAYS = 3


@dataclass(frozen=True)
class InactivityFlagOutcome:
    flagged_user_ids: list[int]
    freshly_flagged_count: int
    already_flagged_count: int


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=now_utc().tzinfo)
    return value


def flag_inactive_accounts(
    db: Session,
    *,
    dealer_id: int,
    cutoff_dt: datetime,
    as_of_dt: datetime,
) -> InactivityFlagOutcome:
    """
    Flag Branch/BA accounts that have not logged in within the inactivity window.

    Design §6.10: a scheduled daily job checks each Branch's and BA's most
    recent LoginEvent; if more than 3 days have passed with no login, the system
    creates an AccountFlag (INACTIVE_3_DAYS) and sets the account status to
    FLAGGED_INACTIVE, plus an in-app notification to HQ.

    Accounts that already hold an unresolved flag are left untouched (one flag
    per inactivity episode). Accounts that have never logged in are only flagged
    once they have existed longer than the inactivity window, so newly-created
    accounts are not flagged immediately.
    """
    eligible_users = db.scalars(
        select(User).where(
            User.dealer_id == dealer_id,
            User.role.in_([Role.BRANCH, Role.BA]),
            User.status == AccountStatus.ACTIVE,
        )
    ).all()
    if not eligible_users:
        return InactivityFlagOutcome(flagged_user_ids=[], freshly_flagged_count=0, already_flagged_count=0)

    user_ids = [user.id for user in eligible_users]

    last_login_rows = db.execute(
        select(LoginEvent.user_id, func.max(LoginEvent.logged_in_at))
        .where(
            LoginEvent.dealer_id == dealer_id,
            LoginEvent.user_id.in_(user_ids),
        )
        .group_by(LoginEvent.user_id)
    ).all()
    last_login_by_user = {user_id: logged_in_at for user_id, logged_in_at in last_login_rows}

    open_flag_user_ids = set(
        db.scalars(
            select(AccountFlag.user_id).where(
                AccountFlag.dealer_id == dealer_id,
                AccountFlag.user_id.in_(user_ids),
                AccountFlag.resolved_at.is_(None),
            )
        ).all()
    )

    hq_users = db.scalars(
        select(User).where(
            User.dealer_id == dealer_id,
            User.role == Role.HQ,
            User.status != AccountStatus.DISABLED,
        )
    ).all()

    branch_ids = {user.branch_id for user in eligible_users if user.branch_id is not None}
    branches_by_id: dict[int, Branch] = {}
    if branch_ids:
        branches_by_id = {
            branch.id: branch
            for branch in db.scalars(
                select(Branch).where(Branch.dealer_id == dealer_id, Branch.id.in_(branch_ids))
            ).all()
        }

    flagged_user_ids: list[int] = []
    already_flagged_count = 0
    freshly_flagged_count = 0

    for user in eligible_users:
        last_login = _as_aware(last_login_by_user.get(user.id))
        if user.id in open_flag_user_ids:
            already_flagged_count += 1
            continue

        if last_login is not None:
            if last_login >= cutoff_dt:
                continue
        else:
            created_at = _as_aware(user.created_at)
            if created_at is None or created_at > cutoff_dt:
                continue

        flag = AccountFlag(
            dealer_id=dealer_id,
            user_id=user.id,
            role=user.role,
            flag_type=AccountFlagType.INACTIVE_3_DAYS,
        )
        db.add(flag)
        user.status = AccountStatus.FLAGGED_INACTIVE

        branch = branches_by_id.get(user.branch_id) if user.branch_id else None
        account_label = f"{branch.name} branch" if branch and user.role == Role.BRANCH else (
            f"{branch.name} BA" if branch else user.role.value
        )
        body = (
            f"{user.email} ({account_label}) has not logged in for more than "
            f"{INACTIVITY_THRESHOLD_DAYS} days."
        )
        if last_login is not None:
            body += f" Last login: {last_login.isoformat()}."
        metadata = {
            "account_user_id": user.id,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "last_login": last_login.isoformat() if last_login is not None else None,
            "flag_type": AccountFlagType.INACTIVE_3_DAYS.value,
        }
        for hq_user in hq_users:
            db.add(
                Notification(
                    dealer_id=dealer_id,
                    user_id=hq_user.id,
                    type=NotificationType.ACCOUNT_FLAGGED_INACTIVE,
                    title="Account flagged for inactivity",
                    body=body,
                    metadata_json=metadata,
                )
            )

        write_audit_log(
            db,
            dealer_id=dealer_id,
            actor_user_id=None,
            action="ACCOUNT_FLAGGED_INACTIVE",
            entity_type="AccountFlag",
            entity_id=flag.id,
            metadata={
                "user_id": user.id,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "last_login": last_login.isoformat() if last_login is not None else None,
                "as_of": as_of_dt.isoformat(),
            },
        )
        flagged_user_ids.append(user.id)
        freshly_flagged_count += 1

    return InactivityFlagOutcome(
        flagged_user_ids=flagged_user_ids,
        freshly_flagged_count=freshly_flagged_count,
        already_flagged_count=already_flagged_count,
    )


def default_cutoff(as_of_dt: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (as_of, cutoff) datetimes for the default 3-day window."""
    as_of = _as_aware(as_of_dt) or now_utc()
    cutoff = as_of - timedelta(days=INACTIVITY_THRESHOLD_DAYS)
    return as_of, cutoff