# HackRitual — Risks & Mitigations

This file tracks known technical risks, their likelihood/impact, and planned mitigations.

Scale: Likelihood and Impact rated Low / Medium / High.

---

## MVP-1 Risks

### R-01 — SQLite contention under burst load
**Likelihood:** Medium | **Impact:** High
**Description:** SQLite with concurrent writers can produce "database is locked" errors under burst submission periods (~100 concurrent users).
**Mitigation:**
- Enable WAL mode (`PRAGMA journal_mode=WAL`) and `PRAGMA busy_timeout=5000` on every connection open.
- Keep write transactions short and atomic.
- Use a single uvicorn worker process initially; scale with caution.
- Monitor via health endpoint DB check.

**Status:** To be addressed in Step 02 (Database Layer).

---

### R-02 — HF Spaces ephemeral storage
**Likelihood:** Medium | **Impact:** High
**Description:** If `/data` is not a persistent volume, all event data is lost on container restart.
**Mitigation:**
- Health endpoint explicitly checks and reports `persistent_storage: true/false`.
- Startup logs a prominent `WARNING` if storage is ephemeral.
- Admin UI to surface the warning to operators.
- Instruct deployers to enable HF persistent storage in deployment guide.

**Status:** Addressed in Step 01 (health endpoint check).

---

### R-03 — JWT secret rotation / loss
**Likelihood:** Low | **Impact:** High
**Description:** If `JWT_SECRET` is not persisted between deployments, all sessions are invalidated on restart.
**Mitigation:**
- Document that `JWT_SECRET` must be set as a stable env var, not auto-generated at runtime.
- Startup validation fails fast if `JWT_SECRET` is absent.

**Status:** Addressed in Step 01 (config validation) and Step 03 (Auth).

---

### R-04 — Next.js static export limitations
**Likelihood:** Low | **Impact:** Medium
**Description:** `output: 'export'` in Next.js disables server-side rendering, dynamic routes, and API routes. All dynamic data must come from the FastAPI backend.
**Mitigation:**
- Design frontend as a pure SPA/static shell; all data fetched from `/api/*`.
- Validate this constraint early (Step 10) before building complex Next.js pages.
- Use Next.js App Router with `'use client'` for interactive components.

**Status:** Decision logged; to be confirmed in Step 10.

---

### R-05 — SMTP blocking the request path
**Likelihood:** Medium | **Impact:** Medium
**Description:** Synchronous SMTP sending during login code requests could time out or slow down the auth flow.
**Mitigation:**
- Send emails via `asyncio` background task (FastAPI `BackgroundTasks`) in MVP-1.
- Move to the internal task queue (Step 14) in MVP-2 for reliability.
- Set a short SMTP connection timeout (e.g., 10s) to avoid hanging requests.

**Status:** To be addressed in Step 12 (Email System).

---

### R-06 — Port conflict (7860)
**Likelihood:** Low | **Impact:** Low
**Description:** Local dev environment may have port 7860 in use. The devcontainer already runs an HTTP server on port 8000.
**Mitigation:**
- `docker-compose.yml` maps 7860 → 7860; developers can override with env var.
- Document alternative port usage in README.

**Status:** Low priority; note in README.

---

### R-07 — Container startup time exceeding 30s on HF Spaces
**Likelihood:** Low | **Impact:** Medium
**Description:** If the production image is large or startup tasks are slow, HF Spaces may time out the health check.
**Mitigation:**
- Use `python:3.11-slim` base image to minimise size.
- Run `pip install --no-cache-dir` to avoid caching bloat.
- Alembic migrations must be fast (idempotent upgrade head).
- Target image size < 500 MB.

**Status:** To be validated once Dockerfile is built.

---

### R-08 — Client-side WASM scoring trusted as authoritative
**Likelihood:** Low | **Impact:** High
**Description:** By design, client-side scoring must never feed the official leaderboard, but a mistake in frontend code could surface client scores as official.
**Mitigation:**
- Leaderboard reads only from `scores` table, which is exclusively written by server-side scorer.
- Client-side WASM preview (MVP-3) renders a clearly labelled "preview" score only.
- Security review checklist before MVP-3 ships.

**Status:** Architectural constraint; enforced in Step 08 and Step 16.

---

## Cross-Cutting Risks

### R-09 — Secrets in export bundle
**Likelihood:** Low | **Impact:** High
**Description:** Export JSON must never include JWT secrets, SMTP credentials, API keys, or IP data.
**Mitigation:**
- Export service has an explicit allowlist of fields per entity.
- Automated test checks that known secret field names are absent from all export files.
- Privacy redaction options for emails (Step 18).

**Status:** To be addressed in Step 11 (JSON Export) and Step 18 (Privacy).

---

### R-10 — Agent API key leakage
**Likelihood:** Low | **Impact:** Medium
**Description:** Agent API keys stored in DB must be hashed; plain-text keys must only be shown once at creation.
**Mitigation:**
- Store `api_key_hash` (bcrypt or SHA-256 with salt) in DB; never store plaintext.
- Return the plaintext key once at creation; thereafter only the masked prefix.
- Keys are revocable by admin at any time.

**Status:** To be addressed in Step 13 (Agent System).

---

*Last updated: 2026-03-06*
