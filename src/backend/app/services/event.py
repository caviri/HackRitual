"""
The ritual state machine and its wards.

A deployment hosts exactly one Event. It advances through five states in a
fixed order; each state gates what the rest of the platform may do. This module
owns the transition rules, the configuration defaults, and the `EventGuard` that
other routers lean on to refuse work the current state forbids.

    DRAFT → OPEN → FROZEN → FINAL → ARCHIVED

The only backward step is the reopen FROZEN → OPEN, and it must be asked for
explicitly (`confirm=True`) because it undoes a closing of the gates.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.event import Event

# --------------------------------------------------------------------------- #
# State machine
# --------------------------------------------------------------------------- #
STATES = ("DRAFT", "OPEN", "FROZEN", "FINAL", "ARCHIVED")

# Allowed forward transitions, plus the one sanctioned reversal (reopen).
TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"OPEN"},
    "OPEN": {"FROZEN"},
    "FROZEN": {"FINAL", "OPEN"},  # OPEN is the admin-override reopen
    "FINAL": {"ARCHIVED"},
    "ARCHIVED": set(),
}

# Transitions that undo a closing and therefore demand explicit confirmation.
REOPEN = ("FROZEN", "OPEN")

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
DEFAULT_CONFIG: dict = {
    "registration_open": True,
    "submission_limit_per_participant": 10,
    "submission_limit_window_hours": 24,
    "leaderboard_mode": "best",  # best | latest
    "agent_policy": "allowed",   # allowed | forbidden
    "auto_score": True,          # run the default scorer on submission create
    "tracks": [],
}

# Fields that must not change once the gates have opened — they would
# retroactively rewrite the rules participants already played under.
LOCKED_AFTER_OPEN: set[str] = {"leaderboard_mode"}

# States in which configuration may still be edited.
CONFIG_EDITABLE_STATES: set[str] = {"DRAFT", "OPEN"}


def load_config(event: Event) -> dict:
    """Merge the event's stored config over the defaults."""
    stored: dict = {}
    if event.config_json:
        try:
            stored = json.loads(event.config_json)
        except (ValueError, TypeError):
            stored = {}
    return {**DEFAULT_CONFIG, **stored}


def dump_config(config: dict) -> str:
    return json.dumps(config)


# --------------------------------------------------------------------------- #
# Event access
# --------------------------------------------------------------------------- #
def get_event(db: Session) -> Event:
    """
    Fetch the singleton event.

    Prefers the configured `EVENT_ID`, but falls back to the first row to stay
    tolerant of a request that races lifespan seeding on the very first boot.
    """
    event = db.get(Event, settings.event_id)
    if event is None:
        event = db.query(Event).first()
    if event is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "event not seeded"
        )
    return event


# --------------------------------------------------------------------------- #
# Transition validation
# --------------------------------------------------------------------------- #
def validate_transition(current: str, target: str, *, confirm: bool) -> None:
    """
    Raise if moving from `current` to `target` is not permitted.

    409 Conflict for an illegal transition; 400 Bad Request for an unknown
    target state or a reopen that was not explicitly confirmed.
    """
    if target not in STATES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"unknown state '{target}'"
        )
    allowed = TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"cannot transition from {current} to {target}",
        )
    if (current, target) == REOPEN and not confirm:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "reopening a FROZEN event requires confirm=true",
        )


# --------------------------------------------------------------------------- #
# State-based guard
# --------------------------------------------------------------------------- #
class EventGuard:
    """
    A read-only view of the event's state, used to gate operations.

    Inject via :func:`get_event_guard` and call :meth:`require_state` at the top
    of a handler, or query the `can_*` predicates for finer control.
    """

    def __init__(self, state: str) -> None:
        self.state = state

    def require_state(self, *allowed_states: str) -> None:
        """Raise 409 Conflict if the event is not in one of `allowed_states`."""
        if self.state not in allowed_states:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"operation not allowed while event is {self.state}; "
                f"requires {' or '.join(allowed_states)}",
            )

    def can_submit(self) -> bool:
        return self.state == "OPEN"

    def can_register(self) -> bool:
        return self.state in {"DRAFT", "OPEN"}

    def can_score(self) -> bool:
        return self.state in {"OPEN", "FROZEN"}

    def can_export(self) -> bool:
        return self.state in {"FINAL", "ARCHIVED"}

    def is_read_only(self) -> bool:
        return self.state == "ARCHIVED"


def get_event_guard(db: Session = Depends(get_db)) -> EventGuard:
    """FastAPI dependency yielding an :class:`EventGuard` for the current event."""
    return EventGuard(get_event(db).state)


# --------------------------------------------------------------------------- #
# Automatic transitions
# --------------------------------------------------------------------------- #
def next_auto_state(
    state: str, now: datetime, start: datetime, end: datetime
) -> str | None:
    """
    Decide the auto-transition (if any) for the given clock reading.

    Pure and side-effect free so it can be unit-tested without a DB:
    DRAFT opens once `start` has passed; OPEN freezes once `end` has passed.
    Returns the target state, or None if no transition is due.
    """
    # Normalise to aware UTC so naive DB timestamps compare cleanly.
    def _aware(dt: datetime) -> datetime:
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    now, start, end = _aware(now), _aware(start), _aware(end)
    if state == "DRAFT" and now >= start:
        return "OPEN"
    if state == "OPEN" and now >= end:
        return "FROZEN"
    return None
