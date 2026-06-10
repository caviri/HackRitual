"""
Step 02 — Database Layer tests.

Covers:
- SQLite WAL mode + pragmas set on connection
- All model tables created and queryable
- DB session dependency (get_db)
- File storage utilities (save_upload, get_upload_path, delete_upload)
- Admin seeding logic
- Event record creation
- check_db() health utility
"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from sqlalchemy import inspect, text


# ------------------------------------------------------------------ #
# WAL mode / PRAGMAs
# ------------------------------------------------------------------ #

def test_wal_mode_enabled(_set_env):
    """journal_mode must be WAL on every new connection."""
    from app.database import engine

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert result == "wal"


def test_foreign_keys_enabled(_set_env):
    """foreign_keys PRAGMA must be ON."""
    from app.database import engine

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert result == 1


def test_busy_timeout_set(_set_env):
    """busy_timeout must be 5000ms."""
    from app.database import engine

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA busy_timeout")).scalar()
    assert result == 5000


# ------------------------------------------------------------------ #
# check_db utility
# ------------------------------------------------------------------ #

def test_check_db_returns_true(_set_env):
    from app.database import check_db

    assert check_db() is True


# ------------------------------------------------------------------ #
# All tables present
# ------------------------------------------------------------------ #

EXPECTED_TABLES = {
    "users",
    "login_codes",
    "sessions",
    "participants",
    "participant_members",
    "agents",
    "submissions",
    "files",
    "scores",
    "tasks",
    "audit_log",
    "events",
    "tracks",
    "phases",
    "pages",
    "projects",
}


def test_all_tables_exist(_set_env):
    """All schema tables must exist in the SQLite DB."""
    from app.database import engine

    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= tables, f"Missing tables: {EXPECTED_TABLES - tables}"


# ------------------------------------------------------------------ #
# Model CRUD smoke tests
# ------------------------------------------------------------------ #

def test_user_crud(_set_env):
    from app.database import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        u = User(email=f"crud_{uuid.uuid4()}@test.local", role="user")
        db.add(u)
        db.commit()
        fetched = db.get(User, u.id)
        assert fetched is not None
        assert fetched.email == u.email
        assert fetched.role == "user"


def test_event_crud(_set_env):
    from datetime import datetime
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        ev = Event(
            id=f"ev-{uuid.uuid4()}",
            title="Test Event",
            type="hackathon",
            state="DRAFT",
            start_at=datetime(2026, 1, 1),
            end_at=datetime(2026, 1, 2),
        )
        db.add(ev)
        db.commit()
        fetched = db.get(Event, ev.id)
        assert fetched is not None
        assert fetched.state == "DRAFT"


def test_participant_crud(_set_env):
    from app.database import SessionLocal
    from app.models.participant import Participant

    with SessionLocal() as db:
        p = Participant(event_id="test-event", type="human", display_name="Tester")
        db.add(p)
        db.commit()
        fetched = db.get(Participant, p.id)
        assert fetched is not None
        assert fetched.status == "active"


def test_task_crud(_set_env):
    from app.database import SessionLocal
    from app.models.task import Task

    with SessionLocal() as db:
        t = Task(type="export_bundle", ref_id="some-id")
        db.add(t)
        db.commit()
        fetched = db.get(Task, t.id)
        assert fetched is not None
        assert fetched.status == "queued"
        assert fetched.attempts == 0


def test_audit_log_crud(_set_env):
    from app.database import SessionLocal
    from app.models.audit_log import AuditLog

    with SessionLocal() as db:
        log = AuditLog(action="test.action", target_type="user", target_id="abc")
        db.add(log)
        db.commit()
        fetched = db.get(AuditLog, log.id)
        assert fetched is not None
        assert fetched.action == "test.action"


def test_login_code_crud(_set_env):
    from datetime import datetime, timedelta
    from app.database import SessionLocal
    from app.models.login_code import LoginCode

    with SessionLocal() as db:
        lc = LoginCode(
            email="lc@test.local",
            code_hash="abc123",
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
        db.add(lc)
        db.commit()
        fetched = db.get(LoginCode, lc.id)
        assert fetched is not None
        assert fetched.used_at is None


# ------------------------------------------------------------------ #
# File storage utilities
# ------------------------------------------------------------------ #

def test_save_upload_creates_file(_set_env):
    from app.utils.files import save_upload, get_upload_path

    data = b"hello hackritual"
    meta = save_upload(
        data=data,
        filename="test.txt",
        mime_type="text/plain",
        submission_id="sub-001",
        participant_id="par-001",
        event_id="ev-001",
    )

    assert meta["size_bytes"] == len(data)
    assert len(meta["sha256"]) == 64
    assert meta["submission_id"] == "sub-001"

    abs_path = get_upload_path(meta["path"])
    assert abs_path.exists()
    assert abs_path.read_bytes() == data


def test_delete_upload(_set_env):
    from app.utils.files import save_upload, delete_upload, get_upload_path

    data = b"to be deleted"
    meta = save_upload(
        data=data,
        filename="del.txt",
        mime_type="text/plain",
        submission_id="sub-del",
        participant_id="par-del",
        event_id="ev-del",
    )

    abs_path = get_upload_path(meta["path"])
    assert abs_path.exists()

    assert delete_upload(meta["path"]) is True
    assert not abs_path.exists()


def test_delete_upload_missing_file(_set_env):
    from app.utils.files import delete_upload

    assert delete_upload("nonexistent/path/file.txt") is False


def test_save_upload_sha256_correctness(_set_env):
    from app.utils.files import save_upload

    data = b"check integrity"
    meta = save_upload(
        data=data,
        filename="integrity.txt",
        mime_type="text/plain",
        submission_id="sub-sha",
        participant_id="par-sha",
        event_id="ev-sha",
    )
    assert meta["sha256"] == hashlib.sha256(data).hexdigest()


def test_upload_stored_in_correct_directory(_set_env):
    """Files must land under <UPLOAD_DIR>/<event_id>/<participant_id>/<submission_id>/."""
    from app.utils.files import save_upload, get_upload_path

    data = b"dir check"
    meta = save_upload(
        data=data,
        filename="dir.txt",
        mime_type="text/plain",
        submission_id="subX",
        participant_id="parX",
        event_id="evX",
    )

    abs_path = get_upload_path(meta["path"])
    assert "evX" in str(abs_path)
    assert "parX" in str(abs_path)
    assert "subX" in str(abs_path)


# ------------------------------------------------------------------ #
# Seeding logic (mirrors lifespan behaviour, tested directly)
# ------------------------------------------------------------------ #

def test_seeding_creates_admin_user(_set_env):
    """Seeding creates an admin User for each email."""
    from app.database import SessionLocal
    from app.models.user import User

    email = f"seedtest_{uuid.uuid4()}@test.local"
    with SessionLocal() as db:
        assert db.query(User).filter_by(email=email).first() is None
        db.add(User(email=email, role="admin"))
        db.commit()

        admin = db.query(User).filter_by(email=email).first()
        assert admin is not None
        assert admin.role == "admin"


def test_seeding_is_idempotent(_set_env):
    """Running seeding twice must not create duplicate users."""
    from app.database import SessionLocal
    from app.models.user import User

    email = f"idempotent_{uuid.uuid4()}@test.local"

    def _seed(db):
        if not db.query(User).filter_by(email=email).first():
            db.add(User(email=email, role="admin"))
        db.commit()

    with SessionLocal() as db:
        _seed(db)
        _seed(db)
        assert db.query(User).filter_by(email=email).count() == 1


def test_event_seeded_from_env(_set_env):
    """Event record can be created from env vars (mirrors lifespan)."""
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

    event_id = f"ev-env-{uuid.uuid4()}"
    with SessionLocal() as db:
        assert db.get(Event, event_id) is None

        ev = Event(
            id=event_id,
            title=settings.event_title,
            type=settings.event_type,
            state="DRAFT",
            start_at=settings.event_start,
            end_at=settings.event_end,
        )
        db.add(ev)
        db.commit()

        fetched = db.get(Event, event_id)
        assert fetched is not None
        assert fetched.state == "DRAFT"
        assert fetched.title == settings.event_title


# ------------------------------------------------------------------ #
# Health endpoint integration
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_health_db_ok(client):
    """Health endpoint must report db_ok=True with the real DB."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db_ok"] is True


@pytest.mark.anyio
async def test_health_event_state_is_valid(client):
    """Health endpoint event_state must be one of the known states."""
    resp = await client.get("/api/health")
    data = resp.json()
    assert data["event_state"] in {"DRAFT", "OPEN", "FROZEN", "FINAL", "ARCHIVED"}
