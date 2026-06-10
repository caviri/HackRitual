"""
Smoke test for the ritual simulator (the Rite of Many Hands).

Runs the whole orchestrated lifecycle end-to-end and asserts the ritual
reached its terminal state, gathered its cast, and that the state-machine
wards refused the operations they should.
"""

import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_full_ritual_runs_to_archived(_create_tables):
    from app.services.ritual_sim import run_ritual

    report = await run_ritual(fresh=True)

    # Walked the full state machine in order.
    assert report.states_visited == ["OPEN", "FROZEN", "FINAL", "ARCHIVED"]
    assert report.final_state == "ARCHIVED"

    # The cast was gathered and a team formed.
    assert report.participants_created >= 3
    assert report.teams_created == 1
    assert report.members_joined >= 1

    # The forge ran: projects proposed, work offered, evidence attached.
    assert report.projects_proposed >= 2
    assert report.submissions_created >= 3
    assert report.files_attached >= 1
    # An autonomous agent submitted over the key-authenticated API.
    assert report.agent_submissions >= 1

    # The admin console reported live metrics during the rite.
    assert report.dashboard_participants >= 1

    # The offerings were weighed: a leaderboard formed and the hand override
    # lifted the sealed offering to the top.
    assert report.leaderboard_entries >= 1
    assert report.scores_overridden >= 1
    assert report.top_score >= 95.0

    # The artefact was drawn — a structured bundle of JSON files.
    assert report.export_files >= 6
    assert report.export_bytes > 0

    # Deterministic wards must have held: leaderboard_mode locked once OPEN, the
    # submission cap, configuration sealed once FROZEN, the backward transition
    # FROZEN→DRAFT, and an offering refused while FROZEN.
    assert report.wards_held >= 4

    # Every transition and config edit was inscribed.
    assert report.audit_entries >= 5


@pytest.mark.asyncio
async def test_ritual_leaves_event_archived(_create_tables, client):
    from app.services.ritual_sim import run_ritual

    await run_ritual(fresh=True)
    resp = await client.get("/api/event")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["state"] == "ARCHIVED"
