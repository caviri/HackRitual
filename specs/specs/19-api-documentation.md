# 19 — API Documentation

**Milestone:** Cross-cutting (build incrementally as endpoints are added)
**Priority:** Medium
**Dependencies:** All backend API tasks
**Specs reference:** §7.9 (API)

---

## Overview

All API endpoints must be documented. FastAPI provides automatic OpenAPI/Swagger documentation. This task covers ensuring complete, accurate API docs, adding descriptions, examples, and organizing endpoints into logical groups.

---

## Tasks

### 19.1 FastAPI OpenAPI Configuration

```python
# backend/app/main.py

app = FastAPI(
    title="HackRitual API",
    description="""
    API for HackRitual — a portable platform for ritualised collaborative invention.

    ## Authentication
    - Human users: passwordless email login (magic codes) → JWT session cookie
    - Agents/bots: API key via `Authorization: Bearer <key>` header

    ## Event States
    Operations are gated by event state: DRAFT → OPEN → FROZEN → FINAL → ARCHIVED

    ## Rate Limits
    All endpoints are rate-limited. See response headers:
    `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
    """,
    version="0.1.0",
    docs_url="/api/docs",          # Swagger UI
    redoc_url="/api/redoc",        # ReDoc
    openapi_url="/api/openapi.json",
)
```

### 19.2 API Tag Groups

Organize endpoints with tags:

```python
tags_metadata = [
    {"name": "Auth", "description": "Authentication (login, logout, session)"},
    {"name": "Event", "description": "Event info and configuration"},
    {"name": "Participants", "description": "Participant registration and profiles"},
    {"name": "Teams", "description": "Team creation and management"},
    {"name": "Submissions", "description": "Submission CRUD and file uploads"},
    {"name": "Scoring", "description": "Scores and leaderboard"},
    {"name": "Agent API", "description": "Agent/bot authentication and submission"},
    {"name": "Admin - Event", "description": "Admin: event lifecycle management"},
    {"name": "Admin - Users", "description": "Admin: user and role management"},
    {"name": "Admin - Participants", "description": "Admin: participant moderation"},
    {"name": "Admin - Submissions", "description": "Admin: submission management"},
    {"name": "Admin - Scoring", "description": "Admin: scoring and WASM module"},
    {"name": "Admin - Export", "description": "Admin: export and archival"},
    {"name": "Admin - Queue", "description": "Admin: task queue monitoring"},
    {"name": "Admin - Metrics", "description": "Admin: statistics and audit logs"},
    {"name": "Health", "description": "Health check and system info"},
]
```

### 19.3 Pydantic Schema Documentation

Ensure all request/response schemas have:
- Field descriptions
- Examples
- Validation constraints

```python
class CreateSubmissionInput(BaseModel):
    title: str = Field(
        ...,
        description="Submission title",
        example="My Solution v2",
        max_length=200,
    )
    description: str | None = Field(
        None,
        description="Detailed description of the submission",
        example="Improved approach using gradient descent...",
        max_length=5000,
    )
    tags: list[str] = Field(
        default=[],
        description="Tags for categorization",
        example=["optimization", "track-1"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "My Solution v2",
                "description": "Improved approach using gradient descent",
                "tags": ["optimization", "track-1"],
            }
        }
    )
```

### 19.4 Response Model Documentation

```python
class SubmissionResponse(BaseModel):
    id: str = Field(description="Unique submission ID")
    participant_id: str = Field(description="Owning participant ID")
    title: str | None
    description: str | None
    tags: list[str]
    files: list[FileInfo]
    status: str = Field(description="Status: received | queued | scored | failed | withdrawn")
    score: ScoreInfo | None = Field(description="Score if available, null if pending")
    created_at: datetime
```

### 19.5 Error Response Documentation

Document standard error responses:

```python
class ErrorResponse(BaseModel):
    detail: str = Field(description="Human-readable error message")
    code: str | None = Field(None, description="Machine-readable error code")

# Use in endpoint decorators
@router.post(
    "/submissions",
    response_model=SubmissionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (wrong role)"},
        409: {"model": ErrorResponse, "description": "Event not in OPEN state"},
        429: {"model": ErrorResponse, "description": "Rate limit or submission cap exceeded"},
    },
)
```

### 19.6 Complete Endpoint Catalog

Document every endpoint across all tasks. Full catalog:

#### Public Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/event` | Event info |
| GET | `/api/participants` | List participants |
| GET | `/api/participants/{id}` | View participant |
| GET | `/api/leaderboard` | View leaderboard |
| GET | `/api/scoring/preview-module` | Download WASM preview |

#### Auth Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/request-code` | Request login code |
| POST | `/api/auth/verify-code` | Verify code |
| POST | `/api/auth/logout` | Logout |
| POST | `/api/auth/refresh` | Refresh session |
| GET | `/api/auth/me` | Current user info |

#### User Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/participants` | Create participant |
| GET | `/api/participants/me` | Own participant |
| PATCH | `/api/participants/me` | Update profile |
| POST | `/api/teams` | Create team |
| POST | `/api/teams/join` | Join team |
| GET | `/api/teams/{id}/members` | Team members |
| POST | `/api/submissions` | Create submission |
| GET | `/api/submissions/mine` | My submissions |
| GET | `/api/submissions/{id}` | View submission |
| GET | `/api/submissions/{id}/files/{fid}` | Download file |
| POST | `/api/submissions/{id}/withdraw` | Withdraw |

#### Agent Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agent/submissions` | Agent submit |
| GET | `/api/agent/submissions/{id}` | Check status |
| GET | `/api/agent/leaderboard` | View leaderboard |

#### Admin Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/admin/event/state` | Change event state |
| PATCH | `/api/admin/event/config` | Update event config |
| GET | `/api/admin/users` | List users |
| PATCH | `/api/admin/users/{id}/role` | Change role |
| GET | `/api/admin/participants` | List all participants |
| PATCH | `/api/admin/participants/{id}/status` | Moderate |
| GET | `/api/admin/submissions` | List all submissions |
| PATCH | `/api/admin/submissions/{id}/status` | Change status |
| POST | `/api/admin/submissions/{id}/rescore` | Re-score |
| POST | `/api/admin/scoring/upload-wasm` | Upload WASM |
| POST | `/api/admin/scoring/rescore-all` | Re-score all |
| POST | `/api/admin/export` | Generate export |
| GET | `/api/admin/export/{id}/download` | Download export |
| POST | `/api/admin/export/{id}/push-github` | Push to GitHub |
| GET | `/api/admin/queue/status` | Queue status |
| GET | `/api/admin/metrics` | Metrics |
| GET | `/api/admin/agents` | List agents |
| POST | `/api/admin/agents` | Create agent |
| POST | `/api/admin/agents/{id}/revoke` | Revoke key |

### 19.7 API Versioning

- All endpoints under `/api/` prefix
- No version prefix in MVP (v1 implied)
- If breaking changes needed later, add `/api/v2/` prefix
- OpenAPI spec version tracks API version

### 19.8 Documentation Verification

As part of CI/testing:
- Verify all router endpoints have response models
- Verify all Pydantic models have field descriptions
- Generate OpenAPI JSON and validate it's complete
- Keep a snapshot of `openapi.json` in the repo for change tracking

---

## Acceptance Criteria

- [ ] Swagger UI accessible at `/api/docs`
- [ ] ReDoc accessible at `/api/redoc`
- [ ] All endpoints organized with meaningful tags
- [ ] Request/response schemas include descriptions and examples
- [ ] Error responses documented for all endpoints
- [ ] OpenAPI spec (`/api/openapi.json`) is valid and complete
- [ ] Agent API documented with Bearer token authentication
- [ ] Rate limit headers documented in API description

---

## Developer Notes

- FastAPI generates OpenAPI docs automatically — the work is in adding descriptions and examples
- Use `Field(description=...)` on every Pydantic field
- Use `responses={...}` on every router decorator for error documentation
- Keep Swagger UI enabled in production (it's useful for debugging)
- Consider generating a static API reference from the OpenAPI spec for the documentation site
- Test the docs by opening `/api/docs` and trying each endpoint
