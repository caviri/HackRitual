"""
Audit log service — the record of every consequential act.

Every write that changes authority (role changes, deactivations,
state transitions) must pass through here.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    action: str,
    actor_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Append an entry to the audit log.

    Does not commit — caller owns the transaction.
    """
    from app.models.audit_log import AuditLog

    entry = AuditLog(
        actor_user_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=json.dumps(metadata) if metadata else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    logger.info(
        "audit",
        extra={
            "action": action,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
        },
    )
