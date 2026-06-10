"""Schemas for the task queue admin endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: str
    type: str
    ref_id: Optional[str] = None
    status: str
    attempts: int
    max_attempts: int
    last_error: Optional[str] = None
    available_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
