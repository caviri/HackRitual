"""
Tests for the scaffold companion API (/api/scaffold/*).
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_tickets_returns_list(client):
    r = await client.get("/api/scaffold/tickets")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # kanban/ exists in repo — should have tickets
    assert len(data) > 0


@pytest.mark.asyncio
async def test_tickets_have_required_fields(client):
    r = await client.get("/api/scaffold/tickets")
    assert r.status_code == 200
    tickets = r.json()
    for t in tickets:
        assert "id" in t
        assert "title" in t
        assert "column" in t
        assert "_body" not in t, "Body must not appear in list response"


@pytest.mark.asyncio
async def test_ticket_columns_are_valid(client):
    valid_cols = {"done", "in-progress", "todo", "backlog"}
    r = await client.get("/api/scaffold/tickets")
    assert r.status_code == 200
    for t in r.json():
        assert t["column"] in valid_cols


@pytest.mark.asyncio
async def test_get_ticket_by_id(client):
    # Ticket 001 (project setup) should always be in done
    r = await client.get("/api/scaffold/tickets/001")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "001"
    assert "_body" in data
    assert data["column"] == "done"


@pytest.mark.asyncio
async def test_get_ticket_id_without_leading_zero(client):
    # "1" and "001" should resolve to the same ticket
    r = await client.get("/api/scaffold/tickets/1")
    assert r.status_code == 200
    assert r.json()["id"] == "001"


@pytest.mark.asyncio
async def test_get_ticket_not_found(client):
    r = await client.get("/api/scaffold/tickets/999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_docs_returns_list(client):
    r = await client.get("/api/scaffold/docs")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    filenames = [d["filename"] for d in data]
    # README.md must always be present at repo root
    assert "README.md" in filenames


@pytest.mark.asyncio
async def test_get_doc_readme(client):
    r = await client.get("/api/scaffold/docs/README.md")
    assert r.status_code == 200
    data = r.json()
    assert data["filename"] == "README.md"
    assert "HackRitual" in data["content"]


@pytest.mark.asyncio
async def test_get_doc_not_found(client):
    r = await client.get("/api/scaffold/docs/nonexistent.md")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_doc_path_traversal_blocked(client):
    r = await client.get("/api/scaffold/docs/../../backend/app/config.py")
    # FastAPI URL routing will handle the slashes; the endpoint sees only the last segment
    # Test the explicit check via query-encoded path attempt
    r2 = await client.get("/api/scaffold/docs/..%2Fconfig.py")
    assert r2.status_code in (400, 404)


@pytest.mark.asyncio
async def test_get_doc_non_md_blocked(client):
    r = await client.get("/api/scaffold/docs/config.py")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_status_endpoint(client):
    r = await client.get("/api/scaffold/status")
    assert r.status_code == 200
    data = r.json()
    assert "steps" in data
    steps = data["steps"]
    assert "total" in steps
    assert "done" in steps
    assert "in_progress" in steps
    assert "todo" in steps
    assert "backlog" in steps
    assert steps["total"] == steps["done"] + steps["in_progress"] + steps["todo"] + steps["backlog"]


@pytest.mark.asyncio
async def test_status_event_state(client):
    r = await client.get("/api/scaffold/status")
    assert r.status_code == 200
    data = r.json()
    # Should return a state string (DRAFT by default in test env)
    assert isinstance(data.get("event_state"), str)
