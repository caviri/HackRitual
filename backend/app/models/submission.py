from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import AuditMixin, TimestampMixin


class Submission(Base, TimestampMixin, AuditMixin):
    """A versioned snapshot of work toward a Project, by a participant.

    Submissions are versioned per (project, participant) so a team can
    iterate. Lifecycle:
      - `draft`     — team is still editing
      - `final`     — team has marked it ready; eligible for scoring
      - `withdrawn` — pulled back, will not be scored

    Scoring state is tracked separately on the `scores` table.
    """

    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String, ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    result: Mapped[str | None] = mapped_column(String, nullable=True)  # URL / output reference
    payload_json: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="draft"
    )  # draft|final|withdrawn

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "participant_id",
            "version",
            name="uq_submissions_project_participant_version",
        ),
        Index("ix_submissions_project_id", "project_id"),
        Index("ix_submissions_participant_id", "participant_id"),
        Index("ix_submissions_status", "status"),
    )
