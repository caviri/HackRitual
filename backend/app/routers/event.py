"""Singleton Event endpoints — read state + admin transitions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventResponse, StateTransitionRequest


router = APIRouter(prefix="/api", tags=["event"])

# Valid forward transitions in the ritual state machine.
TRANSITIONS = {
    "DRAFT": ["OPEN"],
    "OPEN": ["FROZEN"],
    "FROZEN": ["FINAL"],
    "FINAL": ["ARCHIVED"],
    "ARCHIVED": [],
}


def _get_event(db: Session) -> Event:
    event = db.get(Event, settings.event_id)
    if event is None:
        # On the very first request after startup we may race the lifespan
        # seeding. Try a generic first() to be tolerant.
        event = db.query(Event).first()
    if event is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "event not seeded")
    return event


@router.get("/event", response_model=EventResponse)
def get_event(db: Session = Depends(get_db)) -> Event:
    return _get_event(db)


@router.post("/event/transitions", response_model=EventResponse)
def transition(
    body: StateTransitionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Event:
    event = _get_event(db)
    allowed = TRANSITIONS.get(event.state, [])
    if body.to not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"cannot transition from {event.state} to {body.to}",
        )
    previous = event.state
    event.state = body.to
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="event.transition",
            target_type="event",
            target_id=event.id,
            metadata_json=f'{{"from":"{previous}","to":"{body.to}"}}',
        )
    )
    db.commit()
    db.refresh(event)
    return event
