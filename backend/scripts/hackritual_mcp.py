#!/usr/bin/env python3
"""HackRitual MCP server — exposes the REST API as MCP tools.

Run as a subprocess by an MCP-aware client (Claude Desktop, mcp-cli, etc.):

  HACKRITUAL_API_URL=https://your-host \
  HACKRITUAL_API_KEY=ak_xxxxxxxxxxxxxxx \
  uv run python scripts/hackritual_mcp.py

The server talks stdio. The MCP client spawns this process and pipes
JSON-RPC messages. Each tool maps 1:1 to a REST endpoint; the agent uses
its X-API-Key for every call so the platform attributes work to the right
participant.

Required env:
  HACKRITUAL_API_KEY   — the agent's API key (ak_...)

Optional env:
  HACKRITUAL_API_URL   — base URL, default http://localhost:7860
  HACKRITUAL_TIMEOUT   — per-request timeout in seconds, default 15
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as mt


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

API_URL = os.environ.get("HACKRITUAL_API_URL", "http://localhost:7860").rstrip("/")
API_KEY = os.environ.get("HACKRITUAL_API_KEY")
TIMEOUT = float(os.environ.get("HACKRITUAL_TIMEOUT", "15"))

if not API_KEY:
    raise SystemExit(
        "HACKRITUAL_API_KEY is required. Mint one via /admin/agents/ or "
        "/profile/agents/ in the HackRitual UI and pass it in the environment."
    )


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": API_KEY,
        "accept": "application/json",
    }


# ─────────────────────────────────────────────────────────────────────────────
# REST client
# ─────────────────────────────────────────────────────────────────────────────


async def _request(
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
    params: dict | None = None,
) -> dict | list:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.request(
            method,
            f"{API_URL}{path}",
            headers=_headers(),
            params=params,
            json=json_body,
        )
        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = {"detail": resp.text}
            raise RuntimeError(
                f"{method} {path} → {resp.status_code}: "
                f"{json.dumps(body, separators=(',', ':'))}"
            )
        if resp.status_code == 204:
            return {"ok": True}
        return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────────────────────────────────────


TOOLS: list[mt.Tool] = [
    mt.Tool(
        name="whoami",
        description=(
            "Identify the calling agent. Use this first to confirm the API "
            "key works and the agent is active."
        ),
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    mt.Tool(
        name="get_event",
        description=(
            "Return the singleton event's current state, title, dates, and "
            "lifecycle (DRAFT|OPEN|FROZEN|FINAL|ARCHIVED)."
        ),
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    mt.Tool(
        name="list_tracks",
        description="List thematic tracks. Each track groups projects.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    mt.Tool(
        name="list_phases",
        description="List the temporal sub-phases inside the event.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    mt.Tool(
        name="list_pages",
        description="List visible content pages (rules, FAQ, etc.).",
        inputSchema={
            "type": "object",
            "properties": {
                "visible_only": {
                    "type": "boolean",
                    "description": "Only return pages marked visible (default true).",
                    "default": True,
                }
            },
            "additionalProperties": False,
        },
    ),
    mt.Tool(
        name="list_projects",
        description=(
            "List projects in the event. Optionally filter by track_id or "
            "status (proposed|approved|rejected)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "track_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["proposed", "approved", "rejected"],
                },
            },
            "additionalProperties": False,
        },
    ),
    mt.Tool(
        name="get_project",
        description="Get one project by id, including its description and metadata.",
        inputSchema={
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
            "additionalProperties": False,
        },
    ),
    mt.Tool(
        name="propose_project",
        description=(
            "Propose a new project as the calling agent. Requires the "
            "participant_id you propose on behalf of (typically the agent's "
            "own participant)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 200},
                "description": {"type": "string", "minLength": 1},
                "track_id": {"type": "string"},
                "image": {"type": "string"},
                "proposed_by_participant_id": {"type": "string"},
            },
            "required": ["title", "description", "proposed_by_participant_id"],
            "additionalProperties": False,
        },
    ),
    mt.Tool(
        name="list_submissions",
        description="List submission versions. Optionally filter by project or participant.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "participant_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
    ),
    mt.Tool(
        name="get_submission",
        description="Get one submission by id.",
        inputSchema={
            "type": "object",
            "properties": {"submission_id": {"type": "string"}},
            "required": ["submission_id"],
            "additionalProperties": False,
        },
    ),
    mt.Tool(
        name="create_submission",
        description=(
            "Create a new submission version for a project. Version is "
            "auto-assigned by the server (max + 1 per project, participant). "
            "Starts in `draft` status."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "participant_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "result": {
                    "type": "string",
                    "description": "URL or short reference to the artefact (repo link, demo URL, etc.).",
                },
                "payload_json": {
                    "type": "string",
                    "description": "Optional structured payload (must be a JSON-serialised string).",
                },
            },
            "required": ["project_id", "participant_id"],
            "additionalProperties": False,
        },
    ),
    mt.Tool(
        name="update_submission",
        description=(
            "Update an existing submission. Use status='final' to mark "
            "ready for scoring, status='withdrawn' to retract."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "result": {"type": "string"},
                "payload_json": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["draft", "final", "withdrawn"],
                },
            },
            "required": ["submission_id"],
            "additionalProperties": False,
        },
    ),
    mt.Tool(
        name="list_participants",
        description=(
            "List participants in the event. Filter by type (human|agent|team)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["human", "agent", "team"],
                },
                "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
            },
            "additionalProperties": False,
        },
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Tool dispatch
# ─────────────────────────────────────────────────────────────────────────────


async def _dispatch(name: str, args: dict[str, Any]) -> dict | list:
    if name == "whoami":
        return await _request("GET", "/api/agent/me")
    if name == "get_event":
        return await _request("GET", "/api/event")
    if name == "list_tracks":
        return await _request("GET", "/api/tracks")
    if name == "list_phases":
        return await _request("GET", "/api/phases")
    if name == "list_pages":
        params = {"visible_only": str(args.get("visible_only", True)).lower()}
        return await _request("GET", "/api/pages", params=params)
    if name == "list_projects":
        params: dict[str, Any] = {}
        if "track_id" in args:
            params["track_id"] = args["track_id"]
        if "status" in args:
            params["status"] = args["status"]
        return await _request("GET", "/api/projects", params=params)
    if name == "get_project":
        return await _request("GET", f"/api/projects/{args['project_id']}")
    if name == "propose_project":
        body = {k: v for k, v in args.items() if v is not None}
        return await _request("POST", "/api/projects", json_body=body)
    if name == "list_submissions":
        params = {}
        if "project_id" in args:
            params["project_id"] = args["project_id"]
        if "participant_id" in args:
            params["participant_id"] = args["participant_id"]
        return await _request("GET", "/api/submissions", params=params)
    if name == "get_submission":
        return await _request("GET", f"/api/submissions/{args['submission_id']}")
    if name == "create_submission":
        body = {k: v for k, v in args.items() if v is not None}
        return await _request("POST", "/api/submissions", json_body=body)
    if name == "update_submission":
        sub_id = args.pop("submission_id")
        body = {k: v for k, v in args.items() if v is not None}
        return await _request("PATCH", f"/api/submissions/{sub_id}", json_body=body)
    if name == "list_participants":
        params = {"per_page": str(args.get("per_page", 50))}
        if "type" in args:
            params["type"] = args["type"]
        return await _request("GET", "/api/participants", params=params)
    raise RuntimeError(f"unknown tool: {name}")


# ─────────────────────────────────────────────────────────────────────────────
# MCP server wiring
# ─────────────────────────────────────────────────────────────────────────────

server = Server("hackritual")


@server.list_tools()
async def list_tools() -> list[mt.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[mt.TextContent]:
    try:
        result = await _dispatch(name, arguments or {})
        return [
            mt.TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False),
            )
        ]
    except RuntimeError as e:
        return [mt.TextContent(type="text", text=f"error · {e}")]
    except Exception as e:  # pragma: no cover — defensive
        return [mt.TextContent(type="text", text=f"unexpected error · {e!r}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
