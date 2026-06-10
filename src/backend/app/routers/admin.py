"""Admin-only operations beyond CRUD — seeding and the console aggregations."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.user import User
from app.services import admin_console, seeder


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/seed")
def seed_demo_data(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict[str, int]:
    """Idempotently insert fixture data for tables to look populated.

    Safe to call repeatedly — only inserts rows that don't already exist.
    """
    return seeder.seed_fixtures(db)


# ─── Console aggregations (Step 09) ──────────────────────────────────────────


@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Live overview: event state, headline metrics, recent audit."""
    return admin_console.dashboard(db)


@router.get("/scoring/status")
def admin_scoring_status(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Scorer identity, score-status counts, and a value histogram."""
    return admin_console.scoring_status(db)


@router.get("/audit")
def admin_audit(
    action: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    since_hours: Optional[int] = Query(None, ge=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Filterable, paginated audit log across all actions."""
    return admin_console.audit_query(
        db, action=action, actor=actor, page=page, per_page=per_page, since_hours=since_hours
    )
