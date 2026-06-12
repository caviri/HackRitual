"""Project + Submission endpoints."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi import (
    File as FastAPIFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.actor import Actor, get_current_actor
from app.middleware.auth import require_admin
from app.models.file import File as FileModel
from app.models.participant import Participant
from app.models.project import Project
from app.models.submission import Submission
from app.models.user import User
from app.schemas.projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectStatusUpdate,
    SubmissionCreate,
    SubmissionFileResponse,
    SubmissionListResponse,
    SubmissionResponse,
    SubmissionStatusUpdate,
    SubmissionUpdate,
)
from app.services import submissions as submission_rules
from app.services.audit import log_action
from app.services.event import get_event, load_config
from app.services.scoring_service import score_submission
from app.utils.files import delete_upload, get_upload_path, save_upload

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ─── Projects ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    track_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
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
    """Accepts both users and agents as proposers — but only on behalf of a
    participant the actor actually controls (or as the keeper)."""
    participant = db.get(Participant, body.proposed_by_participant_id)
    if not participant:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown participant")
    if not actor.is_admin and participant.id not in submission_rules.participant_ids_for_actor(db, actor):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "you may only propose on behalf of your own participant",
        )
    if participant.status != "active":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "participant is not active"
        )
    # Proposals are accepted while registration is — DRAFT and OPEN. Once the
    # gates close the slate is fixed (admins may still curate).
    if not actor.is_admin:
        event_state = get_event(db).state
        if event_state not in ("DRAFT", "OPEN"):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"proposals are closed in {event_state} state",
            )
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
    db.flush()
    log_action(db, "project.proposed", actor_id=actor_user_id,
               target_type="project", target_id=project.id,
               metadata={"title": project.title})
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
    log_action(db, f"project.{body.status}", actor_id=admin.id,
               target_type="project", target_id=project.id,
               metadata={"title": project.title})
    db.commit()
    db.refresh(project)
    return project


# ─── Submissions (versioned snapshots of work on a project) ──────────────────
# Mounted under the projects router so the URL space stays cohesive.


submissions_router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@submissions_router.get("", response_model=list[SubmissionResponse])
def list_submissions(
    project_id: str | None = Query(None),
    participant_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[Submission]:
    q = db.query(Submission)
    if project_id:
        q = q.filter(Submission.project_id == project_id)
    if participant_id:
        q = q.filter(Submission.participant_id == participant_id)
    return q.order_by(Submission.modified_at.desc()).all()


# Declared before "/{submission_id}" so the literal path wins the match.
@submissions_router.get("/mine", response_model=list[SubmissionResponse])
def list_my_submissions(
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> list[Submission]:
    """All submissions belonging to the current actor's participant(s)."""
    owned = submission_rules.participant_ids_for_actor(db, actor)
    if not owned:
        return []
    return (
        db.query(Submission)
        .filter(Submission.participant_id.in_(owned))
        .order_by(Submission.modified_at.desc())
        .all()
    )


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
    """
    Versioned submission create. Users and agents both call this.

    Gated by the ritual (only OPEN accepts work) and by the per-participant
    submission limit from event config.
    """
    submission_rules.require_open(db)

    participant = db.get(Participant, body.participant_id)
    if participant is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown participant")
    if participant.status != "active":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "participant is not active"
        )

    submission_rules.enforce_submission_limit(db, body.participant_id)

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
    db.flush()

    offered_project = db.get(Project, sub.project_id)
    log_action(db, "submission.offered", actor_id=actor_user_id,
               target_type="submission", target_id=sub.id,
               metadata={"project": offered_project.title if offered_project else None,
                         "version": sub.version})

    # Server-authoritative auto-scoring (Step 08), if enabled for the event.
    if load_config(get_event(db)).get("auto_score"):
        score_submission(db, sub.id)

    from app.services import metrics_service

    metrics_service.increment(db, "submissions_count")
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
    submission_rules.assert_can_act_on(db, actor, sub)
    if sub.status == "final" and body.status != "withdrawn":
        raise HTTPException(status.HTTP_409_CONFLICT, "submission is final")
    previous_status = sub.status
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(sub, field, value)
    if actor.user:
        sub.modified_by_user_id = actor.user.id
    if sub.status == "final" and previous_status != "final":
        log_action(db, "submission.finalised",
                   actor_id=actor.user.id if actor.user else None,
                   target_type="submission", target_id=sub.id,
                   metadata={"title": sub.title, "version": sub.version})
    db.commit()
    db.refresh(sub)
    return sub


