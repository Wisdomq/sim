"""Tenant onboarding and account-management services."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.core.config import settings
from simcards_backend.core.database import set_tenant_context
from simcards_backend.core.security import hash_password
from simcards_backend.models import (
    AccountStatus,
    Branch,
    BranchType,
    BrandAmbassador,
    Dealer,
    Role,
    User,
)
from simcards_backend.services.audit import write_audit_log

_ALLOWED_PHOTO_MIME: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _ensure_required_identity(id_number: str, photo_url: str) -> None:
    if not id_number.strip() or not photo_url.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ID number and current photo are required.",
        )


def _ensure_email_available(db: Session, email: str) -> None:
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )


def onboard_dealer(
    db: Session,
    *,
    dealer_name: str,
    hq_email: str,
    hq_password: str,
    safaricom_dealer_shortcode: str | None = None,
) -> tuple[Dealer, User]:
    email = _normalize_email(hq_email)
    _ensure_email_available(db, email)

    dealer = Dealer(
        name=dealer_name.strip(),
        safaricom_dealer_shortcode=safaricom_dealer_shortcode.strip()
        if safaricom_dealer_shortcode
        else None,
    )
    db.add(dealer)
    db.flush()
    set_tenant_context(db, dealer.id)

    hq_user = User(
        dealer_id=dealer.id,
        role=Role.HQ,
        email=email,
        password_hash=hash_password(hq_password),
        status=AccountStatus.ACTIVE,
    )
    db.add(hq_user)
    db.flush()
    write_audit_log(
        db,
        dealer_id=dealer.id,
        actor_user_id=hq_user.id,
        action="DEALER_ONBOARDED",
        entity_type="Dealer",
        entity_id=dealer.id,
        metadata={"hq_user_id": hq_user.id},
    )
    db.commit()
    db.refresh(dealer)
    db.refresh(hq_user)
    return dealer, hq_user


def create_branch_account(
    db: Session,
    *,
    actor: User,
    name: str,
    branch_type: BranchType,
    id_number: str,
    photo_url: str,
    email: str,
    password: str,
) -> Branch:
    _ensure_required_identity(id_number, photo_url)
    normalized_email = _normalize_email(email)
    _ensure_email_available(db, normalized_email)

    branch = Branch(
        dealer_id=actor.dealer_id,
        name=name.strip(),
        type=branch_type,
        id_number=id_number.strip(),
        photo_url=photo_url.strip(),
        created_by_id=actor.id,
    )
    db.add(branch)
    db.flush()

    branch_user = User(
        dealer_id=actor.dealer_id,
        role=Role.BRANCH,
        email=normalized_email,
        password_hash=hash_password(password),
        branch_id=branch.id,
        status=AccountStatus.ACTIVE,
    )
    db.add(branch_user)
    db.flush()
    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="BRANCH_CREATED",
        entity_type="Branch",
        entity_id=branch.id,
        metadata={"branch_user_id": branch_user.id},
    )
    db.commit()
    db.refresh(branch)
    return branch


def list_branches(db: Session, *, actor: User) -> list[Branch]:
    if actor.role == Role.HQ:
        return list(
            db.scalars(select(Branch).where(Branch.dealer_id == actor.dealer_id).order_by(Branch.id))
        )
    if actor.role == Role.BRANCH and actor.branch_id is not None:
        branch = db.scalar(
            select(Branch).where(
                Branch.dealer_id == actor.dealer_id,
                Branch.id == actor.branch_id,
            )
        )
        return [branch] if branch else []
    return []


def remove_branch_account(db: Session, *, actor: User, branch_id: int) -> None:
    branch = db.scalar(
        select(Branch).where(Branch.dealer_id == actor.dealer_id, Branch.id == branch_id)
    )
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found.")

    branch_users = db.scalars(
        select(User).where(
            User.dealer_id == actor.dealer_id,
            User.role == Role.BRANCH,
            User.branch_id == branch_id,
        )
    ).all()
    for user in branch_users:
        user.status = AccountStatus.DISABLED

    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="BRANCH_REMOVED",
        entity_type="Branch",
        entity_id=branch_id,
        metadata={"disabled_user_ids": [user.id for user in branch_users]},
    )
    db.commit()


def _get_branch_for_actor(db: Session, *, actor: User, branch_id: int) -> Branch:
    branch = db.scalar(
        select(Branch).where(Branch.dealer_id == actor.dealer_id, Branch.id == branch_id)
    )
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found.")
    if actor.role == Role.BRANCH and actor.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Branch users can only manage their own branch.",
        )
    return branch


def create_brand_ambassador_account(
    db: Session,
    *,
    actor: User,
    branch_id: int,
    name: str,
    email: str,
    password: str,
    phone_msisdn: str | None,
    id_number: str,
    photo_url: str,
) -> BrandAmbassador:
    _ensure_required_identity(id_number, photo_url)
    _get_branch_for_actor(db, actor=actor, branch_id=branch_id)
    normalized_email = _normalize_email(email)
    _ensure_email_available(db, normalized_email)

    ba_user = User(
        dealer_id=actor.dealer_id,
        role=Role.BA,
        email=normalized_email,
        password_hash=hash_password(password),
        branch_id=branch_id,
        status=AccountStatus.ACTIVE,
    )
    db.add(ba_user)
    db.flush()

    ba = BrandAmbassador(
        dealer_id=actor.dealer_id,
        branch_id=branch_id,
        user_id=ba_user.id,
        name=name.strip(),
        phone_msisdn=phone_msisdn.strip() if phone_msisdn else None,
        id_number=id_number.strip(),
        photo_url=photo_url.strip(),
        status=AccountStatus.ACTIVE,
        created_by_id=actor.id,
    )
    db.add(ba)
    db.flush()
    ba_user.ba_profile_id = ba.id
    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="BA_CREATED",
        entity_type="BrandAmbassador",
        entity_id=ba.id,
        metadata={"ba_user_id": ba_user.id, "branch_id": branch_id},
    )
    db.commit()
    db.refresh(ba)
    return ba


def list_brand_ambassadors(
    db: Session,
    *,
    actor: User,
    branch_id: int | None = None,
) -> list[BrandAmbassador]:
    query = select(BrandAmbassador).where(BrandAmbassador.dealer_id == actor.dealer_id)
    if actor.role == Role.BRANCH:
        query = query.where(BrandAmbassador.branch_id == actor.branch_id)
    elif branch_id is not None:
        query = query.where(BrandAmbassador.branch_id == branch_id)
    return list(db.scalars(query.order_by(BrandAmbassador.id)))


def get_brand_ambassador(
    db: Session,
    *,
    actor: User,
    ba_id: int,
) -> BrandAmbassador:
    """Fetch a single brand ambassador scoped to the actor's tenant and branch."""
    query = select(BrandAmbassador).where(
        BrandAmbassador.dealer_id == actor.dealer_id,
        BrandAmbassador.id == ba_id,
    )
    if actor.role == Role.BRANCH:
        query = query.where(BrandAmbassador.branch_id == actor.branch_id)
    ba = db.scalar(query)
    if ba is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand ambassador not found.",
        )
    return ba


