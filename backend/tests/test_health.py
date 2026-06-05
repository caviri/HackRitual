"""Tests for GET /api/health."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_schema(client):
    data = (await client.get("/api/health")).json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert data["event_id"] == "test-event"
    assert data["event_state"] == "DRAFT"
    assert isinstance(data["db_ok"], bool)
    assert isinstance(data["persistent_storage"], bool)


@pytest.mark.asyncio
async def test_health_db_ok_with_temp_sqlite(client):
    """DB check should succeed against the temp SQLite file set in conftest."""
    data = (await client.get("/api/health")).json()
    assert data["db_ok"] is True


@pytest.mark.asyncio
async def test_health_db_not_ok_with_bad_path(monkeypatch, _set_env):
    """DB check must report db_ok=False when the db path is invalid."""
    import app.routers.health as h

    original = h._check_db
    monkeypatch.setattr(h, "_check_db", lambda _: False)

    from app.main import create_app
    from httpx import AsyncClient, ASGITransport

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        data = (await ac.get("/api/health")).json()

    assert data["db_ok"] is False
    monkeypatch.setattr(h, "_check_db", original)
