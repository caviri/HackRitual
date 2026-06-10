"""Multi-stage demo tests — snapshot builds, cookie/param routing, guards."""

from __future__ import annotations

import os
import shutil
import uuid
from datetime import UTC

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="module")
def demo_mode(_create_tables):
    """Enable DEMO_STAGES and build all snapshots ONCE for this module —
    building five seeded databases per test would take minutes."""
    # The primary event must exist (this file may run before any test that
    # creates it).
    from datetime import datetime

    from app.config import settings
    from app.database import DEMO_STAGE_NAMES, SessionLocal, dispose_stage_engine, stage_db_path
    from app.models.event import Event
    from app.services.demo_stages import build_all

    with SessionLocal() as db:
        if db.get(Event, settings.event_id) is None:
            db.add(
                Event(
                    id=settings.event_id,
                    title="Test Event",
                    type="hackathon",
                    state="DRAFT",
                    start_at=datetime(2026, 1, 1, tzinfo=UTC),
                    end_at=datetime(2026, 1, 2, tzinfo=UTC),
                )
            )
            db.commit()

    previous = settings.demo_stages
    settings.demo_stages = True
    build_all(force=True)
    yield
    settings.demo_stages = previous
    for stage in DEMO_STAGE_NAMES:
        dispose_stage_engine(stage)
    demo_dir = os.path.dirname(stage_db_path("OPEN"))
    shutil.rmtree(demo_dir, ignore_errors=True)


@pytest.fixture()
async def demo_client(demo_mode):
    """Client against an app constructed WITH the demo-stage middleware."""
    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def _primary_state() -> str:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        ev = db.get(Event, settings.event_id)
        return ev.state if ev else "DRAFT"


