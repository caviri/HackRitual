"""
Admin user management endpoints.

GET    /api/admin/users            — list all users (paginated, filterable)
GET    /api/admin/users/{id}       — get single user
PATCH  /api/admin/users/{id}/role  — change role
DELETE /api/admin/users/{id}       — deactivate (soft-delete)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.middleware.auth import require_admin
from app.schemas.users import UpdateRoleInput, UserDetail, UserListResponse, VALID_ROLES
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/users", tags=["admin"])


def _get_user_or_404(user_id: str, db: Session):
    from app.models.user import User
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _active_admin_count(db: Session) -> int:
    from app.models.user import User
    return db.query(User).filter(User.role == "admin", User.status == "active").count()


# ------------------------------------------------------------------ #
# GET /api/admin/users
# ------------------------------------------------------------------ #

@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> UserListResponse:
    from app.models.user import User

    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if search:
        q = q.filter(User.email.ilike(f"%{search}%"))

    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    # Explicitly access all attributes while session is open to avoid lazy-loading issues
    user_data = [
        UserDetail(
            id=u.id,
            email=u.email,
            role=u.role,
            status=u.status,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]

    return UserListResponse(
        users=user_data,
        total=total,
        page=page,
        per_page=per_page,
    )


# ------------------------------------------------------------------ #
# GET /api/admin/users/{user_id}
# ------------------------------------------------------------------ #

@router.get("/{user_id}", response_model=UserDetail)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> UserDetail:
    user = _get_user_or_404(user_id, db)
    # Explicitly access all attributes while session is open
    return UserDetail(
        id=user.id,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


# ------------------------------------------------------------------ #
# PATCH /api/admin/users/{user_id}/role
# ------------------------------------------------------------------ #

@router.patch("/{user_id}/role", response_model=UserDetail)
def update_role(
    user_id: str,
    data: UpdateRoleInput,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> UserDetail:
    if data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {sorted(VALID_ROLES)}",
        )

    user = _get_user_or_404(user_id, db)

    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change your own role")

    if user.role == "admin" and data.role != "admin" and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot demote the last admin")

    old_role = user.role
    user.role = data.role
    log_action(db, "user.role_changed", actor_id=admin.id, target_type="user", target_id=user.id,
               metadata={"old_role": old_role, "new_role": data.role})
    db.commit()
    db.refresh(user)
    # Explicitly access all attributes while session is open
    return UserDetail(
        id=user.id,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


# ------------------------------------------------------------------ #
# DELETE /api/admin/users/{user_id}
# ------------------------------------------------------------------ #

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> None:
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot deactivate yourself")

    user = _get_user_or_404(user_id, db)

    if user.status == "inactive":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already inactive")

    if user.role == "admin" and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot deactivate the last admin")

    user.status = "inactive"
    log_action(db, "user.deactivated", actor_id=admin.id, target_type="user", target_id=user.id)
    db.commit()
    # Participant cascade added in Step 05
