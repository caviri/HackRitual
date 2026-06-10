"""Schemas for the structured export bundle (Step 11)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

RedactionMode = Literal["public", "private", "full"]


class ExportRequest(BaseModel):
    redaction_mode: RedactionMode = "public"
    include_audit: bool = True
    include_assets: bool = False


class ExportPreviewResponse(BaseModel):
    counts: dict
    estimated_size_mb: float


class ExportGenerateResponse(BaseModel):
    export_id: str
    status: str
    size_bytes: int
    redaction_mode: RedactionMode
    download_url: str
