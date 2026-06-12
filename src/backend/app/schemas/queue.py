"""Schemas for the task queue admin endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: str
    type: str
    ref_id: str | None = None
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None = None
    available_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
