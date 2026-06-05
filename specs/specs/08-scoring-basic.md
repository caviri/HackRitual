# 08 — Scoring (Basic) & Leaderboards

**Milestone:** MVP-1
**Priority:** High
**Dependencies:** [07-submission-system](07-submission-system.md)
**Specs reference:** §7.5 (Scoring & Leaderboards)

---

## Overview

Server-authoritative scoring for submissions. In MVP-1, scoring uses a Python function executed synchronously. Async scoring via task queue is covered in [14-task-queue-worker](14-task-queue-worker.md). WASM scoring is covered in [16-wasm-scoring](16-wasm-scoring.md). Client-side scoring is never trusted for the leaderboard.

---

## Tasks

### 8.1 Scoring Module Interface

Define a standard interface for scoring functions:

```python
# backend/app/scoring/base.py

from dataclasses import dataclass

@dataclass
class ScoreResult:
    score_value: float
    breakdown: dict | None = None  # optional detailed breakdown
    status: str = "scored"         # 'scored' | 'failed'
    error: str | None = None

class BaseScorer:
    """Abstract scoring interface."""

    def score(self, submission_data: dict, files: list[dict]) -> ScoreResult:
        """
        Score a submission.

        Args:
            submission_data: {title, description, payload_json, metadata}
            files: [{path, mime_type, size_bytes, sha256}]

        Returns:
            ScoreResult with score_value and optional breakdown
        """
        raise NotImplementedError
```

### 8.2 Default Python Scorer (MVP-1)

```python
# backend/app/scoring/default_scorer.py

class DefaultScorer(BaseScorer):
    """
    Simple Python scoring function.
    Replace with event-specific logic or WASM module (MVP-3).
    """

    def score(self, submission_data: dict, files: list[dict]) -> ScoreResult:
        # Example: score based on completeness
        score = 0.0
        breakdown = {}

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
```

The deployer/admin can replace this with a custom scoring function by:
1. Mounting a custom scorer module
2. Setting `SCORER_MODULE` env var
3. Or uploading a WASM module (MVP-3)

### 8.3 Synchronous Scoring Service

```python
# backend/app/services/scoring_service.py

class ScoringService:
    def __init__(self, scorer: BaseScorer):
        self.scorer = scorer

    def score_submission(self, db: Session, submission_id: str) -> Score:
        submission = db.get(Submission, submission_id)
        files = db.query(File).filter(File.submission_id == submission_id).all()

        submission_data = {
            "title": submission.title,
            "description": submission.description,
            "payload_json": json.loads(submission.payload_json) if submission.payload_json else None,
        }
        file_data = [
            {"path": f.path, "mime_type": f.mime_type, "size_bytes": f.size_bytes, "sha256": f.sha256}
            for f in files
        ]

        result = self.scorer.score(submission_data, file_data)

        score = Score(
            id=str(uuid4()),
            submission_id=submission_id,
            score_value=result.score_value,
            breakdown_json=json.dumps(result.breakdown) if result.breakdown else None,
            scored_at=datetime.utcnow(),
            status=result.status,
            scorer_version=self.scorer_version,
        )
        db.add(score)
        submission.status = "scored" if result.status == "scored" else "failed"
        db.commit()
        return score
```

### 8.4 Score Endpoints

#### Get submission score
`GET /api/submissions/{submission_id}/score`

```json
{
  "submission_id": "uuid",
  "score_value": 70.0,
  "breakdown": {
    "title": 10,
    "description": 20,
    "payload": 40
  },
  "status": "scored",
  "scored_at": "2026-03-01T14:31:00Z",
  "scorer_version": "default-1.0"
}
```

#### Admin: Trigger re-score
`POST /api/admin/submissions/{id}/rescore`

- Re-runs scoring for a specific submission
- Useful when scoring logic changes before FINAL
- Old score is replaced, logged in audit

#### Admin: Manual score override
`PATCH /api/admin/scores/{score_id}`

