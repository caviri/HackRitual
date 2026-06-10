"""
Tests for the Task Queue & Worker (Step 14): enqueue, atomic claim, async
processing with retry/backoff/dead, stale recovery, and admin monitoring.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi import status


@pytest.fixture(autouse=True)
def _clean_tasks():
    """The queue is a shared singleton table — start each test from empty so
    `claim_next` (which takes the oldest task in the whole table) is deterministic."""
    from app.database import SessionLocal
    from app.models.task import Task

    with SessionLocal() as db:
        db.query(Task).delete()
        db.commit()
    yield


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _admin_token() -> str:
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"q_{uuid.uuid4()}@test.local", role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_jwt(user)


def _make_submission() -> str:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.project import Project
    from app.models.submission import Submission

    with SessionLocal() as db:
        p = Participant(
            event_id=settings.event_id, type="human", display_name="Q", status="active"
        )
        db.add(p)
        db.flush()
        proj = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=p.id,
            title=f"q-{uuid.uuid4().hex[:6]}",
            description="d",
            status="proposed",
        )
        db.add(proj)
        db.flush()
        sub = Submission(
            event_id=settings.event_id,
            project_id=proj.id,
            participant_id=p.id,
            version=1,
            title="t",
            description="d",
            status="draft",
        )
        db.add(sub)
        db.commit()
        return sub.id


# ============================================================================ #
# Enqueue + claim
# ============================================================================ #
class TestEnqueueClaim:
    def test_enqueue_and_claim_order(self):
        from app.database import SessionLocal
        from app.services import task_queue

        with SessionLocal() as db:
            a = task_queue.enqueue(db, "export_bundle", payload={"n": 1})
            b = task_queue.enqueue(db, "export_bundle", payload={"n": 2})
            assert a.status == "queued" and a.payload_json

            first = task_queue.claim_next(db)
            assert first.id == a.id
            assert first.status == "running"
            assert first.attempts == 1

            second = task_queue.claim_next(db)
            assert second.id == b.id

    def test_claim_respects_availability(self):
        from app.database import SessionLocal
        from app.services import task_queue

        with SessionLocal() as db:
            task_queue.enqueue(db, "export_bundle", delay_seconds=3600)
            # Nothing is due yet.
            assert task_queue.claim_next(db) is None


# ============================================================================ #
# Processing (async)
# ============================================================================ #
class TestProcessing:
    @pytest.mark.asyncio
    async def test_score_submission_via_queue(self):
        from app.database import SessionLocal
        from app.models.task import Task
        from app.services import task_queue
        from app.services.scoring_service import active_score
        from app.services.worker import default_handlers, process_task

        sub_id = _make_submission()
        with SessionLocal() as db:
            task_queue.enqueue(db, "score_submission", ref_id=sub_id)
            task = task_queue.claim_next(db)
            await process_task(db, task, default_handlers())
            assert db.get(Task, task.id).status == "done"

        with SessionLocal() as db:
            assert active_score(db, sub_id) is not None  # title+desc = 30

    @pytest.mark.asyncio
    async def test_failure_retries_then_dies(self):
        from app.database import SessionLocal
        from app.models.task import Task
        from app.services import task_queue
        from app.services.worker import process_task

        async def boom(db, task):
            raise RuntimeError("nope")

        handlers = {"boom": boom}

        with SessionLocal() as db:
            t = task_queue.enqueue(db, "boom", max_attempts=2)
            task_id = t.id

            # Attempt 1 → re-queued with backoff.
            task = task_queue.claim_next(db)
            await process_task(db, task, handlers)
            task = db.get(Task, task_id)
            assert task.status == "queued"
            assert task.attempts == 1
            assert task.available_at > datetime.utcnow()
            assert "nope" in task.last_error

            # Make it due again, attempt 2 → dead (hit max_attempts).
            task.available_at = datetime.utcnow() - timedelta(seconds=1)
            db.commit()
            task = task_queue.claim_next(db)
            await process_task(db, task, handlers)
            assert db.get(Task, task_id).status == "dead"

    @pytest.mark.asyncio
    async def test_unknown_type_is_failed(self):
        from app.database import SessionLocal
        from app.models.task import Task
        from app.services import task_queue
        from app.services.worker import process_task

        with SessionLocal() as db:
            task_queue.enqueue(db, "mystery", max_attempts=1)
            task = task_queue.claim_next(db)
            await process_task(db, task, {})
            assert db.get(Task, task.id).status == "dead"


# ============================================================================ #
# Stale recovery
# ============================================================================ #
class TestRecovery:
    def test_recover_stale(self):
        from app.database import SessionLocal
        from app.models.task import Task
        from app.services import task_queue

        with SessionLocal() as db:
            task_queue.enqueue(db, "export_bundle")
            task = task_queue.claim_next(db)
            assert task.status == "running"
            task_id = task.id

        with SessionLocal() as db:
            recovered = task_queue.recover_stale(db)
            assert recovered >= 1
            assert db.get(Task, task_id).status == "queued"


# ============================================================================ #
# Admin endpoints
# ============================================================================ #
class TestAdminQueue:
    @pytest.mark.asyncio
    async def test_status_requires_admin(self, client):
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt

        with SessionLocal() as db:
            user = User(email=f"qu_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        resp = await client.get("/api/admin/queue/status", headers=_headers(token))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_status_shape(self, client):
        from app.database import SessionLocal
        from app.services import task_queue

        with SessionLocal() as db:
            task_queue.enqueue(db, "export_bundle")
        resp = await client.get(
            "/api/admin/queue/status", headers=_headers(_admin_token())
        )
        assert resp.status_code == 200
        body = resp.json()
        for key in ("queued", "running", "done", "dead", "by_type"):
            assert key in body
        assert body["queued"] >= 1

    @pytest.mark.asyncio
    async def test_failed_list_and_retry(self, client):
        from app.database import SessionLocal
        from app.models.task import Task
        from app.services import task_queue

        # Bury a task as dead directly.
        with SessionLocal() as db:
            t = task_queue.enqueue(db, "export_bundle", max_attempts=1)
            t.status = "dead"
            t.last_error = "boom"
            t.completed_at = datetime.utcnow()
            db.commit()
            task_id = t.id

        token = _admin_token()
        failed = await client.get("/api/admin/queue/failed", headers=_headers(token))
        assert failed.status_code == 200
        assert any(t["id"] == task_id for t in failed.json())

        retried = await client.post(
            f"/api/admin/queue/{task_id}/retry", headers=_headers(token)
        )
        assert retried.status_code == 200
        assert retried.json()["status"] == "queued"
        with SessionLocal() as db:
            assert db.get(Task, task_id).attempts == 0

    @pytest.mark.asyncio
    async def test_purge_done(self, client):
        from app.database import SessionLocal
        from app.models.task import Task
        from app.services import task_queue

        with SessionLocal() as db:
            t = task_queue.enqueue(db, "export_bundle")
            t.status = "done"
            t.completed_at = datetime.utcnow() - timedelta(hours=48)
            db.commit()
            task_id = t.id

        resp = await client.post(
            "/api/admin/queue/purge",
            params={"older_than_hours": 24},
            headers=_headers(_admin_token()),
        )
        assert resp.status_code == 200
        assert resp.json()["purged"] >= 1
        with SessionLocal() as db:
            assert db.get(Task, task_id) is None
