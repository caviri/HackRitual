"""The default scorer — a completeness rubric.

A placeholder rubric that rewards a submission for carrying the marks of real
work: a title, a description, attached files, a structured payload. Deployers
replace it with event-specific logic (a custom module via ``SCORER_MODULE``, or
a WASM module in MVP-3); the leaderboard machinery does not care which scorer
produced the number.
"""

from __future__ import annotations

from app.scoring.base import BaseScorer, ScoreResult


class DefaultScorer(BaseScorer):
    """Scores 0–100 on completeness signals."""

    version = "default-1.0"

    def score(self, submission_data: dict, files: list[dict]) -> ScoreResult:
        score = 0.0
        breakdown: dict[str, float] = {}

        if submission_data.get("title"):
            score += 10
            breakdown["title"] = 10
        if submission_data.get("description"):
            score += 20
            breakdown["description"] = 20
        if files:
            file_score = min(len(files) * 10, 30)
            score += file_score
            breakdown["files"] = file_score
        if submission_data.get("payload_json"):
            score += 40
            breakdown["payload"] = 40

        return ScoreResult(score_value=score, breakdown=breakdown)
