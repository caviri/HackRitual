from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    visible: bool = True


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=4000)
    visible: bool | None = None


class AnnouncementOut(BaseModel):
    id: str
    title: str
    body: str
    visible: bool
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}
