"""Reusable API dependencies for auth, RBAC, and tenant scoping."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.core.database import get_db, set_tenant_context
from simcards_backend.core.security import decode_token
from simcards_backend.models import AccountStatus, Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    claims = decode_token(token)
    if claims.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(claims["sub"])
    dealer_id = int(claims["dealer_id"])
    set_tenant_context(db, dealer_id)

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.dealer_id == dealer_id,
        )
    )
    if user is None or user.status == AccountStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*roles: Role) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return current_user

    return dependency


require_hq = require_roles(Role.HQ)
require_branch = require_roles(Role.BRANCH)
require_ba = require_roles(Role.BA)
require_hq_or_branch = require_roles(Role.HQ, Role.BRANCH)
