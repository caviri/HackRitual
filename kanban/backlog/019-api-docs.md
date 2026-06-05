---
id: "019"
title: "API Documentation"
type: doc
status: backlog
estimate: "2d"
size: S
depends_on: []
blocks: []
spec: "specs/specs/19-api-documentation.md"
tags: [docs, openapi, cross-cutting]
---

# API Documentation

Enrich OpenAPI schema with detailed descriptions, examples, and a developer-friendly reference.

## Tasks

- [ ] Add `description`, `response_description`, and `responses` to all route decorators
- [ ] Add Pydantic `model_config` with `json_schema_extra` for request/response examples
- [ ] Verify `/api/docs` (Swagger UI) and `/api/redoc` render correctly for all endpoints
- [ ] Write `docs/api.md` reference (human-readable, not auto-generated)
- [ ] Add authentication guide to OpenAPI description
- [ ] Tag all routers consistently: `auth`, `users`, `participants`, `submissions`, `scores`, `admin`, `scaffold`

## Notes

- FastAPI auto-generates OpenAPI schema; this step enriches it with examples and detail
- `docs/api.md` already exists as a skeleton; this step fills it out completely
- Integrate incrementally as each feature step completes