```json
{
  "score_value": 85.0,
  "status": "scored",
  "reason": "Manual adjustment after review"
}
```

- Log to audit with reason

### 8.5 Leaderboard

#### Public leaderboard
`GET /api/leaderboard`

**Query params:** `?track=track-1&limit=50`

**Response:**
```json
{
  "event_id": "hackritual-2026-bern",
  "event_state": "OPEN",
  "leaderboard_mode": "best",
  "updated_at": "2026-03-01T15:00:00Z",
  "entries": [
    {
      "rank": 1,
      "participant": {
        "id": "uuid",
        "display_name": "Team Forge",
        "type": "team"
      },
      "score": 95.0,
      "submission_count": 3,
      "last_submission_at": "2026-03-01T14:45:00Z"
    },
    {
      "rank": 2,
      "participant": {
        "id": "uuid",
        "display_name": "Alice",
        "type": "human"
      },
      "score": 90.0,
      "submission_count": 5,
      "last_submission_at": "2026-03-01T14:30:00Z"
    }
  ]
}
```

#### Leaderboard Query Logic

```sql
-- For "best" mode:
SELECT
    p.id, p.display_name, p.type,
    MAX(s2.score_value) as best_score,
    COUNT(s.id) as submission_count,
    MAX(s.created_at) as last_submission_at
FROM participants p
JOIN submissions s ON s.participant_id = p.id
    AND s.status NOT IN ('withdrawn')
JOIN scores s2 ON s2.submission_id = s.id
    AND s2.status = 'scored'
WHERE p.event_id = :event_id
    AND p.status = 'active'
GROUP BY p.id
ORDER BY best_score DESC, last_submission_at ASC
LIMIT :limit;

-- For "latest" mode: use the most recent scored submission per participant
```

### 8.6 Tie-Breaking Rules

Configurable per event (specs §7.5):

| Rule | Description |
|------|------------|
| `earliest` (default) | Earliest submission time wins |
| `secondary_metric` | Highest secondary score from breakdown |
| `admin_override` | Admin manually sets rank (logged) |

Implementation:
- Default: ORDER BY score DESC, submission_time ASC
- Secondary: ORDER BY score DESC, breakdown->>'secondary' DESC
- Override: separate `rank_override` column on Score

### 8.7 Score Status Flow

```
Submission created → Score status: PENDING
Scorer runs       → Score status: SCORED or FAILED
Admin override    → Score status: SCORED (with override flag)
Admin DQ          → Score status: DISQUALIFIED
```

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/submissions/{id}/score` | Owner/Public | View score |
| GET | `/api/leaderboard` | Public | View leaderboard |
| POST | `/api/admin/submissions/{id}/rescore` | Admin | Re-score submission |
| PATCH | `/api/admin/scores/{id}` | Admin | Override score |

---

## Acceptance Criteria

- [ ] Submissions are scored synchronously on creation (MVP-1)
- [ ] Scores stored with value, breakdown, status, and scorer version
- [ ] Leaderboard displays ranked participants with correct mode (best/latest)
- [ ] Tie-breaking rules applied correctly
- [ ] Withdrawn and disqualified submissions excluded from leaderboard
- [ ] Admin can trigger re-score and manual override
- [ ] All score modifications logged to audit
- [ ] Leaderboard query performs well with ~100 participants and ~1000 submissions
- [ ] Score API never exposes other participants' private data

---

## Developer Notes

- Keep the scoring interface abstract — it must support Python functions (MVP-1), async queue (MVP-2), and WASM (MVP-3)
- For MVP-1, scoring runs in-request (synchronous). This is acceptable for lightweight scorers
- Cache the leaderboard in memory with a short TTL (e.g., 30 seconds) to avoid repeated heavy queries
- The `scorer_version` field tracks which version of the scorer produced the score — critical for reproducibility
- Breakdown JSON is flexible — scorers define their own structure
- Consider adding a `GET /api/leaderboard/me` endpoint that returns the current user's rank
