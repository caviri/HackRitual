---
id: "007"
title: "Submission System"
type: feature
status: todo
estimate: "4d"
size: L
depends_on: ["005", "006"]
blocks: ["008", "011"]
spec: "specs/specs/07-submission-system.md"
tags: [submissions, file-upload, backend]
---

# Submission System

Allow participants to submit their work during the OPEN phase — supporting both text/link submissions and file uploads.

## Tasks

- [ ] `POST /api/submissions` — create submission (auth required, participant must exist, event must be OPEN)
- [ ] `GET /api/submissions` — list submissions (public or filtered by participant)
- [ ] `GET /api/submissions/{id}` — get single submission
- [ ] `PATCH /api/submissions/{id}` — update own submission (OPEN state only)
- [ ] `DELETE /api/submissions/{id}` (withdraw) — sets status to `withdrawn`
- [ ] File upload: `POST /api/submissions/{id}/files` — multipart upload, SHA-256 integrity, stored in `/data/uploads/`
- [ ] `GET /api/submissions/{id}/files` — list uploaded files
- [ ] `DELETE /api/submissions/{id}/files/{fid}` — remove file
- [ ] Enforce: disabled/banned participants cannot submit
- [ ] Enforce: one submission per participant (or configurable max)
- [ ] Queue scoring task on submission creation
- [ ] `app/schemas/submissions.py` — request/response schemas

## Submission Statuses

`received` → `queued` → `scored` | `failed` | `withdrawn`

## Notes

- File uploads use `app/utils/files.py` (already implemented in Step 02)
- Payload JSON for agent submissions (structured data, not file)
- Submission closes with FROZEN state — no edits after that
