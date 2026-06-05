# 05 — Participant Management

**Milestone:** MVP-1
**Priority:** High
**Dependencies:** [04-user-management](04-user-management.md), [06-event-lifecycle](06-event-lifecycle.md)
**Specs reference:** §7.2 (Participant Management)

---

## Overview

Participants are first-class entities separate from users. A participant can be a human individual, an agent (bot), or a team containing both. This task covers participant registration, team formation with invite codes, profiles, and admin moderation.

---

## Tasks

### 5.1 Participant Types

| Type | Description |
|------|------------|
| `human` | Single human user linked to a Participant |
| `agent` | Single bot/agent linked to a Participant (MVP-2) |
| `team` | Group containing human and/or agent members |

A human user can own/control multiple participants (e.g., be on a team and also have a solo entry, if event rules allow).

### 5.2 Self-Registration Flow

When a logged-in user creates their participant profile:

`POST /api/participants`

```json
{
  "display_name": "Alice",
  "affiliation": "University of Bern",
  "links": ["https://github.com/alice"],
  "type": "human"
}
```

**Server logic:**
1. Verify event state allows registration (DRAFT or OPEN, configurable)
2. Verify user doesn't already have a solo participant (if not allowed)
3. Create `Participant` record with `status='active'`
4. Create `ParticipantMember` linking user to participant (role = `captain` for solo)
5. Return participant info

**Response:**
```json
{
  "id": "uuid",
  "event_id": "hackritual-2026-bern",
  "type": "human",
  "display_name": "Alice",
  "affiliation": "University of Bern",
  "links": ["https://github.com/alice"],
  "status": "active",
  "created_at": "2026-02-18T10:00:00Z"
}
```

### 5.3 Team Creation

`POST /api/teams`

```json
{
  "display_name": "Team Forge",
  "affiliation": "Mixed",
  "links": []
}
```

**Server logic:**
1. Create `Participant` with `type='team'`
2. Generate a unique invite code (8 chars, alphanumeric)
3. Add creating user as `ParticipantMember` with `role_in_team='captain'`
4. Return team info with invite code

**Response:**
```json
{
  "id": "uuid",
  "display_name": "Team Forge",
  "type": "team",
  "invite_code": "A3B7K9X2",
  "members": [
    {
      "user_id": "uuid",
      "display_name": "Alice",
      "role_in_team": "captain"
    }
  ]
}
```

### 5.4 Team Join via Invite Code

`POST /api/teams/join`

```json
{
  "invite_code": "A3B7K9X2"
}
```

**Server logic:**
1. Look up team by invite code
2. Verify team is active and event allows joining
3. Verify user is not already a member
4. Add `ParticipantMember` with `role_in_team='member'`
5. Return updated team info

### 5.5 Team Management

#### List team members
`GET /api/teams/{team_id}/members` — Any team member

#### Remove team member (Captain only)
`DELETE /api/teams/{team_id}/members/{member_id}`

#### Leave team
`POST /api/teams/{team_id}/leave` — Any member (captain must transfer first)

#### Regenerate invite code (Captain only)
`POST /api/teams/{team_id}/regenerate-invite`

### 5.6 Participant Profile

#### View own profile
`GET /api/participants/me`

#### Update own profile
`PATCH /api/participants/me`

```json
{
  "display_name": "Alice B.",
  "affiliation": "Updated Affiliation",
  "links": ["https://github.com/alice"]
}
```

#### View any participant (public info)
`GET /api/participants/{participant_id}`

- Returns public fields only (display_name, affiliation, type)
- Does not expose email or internal IDs

### 5.7 Participant Listing

`GET /api/participants`

**Query params:** `?type=human&status=active&page=1&per_page=20`

- Public endpoint — shows active participants
- Returns display_name, affiliation, type, team info

### 5.8 Admin Moderation

#### Admin: List all participants (with full details)
`GET /api/admin/participants`

#### Admin: Create participant
`POST /api/admin/participants`
- Admin can create participants on behalf of users

#### Admin: Update participant status
`PATCH /api/admin/participants/{id}/status`

```json
{
  "status": "disabled"  // or "banned" or "active"
}
```

- Log to audit log
- Disabled/banned participants cannot submit

#### Admin: Assign to team
`POST /api/admin/participants/{team_id}/members`

```json
{
  "user_id": "uuid",
  "role_in_team": "member"
}
```

---

## Data Model Relationships

```
User (1) ──── (N) ParticipantMember (N) ──── (1) Participant
                                                    │
                                                    ├── type: human (solo)
                                                    ├── type: team (has members)
                                                    └── type: agent (MVP-2)
```

Key rules:
- A `human` participant has exactly 1 member (the user)
- A `team` participant has 1+ members
- An `agent` participant has 1 member (the agent entity) — see MVP-2
- `ParticipantMember.user_id` is set for humans, `agent_id` for agents

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/participants` | User | Create solo participant |
| GET | `/api/participants` | Public | List participants |
| GET | `/api/participants/me` | User | Own participant info |
| PATCH | `/api/participants/me` | User | Update own profile |
| GET | `/api/participants/{id}` | Public | View participant |
| POST | `/api/teams` | User | Create team |
| POST | `/api/teams/join` | User | Join team via invite code |
| GET | `/api/teams/{id}/members` | Team member | List team members |
| DELETE | `/api/teams/{id}/members/{mid}` | Captain | Remove member |
| POST | `/api/teams/{id}/leave` | Member | Leave team |
| POST | `/api/teams/{id}/regenerate-invite` | Captain | New invite code |
| GET | `/api/admin/participants` | Admin | List all participants |
| POST | `/api/admin/participants` | Admin | Create participant |
| PATCH | `/api/admin/participants/{id}/status` | Admin | Moderate participant |
| POST | `/api/admin/participants/{tid}/members` | Admin | Assign to team |

---

## Acceptance Criteria

- [ ] Users can create a solo participant profile after login
- [ ] Users can create teams and get an invite code
- [ ] Users can join teams using invite codes
- [ ] Team captain can manage members and regenerate invite codes
- [ ] Participant profiles show public info only (no emails)
- [ ] Admin can create, view, and moderate all participants
- [ ] Disabled/banned participants cannot create submissions
- [ ] All moderation actions logged to audit log
- [ ] Participant listing supports pagination and filtering

---

## Developer Notes

- Invite codes should be URL-safe and case-insensitive (store uppercase, compare uppercase)
- Use `secrets.token_urlsafe(6)` for invite codes (gives ~8 chars)
- Consider capping team size (configurable in event config)
- The participant `links` field is stored as JSON string — validate it's an array of URLs on input
- For MVP-1, agent participants are not yet implemented — just ensure the model supports it
