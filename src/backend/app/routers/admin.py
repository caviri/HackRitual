"""Admin-only operations beyond CRUD — seeding and the console aggregations."""

from __future__ import annotations

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


@router.post("/demo/rebuild")
def rebuild_demo_stages(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Raze and regrow all five demo stage snapshots (DEMO_STAGES=true only).

    Works from inside any stage sandbox — the keeper is seeded everywhere.
    """
    from fastapi import HTTPException, status

    from app.config import settings
    from app.services.audit import log_action
    from app.services.demo_stages import build_all

    if not settings.demo_stages:
        raise HTTPException(status.HTTP_409_CONFLICT, "DEMO_STAGES is not enabled")
    rebuilt = build_all(force=True)

    # Audit on the PRIMARY trail: the rebuild may have erased the very stage
    # DB this request authenticated against, so the actor's row id is gone —
    # record the email instead.
    from app.database import SessionLocal

    with SessionLocal() as primary:
        log_action(primary, "demo.rebuilt", actor_id=None,
                   metadata={"stages": sorted(rebuilt), "by": admin.email})
        primary.commit()
    return {"rebuilt": rebuilt}


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
    action: str | None = Query(None),
    actor: str | None = Query(None),
    since_hours: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Filterable, paginated audit log across all actions."""
    return admin_console.audit_query(
        db, action=action, actor=actor, page=page, per_page=per_page, since_hours=since_hours
    )