def remove_brand_ambassador_account(db: Session, *, actor: User, ba_id: int) -> None:
    ba = db.scalar(
        select(BrandAmbassador).where(
            BrandAmbassador.dealer_id == actor.dealer_id,
            BrandAmbassador.id == ba_id,
        )
    )
    if ba is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand ambassador not found.")

    ba.status = AccountStatus.DISABLED
    ba_user = db.get(User, ba.user_id)
    if ba_user is not None and ba_user.dealer_id == actor.dealer_id:
        ba_user.status = AccountStatus.DISABLED
    write_audit_log(
        db,
        dealer_id=actor.dealer_id,
        actor_user_id=actor.id,
        action="BA_REMOVED",
        entity_type="BrandAmbassador",
        entity_id=ba.id,
        metadata={"ba_user_id": ba.user_id, "branch_id": ba.branch_id},
    )
    db.commit()


def photo_dir_for(dealer_id: int) -> Path:
    """Dealer-scoped directory for identity photos."""
    return Path(settings.UPLOAD_DIR) / "photos" / str(dealer_id)


def save_uploaded_photo(*, actor: User, file: UploadFile) -> tuple[str, str]:
    """Persist an uploaded identity photo and return (api_url, file_reference).

    The returned ``photo_url`` is an API path (authorized GET) so raw files are
    never exposed without authentication; ``file_reference`` is the on-disk path.
    """
    ext = _ALLOWED_PHOTO_MIME.get((file.content_type or "").lower())
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Photo must be a PNG, JPEG, or WebP image.",
        )

    photo_dir = photo_dir_for(actor.dealer_id)
    photo_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    target = photo_dir / filename
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    photo_url = f"/api/v1/uploads/photo/{filename}"
    return photo_url, str(target)


def resolve_photo(*, dealer_id: int, filename: str) -> Path | None:
    """Resolve a stored photo filename to its on-disk path (name safe)."""
    safe_name = Path(filename).name
    if safe_name != filename:
        return None
    candidate = photo_dir_for(dealer_id) / safe_name
    if not candidate.is_file():
        return None
    return candidate
