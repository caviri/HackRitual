"""Schemas for Repository + RepoCommit."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RepoAttachRequest(BaseModel):
    url: str = Field(..., min_length=1)
    label: str | None = None


class CommitResponse(BaseModel):
    sha: str
    sha_short: str
    branch: str | None = None
    message: str
    message_first_line: str
    author_name: str
    author_login: str | None = None
    author_avatar_url: str | None = None
    author_profile_url: str | None = None
    committed_at: datetime


class RepositoryResponse(BaseModel):
    id: str
    project_id: str
    url: str
    host: str
    owner: str
    repo: str
    label: str | None = None
    default_branch: str | None = None
    description: str | None = None
    stars: int | None = None
    last_pushed_at: datetime | None = None
    last_polled_at: datetime | None = None
    polling_error: str | None = None
    commits: list[CommitResponse] = []


class RepoListResponse(BaseModel):
    """The project's repositories plus whether the asker may modify them."""

    can_edit: bool = False
    repositories: list[RepositoryResponse] = []
