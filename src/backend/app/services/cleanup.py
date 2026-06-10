"""
Data-retention cleanup (§14.12).

Purges short-lived data that has aged out: any DB-backed sessions past their
expiry. Run periodically from the lifespan.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel


def cleanup_expired_data(db: Session) -> dict:
    """Delete expired sessions. Returns counts removed."""
    now = datetime.now(UTC)
    sessions = (
        db.query(SessionModel).filter(SessionModel.expires_at <= now).delete()
    )
    db.commit()
    return {"sessions": sessions}
