"""Schemas for password reset functionality."""

from pydantic import BaseModel, EmailStr, Field, field_validator


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password."""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Response schema for forgot password."""

    message: str = "If the email exists, a reset link has been sent"


class ResetPasswordRequest(BaseModel):
    """Request schema for password reset."""

    token: str = Field(..., min_length=32, description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class ResetPasswordResponse(BaseModel):
    """Response schema for password reset."""

    message: str = "Password has been reset successfully"


class ValidateResetTokenRequest(BaseModel):
    """Request schema for validating reset token."""

    token: str = Field(..., min_length=32, description="Password reset token")


class ValidateResetTokenResponse(BaseModel):
    """Response schema for validating reset token."""

    valid: bool
    expires_at: str | None = None
