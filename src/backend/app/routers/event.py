"""
Singleton Event endpoints.

- Public: read the event and its current state/config.
- Admin: advance the state machine, edit configuration, read the history.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.user import User
from app.schemas.event import (
    AuditEntry,
    EventConfig,
    EventConfigUpdate,
    EventResponse,
    StateTransitionRequest,
    StateTransitionResponse,
)
from app.services.audit import log_action
from app.services.event import (
    CONFIG_EDITABLE_STATES,
    LOCKED_AFTER_OPEN,
    dump_config,
    get_event,
    load_config,
    validate_transition,
)

# Public read lives under /api; admin controls under /api/admin/event.
public_router = APIRouter(prefix="/api", tags=["event"])
admin_router = APIRouter(prefix="/api/admin/event", tags=["event"])


def _to_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        title=event.title,
        type=event.type,
        state=event.state,
        start=event.start_at,
        end=event.end_at,
        config=EventConfig(**load_config(event)),
    )


# --------------------------------------------------------------------------- #
# Public
# --------------------------------------------------------------------------- #
@public_router.get("/event", response_model=EventResponse)
def get_event_info(db: Session = Depends(get_db)) -> EventResponse:
    return _to_response(get_event(db))


# --------------------------------------------------------------------------- #
# Admin — state machine
# --------------------------------------------------------------------------- #
@admin_router.post("/state", response_model=StateTransitionResponse)
def transition_state(
    body: StateTransitionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> StateTransitionResponse:
    event = get_event(db)
    previous = event.state
    validate_transition(previous, body.state, confirm=body.confirm)

    event.state = body.state
    now = datetime.now(timezone.utc)
    event.updated_at = now
    log_action(
        db,
        "event.transition",
        actor_id=admin.id,
        target_type="event",
        target_id=event.id,
        metadata={
            "from": previous,
            "to": body.state,
            "reason": body.reason,
            "by": admin.email,
        },
    )
    db.commit()

    return StateTransitionResponse(
        id=event.id,
        state=event.state,
        previous_state=previous,
        transitioned_at=now,
        transitioned_by=admin.email,
    )


# --------------------------------------------------------------------------- #
# Admin — configuration
# --------------------------------------------------------------------------- #
@admin_router.patch("/config", response_model=EventResponse)
def update_config(
    body: EventConfigUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> EventResponse:
    event = get_event(db)
    if event.state not in CONFIG_EDITABLE_STATES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"configuration is frozen while event is {event.state}; "
            f"editable only in {' or '.join(sorted(CONFIG_EDITABLE_STATES))}",
        )

    changes = body.model_dump(exclude_unset=True)

    # Some fields lock once the gates have opened.
    if event.state == "OPEN":
        locked = LOCKED_AFTER_OPEN & changes.keys()
        if locked:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"cannot change {', '.join(sorted(locked))} after the event is OPEN",
            )

    config = load_config(event)
    config.update(changes)
    event.config_json = dump_config(config)
    event.updated_at = datetime.now(timezone.utc)
    log_action(
        db,
        "event.config_updated",
        actor_id=admin.id,
        target_type="event",
        target_id=event.id,
        metadata={"fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(event)
    return _to_response(event)


# --------------------------------------------------------------------------- #
# Admin — history
# --------------------------------------------------------------------------- #
@admin_router.get("/audit", response_model=list[AuditEntry])
def get_audit(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[AuditEntry]:
    event = get_event(db)
    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.target_type == "event",
            AuditLog.target_id == event.id,
            AuditLog.action.in_(["event.transition", "event.config_updated"]),
        )
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    entries: list[AuditEntry] = []
    for row in rows:
        metadata = None
        if row.metadata_json:
            try:
                metadata = json.loads(row.metadata_json)
            except (ValueError, TypeError):
                metadata = None
        entries.append(
            AuditEntry(
                id=row.id,
                action=row.action,
                actor_user_id=row.actor_user_id,
                target_type=row.target_type,
                target_id=row.target_id,
                metadata=metadata,
                created_at=row.created_at,
            )
        )
    return entries
