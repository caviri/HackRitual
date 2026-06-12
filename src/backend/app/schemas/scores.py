"""Schemas for scoring submissions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ScoreCreate(BaseModel):
    """Body for POST /api/submissions/{id}/scores.

    `breakdown` is a free-form per-criterion mapping (criterion → 0..100).
    `score_value` is the weighted/headline number — the judge may compute it
    however they like; the server just stores it. If absent we compute the
    average of the breakdown.
    """

    score_value: float | None = Field(None, ge=0, le=100)
    breakdown: dict[str, float] | None = None
    notes: str | None = None


class ScoreResponse(BaseModel):
    id: str
    submission_id: str
    score_value: float
    breakdown: dict[str, float] = {}
    notes: str | None = None
    status: str
    scorer_version: str | None = None
    scored_at: datetime | None = None


class ScoreOverride(BaseModel):
    """Admin manual override of a score (Step 08), recorded in the audit log."""

    score_value: float | None = Field(None, ge=0, le=100)
    status: str | None = None  # scored | failed | disqualified
    reason: str | None = None
