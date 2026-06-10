from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class TimestampMixin:
    """Adds created_at + modified_at timestamps. modified_at auto-bumps on update."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AuditMixin:
    """Adds creator/modifier FKs to users.

    Nullable: system-created or migration-seeded rows may have no actor.
    `declared_attr` is used so each subclass gets its own FK constraint.
    """

    @declared_attr
    def created_by_user_id(cls) -> Mapped[str | None]:
        return mapped_column(
            String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )

    @declared_attr
    def modified_by_user_id(cls) -> Mapped[str | None]:
        return mapped_column(
            String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
