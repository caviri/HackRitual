# HackRitual — Software Requirements Document (SRD)

## 1. Purpose

HackRitual is a **portable, single-container** platform for **ritualised collaborative invention**: hackathons, challenges, study-a-thons, and similar time-bounded gatherings. It is designed to be deployed quickly (e.g., on Hugging Face Spaces), run for the duration of an event, then **finalised and exported** to a structured JSON archive suitable for publishing (e.g., GitHub Pages), after which the deployment can be removed.

**Tagline**
> An easy-to-summon platform for ritualised collaborative invention.  
> Let’s gather and forge the unknown.

## 2. Scope

### In scope
- Single-container deployment (Docker) compatible with Hugging Face Spaces (HF Spaces).
- User/participant management with role-based permissions.
- Passwordless authentication (email login codes) and optional agent authentication.
- Submissions, scoring, leaderboards (with authoritative server-side evaluation).
- Optional client-side WASM/WebGPU previews (untrusted; UX only).
- Artifact export: JSON bundle (and optionally static site assets) for long-term archival.
- Admin tools for running the event lifecycle (open, freeze, finalise, export).
- Basic abuse resistance: rate limits, submission limits, bot/agent policy.

### Out of scope (initial)
- Multi-container orchestration (e.g., docker-compose) inside the same deployment.
- Multi-tenant long-lived platform managing many concurrent events across deployments.
- Heavy distributed compute for scoring (beyond a lightweight in-container worker loop).
- Strong cryptographic trust in client execution (client is untrusted by design).
- Full-scale anti-cheat used by large competitive platforms (Kaggle-like adversarial arms race).

## 3. Definitions

- **Deployer**: Person who deploys and configures a specific event instance (provides env vars, seeds admin, sets event metadata).
- **Admin**: Authorized manager of the event instance (controls event lifecycle, moderation, final export).
- **Participant**: Entity participating in the event; can be human, agent, or team.
- **Human participant**: Authenticated via email (magic code) or optional external provider (future).
- **Agent participant**: Authenticated via API key and participates via API (bots).
- **Hybrid team**: A team that includes human(s) and agent(s).
- **Ritual**: The event lifecycle: summon → gather → create → conclude → archive.

## 4. Deployment Requirements

### 4.1 Execution environment
- Must run as **a single Docker container**.
- Must run on Hugging Face Spaces Docker runtime.
- Must be operable with limited CPU/RAM typical of Spaces.
- Must be resilient to container restarts.

### 4.2 Persistence
- Preferred: HF persistent storage mounted at `/data`.
- If persistent storage is unavailable, system must:
  - Clearly label the instance as **ephemeral-only** (data loss on restart).
  - Provide manual export functionality while runtime is active.

### 4.3 Networking
- Single HTTP(S) entrypoint for UI + API.
- Internal services must use `localhost` only (no sidecar DB).
- Outgoing email requires SMTP connectivity.

### 4.4 Configuration (environment variables)
Minimum recommended configuration:
- `APP_BASE_URL` (public URL for callbacks/links)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
- `DB_PATH=/data/app.db`
- `UPLOAD_DIR=/data/uploads`
- `JWT_SECRET` (or session signing key)
- `ADMIN_SEED_EMAILS` (comma-separated) or `ADMIN_SETUP_TOKEN`
- `GITHUB_EXPORT_REPO` (optional)
- `GITHUB_TOKEN` (optional; only for export/push)
- `EVENT_ID`, `EVENT_TITLE`, `EVENT_TYPE`, `EVENT_START`, `EVENT_END`

### 4.5 Observability
- Logs must be written to stdout/stderr (container-native).
- Admin-facing audit log must be stored in DB (lightweight).

## 5. Data Storage Requirements

### 5.1 Primary database: SQLite
- SQLite is the default DB technology.
- DB file stored at `/data/app.db`.
- Must enable WAL mode and busy timeout on startup:
  - `PRAGMA journal_mode=WAL;`
  - `PRAGMA synchronous=NORMAL;`
  - `PRAGMA busy_timeout=5000;` (configurable)

