from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id: Mapped[str] = mapped_column(String, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    score_value: Mapped[float] = mapped_column(Float, nullable=False)
    breakdown_json: Mapped[str | None] = mapped_column(String, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending|scored|failed|disqualified
    scorer_version: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_scores_submission_id", "submission_id"),
    )
