---
id: "009"
title: "Admin Console"
type: feature
status: todo
estimate: "2d"
size: M
depends_on: ["004"]
blocks: []
spec: "specs/specs/09-admin-console.md"
tags: [admin, backend]
---

# Admin Console

Admin-only endpoints for event management, participant moderation, and operational oversight.

## Tasks

- [ ] `GET /api/admin/overview` — summary stats (participant count, submission count, event state, storage usage)
- [ ] `GET /api/admin/audit-log` — paginated audit log with filtering
- [ ] `POST /api/events/transition` — state machine transitions (see Step 06)
- [ ] `GET /api/admin/submissions` — all submissions with full details (admin view)
- [ ] `POST /api/admin/submissions/{id}/reset` — reset submission to `received` (for re-scoring)
- [ ] Admin override for scoring (force-complete even if not all submissions scored)
- [ ] `GET /api/admin/storage` — storage usage stats

## Notes

- All endpoints require `require_admin` dependency
- Audit log is already being populated by Steps 03 and 04; this step adds the read endpoint
- Complements the scaffold companion (Step 10) which shows these stats via the dev UI
