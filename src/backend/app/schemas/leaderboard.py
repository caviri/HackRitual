"""Schemas for the public leaderboard."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LeaderboardParticipant(BaseModel):
    id: str
    display_name: str
    type: str


class LeaderboardEntry(BaseModel):
    rank: int
    participant: LeaderboardParticipant
    score: float
    submission_count: int
    last_submission_at: Optional[datetime] = None


class LeaderboardResponse(BaseModel):
    event_id: str
    event_state: str
    leaderboard_mode: str
    entries: list[LeaderboardEntry]
