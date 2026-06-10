"""Export bundle — the artefact the ritual produces.

Run on ARCHIVED state. Writes a single zip that contains:

  - manifest.json     — event meta, sha256s, build info
  - db/app.db         — SQLite snapshot (via sqlite3 backup API for consistency)
  - audit_log.json    — full audit log dump
  - uploads/...       — every file under UPLOAD_DIR, preserved
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import IO

from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit_log import AuditLog
from app.models.event import Event


def _sqlite_snapshot(src_path: str, dst: IO[bytes]) -> None:
    """Use sqlite3's backup API for a consistent, in-flight-safe snapshot."""
    tmp_path = src_path + ".export.tmp"
    src = sqlite3.connect(src_path)
    bak = sqlite3.connect(tmp_path)
    try:
        src.backup(bak)
    finally:
        bak.close()
        src.close()
    try:
        with open(tmp_path, "rb") as f:
            dst.write(f.read())
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def build_export(db: Session) -> bytes:
    """Build the zip bundle in memory and return its bytes.

    For small events this is fine; for large events we'd stream to disk.
    """
    buf = io.BytesIO()

    event = db.query(Event).first()
    audit_rows = db.query(AuditLog).order_by(AuditLog.created_at).all()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # ── audit log
        audit_payload = [
            {
                "id": r.id,
                "actor_user_id": r.actor_user_id,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "metadata_json": r.metadata_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in audit_rows
        ]
        zf.writestr("audit_log.json", json.dumps(audit_payload, indent=2))

        # ── sqlite snapshot
        db_bytes = io.BytesIO()
        _sqlite_snapshot(settings.db_path, db_bytes)
        db_bytes_value = db_bytes.getvalue()
        zf.writestr("db/app.db", db_bytes_value)

        # ── showcase digest + standalone HTML
        # Both live at the root of the zip so a quick "unzip and double-click
        # showcase.html" gives the recipient the human-readable view.
        from app.services.showcase import build_showcase
        from app.services.showcase_html import render_showcase_html

        showcase = build_showcase(db)
        showcase_json_bytes = json.dumps(showcase, indent=2, ensure_ascii=False).encode("utf-8")
        showcase_html_bytes = render_showcase_html(showcase).encode("utf-8")
        zf.writestr("showcase.json", showcase_json_bytes)
        zf.writestr("showcase.html", showcase_html_bytes)

        # ── uploads tree
        upload_root = Path(settings.upload_dir)
        upload_files: list[dict[str, object]] = []
        if upload_root.is_dir():
            for path in upload_root.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(upload_root)
                content = path.read_bytes()
                zf.writestr(f"uploads/{rel}", content)
                upload_files.append(
                    {
                        "path": str(rel),
                        "size_bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )

        # ── manifest, written last so its sha256s cover the contents
        manifest = {
            "schema": "hackritual.export.v1",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "event": {
                "id": event.id if event else settings.event_id,
                "title": event.title if event else settings.event_title,
                "state": event.state if event else "UNKNOWN",
                "start_at": event.start_at.isoformat() if event and event.start_at else None,
                "end_at": event.end_at.isoformat() if event and event.end_at else None,
            },
            "counts": {
                "audit_log_rows": len(audit_payload),
                "upload_files": len(upload_files),
                "showcase_projects": len(showcase.get("projects", [])),
                "showcase_participants": len(showcase.get("participants", [])),
            },
            "db_sha256": hashlib.sha256(db_bytes_value).hexdigest(),
            "showcase_json_sha256": hashlib.sha256(showcase_json_bytes).hexdigest(),
            "showcase_html_sha256": hashlib.sha256(showcase_html_bytes).hexdigest(),
            "upload_files": upload_files,
            "version": settings.app_version,
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    return buf.getvalue()
