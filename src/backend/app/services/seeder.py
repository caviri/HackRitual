"""Fixture seeder for demo / development purposes.

Populates a fresh database with a realistic event so admin tables and the
landing page have content to display. Idempotent — running twice does not
create duplicates: tracks/phases/pages key on (event_id, name|title),
participants key on (event_id, display_name), projects key on (event_id, title),
submissions key on (project, participant, version), users on email, member
links on (participant, user), files on (submission, sha256), applications on
email. Generated art is deterministic, so file hashes are stable across runs;
disk artifacts regenerate when the DB points at a missing file.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.application import Application
from app.models.file import File
from app.models.page import Page
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember
from app.models.phase import Phase
from app.models.project import Project
from app.models.submission import Submission
from app.models.track import Track
from app.models.user import User
from app.services import demo_art


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


def _user_data() -> list[dict]:
    """Demo users behind the human participants. Fixed passwords keep demos
    reproducible; collisions fall back to a generated one."""
    return [
        {"email": "ada@demo.rite", "name": "Ada Cole", "role": "user", "password": "fern-lantern-4821", "login_hours": 2},
        {"email": "june@demo.rite", "name": "June K.", "role": "user", "password": "moss-quill-7305", "login_hours": 5},
        {"email": "photosym@demo.rite", "name": "Photosym", "role": "user", "password": "cedar-prism-1184", "login_hours": 8},
        {"email": "jane@demo.rite", "name": "Jane Tu", "role": "user", "password": "briar-comet-6592", "login_hours": 11},
        {"email": "aram@demo.rite", "name": "Aram J.", "role": "judge", "password": "rowan-sigil-2417", "login_hours": 26},
        {"email": "mila@demo.rite", "name": "Mila A.", "role": "judge", "password": "heron-ember-9038", "login_hours": 27},
    ]


def _membership_data() -> list[dict]:
    """(team display_name, user email, role_in_team) — beyond each user
    captaining their own solo participant."""
    return [
        {"participant": "the_owls", "email": "june@demo.rite", "role": "captain"},
        {"participant": "the_owls", "email": "ada@demo.rite", "role": "member"},
        {"participant": "photosym-duo", "email": "photosym@demo.rite", "role": "captain"},
        {"participant": "meadow", "email": "jane@demo.rite", "role": "captain"},
    ]


# Submission enrichment: (project, version) → description, payload, and which
# generated plates / reports to attach. File counts are chosen so the default
# completeness scorer lands distinct values (no leaderboard ties):
# mycelium-mesh v3 = 90, rhizome-rpc v1 = 80, photosym-os v2 = 60,
# lichen-loom v2 = 50.
_SUBMISSION_ENRICHMENT: dict[tuple[str, int], dict] = {
    ("mycelium-mesh", 3): {
        "description": "the mesh holds at 200 nodes. gossip converges in four hops; "
        "nutrient routing tables stay under a kilobyte each.",
        "payload": {"repo": "github.com/the-owls/mycelium-mesh", "demo": "demo.mp4", "nodes": 200},
        "plates": [("plate:mycelium-mesh:1", "bloom")],
        "report": "mycelium-mesh",
    },
    ("rhizome-rpc", 1): {
        "description": "no central node, no preferred path. benchmarks against grpc "
        "included — slower, but it survives losing half the graph.",
        "payload": {"repo": "github.com/the-owls/rhizome-rpc", "benchmarks": "bench/results.json"},
        "plates": [],
        "report": "rhizome-rpc",
    },
    ("photosym-os", 2): {
        "description": "the scheduler tracks sunlight across three grid regions; "
        "workloads migrate at dawn and settle by noon.",
        "payload": None,
        "plates": [
            ("plate:photosym-os:1", "nucleus"),
            ("plate:photosym-os:2", "nucleus"),
            ("plate:photosym-os:3", "lattice"),
        ],
        "report": None,
    },
    ("lichen-loom", 2): {
        "description": "cron jobs that reschedule themselves around the weather feed. "
        "the loom held through a simulated storm week.",
        "payload": None,
        "plates": [("plate:lichen-loom:1", "sprout"), ("plate:lichen-loom:2", "sprout")],
        "report": None,
    },
    # Drafts get a single working plate and stay unscored.
    ("mycelium-mesh", 2): {
        "description": "",
        "payload": None,
        "plates": [("plate:mycelium-mesh:wip", "lattice")],
        "report": None,
    },
    ("the_meadow_ide", 3): {
        "description": "",
        "payload": None,
        "plates": [("plate:the_meadow_ide:wip", "sprout")],
        "report": None,
    },
    ("spore-print", 1): {
        "description": "",
        "payload": None,
        "plates": [("plate:spore-print:wip", "lattice")],
        "report": None,
    },
}

# Finals to score, in leaderboard order (values fall out of completeness).
_SCORED_FINALS = [("mycelium-mesh", 3), ("rhizome-rpc", 1), ("photosym-os", 2), ("lichen-loom", 2)]

_TRACK_MOTIF = {
    "data-science": "bloom",
    "research-infra": "nucleus",
    "small-tools": "sprout",
}


def _report_md(project_title: str) -> str:
    return (
        f"# {project_title} — closing report\n\n"
        "What was offered, what held, and what remains.\n\n"
        "## What holds\n"
        "The core path works end to end and survived the demo.\n\n"
        "## What remains\n"
        "Edges. There are always edges.\n"
    )


def _application_data() -> list[dict]:
    return [
        {"name": "Nadia Fern", "email": "nadia@petition.rite", "team": None,
         "interest": "a moss-growth simulator for datacentre cooling maps.", "status": "pending"},
        {"name": "Tomas Reyes", "email": "tomas@petition.rite", "team": "root-cellar",
         "interest": "fermentation telemetry — jars that report their own readiness.", "status": "pending"},
        {"name": "Priya Anand", "email": "priya@petition.rite", "team": "root-cellar",
         "interest": "dashboards for yeast cultures. the colonies deserve observability.", "status": "pending"},
        {"name": "Otto Lind", "email": "otto@petition.rite", "team": None,
         "interest": "a slow-clock for experiments that take longer than attention spans.", "status": "pending"},
        {"name": "Sana Idris", "email": "sana@petition.rite", "team": "night-soil",
         "interest": "a compost chemistry logger with a thermal probe and opinions.", "status": "pending"},
        {"name": "Vik Marsh", "email": "vik@petition.rite", "team": None,
         "interest": "a crypto ticker skin for the leaderboard.", "status": "rejected"},
    ]


def _announcement_data() -> list[dict]:
    return [
        {
            "title": "The circle is drawn",
            "body": "Tracks are inscribed, the rules are bound, and the petition desk "
            "is open. If you hold no key yet, file at /apply/ — the keeper reads "
            "every petition by hand.",
        },
        {
            "title": "Agents are welcome this rite",
            "body": "The agent policy is set to allowed. Mint a key from your profile, "
            "name your bot, and it competes as a participant in its own right.",
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
        {
            "title": "The Judges",
            "order": 4,
            "content": (
                "Two judges hold the scales this rite: Aram J. (Stanford) and "
                "Mila A. (ETH). The scorer renders a first verdict; the judges "
                "may override it, and every override is inscribed in the audit log.\n\n"
                "Scores weigh completeness: a title, a description, attached "
                "evidence, and a structured payload."
            ),
        },
        {
            "title": "The Archive",
            "order": 5,
            "content": (
                "When the rite reaches ARCHIVED, the record seals. The artefact "
                "bundle holds the database, every upload, the audit trail, and a "
                "manifest of sha256 sums.\n\n"
                "Take the zip. Dispel the container. Nothing else remains."
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
        "users_created": 0,
        "members_created": 0,
        "portraits_created": 0,
        "project_images_created": 0,
        "files_created": 0,
        "scores_created": 0,
        "applications_created": 0,
        "announcements_created": 0,
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

    # ── Submissions ── (keep references even for pre-existing rows so the
    # enrichment passes below can fill them in)
    submission_by_key: dict[tuple[str, int], Submission] = {}
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
            submission_by_key[(s["project"], s["version"])] = existing
            continue
        row = Submission(
            event_id=event_id,
            project_id=project.id,
            participant_id=team_participant.id,
            version=s["version"],
            title=s["project"],
            description="",
            result=s["result"],
            status=s["status"],
        )
        db.add(row)
        db.flush()
        submission_by_key[(s["project"], s["version"])] = row
        counts["submissions_created"] += 1

    db.flush()

    upload_root = Path(settings.upload_dir)
    base_login = event.start_at if event else settings.event_start

    # ── Users behind the human participants ──
    user_by_email: dict[str, User] = {}
    for u in _user_data():
        existing_user = db.query(User).filter(User.email == u["email"]).first()
        if existing_user is None:
            password = u["password"]
            if db.query(User).filter(User.access_password == password).first():
                from app.services.passwords import generate_unique_password

                password = generate_unique_password(db)
            existing_user = User(
                email=u["email"],
                display_name=u["name"],
                role=u["role"],
                access_password=password,
                last_login_at=base_login + timedelta(hours=u["login_hours"]),
            )
            db.add(existing_user)
            db.flush()
            counts["users_created"] += 1
        elif not existing_user.access_password:
            from app.services.passwords import generate_unique_password

            existing_user.access_password = generate_unique_password(db)
        user_by_email[u["email"]] = existing_user

    # ── Membership links ── (each user captains their own solo participant,
    # plus the team rosters)
    links: list[tuple[Participant | None, User | None, str]] = []
    for u in _user_data():
        links.append((participant_by_name.get(u["name"]), user_by_email.get(u["email"]), "captain"))
    for m in _membership_data():
        links.append((participant_by_name.get(m["participant"]), user_by_email.get(m["email"]), m["role"]))
    for participant, user, role in links:
        if participant is None or user is None:
            continue
        existing_link = (
            db.query(ParticipantMember)
            .filter(
                ParticipantMember.participant_id == participant.id,
                ParticipantMember.user_id == user.id,
            )
            .first()
        )
        if existing_link:
            continue
        db.add(
            ParticipantMember(
                participant_id=participant.id,
                user_id=user.id,
                role_in_team=role,
            )
        )
        counts["members_created"] += 1

    db.flush()

    # ── Portraits ── (original kept beside the processed copy, like me.py)
    for u in _user_data():
        user = user_by_email.get(u["email"])
        if user is None:
            continue
        have_file = bool(
            user.portrait_path and (upload_root / user.portrait_path).exists()
        )
        if have_file:
            continue
        root = upload_root / "portraits" / user.id
        root.mkdir(parents=True, exist_ok=True)
        original = demo_art.generate_art(f"portrait:{u['email']}", "sprout", (480, 480))
        original_path = root / "original.png"
        original_path.write_bytes(original)
        processed = demo_art.generate_processed_art(
            f"portrait:{u['email']}", "sprout", size=(480, 480)
        )
        processed_path = root / f"processed-{hashlib.sha256(processed).hexdigest()[:12]}.png"
        processed_path.write_bytes(processed)
        user.portrait_original_path = str(original_path.relative_to(upload_root))
        user.portrait_path = str(processed_path.relative_to(upload_root))
        user.portrait_effect = "dither"
        user.portrait_contrast = 1.8
        user.portrait_brightness = 0
        user.portrait_scale = 0.4
        counts["portraits_created"] += 1

    # ── Project covers ──
    for proj in _project_data():
        project = project_by_title.get(proj["title"])
        if project is None:
            continue
        have_cover = bool(
            project.image
            and project.image.startswith("/uploads/")
            and (upload_root / project.image[len("/uploads/"):]).exists()
        )
        if have_cover or (project.image and not project.image.startswith("/uploads/")):
            continue
        motif = "lattice" if proj["status"] == "rejected" else _TRACK_MOTIF.get(proj["track"], "bloom")
        cover = demo_art.generate_processed_art(f"project:{proj['title']}", motif)
        slug = re.sub(r"[^a-z0-9-]+", "-", proj["title"].lower()).strip("-")
        cover_dir = upload_root / "projects" / slug
        cover_dir.mkdir(parents=True, exist_ok=True)
        cover_path = cover_dir / f"cover-{hashlib.sha256(cover).hexdigest()[:12]}.png"
        cover_path.write_bytes(cover)
        project.image = f"/uploads/{cover_path.relative_to(upload_root).as_posix()}"
        counts["project_images_created"] += 1

    # ── Submission enrichment: descriptions, payloads, plates, reports ──
    def _attach(submission: Submission, filename_seed: str, data: bytes, mime: str) -> None:
        sha = hashlib.sha256(data).hexdigest()
        existing_file = (
            db.query(File)
            .filter(File.submission_id == submission.id, File.sha256 == sha)
            .first()
        )
        ext = "png" if mime == "image/png" else "md"
        file_dir = upload_root / event_id / submission.participant_id / submission.id
        abs_path = file_dir / f"{sha[:12]}.{ext}"
        if existing_file and abs_path.exists():
            return
        file_dir.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(data)
        if not existing_file:
            db.add(
                File(
                    submission_id=submission.id,
                    path=str(abs_path.relative_to(upload_root).as_posix()),
                    mime_type=mime,
                    size_bytes=len(data),
                    sha256=sha,
                )
            )
            counts["files_created"] += 1

    for (title, version), extra in _SUBMISSION_ENRICHMENT.items():
        submission = submission_by_key.get((title, version))
        if submission is None:
            continue
        if extra["description"] and not submission.description:
            submission.description = extra["description"]
        if extra["payload"] and not submission.payload_json:
            submission.payload_json = json.dumps(extra["payload"])
        for plate_seed, motif in extra["plates"]:
            _attach(submission, plate_seed, demo_art.generate_processed_art(plate_seed, motif), "image/png")
        if extra["report"]:
            _attach(
                submission,
                f"report:{title}",
                _report_md(extra["report"]).encode("utf-8"),
                "text/markdown",
            )

    db.flush()

    # ── Scores ── (default scorer, pinned, so an active WASM scorer on the
    # instance cannot skew the demo ladder; idempotent via the
    # (submission, scorer_version) upsert)
    from app.models.score import Score
    from app.scoring.default_scorer import DefaultScorer
    from app.services.scoring_service import score_submission

    scorer = DefaultScorer()
    for title, version in _SCORED_FINALS:
        submission = submission_by_key.get((title, version))
        if submission is None:
            continue
        already_scored = (
            db.query(Score)
            .filter(
                Score.submission_id == submission.id,
                Score.scorer_version == scorer.version,
                Score.status == "scored",
            )
            .first()
        )
        if already_scored:
            continue
        score_submission(db, submission.id, scorer=scorer)
        counts["scores_created"] += 1

    # ── Announcements ── (dispatches under the homepage hero)
    from app.models.announcement import Announcement

    for a in _announcement_data():
        existing_news = (
            db.query(Announcement)
            .filter(
                Announcement.event_id == event_id,
                Announcement.title == a["title"],
            )
            .first()
        )
        if existing_news:
            continue
        db.add(
            Announcement(
                event_id=event_id,
                title=a["title"],
                body=a["body"],
                visible=True,
            )
        )
        counts["announcements_created"] += 1

    # ── Applications ── (the petition desk gets a queue to demo)
    for a in _application_data():
        if db.query(Application).filter(Application.email == a["email"]).first():
            continue
        row = Application(
            name=a["name"],
            email=a["email"],
            team=a["team"],
            project_interest=a["interest"],
            status=a["status"],
            source="form",
        )
        if a["status"] == "rejected":
            row.decided_at = base_login + timedelta(hours=1)
        db.add(row)
        counts["applications_created"] += 1

    db.commit()
    return counts
