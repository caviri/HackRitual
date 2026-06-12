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

import hashlib
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
    # FROZEN onward anchors to the window END (the seal happens when the
    # gates close, wherever that end sits for the stage).
    "FROZEN": [
        (0, "event.transition", "event", {"from": "OPEN", "to": "FROZEN", "by": "the keeper"}),
        (2, "submission.finalised", "submission", {"project": "mycelium-mesh", "version": 3}),
        (4, "submission.finalised", "submission", {"project": "rhizome-rpc", "version": 1}),
        (6, "submission.finalised", "submission", {"project": "photosym-os", "version": 2}),
        (8, "submission.finalised", "submission", {"project": "lichen-loom", "version": 2}),
        (20, "score.rendered", "score", {"project": "mycelium-mesh", "score": 90.0, "scorer": "default-1.0"}),
        (21, "score.rendered", "score", {"project": "rhizome-rpc", "score": 80.0, "scorer": "default-1.0"}),
        (22, "score.rendered", "score", {"project": "photosym-os", "score": 60.0, "scorer": "default-1.0"}),
        (23, "score.rendered", "score", {"project": "lichen-loom", "score": 50.0, "scorer": "default-1.0"}),
    ],
    "FINAL": [
        (240, "event.transition", "event", {"from": "FROZEN", "to": "FINAL", "by": "the keeper"}),
        (241, "verdict.inscribed", "event", {"first": "the_owls / mycelium-mesh", "second": "the_owls / rhizome-rpc", "third": "photosym-duo / photosym-os"}),
        (245, "leaderboard.published", "event", None),
    ],
    "ARCHIVED": [
        (1560, "event.transition", "event", {"from": "FINAL", "to": "ARCHIVED", "by": "the keeper"}),
        (1570, "export.sealed", "export", {"files": 14, "redaction": "public"}),
        (1575, "record.closed", "event", {"note": "the ritual is complete"}),
    ],
}

# Chapters anchored to the window end rather than the start.
_END_ANCHORED = {"FROZEN", "FINAL", "ARCHIVED"}

# Cumulative history per stage: each stage carries its predecessors' entries.
_STAGE_HISTORY = {
    "DRAFT": ["DRAFT"],
    "OPEN": ["DRAFT", "OPEN"],
    "FROZEN": ["DRAFT", "OPEN", "FROZEN"],
    "FINAL": ["DRAFT", "OPEN", "FROZEN", "FINAL"],
    "ARCHIVED": ["DRAFT", "OPEN", "FROZEN", "FINAL", "ARCHIVED"],
}


def _anchor_bookkeeping(db, start_at, end_at) -> None:
    """Re-stamp everything the seeding produced — audit rows AND row-level
    created/modified timestamps — into the stage's own timeline. Without
    this, a snapshot whose window closed a month ago carries rows "created"
    at build wall-clock time, and the record contradicts itself."""
    from datetime import timedelta

    from app.models.announcement import Announcement
    from app.models.application import Application
    from app.models.audit_log import AuditLog
    from app.models.participant import Participant
    from app.models.project import Project
    from app.models.score import Score
    from app.models.submission import Submission

    rows = db.query(AuditLog).order_by(AuditLog.created_at).all()
    setup_i = grant_i = 0
    for row in rows:
        if row.action == "application.approved":
            # The keeper reads petitions once the gates open.
            row.created_at = start_at + timedelta(minutes=8 + grant_i * 3)
            grant_i += 1
        else:
            # Inscription-era bookkeeping (keeper seeded, roles recast).
            row.created_at = start_at - timedelta(days=2, minutes=-7 * setup_i)
            setup_i += 1

    for application in db.query(Application).filter(Application.decided_at.isnot(None)).all():
        offset = 8 if application.status == "approved" else 4
        application.decided_at = start_at + timedelta(minutes=offset)

    # Petitions arrive the day before the circle opens.
    for i, application in enumerate(
        db.query(Application).order_by(Application.email).all()
    ):
        application.created_at = start_at - timedelta(days=1, minutes=-11 * i)

    # Seats are reserved in the inscription era.
    for i, participant in enumerate(
        db.query(Participant).order_by(Participant.display_name).all()
    ):
        participant.created_at = start_at - timedelta(days=1, hours=2, minutes=-9 * i)

    # Proposals land shortly after the gates open; offerings follow.
    for i, project in enumerate(db.query(Project).order_by(Project.title).all()):
        stamp = start_at + timedelta(minutes=30 + 13 * i)
        project.created_at = stamp
        project.modified_at = stamp
    for i, submission in enumerate(
        db.query(Submission).order_by(Submission.title, Submission.version).all()
    ):
        stamp = start_at + timedelta(hours=2, minutes=17 * i)
        submission.created_at = stamp
        submission.modified_at = stamp

    # Verdicts render after the seal.
    for i, score in enumerate(db.query(Score).order_by(Score.score_value.desc()).all()):
        score.scored_at = end_at + timedelta(minutes=20 + i)

    # Dispatches follow the chronicle's arc: setup era, gates, seal, verdict,
    # archive — matched by title to their publication moment.
    announcement_stamps = {
        "The circle is drawn": start_at - timedelta(days=2, minutes=-5),
        "The gates are open": start_at + timedelta(minutes=5),
        "Agents are welcome this rite": start_at + timedelta(minutes=35),
        "The forge is sealed": end_at + timedelta(minutes=10),
        "The verdict is inscribed": end_at + timedelta(hours=4, minutes=10),
        "The record is sealed": end_at + timedelta(hours=26, minutes=15),
    }
    for announcement in db.query(Announcement).all():
        stamp = announcement_stamps.get(announcement.title)
        if stamp is not None:
            announcement.created_at = stamp
            announcement.modified_at = stamp
    db.flush()


