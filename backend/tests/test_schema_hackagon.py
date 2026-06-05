"""
Schema tests for the hackagon-inspired adoption.

Covers:
- Track, Phase, Page, Project CRUD
- Page <-> Phase O2O link
- Track unique (event_id, name)
- Project status default = "proposed"
- Submission versioning + unique (project, participant, version)
- Submission status default = "draft"
- Participant.is_waiting default = False, settable for waitlist
- User.display_name nullable
- TimestampMixin: modified_at auto-bumps on update
- AuditMixin: created_by/modified_by FK to users
"""

from __future__ import annotations

import time
import uuid

import pytest
from sqlalchemy.exc import IntegrityError


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _new_user(db, email_suffix=""):
    from app.models.user import User

    u = User(email=f"user_{uuid.uuid4()}{email_suffix}@test.local", role="user")
    db.add(u)
    db.commit()
    return u


def _new_participant(db, event_id="test-event", display_name="Tester", type_="team"):
    from app.models.participant import Participant

    p = Participant(event_id=event_id, type=type_, display_name=display_name)
    db.add(p)
    db.commit()
    return p


# ------------------------------------------------------------------ #
# User.display_name
# ------------------------------------------------------------------ #

def test_user_display_name_nullable(_set_env):
    from app.database import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        u = User(email=f"dn_{uuid.uuid4()}@test.local")
        db.add(u)
        db.commit()
        assert u.display_name is None

        u.display_name = "Carlos"
        db.commit()
        assert db.get(User, u.id).display_name == "Carlos"


# ------------------------------------------------------------------ #
# Participant.is_waiting (waitlist)
# ------------------------------------------------------------------ #

def test_participant_is_waiting_defaults_false(_set_env):
    from app.database import SessionLocal

    with SessionLocal() as db:
        p = _new_participant(db)
        assert p.is_waiting is False


def test_participant_can_be_waitlisted(_set_env):
    from app.database import SessionLocal
    from app.models.participant import Participant

    with SessionLocal() as db:
        p = Participant(
            event_id="test-event",
            type="human",
            display_name="Waitlisted",
            is_waiting=True,
        )
        db.add(p)
        db.commit()
        assert db.get(Participant, p.id).is_waiting is True


# ------------------------------------------------------------------ #
# Track
# ------------------------------------------------------------------ #

def test_track_crud(_set_env):
    from app.database import SessionLocal
    from app.models.track import Track

    with SessionLocal() as db:
        creator = _new_user(db)
        t = Track(
            event_id="test-event",
            name=f"track-{uuid.uuid4()}",
            description="AI tooling",
            created_by_user_id=creator.id,
            modified_by_user_id=creator.id,
        )
        db.add(t)
        db.commit()
        fetched = db.get(Track, t.id)
        assert fetched is not None
        assert fetched.created_at is not None
        assert fetched.modified_at is not None
        assert fetched.created_by_user_id == creator.id


def test_track_unique_per_event(_set_env):
    from app.database import SessionLocal
    from app.models.track import Track

    with SessionLocal() as db:
        name = f"dup-track-{uuid.uuid4()}"
        db.add(Track(event_id="evX", name=name))
        db.commit()

        db.add(Track(event_id="evX", name=name))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # same name, different event is OK
        db.add(Track(event_id="evY", name=name))
        db.commit()


# ------------------------------------------------------------------ #
# Phase
# ------------------------------------------------------------------ #

def test_phase_crud(_set_env):
    from datetime import datetime

    from app.database import SessionLocal
    from app.models.phase import Phase

    with SessionLocal() as db:
        ph = Phase(
            event_id="test-event",
            name="Hacking",
            description="Build phase",
            starts_at=datetime(2026, 5, 14, 9, 0),
            ends_at=datetime(2026, 5, 15, 17, 0),
        )
        db.add(ph)
        db.commit()
        fetched = db.get(Phase, ph.id)
        assert fetched is not None
        assert fetched.starts_at is not None
        assert fetched.ends_at is not None


def test_phase_dates_optional(_set_env):
    from app.database import SessionLocal
    from app.models.phase import Phase

    with SessionLocal() as db:
        ph = Phase(event_id="test-event", name="Pre-hackathon")
        db.add(ph)
        db.commit()
        assert ph.starts_at is None
        assert ph.ends_at is None


# ------------------------------------------------------------------ #
# Page
# ------------------------------------------------------------------ #

def test_page_crud(_set_env):
    from app.database import SessionLocal
    from app.models.page import Page

    with SessionLocal() as db:
        pg = Page(
            event_id="test-event",
            title="Rules",
            content="Be kind.",
            visible=True,
            order=1,
        )
        db.add(pg)
        db.commit()
        fetched = db.get(Page, pg.id)
        assert fetched is not None
        assert fetched.visible is True
        assert fetched.order == 1


