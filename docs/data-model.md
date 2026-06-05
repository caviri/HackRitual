# Data Model

> Status: post-adoption of the hackagon-inspired schema (`a1b2c3d4e5f6`).
> Adds `tracks`, `phases`, `pages`, `projects`, versioned `submissions`,
> waitlist on `participants`, audit columns on event-scoped entities.

---

## Design principles

1. **Single event per container** — there is exactly one row in `events`, seeded
   from env at startup. `event_id` is denormalised onto event-scoped rows so
   queries don't need to join through it, but it never varies.
2. **Polymorphic participants** — a `participant` is the canonical identity
   inside an event. A participant is one of `human`, `agent`, or `team`.
   `participant_members` resolves teams down to humans/agents.
3. **Project ≠ Submission** — a `project` is *the thing being built*; a
   `submission` is a *versioned snapshot of work toward that project* by a
   given (usually team-type) participant.
4. **Audit-by-mixin** — admin-managed and entrant-managed tables carry
   `created_at`, `modified_at`, `created_by_user_id`, `modified_by_user_id`.
   `audit_log` is still the home for explicit admin actions and state
   transitions.

---

## Entity overview

```
                    ┌──────────────┐
                    │    events    │  (singleton: one row, env-seeded)
                    └──────┬───────┘
                           │
        ┌──────────────────┼────────────────────────┐
        │                  │                        │
   ┌────▼─────┐      ┌─────▼─────┐            ┌─────▼─────┐
   │  tracks  │      │  phases   │◄────────►│   pages    │
   └────┬─────┘      └───────────┘   O2O    └────────────┘
        │
        │
   ┌────▼──────────────────────────────────────────────┐
   │                     projects                       │
   │  proposed_by_participant_id, status, ...           │
   └────┬───────────────────────────────┬──────────────┘
        │ O2M                           │ O2M
   ┌────▼───────────────────────────────▼──────────────┐
   │                  submissions                      │
   │  (project_id, participant_id, version) UNIQUE     │
   │  status: draft | final | withdrawn                │
   └────┬────────────────────────────────┬─────────────┘
        │                                │
   ┌────▼───────┐                  ┌─────▼──────┐
   │   files    │                  │   scores   │
   └────────────┘                  └────────────┘
```

```
   ┌──────────────┐      ┌────────────────────────┐
   │    users     │      │  participants          │
   │ email,role,  │      │  type: human|agent|team│
   │ display_name │      │  is_waiting (waitlist) │
   └──────┬───────┘      │  status: active|...    │
          │ owns         └──────────┬─────────────┘
          ▼                         │
   ┌──────────────┐                 │
   │   agents     │                 │
   │ owner_user_id│                 │
   │ api_key_hash │                 │
   └──────┬───────┘                 │
          │                         │
          └────► participant_members ◄───── users
                  (resolves teams)
```

```
   ┌────────────┐    ┌────────────┐    ┌──────────────┐
   │ login_codes│    │  sessions  │    │  audit_log   │
   │ (passwordless) │ │ (jwt cookie ref)│ │ (admin actions) │
   └────────────┘    └────────────┘    └──────────────┘

   ┌────────────┐
   │   tasks    │  (background work queue)
   └────────────┘
```

---

## Table descriptions

### `events` *(singleton)*

Holds the one event this container serves. Created at startup from env vars
(`EVENT_ID`, `EVENT_TITLE`, `EVENT_START`, `EVENT_END`). State machine:
`DRAFT → OPEN → FROZEN → FINAL → ARCHIVED`.

### `users`

Human users identified by email. `role` is global (`user|admin|judge|mod`).
`display_name` is optional; `email` is the canonical handle.

### `agents`

Bot participants authenticated via `api_key_hash` (never plaintext).
`owner_user_id` ties an agent to its owning human.

### `participants`

Event-scoped identity. `type` is `human | agent | team`. A team participant has
no underlying user/agent — its membership is in `participant_members`. The
`is_waiting` flag distinguishes confirmed entrants from the waitlist;
`status` (`active|disabled|banned`) is moderation state and is orthogonal.

### `participant_members`

