"""
Scaffold companion API — dev tool for browsing tickets, docs, and project status.

All endpoints are unauthenticated (dev tool only). Reads from:
- kanban/         ticket markdown files with YAML frontmatter
- docs/           project documentation files
- repo root       README.md, PROGRESS.md, CHANGELOG.md, RISKS.md
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/scaffold", tags=["scaffold"])

# ------------------------------------------------------------------ #
# Path resolution
# ------------------------------------------------------------------ #
_HERE = Path(__file__).resolve().parent          # backend/app/routers/
_REPO = _HERE.parent.parent.parent               # repo root
_KANBAN = _REPO / "kanban"
_DOCS = _REPO / "docs"

COLUMNS = ["done", "in-progress", "todo", "backlog"]

_ROOT_DOCS = ["README.md", "PROGRESS.md", "CHANGELOG.md", "RISKS.md"]


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def _parse_ticket(path: Path) -> dict[str, Any]:
    """Parse a ticket markdown file: extract YAML frontmatter + body."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)", text, re.DOTALL)
    if m:
        fm: dict = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
    else:
        fm, body = {}, text
    return {**fm, "_body": body}


# ------------------------------------------------------------------ #
# Endpoints
# ------------------------------------------------------------------ #
@router.get("/tickets", summary="List all Kanban tickets")
def list_tickets() -> list[dict]:
    """
    Return metadata for all tickets across all Kanban columns.
    Body content is excluded — use GET /api/scaffold/tickets/{id} for full content.
    """
    if not _KANBAN.is_dir():
        return []

    tickets = []
    for col in COLUMNS:
        col_dir = _KANBAN / col
        if not col_dir.is_dir():
            continue
        for f in sorted(col_dir.glob("*.md")):
            data = _parse_ticket(f)
            data.pop("_body", None)
            data["column"] = col
            data["filename"] = f.name
            tickets.append(data)
    return tickets


@router.get("/tickets/{ticket_id}", summary="Get a single ticket with full content")
def get_ticket(ticket_id: str) -> dict:
    """
    Return a ticket's metadata and markdown body.
    ticket_id is the numeric id string (e.g. "006" or "6").
    """
    if not _KANBAN.is_dir():
        raise HTTPException(status_code=404, detail="Kanban directory not found")

    # Normalise: strip leading zeros for comparison
    target = ticket_id.lstrip("0") or "0"

    for col in COLUMNS:
        col_dir = _KANBAN / col
        if not col_dir.is_dir():
            continue
        for f in col_dir.glob("*.md"):
            data = _parse_ticket(f)
            raw_id = str(data.get("id", "")).lstrip("0") or "0"
            if raw_id == target:
                data["column"] = col
                data["filename"] = f.name
                return data

    raise HTTPException(status_code=404, detail=f"Ticket {ticket_id!r} not found")


@router.get("/docs", summary="List all documentation files")
def list_docs() -> list[dict]:
    """Return a list of available documentation files (docs/ and root markdown files)."""
    files = []

    if _DOCS.is_dir():
        for f in sorted(_DOCS.glob("*.md")):
            title = f.stem.replace("-", " ").title()
            files.append({"filename": f.name, "title": title, "group": "docs"})

    for name in _ROOT_DOCS:
        p = _REPO / name
        if p.is_file():
            title = name.replace(".md", "").replace("-", " ").title()
            files.append({"filename": name, "title": title, "group": "root"})

    return files


@router.get("/docs/{filename}", summary="Get the content of a documentation file")
def get_doc(filename: str) -> dict:
    """
    Return raw markdown content for a documentation file.
    Checks docs/ first, then repo root. Only .md files are served.
    Path traversal is blocked.
    """
    # Security: no path separators or parent-directory references
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are supported")

    for search_dir in [_DOCS, _REPO]:
        p = search_dir / filename
        if p.is_file():
            return {"filename": filename, "content": p.read_text(encoding="utf-8")}

    raise HTTPException(status_code=404, detail=f"Doc {filename!r} not found")


@router.get("/status", summary="Project status and aggregate stats")
def get_status() -> dict:
    """Return aggregate project stats and live event state from the database."""
    tickets = list_tickets()
    by_col: dict[str, list] = {}
    for t in tickets:
        by_col.setdefault(t.get("column", "backlog"), []).append(t)

    event_state = "unknown"
    event_id = "unknown"
    try:
        from app.config import settings
        from app.models.event import Event

        event_id = settings.event_id
        db = SessionLocal()
        try:
            ev = db.get(Event, settings.event_id)
            if ev:
                event_state = ev.state
        finally:
            db.close()
    except Exception:
        pass

    return {
        "event_id": event_id,
        "event_state": event_state,
        "steps": {
            "total": len(tickets),
            "done": len(by_col.get("done", [])),
            "in_progress": len(by_col.get("in-progress", [])),
            "todo": len(by_col.get("todo", [])),
            "backlog": len(by_col.get("backlog", [])),
        },
        "columns": COLUMNS,
        "kanban_exists": _KANBAN.is_dir(),
    }
