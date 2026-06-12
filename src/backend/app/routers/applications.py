"""
Application endpoints — the petition desk.

Public:
  POST /api/applications                      file an application (anonymous)

Admin:
  GET  /api/admin/applications                list, filterable by status
  POST /api/admin/applications/{id}/approve   create user + access password
  POST /api/admin/applications/{id}/reject    decline
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.application import Application
from app.models.user import User
from app.schemas.applications import (
    ApplicationCreate,
    ApplicationCreatedResponse,
    ApplicationListResponse,
    ApplicationOut,
    ApplicationUserOut,
)
from app.services import applications as app_svc

logger = logging.getLogger(__name__)

public_router = APIRouter(prefix="/api/applications", tags=["applications"])
admin_router = APIRouter(prefix="/api/admin/applications", tags=["applications"])

_VALID_STATUSES = ("pending", "approved", "rejected")


def _to_out(application: Application, db: Session) -> ApplicationOut:
    user = None
    if application.user_id:
        u = db.get(User, application.user_id)
        if u:
            user = ApplicationUserOut.model_validate(u)
    return ApplicationOut(
        id=application.id,
        name=application.name,
        email=application.email,
        team=application.team,
        project_interest=application.project_interest,
        status=application.status,
        source=application.source,
        user_id=application.user_id,
        created_at=application.created_at,
        decided_at=application.decided_at,
        user=user,
    )


# ------------------------------------------------------------------ #
# Public — file an application
# ------------------------------------------------------------------ #

@public_router.post(
    "", response_model=ApplicationCreatedResponse, status_code=status.HTTP_201_CREATED
)
def submit_application(
    body: ApplicationCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ApplicationCreatedResponse:
    """File a request to join the event. The organizers review it by hand;
    if approved, your access key arrives from them directly."""
    try:
        application = app_svc.create_application(
            db,
            name=body.name,
            email=body.email,
            team=body.team,
            project_interest=body.project_interest,
        )
    except app_svc.ApplicationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    from app.services.audit import log_action

    log_action(db, "application.received", target_type="application",
               target_id=application.id, metadata={"name": application.name})
    db.commit()
    return ApplicationCreatedResponse(id=application.id, status=application.status)


# ------------------------------------------------------------------ #
# Admin — review queue
# ------------------------------------------------------------------ #

@admin_router.get("", response_model=ApplicationListResponse)
def list_applications(
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> ApplicationListResponse:
    if status_filter and status_filter not in _VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {_VALID_STATUSES}",
        )

    q = db.query(Application)
    if status_filter:
        q = q.filter(Application.status == status_filter)
    rows = q.order_by(Application.created_at.desc()).all()

    counts = {s: 0 for s in _VALID_STATUSES}
    for s, n in (
        db.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    ):
        counts[s] = n

    return ApplicationListResponse(
        applications=[_to_out(a, db) for a in rows],
        total=len(rows),
        counts=counts,
    )


def _get_application_or_404(application_id: str, db: Session) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@admin_router.post("/{application_id}/approve", response_model=ApplicationOut)
def approve(
    application_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> ApplicationOut:
    """Approve: mints the User and its access password. The response carries
    the password so the panel can offer copy/mailto immediately."""
    application = _get_application_or_404(application_id, db)
    try:
        app_svc.approve_application(db, application, decided_by=admin.id)
    except app_svc.ApplicationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.commit()
    db.refresh(application)
    return _to_out(application, db)


@admin_router.post("/{application_id}/reject", response_model=ApplicationOut)
def reject(
    application_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> ApplicationOut:
    application = _get_application_or_404(application_id, db)
    try:
        app_svc.reject_application(db, application, decided_by=admin.id)
    except app_svc.ApplicationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.commit()
    db.refresh(application)
    return _to_out(application, db)
