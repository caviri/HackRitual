"""
FastAPI auth dependencies — the gatekeepers.

Usage::

    @router.get("/protected")
    async def protected(user: User = Depends(get_current_user)):
        ...

    @router.post("/admin-only")
    async def admin_only(user: User = Depends(require_admin)):
        ...
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import decode_jwt


def get_current_user(
    session: Annotated[str | None, Cookie()] = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Extract the JWT from the `session` cookie or Authorization header, validate it, and return the User.
    Raises 401 if the token is absent, invalid, or expired.
    """
    from app.models.user import User

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )

    # Try cookie first
    if session is None and request:
        # Try Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session = auth_header[7:]  # Remove "Bearer " prefix
    
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

    return user


def require_admin(user=Depends(get_current_user)):
    """Raises 403 if the authenticated user does not hold the admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_role(*roles: str):
    """
    Factory that returns a dependency requiring one of the given roles.

    Usage::

        @router.get("/judges")
        async def judges_only(user = Depends(require_role("judge", "admin"))):
            ...
    """
    def _dep(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(roles)}",
            )
        return user
    return _dep
