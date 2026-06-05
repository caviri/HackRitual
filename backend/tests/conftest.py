"""
Shared pytest fixtures.

Sets up a temporary SQLite database and a minimal env for every test so
tests never need a real .env file or real SMTP / JWT secrets.
"""

from __future__ import annotations

import os

import pytest
from httpx import AsyncClient, ASGITransport


# ------------------------------------------------------------------ #
# Minimal valid env — set BEFORE app modules are imported by tests
# ------------------------------------------------------------------ #
MINIMAL_ENV = {
    "APP_BASE_URL": "http://localhost:7860",
    "JWT_SECRET": "test-secret-do-not-use-in-production",
    "ADMIN_SEED_EMAILS": "admin@test.local",
    "SMTP_HOST": "localhost",
    "SMTP_USER": "test",
    "SMTP_PASS": "test",
    "SMTP_FROM": "test@test.local",
    "EVENT_ID": "test-event",
    "EVENT_TITLE": "Test Event",
    "EVENT_START": "2026-01-01T09:00:00+00:00",
    "EVENT_END": "2026-01-02T17:00:00+00:00",
    "LOG_LEVEL": "WARNING",
}


@pytest.fixture(scope="session", autouse=True)
def _set_env(tmp_path_factory):
    """Inject env vars for the whole test session before any import."""
    tmp = tmp_path_factory.mktemp("data")
    db_file = str(tmp / "test.db")
    upload_dir = str(tmp / "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    env = {**MINIMAL_ENV, "DB_PATH": db_file, "UPLOAD_DIR": upload_dir}
    original = {}
    for k, v in env.items():
        original[k] = os.environ.get(k)
        os.environ[k] = v

    yield db_file

    for k, v in original.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture(scope="session", autouse=True)
def _create_tables(_set_env):
    """Create all DB tables once per test session (after env is set)."""
    from app.database import Base, engine  # imported AFTER env is set
    import app.models  # noqa: F401 — registers all models on Base.metadata
    Base.metadata.create_all(engine)
    yield


@pytest.fixture()
async def client(_create_tables):
    """Async HTTP client wired to the FastAPI app (with lifespan)."""
    from app.main import create_app
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