def test_page_phase_o2o_link(_set_env):
    from app.database import SessionLocal
    from app.models.page import Page
    from app.models.phase import Phase

    with SessionLocal() as db:
        ph = Phase(event_id="test-event", name="Judging")
        db.add(ph)
        db.commit()

        pg = Page(
            event_id="test-event",
            title="Judging info",
            content="See criteria.",
            visible=True,
            order=0,
            phase_id=ph.id,
        )
        db.add(pg)
        db.commit()
        assert pg.phase_id == ph.id

        # second page on same phase violates O2O uniqueness
        pg2 = Page(
            event_id="test-event",
            title="Other",
            content="x",
            visible=True,
            order=2,
            phase_id=ph.id,
        )
        db.add(pg2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# ------------------------------------------------------------------ #
# Project
# ------------------------------------------------------------------ #

def test_project_default_status(_set_env):
    from app.database import SessionLocal
    from app.models.project import Project

    with SessionLocal() as db:
        p = _new_participant(db, type_="team")
        proj = Project(
            event_id="test-event",
            proposed_by_participant_id=p.id,
            title="Build a thing",
            description="A thing that does stuff.",
        )
        db.add(proj)
        db.commit()
        assert proj.status == "proposed"


def test_project_links_to_track(_set_env):
    from app.database import SessionLocal
    from app.models.project import Project
    from app.models.track import Track

    with SessionLocal() as db:
        p = _new_participant(db)
        t = Track(event_id="test-event", name=f"track-{uuid.uuid4()}")
        db.add(t)
        db.commit()

        proj = Project(
            event_id="test-event",
            track_id=t.id,
            proposed_by_participant_id=p.id,
            title="Tracked Project",
            description="...",
        )
        db.add(proj)
        db.commit()
        assert proj.track_id == t.id


# ------------------------------------------------------------------ #
# Submission (versioned)
# ------------------------------------------------------------------ #

def test_submission_default_status_and_version(_set_env):
    from app.database import SessionLocal
    from app.models.project import Project
    from app.models.submission import Submission

    with SessionLocal() as db:
        p = _new_participant(db)
        proj = Project(
            event_id="test-event",
            proposed_by_participant_id=p.id,
            title="P",
            description="d",
        )
        db.add(proj)
        db.commit()

        s = Submission(
            event_id="test-event", project_id=proj.id, participant_id=p.id
        )
        db.add(s)
        db.commit()
        assert s.status == "draft"
        assert s.version == 1


def test_submission_versions_unique_per_project_participant(_set_env):
    from app.database import SessionLocal
    from app.models.project import Project
    from app.models.submission import Submission

    with SessionLocal() as db:
        p = _new_participant(db)
        proj = Project(
            event_id="test-event",
            proposed_by_participant_id=p.id,
            title="P",
            description="d",
        )
        db.add(proj)
        db.commit()

        db.add(
            Submission(
                event_id="test-event",
                project_id=proj.id,
                participant_id=p.id,
                version=1,
            )
        )
        db.commit()

        # same version again — must fail
        db.add(
            Submission(
                event_id="test-event",
                project_id=proj.id,
                participant_id=p.id,
                version=1,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # different version is fine
        db.add(
            Submission(
                event_id="test-event",
                project_id=proj.id,
                participant_id=p.id,
                version=2,
                status="final",
            )
        )
        db.commit()

        rows = (
            db.query(Submission)
            .filter_by(project_id=proj.id, participant_id=p.id)
            .order_by(Submission.version)
            .all()
        )
        assert [r.version for r in rows] == [1, 2]
        assert rows[1].status == "final"


# ------------------------------------------------------------------ #
# Mixin behaviour
# ------------------------------------------------------------------ #

def test_modified_at_bumps_on_update(_set_env):
    from app.database import SessionLocal
    from app.models.track import Track

    with SessionLocal() as db:
        t = Track(event_id="test-event", name=f"bump-{uuid.uuid4()}")
        db.add(t)
        db.commit()
        original_modified = t.modified_at

        # ensure clock moves measurably
        time.sleep(0.01)
        t.description = "edited"
        db.commit()
        assert t.modified_at > original_modified


def test_audit_columns_present_on_new_models(_set_env):
    """All new entities expose created_by_user_id + modified_by_user_id."""
    from app.models.page import Page
    from app.models.phase import Phase
    from app.models.project import Project
    from app.models.submission import Submission
    from app.models.track import Track

    for model in (Track, Phase, Page, Project, Submission):
        cols = {c.name for c in model.__table__.columns}
        assert "created_by_user_id" in cols, f"{model.__name__} missing created_by_user_id"
        assert "modified_by_user_id" in cols, f"{model.__name__} missing modified_by_user_id"
        assert "created_at" in cols
        assert "modified_at" in cols
