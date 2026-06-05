# 09 — Admin Console

**Milestone:** MVP-1
**Priority:** High
**Dependencies:** [04-user-management](04-user-management.md), [06-event-lifecycle](06-event-lifecycle.md), [10-frontend-foundation](10-frontend-foundation.md)
**Specs reference:** §7.8 (Admin Console)

---

## Overview

The Admin Console is a protected section of the frontend that allows admins to manage the full event lifecycle without shell access. It provides views for event configuration, participant moderation, submission management, scoring oversight, export controls, and audit logs.

---

## Tasks

### 9.1 Admin Layout & Navigation

Create a dedicated admin section in the Next.js app:

```
/admin                    → Dashboard / overview
/admin/event              → Event configuration & state
/admin/participants       → Participant management
/admin/submissions        → Submission browser
/admin/scoring            → Scoring queue & status
/admin/export             → Export & archival controls
/admin/audit              → Audit log viewer
/admin/users              → User management
```

- Protected by `admin` role check (redirect to `/` if not admin)
- Sidebar navigation with section links
- Responsive layout (works on tablet+)

### 9.2 Admin Dashboard

`/admin` — Overview page showing:

- Event status badge (DRAFT / OPEN / FROZEN / FINAL / ARCHIVED)
- Key metrics cards:
  - Total participants
  - Total submissions
  - Submissions today
  - Scoring queue depth
  - Active agents (MVP-2)
- Quick actions:
  - Change event state
  - View recent audit entries
- Event timeline visualization (simple horizontal bar showing phases)

### 9.3 Event Configuration Page

`/admin/event` — Shows:

- **Read-only section** (from env vars):
  - Event ID, title, type
  - Start/end dates
  - Storage path, persistence status
- **Editable section** (from event config_json):
  - Submission limits
  - Leaderboard mode (best / latest)
  - Tracks/categories
  - Agent policy (allowed / forbidden)
  - Registration settings
- **State control panel:**
  - Current state with transition buttons
  - Confirmation modal for state changes
  - Reason field (required for state transitions)
  - Warning for irreversible actions (FINAL → ARCHIVED)

### 9.4 Participant Management Page

`/admin/participants` — Table view:

| Column | Description |
|--------|-------------|
| Display Name | With type badge (human/agent/team) |
| Status | active / disabled / banned |
| Email | For human participants |
| Team | Team name if applicable |
| Submissions | Count |
| Joined | Registration date |
| Actions | Activate / Disable / Ban |

Features:
- Filter by type, status
- Search by name or email
- Bulk actions (disable multiple)
- Click row to view detail panel:
  - Full participant profile
  - Team membership
  - Submission history
  - Status change form with reason

### 9.5 Submission Browser

`/admin/submissions` — Table view:

| Column | Description |
|--------|-------------|
| ID | Short ID |
| Participant | Display name with link |
| Title | Submission title |
| Status | received / queued / scored / failed / withdrawn |
| Score | Numeric score (if scored) |
| Files | File count |
| Created | Timestamp |
| Actions | View / Rescore / Withdraw / DQ |

Features:
- Filter by participant, status, score range, date range
- Sort by score, date, status
- Click row to view full details:
  - Metadata, description, tags
  - File previews (images) or download links
  - Payload JSON viewer (formatted)
  - Score breakdown
  - Rescore button
  - Status change form (withdraw/disqualify with reason)

### 9.6 Scoring Status Page

`/admin/scoring` — Shows:

- Current scorer info (type, version)
- Queue status:
  - Pending scores count
  - Running scores count
  - Failed scores (with error details)
  - Average scoring time
- Batch operations:
  - Rescore all (with confirmation)
  - Retry failed scores
- Score distribution chart (histogram)

### 9.7 Export & Archival Page

`/admin/export` — Shows:

- Export preview:
  - Counts of each entity type
  - Schema version
  - Estimated bundle size
- Redaction options:
  - Hash emails in export (on/off)
  - Separate private admin archive (on/off)
- Actions:
  - Generate export bundle → download ZIP
  - Push to GitHub (if configured) → shows status
  - Mark as ARCHIVED (with confirmation)
- Export history (previous exports with timestamps)

### 9.8 Audit Log Viewer

`/admin/audit` — Table view:

| Column | Description |
|--------|-------------|
| Timestamp | When the action occurred |
| Actor | User who performed the action |
| Action | Action type (e.g., `event.state_change`) |
| Target | What was affected |
| Details | Metadata JSON (expandable) |

Features:
- Filter by action type, actor, date range
- Search in metadata
- Pagination
- Export audit log as JSON

### 9.9 User Management Page

`/admin/users` — Table view:

| Column | Description |
|--------|-------------|
| Email | User email |
| Role | user / admin / judge / mod |
| Participants | Linked participant count |
| Last Login | Timestamp |
| Actions | Change role |

Features:
- Change user role (dropdown)
- View linked participants
- Deactivate user

---

## Acceptance Criteria

- [ ] Admin console accessible only to admin-role users
- [ ] Dashboard shows live event metrics
- [ ] Admin can transition event state with confirmation and reason
- [ ] Admin can configure event settings (submission limits, leaderboard mode, etc.)
- [ ] Admin can view, filter, and moderate all participants
- [ ] Admin can view all submissions with scores and files
- [ ] Admin can trigger rescore and manual score override
- [ ] Admin can generate export and optionally push to GitHub
- [ ] Admin can view and filter audit logs
- [ ] Admin can manage user roles
- [ ] All admin operations work without shell/DB access

---

## Developer Notes

- Use Next.js route groups for the admin section: `app/(admin)/admin/...`
- Protect all admin routes with middleware checking the JWT role claim
- Use a shared admin layout component with sidebar navigation
- For tables, consider using TanStack Table (React Table) for sorting/filtering/pagination
- Keep API calls in a dedicated `lib/admin-api.ts` client
- The admin console fetches data from the `/api/admin/*` endpoints defined in other tasks
- Consider using SWR or React Query for data fetching with automatic revalidation
- Dashboard metrics can poll every 30 seconds for live updates
- Charts can use a lightweight library like Recharts or Chart.js
