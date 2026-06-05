---
id: "011"
title: "JSON Export"
type: feature
status: todo
estimate: "2d"
size: M
depends_on: ["002", "005", "007", "008"]
blocks: ["017"]
spec: "specs/specs/11-json-export.md"
tags: [export, archive, backend]
---

# JSON Export

Generate a structured JSON archive of the complete event — participants, submissions, scores, and metadata — for the ARCHIVED state.

## Tasks

- [ ] `GET /api/export/bundle` — generate full JSON archive (admin only, ARCHIVED state)
- [ ] Bundle structure: event metadata, participants, teams, submissions (with file manifests), scores, leaderboard
- [ ] SHA-256 checksums for all included files
- [ ] Bundle served as downloadable JSON (or ZIP with files)
- [ ] `POST /api/export/trigger` — queue async export task via Task model
- [ ] `GET /api/export/status` — check export task status
- [ ] `app/schemas/export.py` — export bundle schema

## Bundle Schema

```json
{
  "event": { "id", "title", "type", "state", "start_at", "end_at" },
  "exported_at": "ISO 8601",
  "participants": [...],
  "submissions": [...],
  "scores": [...],
  "leaderboard": [...]
}
```

## Notes

- Only available in ARCHIVED state to prevent partial exports
- File contents referenced by path + SHA-256; actual file bytes in ZIP variant
- GitHub export (Step 17) uses this bundle as input
