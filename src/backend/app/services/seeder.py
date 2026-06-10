"""Fixture seeder for demo / development purposes.

Populates a fresh database with a realistic event so admin tables and the
landing page have content to display. Idempotent — running twice does not
create duplicates: tracks/phases/pages key on (event_id, name|title),
participants key on (event_id, display_name), projects key on (event_id, title),
submissions key on (project, participant, version).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.page import Page
from app.models.participant import Participant
from app.models.phase import Phase
from app.models.project import Project
from app.models.submission import Submission
from app.models.track import Track


def _track_data() -> list[dict]:
    return [
        {
            "name": "data-science",
            "description": "datasets, models, and the geometry between them.",
        },
        {
            "name": "research-infra",
            "description": "schedulers, storage, observability. how science holds itself up.",
        },
        {
            "name": "small-tools",
            "description": "one-file utilities. cli rituals. things that compose well.",
        },
    ]


def _phase_data(event_start: datetime, event_end: datetime) -> list[dict]:
    span = event_end - event_start
    third = span / 3
    return [
        {
            "name": "Ideation",
            "description": "the seeds settle into soil.",
            "starts_at": event_start,
            "ends_at": event_start + third,
        },
        {
            "name": "Hacking",
            "description": "the forge runs hot.",
            "starts_at": event_start + third,
            "ends_at": event_start + 2 * third,
        },
        {
            "name": "Judging",
            "description": "the verdict is sown.",
            "starts_at": event_start + 2 * third,
            "ends_at": event_end,
        },
    ]


def _page_data() -> list[dict]:
    return [
        {
            "title": "The Rites",
            "order": 1,
            "content": (
                "A HackRitual is a time-bounded act of collaborative invention. "
                "It is summoned from a single container, runs against a single SQLite "
                "file, and is dispelled when the work is done.\n\n"
                "Five states. They proceed in order and do not skip."
            ),
        },
        {
            "title": "The Rules",
            "order": 2,
            "content": (
                "1. Be kind to the humans, the agents, and the organisers.\n"
                "2. Every submission carries an authorship trail.\n"
                "3. The gates close when the clock says they close.\n"
                "4. The verdict is the verdict."
            ),
        },
        {
            "title": "A Few Questions",
            "order": 3,
            "content": (
                "Q. Can my agent be on a team without me?\n"
                "A. It may, with your consent and an API key.\n\n"
                "Q. What if the container dies?\n"
                "A. SQLite is in WAL mode. If your storage is persistent, you lose nothing."
            ),
        },
    ]


def _participant_data() -> list[dict]:
    return [
        # Humans
        {"display_name": "Ada Cole", "type": "human", "affiliation": "MIT · data-science", "is_waiting": False},
        {"display_name": "June K.", "type": "human", "affiliation": "self-employed · small-tools", "is_waiting": False},
        {"display_name": "Photosym", "type": "human", "affiliation": "CERN · research-infra", "is_waiting": False},
        {"display_name": "Jane Tu", "type": "human", "affiliation": "NYU · small-tools", "is_waiting": True},
        {"display_name": "Aram J.", "type": "human", "affiliation": "Stanford · judge", "is_waiting": False},
        {"display_name": "Mila A.", "type": "human", "affiliation": "ETH · judge", "is_waiting": False},
        # Agents
        {"display_name": "marrowbot", "type": "agent", "affiliation": "owned by jun.k", "is_waiting": False},
        {"display_name": "rendermouse", "type": "agent", "affiliation": "solo agent", "is_waiting": True},
        {"display_name": "weft", "type": "agent", "affiliation": "captained by the_owls", "is_waiting": False},
        # Teams
        {"display_name": "the_owls", "type": "team", "affiliation": "Lisbon collective · 4 members", "is_waiting": False},
        {"display_name": "photosym-duo", "type": "team", "affiliation": "circadian schedulers · 2 members", "is_waiting": False},
        {"display_name": "meadow", "type": "team", "affiliation": "solo team · 1 member", "is_waiting": False},
    ]


def _project_data() -> list[dict]:
    return [
        {
            "title": "mycelium-mesh",
            "track": "data-science",
            "proposer": "the_owls",
            "description": "gossip protocols modeled on fungal nutrient routing, over IPFS. each node a hyphal tip.",
            "status": "approved",
        },
        {
            "title": "photosym-os",
            "track": "research-infra",
            "proposer": "photosym-duo",
            "description": "a circadian scheduler. workloads track sunlight on the grid.",
            "status": "approved",
        },
        {
            "title": "the_meadow_ide",
            "track": "small-tools",
            "proposer": "meadow",
            "description": "an ide that breathes. ambient sound shifts with build state.",
            "status": "approved",
        },
        {
            "title": "lichen-loom",
            "track": "small-tools",
            "proposer": "weft",
            "description": "a weave of cron jobs that schedule themselves around weather.",
            "status": "approved",
        },
        {
            "title": "spore-print",
            "track": "data-science",
            "proposer": "marrowbot",
            "description": "embed any dataset as a hash of cellular automata states. fingerprint via diversity.",
            "status": "proposed",
        },
        {
            "title": "kombu-cache",
            "track": "research-infra",
            "proposer": "Ada Cole",
            "description": "an l4 cache that prefers vegetal eviction policies. lru with fermentation.",
            "status": "proposed",
        },
        {
            "title": "burrow.cli",
            "track": "small-tools",
            "proposer": "June K.",
            "description": "filesystem navigation that learns from how you move through ground.",
            "status": "proposed",
        },
        {
            "title": "petal-fetch",
            "track": "small-tools",
            "proposer": "Jane Tu",
            "description": "http client that flowers in the terminal. each response a different bloom.",
            "status": "proposed",
        },
        {
            "title": "alluvium",
            "track": "data-science",
            "proposer": "Aram J.",
            "description": "stream processor that deposits learnings as sediment. queryable layers.",
            "status": "proposed",
        },
        {
            "title": "compost-net",
            "track": "research-infra",
            "proposer": "Photosym",
            "description": "a network protocol that recycles dropped packets into nutrient frames.",
            "status": "rejected",
        },
        {
            "title": "rhizome-rpc",
            "track": "research-infra",
            "proposer": "the_owls",
            "description": "rpc that propagates underground. no central node, no preferred path.",
            "status": "approved",
        },
        {
            "title": "fern-fold",
            "track": "data-science",
            "proposer": "rendermouse",
            "description": "tensor folding library inspired by leaf phyllotaxis.",
            "status": "proposed",
        },
    ]


def _submission_data() -> list[dict]:
    """One row per (project, version). Higher version = more recent."""
    return [
        # mycelium-mesh — 3 versions, latest final
        {"project": "mycelium-mesh", "team": "the_owls", "version": 1, "status": "draft", "result": "WIP repo + readme"},
        {"project": "mycelium-mesh", "team": "the_owls", "version": 2, "status": "draft", "result": "core protocol implemented"},
        {"project": "mycelium-mesh", "team": "the_owls", "version": 3, "status": "final", "result": "demo.mp4 · report.pdf · github.com/the-owls/mycelium-mesh"},
        # photosym-os — 2 versions, latest final
        {"project": "photosym-os", "team": "photosym-duo", "version": 1, "status": "draft", "result": ""},
        {"project": "photosym-os", "team": "photosym-duo", "version": 2, "status": "final", "result": "paper.pdf · slides"},
        # the_meadow_ide — 3 versions, latest draft
        {"project": "the_meadow_ide", "team": "meadow", "version": 1, "status": "withdrawn", "result": "early sketch withdrawn"},
        {"project": "the_meadow_ide", "team": "meadow", "version": 2, "status": "draft", "result": "audio-engine prototype"},
        {"project": "the_meadow_ide", "team": "meadow", "version": 3, "status": "draft", "result": "build-state listener"},
        # lichen-loom — 2 versions
        {"project": "lichen-loom", "team": "weft", "version": 1, "status": "draft", "result": "weather-feed adapter"},
        {"project": "lichen-loom", "team": "weft", "version": 2, "status": "final", "result": "demo · poster.pdf"},
        # spore-print — 1 version (proposed project, but already has an exploratory submission)
        {"project": "spore-print", "team": "marrowbot", "version": 1, "status": "draft", "result": "cellular automata seed generator"},
        # rhizome-rpc — 1 version final
        {"project": "rhizome-rpc", "team": "the_owls", "version": 1, "status": "final", "result": "gossip-pull-push protocol · benchmarks"},
        # alluvium — 1 draft
        {"project": "alluvium", "team": "Aram J.", "version": 1, "status": "draft", "result": "sketch only"},
    ]


def seed_fixtures(db: Session) -> dict[str, int]:
    """Idempotently insert fixture rows. Returns a count summary."""
    counts: dict[str, int] = {
        "tracks_created": 0,
        "phases_created": 0,
        "pages_created": 0,
        "participants_created": 0,
        "projects_created": 0,
        "submissions_created": 0,
    }
    event_id = settings.event_id

    # ── Tracks ──
    track_by_name: dict[str, Track] = {}
    for t in _track_data():
        existing = (
            db.query(Track)
            .filter(Track.event_id == event_id, Track.name == t["name"])
            .first()
        )
        if existing:
            track_by_name[t["name"]] = existing
            continue
        row = Track(
            event_id=event_id,
            name=t["name"],
            description=t["description"],
        )
        db.add(row)
        db.flush()
        track_by_name[t["name"]] = row
        counts["tracks_created"] += 1

    # ── Phases ── (dates come from the event record — the panel may have
    # edited them since the env-var seed)
    from app.models.event import Event

    event = db.get(Event, event_id)
    phase_start = event.start_at if event else settings.event_start
    phase_end = event.end_at if event else settings.event_end
    for p in _phase_data(phase_start, phase_end):
        existing = (
            db.query(Phase)
            .filter(Phase.event_id == event_id, Phase.name == p["name"])
            .first()
        )
        if existing:
            continue
        db.add(
            Phase(
                event_id=event_id,
                name=p["name"],
                description=p["description"],
                starts_at=p["starts_at"],
                ends_at=p["ends_at"],
            )
        )
        counts["phases_created"] += 1

    # ── Pages ──
    for pg in _page_data():
        existing = (
            db.query(Page)
            .filter(Page.event_id == event_id, Page.title == pg["title"])
            .first()
        )
        if existing:
            continue
        db.add(
            Page(
                event_id=event_id,
                title=pg["title"],
                content=pg["content"],
                visible=True,
                order=pg["order"],
            )
        )
        counts["pages_created"] += 1

    # ── Participants ──
    participant_by_name: dict[str, Participant] = {}
    for p in _participant_data():
        existing = (
            db.query(Participant)
            .filter(
                Participant.event_id == event_id,
                Participant.display_name == p["display_name"],
            )
            .first()
        )
        if existing:
            participant_by_name[p["display_name"]] = existing
            continue
        row = Participant(
            event_id=event_id,
            type=p["type"],
            display_name=p["display_name"],
            affiliation=p["affiliation"],
            is_waiting=p["is_waiting"],
            status="active",
        )
        db.add(row)
        db.flush()
        participant_by_name[p["display_name"]] = row
        counts["participants_created"] += 1

    db.flush()

    # ── Projects ──
    project_by_title: dict[str, Project] = {}
    for proj in _project_data():
        existing = (
            db.query(Project)
            .filter(Project.event_id == event_id, Project.title == proj["title"])
            .first()
        )
        if existing:
            project_by_title[proj["title"]] = existing
            continue
        proposer = participant_by_name.get(proj["proposer"])
        if not proposer:
            continue
        track = track_by_name.get(proj["track"])
        row = Project(
            event_id=event_id,
            track_id=track.id if track else None,
            proposed_by_participant_id=proposer.id,
            title=proj["title"],
            description=proj["description"],
            status=proj["status"],
        )
        db.add(row)
        db.flush()
        project_by_title[proj["title"]] = row
        counts["projects_created"] += 1

    db.flush()

    # ── Submissions ──
    for s in _submission_data():
        project = project_by_title.get(s["project"])
        team_participant = participant_by_name.get(s["team"])
        if not project or not team_participant:
            continue
        existing = (
            db.query(Submission)
            .filter(
                Submission.project_id == project.id,
                Submission.participant_id == team_participant.id,
                Submission.version == s["version"],
            )
            .first()
        )
        if existing:
            continue
        db.add(
            Submission(
                event_id=event_id,
                project_id=project.id,
                participant_id=team_participant.id,
                version=s["version"],
                title=s["project"],
                description="",
                result=s["result"],
                status=s["status"],
            )
        )
        counts["submissions_created"] += 1

    db.commit()
    return counts
