"""
Admin console aggregations — the operator's view of the ritual.

Read-only roll-ups over the existing tables: a live dashboard, the scoring
status, and a global audit query. These back the `/admin/*` console (the Next.js
UI lands with the frontend foundation); everything here is exercisable now over
the API and without shell access.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.participant import Participant
from app.models.score import Score
from app.models.submission import Submission
from app.scoring import DefaultScorer


def _event(db: Session) -> Event | None:
    return db.get(Event, settings.event_id) or db.query(Event).first()


def _audit_entry(row: AuditLog) -> dict:
    metadata = None
    if row.metadata_json:
        try:
            metadata = json.loads(row.metadata_json)
        except (ValueError, TypeError):
            metadata = None
    return {
        "id": row.id,
        "action": row.action,
        "actor_user_id": row.actor_user_id,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "metadata": metadata,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def dashboard(db: Session, recent_audit: int = 10) -> dict:
    """Live overview: event state, headline metrics, and recent audit entries."""
    event = _event(db)
    eid = settings.event_id

    participants = (
        db.query(Participant).filter(Participant.event_id == eid).all()
    )
    by_type: dict[str, int] = {}
    for p in participants:
        by_type[p.type] = by_type.get(p.type, 0) + 1

    subs_total = (
        db.query(func.count(Submission.id))
        .filter(Submission.event_id == eid)
        .scalar()
    )
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    subs_today = (
        db.query(func.count(Submission.id))
        .filter(Submission.event_id == eid, Submission.created_at >= today)
        .scalar()
    )

    # Queue depth = live submissions with no score yet.
    scored_ids = db.query(Score.submission_id).distinct().subquery()
    queue_depth = (
        db.query(func.count(Submission.id))
        .filter(
            Submission.event_id == eid,
            Submission.status != "withdrawn",
            Submission.id.notin_(db.query(scored_ids.c.submission_id)),
        )
        .scalar()
    )

    active_agents = (
        db.query(func.count(Agent.id)).filter(Agent.status == "active").scalar()
    )

    recent = (
        db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(recent_audit).all()
    )

    return {
        "event": {
            "id": event.id if event else eid,
            "title": event.title if event else settings.event_title,
            "state": event.state if event else "UNKNOWN",
            "start": event.start_at.isoformat() if event and event.start_at else None,
            "end": event.end_at.isoformat() if event and event.end_at else None,
        },
        "metrics": {
            "participants_total": len(participants),
            "participants_by_type": by_type,
            "submissions_total": subs_total or 0,
            "submissions_today": subs_today or 0,
            "scoring_queue_depth": queue_depth or 0,
            "active_agents": active_agents or 0,
        },
        "recent_audit": [_audit_entry(r) for r in recent],
    }


# --------------------------------------------------------------------------- #
# Scoring status
# --------------------------------------------------------------------------- #
_BUCKETS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]


def scoring_status(db: Session) -> dict:
    """Scorer identity, score-status counts, and a score-value histogram."""
    eid = settings.event_id

    rows = (
        db.query(Score.status, func.count(Score.id))
        .join(Submission, Submission.id == Score.submission_id)
        .filter(Submission.event_id == eid)
        .group_by(Score.status)
        .all()
    )
    by_status = {status: count for status, count in rows}

    values = [
        v
        for (v,) in db.query(Score.score_value)
        .join(Submission, Submission.id == Score.submission_id)
        .filter(Submission.event_id == eid, Score.status == "scored")
        .all()
    ]
    distribution = []
    for lo, hi in _BUCKETS:
        # The top bucket is inclusive of the maximum (100).
        n = sum(1 for v in values if lo <= v < hi or (hi == 100 and v == 100))
        distribution.append({"range": f"{lo}-{hi}", "count": n})

    return {
        "scorer": {"type": "python", "version": DefaultScorer().version},
        "counts_by_status": by_status,
        "scored_total": len(values),
        "average_score": round(sum(values) / len(values), 2) if values else None,
        "distribution": distribution,
    }


# --------------------------------------------------------------------------- #
# Global audit query
# --------------------------------------------------------------------------- #
def audit_query(
    db: Session,
    action: str | None = None,
    actor: str | None = None,
    page: int = 1,
    per_page: int = 50,
    since_hours: int | None = None,
) -> dict:
    """Filterable, paginated audit log across all actions."""
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if actor:
        q = q.filter(AuditLog.actor_user_id == actor)
    if since_hours:
        q = q.filter(
            AuditLog.created_at >= datetime.utcnow() - timedelta(hours=since_hours)
        )
    total = q.count()
    rows = (
        q.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    pages = (total + per_page - 1) // per_page
    return {
        "entries": [_audit_entry(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }
