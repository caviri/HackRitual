"""
Scoring service — runs a scorer against a submission and records the verdict.

Server-authoritative: client-supplied scores are never trusted for the
leaderboard. In MVP-1 scoring runs synchronously in-request; the same
`score_submission` entry point will later be callable from a worker (MVP-2).
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.file import File
from app.models.score import Score
from app.models.submission import Submission
from app.scoring import BaseScorer, DefaultScorer

# Cache instantiated WASM scorers by version — instantiation is not free.
_wasm_cache: dict[str, BaseScorer] = {}


def get_scorer(db: Session | None = None) -> BaseScorer:
    """
    Return the active scorer.

    If the event configures a WASM scorer (and the module + runtime are present),
    use it; otherwise fall back to the default Python scorer.
    """
    if db is None:
        return DefaultScorer()
    try:
        from app.scoring.wasm_scorer import WasmScorer, wasmtime_available
        from app.services import wasm_store

        scorer_ref = wasm_store.get_active_scorer(db)
        if scorer_ref and scorer_ref.get("type") == "wasm" and wasmtime_available():
            version = scorer_ref.get("version", "wasm:unknown")
            if version not in _wasm_cache:
                data = wasm_store.load_wasm_bytes(scorer_ref)
                if data is None:
                    return DefaultScorer()
                _wasm_cache[version] = WasmScorer(
                    data,
                    version=version,
                    time_limit_ms=settings.wasm_time_limit_ms,
                    memory_limit_mb=settings.wasm_memory_limit_mb,
                )
            return _wasm_cache[version]
    except Exception:
        # Any failure to build the configured scorer falls back to the default.
        return DefaultScorer()
    return DefaultScorer()


def _submission_payload(submission: Submission) -> dict:
    payload = None
    if submission.payload_json:
        try:
            payload = json.loads(submission.payload_json)
        except (ValueError, TypeError):
            payload = None
    return {
        "title": submission.title,
        "description": submission.description,
        "payload_json": payload,
    }


def score_submission(
    db: Session, submission_id: str, scorer: BaseScorer | None = None
) -> Score:
    """
    Score a submission and upsert the scorer's `Score` row.

    One row is kept per (submission, scorer version) — re-scoring replaces the
    previous verdict rather than piling up. Does not commit; the caller owns the
    transaction.
    """
    scorer = scorer or get_scorer(db)
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise ValueError(f"unknown submission {submission_id}")

    files = db.query(File).filter(File.submission_id == submission_id).all()
    file_data = [
        {
            "path": f.path,
            "mime_type": f.mime_type,
            "size_bytes": f.size_bytes,
            "sha256": f.sha256,
        }
        for f in files
    ]

    import time as _time

    from app.services import metrics_service

    _start = _time.perf_counter()
    result = scorer.score(_submission_payload(submission), file_data)
    metrics_service.record_scoring_time(db, (_time.perf_counter() - _start) * 1000)

    row = (
        db.query(Score)
        .filter(
            Score.submission_id == submission_id,
            Score.scorer_version == scorer.version,
        )
        .first()
    )
    if row is None:
        row = Score(submission_id=submission_id, scorer_version=scorer.version)
        db.add(row)

    row.score_value = float(result.score_value)
    row.breakdown_json = json.dumps(result.breakdown) if result.breakdown else None
    row.status = result.status
    row.scored_at = datetime.utcnow()
    db.flush()
    return row


def active_score(db: Session, submission_id: str) -> Score | None:
    """The current headline score for a submission — the most recent one."""
    return (
        db.query(Score)
        .filter(Score.submission_id == submission_id)
        .order_by(Score.scored_at.desc().nullslast())
        .first()
    )
