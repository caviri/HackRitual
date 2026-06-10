"""
Authentication tests — access-password login.

Covers:
- Password generation (format, uniqueness)
- Password lookup (happy path, wrong, inactive, NULL)
- JWT creation and decoding
- Login rate limiting (per-IP failures)
- POST /api/auth/login (200, 401, 422, 429)
- POST /api/auth/logout (204)
- POST /api/auth/refresh (200, 401)
- GET  /api/auth/me (200, 401)
- Solo participant auto-creation on first login
- require_admin rejects non-admins
"""

from __future__ import annotations

import re
import time
import uuid

import pytest


def _make_user(db, password: str, role: str = "user", status: str = "active"):
    from app.models.user import User

    user = User(
        email=f"u_{uuid.uuid4()}@test.local",
        role=role,
        status=status,
        access_password=password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _unique_password() -> str:
    return f"test-{uuid.uuid4().hex[:10]}"


# ------------------------------------------------------------------ #
# Password generation
# ------------------------------------------------------------------ #

def test_generate_password_format():
    from app.services.passwords import generate_password

    for _ in range(20):
        pw = generate_password()
        assert re.fullmatch(r"[a-z]+-[a-z]+-\d{4}", pw), pw


def test_generate_unique_password_avoids_collisions(_set_env):
    from app.database import SessionLocal
    from app.services.passwords import generate_unique_password

    with SessionLocal() as db:
        pws = {generate_unique_password(db) for _ in range(10)}
    assert len(pws) == 10


# ------------------------------------------------------------------ #
# Password lookup
# ------------------------------------------------------------------ #

def test_get_user_by_password_happy_path(_set_env):
    from app.database import SessionLocal
    from app.services.auth import get_user_by_password

    pw = _unique_password()
    with SessionLocal() as db:
        user = _make_user(db, pw)
        found = get_user_by_password(db, pw)
        assert found is not None and found.id == user.id
        # Lookup is case/whitespace tolerant
        assert get_user_by_password(db, f"  {pw.upper()}  ").id == user.id


def test_get_user_by_password_rejects_wrong_and_empty(_set_env):
    from app.database import SessionLocal
    from app.services.auth import get_user_by_password

    with SessionLocal() as db:
        _make_user(db, _unique_password())
        assert get_user_by_password(db, "no-such-password-0000") is None
        assert get_user_by_password(db, "") is None
        assert get_user_by_password(db, None) is None


def test_get_user_by_password_rejects_inactive(_set_env):
    from app.database import SessionLocal
    from app.services.auth import get_user_by_password

    pw = _unique_password()
    with SessionLocal() as db:
        _make_user(db, pw, status="inactive")
        assert get_user_by_password(db, pw) is None


# ------------------------------------------------------------------ #
# JWT
# ------------------------------------------------------------------ #

def test_jwt_roundtrip(_set_env):
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt, decode_jwt

    with SessionLocal() as db:
        user = User(email=f"jwt_{uuid.uuid4()}@test.local", role="user")
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_jwt(user)
        payload = decode_jwt(token)

        assert payload["sub"] == user.id
        assert payload["email"] == user.email
        assert payload["role"] == "user"


def test_invalid_jwt_raises(_set_env):
    from jose import JWTError

    from app.services.auth import decode_jwt

    with pytest.raises(JWTError):
        decode_jwt("not.a.valid.token")


def test_is_near_expiry():
    from app.services.auth import is_near_expiry

    near = {"exp": int(time.time()) + 30 * 60}   # 30 min → within 1h threshold
    far  = {"exp": int(time.time()) + 90 * 60}   # 90 min → outside threshold

    assert is_near_expiry(near) is True
    assert is_near_expiry(far) is False


# ------------------------------------------------------------------ #
# Rate limiting
# ------------------------------------------------------------------ #

def test_rate_limit_login_counts_failures():
    from app.services import auth as svc

    ip = f"10.0.0.{uuid.uuid4().int % 250}"
    svc._rate_buckets.pop(f"login:ip:{ip}", None)

    for _ in range(10):
        assert svc.check_rate_limit_login(ip) is True
        svc.record_login_failure(ip)
    assert svc.check_rate_limit_login(ip) is False

    svc.clear_login_failures(ip)
    assert svc.check_rate_limit_login(ip) is True


def test_rate_limit_login_no_ip_allowed():
    from app.services import auth as svc

    assert svc.check_rate_limit_login(None) is True


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _get_valid_session_cookie(client_headers: dict) -> str | None:
    """Extract session= value from Set-Cookie header."""
    sc = client_headers.get("set-cookie", "")
    for part in sc.split(";"):
        part = part.strip()
        if part.startswith("session="):
            return part[len("session="):]
    return None


async def _full_login(client, password: str | None = None) -> tuple[str, str]:
    """Create a user with a known password and log in over HTTP.

    Returns (session_cookie, user_email).
    """
    from app.database import SessionLocal

    pw = password or _unique_password()
    with SessionLocal() as db:
        user = _make_user(db, pw)
        email = user.email

    resp = await client.post("/api/auth/login", json={"password": pw})
    assert resp.status_code == 200, resp.text
    cookie = _get_valid_session_cookie(dict(resp.headers))
    return cookie, email


# ------------------------------------------------------------------ #
# POST /api/auth/login
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_login_success_sets_cookie_and_returns_user(client):
    from app.database import SessionLocal

    pw = _unique_password()
    with SessionLocal() as db:
        user = _make_user(db, pw)

    resp = await client.post("/api/auth/login", json={"password": pw})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == user.email
    assert _get_valid_session_cookie(dict(resp.headers))


@pytest.mark.anyio
async def test_login_wrong_password_returns_401(client):
    resp = await client.post("/api/auth/login", json={"password": "nope-nope-0000"})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_short_password_returns_422(client):
    resp = await client.post("/api/auth/login", json={"password": "ab"})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_login_inactive_user_returns_401(client):
    from app.database import SessionLocal

    pw = _unique_password()
    with SessionLocal() as db:
        _make_user(db, pw, status="inactive")

    resp = await client.post("/api/auth/login", json={"password": pw})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_rate_limited_after_failures(client):
    from app.services import auth as svc

    ip = "203.0.113.77"
    svc._rate_buckets.pop(f"login:ip:{ip}", None)
    headers = {"x-forwarded-for": ip}

    for _ in range(10):
        r = await client.post(
            "/api/auth/login", json={"password": "wrong-wrong-0000"}, headers=headers
        )
        assert r.status_code == 401

    r = await client.post(
        "/api/auth/login", json={"password": "wrong-wrong-0000"}, headers=headers
    )
    assert r.status_code == 429
    svc._rate_buckets.pop(f"login:ip:{ip}", None)


@pytest.mark.anyio
async def test_login_updates_last_login_at(client):
    from app.database import SessionLocal
    from app.models.user import User

    pw = _unique_password()
    with SessionLocal() as db:
        user = _make_user(db, pw)
        assert user.last_login_at is None
        uid = user.id

    resp = await client.post("/api/auth/login", json={"password": pw})
    assert resp.status_code == 200

    with SessionLocal() as db:
        assert db.get(User, uid).last_login_at is not None


@pytest.mark.anyio
async def test_login_creates_solo_participant_when_open(client):
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember

    from datetime import datetime, timezone

    with SessionLocal() as db:
        event = db.get(Event, settings.event_id)
        if event is None:
            event = Event(
                id=settings.event_id,
                title="Test Event",
                type="hackathon",
                start_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
            db.add(event)
        previous_state = event.state or "DRAFT"
        event.state = "OPEN"
        db.commit()

    try:
        pw = _unique_password()
        with SessionLocal() as db:
            user = _make_user(db, pw)
            uid = user.id

        resp = await client.post("/api/auth/login", json={"password": pw})
        assert resp.status_code == 200

        with SessionLocal() as db:
            p = (
                db.query(Participant)
                .join(ParticipantMember, ParticipantMember.participant_id == Participant.id)
                .filter(ParticipantMember.user_id == uid)
                .first()
            )
            assert p is not None
            assert p.type == "human"
    finally:
        with SessionLocal() as db:
            event = db.get(Event, settings.event_id)
            event.state = previous_state
            db.commit()


# ------------------------------------------------------------------ #
# Session lifecycle: me / logout / refresh
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_me_returns_current_user(client):
    cookie, email = await _full_login(client)

    resp = await client.get("/api/auth/me", cookies={"session": cookie})
    assert resp.status_code == 200
    assert resp.json()["email"] == email


@pytest.mark.anyio
async def test_me_unauthenticated_returns_401(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_logout_clears_cookie(client):
    cookie, _ = await _full_login(client)

    resp = await client.post("/api/auth/logout", cookies={"session": cookie})
    assert resp.status_code == 204
    sc = resp.headers.get("set-cookie", "")
    assert "session=" in sc  # cleared (expired) cookie sent back


@pytest.mark.anyio
async def test_refresh_with_valid_token(client):
    cookie, email = await _full_login(client)

    resp = await client.post("/api/auth/refresh", cookies={"session": cookie})
    assert resp.status_code == 200
    assert resp.json()["email"] == email


@pytest.mark.anyio
async def test_refresh_without_token_returns_401(client):
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_refresh_with_garbage_token_returns_401(client):
    resp = await client.post("/api/auth/refresh", cookies={"session": "garbage"})
    assert resp.status_code == 401


# ------------------------------------------------------------------ #
# Role guard
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_require_admin_rejects_regular_user(client):
    cookie, _ = await _full_login(client)

    resp = await client.get("/api/admin/users", cookies={"session": cookie})
    assert resp.status_code == 403
