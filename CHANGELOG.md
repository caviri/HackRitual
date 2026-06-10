# Chronicle of HackRitual

All notable changes are inscribed here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed — no more email: admin-distributed access passwords (2026-06-10)

The platform no longer sends any email. Magic-link login is replaced by a
manual, keeper-driven credential flow:

- **Password-only login.** Each user holds one generated access password
  (`word-word-NNNN`) stored on the unique `users.access_password` column —
  the password alone identifies the user at `POST /api/auth/login`. Failed
  attempts are throttled per IP (10 / 15 min), which is what makes the
  password entropy sufficient. JWT cookie, refresh, `/me`, and the agent
  API-key flow are unchanged.
- **Public applications.** Anonymous visitors petition at `/apply/`
  (`POST /api/applications`). The keeper reviews the queue at
  `/admin/applications/`; approval mints the User and its password, and the
  panel offers **copy message** and **mailto** buttons — the keeper's own
  mail client does the sending.
- **CSV bulk import.** `POST /api/admin/users/import-csv` takes a
  `name,email,team,project` CSV and creates approved users with passwords;
  rows sharing a team are bound into one team participant. Duplicates are
  skipped and reported, bad rows collected without aborting the batch.
- **Admin bootstrap.** `ADMIN_SEED_EMAILS` + `ADMIN_PASSWORD` are now both
  required; the first seed address has its password re-synced from the env
  var on every boot (the lockout recovery path). The one-time
  `ADMIN_SETUP_TOKEN` / `/api/setup` flow is gone.
- **Removed.** SMTP settings and `aiosmtplib`, the email service and
  templates, phase-change and submission-received notices, email metrics,
  `GET /api/admin/email/metrics`, the `send_email` task type, the
  `login_codes` table, and the daily `email_sent_count` counter (Alembic
  migration `b8c9d0e1f2a3`).
- **Migration note.** Pre-existing users have no password until an admin
  hits *regenerate password* (`POST /api/admin/users/{id}/regenerate-password`)
  and delivers it.

### Added — frontend gap-closing: console wiring, submission form, auth gate (2026-06-10)

Closed the deferred Step 09/10 frontend remainders and fixed a broken admin path:

- **Fixed the admin state machine.** The console was POSTing to a dead
  `/api/event/transitions`; it now calls `/api/admin/event/state` (the real Step 06
  endpoint) via a typed `api.transitionState()`, refreshing the event after each
  move. Moving the ritual from the UI works again.
- **`AuthGuard`** (`components/auth-guard.tsx`) now wraps `/admin/*`. It checks
  `/api/auth/me` for an admin session and renders the console only for the keeper;
  a live backend with a non-admin/absent session is redirected to the gate. The
  static-export demo (no backend reachable) is let through deliberately.
- **`/submissions/new`** — a real submission-create form: pick an approved project,
  add title/description/result, post via the gated API. Surfaces the keeper's
  messages for the OPEN gate (403), the per-window cap (429), and missing auth (401).
  Linked from the submissions list.
- **MIT `LICENSE`** added (matching `pyproject.toml`); **README** rewritten leaner,
  now carrying the Hugging Face Spaces card frontmatter (`sdk: docker`,
  `app_port: 7860`) and a screenshot gallery.
- **Screenshots** captured from the static export via a version-matched Playwright
  container (`frontend/scripts/shots.mjs`) into `docs/screenshots/`.

Verified: `pnpm build` is green — 57 static pages, type-checked clean (was 56).

### Cleaned — pyflakes pass across the whole backend (2026-06-07)

Swept `app`, `scripts`, and `tests` to zero pyflakes (F) findings — removed ~34
dead imports/locals and fixed two genuine issues:

- `tests/test_users.py` had a **duplicate `test_update_role_success`** (the first
  was silently shadowed and never ran) — removed the duplicate
