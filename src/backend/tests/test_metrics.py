"""
Tests for Privacy & Statistics (Step 18): the daily metrics service, the admin
dashboard, the cleanup sweep, and the structured privacy endpoint.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import status


@pytest.fixture(autouse=True)
def _clean_metrics():
    from app.database import SessionLocal
    from app.models.metrics_daily import MetricsDaily

    with SessionLocal() as db:
        db.query(MetricsDaily).delete()
        db.commit()
    yield


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _admin_token() -> str:
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        u = User(email=f"m_{uuid.uuid4()}@test.local", role="admin")
        db.add(u)
        db.commit()
        db.refresh(u)
        return create_jwt(u)


# ============================================================================ #
# Service
# ============================================================================ #
class TestMetricsService:
    def test_increment_upserts(self):
        from app.database import SessionLocal
        from app.services import metrics_service

        with SessionLocal() as db:
            metrics_service.increment(db, "submissions_count")
            metrics_service.increment(db, "submissions_count", 2)
            db.commit()
            rows = metrics_service.get_daily(db)
        today = next(r for r in rows if r["date"] == date.today().isoformat())
        assert today["submissions"] == 3

    def test_unknown_metric_rejected(self):
        from app.database import SessionLocal
        from app.services import metrics_service

        with SessionLocal() as db:
            with pytest.raises(ValueError):
                metrics_service.increment(db, "not_a_metric")

    def test_scoring_avg_and_max(self):
        from app.database import SessionLocal
        from app.services import metrics_service

        with SessionLocal() as db:
            metrics_service.record_scoring_time(db, 100.0)
            metrics_service.record_scoring_time(db, 300.0)
            db.commit()
            rows = metrics_service.get_daily(db)
        today = next(r for r in rows if r["date"] == date.today().isoformat())
        assert today["scoring_avg_ms"] == 200.0
        assert today["scoring_max_ms"] == 300.0


# ============================================================================ #
# Admin dashboard
# ============================================================================ #
class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_requires_admin(self, client):
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt

        with SessionLocal() as db:
            u = User(email=f"mu_{uuid.uuid4()}@test.local", role="user")
            db.add(u)
            db.commit()
            db.refresh(u)
            token = create_jwt(u)
        resp = await client.get("/api/admin/metrics", headers=_headers(token))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_dashboard_shape(self, client):
        from app.database import SessionLocal
        from app.services import metrics_service

        with SessionLocal() as db:
            metrics_service.increment(db, "logins_count")
            db.commit()

        resp = await client.get("/api/admin/metrics", headers=_headers(_admin_token()))
        assert resp.status_code == 200
        body = resp.json()
        assert "daily" in body and "totals" in body and "ephemeral" in body
        for key in ("participants", "teams", "agents", "submissions"):
            assert key in body["totals"]


# ============================================================================ #
# Increment wiring (via real endpoints)
# ============================================================================ #
class TestIncrementWiring:
    @pytest.mark.asyncio
    async def test_submission_increments_counter(self, client):
        from app.config import settings
        from app.database import SessionLocal
        from app.models.event import Event
        from app.models.participant import Participant
        from app.models.participant_member import ParticipantMember
        from app.models.project import Project
        from app.models.user import User
        from app.services.auth import create_jwt

        with SessionLocal() as db:
            ev = db.get(Event, settings.event_id)
            if ev is None:
                ev = Event(
                    id=settings.event_id, title="T", type="hackathon",
                    start_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    end_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                )
                db.add(ev)
            ev.state = "OPEN"
            ev.config_json = None
            user = User(email=f"ms_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.flush()
            p = Participant(event_id=settings.event_id, type="human", display_name="P", status="active")
            db.add(p)
            db.flush()
            db.add(ParticipantMember(participant_id=p.id, user_id=user.id, role_in_team="captain"))
            proj = Project(event_id=settings.event_id, proposed_by_participant_id=p.id, title="x", description="d", status="proposed")
            db.add(proj)
            db.commit()
            token = create_jwt(user)
            pid, projid = p.id, proj.id

        await client.post(
            "/api/submissions",
            json={"project_id": projid, "participant_id": pid, "title": "t"},
            headers=_headers(token),
        )
        resp = await client.get("/api/admin/metrics", headers=_headers(_admin_token()))
        daily = resp.json()["daily"]
        today = next((r for r in daily if r["date"] == date.today().isoformat()), None)
        assert today is not None and today["submissions"] >= 1


# ============================================================================ #
# Cleanup
# ============================================================================ #
class TestCleanup:
    def test_cleanup_removes_expired(self):
        import uuid as _uuid
        from app.database import SessionLocal
        from app.models.session import Session as SessionModel
        from app.models.user import User
        from app.services.cleanup import cleanup_expired_data

        with SessionLocal() as db:
            u = User(email=f"cl_{_uuid.uuid4()}@test.local", role="user")
            db.add(u)
            db.flush()
            db.add(
                SessionModel(
                    user_id=u.id,
                    expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                )
            )
            db.commit()
            removed = cleanup_expired_data(db)
        assert removed["sessions"] >= 1


# ============================================================================ #
# Privacy endpoint
# ============================================================================ #
class TestPrivacyEndpoint:
    @pytest.mark.asyncio
    async def test_privacy_structure(self, client):
        resp = await client.get("/api/privacy")
        assert resp.status_code == 200
        body = resp.json()
        assert body["cookies"]["count"] == 1
        assert body["ip_addresses"]["stored_in_db"] is False
        assert "collects" in body and "retention" in body
