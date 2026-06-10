from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")  # user|admin|judge|mod
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active|inactive
    # The generated access password (word-word-NNNN). Plaintext by design:
    # admins distribute it by hand and can re-copy it from the panel. Unique —
    # login is a lookup on this column alone. NULL means the user cannot log in.
    access_password: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Portrait — the user's dithered/halftoned face. Original source kept
    # alongside the processed version so the effect parameters can be tweaked
    # without re-uploading.
    portrait_path: Mapped[str | None] = mapped_column(String, nullable=True)
    portrait_original_path: Mapped[str | None] = mapped_column(String, nullable=True)
    portrait_effect: Mapped[str | None] = mapped_column(String, nullable=True)  # dither|halftone|none
    portrait_contrast: Mapped[float | None] = mapped_column(Float, nullable=True)
    portrait_brightness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    portrait_scale: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.1..1.0 downsample factor

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_access_password", "access_password", unique=True),
    )