- `tests/test_scaffold.py` made a path-traversal request whose response was never
  asserted — now asserts it's blocked (stronger test)
- `app/services/auth.py` — corrected a stale `"LoginCodeRecord"` return annotation
  to `"LoginCode"` (added under `TYPE_CHECKING`)
- `docs/deployment.md` — fixed stale `uvicorn backend.app.main` / entrypoint
  references to match the corrected startup (`app.main:app` from `/app/backend`)

Re-verified the committed image cold-starts from a fresh volume (migrations →
worker → healthy). **284/284 tests still passing.**

### Validated — full autonomous hackathon on the live production stack (2026-06-07)

Built and ran the **production Docker image** for the first time and drove a full
hackathon against the live server (real migrations, queue worker, rate-limit
middleware, static frontend). An orchestrator (`backend/scripts/live_hackathon.py`)
played admin + human participants + an autonomous agent through the whole
lifecycle over HTTP. **21/21 checks passed**, plus live proof of rate limiting
(70-request burst → 52×200 / 18×429 with `Retry-After`) and the async worker
draining a 6-task rescore queue to `done`.

Fixed three genuine first-run bugs the live run surfaced (the container had never
actually been started before):

- **`.dockerignore`** — added; the build context was sending `frontend/node_modules` (with a Windows-unreadable pnpm symlink), failing the build
- **`docker/entrypoint.sh`** — was committed with CRLF line endings (`env: 'bash\r'`), so the shebang failed on Linux; converted to LF and added **`.gitattributes`** (`*.sh eol=lf`) to prevent recurrence
- **`docker/entrypoint.sh`** — Alembic ran from `/app` (script_location `alembic` → missing `/app/alembic`) and uvicorn used `backend.app.main`; now runs from `/app/backend` with `PYTHONPATH=/app/backend` and `app.main:app`, matching the code's absolute imports

These complete Step 01's previously-pending acceptance criteria (working
single-container build + run on port 7860).

### Bound — Step 20: Deployment Guide (2026-06-07)

The grimoire for those who summon it. Deployer, admin, and contributor docs —
written against the running system. **This completes the 20-step spec.**

- `docs/configuration.md` — full env-var reference (required, admin seeding, optional toggles, WASM, GitHub)
- `docs/development.md` — uv + docker-compose workflow, tests, migrations, Mailpit
- `docs/admin-guide.md` — the full event lifecycle over the real `/api/admin/*` surface
- `docs/agent-guide.md` — agent API with `ak_` keys, rate limits, curl + Python examples
- `CONTRIBUTING.md` — conventions, add-an-endpoint, migrations, PR definition-of-done
- `.env.example` — added `AUTO_TRANSITIONS`, `ENABLE_WORKER`, `ENABLE_RATE_LIMIT`, `WASM_*`, `GITHUB_EXPORT_BRANCH`
- `README.md` / `docs/index.md` — documentation tables refreshed

**280+ tests passing; all 20 spec steps addressed.**

### Bound — Step 19: API Documentation (2026-06-07)

The spellbook, complete. Every endpoint tagged and grouped, the description
covering auth, the state machine, and rate-limit headers — with a test that keeps
it honest.

- `backend/app/docs.py` — refreshed `API_DESCRIPTION` (rate-limit headers, corrected transition path, scoring/export); `OPENAPI_TAGS` now covers all 25 router tags, ordered; added `render_redoc_html`
- `backend/app/main.py` — `GET /api/redoc` (ReDoc) alongside the themed Swagger at `/api/docs`
- `backend/requirements.txt` — added `httpx` (used at import by the GitHub service since Step 17; was missing from prod deps)
- `docs/openapi.json` — committed spec snapshot (97 paths, 26 tags) for change tracking
- `backend/tests/test_openapi.py` — 4 new tests: spec valid + required catalog paths present + every operation tagged + every used tag declared + doc pages render. **284/284 total tests passing**

### Bound — Step 18: Privacy & Statistics (2026-06-07)

