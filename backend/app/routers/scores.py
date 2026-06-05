"""Scoring — judges record numeric scores against submissions.

`breakdown` is stored as JSON in `Score.breakdown_json`. The headline
`score_value` is either supplied by the judge or computed as the mean of
the breakdown if absent.
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.score import Score
from app.models.submission import Submission
from app.models.user import User
from app.schemas.scores import ScoreCreate, ScoreResponse


router = APIRouter(prefix="/api/submissions", tags=["scores"])


def _score_to_response(s: Score) -> ScoreResponse:
    breakdown: dict[str, float] = {}
    notes = None
    if s.breakdown_json:
        try:
            loaded = json.loads(s.breakdown_json)
            if isinstance(loaded, dict):
                breakdown = {
                    k: float(v)
                    for k, v in loaded.items()
                    if k != "_notes" and isinstance(v, (int, float))
                }
                notes = loaded.get("_notes")
        except Exception:
            pass
    return ScoreResponse(
        id=s.id,
        submission_id=s.submission_id,
        score_value=s.score_value,
        breakdown=breakdown,
        notes=notes,
        status=s.status,
        scorer_version=s.scorer_version,
        scored_at=s.scored_at,
    )


@router.get("/{submission_id}/scores", response_model=list[ScoreResponse])
def list_scores(
    submission_id: str,
    db: Session = Depends(get_db),
) -> list[ScoreResponse]:
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    rows = (
        db.query(Score)
        .filter(Score.submission_id == submission_id)
        .order_by(Score.scored_at.desc().nullslast())
        .all()
    )
    return [_score_to_response(s) for s in rows]


@router.post(
    "/{submission_id}/scores",
    response_model=ScoreResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_score(
    submission_id: str,
    body: ScoreCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ScoreResponse:
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    if sub.status != "final":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"submission must be in `final` status to score (is `{sub.status}`)",
        )

    breakdown = body.breakdown or {}
    if body.score_value is None:
        if not breakdown:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "provide either score_value or a non-empty breakdown",
            )
        score_value = sum(breakdown.values()) / len(breakdown)
    else:
        score_value = body.score_value

    payload: dict[str, object] = {k: float(v) for k, v in breakdown.items()}
    if body.notes:
        payload["_notes"] = body.notes

    row = Score(
        submission_id=submission_id,
        score_value=float(score_value),
        breakdown_json=json.dumps(payload) if payload else None,
        status="scored",
        scorer_version=f"admin:{admin.email}",
        scored_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _score_to_response(row)


score_id_router = APIRouter(prefix="/api/scores", tags=["scores"])


@score_id_router.delete(
    "/{score_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_score(
    score_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    s = db.get(Score, score_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "score not found")
    db.delete(s)
    db.commit()
