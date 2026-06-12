"""Schemas for agent management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AgentResponse(BaseModel):
    id: str
    name: str
    owner_user_id: str | None = None
    owner_email: str | None = None
    status: str
    created_at: datetime
    key_preview: str  # last 4 chars of the key — for confirmation, not auth

    model_config = {"from_attributes": True}


class AgentCreatedResponse(BaseModel):
    """One-time response containing the freshly-minted plain-text API key.

    The plaintext is never stored on the server; if the caller loses it they
    must regenerate.
    """

    agent: AgentResponse
    api_key: str


class AgentAdminCreate(BaseModel):
    """Admin creates an agent, optionally on behalf of a user."""

    name: str = Field(..., min_length=1, max_length=100)
    owner_user_id: str | None = None


class AgentSelfResponse(BaseModel):
    """Returned by GET /api/agent/me when authenticated via X-API-Key."""

    id: str
    name: str
    owner_user_id: str | None = None
    status: str
    created_at: datetime


class AgentSubmissionCreate(BaseModel):
    """An agent's offering. `payload` (a JSON object) is the primary channel.

    `project_id` is optional — if omitted, the submission is filed under the
    agent's own auto-created project.
    """

    project_id: str | None = None
    title: str | None = None
    description: str | None = None
    result: str | None = None
    payload: dict | None = None


class AgentSubmissionStatus(BaseModel):
    """Agent's view of one of its submissions, with score if available."""

    id: str
    participant_id: str
    status: str
    version: int
    score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
