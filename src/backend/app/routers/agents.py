"""Agent management — the bot side of HackRitual.

Endpoints:

  GET    /api/agents              list (admin sees all, users see their own)
  POST   /api/agents              create (any authed user), returns one-time key
  POST   /api/agents/{id}/rotate  regenerate key (owner or admin)
  POST   /api/agents/{id}/revoke  flip status=revoked (owner or admin)
  DELETE /api/agents/{id}         hard delete (owner or admin)
  GET    /api/agent/me            agent identifies itself via X-API-Key

The agent's plaintext API key is only ever returned by `create` and `rotate`.
It is not stored — only its SHA-256 hash is.
"""

from __future__ import annotations

import json
import secrets
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.actor import Actor, get_current_actor, hash_api_key
from app.middleware.auth import get_current_user, require_admin
from app.models.agent import Agent
from app.models.project import Project
from app.models.submission import Submission
from app.models.user import User
from app.schemas.agents import (
    AgentAdminCreate,
    AgentCreate,
    AgentCreatedResponse,
    AgentResponse,
    AgentSelfResponse,
    AgentSubmissionCreate,
    AgentSubmissionStatus,
)
from app.schemas.leaderboard import (
    LeaderboardEntry,
    LeaderboardParticipant,
    LeaderboardResponse,
)
from app.schemas.projects import SubmissionResponse
from app.services import notifications
from app.services import submissions as submission_rules
from app.services.agents import agent_participant, link_agent_participant
from app.services.audit import log_action
from app.services.event import get_event, load_config
from app.services.leaderboard import build_leaderboard
from app.services.scoring_service import active_score, score_submission


router = APIRouter(prefix="/api/agents", tags=["agents"])
self_router = APIRouter(prefix="/api/agent", tags=["agents"])
admin_router = APIRouter(prefix="/api/admin/agents", tags=["agents"])


def _require_agent(actor: Actor) -> Agent:
    if actor.agent is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "this endpoint is agent-only — supply an API key",
        )
    return actor.agent


def _mint_key() -> str:
    """Generate a new plaintext API key. Prefix `ak_` makes them recognisable
    in logs/codebases and distinguishes them from JWT bearer tokens."""
    return "ak_" + secrets.token_urlsafe(32)


def _key_preview(plaintext: str) -> str:
    """Last-4 fingerprint shown in lists. Useful for "is this the key I
    have?" confirmation without exposing the secret."""
    return f"…{plaintext[-4:]}" if len(plaintext) >= 4 else "…????"


def _agent_to_response(agent: Agent, db: Session, key_plain: Optional[str] = None) -> AgentResponse:
    owner_email = None
    if agent.owner_user_id:
        owner = db.get(User, agent.owner_user_id)
        if owner:
            owner_email = owner.email
    # We don't store the plaintext so we can't reconstruct the suffix after creation.
    # On a fresh create/rotate we know it; otherwise we just show a hashy short.
    preview = _key_preview(key_plain) if key_plain else f"#{agent.api_key_hash[:4]}"
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        owner_user_id=agent.owner_user_id,
        owner_email=owner_email,
        status=agent.status,
        created_at=agent.created_at,
        key_preview=preview,
    )


def _ensure_owner_or_admin(agent: Agent, actor: Actor) -> None:
    if actor.is_admin:
        return
    if actor.user and agent.owner_user_id == actor.user.id:
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN, "not allowed to modify this agent"
    )


# ─── /api/agents ─────────────────────────────────────────────────────────────


@router.get("", response_model=list[AgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AgentResponse]:
    q = db.query(Agent)
    if user.role != "admin":
        q = q.filter(Agent.owner_user_id == user.id)
    rows = q.order_by(Agent.created_at.desc()).all()
    return [_agent_to_response(a, db) for a in rows]


@router.post("", response_model=AgentCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentCreatedResponse:
    # Self-service agent creation is gated by the event's agent policy.
    if load_config(get_event(db)).get("agent_policy") != "allowed":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "agents are not permitted for this event",
        )
    plain = _mint_key()
    agent = Agent(
        name=body.name,
        owner_user_id=user.id,
        api_key_hash=hash_api_key(plain),
        status="active",
    )
    db.add(agent)
    db.flush()
    # An agent is a first-class participant — give it one so it can compete.
    link_agent_participant(db, agent)
    log_action(
        db,
        "agent.created",
        actor_id=user.id,
        target_type="agent",
        target_id=agent.id,
        metadata={"name": agent.name, "owner": "self"},
    )
    db.commit()
    db.refresh(agent)
    return AgentCreatedResponse(
        agent=_agent_to_response(agent, db, key_plain=plain),
        api_key=plain,
    )


@router.post("/{agent_id}/rotate", response_model=AgentCreatedResponse)
def rotate_agent_key(
    agent_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> AgentCreatedResponse:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "agent not found")
    _ensure_owner_or_admin(agent, actor)
    plain = _mint_key()
    agent.api_key_hash = hash_api_key(plain)
    agent.status = "active"
    db.add(agent)
    log_action(
        db,
        "agent.key_rotated",
        actor_id=actor.user.id if actor.user else None,
        target_type="agent",
        target_id=agent.id,
    )
    db.commit()
    db.refresh(agent)
    return AgentCreatedResponse(
        agent=_agent_to_response(agent, db, key_plain=plain),
        api_key=plain,
    )


@router.post("/{agent_id}/revoke", response_model=AgentResponse)
def revoke_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> AgentResponse:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "agent not found")
    _ensure_owner_or_admin(agent, actor)
    agent.status = "revoked"
    log_action(
        db,
        "agent.revoked",
        actor_id=actor.user.id if actor.user else None,
        target_type="agent",
        target_id=agent.id,
    )
    db.commit()
    db.refresh(agent)
    return _agent_to_response(agent, db)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> None:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "agent not found")
    _ensure_owner_or_admin(agent, actor)
    db.delete(agent)
    db.commit()


