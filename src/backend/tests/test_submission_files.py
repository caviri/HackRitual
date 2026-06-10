"""
Tests for submission file attachments (Step 07 completion):
controlled upload, listing, owner/admin-gated streaming download, and delete.
"""

import hashlib
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import status


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _set_event(state: str = "OPEN") -> None:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        ev = db.get(Event, settings.event_id)
        if ev is None:
            ev = Event(
                id=settings.event_id,
                title="Test Event",
                type="hackathon",
                start_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
            db.add(ev)
        ev.state = state
        ev.config_json = None
        db.commit()


def _make_participant(role: str = "user") -> tuple[str, str]:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"file_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.flush()
        p = Participant(
            event_id=settings.event_id,
            type="human",
            display_name=f"P-{user.id[:6]}",
            status="active",
        )
        db.add(p)
        db.flush()
        db.add(
            ParticipantMember(
                participant_id=p.id, user_id=user.id, role_in_team="captain"
            )
        )
        db.commit()
        return create_jwt(user), p.id


def _make_submission(participant_id: str) -> str:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.project import Project
    from app.models.submission import Submission

    with SessionLocal() as db:
        proj = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=participant_id,
            title=f"proj-{uuid.uuid4().hex[:8]}",
            description="d",
            status="proposed",
        )
        db.add(proj)
        db.flush()
        sub = Submission(
            event_id=settings.event_id,
            project_id=proj.id,
            participant_id=participant_id,
            version=1,
            title="t",
            status="draft",
        )
        db.add(sub)
        db.commit()
        return sub.id


def _file(name="solution.json", content=b'{"k":1}', mime="application/json"):
    return {"file": (name, content, mime)}


# ============================================================================ #
# Attach
# ============================================================================ #
class TestAttach:
    @pytest.mark.asyncio
    async def test_attach_and_metadata(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        sub = _make_submission(pid)
        content = b'{"model": "v2"}'

        resp = await client.post(
            f"/api/submissions/{sub}/files",
            files=_file("model.json", content),
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["filename"] == "model.json"
        assert body["mime_type"] == "application/json"
        assert body["size_bytes"] == len(content)
        assert body["sha256"] == hashlib.sha256(content).hexdigest()

    @pytest.mark.asyncio
    async def test_unsupported_type_rejected(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        sub = _make_submission(pid)
        resp = await client.post(
            f"/api/submissions/{sub}/files",
            files=_file("evil.exe", b"MZ", "application/x-msdownload"),
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    @pytest.mark.asyncio
    async def test_attach_blocked_when_not_open(self, client):
        _set_event("FROZEN")
        token, pid = _make_participant()
        sub = _make_submission(pid)
        resp = await client.post(
            f"/api/submissions/{sub}/files",
            files=_file(),
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_non_owner_cannot_attach(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        intruder, _ = _make_participant()
        sub = _make_submission(pid)
        resp = await client.post(
            f"/api/submissions/{sub}/files",
            files=_file(),
            headers=_headers(intruder),
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================ #
# List + download
# ============================================================================ #
class TestListAndDownload:
    @pytest.mark.asyncio
    async def test_list_and_download_roundtrip(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        sub = _make_submission(pid)
        content = b"# notes\nhello"
        await client.post(
            f"/api/submissions/{sub}/files",
            files=_file("notes.md", content, "text/markdown"),
            headers=_headers(token),
        )

        listing = await client.get(f"/api/submissions/{sub}/files")
        assert listing.status_code == 200
        files = listing.json()
        assert len(files) == 1
        file_id = files[0]["id"]

        dl = await client.get(
            f"/api/submissions/{sub}/files/{file_id}", headers=_headers(token)
        )
        assert dl.status_code == 200
        assert dl.content == content

    @pytest.mark.asyncio
    async def test_download_requires_owner_or_admin(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        sub = _make_submission(pid)
        file_id = (
            await client.post(
                f"/api/submissions/{sub}/files",
                files=_file(),
                headers=_headers(token),
            )
        ).json()["id"]

        # A stranger is refused.
        intruder, _ = _make_participant()
        forbidden = await client.get(
            f"/api/submissions/{sub}/files/{file_id}", headers=_headers(intruder)
        )
        assert forbidden.status_code == status.HTTP_403_FORBIDDEN

        # An admin may pull it.
        admin, _ = _make_participant(role="admin")
        ok = await client.get(
            f"/api/submissions/{sub}/files/{file_id}", headers=_headers(admin)
        )
        assert ok.status_code == 200


# ============================================================================ #
# Delete
# ============================================================================ #
class TestDelete:
    @pytest.mark.asyncio
    async def test_owner_can_delete(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        sub = _make_submission(pid)
        file_id = (
            await client.post(
                f"/api/submissions/{sub}/files",
                files=_file(),
                headers=_headers(token),
            )
        ).json()["id"]

        resp = await client.delete(
            f"/api/submissions/{sub}/files/{file_id}", headers=_headers(token)
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        listing = await client.get(f"/api/submissions/{sub}/files")
        assert listing.json() == []
