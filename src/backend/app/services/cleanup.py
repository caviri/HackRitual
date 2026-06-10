"""
Data-retention cleanup (§14.12).

Purges short-lived data that has aged out: login codes (10-minute TTL) and any
DB-backed sessions past their expiry. Run periodically from the lifespan.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel
from app.services.auth import cleanup_expired_codes


def cleanup_expired_data(db: Session) -> dict:
    """Delete expired login codes and sessions. Returns counts removed."""
    codes = cleanup_expired_codes(db)  # commits internally
    now = datetime.now(timezone.utc)
    sessions = (
        db.query(SessionModel).filter(SessionModel.expires_at <= now).delete()
    )
    db.commit()
    return {"login_codes": codes, "sessions": sessions}
