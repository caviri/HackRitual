"""Admin task-queue monitoring (Step 14)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.user import User
from app.schemas.queue import TaskResponse
from app.services import task_queue


admin_queue_router = APIRouter(prefix="/api/admin/queue", tags=["queue"])


@admin_queue_router.get("/status")
def queue_status(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Queue overview: counts by status, recent throughput, and a per-type breakdown."""
    return task_queue.status_summary(db)


@admin_queue_router.get("/failed", response_model=list[TaskResponse])
def queue_failed(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[TaskResponse]:
    """Dead tasks (exhausted their attempts)."""
    return [TaskResponse.model_validate(t) for t in task_queue.list_failed(db, limit)]


@admin_queue_router.post("/{task_id}/retry", response_model=TaskResponse)
def queue_retry(
    task_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> TaskResponse:
    """Resurrect a dead task — back to queued with attempts reset."""
    task = task_queue.retry_task(db, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return TaskResponse.model_validate(task)


@admin_queue_router.post("/purge")
def queue_purge(
    older_than_hours: int = Query(24, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Delete completed (`done`) tasks older than the threshold."""
    return {"purged": task_queue.purge_done(db, older_than_hours)}
