# =============================================================================
# HackRitual — Multi-stage Docker build
#
# Stage 1: Build Next.js frontend (static export) with pnpm
# Stage 2: Production Python image with uv, serving backend + static frontend
#
# Target deploy: Hugging Face Spaces (port 7860).
#
# Build context is the REPOSITORY ROOT (paths below are root-relative):
#   docker build -f tools/image/docker/Dockerfile -t hackritual .
# HF Spaces require the Dockerfile at the repo root, so the sync-to-HF workflow
# copies this file to ./Dockerfile before pushing (see .github/workflows).
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — Frontend build (pnpm via corepack)
# -----------------------------------------------------------------------------
FROM node:20-alpine AS frontend-build

# corepack ships with Node, but bare `corepack enable` resolves the shim to the
# LATEST pnpm (11.x), which requires Node 22 and dies on node:20 with
# `ERR_UNKNOWN_BUILTIN_MODULE: node:sqlite`. Pin to the packageManager version
# explicitly so the build is reproducible regardless of corepack's default.
RUN corepack enable && corepack prepare pnpm@9.12.3 --activate

WORKDIR /app/frontend

# Install dependencies first (layer-cached unless lockfile/manifest changes)
COPY src/frontend/package.json src/frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prefer-offline

# Copy source and build static export
COPY src/frontend/ ./
RUN pnpm build

# -----------------------------------------------------------------------------
# Stage 2 — Production image (uv for Python deps)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Install uv via its standalone installer — no compile step, fastest path.
# Copying from the official uv image is even cleaner.
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /uvx /usr/local/bin/

# Non-root user for security (HF Spaces runs as non-root anyway)
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Install Python dependencies into the system env via uv. No venv needed
# inside a container (the container is already isolated). requirements.txt
# holds the pinned set; uv is just a faster installer than pip.
COPY src/backend/requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application source. Note: it lands at /app/backend (not /app/src/backend)
# so the entrypoint's `cd /app/backend` and the app's `../../static` resolution
# stay valid inside the container.
COPY src/backend/ ./backend/

# Copy built frontend static files → /app/static (served by the backend)
COPY --from=frontend-build /app/frontend/out ./static/

# (The scaffold companion now lives inside the backend package at
# app/scaffold and is copied with `COPY src/backend` above.)

# Copy entrypoint
COPY tools/image/docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# Data directories — will be overridden by volume/persistent storage
RUN mkdir -p /data/uploads && chown -R appuser:appuser /data /app

USER appuser

# HF Spaces default port
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/health')" || exit 1

CMD ["./entrypoint.sh"]
