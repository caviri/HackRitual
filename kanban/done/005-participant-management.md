---
id: "005"
title: "Participant Management"
type: feature
status: done
estimate: "3d"
size: L
depends_on: ["004"]
blocks: ["007"]
spec: "specs/specs/05-participant-management.md"
tags: [participants, teams, invite-codes]
tests_passing: 22
---

# Participant Management

Self-registration, team creation with invite codes, team membership management, and admin moderation.

## Completed

- [x] Participant types: `human`, `agent`, `team`
- [x] `POST /api/participants` — self-registration (DRAFT or OPEN state only)
- [x] `GET/PATCH /api/participants/me` — own profile management
- [x] `GET /api/participants/{id}` — public profile (no email)
- [x] `GET /api/participants` — paginated listing with filtering
- [x] `POST /api/teams` — create team with auto-generated 8-char invite code
- [x] `POST /api/teams/join` — join via invite code
- [x] `GET /api/teams/{id}/members` — team member list (requires membership)
- [x] `DELETE /api/teams/{id}/members/{mid}` — remove member (captain only)
- [x] `POST /api/teams/{id}/leave` — leave team (captain cannot leave)
- [x] `POST /api/teams/{id}/regenerate-invite` — new invite code (captain only)
- [x] Admin: list all, create, moderate (status change: active/disabled/banned)

## Notes

- Invite codes are 8-char alphanumeric, URL-safe, case-insensitive
- Registration blocked in FROZEN/FINAL/ARCHIVED states
- User model has no `display_name`; email prefix used for team member display
