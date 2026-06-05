"""
Application configuration via environment variables.
Uses pydantic-settings for validation and .env file support in local dev.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables (and optionally a .env file).

    All fields map directly to environment variable names (case-insensitive).
    Required fields without defaults will cause a ``ValidationError`` at import time,
    ensuring the application fails fast with a clear error rather than crashing later.

    Usage::

        from app.config import settings
        print(settings.event_id)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    app_base_url: str
    log_level: str = "INFO"
    app_version: str = "0.1.0"

    # ------------------------------------------------------------------ #
    # Storage
    # ------------------------------------------------------------------ #
    db_path: str = "/data/app.db"
    upload_dir: str = "/data/uploads"

    # ------------------------------------------------------------------ #
    # Auth
    # ------------------------------------------------------------------ #
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 h

    # ------------------------------------------------------------------ #
    # Admin seeding (at least one required)
    # ------------------------------------------------------------------ #
    admin_seed_emails: Optional[str] = None   # comma-separated
    admin_setup_token: Optional[str] = None

    # ------------------------------------------------------------------ #
    # SMTP
    # ------------------------------------------------------------------ #
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_pass: str
    smtp_from: str

    # ------------------------------------------------------------------ #
    # Event metadata
    # ------------------------------------------------------------------ #
    event_id: str
    event_title: str
    event_type: str = "hackathon"
    event_start: datetime
    event_end: datetime

    # ------------------------------------------------------------------ #
    # GitHub export (optional)
    # ------------------------------------------------------------------ #
    github_export_repo: Optional[str] = None
    github_token: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @model_validator(mode="after")
    def require_admin_seeding(self) -> "Settings":
        """
        Ensure at least one admin-seeding mechanism is configured.

        Either ``ADMIN_SEED_EMAILS`` (comma-separated list of email addresses that
        receive the ``admin`` role on first login) or ``ADMIN_SETUP_TOKEN`` (a
        one-time claim token) must be present.  Both may be set simultaneously.

        Raises:
            ValueError: If neither field is provided.
        """
        if not self.admin_seed_emails and not self.admin_setup_token:
            raise ValueError(
                "At least one of ADMIN_SEED_EMAILS or ADMIN_SETUP_TOKEN must be set."
            )
        return self

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Normalise and validate the ``LOG_LEVEL`` environment variable.

        Args:
            v: Raw value from the environment (case-insensitive).

        Returns:
            Upper-cased log level string (e.g. ``"INFO"``).

        Raises:
            ValueError: If the value is not a recognised Python logging level.
        """
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return upper

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @property
    def admin_seed_email_list(self) -> list[str]:
        """
        Parse ``ADMIN_SEED_EMAILS`` into a list of normalised email strings.

        Returns:
            List of stripped, lower-cased email addresses.
            Empty list if ``ADMIN_SEED_EMAILS`` is not set.

        Example::

            # ADMIN_SEED_EMAILS = " Admin@Test.Local , other@test.local "
            settings.admin_seed_email_list
            # → ["admin@test.local", "other@test.local"]
        """
        if not self.admin_seed_emails:
            return []
        return [e.strip().lower() for e in self.admin_seed_emails.split(",") if e.strip()]


#: Module-level singleton — import this everywhere instead of constructing Settings directly.
#: Constructed once at module import time; raises ``ValidationError`` if required vars are missing.
settings: Settings = Settings()  # type: ignore[call-arg]
