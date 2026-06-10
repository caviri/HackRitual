"""Tests for Settings validation (config.py)."""

from __future__ import annotations

import pytest


def _make_settings(**overrides):
    """Helper: build Settings with a valid base env, applying overrides."""

    base = {
        "APP_BASE_URL": "http://localhost:7860",
        "JWT_SECRET": "testsecret",
        "ADMIN_SEED_EMAILS": "admin@test.local",
        "SMTP_HOST": "smtp.test",
        "SMTP_USER": "u",
        "SMTP_PASS": "p",
        "SMTP_FROM": "f@test.local",
        "EVENT_ID": "evt-1",
        "EVENT_TITLE": "Evt",
        "EVENT_START": "2026-01-01T09:00:00+00:00",
        "EVENT_END": "2026-01-02T17:00:00+00:00",
    }
    base.update(overrides)

    from app.config import Settings
    return Settings(**base)  # type: ignore[call-arg]


class TestSettingsValidation:
    def test_valid_config_loads(self):
        s = _make_settings()
        # smtp_port has a default (587) and is not set in the session env
        assert s.smtp_port == 587
        # event_id is set by the session env (test-event); just verify it's non-empty
        assert s.event_id

    def test_requires_admin_seeding(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="ADMIN_SEED_EMAILS or ADMIN_SETUP_TOKEN"):
            _make_settings(admin_seed_emails=None, admin_setup_token=None)

    def test_admin_setup_token_satisfies_requirement(self):
        s = _make_settings(admin_seed_emails=None, admin_setup_token="tok123")
        assert s.admin_setup_token == "tok123"

    def test_invalid_log_level_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="LOG_LEVEL"):
            _make_settings(log_level="VERBOSE")

    def test_log_level_uppercased(self):
        s = _make_settings(log_level="debug")
        assert s.log_level == "DEBUG"

    def test_admin_seed_email_list_parsed(self):
        s = _make_settings(admin_seed_emails=" Admin@Test.Local , other@test.local ")
        assert s.admin_seed_email_list == ["admin@test.local", "other@test.local"]

    def test_github_fields_optional(self):
        s = _make_settings()
        assert s.github_export_repo is None
        assert s.github_token is None