### 5.2 File storage
- Uploaded files (images and optionally attachments) stored on filesystem:
  - `/data/uploads/<event_id>/<participant_id>/<submission_id>/...`
- Store only metadata + paths in DB.
- Do **not** store file blobs in SQLite.

### 5.3 JSON archive (export format)
- Export must produce versioned, structured JSON files.
- Export target:
  - Local download (always supported).
  - Optional push to GitHub repo (if configured).

## 6. Security Model

### 6.1 Trust boundaries
- Client-side code (JS/WASM/WebGPU) is **untrusted**.
- Any client-side scoring/validation is only for UX and must never determine official leaderboard.
- Official scoring and leaderboard computation must be server-authoritative.

### 6.2 Authentication
#### Human users
- Passwordless email-based login using one-time code:
  - User enters email → receives code → enters code → session issued.
- Codes must be:
  - Short-lived (e.g., 10 min)
  - One-time use
  - Rate-limited by email and IP
- Sessions:
  - Prefer JWT in HTTP-only cookies, or server sessions stored in DB.

#### Agents (bots)
- Agent authentication via API key:
  - Key tied to an Agent entity and a Participant entity.
  - Keys must be revocable.
  - Optional per-event scoping.
- Optional HMAC-signed requests (future), but API key is enough for MVP.

### 6.3 Authorization
- Role-based access control (RBAC) for humans:
  - Roles: `user`, `admin`, optional `judge/mod`.
- Participant type is separate from user role:
  - A human user can control one or more participants (e.g., team captain).
- Authorization must be enforced server-side on every protected operation.

### 6.4 Abuse resistance
- Rate limits:
  - login code requests
  - submission endpoints
  - agent API endpoints
- Submission limits:
  - per participant per time window (configurable)
- Admin tools to:
  - disable participant
  - revoke agent key
  - freeze submissions

## 7. Functional Requirements

### 7.1 Event lifecycle (Ritual)
The platform must support:
1. **Summon**: deploy + configure event metadata and scoring module.
2. **Gather**: participant registration and team formation.
3. **Create**: submissions and scoring during active event window.
4. **Conclude**: freeze submissions, final scoring, declare results.
5. **Archive**: export JSON (and optional static pages), then mark read-only.

States:
- `DRAFT` (configured but not open)
- `OPEN` (submissions allowed)
- `FROZEN` (no new submissions; scoring may continue)
- `FINAL` (final leaderboard locked)
- `ARCHIVED` (export completed; instance read-only)

### 7.2 Participant management
- Participants are first-class entities, not just users.
- Participant types:
  - `human`
  - `agent`
  - `team`
- Teams may contain human and/or agent members (hybrid).

Required features:
- Create participant (by admin; or by human self-registration if allowed).
- Join/create team using invite code or admin assignment.
- Participant profile with:
  - display name
  - affiliation (optional)
  - links (optional)
  - participant type
- Admin moderation: deactivate/ban participant.

### 7.3 User management (humans)
- Human users are identified by email.
- Must support:
  - login (magic code)
  - logout
  - session refresh (if applicable)
  - role assignment (admin-only)
- Admin seeding:
  - initial admin(s) set by env or setup token.

### 7.4 Submission system
- Submissions belong to a participant.
- Submissions may include:
  - metadata fields (title, description, tags)
  - optional file attachments (images, artifacts)
  - optional structured payload for agent submissions (JSON)
- Submission constraints:
  - allowed only when event state is `OPEN`
  - submission limits enforced
- Versioning:
  - multiple submissions per participant, latest counts or best counts (configurable per event).

### 7.5 Scoring & leaderboards
#### Authoritative scoring (server)
- Server computes official score for each submission.
- Scoring is deterministic given:
  - scoring module version
  - evaluation dataset version (if any)
  - submission payload/files
- Must support:
  - synchronous scoring for lightweight tasks
  - asynchronous scoring via internal DB queue for heavier tasks

#### Scoring modules
- Scoring logic packaged as:
  - a WASM module (recommended for determinism and portability), OR
  - a Python function (MVP fallback)
