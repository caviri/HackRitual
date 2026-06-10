"""Pydantic schemas for the singleton Event: state, config, and transitions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventState = Literal["DRAFT", "OPEN", "FROZEN", "FINAL", "ARCHIVED"]
LeaderboardMode = Literal["best", "latest"]
AgentPolicy = Literal["allowed", "forbidden"]


class Track(BaseModel):
    """A submission track within the event."""

    id: str
    name: str
    description: str = ""


class EventConfig(BaseModel):
    """The configurable rules of the ritual, stored as JSON on the Event."""

    registration_open: bool = True
    submission_limit_per_participant: int = 10
    submission_limit_window_hours: int = 24
    leaderboard_mode: LeaderboardMode = "best"
    agent_policy: AgentPolicy = "allowed"
    auto_score: bool = True
    tracks: list[Track] = Field(default_factory=list)


class EventResponse(BaseModel):
    """Public view of the event the container is hosting."""

    id: str
    title: str
    type: str
    state: EventState
    start: datetime
    end: datetime
    config: EventConfig


class StateTransitionRequest(BaseModel):
    """Admin request to advance (or reopen) the event's state machine."""

    state: EventState = Field(..., description="Target state")
    reason: str | None = Field(
        None, description="Why the ritual is advancing — recorded in the audit log"
    )
    confirm: bool = Field(
        False,
        description="Required for the FROZEN→OPEN reopen, which undoes a closing",
    )


class StateTransitionResponse(BaseModel):
    """Result of a successful state transition."""

    id: str
    state: EventState
    previous_state: EventState
    transitioned_at: datetime
    transitioned_by: str


class EventMetaUpdate(BaseModel):
    """Partial update of the event's identity — title, type, dates.

    These start as env-var placeholders; the admin panel owns them afterwards.
    """

    title: str | None = Field(None, min_length=1, max_length=200)
    type: str | None = Field(None, min_length=1, max_length=50)
    start: datetime | None = None
    end: datetime | None = None


class EventConfigUpdate(BaseModel):
    """Partial update of event configuration. Only set fields are changed."""

    registration_open: bool | None = None
    submission_limit_per_participant: int | None = Field(None, ge=1)
    submission_limit_window_hours: int | None = Field(None, ge=1)
    leaderboard_mode: LeaderboardMode | None = None
    agent_policy: AgentPolicy | None = None
    auto_score: bool | None = None
    tracks: list[Track] | None = None


class AuditEntry(BaseModel):
    """One row of the event's transition history."""

    id: str
    action: str
    actor_user_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    metadata: dict | None = None
    created_at: datetime
