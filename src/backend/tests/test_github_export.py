"""
Tests for GitHub Export & Static Site (Step 17). The GitHub Git Data API is
simulated with an httpx MockTransport — no network, no real repo.
"""

import uuid
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import status


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _set_event(state: str = "FINAL") -> None:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        ev = db.get(Event, settings.event_id)
        if ev is None:
            ev = Event(
                id=settings.event_id,
                title="Rite Bern",
                type="hackathon",
                start_at=datetime(2026, 1, 1, tzinfo=UTC),
                end_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
            db.add(ev)
        ev.state = state
        ev.config_json = None
        db.commit()


def _admin_token() -> str:
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        u = User(email=f"gh_{uuid.uuid4()}@test.local", role="admin")
        db.add(u)
        db.commit()
        db.refresh(u)
        return create_jwt(u)


def _seed_scored_submission() -> None:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.project import Project
    from app.models.score import Score
    from app.models.submission import Submission

    with SessionLocal() as db:
        p = Participant(
            event_id=settings.event_id, type="human", display_name="Ada", status="active"
        )
        db.add(p)
        db.flush()
        proj = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=p.id,
            title="proj",
            description="d",
            status="approved",
        )
        db.add(proj)
        db.flush()
        sub = Submission(
            event_id=settings.event_id,
            project_id=proj.id,
            participant_id=p.id,
            version=1,
            title="work",
            status="final",
        )
        db.add(sub)
        db.flush()
        db.add(
            Score(
                submission_id=sub.id,
                score_value=88.0,
                status="scored",
                scored_at=datetime.utcnow(),
                scorer_version="default-1.0",
            )
        )
        db.commit()


def _github_mock(calls: list):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        p, m = request.url.path, request.method
        if m == "GET" and "/git/ref/heads/" in p:
            return httpx.Response(200, json={"object": {"sha": "BASE"}})
        if m == "GET" and "/git/commits/" in p:
            return httpx.Response(200, json={"tree": {"sha": "BASETREE"}})
        if m == "POST" and p.endswith("/git/blobs"):
            return httpx.Response(201, json={"sha": "BLOB"})
        if m == "POST" and p.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "TREE"})
        if m == "POST" and p.endswith("/git/commits"):
            return httpx.Response(201, json={"sha": "NEWCOMMIT"})
        if m == "PATCH" and "/git/refs/heads/" in p:
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"message": "not found"})

    return httpx.MockTransport(handler)


# ============================================================================ #
# Secret scan
# ============================================================================ #
class TestSecretScan:
    def test_detects_and_clears(self):
        from app.services.github_service import validate_no_secrets

        files = {"a.json": b'{"k":"hunter2"}', "b.json": b'{"ok":1}'}
        assert validate_no_secrets(files, ["hunter2"]) == ["secret leaked in a.json"]
        assert validate_no_secrets(files, ["nothere"]) == []
        assert validate_no_secrets(files, ["", None]) == []


# ============================================================================ #
# Static site
# ============================================================================ #
class TestStaticSite:
    def test_generates_pages(self):
        from app.database import SessionLocal
        from app.services import static_site

        _set_event("FINAL")
        _seed_scored_submission()
        with SessionLocal() as db:
            files = static_site.generate(db)

        assert {
            "index.html",
            "leaderboard.html",
            "participants.html",
            "submissions.html",
            "style.css",
        } <= set(files)
        assert b"Leaderboard" in files["leaderboard.html"]
        assert b"Ada" in files["leaderboard.html"]
        assert b"Powered by" in files["index.html"]


