"""Announcement tests — public feed, admin CRUD, visibility, auth."""

from __future__ import annotations

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
        "title": f"Dispatch {uuid.uuid4().hex[:6]}",
        "body": "The gates open at the appointed hour. Bring your keys.",
    }
    body.update(overrides)
    return body


@pytest.mark.anyio
async def test_create_and_list_public(client):
    cookie = _admin_cookie()
    created = await client.post(
        "/api/admin/announcements", json=_payload(), cookies={"session": cookie}
    )
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["visible"] is True

    public = await client.get("/api/announcements")
    assert public.status_code == 200
    assert any(a["id"] == row["id"] for a in public.json())


@pytest.mark.anyio
async def test_hidden_announcement_not_public(client):
    cookie = _admin_cookie()
    created = await client.post(
        "/api/admin/announcements",
        json=_payload(visible=False),
        cookies={"session": cookie},
    )
    row = created.json()

    public = await client.get("/api/announcements")
    assert all(a["id"] != row["id"] for a in public.json())

    # ...but the admin list carries it.
    admin_list = await client.get(
        "/api/admin/announcements", cookies={"session": cookie}
    )
    assert any(a["id"] == row["id"] for a in admin_list.json())


@pytest.mark.anyio
async def test_update_and_toggle_visibility(client):
    cookie = _admin_cookie()
    created = await client.post(
        "/api/admin/announcements", json=_payload(), cookies={"session": cookie}
    )
    row = created.json()

    patched = await client.patch(
        f"/api/admin/announcements/{row['id']}",
        json={"title": "Recast title", "visible": False},
        cookies={"session": cookie},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Recast title"
    assert patched.json()["visible"] is False

    empty = await client.patch(
        f"/api/admin/announcements/{row['id']}",
        json={},
        cookies={"session": cookie},
    )
    assert empty.status_code == 422


@pytest.mark.anyio
async def test_delete_announcement(client):
    cookie = _admin_cookie()
    created = await client.post(
        "/api/admin/announcements", json=_payload(), cookies={"session": cookie}
    )
    row = created.json()

    deleted = await client.delete(
        f"/api/admin/announcements/{row['id']}", cookies={"session": cookie}
    )
    assert deleted.status_code == 204

    public = await client.get("/api/announcements")
    assert all(a["id"] != row["id"] for a in public.json())


@pytest.mark.anyio
async def test_admin_endpoints_require_admin(client):
    assert (await client.post("/api/admin/announcements", json=_payload())).status_code == 401
    assert (await client.get("/api/admin/announcements")).status_code == 401


@pytest.mark.anyio
async def test_validation_limits(client):
    cookie = _admin_cookie()
    too_long = await client.post(
        "/api/admin/announcements",
        json=_payload(title="x" * 201),
        cookies={"session": cookie},
    )
    assert too_long.status_code == 422
    blank = await client.post(
        "/api/admin/announcements",
        json=_payload(body=""),
        cookies={"session": cookie},
    )
    assert blank.status_code == 422
