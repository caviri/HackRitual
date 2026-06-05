# 06 — Event Lifecycle

**Milestone:** MVP-1
**Priority:** Critical
**Dependencies:** [02-database-layer](02-database-layer.md), [04-user-management](04-user-management.md)
**Specs reference:** §7.1 (Event Lifecycle / Ritual)

---

## Overview

The platform manages a single event per deployment instance. The event follows a strict state machine (the "Ritual") from creation through archival. Admin controls transition the event between states, and each state gates what operations are allowed.

---

## Tasks

### 6.1 Event State Machine

```
DRAFT → OPEN → FROZEN → FINAL → ARCHIVED
```

| State | Submissions | Scoring | Registration | Export | Description |
|-------|------------|---------|-------------|--------|-------------|
| `DRAFT` | No | No | Configurable | No | Setup phase |
| `OPEN` | Yes | Yes | Yes | Snapshot OK | Active event |
| `FROZEN` | No | Yes (backlog) | No | Snapshot OK | Deadline passed |
| `FINAL` | No | No | No | Yes | Results locked |
| `ARCHIVED` | No | No | No | Read-only | Export complete |

**Valid transitions:**
- `DRAFT` → `OPEN`
- `OPEN` → `FROZEN`
- `FROZEN` → `FINAL`
- `FROZEN` → `OPEN` (reopen — admin override, logged)
- `FINAL` → `ARCHIVED`

**Invalid transitions (must reject):**
- `OPEN` → `DRAFT` (cannot go back to draft)
- `FINAL` → `OPEN` (cannot reopen after finalizing)
- `ARCHIVED` → anything (terminal state)

### 6.2 State Transition Endpoint

`POST /api/admin/event/state`

```json
{
  "state": "OPEN",
  "reason": "Opening submissions for HackRitual Bern 2026"
}
```

**Server logic:**
1. Validate current state allows the requested transition
2. Perform pre-transition checks:
   - `OPEN` → `FROZEN`: warn if scoring queue has pending items
   - `FROZEN` → `FINAL`: verify all scoring is complete (or admin override)
3. Update event state in DB
4. Log to audit log with reason
5. Return updated event

**Response:**
```json
{
  "id": "hackritual-2026-bern",
  "state": "OPEN",
  "previous_state": "DRAFT",
  "transitioned_at": "2026-03-01T09:00:00Z",
  "transitioned_by": "admin@example.com"
}
```

### 6.3 Event Configuration Endpoint

`GET /api/event`

Public endpoint returning event metadata:

```json
{
  "id": "hackritual-2026-bern",
  "title": "HackRitual Bern 2026",
  "type": "hackathon",
  "state": "OPEN",
  "start": "2026-03-01T09:00:00+01:00",
  "end": "2026-03-02T17:00:00+01:00",
  "config": {
    "registration_open": true,
    "submission_limit_per_participant": 10,
    "submission_limit_window_hours": 24,
    "leaderboard_mode": "best",
    "agent_policy": "allowed",
    "tracks": []
  }
}
```

### 6.4 Admin Event Configuration

`PATCH /api/admin/event/config`

```json
{
  "submission_limit_per_participant": 5,
  "leaderboard_mode": "latest",
  "agent_policy": "forbidden",
  "tracks": [
    {"id": "track-1", "name": "Open Track", "description": "Anything goes"}
  ]
}
```

Only modifiable in `DRAFT` and `OPEN` states. Some fields may be locked after `OPEN` (e.g., `leaderboard_mode`).

### 6.5 State-Based Guards

Implement middleware/service that gates operations based on event state:

```python
class EventGuard:
    def require_state(self, *allowed_states: str):
        """Raises 409 Conflict if event is not in an allowed state."""

    def can_submit(self) -> bool:
        """True only if state is OPEN."""

    def can_register(self) -> bool:
        """True if state is DRAFT (with config) or OPEN."""

    def can_score(self) -> bool:
        """True if state is OPEN or FROZEN."""

    def can_export(self) -> bool:
        """True if state is FINAL or ARCHIVED."""

    def is_read_only(self) -> bool:
        """True if state is ARCHIVED."""
```

Use as FastAPI dependency:

```python
@router.post("/submissions")
async def create_submission(
    ...,
    guard: EventGuard = Depends(get_event_guard),
):
    guard.require_state("OPEN")
    ...
```

### 6.6 Event Initialization

On first startup:
1. Read event metadata from env vars (`EVENT_ID`, `EVENT_TITLE`, etc.)
2. Create `Event` record if it doesn't exist (state = `DRAFT`)
3. If event already exists, verify env vars match (warn on mismatch, don't overwrite)
4. Log event creation to audit log

### 6.7 Automatic State Transitions (Optional)

If `EVENT_START` and `EVENT_END` are set:
- Optionally auto-transition `DRAFT` → `OPEN` at start time
- Optionally auto-transition `OPEN` → `FROZEN` at end time
- This should be configurable (`AUTO_TRANSITIONS=true/false`)
- Implemented via a background check every 60 seconds

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/event` | Public | Get event info and state |
| POST | `/api/admin/event/state` | Admin | Transition event state |
| PATCH | `/api/admin/event/config` | Admin | Update event configuration |
| GET | `/api/admin/event/audit` | Admin | Get state transition history |

---

## Acceptance Criteria

- [ ] Event created from env vars on first startup
- [ ] State machine enforces valid transitions only
- [ ] Invalid transitions return `409 Conflict` with clear message
- [ ] All state changes logged to audit log with actor and reason
- [ ] Operations gated by event state (submit only when OPEN, etc.)
- [ ] `GET /api/event` returns current state and config
- [ ] Admin can modify event config in DRAFT/OPEN states
- [ ] Optional auto-transitions based on EVENT_START/EVENT_END

---

## Developer Notes

- The event state machine is central — invest in good tests for all transitions
- Use an enum for states: `class EventState(str, Enum): DRAFT = "DRAFT" ...`
- The `config_json` field on the Event model stores all configurable rules as a JSON object
- Consider emitting a simple in-process event/signal on state change so other services can react (e.g., clear caches, notify)
- The `FROZEN → OPEN` reopen transition should require explicit admin confirmation (extra field in request)
