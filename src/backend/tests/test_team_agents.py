"""Agents as team members — enlistment authorization, roster rendering,
and what an enlisted agent's credential may act on."""

from __future__ import annotations

import hashlib
import uuid

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


def _make_team(captain_user_id: str) -> str:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember

    with SessionLocal() as db:
        team = Participant(
            event_id=settings.event_id,
            type="team",
            display_name=f"circle_{uuid.uuid4().hex[:6]}",
            status="active",
        )
        db.add(team)
        db.flush()
        db.add(
            ParticipantMember(
                participant_id=team.id,
                user_id=captain_user_id,
                role_in_team="captain",
            )
        )
        db.commit()
        db.refresh(team)
        return team.id


def _make_agent(owner_user_id: str | None, status: str = "active"):
    """Returns (agent_id, agent_name, plaintext_api_key)."""
    from app.database import SessionLocal
    from app.models.agent import Agent

    key = f"ak_test_{uuid.uuid4().hex}"
    with SessionLocal() as db:
        agent = Agent(
            name=f"familiar_{uuid.uuid4().hex[:6]}",
            owner_user_id=owner_user_id,
            api_key_hash=hashlib.sha256(key.encode()).hexdigest(),
            status=status,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent.id, agent.name, key


@pytest.mark.anyio
async def test_captain_enlists_own_agent_and_roster_shows_it(client):
    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, agent_name, _ = _make_agent(owner_id)

    resp = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )
    assert resp.status_code == 201, resp.text

    # Public roster carries the agent by name, marked as an agent.
    teams = (await client.get("/api/teams")).json()
    team = next(t for t in teams if t["id"] == team_id)
    agent_members = [m for m in team["members"] if m["kind"] == "agent"]
    assert agent_members == [
        {"display_name": agent_name, "role_in_team": "agent", "kind": "agent"}
    ]
    humans = [m for m in team["members"] if m["kind"] == "human"]
    assert len(humans) == 1


@pytest.mark.anyio
async def test_stranger_cannot_enlist(client):
    owner_id, _ = _make_user()
    team_id = _make_team(owner_id)
    stranger_id, stranger_token = _make_user()
    agent_id, _, _ = _make_agent(stranger_id)

    resp = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": stranger_token},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_member_cannot_enlist_an_agent_they_do_not_own(client):
    captain_id, captain_token = _make_user()
    team_id = _make_team(captain_id)
    other_id, _ = _make_user()
    agent_id, _, _ = _make_agent(other_id)

    resp = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": captain_token},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_can_enlist_any_agent(client):
    owner_id, _ = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, _ = _make_agent(owner_id)
    _, admin_token = _make_user(role="admin")

    resp = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": admin_token},
    )
    assert resp.status_code == 201


@pytest.mark.anyio
async def test_duplicate_enlist_rejected(client):
    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, _ = _make_agent(owner_id)

    first = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )
    assert first.status_code == 201
    second = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )
    assert second.status_code == 400


@pytest.mark.anyio
async def test_revoked_agent_cannot_join(client):
    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, _ = _make_agent(owner_id, status="revoked")

    resp = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_enlisted_agent_may_act_for_the_team(client):
    """The credential's ownership map covers the team after enlistment."""
    from app.database import SessionLocal
    from app.middleware.actor import Actor
    from app.models.agent import Agent
    from app.services.submissions import participant_ids_for_actor

    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, _ = _make_agent(owner_id)

    with SessionLocal() as db:
        agent = db.get(Agent, agent_id)
        before = participant_ids_for_actor(db, Actor(agent=agent))
    assert team_id not in before

    resp = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )
    assert resp.status_code == 201

    with SessionLocal() as db:
        agent = db.get(Agent, agent_id)
        after = participant_ids_for_actor(db, Actor(agent=agent))
    assert team_id in after


@pytest.mark.anyio
async def test_team_membership_does_not_shadow_the_agents_own_identity(client):
    """agent_participant must keep resolving the solo `agent` participant,
    not the team the agent was enlisted into."""
    from app.database import SessionLocal
    from app.models.agent import Agent
    from app.services.agents import agent_participant, link_agent_participant

    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, _ = _make_agent(owner_id)

    with SessionLocal() as db:
        agent = db.get(Agent, agent_id)
        solo = link_agent_participant(db, agent)
        db.commit()
        solo_id = solo.id

    resp = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )
    assert resp.status_code == 201

    with SessionLocal() as db:
        agent = db.get(Agent, agent_id)
        resolved = agent_participant(db, agent)
        assert resolved is not None
        assert resolved.id == solo_id
        assert resolved.type == "agent"


@pytest.mark.anyio
async def test_agent_detail_lists_its_team(client):
    """The agent participant's public detail names the team it serves on."""
    from app.database import SessionLocal
    from app.models.agent import Agent
    from app.services.agents import link_agent_participant

    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, _ = _make_agent(owner_id)

    with SessionLocal() as db:
        agent = db.get(Agent, agent_id)
        solo_id = link_agent_participant(db, agent).id
        db.commit()

    await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )

    detail = (await client.get(f"/api/participants/{solo_id}")).json()
    assert [t["id"] for t in detail["teams"]] == [team_id]
    assert detail["teams"][0]["role_in_team"] == "agent"


