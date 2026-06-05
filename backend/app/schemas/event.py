"""Pydantic schemas for the singleton Event + state transitions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventState = Literal["DRAFT", "OPEN", "FROZEN", "FINAL", "ARCHIVED"]


class EventResponse(BaseModel):
    """The singleton event the container is hosting."""

    id: str
    title: str
    type: str
    state: EventState
    start_at: datetime
    end_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StateTransitionRequest(BaseModel):
    """Admin request to advance the event's state machine."""

    to: EventState = Field(..., description="Target state")
