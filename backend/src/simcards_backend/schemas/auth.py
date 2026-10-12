"""Authentication and onboarding schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from simcards_backend.models import AccountStatus, Role


class LoginRequest(BaseModel):
    email: str
    password: str
    device_info: dict[str, Any] | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class DealerSignupRequest(BaseModel):
    dealer_name: str = Field(min_length=1, max_length=255)
    safaricom_dealer_shortcode: str | None = Field(default=None, max_length=64)
    hq_email: str = Field(min_length=3, max_length=320)
    hq_password: str = Field(min_length=8, max_length=72)


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    role: Role
    email: str
    branch_id: int | None
    ba_profile_id: int | None
    status: AccountStatus
