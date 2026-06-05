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

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.event import Event
from app.models.user import User
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
