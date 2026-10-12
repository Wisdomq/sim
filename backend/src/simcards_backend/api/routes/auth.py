"""Authentication and dealer-onboarding routes."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.api.dependencies import get_current_user
from simcards_backend.core.database import get_db, set_tenant_context
from simcards_backend.core.security import (
    check_login_rate_limit,
    clear_login_rate_limit,
    create_access_token,
    generate_refresh_token,
    hash_password,
    now_utc,
    token_hash,
    verify_password,
)
from simcards_backend.models import AccountFlag, AccountStatus, LoginEvent, RefreshToken, Role, User
from simcards_backend.schemas.auth import (
    CurrentUserResponse,
    DealerSignupRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from simcards_backend.services.accounts import onboard_dealer

router = APIRouter(tags=["auth"])


def _issue_token_pair(db: Session, user: User) -> TokenResponse:
    access_token, expires_in = create_access_token(user)
    refresh_token = generate_refresh_token()
    refresh_row = RefreshToken(
        dealer_id=user.dealer_id,
        user_id=user.id,
        token_hash=token_hash(refresh_token),
        expires_at=now_utc() + timedelta(days=7),
    )
    db.add(refresh_row)
    db.flush()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/onboarding/dealers", response_model=CurrentUserResponse, status_code=status.HTTP_201_CREATED)
def signup_dealer(payload: DealerSignupRequest, db: Session = Depends(get_db)) -> User:
    _, hq_user = onboard_dealer(
        db,
        dealer_name=payload.dealer_name,
        hq_email=payload.hq_email,
        hq_password=payload.hq_password,
        safaricom_dealer_shortcode=payload.safaricom_dealer_shortcode,
    )
    return hq_user


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    check_login_rate_limit(email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status == AccountStatus.DISABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled.")

    set_tenant_context(db, user.dealer_id)
    clear_login_rate_limit(email)
    if user.role in {Role.BRANCH, Role.BA}:
        db.add(
            LoginEvent(
                dealer_id=user.dealer_id,
                user_id=user.id,
                role=user.role,
                device_info=payload.device_info or {"user_agent": request.headers.get("user-agent")},
            )
        )
        for flag in db.scalars(
            select(AccountFlag).where(
                AccountFlag.dealer_id == user.dealer_id,
                AccountFlag.user_id == user.id,
                AccountFlag.resolved_at.is_(None),
            )
        ):
            flag.resolved_at = now_utc()
        if user.status == AccountStatus.FLAGGED_INACTIVE:
            user.status = AccountStatus.ACTIVE

    token_pair = _issue_token_pair(db, user)
    db.commit()
    return token_pair


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    old_hash = token_hash(payload.refresh_token)
    refresh_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == old_hash))
    if refresh_row is None or refresh_row.revoked_at is not None or refresh_row.expires_at <= now_utc():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(
        select(User).where(
            User.id == refresh_row.user_id,
            User.dealer_id == refresh_row.dealer_id,
        )
    )
    if user is None or user.status == AccountStatus.DISABLED:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active.")

    set_tenant_context(db, user.dealer_id)
    refresh_row.revoked_at = now_utc()
    token_pair = _issue_token_pair(db, user)
    new_hash = token_hash(token_pair.refresh_token)
    new_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == new_hash))
    if new_row is not None:
        refresh_row.replaced_by_id = new_row.id
    db.commit()
    return token_pair


@router.get("/auth/me", response_model=CurrentUserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
