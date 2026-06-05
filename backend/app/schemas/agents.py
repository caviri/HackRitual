"""Schemas for agent management."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AgentResponse(BaseModel):
    id: str
    name: str
    owner_user_id: Optional[str] = None
    owner_email: Optional[str] = None
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


class AgentSelfResponse(BaseModel):
    """Returned by GET /api/agent/me when authenticated via X-API-Key."""

    id: str
    name: str
    owner_user_id: Optional[str] = None
    status: str
    created_at: datetime
