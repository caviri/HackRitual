# 13 — Agent System

**Milestone:** MVP-2
**Priority:** High
**Dependencies:** [04-user-management](04-user-management.md), [05-participant-management](05-participant-management.md), [07-submission-system](07-submission-system.md)
**Specs reference:** §6.2 (Agent Authentication), §7.2 (Participant Types), §10.4 (Agent Flow)

---

## Overview

Enable bot/agent participation via API key authentication. Agents are first-class participants that submit via API and are subject to the same scoring and rate limits as human participants. Agents can be standalone or part of hybrid teams.

---

## Tasks

### 13.1 Agent Entity

The `agents` table stores agent identity and API credentials:

```python
class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[str]                    # UUID
    name: Mapped[str]                  # display name
    owner_user_id: Mapped[str | None]  # FK → users.id (human who created it)
    api_key_hash: Mapped[str]          # SHA-256 hash of the API key
    api_key_prefix: Mapped[str]        # First 8 chars for identification (e.g., "hr_abc123")
    status: Mapped[str]                # 'active' | 'revoked'
    last_used_at: Mapped[datetime | None]
    created_at: Mapped[datetime]
```

### 13.2 API Key Generation

When creating an agent, generate a secure API key:

```python
import secrets

def generate_api_key() -> tuple[str, str]:
    """Returns (full_key, key_hash)."""
    raw_key = secrets.token_urlsafe(32)           # ~43 chars
    full_key = f"hr_{raw_key}"                     # prefix for identification
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_hash
```

Key rules:
- Full key shown **once** at creation time (never stored or retrievable)
- Only the hash is stored in DB
- Key prefix (`hr_` + first 8 chars) stored for identification in logs
- Keys must be revocable by admin or owner

### 13.3 Agent Registration Endpoints

#### Admin creates agent
`POST /api/admin/agents`

```json
{
  "name": "ScoreBot v3",
  "owner_user_id": "uuid"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "ScoreBot v3",
  "api_key": "hr_a3b7K9X2...",
  "api_key_prefix": "hr_a3b7K9",
  "status": "active",
  "warning": "Save this API key — it cannot be retrieved again."
}
```

#### User creates own agent (if agent policy allows)
`POST /api/agents`

```json
{
  "name": "My Bot"
}
```

- Only available if event config `agent_policy` is `"allowed"`
- Agent is owned by the requesting user
- Automatically creates an `agent` type Participant linked to this Agent

#### List agents (admin)
`GET /api/admin/agents`

#### Revoke agent key
`POST /api/admin/agents/{agent_id}/revoke`

- Sets `status='revoked'`
- Existing requests with this key will fail immediately
- Logged to audit

#### Regenerate agent key (admin or owner)
`POST /api/agents/{agent_id}/regenerate-key`

- Generates new key, invalidates old one
- Returns new key (shown once)

### 13.4 Agent Authentication Middleware

Agents authenticate via `Authorization: Bearer <api_key>` header:

```python
async def get_agent_from_key(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Agent:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing API key")

    api_key = authorization.removeprefix("Bearer ")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    agent = db.query(Agent).filter(
        Agent.api_key_hash == key_hash,
        Agent.status == "active",
    ).first()

    if not agent:
        raise HTTPException(401, "Invalid or revoked API key")

    agent.last_used_at = datetime.utcnow()
    db.commit()
    return agent
```

### 13.5 Agent Participant Linking

When an agent is created, also create:
1. A `Participant` record with `type='agent'`
2. A `ParticipantMember` linking the agent to the participant

For hybrid teams:
- Agent can be added to a team via admin or team captain
- `ParticipantMember` with `agent_id` set, `role_in_team='agent'`

### 13.6 Agent Submission API

`POST /api/agent/submissions`

**Headers:** `Authorization: Bearer hr_a3b7K9X2...`

**Request:**
```json
{
  "title": "Bot Submission #42",
  "description": "Automated optimization run",
  "payload_json": {
    "model_version": "v3.2",
    "parameters": { "learning_rate": 0.01 },
    "predictions": [0.95, 0.87, 0.92]
  },
  "tags": ["automated", "track-1"]
}
```

**Response:**
```json
{
  "id": "uuid",
  "participant_id": "uuid",
  "status": "received",
  "created_at": "2026-03-01T14:30:00Z"
}
```

- Same submission logic as human submissions (limits, event state check)
- `payload_json` is the primary data channel for agents
- File uploads supported via multipart (same as human endpoint)

#### Agent status check
`GET /api/agent/submissions/{id}`

**Headers:** `Authorization: Bearer hr_a3b7K9X2...`

Returns submission with score (if available).

#### Agent leaderboard
`GET /api/agent/leaderboard`

Same as public leaderboard but authenticated with API key.

### 13.7 Agent-Specific Rate Limits

Per specs §6.4:

| Limit | Default | Description |
|-------|---------|-------------|
| Submissions per hour | 20 | Per agent |
| API requests per minute | 60 | Per agent (all endpoints) |
| Max payload size | 1 MB | JSON payload |

Rate limit headers in response:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1709312400
```

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/admin/agents` | Admin | Create agent |
| GET | `/api/admin/agents` | Admin | List all agents |
| POST | `/api/admin/agents/{id}/revoke` | Admin | Revoke API key |
| POST | `/api/agents` | User | Create own agent |
| POST | `/api/agents/{id}/regenerate-key` | Owner/Admin | Regenerate key |
| POST | `/api/agent/submissions` | Agent (API key) | Submit |
| GET | `/api/agent/submissions/{id}` | Agent (API key) | Check status |
| GET | `/api/agent/leaderboard` | Agent (API key) | View leaderboard |

---

## Acceptance Criteria

- [ ] Admin can create agents with API keys (key shown once)
- [ ] Users can create own agents when agent policy allows
- [ ] API key authentication works via Bearer token
- [ ] Revoked keys are immediately rejected
- [ ] Agents can submit via API and receive scores
- [ ] Agent submissions respect same limits as human submissions
- [ ] Agent-specific rate limits enforced
- [ ] Agents can be added to hybrid teams
- [ ] Rate limit headers present in API responses
- [ ] All agent operations logged to audit

---

## Developer Notes

- API key prefix `hr_` makes keys identifiable in logs without exposing the full key
- Use constant-time comparison for key hash verification (`hmac.compare_digest`)
- Agent endpoints are under `/api/agent/` — separate from human endpoints for clarity
- Consider adding a webhook URL to agents (future) for push-based scoring notifications
- Test with `curl` to verify the agent API works standalone (no browser needed)
- The `last_used_at` field helps admins identify inactive agents
