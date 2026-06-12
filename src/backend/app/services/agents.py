"""
Agent participation — the bridge from an `Agent` credential to a `Participant`.

An agent is a first-class participant: it competes, submits, and is scored under
the same rules as a human. To do that it needs a `Participant` row (type
``agent``) and a `ParticipantMember` link carrying its `agent_id`. This module
creates and resolves that linkage so the agent endpoints can act on behalf of
the right participant.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember


def agent_participant(db: Session, agent: Agent) -> Participant | None:
    """Resolve the participant linked to this agent, if any."""
    return (
        db.query(Participant)
        .join(ParticipantMember, ParticipantMember.participant_id == Participant.id)
        .filter(
            Participant.event_id == settings.event_id,
            ParticipantMember.agent_id == agent.id,
        )
        .first()
    )


def link_agent_participant(db: Session, agent: Agent) -> Participant:
    """
    Get-or-create the agent's `agent`-type participant and its member link.

    Idempotent: calling twice returns the same participant. Does not commit —
    the caller owns the transaction.
    """
    existing = agent_participant(db, agent)
    if existing is not None:
        return existing

    participant = Participant(
        event_id=settings.event_id,
        type="agent",
        display_name=agent.name,
        status="active",
    )
    db.add(participant)
    db.flush()
    db.add(
        ParticipantMember(
            participant_id=participant.id,
            agent_id=agent.id,
            role_in_team="agent",
        )
    )
    db.flush()
    return participant
