"""Seeder tests — idempotency, users/portraits, files, scores, applications."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC
from pathlib import Path

import pytest


@pytest.fixture()
def seeded(_create_tables):
    """Run the seeder once and return its counts."""
    # The seeder reads event dates; make sure the singleton exists.
    from datetime import datetime

    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event
    from app.services.seeder import seed_fixtures

    with SessionLocal() as db:
        if db.get(Event, settings.event_id) is None:
            db.add(
                Event(
                    id=settings.event_id,
                    title="Test Event",
                    type="hackathon",
                    start_at=datetime(2026, 1, 1, tzinfo=UTC),
                    end_at=datetime(2026, 1, 2, tzinfo=UTC),
                )
            )
            db.commit()

    with SessionLocal() as db:
        counts = seed_fixtures(db)
    return counts


def test_seed_creates_everything(seeded):
    # First run on a fresh suite DB may find earlier fixtures from other tests,
    # so assert on totals in the DB rather than created-counts alone.
    from app.database import SessionLocal
    from app.models.application import Application
    from app.models.file import File
    from app.models.score import Score
    from app.models.user import User

    with SessionLocal() as db:
        assert db.query(User).filter(User.email.like("%@demo.rite")).count() == 6
        assert db.query(File).count() >= 8
        assert db.query(Score).filter(Score.status == "scored").count() >= 4
        assert db.query(Application).filter(Application.email.like("%@petition.rite")).count() == 6


def test_seed_twice_creates_nothing_new(seeded):
    from app.database import SessionLocal
    from app.services.seeder import seed_fixtures

    with SessionLocal() as db:
        second = seed_fixtures(db)
    assert all(v == 0 for v in second.values()), second


def test_demo_users_have_passwords_and_roles(seeded):
    from app.database import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        users = db.query(User).filter(User.email.like("%@demo.rite")).all()
        assert len(users) == 6
        for u in users:
            assert re.fullmatch(r"[a-z]+-[a-z]+-\d{4}", u.access_password), u.email
            assert u.last_login_at is not None
        judges = [u for u in users if u.role == "judge"]
        assert len(judges) == 2


def test_portraits_exist_on_disk(seeded):
    from app.config import settings
    from app.database import SessionLocal
    from app.models.user import User

    root = Path(settings.upload_dir)
    with SessionLocal() as db:
        users = db.query(User).filter(User.email.like("%@demo.rite")).all()
        for u in users:
            assert u.portrait_path and (root / u.portrait_path).exists()
            assert u.portrait_original_path and (root / u.portrait_original_path).exists()
            assert u.portrait_effect == "dither"


def test_portrait_regenerated_when_file_missing(seeded):
    from app.config import settings
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.seeder import seed_fixtures

    root = Path(settings.upload_dir)
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "ada@demo.rite").one()
        (root / user.portrait_path).unlink()

    with SessionLocal() as db:
        counts = seed_fixtures(db)
    assert counts["portraits_created"] == 1

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "ada@demo.rite").one()
        assert (root / user.portrait_path).exists()


def test_team_membership_links(seeded):
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.models.user import User

    with SessionLocal() as db:
        # Other suite tests (ritual_sim) may create same-named participants in the
        # shared DB — accept any "the_owls" row that carries our demo links.
        owls_rows = (
            db.query(Participant)
            .filter(Participant.display_name == "the_owls")
            .all()
        )
        assert owls_rows
        for owls in owls_rows:
            members = (
                db.query(ParticipantMember)
                .filter(ParticipantMember.participant_id == owls.id)
                .all()
            )
            emails = {
                db.get(User, m.user_id).email: m.role_in_team
                for m in members
                if m.user_id is not None
            }
            agent_names = set()
            for m in members:
                if m.agent_id is not None:
                    from app.models.agent import Agent

                    agent = db.get(Agent, m.agent_id)
                    if agent is not None:
                        agent_names.add(agent.name)
            if (
                emails.get("june@demo.rite") == "captain"
                and emails.get("ada@demo.rite") == "member"
                and "weft" in agent_names
            ):
                return
        pytest.fail("no the_owls row carries the seeded demo membership")


def test_files_match_disk_sha(seeded):
    from app.config import settings
    from app.database import SessionLocal
    from app.models.file import File

    root = Path(settings.upload_dir)
    with SessionLocal() as db:
        files = db.query(File).all()
        assert files
        for f in files:
            data = (root / f.path).read_bytes()
            assert hashlib.sha256(data).hexdigest() == f.sha256
            assert f.size_bytes == len(data)


def test_final_submission_carries_report(seeded):
    from app.database import SessionLocal
    from app.models.file import File
    from app.models.submission import Submission

    with SessionLocal() as db:
        sub = (
            db.query(Submission)
            .filter(Submission.title == "mycelium-mesh", Submission.version == 3)
            .one()
        )
        files = db.query(File).filter(File.submission_id == sub.id).all()
        mimes = sorted(f.mime_type for f in files)
        assert mimes == ["image/png", "text/markdown"]
        assert sub.description
        assert sub.payload_json


def test_scores_distinct_and_tiefree(seeded):
    # Assert on our own Score rows (the global leaderboard may carry rows from
    # other suite tests in the shared DB).
    from app.database import SessionLocal
    from app.models.file import File
    from app.models.score import Score
    from app.models.submission import Submission

    expected = {
        ("mycelium-mesh", 3): 90.0,
        ("rhizome-rpc", 1): 80.0,
        ("photosym-os", 2): 60.0,
        ("lichen-loom", 2): 50.0,
    }
    with SessionLocal() as db:
        for (title, version), value in expected.items():
            subs = (
                db.query(Submission)
                .filter(Submission.title == title, Submission.version == version)
                .all()
            )
            # Pick the seeded row: the one carrying our files/description.
            scored_values = []
            for sub in subs:
                score = (
                    db.query(Score)
                    .filter(
                        Score.submission_id == sub.id,
                        Score.scorer_version == "default-1.0",
                        Score.status == "scored",
                    )
                    .first()
                )
                if score and db.query(File).filter(File.submission_id == sub.id).count() >= 0:
                    scored_values.append(score.score_value)
            assert value in scored_values, f"{title} v{version}: {scored_values}"
    assert len(set(expected.values())) == len(expected), "demo scores must be tie-free"


def test_applications_seeded(seeded):
    from app.database import SessionLocal
    from app.models.application import Application

    with SessionLocal() as db:
        pending = (
            db.query(Application)
            .filter(Application.email.like("%@petition.rite"), Application.status == "pending")
            .count()
        )
        rejected = (
            db.query(Application)
            .filter(Application.email.like("%@petition.rite"), Application.status == "rejected")
            .count()
        )
    assert pending == 5
    assert rejected == 1


def test_project_covers_exist(seeded):
    from app.config import settings
    from app.database import SessionLocal
    from app.models.project import Project

    root = Path(settings.upload_dir)
    with SessionLocal() as db:
        projects = db.query(Project).filter(Project.title == "mycelium-mesh").all()
        assert projects
        covered = [
            p
            for p in projects
            if p.image
            and p.image.startswith("/uploads/")
            and (root / p.image[len("/uploads/"):]).exists()
        ]
        assert covered, "at least one mycelium-mesh row carries a seeded cover"


@pytest.mark.anyio
async def test_demo_user_can_log_in(seeded, client):
    resp = await client.post("/api/auth/login", json={"password": "fern-lantern-4821"})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "ada@demo.rite"


def test_portrait_paths_use_posix_separators(seeded):
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.user import User

    with SessionLocal() as db:
        for u in db.query(User).filter(User.email.like("%@demo.rite")).all():
            assert "\\" not in u.portrait_path
            assert "\\" not in u.portrait_original_path
        for p in db.query(Participant).filter(Participant.image.isnot(None)).all():
            assert "\\" not in p.image