- If WASM:
  - executed server-side using a WASM runtime (e.g., wasmtime/wasmer)
  - time/memory limits enforced (best-effort)
- Client-side scoring (optional):
  - may run same WASM for preview
  - **never trusted** for leaderboard

#### Leaderboards
- Must support at least:
  - global leaderboard
  - per-track leaderboard (optional)
- Score structure:
  - numeric score (float/int)
  - optional breakdown (JSON)
  - status: `PENDING`, `SCORED`, `FAILED`, `DISQUALIFIED`
- Tie-breaking rules configurable:
  - earliest submission time
  - highest secondary metric
  - manual admin override (logged)

### 7.6 Email sending
Use cases:
- login code delivery
- optional notifications (submission received, scoring complete, event phase changes)

Requirements:
- SMTP integration.
- Email send must not block request path excessively:
  - either a background thread/task
  - or internal DB queue polled by worker loop

### 7.7 Exports & archival
Admin must be able to:
- generate export bundle at any time
- generate final export after event is `FINAL`
- optionally push export to GitHub repository

Export bundle must include:
- `manifest.json` (schema version, event metadata, timestamps, config snapshots)
- `participants.json`
- `teams.json` (if used)
- `agents.json` (if used)
- `submissions.json` (metadata; include file references)
- `scores.json` (official scores, breakdown)
- `audit_log.json`
- `assets/` (optional; thumbnails, static pages)

GitHub export (optional):
- Requires token with least privilege.
- Must support:
  - commit to a branch (e.g., `gh-pages` or `main:/docs`)
  - deterministic filenames (so Git diffs are meaningful)
- Must never export secrets.

### 7.8 Admin console
Admin UI must support:
- event configuration view (read-only if set by deployer)
- set event state (open/freeze/final/archive)
- manage participants (activate/deactivate, assign roles, create teams)
- view submissions and scoring statuses
- trigger re-score (if scoring module changes before final)
- trigger export + GitHub push
- view audit logs

### 7.9 API
Must expose REST (or REST-like) endpoints for:
- authentication (human)
- agent submissions
- leaderboard retrieval
- participant/team info
- export (admin only)

All endpoints must be documented (OpenAPI/Swagger preferred).

## 8. Non-Functional Requirements

### 8.1 Performance
- Target: handle up to ~100 concurrent users browsing/submitting.
- Must remain responsive during burst submission periods.
- DB writes must be kept small and transactions short.

### 8.2 Reliability
- Must recover gracefully from container restart if `/data` persistent.
- Must prevent SQLite "database is locked" errors by:
  - WAL mode
  - busy_timeout
  - short transactions
  - single app process writing (or careful threading)

### 8.3 Portability
- One container should run:
  - locally
  - on HF Spaces
  - on any single-node Docker host

### 8.4 Maintainability
- Clear schema versioning for JSON exports.
- Migrations strategy for SQLite (e.g., Alembic) or simple versioned migrations.

### 8.5 Privacy
- Collect minimal personal data (email, optional display name).
- Export should allow redaction settings:
  - optionally hash emails in public export
  - or export separate private admin archive

## 9. Suggested Data Model (Conceptual)

### Users (humans)
- `users(id, email, role, created_at, last_login_at)`

### Login codes
- `login_codes(id, email, code_hash, expires_at, used_at, request_ip)`

### Sessions (optional if not JWT)
- `sessions(id, user_id, expires_at, created_at)`

### Participants
- `participants(id, event_id, type, display_name, status, created_at)`
  - type: `human|agent|team`
  - status: `active|disabled|banned`

### Participant members
- `participant_members(id, participant_id, user_id NULL, agent_id NULL, role_in_team)`
  - role_in_team: `captain|member|agent`

### Agents
- `agents(id, name, owner_user_id NULL, api_key_hash, status, created_at)`

### Submissions
- `submissions(id, event_id, participant_id, title, description, payload_json, created_at, status)`
  - status: `received|queued|scored|failed|withdrawn`

