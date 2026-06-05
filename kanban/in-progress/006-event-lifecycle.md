---
id: "006"
title: "Event Lifecycle"
type: feature
status: in-progress
estimate: "3d"
size: M
depends_on: ["002"]
blocks: ["007"]
spec: "specs/specs/06-event-lifecycle.md"
tags: [event, state-machine, backend]
---

# Event Lifecycle

Implement the `DRAFT → OPEN → FROZEN → FINAL → ARCHIVED` state machine for the event, with admin-controlled transitions, validation rules, and participant registration enforcement.

## Tasks

- [ ] `GET /api/events/current` — return current event state and metadata (public)
- [ ] `POST /api/events/transition` — admin-only state transition with validation
- [ ] State transition rules:
  - DRAFT → OPEN: start_at must be in the past or present
  - OPEN → FROZEN: closes submission gate
  - FROZEN → FINAL: scoring must be complete (or override flag)
  - FINAL → ARCHIVED: seals the record
  - No backwards transitions allowed
- [ ] Audit log entry for every state change
- [ ] `app/schemas/events.py` — request/response schemas
- [ ] Tests for each valid transition + all invalid transitions

## State Machine

```
DRAFT → OPEN → FROZEN → FINAL → ARCHIVED
```

| State | Meaning |
|-------|---------|
| DRAFT | Configuration phase; no participants |
| OPEN | Registration and submissions open |
| FROZEN | Submissions closed; scoring begins |
| FINAL | Results public; no changes |
| ARCHIVED | Sealed; ready for export |

## Acceptance Criteria

- All 5 states reachable via API
- Invalid transitions return 422 with clear error message
- State visible in `GET /api/health` response
- Participant registration blocked when state not in DRAFT/OPEN (already enforced in Step 05)