@pytest.mark.anyio
async def test_deleting_an_agent_clears_its_seats(client):
    """Hard-deleting an agent must not leave junk membership rows or a ghost
    participant on the public roster."""
    from app.database import SessionLocal
    from app.models.agent import Agent
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.services.agents import link_agent_participant

    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, _ = _make_agent(owner_id)

    with SessionLocal() as db:
        agent = db.get(Agent, agent_id)
        solo_id = link_agent_participant(db, agent).id
        db.commit()

    await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )

    deleted = await client.delete(
        f"/api/agents/{agent_id}", cookies={"session": owner_token}
    )
    assert deleted.status_code == 204

    with SessionLocal() as db:
        leftover = (
            db.query(ParticipantMember)
            .filter(ParticipantMember.agent_id == agent_id)
            .count()
        )
        assert leftover == 0
        # No NULL-NULL junk rows on the team either.
        junk = (
            db.query(ParticipantMember)
            .filter(
                ParticipantMember.participant_id == team_id,
                ParticipantMember.user_id.is_(None),
                ParticipantMember.agent_id.is_(None),
            )
            .count()
        )
        assert junk == 0
        assert db.get(Participant, solo_id).status == "disabled"

    teams = (await client.get("/api/teams")).json()
    team = next(t for t in teams if t["id"] == team_id)
    assert [m for m in team["members"] if m["kind"] == "agent"] == []


@pytest.mark.anyio
async def test_agent_sees_its_team_submission_status(client):
    """A submission made on the team's behalf is visible through the
    agent-key status endpoint."""
    from app.config import settings
    from app.database import SessionLocal
    from app.models.project import Project
    from app.models.submission import Submission

    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, key = _make_agent(owner_id)

    resp = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )
    assert resp.status_code == 201

    with SessionLocal() as db:
        project = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=team_id,
            title=f"loom-{uuid.uuid4().hex[:6]}",
            description="x",
            status="approved",
        )
        db.add(project)
        db.flush()
        sub = Submission(
            event_id=settings.event_id,
            project_id=project.id,
            participant_id=team_id,
            version=1,
            title="v1",
            status="draft",
        )
        db.add(sub)
        db.commit()
        sub_id = sub.id

    seen = await client.get(
        f"/api/agent/submissions/{sub_id}", headers={"X-API-Key": key}
    )
    assert seen.status_code == 200
    assert seen.json()["participant_id"] == team_id

    # A different agent's key still gets a 404, not a leak.
    _, _, other_key = _make_agent(owner_id)
    hidden = await client.get(
        f"/api/agent/submissions/{sub_id}", headers={"X-API-Key": other_key}
    )
    assert hidden.status_code == 404


@pytest.mark.anyio
async def test_owner_can_remove_their_own_agents_seat(client):
    """A non-captain member who owns the agent may pull it from the roster;
    an unrelated member may not."""
    from app.database import SessionLocal
    from app.models.participant_member import ParticipantMember

    captain_id, _ = _make_user()
    team_id = _make_team(captain_id)
    member_id_user, member_token = _make_user()
    other_member_id, other_member_token = _make_user()
    with SessionLocal() as db:
        db.add(
            ParticipantMember(
                participant_id=team_id,
                user_id=member_id_user,
                role_in_team="member",
            )
        )
        db.add(
            ParticipantMember(
                participant_id=team_id,
                user_id=other_member_id,
                role_in_team="member",
            )
        )
        db.commit()

    agent_id, _, _ = _make_agent(member_id_user)
    enlisted = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": member_token},
    )
    assert enlisted.status_code == 201
    seat_id = enlisted.json()["member_id"]

    # A fellow member who does not own the agent is refused.
    forbidden = await client.delete(
        f"/api/teams/{team_id}/members/{seat_id}",
        cookies={"session": other_member_token},
    )
    assert forbidden.status_code == 403

    # The owner may pull their own agent without being captain.
    removed = await client.delete(
        f"/api/teams/{team_id}/members/{seat_id}",
        cookies={"session": member_token},
    )
    assert removed.status_code == 200


@pytest.mark.anyio
async def test_captain_can_remove_agent_member(client):
    owner_id, owner_token = _make_user()
    team_id = _make_team(owner_id)
    agent_id, _, _ = _make_agent(owner_id)

    enlisted = await client.post(
        f"/api/teams/{team_id}/agents",
        json={"agent_id": agent_id},
        cookies={"session": owner_token},
    )
    member_id = enlisted.json()["member_id"]

    removed = await client.delete(
        f"/api/teams/{team_id}/members/{member_id}",
        cookies={"session": owner_token},
    )
    assert removed.status_code == 200

    teams = (await client.get("/api/teams")).json()
    team = next(t for t in teams if t["id"] == team_id)
    assert [m for m in team["members"] if m["kind"] == "agent"] == []
