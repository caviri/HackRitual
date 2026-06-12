"""Membership seals with the gates, the captaincy can pass, and the
proposal window closes — the state-gating round."""

from __future__ import annotations

import uuid

import pytest


def _set_event(state: str) -> None:
    from datetime import UTC, datetime

    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        ev = db.get(Event, settings.event_id)
        if ev is None:
            ev = Event(
                id=settings.event_id,
                title="Test Event",
                type="hackathon",
                start_at=datetime(2026, 1, 1, tzinfo=UTC),
                end_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
            db.add(ev)
        ev.state = state
        db.commit()


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


def _make_team(captain_user_id: str, *, members: list[str] | None = None):
    """Returns (team_id, invite_code, {user_id: member_row_id})."""
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember

    with SessionLocal() as db:
        team = Participant(
            event_id=settings.event_id,
            type="team",
            display_name=f"gate_{uuid.uuid4().hex[:6]}",
            invite_code=uuid.uuid4().hex[:8].upper(),
            status="active",
        )
        db.add(team)
        db.flush()
        seats: dict[str, str] = {}
        rows = [(captain_user_id, "captain")] + [(u, "member") for u in (members or [])]
        for user_id, role in rows:
            m = ParticipantMember(
                participant_id=team.id, user_id=user_id, role_in_team=role
            )
            db.add(m)
            db.flush()
            seats[user_id] = m.id
        db.commit()
        return team.id, team.invite_code, seats


def _make_agent(owner_user_id: str) -> str:
    import hashlib

    from app.database import SessionLocal
    from app.models.agent import Agent

    with SessionLocal() as db:
        agent = Agent(
            name=f"gatebot_{uuid.uuid4().hex[:6]}",
            owner_user_id=owner_user_id,
            api_key_hash=hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest(),
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent.id


def _make_participant(user_id: str, status: str = "active") -> str:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember

    with SessionLocal() as db:
        p = Participant(
            event_id=settings.event_id,
            type="human",
            display_name=f"gp_{uuid.uuid4().hex[:6]}",
            status=status,
        )
        db.add(p)
        db.flush()
        db.add(
            ParticipantMember(
                participant_id=p.id, user_id=user_id, role_in_team="captain"
            )
        )
        db.commit()
        return p.id


# ============================================================================ #
# Membership seals when the gates close
# ============================================================================ #
@pytest.mark.anyio
async def test_membership_sealed_when_frozen(client):
    captain_id, captain_token = _make_user()
    member_id, member_token = _make_user()
    team_id, invite_code, seats = _make_team(captain_id, members=[member_id])
    agent_id = _make_agent(captain_id)
    joiner_id, joiner_token = _make_user()

    _set_event("FROZEN")

    join = await client.post(
        f"/api/teams/join?invite_code={invite_code}",
        cookies={"session": joiner_token},
    )
    assert join.status_code == 400

    enlist = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": captain_token},
    )
    assert enlist.status_code == 400

    leave = await client.post(
        f"/api/teams/{team_id}/leave", cookies={"session": member_token}
    )
    assert leave.status_code == 400

    remove = await client.delete(
        f"/api/teams/{team_id}/members/{seats[member_id]}",
        cookies={"session": captain_token},
    )
    assert remove.status_code == 400

    # The roster is intact.
    teams = (await client.get("/api/teams")).json()
    team = next(t for t in teams if t["id"] == team_id)
    assert len(team["members"]) == 2

    _set_event("OPEN")


@pytest.mark.anyio
async def test_admin_moderation_works_even_when_sealed(client):
    captain_id, _ = _make_user()
    member_id, _ = _make_user()
    team_id, _, seats = _make_team(captain_id, members=[member_id])
    agent_id = _make_agent(captain_id)
    _, admin_token = _make_user(role="admin")

    _set_event("FROZEN")

    enlist = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": admin_token},
    )
    assert enlist.status_code == 201

    removed = await client.delete(
        f"/api/teams/{team_id}/members/{seats[member_id]}",
        cookies={"session": admin_token},
    )
    assert removed.status_code == 200

    _set_event("OPEN")


