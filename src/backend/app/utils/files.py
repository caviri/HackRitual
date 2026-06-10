"""
File storage utilities — per specs §5.2.

Files are stored at: <UPLOAD_DIR>/<event_id>/<participant_id>/<submission_id>/<filename>
Only metadata + paths are stored in the DB; blobs live on disk.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from app.config import settings


def _submission_dir(event_id: str, participant_id: str, submission_id: str) -> Path:
    return Path(settings.upload_dir) / event_id / participant_id / submission_id


def save_upload(
    data: bytes,
    filename: str,
    mime_type: str,
    submission_id: str,
    participant_id: str,
    event_id: str,
) -> dict:
    """
    Write upload bytes to disk and return file metadata dict.

    Returns a dict with: id, path (relative to UPLOAD_DIR), mime_type,
    size_bytes, sha256, submission_id.
    """
    dest_dir = _submission_dir(event_id, participant_id, submission_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    # Prefix with file_id to avoid name collisions
    safe_name = f"{file_id}_{Path(filename).name}"
    abs_path = dest_dir / safe_name

    sha256 = hashlib.sha256(data).hexdigest()

    abs_path.write_bytes(data)

    rel_path = str(abs_path.relative_to(settings.upload_dir))

    return {
        "id": file_id,
        "submission_id": submission_id,
        "path": rel_path,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "sha256": sha256,
    }


def get_upload_path(path: str) -> Path:
    """Return absolute Path for a relative file path stored in the DB."""
    return Path(settings.upload_dir) / path


def delete_upload(path: str) -> bool:
    """Delete a file from disk. Returns True if deleted, False if not found."""
    abs_path = get_upload_path(path)
    try:
        abs_path.unlink()
        return True
    except FileNotFoundError:
        return False
