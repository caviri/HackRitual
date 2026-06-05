# =============================================================================
# HackRitual — Multi-stage Docker build
#
# Stage 1: Build Next.js frontend (static export) with pnpm
# Stage 2: Production Python image with uv, serving backend + static frontend
#
# Target deploy: Hugging Face Spaces (port 7860)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — Frontend build (pnpm via corepack)
# -----------------------------------------------------------------------------
FROM node:20-alpine AS frontend-build

# corepack pins the exact pnpm version from package.json#packageManager
RUN corepack enable

WORKDIR /app/frontend

# Install dependencies first (layer-cached unless lockfile/manifest changes)
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prefer-offline

# Copy source and build static export
COPY frontend/ ./
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
COPY backend/requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application source
COPY backend/ ./backend/

# Copy built frontend static files
COPY --from=frontend-build /app/frontend/out ./static/

# Copy entrypoint
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# Data directories — will be overridden by volume/persistent storage
RUN mkdir -p /data/uploads && chown -R appuser:appuser /data /app

USER appuser

# HF Spaces default port
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/health')" || exit 1

CMD ["./entrypoint.sh"]