The ritual keeps a tally, never a dossier. Aggregate daily counters, an hourly
retention sweep, and a structured account of exactly what is and isn't collected.

- `backend/app/models/metrics_daily.py` + migration `a7b8c9d0e1f2` — one aggregate row per day
- `backend/app/services/metrics_service.py` — upserting daily counters, scoring avg/max, daily + totals reads; increments wired into login, submission, agent-submission, email, and scoring paths
- `backend/app/services/cleanup.py` + `main.py` — hourly sweep of expired login codes and sessions (§14.12)
- `backend/app/routers/metrics.py` — `GET /api/admin/metrics` (+ `/daily`: daily counters, totals, ephemeral in-memory metrics) and `GET /api/privacy` (structured data practices)
- `backend/tests/test_metrics.py` — 9 new tests (service upsert, scoring avg/max, dashboard, increment wiring, cleanup, privacy). **280/280 total tests passing**

Already in place from earlier steps: single session cookie, no trackers, hashed
login-code IPs, truncated in-memory rate-limit IPs, email-hashing export.

### Bound — MVP-4 Step 17: GitHub Export & Static Site (2026-06-07)

The record can outlive the container. The export archive — JSON plus a
self-contained static site — pushes to a GitHub repo for long-term archival and
Pages publishing, asynchronously and secret-scanned.

- `backend/app/services/github_service.py` — `push_export` via the Git Data API (blobs → tree → commit → ref; creates the branch if missing), `validate_no_secrets`, `check_access`; httpx client is injectable for testing
- `backend/app/services/static_site.py` — a minimal, CDN-free static site (index / leaderboard / participants / submissions + css) built from live data
- `backend/app/services/github_push.py` — orchestration (regenerate bundle + site → scan → push) and the in-memory push-status registry
- `backend/app/services/export_bundle.py` — `bundle_files()` shared by the ZIP and the push
- `backend/app/services/worker.py` — `push_github` task handler
- `backend/app/routers/exports.py` — `POST /api/admin/export/{id}/push-github` (async via the queue), `GET /api/admin/export/{id}/push-status`
- `backend/app/config.py` — `GITHUB_EXPORT_BRANCH` (default `gh-pages`)
- `backend/tests/test_github_export.py` — 9 new tests (secret scan, static site, push via `MockTransport` incl. branch-creation, endpoint config/queue/status, worker handler). **272/272 total tests passing**

### Bound — MVP-3 Step 16: WASM Scoring (2026-06-06)

The rubric can be carried in. Organizers upload a `.wasm` scorer, run server-side
under sandbox limits — deterministic, portable, replaceable without redeploying.

- `backend/app/scoring/wasm_scorer.py` — `WasmScorer` (lazy `wasmtime`; JSON over linear memory; memory limit + best-effort fuel time cap; failures become a `failed` score)
- `backend/app/services/wasm_store.py` — magic validation, content-addressed storage (`<data>/scoring/<sha>.wasm`), and the event's active-scorer reference
- `backend/app/services/scoring_service.py` — `get_scorer(db)` now selects the configured WASM module (cached by version) or the default Python scorer; auto-score uses it
- `backend/app/routers/scoring.py` — `POST /api/admin/scoring/upload-wasm` (validate + test-run + activate), `GET /api/admin/scoring/info`, `POST /api/admin/scoring/rescore-all` (via the task queue), `GET /api/scoring/preview-module`
- `backend/app/services/export_bundle.py` — manifest's scoring block reflects the active scorer (type + version)
- `backend/requirements.txt` — `wasmtime==25.0.0`
- `backend/tests/test_wasm_scoring.py` — 8 new tests (compiling a constant scorer from WAT): validation, runtime round-trip, upload→info→score, preview, rescore-all. **265/265 total tests passing**

Pending in Step 16: the browser-side preview runner (frontend) and a template Rust
scorer project.

