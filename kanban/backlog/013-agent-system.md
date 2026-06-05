---
id: "013"
title: "Agent System"
type: feature
status: backlog
estimate: "5d"
size: XL
depends_on: ["004"]
blocks: ["015"]
spec: "specs/specs/13-agent-system.md"
tags: [agents, api-keys, backend]
---

# Agent System

Allow AI agents (bots) to participate in events via API key authentication.

## Tasks

- [ ] `POST /api/agents` — create agent, generate API key (hashed with bcrypt)
- [ ] `GET /api/agents` — list own agents
- [ ] `DELETE /api/agents/{id}` — revoke agent
- [ ] `POST /api/agents/{id}/rotate-key` — generate new API key
- [ ] Extend `get_current_user` middleware to accept `Authorization: Bearer <api_key>`
- [ ] Agent participants auto-created when agent makes first submission
- [ ] Agent submission endpoint: `POST /api/submissions` with agent auth
- [ ] `GET /api/submissions/{id}/status` — agent polls submission status
- [ ] Admin: `GET /api/admin/agents` — list all agents with owner info

## Auth Flow

```
Agent → POST /api/submissions (Authorization: Bearer <api_key>)
      → API key validated, agent participant resolved
      → Submission created, scoring queued
```

## Notes

- API key is shown only once on creation (bcrypt hashed in DB)
- Agent model already in DB schema (Step 02)
- Rate limiting for agent submissions handled in Step 15
