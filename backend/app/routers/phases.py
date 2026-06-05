"""Phase CRUD — sub-phases within the event lifecycle."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.phase import Phase
from app.models.user import User
from app.schemas.content import PhaseCreate, PhaseResponse


router = APIRouter(prefix="/api/phases", tags=["phases"])


@router.get("", response_model=list[PhaseResponse])
def list_phases(db: Session = Depends(get_db)) -> list[Phase]:
    return (
        db.query(Phase)
        .order_by(Phase.starts_at.asc().nullslast(), Phase.created_at)
        .all()
    )


@router.post("", response_model=PhaseResponse, status_code=status.HTTP_201_CREATED)
def create_phase(
    body: PhaseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Phase:
    phase = Phase(
        event_id=settings.event_id,
        name=body.name,
        description=body.description,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        created_by_user_id=admin.id,
        modified_by_user_id=admin.id,
    )
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase


@router.delete("/{phase_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_phase(
    phase_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    phase = db.get(Phase, phase_id)
    if not phase:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "phase not found")
    db.delete(phase)
    db.commit()
