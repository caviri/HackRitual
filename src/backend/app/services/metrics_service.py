"""
Aggregate daily metrics (§14) — counters only, never per-user.

A single row per day in `metrics_daily`, upserted in place. Mutators flush but do
not commit; the caller owns the transaction (so a metric bump rides along with
the action that triggered it). `increment` and `record_scoring_time` are the
write paths; `get_daily` / `totals` are the read side behind the admin dashboard.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.metrics_daily import MetricsDaily

COUNTER_FIELDS = {
    "submissions_count",
    "logins_count",
    "agent_submissions_count",
    "rate_limit_triggered_count",
}


def _today() -> str:
    return date.today().isoformat()


def _row(db: Session, day: str | None = None) -> MetricsDaily:
    day = day or _today()
    row = db.get(MetricsDaily, day)
    if row is None:
        row = MetricsDaily(date=day)
        db.add(row)
        db.flush()
    return row


def increment(db: Session, metric: str, value: int = 1) -> None:
    """Bump a daily counter (flush-only; caller commits)."""
    if metric not in COUNTER_FIELDS:
        raise ValueError(f"unknown metric '{metric}'")
    row = _row(db)
    setattr(row, metric, getattr(row, metric) + value)
    db.flush()


def record_scoring_time(db: Session, duration_ms: float) -> None:
    """Fold a scoring duration into today's running average and max."""
    row = _row(db)
    n = row.scoring_count
    row.scoring_avg_ms = (row.scoring_avg_ms * n + duration_ms) / (n + 1)
    row.scoring_max_ms = max(row.scoring_max_ms, duration_ms)
    row.scoring_count = n + 1
    db.flush()


def _as_dict(row: MetricsDaily) -> dict:
    return {
        "date": row.date,
        "submissions": row.submissions_count,
        "logins": row.logins_count,
        "agent_submissions": row.agent_submissions_count,
        "rate_limits_triggered": row.rate_limit_triggered_count,
        "scoring_avg_ms": round(row.scoring_avg_ms, 1),
        "scoring_max_ms": round(row.scoring_max_ms, 1),
    }


def get_daily(db: Session, start: str | None = None, end: str | None = None) -> list[dict]:
    q = db.query(MetricsDaily)
    if start:
        q = q.filter(MetricsDaily.date >= start)
    if end:
        q = q.filter(MetricsDaily.date <= end)
    return [_as_dict(r) for r in q.order_by(MetricsDaily.date).all()]


def totals(db: Session) -> dict:
    from app.models.agent import Agent
    from app.models.participant import Participant
    from app.models.submission import Submission

    eid = settings.event_id
    parts = (
        db.query(Participant.type, func.count(Participant.id))
        .filter(Participant.event_id == eid)
        .group_by(Participant.type)
        .all()
    )
    by_type = {t: n for t, n in parts}
    return {
        "participants": sum(by_type.values()),
        "teams": by_type.get("team", 0),
        "agents": db.query(func.count(Agent.id)).scalar() or 0,
        "submissions": (
            db.query(func.count(Submission.id))
            .filter(Submission.event_id == eid)
            .scalar()
            or 0
        ),
    }
