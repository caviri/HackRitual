"""Schemas for admin-managed content: Track, Phase, Page."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ─── Track ────────────────────────────────────────────────────────────────────


class TrackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class TrackUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class TrackResponse(BaseModel):
    id: str
    event_id: str
    name: str
    description: str | None = None
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}


# ─── Phase ────────────────────────────────────────────────────────────────────


class PhaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class PhaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class PhaseResponse(BaseModel):
    id: str
    event_id: str
    name: str
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}


# ─── Page ─────────────────────────────────────────────────────────────────────


class PageCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    visible: bool = True
    order: int = 0
    phase_id: str | None = None


class PageUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    visible: bool | None = None
    order: int | None = None
    phase_id: str | None = None


class PageResponse(BaseModel):
    id: str
    event_id: str
    title: str
    content: str
    visible: bool
    order: int
    phase_id: str | None = None
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}
