# 11 — JSON Export

**Milestone:** MVP-1
**Priority:** Medium
**Dependencies:** [02-database-layer](02-database-layer.md), [07-submission-system](07-submission-system.md), [08-scoring-basic](08-scoring-basic.md)
**Specs reference:** §7.7 (Exports & Archival), Appendix A (Export Schema)

---

## Overview

Generate a structured JSON export bundle containing all event data. This is the core archival mechanism — the exported bundle must be self-contained, versioned, and suitable for long-term storage or publishing via GitHub Pages. Local download is always supported; GitHub push is covered in [17-github-export](17-github-export.md).

---

## Tasks

### 11.1 Export Bundle Structure

The export produces a ZIP file containing:

```
export/
├── manifest.json          # Schema version, event metadata, timestamps
├── participants.json      # All participants
├── teams.json             # Team structures and memberships
├── agents.json            # Agent entities (if any)
├── submissions.json       # Submission metadata (no file blobs)
├── scores.json            # Official scores and breakdowns
├── audit_log.json         # Admin audit trail
├── statistics.json        # Aggregate event statistics
└── assets/                # Optional: thumbnails, images
    └── ...
```

### 11.2 Export Service

```python
# backend/app/services/export_service.py

class ExportService:
    def generate_bundle(
        self,
        db: Session,
        redaction: RedactionConfig,
    ) -> Path:
        """Generate full export bundle as a ZIP file."""

    def generate_manifest(self, event: Event) -> dict:
        """Generate manifest.json content."""

    def export_participants(self, db, redaction) -> list[dict]:
        """Export participants with optional email hashing."""

    def export_submissions(self, db) -> list[dict]:
        """Export submission metadata (no blobs)."""

    def export_scores(self, db) -> list[dict]:
        """Export official scores."""

    def export_audit_log(self, db) -> list[dict]:
        """Export audit log entries."""
```

### 11.3 manifest.json

Per specs Appendix A:

```json
{
  "schema_version": "1.0.0",
  "exported_at": "2026-02-18T12:00:00Z",
  "exporter_version": "0.1.0",
  "event": {
    "id": "hackritual-2026-bern",
    "title": "HackRitual Bern 2026",
    "type": "hackathon",
    "state": "FINAL",
    "start": "2026-03-01T09:00:00+01:00",
    "end": "2026-03-02T17:00:00+01:00"
  },
  "scoring": {
    "mode": "server_authoritative",
    "scorer_type": "python",
    "scorer_version": "default-1.0",
    "notes": ""
  },
  "privacy": {
    "emails_exported": false,
    "participant_ids_stable": true,
    "redaction_mode": "public"
  },
  "counts": {
    "participants": 42,
    "teams": 8,
    "agents": 3,
    "submissions": 150,
    "scores": 148
  }
}
```

### 11.4 Redaction Configuration

```python
@dataclass
class RedactionConfig:
    mode: str = "public"       # 'public' | 'private' | 'full'
    hash_emails: bool = True   # hash emails in public export
    include_audit: bool = True
    include_assets: bool = False
```

| Mode | Emails | Audit Log | Payload JSON | Files |
|------|--------|-----------|-------------|-------|
| `public` | Hashed | Included (actors hashed) | Included | References only |
| `private` | Plaintext | Full | Full | References + assets |
| `full` | Plaintext | Full | Full | Included |

Email hashing: `sha256(email + event_id)[:16]` — stable within event, not reversible.

### 11.5 participants.json

```json
[
  {
    "id": "uuid",
    "type": "human",
    "display_name": "Alice",
    "affiliation": "University of Bern",
    "status": "active",
    "email_hash": "a3b7c9d2e4f61234",
    "created_at": "2026-02-20T10:00:00Z"
  }
]
```

### 11.6 submissions.json

```json
[
  {
    "id": "uuid",
    "participant_id": "uuid",
    "title": "My Solution v2",
    "description": "...",
    "tags": ["optimization"],
    "files": [
      {
        "filename": "solution.zip",
        "mime_type": "application/zip",
        "size_bytes": 245760,
        "sha256": "abc123..."
      }
    ],
    "status": "scored",
    "created_at": "2026-03-01T14:30:00Z"
  }
]
```

Note: file blobs are NOT included. Only metadata and references.

### 11.7 scores.json

```json
[
  {
    "submission_id": "uuid",
    "participant_id": "uuid",
    "score_value": 95.0,
    "breakdown": { "accuracy": 80, "style": 15 },
    "status": "scored",
    "scorer_version": "default-1.0",
    "scored_at": "2026-03-01T14:31:00Z"
  }
]
```

### 11.8 Export API Endpoints

#### Generate export
`POST /api/admin/export`

```json
{
  "redaction_mode": "public",
  "include_assets": false
}
```

**Response:**
```json
{
  "export_id": "uuid",
  "status": "generating",
  "estimated_size_mb": 2.5
}
```

For MVP-1, generation is synchronous and returns the download URL directly. For larger events, async generation via task queue (MVP-2).

#### Download export
`GET /api/admin/export/{export_id}/download`

Returns ZIP file as streaming response.

#### Export preview (counts only)
`GET /api/admin/export/preview`

Returns counts and estimated size without generating.

### 11.9 Export Validation

After generation, validate:
- manifest.json is valid JSON with required fields
- All referenced IDs in submissions match existing participants
- All referenced IDs in scores match existing submissions
- No secrets are present (JWT_SECRET, SMTP_PASS, API keys)
- Email hashing applied correctly in public mode

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/export/preview` | Admin | Preview export counts |
| POST | `/api/admin/export` | Admin | Generate export bundle |
| GET | `/api/admin/export/{id}/download` | Admin | Download ZIP |

---

## Acceptance Criteria

- [ ] Export generates a valid ZIP with all required JSON files
- [ ] manifest.json contains accurate metadata and counts
- [ ] Public redaction mode hashes emails consistently
- [ ] No secrets or private config present in export
- [ ] Export can be generated at any event state (snapshot)
- [ ] Final export (FINAL state) produces a complete, frozen archive
- [ ] Download endpoint streams ZIP file correctly
- [ ] Export is reproducible (same input → same content, different timestamps)

---

## Developer Notes

- Use Python's `zipfile` module with `ZIP_DEFLATED` compression
- Generate export to a temp directory, then zip it
- For deterministic export, sort all JSON arrays by ID
- The `schema_version` should follow semver — bump on breaking changes
- Consider streaming the ZIP generation for large exports instead of buffering in memory
- Export preview endpoint is useful for the admin UI to show counts before generating
- Never include `login_codes`, `sessions`, `tasks` (internal queue), or raw IPs in export
