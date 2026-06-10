from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import AuditMixin, TimestampMixin


class Track(Base, TimestampMixin, AuditMixin):
    """A thematic track within an event that groups related projects."""

    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_tracks_event_name"),
    )
