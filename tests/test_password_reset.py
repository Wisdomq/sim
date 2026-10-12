"""Tests for password reset functionality."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from simcards_backend.models import PasswordResetToken, RefreshToken, User
from simcards_backend.services.password_reset import password_reset_service
from simcards_backend.core.security import (
    check_password_reset_rate_limit,
    clear_password_reset_rate_limit,
)


@pytest.fixture(autouse=True)
def clear_rate_limits():
    """Clear rate limits before each test."""
    yield
    # Clear all rate limits after each test
    for suffix in ["valid", "rate", "validate", "expired", "used", "reset", "weak", "sessions", "strength", "test"]:
        try:
            clear_password_reset_rate_limit(f"hq-{suffix}@example.com")
        except:
            pass


def _signup_hq(client, email_suffix="test"):
    """Helper to create HQ user and return token."""
    response = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "Test Dealer",
            "safaricom_dealer_shortcode": f"TEST{email_suffix}",
            "hq_email": f"hq-{email_suffix}@example.com",
            "hq_password": "OldPassword123!",
        },
    )
    assert response.status_code == 201
    return response.json()


def _login(client, email, password):
    """Helper to login and return token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_forgot_password_with_valid_email(client, db_session):
    """Test forgot password with a valid email creates a token."""
    user_data = _signup_hq(client, "valid")
    email = user_data["email"]

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )

    # Always returns 200 to prevent email enumeration
    assert response.status_code == 200
    assert response.json() == {"message": "If the email exists, a reset link has been sent"}

    # Verify token was created in database
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None

    tokens = db_session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    ).scalars().all()

    assert len(tokens) == 1
    assert tokens[0].token is not None
    assert tokens[0].expires_at > datetime.utcnow()


