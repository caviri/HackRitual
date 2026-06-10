"""Export endpoints — three flavours of artefact.

  GET /api/export.zip                  full backup bundle (admin, FINAL/ARCHIVED only)
  GET /api/export/showcase.json        public-safe digest as JSON
  GET /api/export/showcase.html        standalone HTML page, embed-ready

The showcase endpoints are intentionally available in any state — they're
public-safe and useful to preview ("what would the showcase look like right
now?"). The full bundle is admin-only and gated on the ritual being sealed.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.event import Event
from app.models.user import User
from app.schemas.export import (
    ExportGenerateResponse,
    ExportPreviewResponse,
    ExportRequest,
)
from app.services import export_bundle, github_push, task_queue
from app.services.audit import log_action
from app.services.export import build_export
from app.services.showcase import build_showcase
from app.services.showcase_html import render_showcase_html


router = APIRouter(prefix="/api/export", tags=["export"])


# ─── Full backup bundle ──────────────────────────────────────────────────────


@router.get(".zip")
def export_zip(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    event = db.get(Event, settings.event_id) or db.query(Event).first()
    if event is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "event not seeded")
    if event.state not in ("FINAL", "ARCHIVED"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"export only available in FINAL or ARCHIVED (current: {event.state})",
        )
    payload = build_export(db)
    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="hackritual-{event.id}.zip"',
            "Content-Length": str(len(payload)),
        },
    )


# ─── Public-safe showcase digest ─────────────────────────────────────────────


@router.get("/showcase.json")
def showcase_json(db: Session = Depends(get_db)) -> Response:
    """The showcase as JSON — drop into any static site or stream into analytics."""
    data = build_showcase(db)
    payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    event_id = data["event"]["id"]
    return Response(
        content=payload,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="hackritual-{event_id}-showcase.json"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/showcase.html")
def showcase_html(db: Session = Depends(get_db)) -> HTMLResponse:
    """Standalone themed HTML showcase. Self-contained, host anywhere."""
    data = build_showcase(db)
    html = render_showcase_html(data)
    event_id = data["event"]["id"]
    return HTMLResponse(
        content=html,
        headers={
            # `inline` so the browser renders it; admins can save-as if they want
            # to host elsewhere. A separate `?dl=1` param flips to attachment.
            "Content-Disposition": f'inline; filename="hackritual-{event_id}-showcase.html"',
        },
    )


# ─── Structured JSON export bundle (Step 11) ─────────────────────────────────
#
# A curated, redacted, deterministic JSON archive — distinct from the full
# SQLite backup above. Synchronous for MVP-1: generate, store, download. The
# registry maps an export id to the file on disk; bundles live under a sibling
# of the database so they share its persistence.

admin_export_router = APIRouter(prefix="/api/admin/export", tags=["export"])

# export_id → {path, size, mode, created_at}
_EXPORTS: dict[str, dict] = {}


def _export_dir() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(settings.db_path)), "exports")
    os.makedirs(path, exist_ok=True)
    return path


@admin_export_router.get("/preview", response_model=ExportPreviewResponse)
def export_preview(
    redaction_mode: str = "public",
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ExportPreviewResponse:
    """Counts and an estimated size without generating the bundle."""
    redaction = export_bundle.RedactionConfig(mode=redaction_mode)
    result = export_bundle.preview(db, redaction)
    return ExportPreviewResponse(**result)


@admin_export_router.post("", response_model=ExportGenerateResponse)
def generate_export(
    body: ExportRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ExportGenerateResponse:
    """Generate the export bundle synchronously and register it for download."""
    redaction = export_bundle.RedactionConfig(
        mode=body.redaction_mode,
        include_audit=body.include_audit,
        include_assets=body.include_assets,
    )
    try:
        payload = export_bundle.build_bundle(db, redaction)
    except ValueError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))

    export_id = str(uuid.uuid4())
    path = os.path.join(_export_dir(), f"{export_id}.zip")
    with open(path, "wb") as f:
        f.write(payload)
    _EXPORTS[export_id] = {
        "path": path,
        "size": len(payload),
        "mode": body.redaction_mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return ExportGenerateResponse(
        export_id=export_id,
        status="ready",
        size_bytes=len(payload),
        redaction_mode=body.redaction_mode,
        download_url=f"/api/admin/export/{export_id}/download",
    )


@admin_export_router.get("/{export_id}/download")
def download_export(
    export_id: str,
    _admin: User = Depends(require_admin),
) -> FileResponse:
    """Stream a previously generated export ZIP."""
    record = _EXPORTS.get(export_id)
    if record is None or not os.path.exists(record["path"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "export not found")
    return FileResponse(
        record["path"],
        media_type="application/zip",
        filename=f"hackritual-export-{export_id}.zip",
    )


# ─── GitHub push (Step 17) ───────────────────────────────────────────────────


class PushGithubRequest(BaseModel):
    branch: Optional[str] = None
    commit_message: Optional[str] = None


@admin_export_router.post("/{export_id}/push-github")
def push_github(
    export_id: str,
    body: PushGithubRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Queue an async push of the export (JSON + static site) to GitHub."""
    record = _EXPORTS.get(export_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "export not found")
    if not settings.github_export_repo or not settings.github_token:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "GITHUB_EXPORT_REPO and GITHUB_TOKEN must be configured",
        )

    branch = body.branch or settings.github_export_branch
    task = task_queue.enqueue(
        db,
        "push_github",
        ref_id=export_id,
        payload={
            "export_id": export_id,
            "redaction_mode": record["mode"],
            "branch": branch,
            "commit_message": body.commit_message,
        },
    )
    github_push.set_status(
        export_id,
        status="queued",
        task_id=task.id,
        repo=settings.github_export_repo,
        branch=branch,
    )
    log_action(
        db,
        "export.push_github",
        actor_id=admin.id,
        target_type="export",
        target_id=export_id,
        metadata={"repo": settings.github_export_repo, "branch": branch},
    )
    db.commit()
    return {
        "status": "queued",
        "task_id": task.id,
        "repo": settings.github_export_repo,
        "branch": branch,
    }


@admin_export_router.get("/{export_id}/push-status")
def push_status(
    export_id: str,
    _admin: User = Depends(require_admin),
) -> dict:
    """The status of a queued/completed GitHub push for this export."""
    s = github_push.get_status(export_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no push for this export")
    return s
