"""Schemas for scoring submissions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScoreCreate(BaseModel):
    """Body for POST /api/submissions/{id}/scores.

    `breakdown` is a free-form per-criterion mapping (criterion → 0..100).
    `score_value` is the weighted/headline number — the judge may compute it
    however they like; the server just stores it. If absent we compute the
    average of the breakdown.
    """

    score_value: Optional[float] = Field(None, ge=0, le=100)
    breakdown: Optional[dict[str, float]] = None
    notes: Optional[str] = None


class ScoreResponse(BaseModel):
    id: str
    submission_id: str
    score_value: float
    breakdown: dict[str, float] = {}
    notes: Optional[str] = None
    status: str
    scorer_version: Optional[str] = None
    scored_at: Optional[datetime] = None