@submissions_router.post(
    "/{submission_id}/withdraw", response_model=SubmissionResponse
)
def withdraw_submission(
    submission_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> Submission:
    """Withdraw a submission. Owner only, and only while the event is OPEN."""
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    submission_rules.assert_can_act_on(db, actor, sub)
    # Can only withdraw while work is still being accepted.
    submission_rules.require_open(db)
    sub.status = "withdrawn"
    if actor.user:
        sub.modified_by_user_id = actor.user.id
    log_action(db, "submission.withdrawn",
               actor_id=actor.user.id if actor.user else None,
               target_type="submission", target_id=sub.id,
               metadata={"title": sub.title, "version": sub.version})
    db.commit()
    db.refresh(sub)
    return sub


# ─── Submission files (controlled upload + download) ─────────────────────────
# Files live on disk under UPLOAD_DIR/<event>/<participant>/<submission>/ and are
# never served from the static mount — downloads go through the gated endpoint
# below so ownership can be checked.

ALLOWED_FILE_MIME = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "application/zip",
    "application/json",
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB per file (spec default)


def _original_name(path: str) -> str:
    """Recover the client filename from a stored path (`<uuid>_<name>`)."""
    stored = path.rsplit("/", 1)[-1]
    return stored.split("_", 1)[-1] if "_" in stored else stored


def _file_response(row: FileModel) -> SubmissionFileResponse:
    return SubmissionFileResponse(
        id=row.id,
        submission_id=row.submission_id,
        filename=_original_name(row.path),
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        created_at=row.created_at,
    )


def _require_submission(db: Session, submission_id: str) -> Submission:
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    return sub


@submissions_router.get(
    "/{submission_id}/files", response_model=list[SubmissionFileResponse]
)
def list_submission_files(
    submission_id: str, db: Session = Depends(get_db)
) -> list[SubmissionFileResponse]:
    """File metadata for a submission (public — no blobs, no paths leaked)."""
    _require_submission(db, submission_id)
    rows = (
        db.query(FileModel)
        .filter(FileModel.submission_id == submission_id)
        .order_by(FileModel.created_at)
        .all()
    )
    return [_file_response(r) for r in rows]


@submissions_router.post(
    "/{submission_id}/files",
    response_model=SubmissionFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_submission_file(
    submission_id: str,
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> SubmissionFileResponse:
    """Attach a file to a submission. Owner/admin only, while the event is OPEN."""
    sub = _require_submission(db, submission_id)
    submission_rules.assert_can_act_on(db, actor, sub)
    submission_rules.require_open(db)

    if file.content_type not in ALLOWED_FILE_MIME:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"unsupported type '{file.content_type}'",
        )
    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty file")
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"file exceeds {MAX_FILE_BYTES} bytes",
        )

    meta = save_upload(
        raw,
        file.filename or "file",
        file.content_type,
        sub.id,
        sub.participant_id,
        sub.event_id,
    )
    row = FileModel(
        id=meta["id"],
        submission_id=sub.id,
        path=meta["path"],
        mime_type=meta["mime_type"],
        size_bytes=meta["size_bytes"],
        sha256=meta["sha256"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _file_response(row)


@submissions_router.get("/{submission_id}/files/{file_id}")
def download_submission_file(
    submission_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> FileResponse:
    """Stream a file. Controlled — owner or admin only, never the static mount."""
    sub = _require_submission(db, submission_id)
    submission_rules.assert_can_act_on(db, actor, sub)
    row = db.get(FileModel, file_id)
    if not row or row.submission_id != submission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
    abs_path = get_upload_path(row.path)
    if not abs_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file missing from storage")
    return FileResponse(
        str(abs_path),
        media_type=row.mime_type,
        filename=_original_name(row.path),
    )


@submissions_router.delete(
    "/{submission_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_submission_file(
    submission_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> None:
    """Remove an attached file. Owner/admin only, while the event is OPEN."""
    sub = _require_submission(db, submission_id)
    submission_rules.assert_can_act_on(db, actor, sub)
    submission_rules.require_open(db)
    row = db.get(FileModel, file_id)
    if not row or row.submission_id != submission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
    delete_upload(row.path)
    db.delete(row)
    db.commit()


# ─── Admin submission management ─────────────────────────────────────────────

admin_submissions_router = APIRouter(
    prefix="/api/admin/submissions", tags=["submissions"]
)


@admin_submissions_router.get("", response_model=SubmissionListResponse)
def admin_list_submissions(
    participant_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SubmissionListResponse:
    q = db.query(Submission)
    if participant_id:
        q = q.filter(Submission.participant_id == participant_id)
    if status_filter:
        q = q.filter(Submission.status == status_filter)
    total = q.count()
    rows = (
        q.order_by(Submission.modified_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    pages = (total + per_page - 1) // per_page
    return SubmissionListResponse(
        submissions=[SubmissionResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@admin_submissions_router.get("/{submission_id}", response_model=SubmissionResponse)
def admin_get_submission(
    submission_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Submission:
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    return sub


@admin_submissions_router.patch(
    "/{submission_id}/status", response_model=SubmissionResponse
)
def admin_update_submission_status(
    submission_id: str,
    body: SubmissionStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Submission:
    """Admin moderation — change status (e.g. disqualify) with an audit trail."""
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    previous = sub.status
    sub.status = body.status
    sub.modified_by_user_id = admin.id
    log_action(
        db,
        "submission.status_changed",
        actor_id=admin.id,
        target_type="submission",
        target_id=sub.id,
        metadata={"from": previous, "to": body.status, "reason": body.reason},
    )
    db.commit()
    db.refresh(sub)
    return sub
