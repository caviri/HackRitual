# 07 — Submission System

**Milestone:** MVP-1
**Priority:** High
**Dependencies:** [05-participant-management](05-participant-management.md), [06-event-lifecycle](06-event-lifecycle.md)
**Specs reference:** §7.4 (Submission System), §5.2 (File Storage)

---

## Overview

The submission system allows participants to submit work (metadata, files, structured payloads) during the active event window. Submissions are constrained by configurable limits and versioning rules. File uploads are stored on the filesystem with metadata in SQLite.

---

## Tasks

### 7.1 Create Submission

`POST /api/submissions`

**Request (multipart/form-data):**
```
title: "My Solution v2"
description: "Improved approach using..."
tags: ["optimization", "track-1"]
files: [file1.png, file2.zip]         # optional
payload_json: '{"model": "v2", ...}'  # optional, for agent submissions
```

**Server logic:**
1. Verify event state is `OPEN` (via EventGuard)
2. Verify participant is `active`
3. Check submission limits:
   - Count participant's submissions in the configured time window
   - Reject with `429` if limit exceeded
4. Create `Submission` record with `status='received'`
5. Process file uploads (if any):
   - Save to `/data/uploads/<event_id>/<participant_id>/<submission_id>/`
   - Calculate SHA-256 hash
   - Create `File` records
6. Queue scoring task (if auto-score is enabled)
7. Return submission with status

**Response:**
```json
{
  "id": "uuid",
  "participant_id": "uuid",
  "title": "My Solution v2",
  "description": "Improved approach using...",
  "tags": ["optimization", "track-1"],
  "files": [
    {
      "id": "uuid",
      "filename": "file1.png",
      "mime_type": "image/png",
      "size_bytes": 245760,
      "sha256": "abc123..."
    }
  ],
  "status": "received",
  "created_at": "2026-03-01T14:30:00Z"
}
```

### 7.2 Submission Limits

Configurable per event (in `event.config_json`):

| Setting | Default | Description |
|---------|---------|-------------|
| `submission_limit_per_participant` | 10 | Max submissions per window |
| `submission_limit_window_hours` | 24 | Rolling window in hours |
| `max_file_size_mb` | 10 | Max single file size |
| `max_files_per_submission` | 5 | Max files per submission |
| `allowed_file_types` | `["image/*", "application/zip", "application/json"]` | MIME type allowlist |

Enforcement:
```python
def check_submission_limits(db, participant_id, event_config) -> bool:
    window_start = datetime.utcnow() - timedelta(hours=event_config.window_hours)
    count = db.query(Submission).filter(
        Submission.participant_id == participant_id,
        Submission.created_at >= window_start,
        Submission.status != "withdrawn",
    ).count()
    return count < event_config.submission_limit
```

### 7.3 File Upload Handling

```python
async def save_upload(
    file: UploadFile,
    submission_id: str,
    participant_id: str,
    event_id: str,
) -> File:
    # Validate MIME type
    # Validate file size
    # Generate storage path
    upload_dir = Path(settings.UPLOAD_DIR) / event_id / participant_id / submission_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file, compute hash
    file_path = upload_dir / secure_filename(file.filename)
    sha256_hash = hashlib.sha256()
    size = 0
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
            sha256_hash.update(chunk)
            size += len(chunk)

    # Create File record
    return File(
        id=str(uuid4()),
        submission_id=submission_id,
        path=str(file_path.relative_to(settings.UPLOAD_DIR)),
        mime_type=file.content_type,
        size_bytes=size,
        sha256=sha256_hash.hexdigest(),
    )
```

Security:
- Sanitize filenames (`werkzeug.utils.secure_filename` or equivalent)
- Validate MIME type against allowlist
- Enforce max file size (reject early, don't buffer entire file)
- Never serve uploads directly — use a controlled download endpoint

### 7.4 Versioning Modes

Per event configuration, `leaderboard_mode` determines which submission counts:

| Mode | Behavior |
|------|----------|
| `latest` | Most recent submission is the active one |
| `best` | Highest-scoring submission is the active one |

Implementation:
- All submissions are stored regardless of mode
- Leaderboard query selects the "active" submission based on mode
- Participants can always see all their submissions and scores

### 7.5 View Submissions

#### Own submissions
`GET /api/submissions/mine`

Returns all submissions for the current user's participant(s), with scores.

#### Single submission
`GET /api/submissions/{submission_id}`

- Participant can view own submissions (with full details)
- Others can view public fields only (if leaderboard is public)

#### Download file
`GET /api/submissions/{submission_id}/files/{file_id}`

- Verify requester is the submission owner or admin
- Stream file from filesystem
- Set proper `Content-Type` and `Content-Disposition` headers

### 7.6 Withdraw Submission

`POST /api/submissions/{submission_id}/withdraw`

- Only the owning participant can withdraw
- Sets `status='withdrawn'`
- Withdrawn submissions don't count toward limits or leaderboard
- Cannot withdraw in `FROZEN` or later states

### 7.7 Admin Submission Management

#### List all submissions
`GET /api/admin/submissions`

**Query params:** `?participant_id=&status=&page=1&per_page=20`

#### View submission details (admin)
`GET /api/admin/submissions/{id}`

Full details including payload_json, files, scores.

#### Admin withdraw/disqualify
`PATCH /api/admin/submissions/{id}/status`

```json
{
  "status": "withdrawn",
  "reason": "Violated rules section 3"
}
```

- Log to audit log

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/submissions` | Participant | Create submission |
| GET | `/api/submissions/mine` | User | List own submissions |
| GET | `/api/submissions/{id}` | User/Public | View submission |
| GET | `/api/submissions/{id}/files/{fid}` | Owner/Admin | Download file |
| POST | `/api/submissions/{id}/withdraw` | Owner | Withdraw submission |
| GET | `/api/admin/submissions` | Admin | List all submissions |
| GET | `/api/admin/submissions/{id}` | Admin | View full details |
| PATCH | `/api/admin/submissions/{id}/status` | Admin | Change status |

---

## Acceptance Criteria

- [ ] Participants can create submissions with metadata and file uploads
- [ ] Submissions only accepted when event is `OPEN`
- [ ] Submission limits enforced (per participant, per time window)
- [ ] File uploads stored on filesystem, metadata in DB
- [ ] File types and sizes validated against allowlist
- [ ] Files served via controlled download endpoint (not direct filesystem)
- [ ] Participants can view and withdraw their own submissions
- [ ] Admin can view, filter, and moderate all submissions
- [ ] Withdrawn/disqualified submissions excluded from leaderboard
- [ ] Versioning mode (latest/best) correctly determines active submission

---

## Developer Notes

- Use FastAPI's `UploadFile` for file handling — it streams to temp file automatically
- For large files, use chunked reading to avoid memory issues on low-RAM Spaces
- `secure_filename()` is critical — never trust client-provided filenames
- The `payload_json` field is used by agent submissions (MVP-2) but should be accepted from MVP-1
- Consider adding a `submission_number` auto-increment per participant for human-friendly display
- SHA-256 hashes enable integrity verification during export
