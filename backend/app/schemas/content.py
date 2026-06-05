"""Schemas for admin-managed content: Track, Phase, Page."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Track ────────────────────────────────────────────────────────────────────


class TrackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TrackResponse(BaseModel):
    id: str
    event_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}


# ─── Phase ────────────────────────────────────────────────────────────────────


class PhaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class PhaseResponse(BaseModel):
    id: str
    event_id: str
    name: str
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}


# ─── Page ─────────────────────────────────────────────────────────────────────


class PageCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    visible: bool = True
    order: int = 0
    phase_id: Optional[str] = None


class PageUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    visible: Optional[bool] = None
    order: Optional[int] = None
    phase_id: Optional[str] = None


class PageResponse(BaseModel):
    id: str
    event_id: str
    title: str
    content: str
    visible: bool
    order: int
    phase_id: Optional[str] = None
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}
