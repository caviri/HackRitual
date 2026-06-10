"""
Applications tests — the petition desk.

Covers:
- POST /api/applications (201, 409 duplicate, 422 invalid)
- GET  /api/admin/applications (list, filter, counts, auth)
- POST /api/admin/applications/{id}/approve (creates user + password, 409 re-decide)
- POST /api/admin/applications/{id}/reject
- End-to-end: approve → log in with the issued password
- POST /api/admin/users/{id}/regenerate-password
"""

from __future__ import annotations

import re
import uuid

import pytest


def _admin_cookie():
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        admin = db.query(User).filter_by(role="admin", status="active").first()
        if admin is None:
            admin = User(email=f"adm_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
        return create_jwt(admin)


def _payload(**overrides):
    body = {
        "name": "Mira Vale",
        "email": f"app_{uuid.uuid4()}@test.local",
        "team": "The Foragers",
        "project_interest": "Mushroom-based dyes.",
    }
    body.update(overrides)
    return body


# ------------------------------------------------------------------ #
# Public form
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_submit_application_returns_201(client):
    resp = await client.post("/api/applications", json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["id"]


@pytest.mark.anyio
async def test_submit_application_duplicate_email_409(client):
    payload = _payload()
    assert (await client.post("/api/applications", json=payload)).status_code == 201
    resp = await client.post("/api/applications", json=payload)
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_submit_application_existing_user_409(client):
    from app.database import SessionLocal
    from app.models.user import User

    email = f"existing_{uuid.uuid4()}@test.local"
    with SessionLocal() as db:
        db.add(User(email=email, role="user"))
        db.commit()

    resp = await client.post("/api/applications", json=_payload(email=email))
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_submit_application_invalid_email_422(client):
    resp = await client.post("/api/applications", json=_payload(email="not-an-email"))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_submit_application_blank_name_422(client):
    resp = await client.post("/api/applications", json=_payload(name=""))
    assert resp.status_code == 422


# ------------------------------------------------------------------ #
# Admin list
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_list_applications_requires_admin(client):
    resp = await client.get("/api/admin/applications")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_list_applications_filter_and_counts(client):
    cookie = _admin_cookie()
    created = await client.post("/api/applications", json=_payload())
    app_id = created.json()["id"]

    resp = await client.get(
        "/api/admin/applications?status=pending", cookies={"session": cookie}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert any(a["id"] == app_id for a in body["applications"])
    assert set(body["counts"]) == {"pending", "approved", "rejected"}
    assert body["counts"]["pending"] >= 1


@pytest.mark.anyio
async def test_list_applications_invalid_status_422(client):
    cookie = _admin_cookie()
    resp = await client.get(
        "/api/admin/applications?status=bogus", cookies={"session": cookie}
    )
    assert resp.status_code == 422


# ------------------------------------------------------------------ #
# Approve / reject
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_approve_creates_user_with_password(client):
    cookie = _admin_cookie()
    created = await client.post("/api/applications", json=_payload())
    app_id = created.json()["id"]

    resp = await client.post(
        f"/api/admin/applications/{app_id}/approve", cookies={"session": cookie}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["user"] is not None
    assert re.fullmatch(r"[a-z]+-[a-z]+-\d{4}", body["user"]["access_password"])
    assert body["user"]["display_name"] == "Mira Vale"


@pytest.mark.anyio
async def test_approve_twice_returns_409(client):
    cookie = _admin_cookie()
    created = await client.post("/api/applications", json=_payload())
    app_id = created.json()["id"]

    first = await client.post(
        f"/api/admin/applications/{app_id}/approve", cookies={"session": cookie}
    )
    assert first.status_code == 200
    second = await client.post(
        f"/api/admin/applications/{app_id}/approve", cookies={"session": cookie}
    )
    assert second.status_code == 409


@pytest.mark.anyio
async def test_reject_application(client):
    cookie = _admin_cookie()
    created = await client.post("/api/applications", json=_payload())
    app_id = created.json()["id"]

    resp = await client.post(
        f"/api/admin/applications/{app_id}/reject", cookies={"session": cookie}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["user"] is None


@pytest.mark.anyio
async def test_approve_missing_application_404(client):
    cookie = _admin_cookie()
    resp = await client.post(
        "/api/admin/applications/nope/approve", cookies={"session": cookie}
    )
    assert resp.status_code == 404


# ------------------------------------------------------------------ #
# End-to-end: approval → login
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_approved_user_can_log_in(client):
    cookie = _admin_cookie()
    payload = _payload()
    created = await client.post("/api/applications", json=payload)
    app_id = created.json()["id"]

    approved = await client.post(
        f"/api/admin/applications/{app_id}/approve", cookies={"session": cookie}
    )
    password = approved.json()["user"]["access_password"]

    login = await client.post("/api/auth/login", json={"password": password})
    assert login.status_code == 200
    assert login.json()["user"]["email"] == payload["email"].lower()


# ------------------------------------------------------------------ #
# Regenerate password
# ------------------------------------------------------------------ #

@pytest.mark.anyio
async def test_regenerate_password_rotates_credential(client):
    cookie = _admin_cookie()
    created = await client.post("/api/applications", json=_payload())
    app_id = created.json()["id"]
    approved = await client.post(
        f"/api/admin/applications/{app_id}/approve", cookies={"session": cookie}
    )
    user = approved.json()["user"]
    old_password = user["access_password"]

    resp = await client.post(
        f"/api/admin/users/{user['id']}/regenerate-password", cookies={"session": cookie}
    )
    assert resp.status_code == 200
    new_password = resp.json()["access_password"]
    assert new_password != old_password
    assert re.fullmatch(r"[a-z]+-[a-z]+-\d{4}", new_password)

    # Old credential is dead; new one works.
    assert (
        await client.post("/api/auth/login", json={"password": old_password})
    ).status_code == 401
    assert (
        await client.post("/api/auth/login", json={"password": new_password})
    ).status_code == 200


@pytest.mark.anyio
async def test_regenerate_password_requires_admin(client):
    resp = await client.post("/api/admin/users/whoever/regenerate-password")
    assert resp.status_code == 401