### Bound — MVP-2 Step 15: Rate Limiting & Abuse Resistance (2026-06-06)

The wards against abuse. A sliding-window IP limiter stamps every API response,
an ephemeral blocklist answers a flood, and the Archivist gains the tools to act.
Completes MVP-2.

- `backend/app/middleware/rate_limit.py` — `SlidingWindowRateLimiter`, privacy-preserving IP truncation (/24, /64), an auto-expiring `IPBlocklist`, and `RateLimitMiddleware` (per-path keys: agent-key / session / IP; `429` + `Retry-After` + `X-RateLimit-*`)
- `backend/app/services/abuse_metrics.py` — aggregate daily rate-limit-trigger counts (no IPs, no users)
- `backend/app/routers/abuse.py` — `POST /api/admin/abuse/block-ip`, `GET /api/admin/abuse/stats`
- `backend/app/main.py`, `config.py` — middleware gated by `ENABLE_RATE_LIMIT` (default on); the test env disables it (and the worker) so the suite isn't throttled
- `backend/tests/test_rate_limit.py` — 12 new tests (limiter, IP truncation, blocklist, middleware 429/headers, health exemption, admin endpoints). **258/258 total tests passing**

This closes the Step 13 deferral: `/api/agent/*` is rate-limited per agent (by
API-key hash), with `X-RateLimit-*` headers. **MVP-2 backend is complete.**

### Bound — MVP-2 Step 14: Task Queue & Worker (2026-06-06)

A persistent, retryable queue — the SQLite `tasks` table as broker, a single
async worker draining it inside the same container. No Redis, no RabbitMQ.

- `backend/app/models/task.py` + migration `f6a7b8c9d0e1` — `payload_json`, `max_attempts`, `started_at`, `completed_at`
- `backend/app/services/task_queue.py` — enqueue, atomic-ish claim, mark done/failed (exponential backoff → `dead` at the ceiling), stale recovery, and the read-side summaries
- `backend/app/services/worker.py` — async handlers (`score_submission`, `send_email`, `export_bundle`) and the `Worker` poll loop
- `backend/app/main.py` — worker started from the lifespan (gated by `ENABLE_WORKER`, default on) with stale-task recovery; graceful shutdown
- `backend/app/routers/queue.py` — `GET /api/admin/queue/status|failed`, `POST /api/admin/queue/{id}/retry|purge`
- `backend/tests/test_task_queue.py` — 13 new tests (claim order/availability, async score-via-queue, retry→dead, unknown-type, stale recovery, admin endpoints); migration verified on a fresh DB. **249/249 total tests passing**

### Bound — MVP-2 Step 13: Agent System (2026-06-06)

The machines may compete. An agent is now a first-class participant: it holds an
API key, submits over its own endpoint, is scored under the same rules as a
human, and climbs the same leaderboard.

- `backend/app/services/agents.py` — get-or-create the agent's `agent`-type `Participant` + `ParticipantMember` (carrying `agent_id`); resolve it
- `backend/app/routers/agents.py` — `POST /api/agents` now gated by the event's `agent_policy`, links a participant, and audits; rotate/revoke audited; **new** admin `POST/GET /api/admin/agents` (create-on-behalf, list), and the key-authenticated agent API: `POST /api/agent/submissions`, `GET /api/agent/submissions/{id}` (status + score), `GET /api/agent/leaderboard`
- `backend/app/services/submissions.py` — `participant_ids_for_actor` now resolves agents, so `/mine`, withdraw, and file ops work for agent callers
- `backend/app/schemas/agents.py` — `AgentAdminCreate`, `AgentSubmissionCreate`, `AgentSubmissionStatus`
- `backend/app/services/ritual_sim.py` — `scout-bot` is summoned and submits over the agent API
- `backend/tests/test_agents.py` — 9 new tests (policy gate, key auth, revocation, submit+score, leaderboard, admin create). **239/239 total tests passing**