# ============================================================================ #
# The captaincy can pass
# ============================================================================ #
@pytest.mark.anyio
async def test_captain_transfers_then_leaves(client):
    _set_event("OPEN")
    captain_id, captain_token = _make_user()
    member_id, _ = _make_user()
    team_id, _, seats = _make_team(captain_id, members=[member_id])

    transferred = await client.post(
        f"/api/teams/{team_id}/captain",
        json={"member_id": seats[member_id]},
        cookies={"session": captain_token},
    )
    assert transferred.status_code == 200, transferred.text

    # The old captain is a plain member now — and may finally leave.
    left = await client.post(
        f"/api/teams/{team_id}/leave", cookies={"session": captain_token}
    )
    assert left.status_code == 200

    from app.database import SessionLocal
    from app.models.participant_member import ParticipantMember

    with SessionLocal() as db:
        rows = (
            db.query(ParticipantMember)
            .filter(ParticipantMember.participant_id == team_id)
            .all()
        )
        assert [(m.user_id, m.role_in_team) for m in rows] == [
            (member_id, "captain")
        ]


@pytest.mark.anyio
async def test_only_the_captain_passes_the_captaincy(client):
    _set_event("OPEN")
    captain_id, _ = _make_user()
    member_id, member_token = _make_user()
    team_id, _, seats = _make_team(captain_id, members=[member_id])

    refused = await client.post(
        f"/api/teams/{team_id}/captain",
        json={"member_id": seats[member_id]},
        cookies={"session": member_token},
    )
    assert refused.status_code == 403


@pytest.mark.anyio
async def test_captaincy_cannot_pass_to_an_agent(client):
    _set_event("OPEN")
    captain_id, captain_token = _make_user()
    team_id, _, _ = _make_team(captain_id)
    agent_id = _make_agent(captain_id)

    enlisted = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": captain_token},
    )
    seat_id = enlisted.json()["member_id"]

    refused = await client.post(
        f"/api/teams/{team_id}/captain",
        json={"member_id": seat_id},
        cookies={"session": captain_token},
    )
    assert refused.status_code == 400


# ============================================================================ #
# Admin add-member respects the requested role
# ============================================================================ #
@pytest.mark.anyio
async def test_admin_add_member_respects_role(client):
    _set_event("OPEN")
    captain_id, _ = _make_user()
    team_id, _, _ = _make_team(captain_id)
    new_user_id, _ = _make_user()
    _, admin_token = _make_user(role="admin")

    resp = await client.post(
        f"/api/admin/teams/{team_id}/members?user_id={new_user_id}&role_in_team=captain",
        cookies={"session": admin_token},
    )
    assert resp.status_code == 200, resp.text

    from app.database import SessionLocal
    from app.models.participant_member import ParticipantMember

    with SessionLocal() as db:
        row = (
            db.query(ParticipantMember)
            .filter(
                ParticipantMember.participant_id == team_id,
                ParticipantMember.user_id == new_user_id,
            )
            .one()
        )
        assert row.role_in_team == "captain"


# ============================================================================ #
# The proposal window
# ============================================================================ #
@pytest.mark.anyio
async def test_proposals_close_when_frozen(client):
    user_id, token = _make_user()
    participant_id = _make_participant(user_id)

    _set_event("FROZEN")
    refused = await client.post(
        "/api/projects",
        json={
            "proposed_by_participant_id": participant_id,
            "title": f"late-{uuid.uuid4().hex[:6]}",
            "description": "x",
        },
        cookies={"session": token},
    )
    assert refused.status_code == 409

    _set_event("OPEN")
    accepted = await client.post(
        "/api/projects",
        json={
            "proposed_by_participant_id": participant_id,
            "title": f"ontime-{uuid.uuid4().hex[:6]}",
            "description": "x",
        },
        cookies={"session": token},
    )
    assert accepted.status_code == 201


@pytest.mark.anyio
async def test_disabled_participant_cannot_propose(client):
    _set_event("OPEN")
    user_id, token = _make_user()
    participant_id = _make_participant(user_id, status="disabled")

    refused = await client.post(
        "/api/projects",
        json={
            "proposed_by_participant_id": participant_id,
            "title": f"ghost-{uuid.uuid4().hex[:6]}",
            "description": "x",
        },
        cookies={"session": token},
    )
    assert refused.status_code == 403