### Files
- `files(id, submission_id, path, mime_type, size_bytes, sha256, created_at)`

### Scores
- `scores(id, submission_id, score_value, breakdown_json, scored_at, status, scorer_version)`
  - status: `pending|scored|failed|disqualified`

### Tasks (internal queue)
- `tasks(id, type, ref_id, status, attempts, available_at, last_error, created_at, updated_at)`
  - type: `send_email|score_submission|export_bundle|push_github`
  - status: `queued|running|done|failed`

### Audit log
- `audit_log(id, actor_user_id, action, target_type, target_id, metadata_json, created_at)`

## 10. User Flows

### 10.1 Deployer flow (Summon)
**Goal:** Deploy a single-container instance for an event and seed admins.

1. Choose hosting (HF Space or local Docker host).
2. Configure environment variables:
   - event metadata: id/title/type/start/end
   - storage paths: `/data/app.db`, `/data/uploads`
   - SMTP settings
   - admin seeding (seed emails or setup token)
   - optional GitHub export repo + token
3. Deploy container.
4. Verify health endpoint is OK.
5. (Optional) Enable HF persistent storage and confirm `/data` persists.
6. Provide the instance URL to admins and participants.

**Acceptance criteria**
- Instance starts without manual intervention.
- Admin can log in and open event.
- Data persists across restart if storage enabled.

---

### 10.2 Admin flow (Run the ritual)
**Goal:** Operate the event lifecycle and produce the final archive.

#### A) Prepare
1. Admin logs in via email code.
2. Admin accesses Admin Console.
3. Confirm event metadata and current state (`DRAFT`).
4. Configure rules (as allowed by deployer):
   - submission limits
   - leaderboard mode (best-of vs latest)
   - tracks/categories (optional)
   - agent policy (allowed/forbidden)
5. Create/approve initial participants or enable self-registration.
6. (Optional) Upload scoring module (WASM) and set scorer version.

#### B) Open (Gather → Create)
7. Switch event to `OPEN`.
8. Monitor participants, submissions, and scoring queue.
9. Moderate if needed:
   - disable participants
   - revoke agent keys
   - delete/withdraw submissions (policy-driven)
10. Handle bursts:
   - ensure scoring queue is progressing
   - increase worker concurrency cautiously (if supported)

#### C) Conclude
11. At deadline, set state to `FROZEN`:
   - stop new submissions
   - allow scoring backlog to finish
12. Resolve disputes / apply disqualifications (logged).
13. Trigger final recomputation if needed.
14. Set state to `FINAL`.

#### D) Archive
15. Trigger “Export Bundle”.
16. Review export preview (counts, schema version, redaction options).
17. Optionally “Push to GitHub”.
18. Set state to `ARCHIVED` (read-only).

**Acceptance criteria**
- Admin can manage event without shell access.
- Final leaderboard is reproducible from export.
- Export contains everything needed for a GitHub Pages archive.

---

### 10.3 Participant flow (Human)
**Goal:** Join, submit work, and see results.

1. Participant visits instance URL.
2. Enters email to log in.
3. Receives code; enters code.
4. Creates or joins participant identity:
   - choose display name
   - optionally create/join a team via invite code
5. Sees event dashboard:
   - event description, rules, timeline
   - submission limits and tracks
   - leaderboard (if enabled)
6. Creates submission:
   - title/description
   - upload images/artifacts (optional)
   - submit
7. Sees submission status:
   - received → queued → scored
8. Views official score and breakdown (if provided).
9. Iterates submissions until deadline.
10. After event finalises, views final results and archive link.

**Acceptance criteria**
- Login is frictionless and does not require password creation.
- Submission is straightforward and resilient under moderate load.
- Participant can always see official scoring status.

---

### 10.4 Participant flow (Agent/Bot)
**Goal:** Participate via API reliably and fairly.

1. Agent is created:
   - by admin, or by a human owner in UI (policy)
2. API key is issued (shown once).
3. Agent registers/associates with a Participant (agent or team).
4. Agent submits via API:
   - include metadata + payload JSON and/or artifact references
