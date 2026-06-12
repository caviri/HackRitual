"""
Tests for the Admin Console aggregation API (Step 09, backend slice):
the dashboard, scoring status, and global audit query.
"""

import uuid
from datetime import UTC, datetime

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
                start_at=datetime(2026, 1, 1, tzinfo=UTC),
                end_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
            db.add(ev)
        ev.state = state
        ev.config_json = None
        db.commit()


def _make_user(role: str = "user") -> str:
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"adm_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_jwt(user)


# ============================================================================ #
# Authorization
# ============================================================================ #
class TestAdminConsoleAuth:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path", ["/api/admin/dashboard", "/api/admin/scoring/status", "/api/admin/audit"]
    )
    async def test_requires_admin(self, client, path):
        token = _make_user("user")
        resp = await client.get(path, headers=_headers(token))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================ #
# Dashboard
# ============================================================================ #
class TestDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_shape(self, client):
        _set_event("OPEN")
        token = _make_user("admin")
        resp = await client.get("/api/admin/dashboard", headers=_headers(token))
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["event"]["state"] == "OPEN"
        metrics = body["metrics"]
        for key in (
            "participants_total",
            "participants_by_type",
            "submissions_total",
            "submissions_today",
            "scoring_queue_depth",
            "active_agents",
        ):
            assert key in metrics
        assert isinstance(body["recent_audit"], list)


# ============================================================================ #
# Scoring status
# ============================================================================ #
class TestScoringStatus:
    @pytest.mark.asyncio
    async def test_scoring_status_shape(self, client):
        token = _make_user("admin")
        resp = await client.get("/api/admin/scoring/status", headers=_headers(token))
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["scorer"]["version"] == "default-1.0"
        assert len(body["distribution"]) == 5
        assert {d["range"] for d in body["distribution"]} == {
            "0-20",
            "20-40",
            "40-60",
            "60-80",
            "80-100",
        }


# ============================================================================ #
# Audit query
# ============================================================================ #
class TestAuditQuery:
    @pytest.mark.asyncio
    async def test_audit_filter_by_action(self, client):
        from app.database import SessionLocal
        from app.services.audit import log_action

        token = _make_user("admin")
        marker = f"test.console_{uuid.uuid4().hex[:8]}"
        with SessionLocal() as db:
            log_action(db, marker, target_type="thing", target_id="x")
            db.commit()

        resp = await client.get(
            "/api/admin/audit",
            params={"action": marker},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["total"] == 1
        assert body["entries"][0]["action"] == marker

    @pytest.mark.asyncio
    async def test_audit_pagination(self, client):
        token = _make_user("admin")
        resp = await client.get(
            "/api/admin/audit",
            params={"page": 1, "per_page": 5},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["per_page"] == 5
        assert len(body["entries"]) <= 5
        assert "pages" in body
