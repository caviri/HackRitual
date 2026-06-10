"""
Tests for WASM Scoring (Step 16).

Requires `wasmtime` (skipped otherwise). A tiny constant scorer is compiled from
WAT at runtime — it ignores input and returns a fixed verdict, which is exactly
what we need to exercise the full host↔module round-trip deterministically.
"""

import uuid

import pytest
from fastapi import status

wasmtime = pytest.importorskip("wasmtime")


# A constant scorer: always returns the same JSON verdict.
_OUTPUT = '{"score":42.0,"breakdown":{"flat":42},"status":"scored"}'


def _scorer_wasm() -> bytes:
    escaped = _OUTPUT.replace("\\", "\\\\").replace('"', '\\"')
    wat = (
        "(module "
        '(memory (export "memory") 2) '
        f'(data (i32.const 1024) "{escaped}") '
        '(func (export "alloc") (param i32) (result i32) (i32.const 8192)) '
        '(func (export "dealloc") (param i32) (param i32)) '
        '(func (export "score") (param i32 i32) (result i32) (i32.const 1024)) '
        f'(func (export "get_output_len") (result i32) (i32.const {len(_OUTPUT.encode())})))'
    )
    return bytes(wasmtime.wat2wasm(wat))


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _set_event(state: str = "OPEN") -> None:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        ev = db.get(Event, settings.event_id)
        if ev is None:
            from datetime import datetime, timezone

            ev = Event(
                id=settings.event_id,
                title="Test",
                type="hackathon",
                start_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
            db.add(ev)
        ev.state = state
        ev.config_json = None
        db.commit()


def _participant(role: str = "user") -> tuple[str, str]:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"wasm_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.flush()
        p = Participant(
            event_id=settings.event_id, type="human", display_name="W", status="active"
        )
        db.add(p)
        db.flush()
        db.add(
            ParticipantMember(participant_id=p.id, user_id=user.id, role_in_team="captain")
        )
        db.commit()
        return create_jwt(user), p.id


def _project(pid: str) -> str:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.project import Project

    with SessionLocal() as db:
        proj = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=pid,
            title=f"w-{uuid.uuid4().hex[:6]}",
            description="d",
            status="proposed",
        )
        db.add(proj)
        db.commit()
        return proj.id


def _wasm_upload(name="scorer.wasm"):
    return {"file": (name, _scorer_wasm(), "application/wasm")}


# ============================================================================ #
# Validation + runtime
# ============================================================================ #
class TestWasmRuntime:
    def test_magic_validation(self):
        from app.services.wasm_store import is_valid_wasm

        assert is_valid_wasm(_scorer_wasm()) is True
        assert is_valid_wasm(b"not wasm at all") is False

    def test_scorer_executes(self):
        from app.scoring.wasm_scorer import WasmScorer

        scorer = WasmScorer(_scorer_wasm(), version="wasm:test")
        result = scorer.score({"title": "x", "description": "y"}, [])
        assert result.status == "scored"
        assert result.score_value == 42.0
        assert result.breakdown == {"flat": 42}

    def test_bad_module_fails_gracefully(self):
        from app.scoring.wasm_scorer import WasmScorer

        # Valid header, garbage body → construction raises; the scorer wraps it.
        with pytest.raises(Exception):
            WasmScorer(b"\x00asm\x01\x00\x00\x00garbage", version="wasm:bad")


# ============================================================================ #
# Upload + info + selection (end-to-end)
# ============================================================================ #
class TestWasmEndpoints:
    @pytest.mark.asyncio
    async def test_upload_rejects_non_wasm(self, client):
        _set_event("OPEN")
        admin = _participant(role="admin")[0]
        resp = await client.post(
            "/api/admin/scoring/upload-wasm",
            files={"file": ("x.wasm", b"definitely not wasm", "application/wasm")},
            headers=_headers(admin),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_upload_then_info_and_score(self, client):
        _set_event("OPEN")
        admin = _participant(role="admin")[0]

        up = await client.post(
            "/api/admin/scoring/upload-wasm",
            files=_wasm_upload(),
            headers=_headers(admin),
        )
        assert up.status_code == 200, up.text
        body = up.json()
        assert body["scorer_type"] == "wasm"
        assert body["validated"] is True
        assert body["test_result"]["score"] == 42.0
        version = body["scorer_version"]

        info = await client.get("/api/admin/scoring/info", headers=_headers(admin))
        assert info.json()["scorer_version"] == version

        # A new submission is now scored by the WASM module.
        token, pid = _participant()
        proj = _project(pid)
        sub = await client.post(
            "/api/submissions",
            json={"project_id": proj, "participant_id": pid, "title": "t"},
            headers=_headers(token),
        )
        sub_id = sub.json()["id"]
        score = await client.get(f"/api/submissions/{sub_id}/score")
        assert score.status_code == 200
        assert score.json()["score_value"] == 42.0
        assert score.json()["scorer_version"] == version

    @pytest.mark.asyncio
    async def test_preview_module_served_then_404(self, client):
        _set_event("OPEN")
        admin = _participant(role="admin")[0]

        # No scorer yet → 404.
        assert (await client.get("/api/scoring/preview-module")).status_code == 404

        await client.post(
            "/api/admin/scoring/upload-wasm",
            files=_wasm_upload(),
            headers=_headers(admin),
        )
        served = await client.get("/api/scoring/preview-module")
        assert served.status_code == 200
        assert served.headers["content-type"] == "application/wasm"
        assert served.content[:4] == b"\x00asm"

    @pytest.mark.asyncio
    async def test_rescore_all_enqueues(self, client):
        from app.database import SessionLocal
        from app.models.task import Task

        _set_event("OPEN")
        token, pid = _participant()
        admin = _participant(role="admin")[0]
        proj = _project(pid)
        await client.post(
            "/api/submissions",
            json={"project_id": proj, "participant_id": pid, "title": "t"},
            headers=_headers(token),
        )

        resp = await client.post(
            "/api/admin/scoring/rescore-all", headers=_headers(admin)
        )
        assert resp.status_code == 200
        assert resp.json()["queued"] >= 1

        with SessionLocal() as db:
            assert (
                db.query(Task).filter(Task.type == "score_submission").count() >= 1
            )
