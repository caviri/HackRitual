---
id: "004"
title: "User Management"
type: feature
status: done
estimate: "2d"
size: M
depends_on: ["003"]
blocks: ["005", "009", "013"]
spec: "specs/specs/04-user-management.md"
tags: [admin, users, roles]
tests_passing: 37
---

# User Management

Admin endpoints for managing users, roles, and seeding the initial admin accounts.

## Completed

- [x] `GET /api/admin/users` — paginated user listing with role/email filtering
- [x] `GET /api/admin/users/{id}` — single user detail
- [x] `PATCH /api/admin/users/{id}/role` — change role (prevents demoting last admin)
- [x] `DELETE /api/admin/users/{id}` — soft delete (status → inactive)
- [x] Admin seeding via `ADMIN_SEED_EMAILS` and/or `ADMIN_SETUP_TOKEN` on startup
- [x] `POST /api/admin/setup` — one-time admin claim via setup token
- [x] Audit logging integrated for role changes and deactivations
- [x] Schemas for user list, detail, role update requests/responses

## User Roles

`user` · `admin` · `judge` · `mod`

## Notes

- Seeding is idempotent: existing admin users are not demoted on restart
- Soft delete sets `status=inactive`; inactive users cannot authenticate
- At least one of `ADMIN_SEED_EMAILS` or `ADMIN_SETUP_TOKEN` must be set (enforced at startup)
