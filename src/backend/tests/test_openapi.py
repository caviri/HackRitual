"""
Tests for API Documentation (Step 19): the OpenAPI spec is valid and complete,
every operation is tagged with a declared tag, and the doc pages render.
"""

import pytest

# A representative slice of the catalog (§19.6) that must always be documented.
_REQUIRED_PATHS = [
    "/api/health",
    "/api/event",
    "/api/leaderboard",
    "/api/privacy",
    "/api/auth/login",
    "/api/participants",
    "/api/submissions",
    "/api/submissions/mine",
    "/api/agent/submissions",
    "/api/agent/leaderboard",
    "/api/admin/event/state",
    "/api/admin/metrics",
    "/api/admin/queue/status",
    "/api/admin/export",
    "/api/admin/scoring/upload-wasm",
    "/api/scoring/preview-module",
]

_METHODS = {"get", "post", "put", "patch", "delete"}


@pytest.mark.asyncio
async def test_openapi_valid_and_complete(client):
    r = await client.get("/api/openapi.json")
    assert r.status_code == 200
    spec = r.json()

    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "HackRitual"
    assert spec["info"]["version"]
    assert spec["info"]["description"]

    paths = spec["paths"]
    missing = [p for p in _REQUIRED_PATHS if p not in paths]
    assert not missing, f"undocumented paths: {missing}"


@pytest.mark.asyncio
async def test_every_operation_is_tagged(client):
    spec = (await client.get("/api/openapi.json")).json()
    untagged = [
        f"{method.upper()} {path}"
        for path, ops in spec["paths"].items()
        for method, op in ops.items()
        if method in _METHODS and not op.get("tags")
    ]
    assert not untagged, f"operations without a tag: {untagged}"


@pytest.mark.asyncio
async def test_used_tags_are_declared(client):
    spec = (await client.get("/api/openapi.json")).json()
    declared = {t["name"] for t in spec.get("tags", [])}
    used: set[str] = set()
    for ops in spec["paths"].values():
        for method, op in ops.items():
            if method in _METHODS:
                used.update(op.get("tags", []))
    assert used <= declared, f"tags used but not declared in OPENAPI_TAGS: {used - declared}"


@pytest.mark.asyncio
async def test_doc_pages_render(client):
    assert (await client.get("/api/docs")).status_code == 200
    assert (await client.get("/api/redoc")).status_code == 200
