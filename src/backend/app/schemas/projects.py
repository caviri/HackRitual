"""Schemas for Project + Submission (versioned snapshots)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProjectStatus = Literal["proposed", "approved", "rejected"]
SubmissionStatus = Literal["draft", "final", "withdrawn"]


# ─── Project ─────────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str
    image: str | None = None
    track_id: str | None = None
    proposed_by_participant_id: str


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus


class ProjectResponse(BaseModel):
    id: str
    event_id: str
    track_id: str | None = None
    proposed_by_participant_id: str
    title: str
    description: str
    image: str | None = None
    status: ProjectStatus
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}


# ─── Submission ──────────────────────────────────────────────────────────────


class SubmissionCreate(BaseModel):
    project_id: str
    participant_id: str
    title: str | None = None
    description: str | None = None
    result: str | None = None
    payload_json: str | None = None


class SubmissionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    result: str | None = None
    payload_json: str | None = None
    status: SubmissionStatus | None = None


class SubmissionResponse(BaseModel):
    id: str
    event_id: str
    project_id: str
    participant_id: str
    version: int
    title: str | None = None
    description: str | None = None
    result: str | None = None
    payload_json: str | None = None
    status: SubmissionStatus
    created_at: datetime
    modified_at: datetime

    model_config = {"from_attributes": True}


class SubmissionStatusUpdate(BaseModel):
    """Admin moderation of a submission, recorded in the audit log."""

    status: SubmissionStatus
    reason: str | None = None


class SubmissionListResponse(BaseModel):
    """Paginated admin listing of submissions."""

    submissions: list[SubmissionResponse]
    total: int
    page: int
    per_page: int
    pages: int


class SubmissionFileResponse(BaseModel):
    """Metadata for a file attached to a submission (no blob)."""

    id: str
    submission_id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    created_at: datetime | None = None
