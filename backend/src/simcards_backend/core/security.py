"""Password hashing, JWTs, refresh tokens, and login throttling."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from simcards_backend.core.config import settings
from simcards_backend.models import Role, User

_login_attempts: dict[str, list[datetime]] = {}
_password_reset_attempts: dict[str, list[datetime]] = {}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be 72 bytes or fewer when using bcrypt.",
        )
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > 72:
        return False
    return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))


def check_login_rate_limit(email: str) -> None:
    key = email.lower().strip()
    current_time = now_utc()
    window_start = current_time - timedelta(seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    attempts = [attempt for attempt in _login_attempts.get(key, []) if attempt >= window_start]
    if len(attempts) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again shortly.",
        )
    attempts.append(current_time)
    _login_attempts[key] = attempts


def clear_login_rate_limit(email: str) -> None:
    _login_attempts.pop(email.lower().strip(), None)


def check_password_reset_rate_limit(email: str) -> None:
    """Check if email has exceeded password reset rate limit."""
    key = email.lower().strip()
    current_time = now_utc()
    window_start = current_time - timedelta(hours=settings.PASSWORD_RESET_RATE_LIMIT_HOURS)
    attempts = [attempt for attempt in _password_reset_attempts.get(key, []) if attempt >= window_start]
    if len(attempts) >= settings.PASSWORD_RESET_RATE_LIMIT_ATTEMPTS:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset attempts. Try again later.",
        )
    attempts.append(current_time)
    _password_reset_attempts[key] = attempts


def clear_password_reset_rate_limit(email: str) -> None:
    """Clear password reset rate limit for an email."""
    _password_reset_attempts.pop(email.lower().strip(), None)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _user_claims(user: User) -> dict[str, Any]:
    return {
        "sub": str(user.id),
        "dealer_id": user.dealer_id,
        "role": user.role.value if isinstance(user.role, Role) else str(user.role),
        "branch_id": user.branch_id,
        "ba_id": user.ba_profile_id,
    }


def create_access_token(user: User) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = now_utc() + expires_delta
    claims = _user_claims(user)
    claims.update({"type": "access", "exp": expires_at})
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM), int(
        expires_delta.total_seconds()
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
