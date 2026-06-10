"""
Authentication endpoints — the gates of the ritual.

POST /api/auth/login    — present your access password, receive a session cookie
POST /api/auth/logout   — dissolve the session
POST /api/auth/refresh  — renew a near-expiry token
GET  /api/auth/me       — identify the current bearer
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.schemas.auth import LoginInput, LoginResponse, MeResponse, UserOut
from app.services import auth as auth_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE_NAME = "session"
_COOKIE_MAX_AGE = 86400  # 24 h


def _set_session_cookie(response: Response, token: str) -> None:
    from app.config import settings

    secure = settings.app_base_url.startswith("https://")
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE_NAME, path="/")


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


# ------------------------------------------------------------------ #
# POST /api/auth/login
# ------------------------------------------------------------------ #

@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Log in with an access password (admin-distributed). On success: issue a
    JWT session cookie.

    The password alone identifies the user. Failed attempts are throttled
    per IP (10 per 15 minutes); the error never reveals whether a password
    exists.
    """
    from datetime import datetime

    ip = _client_ip(request)

    if not auth_svc.check_rate_limit_login(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Wait a few minutes and try again.",
        )

    user = auth_svc.get_user_by_password(db, data.password)
    if user is None:
        auth_svc.record_login_failure(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access password.",
        )

    auth_svc.clear_login_failures(ip)

    user.last_login_at = datetime.now(UTC)
    token = auth_svc.create_jwt(user)
    _set_session_cookie(response, token)

    from app.services import metrics_service

    metrics_service.increment(db, "logins_count")
    db.commit()

    # ── Auto-create a solo human Participant in the current event so the
    # user can propose projects and create submissions immediately. Skip
    # silently if registration is closed (FROZEN/FINAL/ARCHIVED) or if the
    # user already has a participant.
    try:
        from app.config import settings as _settings
        from app.models.participant import Participant
        from app.models.participant_member import ParticipantMember

        already = (
            db.query(Participant)
            .join(ParticipantMember, ParticipantMember.participant_id == Participant.id)
            .filter(
                Participant.event_id == _settings.event_id,
                ParticipantMember.user_id == user.id,
            )
            .first()
        )
        if not already:
            from app.schemas.participants import ParticipantCreate
            from app.services.participants import (
                can_register_participant,
                create_solo_participant,
                get_event_state,
            )

            state = get_event_state(db)
            if can_register_participant(state):
                handle = user.display_name or user.email.split("@")[0]
                create_solo_participant(
                    db,
                    user,
                    ParticipantCreate(type="human", display_name=handle),
                    _settings.event_id,
                )
                # create_solo_participant flushes but does not commit
                db.commit()
    except Exception:
        # Never block signin on participant-create failure.
        db.rollback()

    return LoginResponse(user=UserOut.model_validate(user))


# ------------------------------------------------------------------ #
# POST /api/auth/logout
# ------------------------------------------------------------------ #

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    response: Response,
    _user=Depends(get_current_user),
) -> None:
    """Dissolve the session — clears the session cookie."""
    _clear_session_cookie(response)


# ------------------------------------------------------------------ #
# POST /api/auth/refresh
# ------------------------------------------------------------------ #

@router.post("/refresh", response_model=UserOut)
async def refresh(
    response: Response,
    session: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> UserOut:
    """
    Renew a near-expiry JWT. Returns 401 if the token is expired or invalid.
    Issues a fresh cookie only when the token is within 1 hour of expiry.
    """
    from app.models.user import User

    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = auth_svc.decode_jwt(session)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid or expired")

    user_id = payload.get("sub")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if auth_svc.is_near_expiry(payload):
        token = auth_svc.create_jwt(user)
        _set_session_cookie(response, token)

    return UserOut.model_validate(user)


# ------------------------------------------------------------------ #
# GET /api/auth/me
# ------------------------------------------------------------------ #

@router.get("/me", response_model=MeResponse)
async def me(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    """Return the identity of the current bearer. Raises 401 if not authenticated."""
    from app.config import settings
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.schemas.auth import PortraitInfo

    portrait = None
    if user.portrait_path:
        portrait = PortraitInfo(
            url=f"/uploads/{user.portrait_path}",
            effect=user.portrait_effect,
            contrast=user.portrait_contrast,
            brightness=user.portrait_brightness,
            scale=user.portrait_scale,
        )

    # Resolve the user's participant in the current event (if any).
    participant_dict = None
    p = (
        db.query(Participant)
        .join(ParticipantMember, ParticipantMember.participant_id == Participant.id)
        .filter(
            Participant.event_id == settings.event_id,
            ParticipantMember.user_id == user.id,
        )
        .first()
    )
    if p:
        participant_dict = {
            "id": p.id,
            "display_name": p.display_name,
            "type": p.type,
            "status": p.status,
            "is_waiting": bool(p.is_waiting),
            "affiliation": p.affiliation,
        }

    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        participant=participant_dict,
        portrait=portrait,
    )
