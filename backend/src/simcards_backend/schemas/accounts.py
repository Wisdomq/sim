"""Account-management schemas for branches and brand ambassadors."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from simcards_backend.models import AccountStatus, BranchType


class BranchCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: BranchType
    id_number: str = Field(min_length=1, max_length=128)
    photo_url: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=72)


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    name: str
    type: BranchType
    id_number: str
    photo_url: str
    created_by_id: int | None
    created_at: datetime


class BrandAmbassadorCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=72)
    phone_msisdn: str | None = Field(default=None, max_length=32)
    id_number: str = Field(min_length=1, max_length=128)
    photo_url: str = Field(min_length=1)


class BrandAmbassadorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    branch_id: int
    user_id: int
    name: str
    phone_msisdn: str | None
    id_number: str
    photo_url: str
    status: AccountStatus
    created_by_id: int | None
    created_at: datetime


class PhotoUploadResponse(BaseModel):
    """Response after uploading an identity photo (Branch/BA capture)."""

    photo_url: str
    file_reference: str