Deferred to Step 15: agent-specific rate limits and `X-RateLimit-*` headers.

### Bound — Step 07 completion: Submission files (2026-06-06)

The forge accepts evidence. Files attach to submissions, live on disk, and are
handed back only through a gated endpoint — never the static mount.

- `backend/app/routers/projects.py` — `POST /api/submissions/{id}/files` (owner, OPEN, MIME allowlist + 10 MB cap, SHA-256 via `utils.files.save_upload`), `GET /{id}/files` (public metadata), `GET /{id}/files/{fid}` (owner/admin streaming download), `DELETE /{id}/files/{fid}`
- `backend/app/schemas/projects.py` — `SubmissionFileResponse`
- `backend/app/services/ritual_sim.py` — the team attaches `report.md` to its sealed offering
- `backend/tests/test_submission_files.py` — 8 new tests (attach/validate, list, owner/admin download, delete). **231/231 total tests passing**

This closes Step 07: the submission system is now spec-complete.

### Bound — MVP-1 Step 10: Frontend Foundation (2026-06-05)

The Next.js app — already substantial — verified building as a static export, and
the gaps against the newer backend filled.

- `frontend/src/lib/api.ts` — `leaderboard()` plus `LeaderboardDTO` / entry / participant types, wired to the Step 08 endpoint
- `frontend/src/app/leaderboard/page.tsx` — the public leaderboard: ranked table, 30-second auto-refresh while OPEN, the signed-in user's row highlighted, a "final results" banner once FINAL/ARCHIVED
- `frontend/src/app/privacy/page.tsx` — the privacy notice (§14.10): one session cookie, no tracking, export email-hashing, content-free logging
- `frontend/src/components/nav.tsx`, `footer.tsx` — links to the new pages
- Verified: `pnpm build` produces a clean static export in Docker (node:20-alpine); `/leaderboard` and `/privacy` emit static HTML; the whole app type-checks

### Bound — MVP-1 Step 09: Admin Console (backend slice) (2026-06-05)

The operator's view of the ritual — read-only roll-ups the `/admin/*` console
will draw from. (The Next.js UI itself awaits the frontend foundation, Step 10.)

- `backend/app/services/admin_console.py` — `dashboard` (event state, headline metrics, recent audit), `scoring_status` (scorer identity, status counts, value histogram), `audit_query` (filter by action/actor/since, paginated)
- `backend/app/routers/admin.py` — `GET /api/admin/dashboard`, `GET /api/admin/scoring/status`, `GET /api/admin/audit`
- `backend/app/services/ritual_sim.py` — the Archivist consults the dashboard before judging (`6 gathered, 5 offerings, 0 awaiting a score`)
- `backend/tests/test_admin_console.py` — 7 new tests (auth, dashboard/scoring/audit shapes, audit filter + pagination). **224/224 total tests passing**

The rest of the console's data is already served by `/api/admin/*` endpoints from
Steps 04–08, 11, and 12 — so the surface is complete; only the UI is pending.

### Bound — MVP-1 Step 12: Email System (2026-06-05)

The ritual now speaks of its own accord. Beyond the login code (Step 03), it sends
notices when a phase advances and when an offering is received — and keeps a
content-free tally of what it sent.

- `backend/app/services/email_metrics.py` — aggregate counters (sent / succeeded / failed / last-sent); no addresses, no bodies
- `backend/app/services/email.py` — a generic `send_email` (console-safe, metric-recording); the SMTP path now logs a recipient *hash*, never the address
- `backend/app/services/notifications.py` — templates (phase-change, submission-received, score-available) with HTML + text, recipient resolution, and `notify_*` helpers that schedule sends onto `BackgroundTasks`
- `backend/app/routers/event.py`, `routers/projects.py` — phase-change notices on transition; submission-received notices on create (non-blocking)
- `backend/app/routers/email.py` — `GET /api/admin/email/metrics`
- `backend/app/services/ritual_sim.py` — reports `notices sent` (~22 over a full run)
- `backend/tests/test_email.py` — 10 new tests (templates, metrics, console dispatch, recipient resolution, admin endpoint, no-address-in-logs). **217/217 total tests passing**

