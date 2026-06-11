"""Actor-aware authentication.

A request can come from either a human (`User`, via JWT cookie / bearer token)
or an autonomous agent (`Agent`, via the `X-API-Key` header). Both paths
funnel through `get_current_actor`, which returns a small discriminated-union
Actor wrapper.

When you only ever want humans, keep using `get_current_user`. When you want
"either humans or agents — both can do this", use `get_current_actor`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent
from app.models.user import User
from app.services.auth import decode_jwt


@dataclass
class Actor:
    """Discriminated wrapper around the two ways to identify a request."""

    user: User | None = None
    agent: Agent | None = None

    @property
    def kind(self) -> str:
        return "user" if self.user is not None else "agent"

    @property
    def id(self) -> str:
        if self.user is not None:
            return self.user.id
        assert self.agent is not None
        return self.agent.id

    @property
    def display(self) -> str:
        if self.user is not None:
            return self.user.email
        assert self.agent is not None
        return f"agent:{self.agent.name}"

    @property
    def is_admin(self) -> bool:
        return self.user is not None and self.user.role == "admin"


def hash_api_key(key: str) -> str:
    """One-way hash of an agent's plaintext API key. SHA-256 — fast enough for
    per-request auth, irreversible enough for storage."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _agent_from_api_key(db: Session, api_key: str) -> Agent | None:
    if not api_key:
        return None
    h = hash_api_key(api_key)
    agent = db.query(Agent).filter(Agent.api_key_hash == h).first()
    if agent is None or agent.status != "active":
        return None
    return agent


def get_current_actor(
    request: Request,
    session: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> Actor:
    """Resolve the current actor from request credentials.

    Priority:
      1. `X-API-Key` header  → Agent
      2. `Authorization: Bearer <key>` where the value starts with `ak_` → Agent
      3. JWT session cookie or `Authorization: Bearer <jwt>` → User

    Raises 401 if no valid credential is found.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="not authenticated",
    )

    # --- Agent paths ----------------------------------------------------
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer ak_"):
            api_key = auth_header[len("Bearer "):]

    if api_key:
        agent = _agent_from_api_key(db, api_key)
        if agent is None:
            # They TRIED to authenticate as an agent — fail loud rather than
            # silently fall back to user auth.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or revoked api key",
            )
        return Actor(agent=agent)

    # --- User path ------------------------------------------------------
    if session is None:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session = auth_header[len("Bearer "):]

    if session is None:
        raise credentials_exc

    try:
        payload = decode_jwt(session)
    except JWTError:
        raise credentials_exc

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exc

    user = db.get(User, user_id)
    if user is None or user.status == "inactive":
        raise credentials_exc

    return Actor(user=user)


def get_optional_actor(
    request: Request,
    session: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> Actor | None:
    """Like get_current_actor, but anonymous requests resolve to None
    instead of 401 — for public endpoints that adapt to who is asking."""
    try:
        return get_current_actor(request, session, db)
    except HTTPException:
        return None


def require_actor_admin(actor: Actor = Depends(get_current_actor)) -> Actor:
    """Admin gate that accepts an actor (agents can be admins in theory, but
    in practice this is for human admins only — agents that hold admin
    privileges would be a separate design decision)."""
    if not actor.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin access required",
        )
    return actor
