"""
Tests for the Email System (Step 12) — templates, metrics, dispatch, and the
admin metrics endpoint. Auth-path delivery is covered in test_auth.
"""

import uuid

import pytest
from fastapi import status


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_user(role: str = "user") -> str:
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"mail_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_jwt(user)


# ============================================================================ #
# Templates
# ============================================================================ #
class TestTemplates:
    def test_phase_change_template(self):
        from app.services.notifications import phase_change_email

        subject, html, text = phase_change_email("HackRitual Bern", "OPEN")
        assert "OPEN" in subject
        assert "HackRitual Bern" in html
        assert "OPEN" in text

    def test_submission_received_template(self):
        from app.services.notifications import submission_received_email

        subject, html, text = submission_received_email("Bern", "my-thing", "draft")
        assert "Submission received" in subject
        assert "my-thing" in html
        assert "draft" in text

    def test_score_available_template(self):
        from app.services.notifications import score_available_email

        subject, html, text = score_available_email("Bern", "my-thing", 92.0)
        assert "Score available" in subject
        assert "92" in html


# ============================================================================ #
# Metrics + dispatch
# ============================================================================ #
class TestMetrics:
    def test_record_and_snapshot(self):
        from app.services import email_metrics

        email_metrics.reset()
        email_metrics.record(True)
        email_metrics.record(False)
        snap = email_metrics.snapshot()
        assert snap["sent"] == 2
        assert snap["succeeded"] == 1
        assert snap["failed"] == 1
        assert snap["last_sent_at"] is not None

    @pytest.mark.asyncio
    async def test_console_dispatch_records_success(self):
        # In test env SMTP_HOST is "localhost" → console mode → counted success.
        from app.services import email_metrics
        from app.services.email import send_email

        email_metrics.reset()
        ok = await send_email("nobody@test.local", "subj", "<b>hi</b>", "hi")
        assert ok is True
        assert email_metrics.snapshot()["succeeded"] == 1


# ============================================================================ #
# Recipient resolution
# ============================================================================ #
class TestRecipients:
    def test_event_recipients(self):
        from app.config import settings
        from app.database import SessionLocal
        from app.models.participant import Participant
        from app.models.participant_member import ParticipantMember
        from app.models.user import User
        from app.services.notifications import event_recipient_emails

        email = f"recip_{uuid.uuid4()}@test.local"
        with SessionLocal() as db:
            user = User(email=email, role="user")
            db.add(user)
            db.flush()
            p = Participant(
                event_id=settings.event_id,
                type="human",
                display_name="R",
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

            recipients = event_recipient_emails(db, settings.event_id)
        assert email in recipients


# ============================================================================ #
# Admin metrics endpoint
# ============================================================================ #
class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_requires_admin(self, client):
        token = _make_user("user")
        resp = await client.get("/api/admin/email/metrics", headers=_headers(token))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_metrics_shape(self, client):
        from app.services import email_metrics

        email_metrics.reset()
        email_metrics.record(True)
        token = _make_user("admin")
        resp = await client.get("/api/admin/email/metrics", headers=_headers(token))
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert set(body) == {"sent", "succeeded", "failed", "last_sent_at"}
        assert body["sent"] >= 1


# ============================================================================ #
# No recipient address leaks into logs
# ============================================================================ #
class TestPrivacy:
    @pytest.mark.asyncio
    async def test_recipient_not_logged_by_smtp_path(self, caplog):
        # Force the SMTP path to fail and assert the address is not in the logs.
        import logging

        from app.services import email

        with caplog.at_level(logging.INFO):
            # _send_smtp will raise (no SMTP server) → send_email returns False.
            # Monkeypatch console detection so we exercise the SMTP branch.
            orig = email._is_console_mode
            email._is_console_mode = lambda host: False
            try:
                await email.send_email(
                    "secret-address@test.local", "s", "<b>h</b>", "h"
                )
            finally:
                email._is_console_mode = orig

        assert "secret-address@test.local" not in caplog.text
