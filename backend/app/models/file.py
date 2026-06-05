from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id: Mapped[str] = mapped_column(String, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)  # relative path in UPLOAD_DIR
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_files_submission_id", "submission_id"),
    )
