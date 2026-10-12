"""Service for password reset functionality."""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from simcards_backend.core.config import settings
from simcards_backend.core.security import hash_password
from simcards_backend.models import PasswordResetToken, User
from simcards_backend.services.email import email_service

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service for managing password reset tokens and resets."""

    @staticmethod
    def generate_token() -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def get_token_expiry() -> datetime:
        """Get token expiration datetime."""
        return datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)

    def create_reset_token(
        self,
        db: Session,
        user: User,
    ) -> str:
        """
        Create a password reset token for a user.

        Args:
            db: Database session
            user: User to create token for

        Returns:
            The generated token
        """
        token = self.generate_token()
        expires_at = self.get_token_expiry()

        # Invalidate any existing unused tokens for this user
        db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > datetime.utcnow(),
            )
        )
        # Note: We don't actually invalidate them, just create a new one
        # The old tokens will still work until they expire or are used

        # Create new token
        reset_token = PasswordResetToken(
            user_id=user.id,
            dealer_id=user.dealer_id,
            token=token,
            expires_at=expires_at,
        )
        db.add(reset_token)
        db.commit()

        return token

    def validate_token(
        self,
        db: Session,
        token: str,
    ) -> Optional[PasswordResetToken]:
        """
        Validate a password reset token.

        Args:
            db: Database session
            token: Token to validate

        Returns:
            PasswordResetToken if valid, None otherwise
        """
        result = db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token == token,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > datetime.utcnow(),
            )
        )
        return result.scalar_one_or_none()

    def reset_password(
        self,
        db: Session,
        token: str,
        new_password: str,
    ) -> bool:
        """
        Reset user password using a valid token.

        Args:
            db: Database session
            token: Password reset token
            new_password: New password to set

        Returns:
            True if password reset successful, False otherwise
        """
        # Validate token
        reset_token = self.validate_token(db, token)
        if not reset_token:
            return False

        # Get user
        result = db.execute(
            select(User).where(User.id == reset_token.user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False

        # Update password
        user.password_hash = hash_password(new_password)

        # Mark token as used
        reset_token.used_at = datetime.utcnow()

        # Revoke all refresh tokens for this user (invalidate all sessions)
        from simcards_backend.models import RefreshToken
        db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        # Actually revoke them
        revoke_result = db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for refresh_token in revoke_result.scalars():
            refresh_token.revoked_at = datetime.utcnow()

        db.commit()
        return True

    def initiate_password_reset(
        self,
        db: Session,
        email: str,
    ) -> bool:
        """
        Initiate password reset process for an email.

        Args:
            db: Database session
            email: User's email address

        Returns:
            True if reset initiated (email exists), False otherwise
        """
        # Check rate limit
        from simcards_backend.core.security import check_password_reset_rate_limit
        check_password_reset_rate_limit(email)

        # Find user by email
        result = db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Don't reveal if email exists - return True anyway
            return True

        # Create reset token
        token = self.create_reset_token(db, user)

        # Send email
        # Note: For user name, we could use BA name or branch name if available
        # For now, use email as fallback
        user_name = email.split("@")[0]
        email_sent = email_service.send_password_reset_email(
            to_email=email,
            user_name=user_name,
            reset_token=token,
        )

        if not email_sent:
            logger.warning(f"Failed to send password reset email to {email}")
            # Still return True to prevent email enumeration

        return True


# Global service instance
password_reset_service = PasswordResetService()
