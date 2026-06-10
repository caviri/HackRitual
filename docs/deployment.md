# Deployment Guide

HackRitual is designed to be deployed in minutes with a single Docker container.

---

## Option A — Hugging Face Spaces (recommended)

HF Spaces provides a free Docker runtime with optional persistent storage.

### Steps

1. **Create a new Space**
   - Go to huggingface.co → New Space
   - SDK: **Docker**
   - Hardware: CPU Basic (free tier) is sufficient for ~100 participants

2. **Enable Persistent Storage** *(strongly recommended)*
   - Space Settings → Persistent storage → Enable
   - This mounts a volume at `/data`
   - Without it, all data is lost on each restart

3. **Set environment variables** (Space Settings → Repository secrets / Variables)

   ```
   APP_BASE_URL        = https://<your-space>.hf.space
   JWT_SECRET          = <generate: python3 -c "import secrets; print(secrets.token_hex(32))">
   ADMIN_SEED_EMAILS   = you@example.com
   SMTP_HOST           = smtp.sendgrid.net  (or your provider)
   SMTP_PORT           = 587
   SMTP_USER           = apikey
   SMTP_PASS           = <your SMTP password>
   SMTP_FROM           = hackritual@yourdomain.com
   EVENT_ID            = my-hackathon-2026
   EVENT_TITLE         = My Hackathon 2026
   EVENT_TYPE          = hackathon
   EVENT_START         = 2026-04-01T09:00:00+02:00
   EVENT_END           = 2026-04-02T17:00:00+02:00
   ```

4. **Deploy**
   - Push the repository to your HF Space (the `.github/workflows/sync-to-hf.yml`
     action mirrors GitHub → HF on every push to `main`)
   - HF builds the `Dockerfile` at the repo root. The sync workflow stages it
     there from `tools/image/docker/Dockerfile`; the README frontmatter
     (`sdk: docker`, `app_port: 7860`) tells HF how to run it
   - Port `7860` is exposed automatically

5. **Verify**
   ```
   curl https://<your-space>.hf.space/api/health
   ```
   Expected:
   ```json
   {
     "status": "ok",
     "persistent_storage": true,
     "db_ok": true,
     "event_state": "DRAFT"
   }
   ```

6. **Admin login**
   - Visit `https://<your-space>.hf.space`
   - Enter your `ADMIN_SEED_EMAILS` address
   - Receive login code in email → enter it → admin session active

---

## Option B — Local Docker

```bash
# 1. Clone the repo
git clone <repo-url>
cd HackRitual

# 2. Configure environment
cp .env.example .env
# Edit .env with your values

# 3. Create local data directory
mkdir -p data

# 4. Build and run
docker build -f tools/image/docker/Dockerfile -t hackritual .
docker run -p 7860:7860 \
  --env-file .env \
  -v $(pwd)/data:/data \
  hackritual

# 5. Verify
curl http://localhost:7860/api/health
```

---

## Option C — docker-compose (local development)

```bash
cp .env.example .env
# Edit .env

docker compose -f tools/image/docker/docker-compose.yml up --build
```

The compose file mounts `src/backend` for hot-reload.
Run `cd src/frontend && pnpm dev` separately for frontend hot-reload on port 3000.

---

## Option D — Run without Docker (devcontainer)

Useful for development and running tests:

```bash
# Install backend deps
pip install -r src/backend/requirements-dev.txt

# Copy and fill in .env
cp .env.example .env

# Run migrations (creates DB at DB_PATH)
cd src/backend && alembic upgrade head

# Start server (from backend/, where the app's absolute `app.*` imports resolve)
uvicorn app.main:app --reload --port 7860
# — or, the friendlier wrapper —
uv run hackritual serve --reload
```

---

## Startup Sequence

```
entrypoint.sh
  │
  ├─ mkdir -p /data/uploads
  │
  ├─ Check /proc/mounts for /data persistence
  │    └─ If tmpfs → log WARNING (ephemeral)
  │
  ├─ cd /app/backend ; export PYTHONPATH=/app/backend
  │
  ├─ alembic --config alembic.ini upgrade head
  │    ├─ Creates app.db if not exists
  │    └─ Applies any pending migrations
  │
  └─ uvicorn app.main:app --port 7860
       │
       └─ lifespan startup
            ├─ Logging configured (JSON → stdout)
            ├─ Settings loaded and validated
            └─ (Step 02+) DB engine initialised, WAL mode set
```

---

## Health Check

```
GET /api/health
```

| Field | Description |
|-------|-------------|
| `status` | `"ok"` if server is running |
| `version` | App version |
| `event_id` | Configured event ID |
| `event_state` | Current ritual state |
| `persistent_storage` | `true` if `/data` is a non-tmpfs mount |
| `db_ok` | `true` if SQLite responds to a query |

If `persistent_storage: false`, data will be lost on restart.
Set up persistent storage before opening the event to participants.

---

## Teardown

After the event is `ARCHIVED`:

1. Download or push the export bundle (`POST /api/admin/export`)
2. Verify the export is complete
3. Remove the HF Space (or stop the container)

The export bundle is a self-contained JSON archive — no server needed to read it.

---

## Environment Variable Reference

See `.env.example` for the full annotated list.

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `APP_BASE_URL` | Yes | — | Public URL; used in email links |
| `JWT_SECRET` | Yes | — | Must be stable; rotate = all sessions invalidated |
| `ADMIN_SEED_EMAILS` | One of | — | Comma-separated admin emails |
| `ADMIN_SETUP_TOKEN` | One of | — | One-time claim token |
| `SMTP_*` | Yes | — | Required for email login codes |
| `EVENT_ID` | Yes | — | Unique slug (used in export filenames) |
| `EVENT_TITLE` | Yes | — | Human-readable name |
| `EVENT_START/END` | Yes | — | ISO 8601 datetimes |
| `DB_PATH` | No | `/data/app.db` | SQLite file location |
| `UPLOAD_DIR` | No | `/data/uploads` | File upload root |
| `LOG_LEVEL` | No | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `GITHUB_EXPORT_REPO` | No | — | `owner/repo` for optional export push |
| `GITHUB_TOKEN` | No | — | PAT with repo write access |
