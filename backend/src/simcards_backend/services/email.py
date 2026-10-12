"""Email service for sending password reset emails."""

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from simcards_backend.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM
        self.use_tls = settings.SMTP_USE_TLS

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_user and self.smtp_password)

    def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_token: str,
    ) -> bool:
        """
        Send password reset email to user.

        Args:
            to_email: Recipient email address
            user_name: User's name for personalization
            reset_token: Password reset token

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email service not configured - skipping email send")
            return False

        try:
            # Create reset link
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

            # Create email message
            msg = EmailMessage()
            msg["From"] = self.smtp_from
            msg["To"] = to_email
            msg["Subject"] = "Reset Your SIM Cards Password"

            # Email body
            body = f"""Hello {user_name},

You requested a password reset for your SIM Cards account.

Click the link below to reset your password:
{reset_link}

This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hour(s).

If you did not request this password reset, please ignore this email.

Best regards,
SIM Cards Team
"""
            msg.set_content(body)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Password reset email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {e}")
            return False


# Global email service instance
email_service = EmailService()
