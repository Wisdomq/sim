"""Login-inactivity flag schemas (design §6.10, B-07-01/03)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from simcards_backend.models import AccountFlagType, Role


class AccountFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    user_id: int
    role: Role
    flag_type: AccountFlagType
    flagged_at: datetime
    resolved_at: datetime | None
    acknowledged_by_id: int | None
    last_login_at: datetime | None = None