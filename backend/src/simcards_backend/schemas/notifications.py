"""In-app notification schemas (design §6.10, B-07-02)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from simcards_backend.models import NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dealer_id: int
    user_id: int
    type: NotificationType
    title: str
    body: str | None
    metadata_json: dict[str, Any] | None
    is_read: bool
    created_at: datetime