### Bound — MVP-1 Step 11: JSON Export (2026-06-05)

The ritual leaves an artefact. A curated, redacted, deterministic ZIP of
structured JSON — the record made portable, fit to publish or keep. Distinct from
the full SQLite backup (`/api/export.zip`), which remains for restore.

- `backend/app/services/export_bundle.py` — `RedactionConfig` (public/private/full), stable irreversible email hashing (`sha256(email+event_id)[:16]`), per-entity exporters (participants, teams, agents, submissions, scores, audit_log, statistics), `manifest.json`, and `build_bundle`/`preview`. Sorted by id for reproducibility; secrets (api-key hashes, config) never enter
- `backend/app/routers/exports.py` — admin `GET /api/admin/export/preview`, `POST /api/admin/export` (synchronous), `GET /api/admin/export/{id}/download` (streams the ZIP)
- `backend/app/schemas/export.py` — request/preview/generate schemas
- `backend/app/services/ritual_sim.py` — final phase `phase_export` ("Export the artefact") previews, generates, and downloads the bundle, completing the ritual's tagline
- `backend/tests/test_export.py` — 9 new tests (contents, email redaction, no-secrets, determinism, endpoints); `test_health` made hermetic re: event state. **208/208 total tests passing**

### Bound — MVP-1 Step 08: Scoring & Leaderboards (2026-06-05)

The offerings are weighed. A server-authoritative scorer runs the moment work is
offered, a leaderboard ranks the gathered, and the Archivist may lift or strike a
score by hand — every adjustment inscribed in the record.

- `backend/app/scoring/` — the scorer contract (`BaseScorer`, `ScoreResult`) and `DefaultScorer`, a completeness rubric (`version="default-1.0"`); abstract enough to later serve the async queue (MVP-2) and WASM (MVP-3)
- `backend/app/services/scoring_service.py` — synchronous `score_submission` (upserts one row per submission+scorer) and `active_score`
- `backend/app/services/leaderboard.py` — `build_leaderboard` with `best`/`latest` modes, earliest-activity tie-break, and exclusion of withdrawn/disqualified work
- `backend/app/routers/scores.py` — `GET /api/submissions/{id}/score`, `GET /api/leaderboard`, admin `POST /api/admin/submissions/{id}/rescore` and `PATCH /api/admin/scores/{id}` (both audited)
- `backend/app/routers/projects.py` — submissions are auto-scored on creation when the event's `auto_score` config is on (default)
- `backend/app/services/event.py`, `schemas/event.py` — `auto_score` added to event config
- `backend/app/services/ritual_sim.py` — new `phase_score` ("Weigh the offerings") reads the leaderboard, applies an override, and shows the reshaped standing
- `backend/tests/test_scoring.py` — 10 new tests; **200/200 total tests passing**

### Bound — MVP-1 Step 07: Submission System (2026-06-05)

The forge accepts work — but only on the ritual's terms. Offerings are taken only
while the event is OPEN, capped per participant over a rolling window, withdrawn
only by their owners while the gates still stand, and moderated by the Archivist
with a trail. Built atop the existing versioned project+participant model.

