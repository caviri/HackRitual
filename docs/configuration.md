# Configuration Reference

HackRitual is configured entirely through environment variables (loaded from the
process environment, or a `.env` file in local dev). Settings are validated at
startup — a missing required variable fails fast with a clear error rather than
crashing later. See `.env.example` in the repo root for a copy-paste template.

> One of `ADMIN_SEED_EMAILS` or `ADMIN_SETUP_TOKEN` **must** be set, or startup
> aborts (otherwise no one could ever become an admin).

## Required

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_BASE_URL` | Public URL of the instance (email links, CORS, secure-cookie detection) | `https://myevent.hf.space` |
| `JWT_SECRET` | Secret for signing JWTs. Must be stable across restarts. | `python3 -c "import secrets;print(secrets.token_hex(32))"` |
| `SMTP_HOST` | SMTP server hostname. `localhost`/`127.0.0.1`/`console` → dev mode (codes printed to stdout) | `smtp.gmail.com` |
| `SMTP_USER` | SMTP username | `noreply@example.com` |
| `SMTP_PASS` | SMTP password / app password | `xxxx-xxxx-xxxx-xxxx` |
| `SMTP_FROM` | Sender address | `noreply@example.com` |
| `EVENT_ID` | Unique event id (no spaces) | `hackritual-bern-2026` |
| `EVENT_TITLE` | Display title | `HackRitual Bern 2026` |
| `EVENT_START` | ISO 8601 start datetime | `2026-03-01T09:00:00+01:00` |
| `EVENT_END` | ISO 8601 end datetime | `2026-03-02T17:00:00+01:00` |
| **one of** `ADMIN_SEED_EMAILS` / `ADMIN_SETUP_TOKEN` | How the first admin is granted | see below |

## Admin seeding

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_SEED_EMAILS` | — | Comma-separated emails that receive the `admin` role on first login |
| `ADMIN_SETUP_TOKEN` | — | One-time token to claim admin via `/api/setup` |

## Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `/data/app.db` | SQLite database path |
| `UPLOAD_DIR` | `/data/uploads` | Upload directory |
| `EVENT_TYPE` | `hackathon` | Event type label |
| `SMTP_PORT` | `587` | SMTP port (587 STARTTLS, 465 TLS) |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL` |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` | Session lifetime (24 h) |
| `AUTO_TRANSITIONS` | `false` | Auto-advance DRAFT→OPEN at start, OPEN→FROZEN at end |
| `ENABLE_WORKER` | `true` | Run the in-process task queue worker + hourly cleanup sweep |
| `ENABLE_RATE_LIMIT` | `true` | Apply the IP/abuse rate-limit middleware (`X-RateLimit-*` headers) |
| `WASM_TIME_LIMIT_MS` | `5000` | WASM scorer time budget |
| `WASM_MEMORY_LIMIT_MB` | `64` | WASM scorer memory ceiling |
| `GITHUB_EXPORT_REPO` | — | `owner/repo` for the export push |
| `GITHUB_TOKEN` | — | GitHub PAT (Contents: read & write) for the push |
| `GITHUB_EXPORT_BRANCH` | `gh-pages` | Target branch for the export push |

## Notes

- **Secrets** (`JWT_SECRET`, `SMTP_PASS`, `GITHUB_TOKEN`) should be set as platform
  *secrets*, never committed. On Hugging Face Spaces, add them under
  Settings → Variables and Secrets as **Secrets**.
- **Dev SMTP**: set `SMTP_HOST=console` (or `localhost`) to skip real sending —
  login codes are printed to stdout. Handy for local runs and the test suite.
- **Rate limits** (when `ENABLE_RATE_LIMIT=true`): public 60/min per truncated IP,
  authenticated users 120/min, agents 60/min. `/api/health` is exempt.
- Inspect the resolved config (secrets masked) at runtime with
  `hackritual info` or `make info`.
