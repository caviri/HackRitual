"""Image upload — server-side dither/halftone, then store on disk.

Pipeline:
  1. Client POSTs a multipart form (file + optional effect override).
  2. Server reads bytes, runs the effect via app.services.images, computes
     sha256, writes to UPLOAD_DIR/<event>/<participant>/<submission>/<name>.png,
     records a File row.
  3. Response carries the served URL (proxied by the FastAPI app under /uploads).
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.file import File as FileModel
from app.models.user import User
from app.schemas.uploads import UploadResponse
from app.services import images as image_service


router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_BYTES = 6 * 1024 * 1024  # 6 MB hard cap


def _sanitise_segment(s: str) -> str:
    keep = [c for c in s if c.isalnum() or c in ("-", "_")]
    return "".join(keep) or "unnamed"


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    submission_id: str = Form(...),
    participant_id: str = Form(...),
    effect: Literal["none", "dither", "halftone"] = Form("dither"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadResponse:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"only images allowed ({sorted(ALLOWED_MIME)})",
        )
    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty upload")
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"max {MAX_BYTES} bytes",
        )

    processed = image_service.process(raw, effect)
    digest = hashlib.sha256(processed).hexdigest()

    # On-disk layout: UPLOAD_DIR/<event>/<participant>/<submission>/<sha[:12]>.png
    rel_dir = Path(
        _sanitise_segment(settings.event_id),
        _sanitise_segment(participant_id),
        _sanitise_segment(submission_id),
    )
    abs_dir = Path(settings.upload_dir) / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{digest[:12]}.png"
    abs_path = abs_dir / filename
    abs_path.write_bytes(processed)

    rel_path = str(rel_dir / filename)
    row = FileModel(
        submission_id=submission_id,
        path=rel_path,
        mime_type="image/png",  # always re-encoded to PNG
        size_bytes=len(processed),
        sha256=digest,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return UploadResponse(
        id=row.id,
        submission_id=submission_id,
        path=rel_path,
        url=f"/uploads/{rel_path}",
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        effect=effect,
        created_at=row.created_at or datetime.utcnow(),
    )
