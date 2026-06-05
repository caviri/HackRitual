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

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.actor import Actor, get_current_actor, hash_api_key
from app.middleware.auth import get_current_user
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agents import (
    AgentCreate,
    AgentCreatedResponse,
    AgentResponse,
    AgentSelfResponse,
)


router = APIRouter(prefix="/api/agents", tags=["agents"])
self_router = APIRouter(prefix="/api/agent", tags=["agents"])


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
    plain = _mint_key()
    agent = Agent(
        name=body.name,
        owner_user_id=user.id,
        api_key_hash=hash_api_key(plain),
        status="active",
    )
    db.add(agent)
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
