from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import AuditMixin, TimestampMixin


class Project(Base, TimestampMixin, AuditMixin):
    """A proposal for something to build during the event.

    A Project is the *idea/artefact-in-progress*. Concrete work toward it
    flows through Submissions, which are versioned snapshots tied to
    (project, team-type participant). Projects move through a lightweight
    approval workflow: proposed → approved.
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    track_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True
    )
    proposed_by_participant_id: Mapped[str] = mapped_column(
        String, ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    image: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="proposed"
    )  # proposed|approved|rejected

    __table_args__ = (
        Index("ix_projects_event_id", "event_id"),
        Index("ix_projects_track_id", "track_id"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_title", "title"),
    )
