"""Scoring modules — the rubrics by which work is weighed.

The interface (`BaseScorer`) is deliberately abstract so the same contract
serves a synchronous Python scorer (MVP-1), an async queue (MVP-2), and a
sandboxed WASM module (MVP-3).
"""

from app.scoring.base import BaseScorer, ScoreResult
from app.scoring.default_scorer import DefaultScorer

__all__ = ["BaseScorer", "ScoreResult", "DefaultScorer"]
