"""API routes for password reset functionality."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from simcards_backend.api.dependencies import get_db
from simcards_backend.schemas.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ValidateResetTokenRequest,
    ValidateResetTokenResponse,
)
from simcards_backend.services.password_reset import password_reset_service

router = APIRouter(prefix="/auth", tags=["password-reset"])


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """
    Initiate password reset process.

    This endpoint always returns success to prevent email enumeration.
    If the email exists, a reset link will be sent.
    """
    password_reset_service.initiate_password_reset(db, request.email)
    return ForgotPasswordResponse()


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> ResetPasswordResponse:
    """
    Reset password using a valid token.

    Raises:
        HTTPException: If token is invalid or expired
    """
    success = password_reset_service.reset_password(
        db,
        request.token,
        request.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return ResetPasswordResponse()


@router.post(
    "/validate-reset-token",
    response_model=ValidateResetTokenResponse,
    status_code=status.HTTP_200_OK,
)
def validate_reset_token(
    request: ValidateResetTokenRequest,
    db: Session = Depends(get_db),
) -> ValidateResetTokenResponse:
    """
    Validate a password reset token.

    Returns token validity and expiration time.
    """
    reset_token = password_reset_service.validate_token(db, request.token)

    if not reset_token:
        return ValidateResetTokenResponse(valid=False, expires_at=None)

    return ValidateResetTokenResponse(
        valid=True,
        expires_at=reset_token.expires_at.isoformat(),
    )