# ============================================================================ #
# GitHub push (mocked API)
# ============================================================================ #
class TestPushExport:
    @pytest.mark.asyncio
    async def test_push_happy_path(self):
        from app.services.github_service import GITHUB_API, push_export

        calls: list = []
        async with httpx.AsyncClient(
            transport=_github_mock(calls), base_url=GITHUB_API
        ) as client:
            result = await push_export(
                {"manifest.json": b"{}", "index.html": b"<html></html>"},
                repo="org/archive",
                token="tok",
                branch="gh-pages",
                client=client,
            )
        assert result["commit_sha"] == "NEWCOMMIT"
        assert result["commit_url"].endswith("/commit/NEWCOMMIT")
        assert result["pages_url"] == "https://org.github.io/archive/"
        assert ("POST", "/repos/org/archive/git/trees") in calls
        assert ("PATCH", "/repos/org/archive/git/refs/heads/gh-pages") in calls

    @pytest.mark.asyncio
    async def test_creates_branch_when_missing(self):
        from app.services.github_service import GITHUB_API, push_export

        def handler(request: httpx.Request) -> httpx.Response:
            p, m = request.url.path, request.method
            if m == "GET" and p.endswith("/git/ref/heads/gh-pages"):
                return httpx.Response(404, json={"message": "no branch"})
            if m == "GET" and p.endswith("/repos/org/archive"):
                return httpx.Response(200, json={"default_branch": "main"})
            if m == "GET" and p.endswith("/git/ref/heads/main"):
                return httpx.Response(200, json={"object": {"sha": "BASE"}})
            if m == "GET" and "/git/commits/" in p:
                return httpx.Response(200, json={"tree": {"sha": "BT"}})
            if m == "POST" and p.endswith("/git/blobs"):
                return httpx.Response(201, json={"sha": "B"})
            if m == "POST" and p.endswith("/git/trees"):
                return httpx.Response(201, json={"sha": "T"})
            if m == "POST" and p.endswith("/git/commits"):
                return httpx.Response(201, json={"sha": "C"})
            if m == "POST" and p.endswith("/git/refs"):
                return httpx.Response(201, json={})
            return httpx.Response(404, json={"message": "?"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url=GITHUB_API
        ) as client:
            result = await push_export(
                {"manifest.json": b"{}"}, repo="org/archive", token="t", client=client
            )
        assert result["commit_sha"] == "C"


# ============================================================================ #
# Endpoints + worker handler
# ============================================================================ #
class TestPushEndpoints:
    @pytest.mark.asyncio
    async def test_push_requires_config(self, client):
        _set_event("FINAL")
        admin = _admin_token()
        gen = await client.post(
            "/api/admin/export", json={"redaction_mode": "public"}, headers=_h(admin)
        )
        eid = gen.json()["export_id"]
        resp = await client.post(
            f"/api/admin/export/{eid}/push-github", json={}, headers=_h(admin)
        )
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_push_queues_and_status(self, client):
        from app.config import settings

        _set_event("FINAL")
        admin = _admin_token()
        gen = await client.post(
            "/api/admin/export", json={"redaction_mode": "public"}, headers=_h(admin)
        )
        eid = gen.json()["export_id"]

        orig = (settings.github_export_repo, settings.github_token)
        settings.github_export_repo = "org/archive"
        settings.github_token = "tok"
        try:
            resp = await client.post(
                f"/api/admin/export/{eid}/push-github",
                json={"branch": "gh-pages"},
                headers=_h(admin),
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "queued"
            assert resp.json()["repo"] == "org/archive"

            st = await client.get(
                f"/api/admin/export/{eid}/push-status", headers=_h(admin)
            )
            assert st.status_code == 200
            assert st.json()["status"] == "queued"
        finally:
            settings.github_export_repo, settings.github_token = orig

    @pytest.mark.asyncio
    async def test_worker_handler_marks_done(self):
        from app.database import SessionLocal
        from app.models.task import Task
        from app.services import github_push, task_queue
        from app.services.worker import default_handlers, process_task

        async def fake_run(payload):
            return {
                "commit_sha": "Z",
                "commit_url": "u",
                "pages_url": "p",
                "pushed_at": "t",
            }

        orig = github_push.run_push
        github_push.run_push = fake_run
        try:
            with SessionLocal() as db:
                t = task_queue.enqueue(
                    db, "push_github", payload={"export_id": "EXP1"}
                )
                t.status = "running"
                t.attempts = 1
                db.commit()
                await process_task(db, t, default_handlers())
                assert db.get(Task, t.id).status == "done"
            assert github_push.get_status("EXP1")["status"] == "done"
        finally:
            github_push.run_push = orig
