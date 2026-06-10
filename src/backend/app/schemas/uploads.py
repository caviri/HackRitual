"""Schemas for image uploads."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ImageEffect = Literal["none", "dither", "halftone"]


class UploadResponse(BaseModel):
    id: str
    submission_id: str
    path: str  # relative to UPLOAD_DIR
    url: str  # served path /uploads/...
    mime_type: str
    size_bytes: int
    sha256: str
    effect: ImageEffect
    created_at: datetime
