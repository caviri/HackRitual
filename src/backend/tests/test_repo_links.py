"""Repository-link authorization — only the project's people may modify."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest


def _make_user(role: str = "user"):
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"{role}_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id, create_jwt(user)


def _make_project_with_owner(owner_user_id: str):
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.models.project import Project

    with SessionLocal() as db:
        participant = Participant(
            event_id=settings.event_id,
            type="human",
            display_name=f"owner_{uuid.uuid4().hex[:6]}",
            status="active",
        )
        db.add(participant)
        db.flush()
        db.add(
            ParticipantMember(
                participant_id=participant.id,
                user_id=owner_user_id,
                role_in_team="captain",
            )
        )
        project = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=participant.id,
            title=f"repo-guard-{uuid.uuid4().hex[:6]}",
            description="x",
            status="approved",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project.id


_REPO_URL = "https://github.com/example/garden"


@pytest.mark.anyio
async def test_stranger_cannot_attach_repo(client):
    owner_id, _ = _make_user()
    project_id = _make_project_with_owner(owner_id)
    _, stranger_token = _make_user()

    resp = await client.post(
        f"/api/projects/{project_id}/repos",
        json={"url": _REPO_URL},
        cookies={"session": stranger_token},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_member_can_attach_and_detach(client):
    owner_id, owner_token = _make_user()
    project_id = _make_project_with_owner(owner_id)

    with patch("app.routers.repos.repo_service.fetch_github", new=AsyncMock()):
        created = await client.post(
            f"/api/projects/{project_id}/repos",
            json={"url": _REPO_URL},
            cookies={"session": owner_token},
        )
    assert created.status_code == 201, created.text
    repo_id = created.json()["id"]

    _, stranger_token = _make_user()
    forbidden = await client.delete(
        f"/api/projects/{project_id}/repos/{repo_id}",
        cookies={"session": stranger_token},
    )
    assert forbidden.status_code == 403

    gone = await client.delete(
        f"/api/projects/{project_id}/repos/{repo_id}",
        cookies={"session": owner_token},
    )
    assert gone.status_code == 204


@pytest.mark.anyio
async def test_admin_can_attach_anywhere(client):
    owner_id, _ = _make_user()
    project_id = _make_project_with_owner(owner_id)
    _, admin_token = _make_user(role="admin")

    with patch("app.routers.repos.repo_service.fetch_github", new=AsyncMock()):
        resp = await client.post(
            f"/api/projects/{project_id}/repos",
            json={"url": "https://github.com/example/keeper-repo"},
            cookies={"session": admin_token},
        )
    assert resp.status_code == 201


@pytest.mark.anyio
async def test_anonymous_cannot_attach(client):
    owner_id, _ = _make_user()
    project_id = _make_project_with_owner(owner_id)
    resp = await client.post(
        f"/api/projects/{project_id}/repos", json={"url": _REPO_URL}
    )
    assert resp.status_code == 401
