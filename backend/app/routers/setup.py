"""
One-time admin setup endpoint.

POST /api/setup — accepts ADMIN_SETUP_TOKEN + email, creates first admin.
Returns 410 Gone once any admin exists.
Only available when ADMIN_SETUP_TOKEN is configured.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import UserOut
from app.schemas.users import SetupInput
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(tags=["setup"])


@router.post("/api/setup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def setup(data: SetupInput, db: Session = Depends(get_db)) -> UserOut:
    """
    Create the first admin via setup token.

    Becomes unavailable (410) as soon as any admin user exists.
    Disabled entirely when ADMIN_SETUP_TOKEN is not configured.
    """
    from app.config import settings
    from app.models.user import User

    if not settings.admin_setup_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Seal the gate once any admin exists
    admin_exists = db.query(User).filter_by(role="admin").first() is not None
    if admin_exists:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Setup already complete. An admin already exists.",
        )

    if data.token != settings.admin_setup_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid setup token")

    email = data.email.strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if user is None:
        user = User(email=email, role="admin")
        db.add(user)
    else:
        user.role = "admin"

    log_action(db, "user.admin_seeded", target_type="user", target_id=user.id,
               metadata={"method": "setup_token"})
    db.commit()
    db.refresh(user)

    logger.info("First admin created via setup token", extra={"email": email})
    return UserOut.model_validate(user)