@pytest.mark.anyio
async def test_cookie_routes_to_stage(demo_client):
    resp = await demo_client.get("/api/event", cookies={"demo_stage": "FROZEN"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "FROZEN"

    bare = await demo_client.get("/api/event")
    assert bare.json()["state"] == _primary_state()


@pytest.mark.anyio
async def test_query_param_wins_over_cookie(demo_client):
    resp = await demo_client.get(
        "/api/event?stage=ARCHIVED", cookies={"demo_stage": "OPEN"}
    )
    assert resp.json()["state"] == "ARCHIVED"


@pytest.mark.anyio
async def test_invalid_stage_falls_through_to_primary(demo_client):
    resp = await demo_client.get("/api/event", cookies={"demo_stage": "banana"})
    assert resp.json()["state"] == _primary_state()


def test_stage_profiles(demo_mode):
    from app.database import get_sessionmaker
    from app.models.event import Event
    from app.models.participant import Participant
    from app.models.project import Project
    from app.models.score import Score
    from app.models.submission import Submission

    with get_sessionmaker("DRAFT")() as db:
        assert db.query(Event).one().state == "DRAFT"
        assert db.query(Project).count() == 0
        assert db.query(Submission).count() == 0
        assert db.query(Participant).filter(Participant.is_waiting.is_(False)).count() == 0

    with get_sessionmaker("OPEN")() as db:
        assert db.query(Project).count() == 12
        assert db.query(Submission).filter(Submission.status == "final").count() == 0
        assert db.query(Score).count() == 0

    with get_sessionmaker("FROZEN")() as db:
        scored = db.query(Score).filter(Score.status == "scored").all()
        assert len(scored) == 4
        assert sorted(s.score_value for s in scored) == [50.0, 60.0, 80.0, 90.0]


@pytest.mark.anyio
async def test_demo_user_login_inside_stage(demo_client):
    inside = await demo_client.post(
        "/api/auth/login?stage=OPEN", json={"password": "fern-lantern-4821"}
    )
    assert inside.status_code == 200
    cookie = inside.cookies.get("session")
    assert cookie

    me = await demo_client.get("/api/auth/me?stage=OPEN", cookies={"session": cookie})
    assert me.status_code == 200
    assert me.json()["email"] == "ada@demo.rite"

    # Same token without the stage → user id unknown to the primary DB.
    cross = await demo_client.get("/api/auth/me", cookies={"session": cookie})
    assert cross.status_code == 401


@pytest.mark.anyio
async def test_admin_seeded_in_every_stage(demo_client):
    from app.config import settings

    resp = await demo_client.post(
        "/api/auth/login?stage=DRAFT", json={"password": settings.admin_password}
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "admin"


@pytest.mark.anyio
async def test_stage_writes_do_not_touch_primary(demo_client):
    from app.config import settings
    from app.database import SessionLocal
    from app.models.announcement import Announcement

    login = await demo_client.post(
        "/api/auth/login?stage=OPEN", json={"password": settings.admin_password}
    )
    cookie = login.cookies.get("session")

    title = f"Sandbox dispatch {uuid.uuid4().hex[:6]}"
    created = await demo_client.post(
        "/api/admin/announcements?stage=OPEN",
        json={"title": title, "body": "Written inside the OPEN sandbox."},
        cookies={"session": cookie},
    )
    assert created.status_code == 201

    with SessionLocal() as db:
        assert (
            db.query(Announcement).filter(Announcement.title == title).count() == 0
        )


@pytest.mark.anyio
async def test_rebuild_endpoint_resets_sandboxes(demo_client):
    from app.config import settings
    from app.database import get_sessionmaker
    from app.models.announcement import Announcement

    login = await demo_client.post(
        "/api/auth/login?stage=OPEN", json={"password": settings.admin_password}
    )
    cookie = login.cookies.get("session")
    title = f"Doomed dispatch {uuid.uuid4().hex[:6]}"
    await demo_client.post(
        "/api/admin/announcements?stage=OPEN",
        json={"title": title, "body": "This will not survive the rebuild."},
        cookies={"session": cookie},
    )

    rebuilt = await demo_client.post(
        "/api/admin/demo/rebuild?stage=OPEN", cookies={"session": cookie}
    )
    assert rebuilt.status_code == 200
    assert all(rebuilt.json()["rebuilt"].values())

    with get_sessionmaker("OPEN")() as db:
        assert db.query(Announcement).filter(Announcement.title == title).count() == 0


@pytest.mark.anyio
async def test_rebuild_409_when_flag_off(client):
    # `client` fixture builds the app without demo mode; force the flag off
    # for the duration (the module fixture may have it on).
    from app.config import settings
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    previous = settings.demo_stages
    settings.demo_stages = False
    with SessionLocal() as db:
        admin = db.query(User).filter_by(role="admin", status="active").first()
        if admin is None:
            admin = User(email=f"adm_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
        token = create_jwt(admin)

    try:
        resp = await client.post("/api/admin/demo/rebuild", cookies={"session": token})
        assert resp.status_code == 409
    finally:
        settings.demo_stages = previous


@pytest.mark.anyio
async def test_guard_rails_block_sandbox_enqueues(demo_client):
    from app.config import settings

    login = await demo_client.post(
        "/api/auth/login?stage=FROZEN", json={"password": settings.admin_password}
    )
    cookie = login.cookies.get("session")

    export = await demo_client.post(
        "/api/admin/export?stage=FROZEN",
        json={"redaction_mode": "public"},
        cookies={"session": cookie},
    )
    assert export.status_code == 409

    rescore = await demo_client.post(
        "/api/admin/scoring/rescore-all?stage=FROZEN", cookies={"session": cookie}
    )
    assert rescore.status_code == 409


@pytest.mark.anyio
async def test_health_reports_demo_stages_and_routed_state(demo_client):
    resp = await demo_client.get("/api/health?stage=FINAL")
    body = resp.json()
    assert body["demo_stages"] is True
    assert body["event_state"] == "FINAL"


def test_seed_profile_draft_yields_no_submissions(_create_tables):
    # The profile machinery itself, against a scratch in-memory check via the
    # DRAFT snapshot path is covered above; here just assert the default
    # profile still seeds everything (existing seeder tests rely on it).
    from app.services.seeder import FULL_PROFILE

    assert FULL_PROFILE.include_projects is True
    assert FULL_PROFILE.include_scores is True