def _seed_chronicle(db, stage: str, start_at=None, end_at=None) -> None:
    """Write the stage's narrative into the audit log. DRAFT/OPEN chapters
    offset from the window start; FROZEN onward from the window end, so the
    seal lands when the gates actually close. Flushes; caller commits."""
    import json
    from datetime import timedelta

    from app.models.audit_log import AuditLog

    if start_at is None:
        start_at = settings.event_start.replace(tzinfo=None)
    if end_at is None:
        end_at = settings.event_end.replace(tzinfo=None)
    for chapter in _STAGE_HISTORY[stage]:
        anchor = end_at if chapter in _END_ANCHORED else start_at
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


def _schema_fingerprint() -> str:
    """Hash of the current model schema (tables + columns). Snapshots built
    under an older schema would 500 on new columns — the fingerprint makes
    boot rebuild them automatically instead."""
    import app.models  # noqa: F401 — register all models

    parts = []
    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        for column in sorted(table.columns, key=lambda c: c.name):
            parts.append(f"{table.name}.{column.name}:{column.type}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _fingerprint_path(stage: str) -> str:
    return stage_db_path(stage) + ".schema"


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
    fingerprint = _schema_fingerprint()
    if os.path.exists(path) and not force:
        try:
            with open(_fingerprint_path(stage)) as fh:
                if fh.read().strip() == fingerprint:
                    return False
        except OSError:
            pass
        logger.info("Demo stage snapshot outdated — rebuilding", extra={"stage": stage})

    started = time.monotonic()
    dispose_stage_engine(stage)  # clear pooled connections; file stays
    os.makedirs(os.path.dirname(path), exist_ok=True)

    import app.models  # noqa: F401 — register all models on Base.metadata

    eng = get_engine(stage)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)

    from app.models.event import Event

    start_at, end_at = _stage_window(stage)
    sealed = stage in ("FROZEN", "FINAL", "ARCHIVED")
    with get_sessionmaker(stage)() as db:
        db.add(
            Event(
                id=settings.event_id,
                title=settings.event_title,
                type=settings.event_type,
                state=stage,
                start_at=start_at,
                end_at=end_at,
                config_json='{"registration_open": false}' if sealed else None,
            )
        )
        db.flush()
        seed_admin_users(db)
        counts = seed_fixtures(db, PROFILES[stage])
        _anchor_bookkeeping(db, start_at, end_at)
        _seed_chronicle(db, stage, start_at=start_at, end_at=end_at)
        db.commit()

    with open(_fingerprint_path(stage), "w") as fh:
        fh.write(fingerprint)

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