def test_forgot_password_with_invalid_email(client):
    """Test forgot password with invalid email returns success (email enumeration prevention)."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"},
    )

    # Always returns 200 to prevent email enumeration
    assert response.status_code == 200
    assert response.json() == {"message": "If the email exists, a reset link has been sent"}


def test_forgot_password_rate_limiting(client):
    """Test forgot password rate limiting (3 attempts per hour)."""
    user_data = _signup_hq(client, "rate")
    email = user_data["email"]

    # First 3 attempts should succeed
    for _ in range(3):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
        )
        assert response.status_code == 200

    # 4th attempt should be rate limited
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )
    assert response.status_code == 429
    assert "Too many password reset attempts" in response.json()["detail"]


def test_validate_reset_token_valid(client, db_session):
    """Test validating a valid reset token."""
    user_data = _signup_hq(client, "validate")
    email = user_data["email"]

    # Create token
    client.post("/api/v1/auth/forgot-password", json={"email": email})

    # Get token from database
    user = db_session.scalar(select(User).where(User.email == email))
    token = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )

    response = client.post(
        "/api/v1/auth/validate-reset-token",
        json={"token": token.token},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["expires_at"] is not None


def test_validate_reset_token_invalid(client):
    """Test validating an invalid reset token."""
    response = client.post(
        "/api/v1/auth/validate-reset-token",
        json={"token": "invalid_token_123456789012345678901234567890"},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["expires_at"] is None


def test_validate_reset_token_expired(client, db_session):
    """Test validating an expired reset token."""
    user_data = _signup_hq(client, "expired")
    email = user_data["email"]

    # Create token
    client.post("/api/v1/auth/forgot-password", json={"email": email})

    # Get token and manually expire it
    user = db_session.scalar(select(User).where(User.email == email))
    token = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    token.expires_at = datetime.utcnow() - timedelta(hours=1)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/validate-reset-token",
        json={"token": token.token},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_validate_reset_token_already_used(client, db_session):
    """Test validating a token that has already been used."""
    user_data = _signup_hq(client, "used")
    email = user_data["email"]

    # Create token
    client.post("/api/v1/auth/forgot-password", json={"email": email})

    # Get token and mark as used
    user = db_session.scalar(select(User).where(User.email == email))
    token = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    token.used_at = datetime.utcnow()
    db_session.commit()

    response = client.post(
        "/api/v1/auth/validate-reset-token",
        json={"token": token.token},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_reset_password_with_valid_token(client, db_session):
    """Test resetting password with a valid token."""
    user_data = _signup_hq(client, "reset")
    email = user_data["email"]
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"

    # Create token
    client.post("/api/v1/auth/forgot-password", json={"email": email})

    # Get token from database
    user = db_session.scalar(select(User).where(User.email == email))
    token = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token.token,
            "new_password": new_password,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password has been reset successfully"}

    # Verify old password no longer works
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert login_response.status_code == 401

    # Verify new password works
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert login_response.status_code == 200

    # Verify token was marked as used
    db_session.refresh(token)
    assert token.used_at is not None


def test_reset_password_invalid_token(client):
    """Test resetting password with an invalid token."""
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "invalid_token_123456789012345678901234567890",
            "new_password": "NewPassword456!",
        },
    )

    assert response.status_code == 400
    assert "Invalid or expired reset token" in response.json()["detail"]


def test_reset_password_weak_password(client, db_session):
    """Test resetting password with weak password fails validation."""
    user_data = _signup_hq(client, "weak")
    email = user_data["email"]

    # Create token
    client.post("/api/v1/auth/forgot-password", json={"email": email})

    # Get token from database
    user = db_session.scalar(select(User).where(User.email == email))
    token = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )

    # Test weak passwords
    weak_passwords = [
        "short",  # Too short
        "nouppercase123!",  # No uppercase
        "NOLOWERCASE123!",  # No lowercase
        "NoNumbers!",  # No numbers
        "NoSpecialChars123",  # No special character
    ]

    for weak_pwd in weak_passwords:
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token.token,
                "new_password": weak_pwd,
            },
        )
        assert response.status_code == 422


def test_reset_password_invalidates_sessions(client, db_session):
    """Test that password reset invalidates all refresh tokens."""
    user_data = _signup_hq(client, "sessions")
    email = user_data["email"]

    # Login to create refresh token
    token = _login(client, email, "OldPassword123!")

    # Create reset token
    client.post("/api/v1/auth/forgot-password", json={"email": email})

    # Get reset token from database
    user = db_session.scalar(select(User).where(User.email == email))
    reset_token = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )

    # Reset password
    client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token.token,
            "new_password": "NewPassword456!",
        },
    )

    # Verify all refresh tokens were revoked
    refresh_tokens = db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    ).scalars().all()

    assert len(refresh_tokens) == 0


def test_password_reset_rate_limit_service():
    """Test password reset rate limiting service."""
    email = "test@example.com"

    # First 3 attempts should pass
    for _ in range(3):
        check_password_reset_rate_limit(email)

    # 4th attempt should raise
    with pytest.raises(Exception) as exc_info:
        check_password_reset_rate_limit(email)
    assert "Too many password reset attempts" in str(exc_info.value)

    # Clear rate limit
    clear_password_reset_rate_limit(email)

    # Should work again after clearing
    check_password_reset_rate_limit(email)


def test_token_generation_uniqueness():
    """Test that generated tokens are unique."""
    tokens = []
    for _ in range(10):
        token = password_reset_service.generate_token()
        tokens.append(token)
    
    # All tokens should be unique
    assert len(set(tokens)) == 10


def test_token_expiry_calculation():
    """Test token expiry calculation."""
    from simcards_backend.core.config import settings
    
    expiry = password_reset_service.get_token_expiry()
    expected_expiry = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    
    # Allow 1 second difference
    assert abs((expiry - expected_expiry).total_seconds()) < 1


def test_password_strength_validation(client, db_session):
    """Test password strength validation through API."""
    user_data = _signup_hq(client, "strength")
    email = user_data["email"]

    # Create token
    client.post("/api/v1/auth/forgot-password", json={"email": email})

    # Get token from database
    user = db_session.scalar(select(User).where(User.email == email))
    token = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )

    # Valid password
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token.token,
            "new_password": "ValidPassword123!",
        },
    )
    assert response.status_code == 200
