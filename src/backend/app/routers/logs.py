"""Public audit-log explorer endpoint.

Returns a sanitised projection of `audit_log` rows for the front-end's
ritual-log page. Sensitive metadata (IPs, raw tokens) is filtered out;
actor user IDs are resolved to display_name/email so the feed reads like
the syslog-meets-liturgy footer ticker.

The full event log is exported in the FINAL/ARCHIVED zip — this endpoint
is just the live view.
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/log", tags=["log"])


class LogEntry(BaseModel):
    id: str
    ts: datetime
    actor: str | None = None  # email or display_name; None if system
    actor_id: str | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    summary: str | None = None


class LogPage(BaseModel):
    entries: list[LogEntry]
    total: int
    limit: int
    offset: int


# Keys we will surface verbatim from metadata_json; anything else we omit
# to avoid leaking sensitive fields (IPs, tokens, etc.).
_SAFE_META_KEYS = {
    "from",
    "to",
    "name",
    "title",
    "version",
    "score",
    "status",
    "old_role",
    "new_role",
    "track",
    "phase",
    "method",
    "handle",
    "project",
}


def _summarise(meta_json: str | None) -> str | None:
    if not meta_json:
        return None
    try:
        loaded = json.loads(meta_json)
    except Exception:
        return None
    if not isinstance(loaded, dict):
        return None
    bits = [
        f"{k}={loaded[k]}"
        for k in _SAFE_META_KEYS
        if k in loaded and loaded[k] is not None
    ]
    return " · ".join(bits) if bits else None


@router.get("", response_model=LogPage)
def list_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action_prefix: str | None = Query(
        None, description="e.g. event., user., participant."
    ),
    actor: str | None = Query(
        None,
        description="Filter by actor — matches against user email or display_name",
    ),
    target_type: str | None = Query(None),
    db: Session = Depends(get_db),
) -> LogPage:
    """Public log feed. Only sanitised fields are returned."""
    q = db.query(AuditLog)

    if action_prefix:
        q = q.filter(AuditLog.action.startswith(action_prefix))
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if actor:
        matching_ids = [
            u.id
            for u in db.query(User)
            .filter(
                or_(
                    User.email.ilike(f"%{actor}%"),
                    User.display_name.ilike(f"%{actor}%"),
                )
            )
            .all()
        ]
        if not matching_ids:
            return LogPage(entries=[], total=0, limit=limit, offset=offset)
        q = q.filter(AuditLog.actor_user_id.in_(matching_ids))

    total = q.count()
    rows = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    actor_ids = [r.actor_user_id for r in rows if r.actor_user_id]
    actors_by_id: dict[str, str] = {}
    if actor_ids:
        for u in db.query(User).filter(User.id.in_(actor_ids)).all():
            actors_by_id[u.id] = u.display_name or u.email.split("@")[0]

    entries = [
        LogEntry(
            id=r.id,
            ts=r.created_at,
            actor=actors_by_id.get(r.actor_user_id) if r.actor_user_id else None,
            actor_id=r.actor_user_id,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            summary=_summarise(r.metadata_json),
        )
        for r in rows
    ]
    return LogPage(entries=entries, total=total, limit=limit, offset=offset)
