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
        announcement_stages=("DRAFT",),
    ),
    "OPEN": SeedProfile(
        submission_statuses=frozenset({"draft", "withdrawn"}),
        include_scores=False,
        decide_applications=True,
        announcement_stages=("DRAFT", "OPEN"),
    ),
    "FROZEN": SeedProfile(
        decide_applications=True,
        announcement_stages=("DRAFT", "OPEN", "FROZEN"),
    ),
    "FINAL": SeedProfile(
        decide_applications=True,
        announcement_stages=("DRAFT", "OPEN", "FROZEN", "FINAL"),
    ),
    "ARCHIVED": SeedProfile(
        decide_applications=True,
        announcement_stages=("DRAFT", "OPEN", "FROZEN", "FINAL", "ARCHIVED"),
    ),
}

# Each snapshot's event window sits where that stage would find it on a real
# clock: DRAFT before the gates, OPEN inside the window, ARCHIVED long past.
# (offset of start from build time, event duration)
_STAGE_WINDOWS: dict[str, tuple] = {}


def _stage_window(stage: str):
    from datetime import datetime, timedelta

    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    spans = {
        "DRAFT": (now + timedelta(days=21), now + timedelta(days=23)),
        "OPEN": (now - timedelta(days=1), now + timedelta(days=1)),
        "FROZEN": (now - timedelta(days=3), now - timedelta(hours=3)),
        "FINAL": (now - timedelta(days=5), now - timedelta(days=2)),
        "ARCHIVED": (now - timedelta(days=30), now - timedelta(days=27)),
    }
    return spans[stage]


# The chronicle each snapshot carries — what the audit log would hold if the
# ritual had genuinely walked to that stage. (minutes offset from event start,
# action, target_type, metadata). Stages are cumulative: FROZEN includes
# OPEN's history, and so on.
_CHRONICLE: dict[str, list[tuple[int, str, str | None, dict | None]]] = {
    "DRAFT": [
        (-2880, "event.created", "event", {"state": "DRAFT"}),
        (-2870, "event.config_updated", "event", {"fields": ["tracks", "submission_limit_per_participant"]}),
        (-2860, "page.published", "page", {"title": "The Rites"}),
        (-2855, "page.published", "page", {"title": "The Rules"}),
        (-1440, "application.received", "application", {"name": "Nadia Fern"}),
        (-1380, "application.received", "application", {"name": "Tomas Reyes"}),
        (-1320, "application.received", "application", {"name": "Priya Anand"}),
        (-1260, "application.rejected", "application", {"name": "Vik Marsh", "reason": "off-theme"}),
        (-720, "participant.reserved", "participant", {"handle": "Ada Cole", "waitlist": True}),
        (-700, "participant.reserved", "participant", {"handle": "June K.", "waitlist": True}),
    ],
    "OPEN": [
        (0, "event.transition", "event", {"from": "DRAFT", "to": "OPEN", "by": "the keeper"}),
        (12, "participant.registered", "participant", {"handle": "Ada Cole"}),
        (15, "participant.registered", "participant", {"handle": "June K."}),
        (22, "team.formed", "participant", {"handle": "the_owls", "captain": "June K."}),
        (30, "agent.created", "agent", {"name": "marrowbot"}),
        (45, "project.proposed", "project", {"title": "mycelium-mesh", "track": "data-science"}),
        (52, "project.proposed", "project", {"title": "photosym-os", "track": "research-infra"}),
        (60, "project.approved", "project", {"title": "mycelium-mesh"}),
        (95, "submission.offered", "submission", {"project": "mycelium-mesh", "version": 1}),
        (140, "submission.offered", "submission", {"project": "lichen-loom", "version": 1}),
        (180, "submission.withdrawn", "submission", {"project": "the_meadow_ide", "version": 1}),
        (220, "submission.offered", "submission", {"project": "spore-print", "version": 1}),
    ],
    "FROZEN": [
        (1440, "event.transition", "event", {"from": "OPEN", "to": "FROZEN", "by": "the keeper"}),
        (1442, "submission.finalised", "submission", {"project": "mycelium-mesh", "version": 3}),
        (1444, "submission.finalised", "submission", {"project": "rhizome-rpc", "version": 1}),
        (1446, "submission.finalised", "submission", {"project": "photosym-os", "version": 2}),
        (1448, "submission.finalised", "submission", {"project": "lichen-loom", "version": 2}),
        (1460, "score.rendered", "score", {"project": "mycelium-mesh", "value": 90.0, "scorer": "default-1.0"}),
        (1461, "score.rendered", "score", {"project": "rhizome-rpc", "value": 80.0, "scorer": "default-1.0"}),
        (1462, "score.rendered", "score", {"project": "photosym-os", "value": 60.0, "scorer": "default-1.0"}),
        (1463, "score.rendered", "score", {"project": "lichen-loom", "value": 50.0, "scorer": "default-1.0"}),
    ],
    "FINAL": [
        (1700, "event.transition", "event", {"from": "FROZEN", "to": "FINAL", "by": "the keeper"}),
        (1701, "verdict.inscribed", "event", {"first": "the_owls / mycelium-mesh", "second": "the_owls / rhizome-rpc", "third": "photosym-duo / photosym-os"}),
        (1705, "leaderboard.published", "event", None),
    ],
    "ARCHIVED": [
        (2100, "event.transition", "event", {"from": "FINAL", "to": "ARCHIVED", "by": "the keeper"}),
        (2110, "export.sealed", "export", {"files": 14, "redaction": "public"}),
        (2115, "record.closed", "event", {"note": "the ritual is complete"}),
    ],
}

# Cumulative history per stage: each stage carries its predecessors' entries.
_STAGE_HISTORY = {
    "DRAFT": ["DRAFT"],
    "OPEN": ["DRAFT", "OPEN"],
    "FROZEN": ["DRAFT", "OPEN", "FROZEN"],
    "FINAL": ["DRAFT", "OPEN", "FROZEN", "FINAL"],
    "ARCHIVED": ["DRAFT", "OPEN", "FROZEN", "FINAL", "ARCHIVED"],
}


def _seed_chronicle(db, stage: str, anchor=None) -> None:
    """Write the stage's narrative into the audit log (deterministic offsets
    from the stage's event start). Flushes; caller commits."""
    import json
    from datetime import timedelta

    from app.models.audit_log import AuditLog

    if anchor is None:
        anchor = settings.event_start.replace(tzinfo=None)
    for chapter in _STAGE_HISTORY[stage]:
        for minutes, action, target_type, metadata in _CHRONICLE[chapter]:
            db.add(
                AuditLog(
                    action=action,
                    target_type=target_type,
                    metadata_json=json.dumps(metadata) if metadata else None,
                    created_at=anchor + timedelta(minutes=minutes),
                )
            )
    db.flush()


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

    start_at, end_at = _stage_window(stage)
    with get_sessionmaker(stage)() as db:
        db.add(
            Event(
                id=settings.event_id,
                title=settings.event_title,
                type=settings.event_type,
                state=stage,
                start_at=start_at,
                end_at=end_at,
            )
        )
        db.flush()
        seed_admin_users(db)
        counts = seed_fixtures(db, PROFILES[stage])
        _seed_chronicle(db, stage, anchor=start_at)
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
