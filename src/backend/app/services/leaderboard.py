"""
Leaderboard — the ranked standing of participants.

Server-authoritative and derived purely from stored `Score` rows. Withdrawn
submissions and non-`scored` verdicts (failed, disqualified) are excluded. The
event's `leaderboard_mode` decides which of a participant's submissions counts:

- ``best``   — their highest scored submission
- ``latest`` — the score of their most recently created scored submission

Ties break by earliest activity (``last_submission_at`` ascending), per spec §8.6.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.participant import Participant
from app.models.project import Project
from app.models.score import Score
from app.models.submission import Submission


@dataclass
class LeaderboardRow:
    participant: Participant
    score: float
    submission_count: int
    last_submission_at: Optional[datetime]


def _best_scored_value(db: Session, submission_id: str) -> Optional[float]:
    """Highest `scored` value recorded against a submission, if any."""
    rows = (
        db.query(Score.score_value)
        .filter(Score.submission_id == submission_id, Score.status == "scored")
        .all()
    )
    values = [r[0] for r in rows]
    return max(values) if values else None


def build_leaderboard(
    db: Session,
    event_id: str,
    mode: str = "best",
    track_id: Optional[str] = None,
    limit: int = 50,
) -> list[LeaderboardRow]:
    """Compute the ranked standing for an event.

    Plain Python rather than one heavy SQL statement — clear, easy to test, and
    fast enough for MVP-1 scale (~100 participants / ~1000 submissions).
    """
    participants = (
        db.query(Participant)
        .filter(Participant.event_id == event_id, Participant.status == "active")
        .all()
    )

    rows: list[LeaderboardRow] = []
    for participant in participants:
        q = db.query(Submission).filter(
            Submission.participant_id == participant.id,
            Submission.status != "withdrawn",
        )
        if track_id:
            q = q.join(Project, Project.id == Submission.project_id).filter(
                Project.track_id == track_id
            )
        subs = q.all()
        if not subs:
            continue

        # (submission, its best scored value) for submissions that have a score.
        scored = [
            (s, v)
            for s in subs
            if (v := _best_scored_value(db, s.id)) is not None
        ]
        if not scored:
            continue

        if mode == "latest":
            latest = max(scored, key=lambda sv: sv[0].created_at or datetime.min)
            headline = latest[1]
        else:  # best
            headline = max(v for _, v in scored)

        rows.append(
            LeaderboardRow(
                participant=participant,
                score=headline,
                submission_count=len(subs),
                last_submission_at=max(
                    (s.created_at for s in subs if s.created_at), default=None
                ),
            )
        )

    # Highest score first; ties to earliest activity.
    rows.sort(
        key=lambda r: (
            -r.score,
            r.last_submission_at or datetime.max,
        )
    )
    return rows[:limit]