5. System returns:
   - submission id
   - current status
6. Agent polls status endpoint for scoring result.
7. Leaderboard reflects server score only.

**Acceptance criteria**
- API key authentication works consistently.
- Rate limits and submission caps are enforced.
- Agents cannot bypass server scoring.

## 11. Security Notes on Client-side WASM/WebGPU

- Any code/data shipped to the client can be inspected, extracted, and modified.
- Client-side scoring/validation can improve UX but cannot protect secrets or fairness.
- If using a public dataset for preview scoring, assume it will be leaked.
- Official scoring must remain server-side with private data or authoritative evaluation.

## 12. MVP Milestones

### MVP-1 (Core ritual capsule)
- Single-container app
- SQLite WAL + filesystem uploads
- Email code login
- Admin console: open/freeze/final/export
- Human participants + basic submissions
- Server-side scoring (simple function)
- JSON export download

### MVP-2 (Agents + queue)
- Agent API keys
- Submission API endpoints
- Internal tasks table worker loop
- Score queue (async)
- Rate limits + submission caps

### MVP-3 (WASM scoring parity)
- WASM scoring module executed server-side
- Optional client-side preview WASM
- scorer_version and deterministic export metadata

### MVP-4 (GitHub Pages export)
- Optional GitHub push
- Static summary generation (optional)
- Public/private export redaction modes

## 13. Open Questions (non-blocking)
- Do events require team formation by default or optional?
- Is voting/judging needed (separate from scoring)?
- Do we need tracks/categories in MVP?
- Should public export anonymize emails by default?

---

## Appendix A — Export Schema (Draft)

### manifest.json (example)
```json
{
  "schema_version": "1.0.0",
  "exported_at": "2026-02-18T12:00:00Z",
  "event": {
    "id": "hackritual-2026-bern",
    "title": "HackRitual Bern 2026",
    "type": "hackathon",
    "state": "FINAL",
    "start": "2026-03-01T09:00:00+01:00",
    "end": "2026-03-02T17:00:00+01:00"
  },
  "scoring": {
    "mode": "server_authoritative",
    "scorer_type": "wasm",
    "scorer_version": "sha256:....",
    "notes": "Client preview was enabled with public dev set."
  },
  "privacy": {
    "emails_exported": false,
    "participant_ids_stable": true
  }
}

Message crop.
```

## 14. Privacy-Respecting Statistics & Minimal Cookies

HackRitual is designed to be deployed temporarily and archived.  
It should collect **only what is strictly necessary** to operate the event.

This section defines how to gather useful operational statistics while remaining GDPR-compliant and privacy-minimal.

---

## 14.1 Privacy Principles

1. **Data minimisation** — collect only what is necessary to operate the event.
2. **No tracking for tracking’s sake** — no behavioural analytics, no profiling.
3. **No persistent identifiers beyond what is required for authentication.**
4. **No third-party analytics scripts.**
5. **No IP storage unless strictly required for security (and even then, truncated or hashed).**
6. **Statistics should be aggregate-only whenever possible.**

---

## 14.2 What Statistics Are Legitimate?

For a hackathon capsule, useful metrics include:

- Number of participants
- Number of teams
- Number of agent participants
- Number of submissions
- Submission timestamps (for activity histogram)
- Average scoring time
- Queue depth over time
- Login attempts (count only)
- Email sends (count only)
- Rate-limit triggers (count only)
- Page views (optional, aggregate only)

These are **operational metrics**, not user-tracking metrics.

---

## 14.3 What Must NOT Be Stored

By default, HackRitual must not store:

- Full IP addresses
- User agents for fingerprinting
- Referrer tracking
- Persistent tracking cookies
- Cross-session analytics identifiers
- Third-party analytics (Google Analytics, etc.)

---

## 14.4 IP Handling Policy

### Default Mode (Recommended)
- Do **not** store IP addresses in the database.
- Use IP only transiently for:
  - rate limiting
  - login abuse protection
- Do not log IP in application logs unless required for debugging.

