"""
Demo stage snapshots — five small worlds, one per event state.

Each snapshot is a complete SQLite database holding the event frozen at one
stage: DRAFT has petitions and a waitlist but no projects; OPEN has proposals
and work in flight; FROZEN through ARCHIVED hold the sealed, scored record.
Snapshots are writable sandboxes; a rebuild drops and regrows their tables in place.

Schema comes from `Base.metadata.create_all`, not Alembic: snapshots are
always built from scratch from the current models and regenerated wholesale,
so there is no migration history to preserve. A rebuild after any future
migration picks up the new schema automatically.
"""

from __future__ import annotations

import logging
import os
import time

from app.config import settings
from app.database import (
    DEMO_STAGE_NAMES,
    Base,
    dispose_stage_engine,
    get_engine,
    get_sessionmaker,
    stage_db_path,
)
from app.services.seeder import SeedProfile, seed_admin_users, seed_fixtures

logger = logging.getLogger(__name__)

PROFILES: dict[str, SeedProfile] = {
    "DRAFT": SeedProfile(
        include_projects=False,
        submission_statuses=frozenset(),
        include_scores=False,
        force_waiting=True,
    ),
    "OPEN": SeedProfile(
        submission_statuses=frozenset({"draft", "withdrawn"}),
        include_scores=False,
    ),
    "FROZEN": SeedProfile(),
    "FINAL": SeedProfile(),
    "ARCHIVED": SeedProfile(),
}


def build_stage(stage: str, force: bool = False) -> bool:
    """Create (or with force, recreate) one stage snapshot.

    Returns True when the snapshot was (re)built, False when it already
    existed and force was not set. The file is never deleted — a rebuild
    drops and recreates the tables in place, so requests currently inside
    the stage (including the one that triggered the rebuild) keep a valid
    file handle. WAL lets their read snapshots coexist with the rebuild.
    """
    if stage not in DEMO_STAGE_NAMES:
        raise ValueError(f"unknown stage '{stage}'")

    path = stage_db_path(stage)
    if os.path.exists(path) and not force:
        return False

    started = time.monotonic()
    dispose_stage_engine(stage)  # clear pooled connections; file stays
    os.makedirs(os.path.dirname(path), exist_ok=True)

    import app.models  # noqa: F401 — register all models on Base.metadata

    eng = get_engine(stage)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)

    from app.models.event import Event

    with get_sessionmaker(stage)() as db:
        db.add(
            Event(
                id=settings.event_id,
                title=settings.event_title,
                type=settings.event_type,
                state=stage,
                start_at=settings.event_start,
                end_at=settings.event_end,
            )
        )
        db.flush()
        seed_admin_users(db)
        counts = seed_fixtures(db, PROFILES[stage])
        db.commit()

    logger.info(
        "Demo stage snapshot built",
        extra={
            "stage": stage,
            "seconds": round(time.monotonic() - started, 2),
            "counts": {k: v for k, v in counts.items() if v},
        },
    )
    return True


def build_all(force: bool = False) -> dict[str, bool]:
    """Build every missing snapshot (or all of them, with force)."""
    return {stage: build_stage(stage, force=force) for stage in DEMO_STAGE_NAMES}