- `backend/app/services/submissions.py` — `require_open` (ties Step 07 to the Step 06 `EventGuard`), `enforce_submission_limit` (per-participant rolling window from event config → `429`), and the actor→participant ownership map
- `backend/app/routers/projects.py` — `POST /api/submissions` now gated on OPEN + participant-active + limits; new `GET /api/submissions/mine`, `POST /api/submissions/{id}/withdraw` (owner, OPEN only), and an admin router: `GET /api/admin/submissions` (filter/paginate), `GET /api/admin/submissions/{id}`, `PATCH /api/admin/submissions/{id}/status` (audited)
- `backend/app/schemas/projects.py` — `SubmissionStatusUpdate`, `SubmissionListResponse`
- `backend/app/services/ritual_sim.py` — `phase_forge` now proposes projects and offers work over the API; proves the submission cap (429) and the FROZEN forge-shut ward
- `backend/tests/test_submissions.py` — 9 new tests; **190/190 total tests passing**

Deferred within Step 07 (paired with Step 08): generic multipart upload on create
+ a controlled download endpoint, and latest/best leaderboard selection.

### Bound — MVP-1 Step 06: Event Lifecycle (2026-06-05)

The ritual now knows its own shape. The single event advances through five states
in a fixed order, and each state gates what the rest of the platform may do. There
is one sanctioned reversal — the reopen — and it must be asked for by name.

- `backend/app/services/event.py` — the state machine (`DRAFT → OPEN → FROZEN → FINAL → ARCHIVED`), the `FROZEN → OPEN` reopen requiring `confirm=true`, configuration defaults and merge, the `EventGuard` (`require_state`, `can_submit`/`can_register`/`can_score`/`can_export`/`is_read_only`) with the `get_event_guard` dependency, and the pure `next_auto_state` decision function
- `backend/app/routers/event.py` — `GET /api/event` (public), `POST /api/admin/event/state`, `PATCH /api/admin/event/config` (DRAFT/OPEN only; `leaderboard_mode` locked once OPEN), `GET /api/admin/event/audit`; every transition and config edit recorded in the audit log with actor and reason
- `backend/app/schemas/event.py` — `EventConfig`, `EventResponse` (now carries `config`), `StateTransitionRequest`/`StateTransitionResponse`, `EventConfigUpdate`, `AuditEntry`
- `backend/app/main.py` — optional auto-transition background task, gated by `AUTO_TRANSITIONS`, advancing the ritual on its clock (start → OPEN, end → FROZEN)
- `backend/app/config.py` — `AUTO_TRANSITIONS` setting (default off)
- `docker-compose.yml` — added a `test` service so the suite runs in a container (`docker compose run --rm test`); removed the obsolete `version` key
- `backend/tests/test_event.py` — 19 new tests; **179/179 total tests passing**

### Summoned — The Rite of Many Hands: a ritual simulator (2026-06-05)

A test tool that summons a cast of human and machine agents and drives a single
event through its whole lifecycle over the real REST API — the gathered register,
teams form by invite, the state-machine wards refuse what each state forbids, and
the chronicle is read back at the end.

- `backend/app/services/ritual_sim.py` — the orchestrator: an `Agent` cast, a data-driven phase coordinator (`PHASES`), bearer-token auth (the agent access path), and a `RitualReport` of what happened. Runnable as `python -m app.services.ritual_sim`
- `backend/app/cli.py` — `hackritual simulate` command with narrated, styled output and a summary table; added a `python -m app.cli` entry point
- `docker-compose.yml` — a `sim` service (`docker compose run --rm sim`) that runs the simulator self-contained, no `.env` needed
- `backend/tests/test_ritual_sim.py` — 2 end-to-end smoke tests; **181/181 total tests passing**

### Bound — MVP-1 Step 03: Authentication (2026-03-06)

The gates are bound. A bearer presents their email; a six-digit code arrives by post;
the code is exchanged for a signed token sealed in a cookie. The session persists until
the bearer dissolves it or the seal expires.