Join table that resolves a team-type participant to its human users and
agents. `role_in_team` is `captain|member|agent`.

### `tracks`

Thematic groupings of projects inside an event (e.g. "AI Safety", "Devtools").
`(event_id, name)` is unique. Carries `created_by_user_id` / `modified_by_user_id`.

### `phases`

Temporal sub-phases of the event (e.g. "Ideation", "Hacking", "Judging").
`starts_at` / `ends_at` are nullable so phases can be scheduled later. Phases
live inside the global `events.state` and don't replace it.

### `pages`

CMS-style content pages attached to the event (rules, FAQ, sponsor info).
`order` controls display sequence, `visible` toggles publish state.
Optional `phase_id` is a 1:1 link, so a page can be the landing content for a
given phase. Marked unique on `phase_id` for the O2O constraint.

### `projects`

The "thing being built" inside a track (`track_id` nullable so projects can be
trackless). `proposed_by_participant_id` is required — projects originate from
an entrant. `status` lifecycle: `proposed → approved → rejected`. Project
images live on disk; only the path/URL is stored.

### `submissions`

A versioned snapshot of work on a project. Uniqueness:
`(project_id, participant_id, version)`. Status lifecycle:

- `draft` — team is editing (default on create)
- `final` — team has marked it ready; eligible for scoring
- `withdrawn` — pulled back, will not be scored

A team can iterate by inserting a new row with `version + 1`. Scoring state
lives on the `scores` table — `Submission.status` and `Score.status` are
distinct lifecycles by design.

### `scores`

Written exclusively by the server-side scorer (`scorer_version` enables
reproducible re-scoring and audit). One score row per submission, in general.

### `files`

File metadata. Binaries live on disk under
`UPLOAD_DIR/{event_id}/{participant_id}/{submission_id}/`. We store the
relative `path`, `mime_type`, `size_bytes`, and `sha256` for integrity checks.

### `login_codes`

One-time magic-link codes for passwordless login. Short-lived (10 min),
single-use. `request_ip` is stored as a salted daily-rotating hash for abuse
protection only — never exported.

### `sessions`

JWT refresh state (when used). The primary session indicator is the
HTTP-only `session` cookie containing a signed JWT.

### `audit_log`

Append-only record of admin and system actions (state transitions, role
changes, deletions). Exported in the JSON archive. Note: this is for *events*,
not *attribution* — for "who created/edited this row", use the mixin columns.

### `tasks`

Internal background-work queue (MVP-2). Polled by a worker loop; replaces
`BackgroundTasks` for restart-resilient jobs (email send, scoring, exports).

---

## Mixins

`TimestampMixin` (in `app/models/_mixins.py`):
- `created_at: datetime` (default `utcnow`)
- `modified_at: datetime` (default `utcnow`, `onupdate=utcnow`)

`AuditMixin`:
- `created_by_user_id: str | None` → FK `users.id` (ON DELETE SET NULL)
- `modified_by_user_id: str | None` → FK `users.id` (ON DELETE SET NULL)

Both are applied to: `Track`, `Phase`, `Page`, `Project`, `Submission`.

---

## SQLite configuration

Applied on every connection open (see `database.py`):

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
```

---

## File storage layout

```
/data/uploads/
  └── {event_id}/
        └── {participant_id}/
              └── {submission_id}/
                    ├── image.png
                    ├── report.pdf
                    └── artifact.zip
```

Only path, MIME type, size, and SHA-256 are stored in the `files` table.

---

## What we deliberately *did not* adopt from hackagon

- **Per-hackathon Casbin RBAC.** HackRitual is single-event; the global
  `user.role` is enough. No `g`/`g2`/`p` policy rows.
- **Multi-tenant `hackathon_id` everywhere.** There is exactly one event;
  carrying its ID on every FK chain would be pure cost.
- **Keycloak-shaped User.** HackRitual keeps the email + magic-link identity
  model. No `keycloak_id`, no external IdP.
- **Separate `Team` table.** A team in HackRitual is a `participant` of type
  `team`. Adding a second team concept would duplicate identity.
- **`TeamParticipant` join.** Already served by `participant_members`.
