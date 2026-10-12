"""Audit-log write helpers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from simcards_backend.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    dealer_id: int,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        dealer_id=dealer_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
    )
    db.add(audit_log)
    return audit_log
