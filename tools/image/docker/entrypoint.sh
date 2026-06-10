#!/usr/bin/env bash
# =============================================================================
# HackRitual — Container entrypoint
#
# 1. Ensure /data directories exist
# 2. Run Alembic migrations (idempotent)
# 3. Start uvicorn
# =============================================================================

set -euo pipefail

log() { echo "[entrypoint] $*"; }

# ------------------------------------------------------------------ #
# 1. Storage directories
# ------------------------------------------------------------------ #
log "Ensuring data directories exist..."
mkdir -p /data/uploads

# Warn if /data is not a dedicated persistent mount (heuristic)
if grep -qsE '\s/data\s' /proc/mounts; then
  if grep -qsE '\s/data\s+tmpfs' /proc/mounts; then
    log "WARNING: /data is mounted as tmpfs — storage is EPHEMERAL. Data will be lost on restart."
    log "WARNING: Enable HF Spaces persistent storage to avoid data loss."
  else
    log "Persistent storage detected at /data."
  fi
else
  log "WARNING: /data has no dedicated mount — storage may be EPHEMERAL."
fi

# The app is written with absolute `app.*` imports; run everything from the
# backend package root so both Alembic and uvicorn resolve it.
export PYTHONPATH=/app/backend
cd /app/backend

# ------------------------------------------------------------------ #
# 2. Database migrations
# ------------------------------------------------------------------ #
log "Running Alembic migrations..."
alembic --config alembic.ini upgrade head || {
  log "ERROR: Alembic migrations failed. Aborting startup."
  exit 1
}

# ------------------------------------------------------------------ #
# 3. Start application
# ------------------------------------------------------------------ #
log "Starting uvicorn on 0.0.0.0:7860..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 7860 \
  --workers 1 \
  --no-access-log
