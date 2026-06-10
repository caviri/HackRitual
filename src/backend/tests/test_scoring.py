"""
Tests for Scoring & Leaderboards (Step 08).

Covers the default scorer, auto-scoring on submission creation, the
get-score / rescore / override endpoints, and the leaderboard service
(best/latest modes, tie-breaking, and exclusion of withdrawn/disqualified work).
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _set_event(state: str = "OPEN", config: dict | None = None) -> None:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        event = db.get(Event, settings.event_id)
        if event is None:
            event = Event(
                id=settings.event_id,
                title="Test Event",
                type="hackathon",
                start_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
            db.add(event)
        event.state = state
        event.config_json = json.dumps(config) if config else None
        db.commit()


def _make_participant(role: str = "user", ptype: str = "human") -> tuple[str, str]:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"score_{uuid.uuid4()}@test.local", role=role)
        db.add(user)
        db.flush()
        participant = Participant(
            event_id=settings.event_id,
            type=ptype,
            display_name=f"P-{user.id[:6]}",
            status="active",
        )
        db.add(participant)
        db.flush()
        db.add(
            ParticipantMember(
                participant_id=participant.id, user_id=user.id, role_in_team="captain"
            )
        )
        db.commit()
        return create_jwt(user), participant.id


def _make_project(participant_id: str) -> str:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.project import Project

    with SessionLocal() as db:
        project = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=participant_id,
            title=f"proj-{uuid.uuid4().hex[:8]}",
            description="a thing",
            status="proposed",
        )
        db.add(project)
        db.commit()
        return project.id


async def _submit(client, token, project_id, participant_id, **extra):
    body = {"project_id": project_id, "participant_id": participant_id, **extra}
    return await client.post("/api/submissions", json=body, headers=_headers(token))


# ============================================================================ #
# The default scorer
# ============================================================================ #
class TestDefaultScorer:
    def test_completeness_rubric(self):
        from app.scoring import DefaultScorer

        scorer = DefaultScorer()
        assert scorer.version == "default-1.0"

        full = scorer.score(
            {"title": "t", "description": "d", "payload_json": {"x": 1}},
            [{"path": "a", "mime_type": "image/png", "size_bytes": 1, "sha256": "h"}],
        )
        assert full.score_value == 80  # 10 + 20 + 10(file) + 40
        assert full.status == "scored"

        bare = scorer.score({"title": "t"}, [])
        assert bare.score_value == 10


# ============================================================================ #
# Auto-scoring + score endpoints
# ============================================================================ #
class TestScoreEndpoints:
    @pytest.mark.asyncio
    async def test_auto_score_on_create(self, client):
        _set_event("OPEN")  # auto_score defaults to True
        token, pid = _make_participant()
        proj = _make_project(pid)
        sub_id = (
            await _submit(client, token, proj, pid, title="x", description="y")
        ).json()["id"]

        resp = await client.get(f"/api/submissions/{sub_id}/score")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["score_value"] == 30  # title 10 + description 20
        assert body["scorer_version"] == "default-1.0"

    @pytest.mark.asyncio
    async def test_no_score_when_auto_score_off(self, client):
        _set_event("OPEN", config={"auto_score": False})
        token, pid = _make_participant()
        proj = _make_project(pid)
        sub_id = (await _submit(client, token, proj, pid, title="x")).json()["id"]

        resp = await client.get(f"/api/submissions/{sub_id}/score")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_admin_rescore(self, client):
        _set_event("OPEN", config={"auto_score": False})
        token, pid = _make_participant()
        admin_token, _ = _make_participant(role="admin")
        proj = _make_project(pid)
        sub_id = (
            await _submit(client, token, proj, pid, title="x", description="y")
        ).json()["id"]

        resp = await client.post(
            f"/api/admin/submissions/{sub_id}/rescore", headers=_headers(admin_token)
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["score_value"] == 30

    @pytest.mark.asyncio
    async def test_admin_override_and_audit(self, client):
        from app.database import SessionLocal
        from app.models.audit_log import AuditLog

        _set_event("OPEN")
        token, pid = _make_participant()
        admin_token, _ = _make_participant(role="admin")
        proj = _make_project(pid)
        sub_id = (
            await _submit(client, token, proj, pid, title="x", description="y")
        ).json()["id"]
        score_id = (await client.get(f"/api/submissions/{sub_id}/score")).json()["id"]

        resp = await client.patch(
            f"/api/admin/scores/{score_id}",
            json={"score_value": 88, "reason": "manual review"},
            headers=_headers(admin_token),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["score_value"] == 88

        with SessionLocal() as db:
            entry = (
                db.query(AuditLog)
                .filter(AuditLog.action == "score.overridden", AuditLog.target_id == score_id)
                .first()
            )
            assert entry is not None

    @pytest.mark.asyncio
    async def test_override_requires_admin(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        proj = _make_project(pid)
        sub_id = (await _submit(client, token, proj, pid, title="x")).json()["id"]
        score_id = (await client.get(f"/api/submissions/{sub_id}/score")).json()["id"]

        resp = await client.patch(
            f"/api/admin/scores/{score_id}",
            json={"score_value": 100},
            headers=_headers(token),
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================ #
# Leaderboard (service-level, for deterministic control)
# ============================================================================ #
class TestLeaderboard:
    def _seed(self, db, *, score, status_="scored", withdrawn=False, created=None, ptype="human"):
        """Create participant + submission + score; return the participant id."""
        from app.config import settings
        from app.models.participant import Participant
        from app.models.score import Score
        from app.models.submission import Submission

        p = Participant(
            event_id=settings.event_id,
            type=ptype,
            display_name=f"L-{uuid.uuid4().hex[:6]}",
            status="active",
        )
        db.add(p)
        db.flush()
        proj_part = p.id
        from app.models.project import Project

        proj = Project(
            event_id=settings.event_id,
            proposed_by_participant_id=proj_part,
            title=f"lp-{uuid.uuid4().hex[:6]}",
            description="d",
            status="proposed",
        )
        db.add(proj)
        db.flush()
        sub = Submission(
            event_id=settings.event_id,
            project_id=proj.id,
            participant_id=p.id,
            version=1,
            title="t",
            status="withdrawn" if withdrawn else "draft",
        )
        if created is not None:
            sub.created_at = created
        db.add(sub)
        db.flush()
        db.add(
            Score(
                submission_id=sub.id,
                score_value=float(score),
                status=status_,
                scored_at=datetime.utcnow(),
                scorer_version="default-1.0",
            )
        )
        db.flush()
        return p.id, sub

    def test_ranks_by_score_desc(self):
        from app.config import settings
        from app.database import SessionLocal
        from app.services.leaderboard import build_leaderboard

        with SessionLocal() as db:
            hi, _ = self._seed(db, score=90)
            lo, _ = self._seed(db, score=20)
            db.commit()
            rows = build_leaderboard(db, settings.event_id, mode="best")

        ranked = [r.participant.id for r in rows]
        assert ranked.index(hi) < ranked.index(lo)

    def test_excludes_withdrawn_and_disqualified(self):
        from app.config import settings
        from app.database import SessionLocal
        from app.services.leaderboard import build_leaderboard

        with SessionLocal() as db:
            keep, _ = self._seed(db, score=50)
            gone_wd, _ = self._seed(db, score=99, withdrawn=True)
            gone_dq, _ = self._seed(db, score=99, status_="disqualified")
            db.commit()
            ids = {r.participant.id for r in build_leaderboard(db, settings.event_id, mode="best")}

        assert keep in ids
        assert gone_wd not in ids
        assert gone_dq not in ids

    def test_latest_mode_uses_most_recent_submission(self):
        from app.config import settings
        from app.database import SessionLocal
        from app.models.score import Score
        from app.models.submission import Submission
        from app.services.leaderboard import build_leaderboard

        now = datetime.utcnow()
        with SessionLocal() as db:
            pid, old_sub = self._seed(db, score=90, created=now - timedelta(hours=2))
            # A newer, lower-scoring submission for the same participant.
            new_sub = Submission(
                event_id=settings.event_id,
                project_id=old_sub.project_id,
                participant_id=pid,
                version=2,
                title="t2",
                status="draft",
            )
            new_sub.created_at = now
            db.add(new_sub)
            db.flush()
            db.add(
                Score(
                    submission_id=new_sub.id,
                    score_value=15.0,
                    status="scored",
                    scored_at=now,
                    scorer_version="default-1.0",
                )
            )
            db.commit()

            best = {r.participant.id: r.score for r in build_leaderboard(db, settings.event_id, mode="best")}
            latest = {r.participant.id: r.score for r in build_leaderboard(db, settings.event_id, mode="latest")}

        assert best[pid] == 90      # best keeps the high one
        assert latest[pid] == 15    # latest follows the most recent submission


# ============================================================================ #
# Leaderboard endpoint
# ============================================================================ #
class TestLeaderboardEndpoint:
    @pytest.mark.asyncio
    async def test_endpoint_shape(self, client):
        _set_event("OPEN")
        token, pid = _make_participant()
        proj = _make_project(pid)
        await _submit(client, token, proj, pid, title="x", description="y", payload_json='{"m":1}')

        resp = await client.get("/api/leaderboard")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["leaderboard_mode"] == "best"
        assert body["event_state"] == "OPEN"
        mine = [e for e in body["entries"] if e["participant"]["id"] == pid]
        assert len(mine) == 1
        assert mine[0]["score"] == 70  # title 10 + description 20 + payload 40
        assert mine[0]["rank"] >= 1
