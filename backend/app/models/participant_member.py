from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ParticipantMember(Base):
    __tablename__ = "participant_members"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    participant_id: Mapped[str] = mapped_column(String, ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    role_in_team: Mapped[str] = mapped_column(String, nullable=False)  # captain|member|agent
