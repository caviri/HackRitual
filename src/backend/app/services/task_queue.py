"""
A poor man's task queue — SQLite-backed, in-process, retryable.

No Redis, no broker: the `tasks` table is the queue and a single worker (see
`worker.py`) drains it. This module owns the persistence and state-machine —
enqueue, claim, complete, fail-with-backoff, stale recovery — and the read-side
summaries the admin queue endpoints expose.

Task lifecycle::

    queued → running → done
                ↘ (error, attempts < max) → queued  (exponential backoff)
                ↘ (error, attempts ≥ max) → dead
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.task import Task

TASK_TYPES = ("score_submission", "export_bundle", "push_github")


def enqueue(
    db: Session,
    task_type: str,
    ref_id: Optional[str] = None,
    payload: Optional[dict] = None,
    delay_seconds: int = 0,
    max_attempts: int = 3,
) -> Task:
    """Add a task to the queue. Commits."""
    now = datetime.utcnow()
    task = Task(
        type=task_type,
        ref_id=ref_id,
        payload_json=json.dumps(payload) if payload is not None else None,
        status="queued",
        attempts=0,
        max_attempts=max_attempts,
        available_at=now + timedelta(seconds=delay_seconds),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def claim_next(db: Session, now: Optional[datetime] = None) -> Optional[Task]:
    """
    Claim the oldest due `queued` task, flipping it to `running`.

    Single-worker model (per spec): WAL + busy_timeout make this safe enough
    without row locks. Increments `attempts` as it claims.
    """
    now = now or datetime.utcnow()
    task = (
        db.query(Task)
        .filter(Task.status == "queued", Task.available_at <= now)
        .order_by(Task.available_at.asc(), Task.created_at.asc())
        .first()
    )
    if task is None:
        return None
    task.status = "running"
    task.attempts += 1
    task.started_at = now
    task.updated_at = now
    db.commit()
    db.refresh(task)
    return task


def mark_done(db: Session, task: Task) -> None:
    now = datetime.utcnow()
    task.status = "done"
    task.completed_at = now
    task.updated_at = now
    db.commit()


def mark_failed(db: Session, task: Task, error: str) -> None:
    """Record a failure: back off and re-queue, or bury as `dead` at the ceiling."""
    now = datetime.utcnow()
    task.last_error = (error or "")[:1000]
    if task.attempts >= task.max_attempts:
        task.status = "dead"
        task.completed_at = now
    else:
        task.status = "queued"
        # Exponential backoff: 30s, 120s, 480s, …
        delay = 30 * (4 ** (task.attempts - 1))
        task.available_at = now + timedelta(seconds=delay)
    task.updated_at = now
    db.commit()


def recover_stale(db: Session) -> int:
    """Reset tasks stuck in `running` (e.g. a container restart) back to queued."""
    stale = db.query(Task).filter(Task.status == "running").all()
    now = datetime.utcnow()
    for task in stale:
        task.status = "queued"
        task.updated_at = now
    db.commit()
    return len(stale)


# --------------------------------------------------------------------------- #
# Read-side (admin monitoring)
# --------------------------------------------------------------------------- #
def status_summary(db: Session) -> dict:
    since = datetime.utcnow() - timedelta(hours=1)
    counts = {
        s: n
        for s, n in db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    }
    done_last_hour = (
        db.query(func.count(Task.id))
        .filter(Task.status == "done", Task.completed_at >= since)
        .scalar()
    )
    failed_last_hour = (
        db.query(func.count(Task.id))
        .filter(Task.status == "dead", Task.completed_at >= since)
        .scalar()
    )
    by_type: dict[str, dict[str, int]] = {}
    for ttype, sstatus, n in (
        db.query(Task.type, Task.status, func.count(Task.id))
        .group_by(Task.type, Task.status)
        .all()
    ):
        by_type.setdefault(ttype, {})[sstatus] = n
    return {
        "queued": counts.get("queued", 0),
        "running": counts.get("running", 0),
        "done": counts.get("done", 0),
        "dead": counts.get("dead", 0),
        "done_last_hour": done_last_hour or 0,
        "failed_last_hour": failed_last_hour or 0,
        "by_type": by_type,
    }


def list_failed(db: Session, limit: int = 50) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.status == "dead")
        .order_by(Task.updated_at.desc())
        .limit(limit)
        .all()
    )


def retry_task(db: Session, task_id: str) -> Optional[Task]:
    """Resurrect a dead task: back to queued, attempts reset, available now."""
    task = db.get(Task, task_id)
    if task is None:
        return None
    task.status = "queued"
    task.attempts = 0
    task.available_at = datetime.utcnow()
    task.started_at = None
    task.completed_at = None
    task.last_error = None
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def purge_done(db: Session, older_than_hours: int = 24) -> int:
    """Delete `done` tasks older than the threshold. Returns the count removed."""
    cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
    rows = (
        db.query(Task)
        .filter(Task.status == "done", Task.completed_at < cutoff)
        .all()
    )
    for task in rows:
        db.delete(task)
    db.commit()
    return len(rows)
