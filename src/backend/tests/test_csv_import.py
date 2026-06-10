"""
CSV bulk-import tests.

Covers:
- Happy path: users created with passwords, applications recorded as imports
- Team grouping: shared team value → one team participant, captain + members
- Duplicate emails skipped (user / application), bad rows collected as errors
- Whole-file failures: missing headers, empty file, oversized file → 422
- Imported users can log in
- Admin-only access
"""

from __future__ import annotations

import io
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


async def _upload(client, csv_text: str, cookie: str):
    return await client.post(
        "/api/admin/users/import-csv",
        files={"file": ("import.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")},
        cookies={"session": cookie},
    )


def _emails(n: int) -> list[str]:
    tag = uuid.uuid4().hex[:8]
    return [f"csv_{tag}_{i}@test.local" for i in range(n)]


@pytest.mark.anyio
async def test_import_creates_users_with_passwords(client):
    cookie = _admin_cookie()
    e1, e2 = _emails(2)
    resp = await _upload(
        client,
        f"name,email,team,project\nAda Hart,{e1},,\nBen Holt,{e2},,Garden sensors\n",
        cookie,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["created"]) == 2
    assert body["skipped"] == [] and body["errors"] == []
    for row in body["created"]:
        assert re.fullmatch(r"[a-z]+-[a-z]+-\d{4}", row["access_password"])

    # The application trail records the import source.
    from app.database import SessionLocal
    from app.models.application import Application

    with SessionLocal() as db:
        a = db.query(Application).filter_by(email=e1).one()
        assert a.source == "import"
        assert a.status == "approved"


@pytest.mark.anyio
async def test_import_groups_teams(client):
    cookie = _admin_cookie()
    e1, e2, e3 = _emails(3)
    team = f"Team {uuid.uuid4().hex[:6]}"
    resp = await _upload(
        client,
        f"name,email,team,project\nA,{e1},{team},\nB,{e2},{team},\nC,{e3},,\n",
        cookie,
    )
    assert resp.status_code == 200
    created = resp.json()["created"]
    assert [r["team"] for r in created] == [team, team, None]

    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember

    with SessionLocal() as db:
        teams = (
            db.query(Participant)
            .filter(Participant.type == "team", Participant.display_name == team)
            .all()
        )
        assert len(teams) == 1
        members = (
            db.query(ParticipantMember)
            .filter(ParticipantMember.participant_id == teams[0].id)
            .order_by(ParticipantMember.id)
            .all()
        )
        assert len(members) == 2
        assert sorted(m.role_in_team for m in members) == ["captain", "member"]
        assert teams[0].invite_code


@pytest.mark.anyio
async def test_import_skips_existing_and_collects_errors(client):
    from app.database import SessionLocal
    from app.models.user import User

    cookie = _admin_cookie()
    existing, fresh = _emails(2)
    with SessionLocal() as db:
        db.add(User(email=existing, role="user"))
        db.commit()

    resp = await _upload(
        client,
        "name,email,team,project\n"
        f"Old Hand,{existing},,\n"
        "No Email,,,\n"
        f"Bad Email,not-an-email,,\n"
        f",missing-name@test.local,,\n"
        f"New Face,{fresh},,\n",
        cookie,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [r["email"] for r in body["created"]] == [fresh]
    assert body["skipped"][0]["email"] == existing
    assert len(body["errors"]) == 3  # blank email, bad email, missing name


@pytest.mark.anyio
async def test_import_missing_header_422(client):
    cookie = _admin_cookie()
    resp = await _upload(client, "fullname,mail\nA,a@test.local\n", cookie)
    assert resp.status_code == 422
    assert "name" in resp.json()["detail"]


@pytest.mark.anyio
async def test_import_empty_file_422(client):
    cookie = _admin_cookie()
    resp = await _upload(client, "", cookie)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_import_oversized_file_422(client):
    cookie = _admin_cookie()
    resp = await _upload(client, "name,email\n" + "x" * (1024 * 1024 + 1), cookie)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_import_requires_admin(client):
    resp = await client.post(
        "/api/admin/users/import-csv",
        files={"file": ("x.csv", io.BytesIO(b"name,email\n"), "text/csv")},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_imported_user_can_log_in(client):
    cookie = _admin_cookie()
    (email,) = _emails(1)
    resp = await _upload(client, f"name,email\nLog In,{email}\n", cookie)
    assert resp.status_code == 200
    password = resp.json()["created"][0]["access_password"]

    login = await client.post("/api/auth/login", json={"password": password})
    assert login.status_code == 200
    assert login.json()["user"]["email"] == email
