from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # human|agent|team
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    affiliation: Mapped[str | None] = mapped_column(String, nullable=True)
    links_json: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON string
    invite_code: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)  # For teams
    is_waiting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active|disabled|banned
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_participants_event_id", "event_id"),
        Index("ix_participants_invite_code", "invite_code"),
    )
