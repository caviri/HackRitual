"""
GitHub push orchestration + status (Step 17).

Bridges the export bundle, the static site, the secret scan, and the GitHub
service — and holds the in-memory push status the admin endpoint reads. Invoked
from the task-queue `push_github` handler so a large push never blocks a request.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from app.config import settings
from app.database import SessionLocal
from app.services import github_service, static_site
from app.services.export_bundle import RedactionConfig, bundle_files

_lock = threading.Lock()
_status: dict[str, dict] = {}  # export_id → status dict


def set_status(export_id: str, **fields) -> None:
    with _lock:
        cur = _status.get(export_id, {})
        cur.update(fields)
        _status[export_id] = cur


def get_status(export_id: str) -> dict | None:
    with _lock:
        s = _status.get(export_id)
        return dict(s) if s is not None else None


async def run_push(payload: dict) -> dict:
    """
    Build the archive (JSON + static HTML), scan for secrets, and push to GitHub.

    `payload`: {export_id, redaction_mode, branch, commit_message}. Repo/token come
    from settings. Returns the GitHub result; raises on any failure.
    """
    repo = settings.github_export_repo
    token = settings.github_token
    if not repo or not token:
        raise RuntimeError("GITHUB_EXPORT_REPO and GITHUB_TOKEN must be set")

    redaction = RedactionConfig(mode=payload.get("redaction_mode", "public"))
    with SessionLocal() as db:
        files = bundle_files(db, redaction)
        files.update(static_site.generate(db))

    violations = github_service.validate_no_secrets(
        files, [settings.jwt_secret, settings.smtp_pass, token]
    )
    if violations:
        raise RuntimeError("; ".join(violations))

    result = await github_service.push_export(
        files,
        repo=repo,
        token=token,
        branch=payload.get("branch") or settings.github_export_branch,
        commit_message=payload.get("commit_message") or "Export HackRitual archive",
    )
    result["pushed_at"] = datetime.now(timezone.utc).isoformat()
    return result
