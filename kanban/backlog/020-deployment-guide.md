---
id: "020"
title: "Deployment Guide"
type: doc
status: backlog
estimate: "1d"
size: S
depends_on: []
blocks: []
spec: "specs/specs/20-deployment-guide.md"
tags: [docs, deployment, hf-spaces, docker]
---

# Deployment Guide

Complete deployment documentation and operational runbook for all supported environments.

## Tasks

- [ ] Validate `docker build` produces a working image (requires Docker daemon)
- [ ] Validate deployment on HF Spaces Docker runtime (port 7860, persistent storage)
- [ ] Document env var checklist for production
- [ ] Document persistent storage setup on HF Spaces
- [ ] Write disaster recovery procedure (export before teardown)
- [ ] Document upgrade path (Alembic migration during container restart)
- [ ] Add `docs/deployment.md` operational runbook sections:
  - Pre-flight checklist
  - First-run verification
  - Health monitoring
  - Export and teardown
  - Troubleshooting

## Deployment Targets

| Environment | Status |
|-------------|--------|
| Local dev (uv run) | Working |
| docker-compose | Structurally validated |
| Docker single container | Pending daemon |
| HF Spaces (Docker SDK) | Pending live deploy |

## Notes

- `docs/deployment.md` already exists as a skeleton from Step 01
- This step validates everything end-to-end and completes the runbook
