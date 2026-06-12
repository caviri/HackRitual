"""
Tests for the Agent System (Step 13): policy-gated creation, participant
linking, API-key auth, revocation, and the agent submission/leaderboard API.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi import status


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _key(api_key: str) -> dict:
    return {"X-API-Key": api_key}


def _set_event(state: str = "OPEN", policy: str = "allowed") -> None:
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
                start_at=datetime(2026, 1, 1, tzinfo=UTC),
                end_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
            db.add(ev)
        ev.state = state
        ev.config_json = json.dumps({"agent_policy": policy})
        db.commit()


def _user_token(role: str = "user") -> str:
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"agent_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_jwt(user)


async def _new_agent(client, token) -> tuple[str, str]:
    """Create an agent, return (agent_id, api_key)."""
    resp = await client.post(
        "/api/agents", json={"name": f"bot-{uuid.uuid4().hex[:6]}"}, headers=_bearer(token)
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    body = resp.json()
    return body["agent"]["id"], body["api_key"]


# ============================================================================ #
# Creation + policy + linking
# ============================================================================ #
class TestAgentCreation:
    @pytest.mark.asyncio
    async def test_create_blocked_when_policy_forbidden(self, client):
        _set_event("OPEN", policy="forbidden")
        token = _user_token()
        resp = await client.post(
            "/api/agents", json={"name": "nope"}, headers=_bearer(token)
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_returns_key_once_and_links_participant(self, client):
        _set_event("OPEN", policy="allowed")
        token = _user_token()
        resp = await client.post(
            "/api/agents", json={"name": "scout"}, headers=_bearer(token)
        )
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["api_key"].startswith("ak_")

        # The key authenticates the agent (X-API-Key path).
        me = await client.get("/api/agent/me", headers=_key(body["api_key"]))
        assert me.status_code == 200
        assert me.json()["name"] == "scout"

        # A linked agent-type participant now exists.
        from app.database import SessionLocal
        from app.models.agent import Agent
        from app.services.agents import agent_participant

        with SessionLocal() as db:
            agent = db.get(Agent, body["agent"]["id"])
            p = agent_participant(db, agent)
            assert p is not None and p.type == "agent"


# ============================================================================ #
# Auth + revocation
# ============================================================================ #
class TestAgentAuth:
    @pytest.mark.asyncio
    async def test_revoked_key_rejected(self, client):
        _set_event("OPEN", policy="allowed")
        token = _user_token()
        agent_id, key = await _new_agent(client, token)

        # Works before revocation.
        assert (await client.get("/api/agent/me", headers=_key(key))).status_code == 200

        # Owner revokes.
        rv = await client.post(f"/api/agents/{agent_id}/revoke", headers=_bearer(token))
        assert rv.status_code == 200

        # Now rejected.
        after = await client.get("/api/agent/me", headers=_key(key))
        assert after.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_agent_endpoint_rejects_user(self, client):
        _set_event("OPEN", policy="allowed")
        token = _user_token()
        resp = await client.get("/api/agent/leaderboard", headers=_bearer(token))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================ #
# Agent submission API
# ============================================================================ #
class TestAgentSubmissions:
    @pytest.mark.asyncio
    async def test_agent_submits_and_is_scored(self, client):
        _set_event("OPEN", policy="allowed")
        token = _user_token()
        _agent_id, key = await _new_agent(client, token)

        resp = await client.post(
            "/api/agent/submissions",
            json={
                "title": "run #1",
                "description": "automated",
                "payload": {"model": "v3", "lr": 0.01},
            },
            headers=_key(key),
        )
        assert resp.status_code == status.HTTP_201_CREATED
        sub_id = resp.json()["id"]

        status_resp = await client.get(
            f"/api/agent/submissions/{sub_id}", headers=_key(key)
        )
        assert status_resp.status_code == 200
        # title 10 + description 20 + payload 40 = 70
        assert status_resp.json()["score"] == 70

    @pytest.mark.asyncio
    async def test_agent_submission_blocked_when_not_open(self, client):
        _set_event("FROZEN", policy="allowed")
        token = _user_token()
        _agent_id, key = await _new_agent_when_open(client, token)
        resp = await client.post(
            "/api/agent/submissions",
            json={"title": "late", "payload": {"x": 1}},
            headers=_key(key),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_agent_leaderboard(self, client):
        _set_event("OPEN", policy="allowed")
        token = _user_token()
        _agent_id, key = await _new_agent(client, token)
        await client.post(
            "/api/agent/submissions",
            json={"title": "x", "description": "y", "payload": {"a": 1}},
            headers=_key(key),
        )
        board = await client.get("/api/agent/leaderboard", headers=_key(key))
        assert board.status_code == 200
        assert board.json()["leaderboard_mode"] in ("best", "latest")


# ============================================================================ #
# Admin agent management
# ============================================================================ #
class TestAdminAgents:
    @pytest.mark.asyncio
    async def test_admin_create_on_behalf(self, client):
        _set_event("OPEN", policy="forbidden")  # admin bypasses policy
        admin = _user_token("admin")
        owner = _user_token()  # token; we need the user id
        # Resolve the owner's user id from the token's subject.
        from app.services.auth import decode_jwt

        owner_id = decode_jwt(owner)["sub"]

        resp = await client.post(
            "/api/admin/agents",
            json={"name": "house-bot", "owner_user_id": owner_id},
            headers=_bearer(admin),
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["agent"]["owner_user_id"] == owner_id

        listing = await client.get("/api/admin/agents", headers=_bearer(admin))
        assert listing.status_code == 200
        assert any(a["name"] == "house-bot" for a in listing.json())


async def _new_agent_when_open(client, token) -> tuple[str, str]:
    """Create an agent while OPEN, then leave the caller to change state."""
    _set_event("OPEN", policy="allowed")
    agent = await _new_agent(client, token)
    _set_event("FROZEN", policy="allowed")
    return agent
