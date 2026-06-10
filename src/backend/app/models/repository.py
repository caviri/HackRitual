from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Repository(Base):
    """A code repository linked to a project — the *where* of its evolution.

    Public-only for v1: we fetch via the host's public API without
    credentials (with an optional shared platform token to lift rate limits).
    Polling cadence is TTL-based: a `GET /api/projects/{id}/repos` triggers
    a refetch only if `last_polled_at` is older than the TTL.
    """

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    url: Mapped[str] = mapped_column(String, nullable=False)
    host: Mapped[str] = mapped_column(String, nullable=False)  # github | gitlab | …
    owner: Mapped[str] = mapped_column(String, nullable=False)
    repo: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str | None] = mapped_column(String, nullable=True)  # optional human-readable

    # Cached metadata from the host
    default_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    stars: Mapped[int | None] = mapped_column(nullable=True)
    last_pushed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Polling state
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    polling_error: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("project_id", "url", name="uq_repositories_project_url"),
        Index("ix_repositories_project_id", "project_id"),
    )


class RepoCommit(Base):
    """A commit observed on a linked repository.

    Stored per-repo with branch context so the UI can render an "evolution"
    feed grouped by branch. We keep up to N most recent commits per repo
    (older ones get evicted on refresh — kept lightweight on purpose).
    """

    __tablename__ = "repo_commits"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(
        String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )

    sha: Mapped[str] = mapped_column(String, nullable=False)
    branch: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(String, nullable=False)

    # Author — commit's git author info plus optional host-resolved user
    author_name: Mapped[str] = mapped_column(String, nullable=False)
    author_login: Mapped[str | None] = mapped_column(String, nullable=True)
    author_avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    author_profile_url: Mapped[str | None] = mapped_column(String, nullable=True)

    committed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("repository_id", "sha", name="uq_repo_commits_repo_sha"),
        Index("ix_repo_commits_repository_id", "repository_id"),
        Index("ix_repo_commits_committed_at", "committed_at"),
    )
