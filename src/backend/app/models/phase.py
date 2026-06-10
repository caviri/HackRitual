from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import AuditMixin, TimestampMixin


class Phase(Base, TimestampMixin, AuditMixin):
    """A temporal sub-phase of the event (e.g. ideation, hacking, judging).

    Phases live inside the global event lifecycle and let organisers
    structure activity within the OPEN state without changing the ritual state.
    """

    __tablename__ = "phases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_phases_event_id", "event_id"),
        Index("ix_phases_starts_at", "starts_at"),
        Index("ix_phases_ends_at", "ends_at"),
    )
