"""
Tests for the Event Lifecycle (Step 06).

Covers the state machine, state-based guards, configuration editing rules,
the audit history, and the pure auto-transition decision function.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _reset_event(state: str = "DRAFT", config_json: str | None = None) -> str:
    """Put the singleton event into a known state. Returns its id."""
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        event = db.query(Event).first()
        if event is None:
            event = Event(
                id="test-event",
                title="Test Event",
                type="hackathon",
                start_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
            db.add(event)
        event.state = state
        event.config_json = config_json
        db.commit()
        return event.id


def _make_user(role: str = "user") -> str:
    """Create a user with the given role and return a bearer token."""
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"{role}_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_jwt(user)


# ============================================================================ #
# Public read
# ============================================================================ #
class TestGetEvent:
    @pytest.mark.asyncio
    async def test_get_event_returns_state_and_config(self, client):
        _reset_event("OPEN")
        resp = await client.get("/api/event")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["state"] == "OPEN"
        # Defaults are surfaced even when nothing is stored.
        assert data["config"]["leaderboard_mode"] == "best"
        assert data["config"]["submission_limit_per_participant"] == 10
        assert data["config"]["tracks"] == []
        assert "start" in data and "end" in data


# ============================================================================ #
# State machine
# ============================================================================ #
class TestStateTransitions:
    @pytest.mark.asyncio
    async def test_valid_forward_transition(self, client):
        _reset_event("DRAFT")
        token = _make_user("admin")
        resp = await client.post(
            "/api/admin/event/state",
            json={"state": "OPEN", "reason": "open the gates"},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["state"] == "OPEN"
        assert data["previous_state"] == "DRAFT"
        assert data["transitioned_by"].endswith("@test.local")

    @pytest.mark.asyncio
    async def test_invalid_backward_transition_rejected(self, client):
        _reset_event("OPEN")
        token = _make_user("admin")
        resp = await client.post(
            "/api/admin/event/state",
            json={"state": "DRAFT"},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_archived_is_terminal(self, client):
        _reset_event("ARCHIVED")
        token = _make_user("admin")
        resp = await client.post(
            "/api/admin/event/state",
            json={"state": "FINAL"},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_reopen_requires_confirmation(self, client):
        _reset_event("FROZEN")
        token = _make_user("admin")
        # Without confirm → 400
        resp = await client.post(
            "/api/admin/event/state",
            json={"state": "OPEN", "reason": "reopen"},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        # With confirm → 200
        resp = await client.post(
            "/api/admin/event/state",
            json={"state": "OPEN", "reason": "reopen", "confirm": True},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["state"] == "OPEN"

    @pytest.mark.asyncio
    async def test_full_happy_path(self, client):
        _reset_event("DRAFT")
        token = _make_user("admin")
        for target in ["OPEN", "FROZEN", "FINAL", "ARCHIVED"]:
            resp = await client.post(
                "/api/admin/event/state",
                json={"state": target},
                headers=_headers(token),
            )
            assert resp.status_code == status.HTTP_200_OK, target
            assert resp.json()["state"] == target


# ============================================================================ #
# Authorization
# ============================================================================ #
class TestTransitionAuth:
    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, client):
        _reset_event("DRAFT")
        token = _make_user("user")
        resp = await client.post(
            "/api/admin/event/state",
            json={"state": "OPEN"},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client):
        _reset_event("DRAFT")
        resp = await client.post("/api/admin/event/state", json={"state": "OPEN"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================ #
# Configuration
# ============================================================================ #
class TestEventConfig:
    @pytest.mark.asyncio
    async def test_update_config_in_draft(self, client):
        _reset_event("DRAFT")
        token = _make_user("admin")
        resp = await client.patch(
            "/api/admin/event/config",
            json={
                "submission_limit_per_participant": 5,
                "leaderboard_mode": "latest",
                "tracks": [{"id": "t1", "name": "Open Track", "description": "anything"}],
            },
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        cfg = resp.json()["config"]
        assert cfg["submission_limit_per_participant"] == 5
        assert cfg["leaderboard_mode"] == "latest"
        assert cfg["tracks"][0]["name"] == "Open Track"

    @pytest.mark.asyncio
    async def test_leaderboard_mode_locked_after_open(self, client):
        _reset_event("OPEN")
        token = _make_user("admin")
        resp = await client.patch(
            "/api/admin/event/config",
            json={"leaderboard_mode": "latest"},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_other_fields_editable_when_open(self, client):
        _reset_event("OPEN")
        token = _make_user("admin")
        resp = await client.patch(
            "/api/admin/event/config",
            json={"registration_open": False},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["config"]["registration_open"] is False

    @pytest.mark.asyncio
    async def test_config_frozen_after_open(self, client):
        _reset_event("FROZEN")
        token = _make_user("admin")
        resp = await client.patch(
            "/api/admin/event/config",
            json={"registration_open": False},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


# ============================================================================ #
# Audit history
# ============================================================================ #
class TestAuditHistory:
    @pytest.mark.asyncio
    async def test_transition_is_logged(self, client):
        _reset_event("DRAFT")
        token = _make_user("admin")
        await client.post(
            "/api/admin/event/state",
            json={"state": "OPEN", "reason": "let them in"},
            headers=_headers(token),
        )
        resp = await client.get("/api/admin/event/audit", headers=_headers(token))
        assert resp.status_code == status.HTTP_200_OK
        entries = resp.json()
        assert any(
            e["action"] == "event.transition"
            and e["metadata"]["to"] == "OPEN"
            and e["metadata"]["reason"] == "let them in"
            for e in entries
        )


# ============================================================================ #
# EventGuard (service-level)
# ============================================================================ #
class TestEventGuard:
    def test_predicates(self):
        from app.services.event import EventGuard

        assert EventGuard("OPEN").can_submit() is True
        assert EventGuard("FROZEN").can_submit() is False
        assert EventGuard("DRAFT").can_register() is True
        assert EventGuard("FROZEN").can_register() is False
        assert EventGuard("FROZEN").can_score() is True
        assert EventGuard("FINAL").can_score() is False
        assert EventGuard("FINAL").can_export() is True
        assert EventGuard("OPEN").can_export() is False
        assert EventGuard("ARCHIVED").is_read_only() is True

    def test_require_state_raises(self):
        from fastapi import HTTPException

        from app.services.event import EventGuard

        EventGuard("OPEN").require_state("OPEN")  # no raise
        with pytest.raises(HTTPException) as exc:
            EventGuard("DRAFT").require_state("OPEN")
        assert exc.value.status_code == status.HTTP_409_CONFLICT


# ============================================================================ #
# Auto-transition decision (pure)
# ============================================================================ #
class TestNextAutoState:
    def test_draft_opens_at_start(self):
        from app.services.event import next_auto_state

        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)
        assert next_auto_state("DRAFT", start - timedelta(hours=1), start, end) is None
        assert next_auto_state("DRAFT", start, start, end) == "OPEN"

    def test_open_freezes_at_end(self):
        from app.services.event import next_auto_state

        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)
        assert next_auto_state("OPEN", end - timedelta(hours=1), start, end) is None
        assert next_auto_state("OPEN", end, start, end) == "FROZEN"

    def test_terminal_states_never_transition(self):
        from app.services.event import next_auto_state

        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)
        later = end + timedelta(days=10)
        for state in ("FROZEN", "FINAL", "ARCHIVED"):
            assert next_auto_state(state, later, start, end) is None

    def test_handles_naive_db_timestamps(self):
        from app.services.event import next_auto_state

        # Event start/end may come back naive from SQLite — must still compare.
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)
        now = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        assert next_auto_state("DRAFT", now, start, end) == "OPEN"
