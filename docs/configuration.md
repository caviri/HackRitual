# Configuration Reference

HackRitual is configured entirely through environment variables (loaded from the
process environment, or a `.env` file in local dev). Settings are validated at
startup — a missing required variable fails fast with a clear error rather than
crashing later. See `.env.example` in the repo root for a copy-paste template.

> `ADMIN_SEED_EMAILS` and `ADMIN_PASSWORD` **must** both be set, or startup
> aborts (otherwise no one could ever log in).

## Required

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_BASE_URL` | Public URL of the instance (CORS, secure-cookie detection) | `https://myevent.hf.space` |
| `JWT_SECRET` | Secret for signing JWTs. Must be stable across restarts. | `python3 -c "import secrets;print(secrets.token_hex(32))"` |
| `ADMIN_SEED_EMAILS` | Comma-separated admin emails; the first is the primary admin | `you@example.com` |
| `ADMIN_PASSWORD` | The primary admin's login password (min 8 chars) | `a-long-strong-phrase` |

## Admin seeding

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_SEED_EMAILS` | — | Comma-separated emails that hold the `admin` role. The **first** address is the primary admin: its access password is re-synced to `ADMIN_PASSWORD` on every startup (the lockout recovery path). Other seed admins get a generated password, visible in the admin users list. |
| `ADMIN_PASSWORD` | — | Login password for the primary admin |

## Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_ID` | `hackritual-event` | Unique event id (no spaces). Seeds the event record on first boot. |
| `EVENT_TITLE` | `HackRitual` | Display title — editable afterwards in the admin panel ("event identity"). |
| `EVENT_START` | placeholder (2030) | ISO 8601 start — editable in the admin panel. |
| `EVENT_END` | placeholder (2030) | ISO 8601 end — editable in the admin panel. |
| `DB_PATH` | `/data/app.db` | SQLite database path |
| `UPLOAD_DIR` | `/data/uploads` | Upload directory |
| `EVENT_TYPE` | `hackathon` | Event type label |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL` |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` | Session lifetime (24 h) |
| `AUTO_TRANSITIONS` | `false` | Auto-advance DRAFT→OPEN at start, OPEN→FROZEN at end |
| `ENABLE_WORKER` | `true` | Run the in-process task queue worker + hourly cleanup sweep |
| `ENABLE_RATE_LIMIT` | `true` | Apply the IP/abuse rate-limit middleware (`X-RateLimit-*` headers) |
| `DEMO_STAGES` | `false` | Demo mode: serve each event stage from its own writable SQLite snapshot under `<data>/demo/`, flipped per visitor via the stage bar. For showing the ritual, not running one — see [Demo mode](demo-mode.md). |
| `WASM_TIME_LIMIT_MS` | `5000` | WASM scorer time budget |
| `WASM_MEMORY_LIMIT_MB` | `64` | WASM scorer memory ceiling |
| `GITHUB_EXPORT_REPO` | — | `owner/repo` for the export push |
| `GITHUB_TOKEN` | — | GitHub PAT (Contents: read & write) for the push |
| `GITHUB_EXPORT_BRANCH` | `gh-pages` | Target branch for the export push |

## Notes

- **Secrets** (`JWT_SECRET`, `ADMIN_PASSWORD`, `GITHUB_TOKEN`) should be set as
  platform *secrets*, never committed. On Hugging Face Spaces, add them under
  Settings → Variables and Secrets as **Secrets**.
- **`UPLOAD_DIR` is served publicly** at `/uploads`. Startup refuses any
  configuration where `DB_PATH` lies inside `UPLOAD_DIR` — that would make the
  SQLite file (which holds plaintext access passwords) downloadable.
- **Rate limits** (when `ENABLE_RATE_LIMIT=true`): public 60/min per truncated IP,
  authenticated users 120/min, agents 60/min. `/api/health` is exempt.
- Inspect the resolved config (secrets masked) at runtime with
  `hackritual info` or `make info`.
