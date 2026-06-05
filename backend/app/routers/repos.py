"""Repository endpoints — link, refresh, unlink."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.actor import Actor, get_current_actor
from app.models.project import Project
from app.models.repository import RepoCommit, Repository
from app.schemas.repos import (
    CommitResponse,
    RepoAttachRequest,
    RepositoryResponse,
)
from app.services import repos as repo_service


router = APIRouter(prefix="/api/projects", tags=["repositories"])


def _commit_to_response(c: RepoCommit) -> CommitResponse:
    msg = c.message or ""
    return CommitResponse(
        sha=c.sha,
        sha_short=c.sha[:7],
        branch=c.branch,
        message=msg,
        message_first_line=msg.split("\n", 1)[0][:140],
        author_name=c.author_name,
        author_login=c.author_login,
        author_avatar_url=c.author_avatar_url,
        author_profile_url=c.author_profile_url,
        committed_at=c.committed_at,
    )


def _repo_to_response(repo: Repository, db: Session) -> RepositoryResponse:
    commits = (
        db.query(RepoCommit)
        .filter(RepoCommit.repository_id == repo.id)
        .order_by(RepoCommit.committed_at.desc())
        .limit(20)
        .all()
    )
    return RepositoryResponse(
        id=repo.id,
        project_id=repo.project_id,
        url=repo.url,
        host=repo.host,
        owner=repo.owner,
        repo=repo.repo,
        label=repo.label,
        default_branch=repo.default_branch,
        description=repo.description,
        stars=repo.stars,
        last_pushed_at=repo.last_pushed_at,
        last_polled_at=repo.last_polled_at,
        polling_error=repo.polling_error,
        commits=[_commit_to_response(c) for c in commits],
    )


@router.get("/{project_id}/repos", response_model=list[RepositoryResponse])
async def list_project_repos(
    project_id: str,
    db: Session = Depends(get_db),
) -> list[RepositoryResponse]:
    """List a project's linked repositories with cached commits.

    Auto-refreshes any repo whose data is older than the TTL.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")

    repos = (
        db.query(Repository)
        .filter(Repository.project_id == project_id)
        .order_by(Repository.created_at)
        .all()
    )
    for repo in repos:
        await repo_service.refresh_if_stale(repo, db)
        db.refresh(repo)
    return [_repo_to_response(r, db) for r in repos]


@router.post(
    "/{project_id}/repos",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_repo(
    project_id: str,
    body: RepoAttachRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> RepositoryResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")

    parsed = repo_service.parse_url(body.url)
    if not parsed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "unrecognised repository URL (only GitHub supported for now)",
        )
    host, owner, repo_name = parsed
    url = repo_service.normalize_url(host, owner, repo_name)

    repo = Repository(
        project_id=project_id,
        url=url,
        host=host,
        owner=owner,
        repo=repo_name,
        label=body.label,
    )
    db.add(repo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "this repository is already linked to the project",
        )
    db.refresh(repo)

    # Initial fetch — failures are stored on the row, not raised.
    await repo_service.fetch_github(repo, db)
    db.refresh(repo)
    return _repo_to_response(repo, db)


@router.post("/{project_id}/repos/{repo_id}/refresh", response_model=RepositoryResponse)
async def refresh_repo(
    project_id: str,
    repo_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> RepositoryResponse:
    repo = db.get(Repository, repo_id)
    if not repo or repo.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "repository not found")
    await repo_service.fetch_github(repo, db)
    db.refresh(repo)
    return _repo_to_response(repo, db)


@router.delete(
    "/{project_id}/repos/{repo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def detach_repo(
    project_id: str,
    repo_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> None:
    repo = db.get(Repository, repo_id)
    if not repo or repo.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "repository not found")
    db.delete(repo)
    db.commit()


# ── feed endpoint: aggregated commits across participant/team's projects ────


feed_router = APIRouter(prefix="/api/feed", tags=["repositories"])


@feed_router.get("/participant/{participant_id}", response_model=list[CommitResponse])
async def participant_feed(
    participant_id: str,
    db: Session = Depends(get_db),
) -> list[CommitResponse]:
    """Recent commits across every project the participant has proposed.

    Trigger a refresh on stale repos along the way so the feed reflects
    near-current activity (within the TTL window).
    """
    projects = (
        db.query(Project)
        .filter(Project.proposed_by_participant_id == participant_id)
        .all()
    )
    if not projects:
        return []
    project_ids = [p.id for p in projects]
    repos = (
        db.query(Repository)
        .filter(Repository.project_id.in_(project_ids))
        .all()
    )
    for repo in repos:
        await repo_service.refresh_if_stale(repo, db)
    repo_ids = [r.id for r in repos]
    if not repo_ids:
        return []
    commits = (
        db.query(RepoCommit)
        .filter(RepoCommit.repository_id.in_(repo_ids))
        .order_by(RepoCommit.committed_at.desc())
        .limit(30)
        .all()
    )
    return [_commit_to_response(c) for c in commits]
