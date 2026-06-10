"""The scoring contract.

A scorer takes a submission's data and files and returns a `ScoreResult`. The
interface is intentionally minimal and side-effect free — persistence is the
service's job, not the scorer's — so the same scorer can run in-request, on a
worker, or inside a WASM sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScoreResult:
    """The verdict of a single scoring run."""

    score_value: float
    breakdown: Optional[dict] = None  # optional per-criterion detail
    status: str = "scored"            # "scored" | "failed"
    error: Optional[str] = None


class BaseScorer:
    """Abstract scoring interface. Subclasses implement :meth:`score`."""

    #: Identifies which scorer produced a score — critical for reproducibility.
    version: str = "base-0"

    def score(self, submission_data: dict, files: list[dict]) -> ScoreResult:
        """
        Score a submission.

        Args:
            submission_data: ``{title, description, payload_json, ...}``
            files: ``[{path, mime_type, size_bytes, sha256}, ...]``

        Returns:
            A :class:`ScoreResult`.
        """
        raise NotImplementedError
