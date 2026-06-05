---
id: "008"
title: "Scoring (Basic)"
type: feature
status: todo
estimate: "3d"
size: L
depends_on: ["007"]
blocks: ["016"]
spec: "specs/specs/08-scoring-basic.md"
tags: [scoring, leaderboard, backend]
---

# Scoring (Basic)

Judge-facing scoring interface and leaderboard. Authoritative scores are server-side only.

## Tasks

- [ ] `POST /api/scores` — submit a score for a submission (judge/admin only)
- [ ] `GET /api/scores/{submission_id}` — get scores for a submission
- [ ] `GET /api/leaderboard` — ranked list of participants by score (public in FINAL/ARCHIVED)
- [ ] `PATCH /api/scores/{id}` — update score (FROZEN state only, judge/admin)
- [ ] Score aggregation: average, sum, or weighted (configurable via event config_json)
- [ ] Score model: criterion, value (float), max_value, judge_user_id, notes
- [ ] Enforce: scores only accepted in FROZEN state
- [ ] Enforce: leaderboard only public in FINAL or ARCHIVED state
- [ ] `app/schemas/scores.py` — request/response schemas

## Security

Client-side WASM scoring (Step 16) is preview-only. Official scores written only by server.
Leaderboard reads exclusively from DB `scores` table.

## Notes

- Scoring criteria configurable in `event.config_json`
- Multiple judges can score the same submission (averaged or aggregated)
