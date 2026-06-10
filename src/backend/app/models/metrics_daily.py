from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MetricsDaily(Base):
    """Aggregate-only daily counters (§14). No per-user data, ever."""

    __tablename__ = "metrics_daily"

    date: Mapped[str] = mapped_column(String, primary_key=True)  # YYYY-MM-DD
    submissions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    logins_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agent_submissions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rate_limit_triggered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scoring_avg_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scoring_max_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scoring_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
