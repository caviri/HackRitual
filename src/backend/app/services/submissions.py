"""
Submission rules — the gates the work must pass through.

The lifecycle (Step 06) decides *when* work may be offered; the event config
decides *how much*. This module holds both checks plus the ownership map, so the
router stays thin and the rules are tested in one place.

Offerings are accepted only while the event is OPEN, capped per participant over
a rolling window, and may be withdrawn only by their owners while still OPEN.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.middleware.actor import Actor
from app.models.submission import Submission
from app.services.event import EventGuard, get_event, load_config
from app.services.participants import get_user_participants


# --------------------------------------------------------------------------- #
# State gating (ties Step 07 to the Step 06 ritual)
# --------------------------------------------------------------------------- #
def require_open(db: Session) -> None:
    """Raise 409 unless the event is OPEN — the only state that accepts work."""
    EventGuard(get_event(db).state).require_state("OPEN")


# --------------------------------------------------------------------------- #
# Submission limits (from event config)
# --------------------------------------------------------------------------- #
def submission_count_in_window(
    db: Session, participant_id: str, window_hours: int
) -> int:
    """Count a participant's live submissions within the rolling window."""
    window_start = datetime.utcnow() - timedelta(hours=window_hours)
    return (
        db.query(Submission)
        .filter(
            Submission.participant_id == participant_id,
            Submission.created_at >= window_start,
            Submission.status != "withdrawn",
        )
        .count()
    )


def enforce_submission_limit(db: Session, participant_id: str) -> None:
    """
    Raise 429 if the participant has reached the configured cap for the window.

    Withdrawn submissions don't count, so withdrawing frees a slot.
    """
    config = load_config(get_event(db))
    limit = config["submission_limit_per_participant"]
    window = config["submission_limit_window_hours"]
    count = submission_count_in_window(db, participant_id, window)
    if count >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"submission limit reached: {limit} per {window}h window",
        )


# --------------------------------------------------------------------------- #
# Ownership
# --------------------------------------------------------------------------- #
def participant_ids_for_actor(db: Session, actor: Actor) -> set[str]:
    """The participant ids the actor may act on behalf of.

    Humans own the participants they are a member of; an agent owns the
    participant its credential is linked to (Step 13).
    """
    if actor.user is not None:
        return {p.id for p in get_user_participants(db, actor.user.id)}
    if actor.agent is not None:
        from app.services.agents import agent_participant

        p = agent_participant(db, actor.agent)
        return {p.id} if p else set()
    return set()


def assert_can_act_on(db: Session, actor: Actor, submission: Submission) -> None:
    """Raise 403 unless the actor owns the submission's participant, or is admin."""
    if actor.is_admin:
        return
    if submission.participant_id in participant_ids_for_actor(db, actor):
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN, "not your submission"
    )
