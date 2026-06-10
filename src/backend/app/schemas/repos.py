"""Schemas for Repository + RepoCommit."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RepoAttachRequest(BaseModel):
    url: str = Field(..., min_length=1)
    label: Optional[str] = None


class CommitResponse(BaseModel):
    sha: str
    sha_short: str
    branch: Optional[str] = None
    message: str
    message_first_line: str
    author_name: str
    author_login: Optional[str] = None
    author_avatar_url: Optional[str] = None
    author_profile_url: Optional[str] = None
    committed_at: datetime


class RepositoryResponse(BaseModel):
    id: str
    project_id: str
    url: str
    host: str
    owner: str
    repo: str
    label: Optional[str] = None
    default_branch: Optional[str] = None
    description: Optional[str] = None
    stars: Optional[int] = None
    last_pushed_at: Optional[datetime] = None
    last_polled_at: Optional[datetime] = None
    polling_error: Optional[str] = None
    commits: list[CommitResponse] = []
