"""Self endpoints — things the bearer can do to their own identity.

POST /api/me/portrait
  Multipart upload of a portrait image plus optional effect/contrast/brightness/scale
  parameters. The original is preserved on disk so the user can re-tune the
  effect later without re-uploading.

PATCH /api/me/portrait
  Same as POST but without a new file — only re-applies the chosen effect
  parameters against the previously-uploaded original.

The ritual carries little weight: portraits are dithered to small two-tone
PNGs (typically a few KB) and stored only for the life of this container.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.auth import MeResponse, PortraitInfo
from app.services import images as image_service

router = APIRouter(prefix="/api/me", tags=["me"])

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_BYTES = 4 * 1024 * 1024  # 4 MB — keep the ritual light


def _portrait_root(user_id: str) -> Path:
    """The directory holding a user's portrait files."""
    return Path(settings.upload_dir) / "portraits" / user_id


def _build_me_response(user: User) -> MeResponse:
    portrait: PortraitInfo | None = None
    if user.portrait_path:
        portrait = PortraitInfo(
            url=f"/uploads/{user.portrait_path}",
            effect=user.portrait_effect,
            contrast=user.portrait_contrast,
            brightness=user.portrait_brightness,
            scale=user.portrait_scale,
        )
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        participant=None,
        portrait=portrait,
    )


def _process_and_save(
    user: User,
    db: Session,
    effect: str,
    contrast: float,
    brightness: int,
    scale: float,
    new_original_bytes: bytes | None = None,
    new_original_suffix: str | None = None,
) -> User:
    """Run the image pipeline and persist the result.

    If new_original_bytes is supplied the previous original is replaced.
    Otherwise the existing original is re-processed with the new parameters.
    """
    root = _portrait_root(user.id)
    root.mkdir(parents=True, exist_ok=True)

    if new_original_bytes is not None:
        for old in root.glob("original.*"):
            try:
                old.unlink()
            except OSError:
                pass
        original_path = root / f"original.{new_original_suffix or 'png'}"
        original_path.write_bytes(new_original_bytes)
        source_bytes = new_original_bytes
        user.portrait_original_path = str(
            original_path.relative_to(Path(settings.upload_dir))
        )
    else:
        if not user.portrait_original_path:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "no portrait uploaded yet — supply a file first",
            )
        source = Path(settings.upload_dir) / user.portrait_original_path
        if not source.exists():
            raise HTTPException(
                status.HTTP_410_GONE, "previous portrait file is missing"
            )
        source_bytes = source.read_bytes()

    processed = image_service.process(
        source_bytes,
        effect,  # type: ignore[arg-type]
        contrast=contrast,
        brightness=brightness,
        scale=scale,
    )
    digest = hashlib.sha256(processed).hexdigest()
    processed_name = f"processed-{digest[:12]}.png"
    processed_path = root / processed_name

    for old in root.glob("processed-*.png"):
        if old.name == processed_name:
            continue
        try:
            old.unlink()
        except OSError:
            pass

    processed_path.write_bytes(processed)

    user.portrait_path = str(processed_path.relative_to(Path(settings.upload_dir)))
    user.portrait_effect = effect
    user.portrait_contrast = float(contrast)
    user.portrait_brightness = int(brightness)
    user.portrait_scale = float(scale)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/portrait", response_model=MeResponse)
async def upload_portrait(
    file: UploadFile = File(...),
    effect: Literal["none", "dither", "halftone"] = Form("dither"),
    contrast: float = Form(1.8, ge=0.5, le=3.0),
    brightness: int = Form(0, ge=-50, le=50),
    scale: float = Form(0.4, ge=0.1, le=1.0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeResponse:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"only images allowed ({sorted(ALLOWED_MIME)})",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty upload")
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"the ritual carries little weight — max {MAX_BYTES // 1024 // 1024} MB",
        )

    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}[
        file.content_type
    ]
    updated = _process_and_save(
        user,
        db,
        effect=effect,
        contrast=contrast,
        brightness=brightness,
        scale=scale,
        new_original_bytes=raw,
        new_original_suffix=ext,
    )
    return _build_me_response(updated)


@router.patch("/portrait", response_model=MeResponse)
def retune_portrait(
    effect: Literal["none", "dither", "halftone"] = Form(...),
    contrast: float = Form(..., ge=0.5, le=3.0),
    brightness: int = Form(..., ge=-50, le=50),
    scale: float = Form(..., ge=0.1, le=1.0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeResponse:
    """Re-process the previously uploaded original with new parameters."""
    updated = _process_and_save(
        user,
        db,
        effect=effect,
        contrast=contrast,
        brightness=brightness,
        scale=scale,
    )
    return _build_me_response(updated)


@router.delete("/portrait", response_model=MeResponse)
def remove_portrait(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeResponse:
    """Dispel the portrait. The directory and its files are removed."""
    root = _portrait_root(user.id)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    user.portrait_path = None
    user.portrait_original_path = None
    user.portrait_effect = None
    user.portrait_contrast = None
    user.portrait_brightness = None
    user.portrait_scale = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_me_response(user)
