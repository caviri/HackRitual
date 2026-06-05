# 04 — User Management

**Milestone:** MVP-1
**Priority:** Critical
**Dependencies:** [02-database-layer](02-database-layer.md), [03-authentication](03-authentication.md)
**Specs reference:** §6.3 (Authorization), §7.3 (User Management)

---

## Overview

Manage human user accounts with role-based access control (RBAC). Users are identified by email and assigned roles. Admin seeding happens at deployment time. This task covers user CRUD, role management, and authorization enforcement.

---

## Tasks

### 4.1 Role-Based Access Control (RBAC)

Define the role hierarchy:

| Role | Permissions |
|------|------------|
| `user` | Login, view event, create/manage own participant, submit |
| `judge` | All `user` + view all submissions, add manual scores (future) |
| `mod` | All `user` + moderate participants (disable/ban) |
| `admin` | Full access — manage event lifecycle, users, participants, export |

Authorization must be enforced **server-side on every protected operation** (specs §6.3).

### 4.2 User Endpoints

#### List Users (Admin only)

`GET /api/admin/users`

**Query params:** `?page=1&per_page=20&role=admin&search=email`

**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "admin@example.com",
      "role": "admin",
      "created_at": "2026-01-15T10:00:00Z",
      "last_login_at": "2026-02-18T09:30:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

#### Get User (Admin only)

`GET /api/admin/users/{user_id}`

#### Update User Role (Admin only)

`PATCH /api/admin/users/{user_id}/role`

```json
{
  "role": "admin"
}
```

- Must log action to audit log
- Cannot demote the last admin (safety check)
- Cannot change own role (prevent self-lockout)

#### Delete / Deactivate User (Admin only)

`DELETE /api/admin/users/{user_id}`

- Soft-delete preferred (mark as inactive)
- Cascade: deactivate associated participants
- Must log action to audit log

### 4.3 Admin Seeding

Two modes (configured via env vars):

**Mode A: `ADMIN_SEED_EMAILS`**
- On startup, for each email in the comma-separated list:
  - If user doesn't exist, create with `role='admin'`
  - If user exists but isn't admin, promote to admin
  - Log action
- Idempotent — safe to run on every restart

**Mode B: `ADMIN_SETUP_TOKEN`**
- Expose `POST /api/setup` (only available when no admin exists):
  ```json
  {
    "token": "the-setup-token",
    "email": "admin@example.com"
  }
  ```
- Validates token matches env var
- Creates admin user
- Endpoint becomes unavailable after first admin is created
- Return `410 Gone` if admin already exists

### 4.4 Session Management

- Users can view their active sessions (future enhancement)
- Admin can invalidate user sessions (if using DB sessions)
- JWT expiry enforced on every request
- On role change, existing tokens remain valid until expiry (acceptable for MVP)

### 4.5 Audit Logging Helper

Create a reusable service for audit logging:

```python
class AuditService:
    def log(
        self,
        db: Session,
        actor_id: str | None,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
```

Actions to log:
- `user.created` — new user registered
- `user.role_changed` — role updated
- `user.deactivated` — user deactivated
- `user.admin_seeded` — admin created via seed

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/users` | Admin | List all users |
| GET | `/api/admin/users/{id}` | Admin | Get user details |
| PATCH | `/api/admin/users/{id}/role` | Admin | Change user role |
| DELETE | `/api/admin/users/{id}` | Admin | Deactivate user |
| POST | `/api/setup` | Public (one-time) | Create first admin via setup token |

---

## Acceptance Criteria

- [ ] Admin users are seeded on first startup from env vars
- [ ] Role-based authorization enforced on all admin endpoints
- [ ] Admin can list, view, and update user roles
- [ ] Cannot demote last admin or change own role
- [ ] All role changes logged to audit log
- [ ] Setup token endpoint works only when no admin exists
- [ ] User creation happens automatically on first login (from auth flow)

---

## Developer Notes

- Use FastAPI dependency injection for role checks (see [03-authentication](03-authentication.md) §3.6)
- Keep role checks as simple string comparisons for now — no need for a permissions framework
- The audit log service should be injected as a dependency, not imported globally
- Consider adding an index on `audit_log.actor_user_id` and `audit_log.created_at` for admin queries
