"""
Health check endpoint.

GET /api/health

Returns operational status including:
- DB connectivity
- Persistent storage detection
- Event identity
- App version
"""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """
    Schema for the ``GET /api/health`` response.

    Attributes:
        status:             Always ``"ok"`` when the endpoint is reachable.
        version:            Application version string (e.g. ``"0.1.0"``).
        event_id:           Configured event identifier from ``EVENT_ID``.
        event_state:        Current ritual state (``DRAFT`` | ``OPEN`` | ``FROZEN`` |
                            ``FINAL`` | ``ARCHIVED``).  Placeholder until Step 02.
        persistent_storage: ``True`` if ``/data`` appears to be a non-ephemeral mount.
                            ``False`` means data will be lost on container restart.
        db_ok:              ``True`` if a trivial ``SELECT 1`` against the SQLite
                            database succeeds.
    """

    status: Literal["ok"]
    version: str
    event_id: str
    event_state: str
    persistent_storage: bool
    db_ok: bool


def _check_persistent_storage(data_dir: str) -> bool:
    """
    Heuristic check for whether ``data_dir`` is backed by persistent storage.

    Strategy (Linux):

    1. Write a marker file and read it back to confirm the filesystem is writable.
    2. Parse ``/proc/mounts`` looking for a non-``tmpfs`` mount point matching
       ``data_dir``.  If found, the directory is considered persistent.
    3. If ``/proc/mounts`` is unavailable (non-Linux), assume persistent.

    On Hugging Face Spaces the persistent volume is mounted at ``/data``
    as a real filesystem (not tmpfs), so this heuristic works correctly.

    Args:
        data_dir: Absolute path to the directory that should be persistent
                  (typically the parent of ``DB_PATH``, e.g. ``"/data"``).

    Returns:
        ``True`` if the directory appears to be on a persistent non-tmpfs mount,
        ``False`` if it is likely ephemeral (tmpfs or write failure).
    """
    marker = os.path.join(data_dir, ".hackritual_persistent_check")
    try:
        with open(marker, "w") as fh:
            fh.write("ok")
        with open(marker) as fh:
            result = fh.read()
        os.unlink(marker)
        if result != "ok":
            return False
        # Best-effort: check /proc/mounts for a non-tmpfs mount on data_dir
        try:
            with open("/proc/mounts") as mf:
                mounts = mf.read()
            # If any line shows /data mounted on something other than tmpfs
            for line in mounts.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[1] == data_dir and parts[2] != "tmpfs":
                    return True
            # /data not found as a dedicated mount → likely ephemeral
            # but we still return True if the write succeeded on non-Linux
            return os.path.exists("/proc/mounts") is False
        except OSError:
            # Not Linux or /proc not available — assume persistent
            return True
    except OSError:
        return False


def _check_db(db_path: str) -> bool:
    """
    Verify that the SQLite database is reachable by executing ``SELECT 1``.

    Opens a short-lived synchronous connection (bypassing SQLAlchemy) so this
    check works before the DB layer is fully initialised (e.g. during startup).

    Args:
        db_path: Filesystem path to the SQLite database file.

    Returns:
        ``True`` if the query succeeds, ``False`` otherwise.
        Failures are logged at ``WARNING`` level.
    """
    try:
        con = sqlite3.connect(db_path, timeout=5)
        con.execute("SELECT 1")
        con.close()
        return True
    except Exception as exc:
        logger.warning("DB health check failed", extra={"error": str(exc)})
        return False


@router.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """
    Return operational status of the running HackRitual instance.

    This endpoint is unauthenticated and is used by:

    - Docker ``HEALTHCHECK`` directives
    - The Hugging Face Spaces health probe
    - Operators verifying a fresh deployment

    Returns:
        A :class:`HealthResponse` reflecting current DB and storage status.
    """
    from app.config import settings  # late import to allow test overrides

    data_dir = os.path.dirname(settings.db_path)
    persistent = _check_persistent_storage(data_dir)
    db_ok = _check_db(settings.db_path)

    if not persistent:
        logger.warning(
            "EPHEMERAL STORAGE DETECTED — data will be lost on container restart. "
            "Enable persistent storage at /data to avoid data loss."
        )

    # Read event_state from DB (Step 02+). Fall back to "DRAFT" if not seeded yet.
    event_state = "DRAFT"
    if db_ok:
        try:
            from app.database import SessionLocal
            from app.models.event import Event

            with SessionLocal() as db:
                ev = db.get(Event, settings.event_id)
                if ev is not None:
                    event_state = ev.state
        except Exception:
            pass

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        event_id=settings.event_id,
        event_state=event_state,
        persistent_storage=persistent,
        db_ok=db_ok,
    )