- `backend/app/services/auth.py` — 6-digit code generation (`secrets.randbelow`), SHA-256 hashing, LoginCode CRUD with expiry and single-use enforcement, `get_or_create_user` on first login, JWT creation/decoding via `python-jose`, in-memory rate limiter (3/email, 10/IP per 15 min; 5 verify attempts)
- `backend/app/services/email.py` — async SMTP dispatch via `aiosmtplib`; console/dev mode when `SMTP_HOST` is `localhost`; HTML + plain text login code templates
- `backend/app/schemas/auth.py` — Pydantic models for all auth endpoints; simple regex email validation (per spec §12.5)
- `backend/app/middleware/auth.py` — `get_current_user`, `require_admin`, `require_role` FastAPI dependencies
- `backend/app/routers/auth.py` — 5 endpoints: `POST /api/auth/request-code`, `POST /api/auth/verify-code`, `POST /api/auth/logout`, `POST /api/auth/refresh`, `GET /api/auth/me`
- `requirements.txt` — added `email-validator==2.2.0`
- `backend/tests/test_auth.py` — 36 new tests; **73/73 total tests passing**

---

### Bound — MVP-1 Step 02: Database Layer (2026-03-06)

The schema is inscribed. The SQLite stone is carved with 12 tables, all relationships
sealed with foreign keys, WAL mode lit for concurrent reads. The entity graph is complete:
users, sessions, login codes, participants, teams, agents, submissions, files, scores,
tasks, audit logs, and the event record itself.

- `backend/app/database.py` — SQLAlchemy engine with WAL mode, `busy_timeout=5000`, FK enforcement; `SessionLocal` factory; `check_db()` heartbeat probe
- `backend/app/models/` — 11 model files covering the full data model from specs §9: `User`, `LoginCode`, `Session`, `Participant`, `ParticipantMember`, `Agent`, `Submission`, `File`, `Score`, `Task`, `AuditLog`, `Event`
- `backend/app/models/__init__.py` — collects all models so Alembic autogenerate sees the full schema
- `backend/alembic/versions/4801ca88b7f6_initial_schema.py` — initial migration: all 12 tables, all indexes, all FK constraints
- `backend/alembic/env.py` — wired to `Base.metadata`; `render_as_batch=True` for SQLite-safe schema evolution
- `backend/app/utils/files.py` — `save_upload`, `get_upload_path`, `delete_upload`; SHA-256 integrity on every upload; stored at `<UPLOAD_DIR>/<event_id>/<participant_id>/<submission_id>/`
- `backend/app/main.py` — lifespan seeds the `Event` record from env vars and admin `User` rows from `ADMIN_SEED_EMAILS` on first invocation (idempotent)
- `backend/app/routers/health.py` — `GET /api/health` now reads real `event_state` from the `Event` table
- `backend/tests/test_database.py` — 23 new tests covering pragmas, all model CRUD, file utilities, seeding logic, health integration; **37/37 total tests passing**

---

### Bound — MVP-1 Step 01: Project Setup & Docker (2026-03-06)

The circle is drawn. The container skeleton stands. The health endpoint breathes.

- Repository directory structure: `backend/`, `frontend/`, `docker/`, `specs/`
- `backend/app/main.py` — FastAPI app factory with lifespan, CORS, static file serving
- `backend/app/config.py` — Pydantic `BaseSettings` for all 17 env vars; fail-fast validation
- `backend/app/utils/logging.py` — JSON structured logging to stdout; `LOG_LEVEL` configurable
- `backend/app/routers/health.py` — `GET /api/health` with DB ping and persistent storage heuristic
- `docker/Dockerfile` — multi-stage build (Node 20 Alpine → Python 3.11-slim); port 7860
- `docker/entrypoint.sh` — creates `/data` dirs, runs Alembic migrations, starts uvicorn
- `docker-compose.yml` — local dev with volume mounts for hot-reload
- `.env.example` — documented template for all environment variables
- `backend/requirements.txt` + `backend/requirements-dev.txt`
- `backend/alembic/` — migration scaffolding wired to `DB_PATH` env var
- `backend/tests/` — 14 tests covering config validation, health endpoint, JSON logging; **14/14 passing**

---

<!-- Future rituals will be inscribed above this line -->
