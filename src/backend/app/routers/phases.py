"""Phase CRUD — sub-phases within the event lifecycle."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.phase import Phase
from app.models.user import User
from app.schemas.content import PhaseCreate, PhaseResponse, PhaseUpdate

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


@router.patch("/{phase_id}", response_model=PhaseResponse)
def update_phase(
    phase_id: str,
    body: PhaseUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Phase:
    phase = db.get(Phase, phase_id)
    if not phase:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "phase not found")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "no fields to update")
    starts = changes.get("starts_at", phase.starts_at)
    ends = changes.get("ends_at", phase.ends_at)
    if starts and ends:
        s_naive = starts.replace(tzinfo=None) if getattr(starts, "tzinfo", None) else starts
        e_naive = ends.replace(tzinfo=None) if getattr(ends, "tzinfo", None) else ends
        if e_naive <= s_naive:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ends_at must be after starts_at")
    for field, value in changes.items():
        setattr(phase, field, value)
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
