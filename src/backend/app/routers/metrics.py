"""
Aggregate metrics dashboard + a structured privacy endpoint (Step 18).

`/api/admin/metrics` serves daily counters and headline totals — aggregate only,
no per-user data. `/api/privacy` returns the data practices in structured form
for programmatic consumers (the human page lives in the frontend at `/privacy`).
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.user import User
from app.services import abuse_metrics, metrics_service

admin_metrics_router = APIRouter(prefix="/api/admin/metrics", tags=["metrics"])
privacy_router = APIRouter(prefix="/api", tags=["privacy"])


@admin_metrics_router.get("")
def metrics(
    start: str | None = Query(None, description="YYYY-MM-DD (default: 30 days ago)"),
    end: str | None = Query(None, description="YYYY-MM-DD (default: today)"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Daily aggregate counters + headline totals + ephemeral (in-memory) metrics."""
    start = start or (date.today() - timedelta(days=30)).isoformat()
    end = end or date.today().isoformat()
    return {
        "daily": metrics_service.get_daily(db, start, end),
        "totals": metrics_service.totals(db),
        "ephemeral": {
            "rate_limit": abuse_metrics.snapshot(),
        },
    }


@admin_metrics_router.get("/daily")
def metrics_daily(
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[dict]:
    start = start or (date.today() - timedelta(days=30)).isoformat()
    end = end or date.today().isoformat()
    return metrics_service.get_daily(db, start, end)


@privacy_router.get("/privacy")
def privacy() -> dict:
    """Structured statement of what HackRitual collects, and what it never does."""
    return {
        "collects": [
            "Email address — for your account and so organizers can reach you.",
            "Display name and affiliation — provided voluntarily for your profile.",
            "Submissions — the work you offer during the event.",
            "An audit trail of consequential admin actions.",
        ],
        "cookies": {
            "count": 1,
            "name": "session",
            "http_only": True,
            "purpose": "authentication",
            "third_party": False,
            "tracking": False,
        },
        "ip_addresses": {
            "stored_in_db": False,
            "rate_limiting": "truncated (/24, /64), in-memory only, never logged",
        },
        "statistics": "aggregate only — no per-user analytics, no third-party trackers",
        "retention": {
            "sessions": "expire per JWT TTL; cleaned hourly",
            "rate_limit_data": "in-memory only; cleared on restart",
            "event_data": "until export or deletion",
            "export_public": "curated, with emails hashed",
        },
        "your_rights": "Under GDPR you may access, rectify, or request deletion of your "
        "personal data — contact the event administrator.",
    }
