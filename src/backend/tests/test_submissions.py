"""
Tests for the Submission System (Step 07).

Covers the ritual gating (only OPEN accepts work), per-participant submission
limits, own-submission listing, owner/admin withdrawal rules, and admin
moderation with an audit trail.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import status


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _set_event(state: str = "OPEN", config: dict | None = None) -> None:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

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
        event.state = state
        event.config_json = json.dumps(config) if config else None
        db.commit()


def _make_participant(role: str = "user") -> tuple[str, str]:
    """Create a user + linked solo participant. Returns (token, participant_id)."""
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"sub_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.flush()
        participant = Participant(
            event_id=settings.event_id,
            type="human",
            display_name=f"P-{user.id[:6]}",
            status="active",
        )
        db.add(participant)
        db.flush()
        db.add(
            ParticipantMember(
                participant_id=participant.id, user_id=user.id, role_in_team="captain"
            )
        )
        db.commit()
        return create_jwt(user), participant.id


def _make_project(participant_id: str) -> str:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.project import Project

    with SessionLocal() as db:
        project = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=participant_id,
            title=f"proj-{uuid.uuid4().hex[:8]}",
            description="a thing",
            status="proposed",
        )
        db.add(project)
        db.commit()
        return project.id


async def _submit(client, token, project_id, participant_id, **extra):
    body = {
        "project_id": project_id,
        "participant_id": participant_id,
        "title": "work",
        "result": "r",
        **extra,
    }
    return await client.post("/api/submissions", json=body, headers=_headers(token))


# ============================================================================ #
# Ritual gating
# ============================================================================ #
class TestSubmissionGating:
    @pytest.mark.asyncio
    async def test_rejected_when_not_open(self, client):
        _set_event("DRAFT")
        token, pid = _make_participant()
        proj = _make_project(pid)
        resp = await _submit(client, token, proj, pid)
        assert resp.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_accepted_when_open(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        proj = _make_project(pid)
        resp = await _submit(client, token, proj, pid)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["version"] == 1
        assert resp.json()["status"] == "draft"


# ============================================================================ #
# Limits
# ============================================================================ #
class TestSubmissionLimits:
    @pytest.mark.asyncio
    async def test_limit_enforced(self, client):
        _set_event("OPEN", config={"submission_limit_per_participant": 2})
        token, pid = _make_participant()
        proj = _make_project(pid)

        assert (await _submit(client, token, proj, pid)).status_code == 201
        assert (await _submit(client, token, proj, pid)).status_code == 201
        # Third exceeds the cap.
        resp = await _submit(client, token, proj, pid)
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_withdrawn_frees_a_slot(self, client):
        _set_event("OPEN", config={"submission_limit_per_participant": 1})
        token, pid = _make_participant()
        proj = _make_project(pid)

        first = await _submit(client, token, proj, pid)
        assert first.status_code == 201
        # At the cap now.
        assert (await _submit(client, token, proj, pid)).status_code == 429
        # Withdraw the first, freeing the slot.
        wd = await client.post(
            f"/api/submissions/{first.json()['id']}/withdraw", headers=_headers(token)
        )
        assert wd.status_code == 200
        assert (await _submit(client, token, proj, pid)).status_code == 201


# ============================================================================ #
# Own submissions + withdrawal
# ============================================================================ #
class TestMineAndWithdraw:
    @pytest.mark.asyncio
    async def test_mine_lists_own_only(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        other_token, other_pid = _make_participant()
        proj = _make_project(pid)
        await _submit(client, token, proj, pid)

        mine = await client.get("/api/submissions/mine", headers=_headers(token))
        assert mine.status_code == 200
        assert len(mine.json()) == 1
        assert all(s["participant_id"] == pid for s in mine.json())

        # The other participant sees none of it.
        theirs = await client.get(
            "/api/submissions/mine", headers=_headers(other_token)
        )
        assert theirs.json() == []

    @pytest.mark.asyncio
    async def test_withdraw_requires_ownership(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        intruder_token, _ = _make_participant()
        proj = _make_project(pid)
        sub_id = (await _submit(client, token, proj, pid)).json()["id"]

        resp = await client.post(
            f"/api/submissions/{sub_id}/withdraw", headers=_headers(intruder_token)
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_cannot_withdraw_when_frozen(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        proj = _make_project(pid)
        sub_id = (await _submit(client, token, proj, pid)).json()["id"]

        _set_event("FROZEN")
        resp = await client.post(
            f"/api/submissions/{sub_id}/withdraw", headers=_headers(token)
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


# ============================================================================ #
# Admin moderation
# ============================================================================ #
class TestAdminSubmissions:
    @pytest.mark.asyncio
    async def test_admin_list_and_disqualify(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        admin_token, _ = _make_participant(role="admin")
        proj = _make_project(pid)
        sub_id = (await _submit(client, token, proj, pid)).json()["id"]

        listing = await client.get(
            "/api/admin/submissions",
            params={"participant_id": pid},
            headers=_headers(admin_token),
        )
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1

        resp = await client.patch(
            f"/api/admin/submissions/{sub_id}/status",
            json={"status": "withdrawn", "reason": "rule 3"},
            headers=_headers(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "withdrawn"

    @pytest.mark.asyncio
    async def test_non_admin_cannot_list(self, client):
        _set_event("OPEN")
        token, _ = _make_participant()
        resp = await client.get("/api/admin/submissions", headers=_headers(token))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
