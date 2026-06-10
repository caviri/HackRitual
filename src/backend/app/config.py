"""
Application configuration via environment variables.
Uses pydantic-settings for validation and .env file support in local dev.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
    # Admin seeding
    # ------------------------------------------------------------------ #
    # Comma-separated emails that hold the admin role. The FIRST address is
    # the primary admin: its access password is re-synced to ADMIN_PASSWORD
    # on every startup (which is also the lockout recovery path).
    admin_seed_emails: str
    admin_password: str

    # ------------------------------------------------------------------ #
    # Event metadata — defaults are placeholders; the Event record is seeded
    # from these on FIRST boot only, and the admin panel edits the record
    # afterwards (PATCH /api/admin/event/meta). The DB record is the source
    # of truth for title/dates once it exists.
    # ------------------------------------------------------------------ #
    event_id: str = "hackritual-event"
    event_title: str = "HackRitual"
    event_type: str = "hackathon"
    event_start: datetime = datetime(2030, 1, 1, 9, 0, tzinfo=UTC)
    event_end: datetime = datetime(2030, 1, 2, 17, 0, tzinfo=UTC)
    # When true, a background task advances DRAFT→OPEN at EVENT_START and
    # OPEN→FROZEN at EVENT_END. The ritual otherwise advances only by hand.
    auto_transitions: bool = False
    # When true, the in-process queue worker runs (drains the `tasks` table).
    enable_worker: bool = True
    # When true, the IP/abuse rate-limit middleware is active.
    enable_rate_limit: bool = True

    # ------------------------------------------------------------------ #
    # WASM scoring (MVP-3) — sandbox limits for uploaded scorer modules
    # ------------------------------------------------------------------ #
    wasm_time_limit_ms: int = 5000
    wasm_memory_limit_mb: int = 64

    # ------------------------------------------------------------------ #
    # GitHub export (optional)
    # ------------------------------------------------------------------ #
    github_export_repo: str | None = None
    github_token: str | None = None
    github_export_branch: str = "gh-pages"

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @model_validator(mode="after")
    def require_admin_seeding(self) -> Settings:
        """
        Ensure admin seeding is fully configured.

        ``ADMIN_SEED_EMAILS`` must contain at least one address and
        ``ADMIN_PASSWORD`` must be non-trivial — without them no one could
        ever log in.

        Raises:
            ValueError: If either field is missing or too weak.
        """
        if not self.admin_seed_email_list:
            raise ValueError("ADMIN_SEED_EMAILS must contain at least one email address.")
        if not self.admin_password or len(self.admin_password.strip()) < 8:
            raise ValueError("ADMIN_PASSWORD must be set (at least 8 characters).")
        return self

    @model_validator(mode="after")
    def forbid_db_inside_upload_dir(self) -> Settings:
        """
        Refuse to start if the database file lives inside the upload directory.

        ``UPLOAD_DIR`` is served publicly at ``/uploads``; a ``DB_PATH`` inside
        it would make the SQLite file (which holds plaintext access passwords)
        downloadable by anyone.

        Raises:
            ValueError: If ``DB_PATH`` resolves to a path under ``UPLOAD_DIR``.
        """
        import os

        db = os.path.normpath(os.path.abspath(self.db_path))
        uploads = os.path.normpath(os.path.abspath(self.upload_dir))
        if db == uploads or db.startswith(uploads + os.sep):
            raise ValueError(
                "DB_PATH must not be inside UPLOAD_DIR — the upload directory is "
                "served publicly at /uploads, which would expose the database "
                "(and the access passwords it holds) for download."
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
