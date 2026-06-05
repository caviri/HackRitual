"""Admin-only operations beyond CRUD — seeding, etc."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.user import User
from app.services import seeder


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
