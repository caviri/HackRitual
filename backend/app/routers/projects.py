"""Project + Submission endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.actor import Actor, get_current_actor
from app.middleware.auth import require_admin
from app.models.participant import Participant
from app.models.project import Project
from app.models.submission import Submission
from app.models.user import User
from app.schemas.projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectStatusUpdate,
    SubmissionCreate,
    SubmissionResponse,
    SubmissionUpdate,
)


router = APIRouter(prefix="/api/projects", tags=["projects"])


# ─── Projects ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    track_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> list[Project]:
    q = db.query(Project)
    if track_id:
        q = q.filter(Project.track_id == track_id)
    if status_filter:
        q = q.filter(Project.status == status_filter)
    return q.order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> Project:
    """Accepts both users and agents as proposers. The participant being
    proposed-for must exist; finer-grained ownership checks come later."""
    participant = db.get(Participant, body.proposed_by_participant_id)
    if not participant:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown participant")
    # created_by_user_id only meaningful for users; for agents, leave null and
    # rely on participant linkage to attribute provenance.
    actor_user_id = actor.user.id if actor.user else None
    project = Project(
        event_id=settings.event_id,
        track_id=body.track_id,
        proposed_by_participant_id=body.proposed_by_participant_id,
        title=body.title,
        description=body.description,
        image=body.image,
        status="proposed",
        created_by_user_id=actor_user_id,
        modified_by_user_id=actor_user_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}/status", response_model=ProjectResponse)
def update_project_status(
    project_id: str,
    body: ProjectStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    project.status = body.status
    project.modified_by_user_id = admin.id
    db.commit()
    db.refresh(project)
    return project


# ─── Submissions (versioned snapshots of work on a project) ──────────────────
# Mounted under the projects router so the URL space stays cohesive.


submissions_router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@submissions_router.get("", response_model=list[SubmissionResponse])
def list_submissions(
    project_id: Optional[str] = Query(None),
    participant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> list[Submission]:
    q = db.query(Submission)
    if project_id:
        q = q.filter(Submission.project_id == project_id)
    if participant_id:
        q = q.filter(Submission.participant_id == participant_id)
    return q.order_by(Submission.modified_at.desc()).all()


@submissions_router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(submission_id: str, db: Session = Depends(get_db)) -> Submission:
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    return sub


@submissions_router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    body: SubmissionCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> Submission:
    """Versioned submission create. Users and agents both call this."""
    existing_max = (
        db.query(func.coalesce(func.max(Submission.version), 0))
        .filter(
            Submission.project_id == body.project_id,
            Submission.participant_id == body.participant_id,
        )
        .scalar()
    )
    actor_user_id = actor.user.id if actor.user else None
    sub = Submission(
        event_id=settings.event_id,
        project_id=body.project_id,
        participant_id=body.participant_id,
        version=(existing_max or 0) + 1,
        title=body.title,
        description=body.description,
        result=body.result,
        payload_json=body.payload_json,
        status="draft",
        created_by_user_id=actor_user_id,
        modified_by_user_id=actor_user_id,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@submissions_router.patch("/{submission_id}", response_model=SubmissionResponse)
def update_submission(
    submission_id: str,
    body: SubmissionUpdate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> Submission:
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    if sub.status == "final" and body.status != "withdrawn":
        raise HTTPException(status.HTTP_409_CONFLICT, "submission is final")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(sub, field, value)
    if actor.user:
        sub.modified_by_user_id = actor.user.id
    db.commit()
    db.refresh(sub)
    return sub
