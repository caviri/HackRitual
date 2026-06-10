"""
Tests for the structured JSON export bundle (Step 11).

Covers bundle contents and manifest, email redaction (public vs private),
absence of secrets, determinism, and the admin preview/generate/download
endpoints.
"""

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone

import pytest
from fastapi import status


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _set_event(state: str = "FINAL", config: dict | None = None) -> None:
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


def _make_participant(role: str = "user") -> tuple[str, str, str]:
    """Create user + solo participant. Returns (token, participant_id, email)."""
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.models.user import User
    from app.services.auth import create_jwt

    email = f"exp_{uuid.uuid4()}@test.local"
    with SessionLocal() as db:
        user = User(email=email, role=role)
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
        return create_jwt(user), participant.id, email


# ============================================================================ #
# Bundle service
# ============================================================================ #
class TestExportBundle:
    def test_bundle_contains_required_files(self):
        from app.database import SessionLocal
        from app.services.export_bundle import RedactionConfig, build_bundle

        _set_event("FINAL")
        _make_participant()
        with SessionLocal() as db:
            payload = build_bundle(db, RedactionConfig(mode="public"))

        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            names = set(zf.namelist())
            manifest = json.loads(zf.read("manifest.json"))

        required = {
            "manifest.json",
            "participants.json",
            "teams.json",
            "agents.json",
            "submissions.json",
            "scores.json",
            "statistics.json",
            "audit_log.json",
        }
        assert required <= names
        assert manifest["schema_version"] == "1.0.0"
        assert manifest["event"]["state"] == "FINAL"
        assert manifest["counts"]["participants"] >= 1

    def test_public_mode_hashes_emails(self):
        from app.config import settings
        from app.database import SessionLocal
        from app.services.export_bundle import (
            RedactionConfig,
            build_bundle,
            email_hash,
        )

        _set_event("FINAL")
        _token, pid, email = _make_participant()

        with SessionLocal() as db:
            public = build_bundle(db, RedactionConfig(mode="public"))
            private = build_bundle(db, RedactionConfig(mode="private"))

        def _participant(payload, pid):
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                parts = json.loads(zf.read("participants.json"))
            return next(p for p in parts if p["id"] == pid)

        pub = _participant(public, pid)
        assert "email" not in pub
        assert pub["email_hash"] == email_hash(email, settings.event_id)

        priv = _participant(private, pid)
        assert priv["email"] == email
        assert "email_hash" not in priv

    def test_no_secrets_in_bundle(self):
        from app.database import SessionLocal
        from app.services.export_bundle import RedactionConfig, build_bundle

        _set_event("FINAL")
        _make_participant()
        with SessionLocal() as db:
            payload = build_bundle(db, RedactionConfig(mode="full"))

        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            blob = b" ".join(zf.read(n) for n in zf.namelist()).decode("utf-8")

        for secret in ("api_key_hash", "JWT_SECRET", "jwt_secret"):
            assert secret not in blob

    def test_deterministic_except_timestamp(self):
        from app.database import SessionLocal
        from app.services.export_bundle import RedactionConfig, build_bundle

        _set_event("FINAL")
        _make_participant()
        with SessionLocal() as db:
            a = build_bundle(db, RedactionConfig(mode="public"))
            b = build_bundle(db, RedactionConfig(mode="public"))

        def _without_manifest(payload):
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                return {n: zf.read(n) for n in zf.namelist() if n != "manifest.json"}

        # Every section but the timestamped manifest is byte-identical.
        assert _without_manifest(a) == _without_manifest(b)


# ============================================================================ #
# Endpoints
# ============================================================================ #
class TestExportEndpoints:
    @pytest.mark.asyncio
    async def test_preview_requires_admin(self, client):
        _set_event("FINAL")
        token, _, _ = _make_participant()
        resp = await client.get("/api/admin/export/preview", headers=_headers(token))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_generate_and_download(self, client):
        _set_event("FINAL")
        admin_token, _, _ = _make_participant(role="admin")

        preview = await client.get(
            "/api/admin/export/preview", headers=_headers(admin_token)
        )
        assert preview.status_code == 200
        assert "participants" in preview.json()["counts"]

        gen = await client.post(
            "/api/admin/export",
            json={"redaction_mode": "public"},
            headers=_headers(admin_token),
        )
        assert gen.status_code == 200
        export_id = gen.json()["export_id"]
        assert gen.json()["size_bytes"] > 0

        dl = await client.get(
            f"/api/admin/export/{export_id}/download", headers=_headers(admin_token)
        )
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(dl.content)) as zf:
            assert "manifest.json" in zf.namelist()

    @pytest.mark.asyncio
    async def test_download_unknown_404(self, client):
        _set_event("FINAL")
        admin_token, _, _ = _make_participant(role="admin")
        resp = await client.get(
            f"/api/admin/export/{uuid.uuid4()}/download", headers=_headers(admin_token)
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_export_works_in_any_state(self, client):
        # Snapshot semantics — export is allowed even mid-event (OPEN).
        _set_event("OPEN")
        admin_token, _, _ = _make_participant(role="admin")
        gen = await client.post(
            "/api/admin/export",
            json={"redaction_mode": "public"},
            headers=_headers(admin_token),
        )
        assert gen.status_code == 200
