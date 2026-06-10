from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import AuditMixin, TimestampMixin


class Page(Base, TimestampMixin, AuditMixin):
    """A content page attached to the event (rules, FAQ, sponsor info, etc.).

    May optionally be linked to a Phase, so a page can act as the landing
    content for a given sub-phase of the event.
    """

    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    phase_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("phases.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,  # O2O — at most one page per phase
    )

    __table_args__ = (
        Index("ix_pages_event_id", "event_id"),
        Index("ix_pages_order", "order"),
        Index("ix_pages_visible", "visible"),
    )