# ─── /api/agent/me ───────────────────────────────────────────────────────────


@self_router.get("/me", response_model=AgentSelfResponse)
def agent_me(
    actor: Actor = Depends(get_current_actor),
) -> AgentSelfResponse:
    """Identify the calling agent. Requires `X-API-Key`. Returns 401 if a User
    is the one authenticated — this endpoint is agent-only."""
    if actor.agent is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "this endpoint is agent-only — supply X-API-Key",
        )
    return AgentSelfResponse(
        id=actor.agent.id,
        name=actor.agent.name,
        owner_user_id=actor.agent.owner_user_id,
        status=actor.agent.status,
        created_at=actor.agent.created_at,
    )


# ─── Agent submission API (key-authenticated, /api/agent/*) ──────────────────


@self_router.post(
    "/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def agent_create_submission(
    body: AgentSubmissionCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> Submission:
    """Submit as an agent. Same gating, limits, and scoring as humans."""
    agent = _require_agent(actor)
    participant = link_agent_participant(db, agent)

    submission_rules.require_open(db)
    submission_rules.enforce_submission_limit(db, participant.id)

    # Resolve the project: an explicit one, or the agent's own default.
    if body.project_id:
        project = db.get(Project, body.project_id)
        if project is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown project")
    else:
        title = f"agent:{agent.name}"
        project = (
            db.query(Project)
            .filter(
                Project.event_id == settings.event_id,
                Project.proposed_by_participant_id == participant.id,
                Project.title == title,
            )
            .first()
        )
        if project is None:
            project = Project(
                event_id=settings.event_id,
                proposed_by_participant_id=participant.id,
                title=title,
                description=f"autonomous submissions by {agent.name}",
                status="proposed",
            )
            db.add(project)
            db.flush()

    existing_max = (
        db.query(func.coalesce(func.max(Submission.version), 0))
        .filter(
            Submission.project_id == project.id,
            Submission.participant_id == participant.id,
        )
        .scalar()
    )
    sub = Submission(
        event_id=settings.event_id,
        project_id=project.id,
        participant_id=participant.id,
        version=(existing_max or 0) + 1,
        title=body.title,
        description=body.description,
        result=body.result,
        payload_json=json.dumps(body.payload) if body.payload is not None else None,
        status="draft",
    )
    db.add(sub)
    db.flush()
    if load_config(get_event(db)).get("auto_score"):
        score_submission(db, sub.id)
    from app.services import metrics_service

    metrics_service.increment(db, "agent_submissions_count")
    db.commit()
    db.refresh(sub)
    # Agent participants carry no human email, so this is a no-op for them.
    notifications.notify_submission_received(background, db, sub)
    return sub


@self_router.get(
    "/submissions/{submission_id}", response_model=AgentSubmissionStatus
)
def agent_submission_status(
    submission_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> AgentSubmissionStatus:
    """An agent checks one of its own submissions, with score if available."""
    agent = _require_agent(actor)
    participant = agent_participant(db, agent)
    sub = db.get(Submission, submission_id)
    if sub is None or participant is None or sub.participant_id != participant.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    score = active_score(db, sub.id)
    return AgentSubmissionStatus(
        id=sub.id,
        participant_id=sub.participant_id,
        status=sub.status,
        version=sub.version,
        score=score.score_value if score else None,
        created_at=sub.created_at,
    )


@self_router.get("/leaderboard", response_model=LeaderboardResponse)
def agent_leaderboard(
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> LeaderboardResponse:
    """The public leaderboard, reached with an API key."""
    _require_agent(actor)
    event = get_event(db)
    mode = load_config(event).get("leaderboard_mode", "best")
    rows = build_leaderboard(db, event.id, mode=mode)
    return LeaderboardResponse(
        event_id=event.id,
        event_state=event.state,
        leaderboard_mode=mode,
        entries=[
            LeaderboardEntry(
                rank=i + 1,
                participant=LeaderboardParticipant(
                    id=r.participant.id,
                    display_name=r.participant.display_name,
                    type=r.participant.type,
                ),
                score=r.score,
                submission_count=r.submission_count,
                last_submission_at=r.last_submission_at,
            )
            for i, r in enumerate(rows)
        ],
    )


# ─── Admin agent management (/api/admin/agents) ──────────────────────────────


@admin_router.post(
    "", response_model=AgentCreatedResponse, status_code=status.HTTP_201_CREATED
)
def admin_create_agent(
    body: AgentAdminCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AgentCreatedResponse:
    """Admin mints an agent, optionally on behalf of a user. Bypasses policy."""
    if body.owner_user_id and db.get(User, body.owner_user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "owner user not found")
    plain = _mint_key()
    agent = Agent(
        name=body.name,
        owner_user_id=body.owner_user_id,
        api_key_hash=hash_api_key(plain),
        status="active",
    )
    db.add(agent)
    db.flush()
    link_agent_participant(db, agent)
    log_action(
        db,
        "agent.created",
        actor_id=admin.id,
        target_type="agent",
        target_id=agent.id,
        metadata={"name": agent.name, "owner": body.owner_user_id or "admin"},
    )
    db.commit()
    db.refresh(agent)
    return AgentCreatedResponse(
        agent=_agent_to_response(agent, db, key_plain=plain),
        api_key=plain,
    )


@admin_router.get("", response_model=list[AgentResponse])
def admin_list_agents(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[AgentResponse]:
    rows = db.query(Agent).order_by(Agent.created_at.desc()).all()
    return [_agent_to_response(a, db) for a in rows]