### Optional Enhanced Abuse Protection
If rate limiting requires some record:

- Store only:
  - truncated IP (e.g., IPv4 /24, IPv6 /64), OR
  - salted hash of IP with daily-rotating salt.
- Automatically expire such entries (e.g., 24 hours).
- Never include IP data in export JSON.

This keeps abuse protection functional while avoiding personal data retention.

---

## 14.5 Aggregate Statistics Architecture

### Approach: Server-Side Event Counters

Instead of tracking users, maintain aggregated counters.

Example table:

metrics_daily (
date,
submissions_count,
logins_count,
agents_submissions_count,
email_sent_count,
rate_limit_triggered_count,
scoring_avg_ms,
scoring_max_ms
)


Increment counters at event-level only.
No per-user, per-IP analytics.

### For activity visualization:
- Use submission timestamps (already required for core logic).
- Generate histograms dynamically.
- Do not store additional tracking data.

---

## 14.6 Page View Metrics (Optional)

If lightweight page view statistics are desired:

- Increment a simple counter per route.
- Do not attach to user identity.
- Do not persist per-session identifiers.
- Do not track navigation paths.

Example:

page_views (
route,
count
)


This allows:
- “Leaderboard viewed 240 times”
- Without tracking who viewed it.

---

## 14.7 Email Metrics

Only store:

- Count of emails sent
- Success/failure state
- Timestamp

Do not store:
- SMTP response bodies
- Email content beyond what is operationally necessary

---

## 14.8 Export & Statistics

The exported JSON archive may include:

- Total participants
- Total submissions
- Event timeline
- Score distributions
- Activity histograms (derived, not raw logs)

It must NOT include:

- IP data
- Session identifiers
- Login attempt logs
- Rate-limit metadata tied to individuals

---

## 14.9 Cookies Policy (Minimalist Approach)

### Required Cookies

HackRitual needs only:

1. **Session Cookie** (JWT or session ID)
   - HTTP-only
   - Secure
   - SameSite=Lax or Strict
   - Short-lived (configurable)

No other cookies should be set by default.

### No Tracking Cookies
- No analytics cookies
- No marketing cookies
- No third-party cookies
- No fingerprinting

---

## 14.10 Do We Need a Cookie Banner?

### If HackRitual uses only:
- Strictly necessary session cookies
- No tracking
- No third-party analytics

Then:

Under EU GDPR & ePrivacy Directive:
- A cookie banner is generally **not required** for strictly necessary cookies.
- You still need a **Privacy Notice page** explaining:
  - what data is collected
  - why
  - how long it is stored
  - contact information

### Recommendation

Instead of a banner, include:

- A clear footer link: “Privacy”
- A concise privacy statement:

Example:

> HackRitual uses a single session cookie required for authentication.  
> No tracking, profiling, or third-party analytics are used.  
> Operational statistics are stored only in aggregate form.

If later you add analytics or optional tracking:
- Then a consent banner becomes required.

---

## 14.11 Privacy by Default Configuration

Default configuration should:

- Disable third-party scripts.
- Disable IP logging.
- Enable aggregate-only metrics.
- Set session cookies as:
  - HttpOnly
  - Secure
  - SameSite=Lax
- Rotate JWT signing key per deployment (recommended).
- Automatically purge expired login codes and session data.

---

## 14.12 Data Retention Policy

Since HackRitual is ephemeral by design:

- Active event data retained until export or deletion.
- Login codes auto-expire within minutes.
- Optional rate-limit IP hashes expire within 24 hours.
- Upon archival:
  - Admin may delete runtime DB.
  - Public export contains only curated structured data.

This aligns with the ritual model:
> Gather → Create → Conclude → Archive → Release.

---

## 14.13 Summary

HackRitual statistics model:

- No tracking.
- No personal analytics.
- No IP storage by default.
- Aggregate counters only.
- One strictly necessary session cookie.
- No banner required if no tracking is introduced.
- Clear privacy notice instead.

This preserves:
- GDPR compliance,
- user trust,
- and the philosophical coherence of a temporary collaborative ritual.

