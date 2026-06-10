"""
SQLite database engine, session factory, and FastAPI dependency.

Key design decisions (per specs §5.1):
- WAL mode for concurrent reads alongside single-writer FastAPI process
- busy_timeout=5000ms to survive brief lock contention
- foreign_keys=ON enforced on every connection
- synchronous=NORMAL (safe for WAL mode, faster than FULL)

Multi-stage demo (DEMO_STAGES=true): each event stage can be served from its
own SQLite snapshot under `<dirname(DB_PATH)>/demo/<stage>.db`. The middleware
sets `active_demo_stage` per request and `get_db()` routes to the matching
engine; `None` (the default) means the primary database. Background tasks use
`SessionLocal` directly and therefore always operate on the primary.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Generator
from contextvars import ContextVar

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

DEMO_STAGE_NAMES = ("DRAFT", "OPEN", "FROZEN", "FINAL", "ARCHIVED")

#: Set per-request by DemoStageMiddleware; None = primary DB.
active_demo_stage: ContextVar[str | None] = ContextVar("active_demo_stage", default=None)


class Base(DeclarativeBase):
    pass


def _make_engine(db_path: str) -> Engine:
    """Create an engine with the platform's SQLite pragmas attached."""
    eng = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


engine = _make_engine(settings.db_path)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_stage_engines: dict[str, Engine] = {}
_stage_sessionmakers: dict[str, sessionmaker] = {}
_stage_lock = threading.Lock()


def stage_db_path(stage: str) -> str:
    """Snapshot file for a demo stage, beside the primary database."""
    base = os.path.dirname(os.path.abspath(settings.db_path))
    return os.path.join(base, "demo", f"{stage.lower()}.db")


def get_engine(stage: str | None = None) -> Engine:
    """The engine for a demo stage, or the primary engine when stage is None."""
    if stage is None:
        return engine
    with _stage_lock:
        if stage not in _stage_engines:
            _stage_engines[stage] = _make_engine(stage_db_path(stage))
        return _stage_engines[stage]


def get_sessionmaker(stage: str | None = None) -> sessionmaker:
    if stage is None:
        return SessionLocal
    eng = get_engine(stage)  # outside the lock — _stage_lock is not reentrant
    with _stage_lock:
        if stage not in _stage_sessionmakers:
            _stage_sessionmakers[stage] = sessionmaker(
                bind=eng, autocommit=False, autoflush=False
            )
        return _stage_sessionmakers[stage]


def dispose_stage_engine(stage: str) -> None:
    """Close pooled connections and forget the stage's engine.

    Required before deleting the snapshot file — Windows keeps the file
    locked while any pooled connection is open.
    """
    with _stage_lock:
        eng = _stage_engines.pop(stage, None)
        _stage_sessionmakers.pop(stage, None)
    if eng is not None:
        eng.dispose()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session, always closes on exit.

    Routed: when DemoStageMiddleware has set `active_demo_stage`, the session
    binds to that stage's snapshot instead of the primary database.
    """
    db = get_sessionmaker(active_demo_stage.get())()
    try:
        yield db
    finally:
        db.close()


def check_db() -> bool:
    """Return True if the primary DB is reachable (used by health endpoint)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
