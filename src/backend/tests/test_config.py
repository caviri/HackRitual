"""Tests for Settings validation (config.py)."""

from __future__ import annotations

import pytest


def _make_settings(**overrides):
    """Helper: build Settings with a valid base env, applying overrides."""

    base = {
        "APP_BASE_URL": "http://localhost:7860",
        "JWT_SECRET": "testsecret",
        "ADMIN_SEED_EMAILS": "admin@test.local",
        "ADMIN_PASSWORD": "test-admin-pass",
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
        # event_id is set by the session env (test-event); just verify it's non-empty
        assert s.event_id

    def test_requires_admin_seeding(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="ADMIN_SEED_EMAILS"):
            _make_settings(admin_seed_emails="")

    def test_requires_admin_password(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="ADMIN_PASSWORD"):
            _make_settings(admin_password="short")

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
