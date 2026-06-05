# 17 — GitHub Export & Static Site

**Milestone:** MVP-4
**Priority:** Medium
**Dependencies:** [11-json-export](11-json-export.md), [14-task-queue-worker](14-task-queue-worker.md)
**Specs reference:** §7.7 (GitHub export), §5.3 (JSON archive)

---

## Overview

Optionally push the JSON export bundle to a GitHub repository for long-term archival and static site publishing (e.g., GitHub Pages). Also includes optional static HTML summary generation for human-browsable archives.

---

## Tasks

### 17.1 GitHub Integration Service

```python
# backend/app/services/github_service.py

import httpx

class GitHubService:
    def __init__(self, settings: Settings):
        self.repo = settings.GITHUB_EXPORT_REPO    # e.g., "org/hackritual-archive"
        self.token = settings.GITHUB_TOKEN
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def push_export(
        self,
        export_path: Path,
        branch: str = "gh-pages",
        commit_message: str = "Export HackRitual archive",
    ) -> dict:
        """Push export files to GitHub repo."""
        # 1. Get current branch SHA (or create branch)
        # 2. Create blobs for each file
        # 3. Create tree
        # 4. Create commit
        # 5. Update branch reference
```

### 17.2 GitHub Push Flow

1. **Validate configuration:**
   - `GITHUB_EXPORT_REPO` must be set
   - `GITHUB_TOKEN` must have repo write permissions
   - Test API connectivity before proceeding

2. **Prepare files:**
   - Start from the generated export bundle (ZIP)
   - Extract all JSON files
   - Optionally generate static HTML (§17.4)
   - Use deterministic filenames for meaningful Git diffs

3. **Push via Git Data API:**
   - Create blobs for each file (Base64 encoded)
   - Create a tree referencing all blobs
   - Create a commit pointing to the tree
   - Update the target branch reference

4. **Target branch options:**
   - `gh-pages` — for GitHub Pages deployment
   - `main` with `/docs` path — alternative Pages config
   - Configurable via `GITHUB_EXPORT_BRANCH` env var

### 17.3 Push Endpoint

`POST /api/admin/export/{export_id}/push-github`

```json
{
  "branch": "gh-pages",
  "commit_message": "Final export — HackRitual Bern 2026"
}
```

**Response:**
```json
{
  "status": "queued",
  "task_id": "uuid",
  "repo": "org/hackritual-archive",
  "branch": "gh-pages"
}
```

The push runs via the task queue (async) because it may take time for large exports.

#### Check push status
`GET /api/admin/export/{export_id}/push-status`

```json
{
  "status": "done",
  "commit_sha": "abc123...",
  "commit_url": "https://github.com/org/hackritual-archive/commit/abc123",
  "pages_url": "https://org.github.io/hackritual-archive/",
  "pushed_at": "2026-03-02T18:00:00Z"
}
```

### 17.4 Static Site Generation (Optional)

Generate a minimal static HTML site from the export data:

```
export/
├── index.html           # Event overview + results
├── leaderboard.html     # Full leaderboard table
├── participants.html    # Participant directory
├── submissions.html     # Submission gallery
├── style.css            # Minimal styling
├── manifest.json
├── participants.json
├── submissions.json
├── scores.json
└── ...
```

**index.html template:**
- Event title, dates, description
- Final leaderboard (top 10)
- Link to full leaderboard
- Submission count, participant count
- Export metadata (schema version, exported at)
- "Powered by HackRitual" footer

**leaderboard.html:**
- Full ranked table
- Score breakdown columns
- Sortable by column (client-side JS, minimal)

Use simple Jinja2 templates — no frontend framework needed for static pages.

### 17.5 Redaction in GitHub Export

Per specs §7.7:
- **Never export secrets** (JWT_SECRET, SMTP_PASS, API keys, GITHUB_TOKEN)
- Apply redaction settings from the export config
- Public mode: hash emails, sanitize audit log
- Validate no secrets present before pushing (automated check)

```python
def validate_no_secrets(export_dir: Path, settings: Settings) -> list[str]:
    """Scan export files for accidental secret leaks."""
    secrets_to_check = [
        settings.JWT_SECRET,
        settings.SMTP_PASS,
        settings.GITHUB_TOKEN,
    ]
    violations = []
    for file in export_dir.rglob("*.json"):
        content = file.read_text()
        for secret in secrets_to_check:
            if secret and secret in content:
                violations.append(f"Secret found in {file.name}")
    return violations
```

### 17.6 Deterministic Filenames

For meaningful Git diffs between exports:
- JSON files sorted by keys and arrays sorted by ID
- Consistent indentation (2 spaces)
- Stable filenames (no timestamps in names)
- Timestamps only inside file content

### 17.7 GitHub Token Permissions

Minimum required token permissions:
- `repo` scope (for private repos) OR `public_repo` (for public repos)
- Specifically: create blobs, create trees, create commits, update refs

Recommend using a **fine-grained personal access token** (PAT) with:
- Only the target repository selected
- Contents: Read and Write
- No other permissions

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/admin/export/{id}/push-github` | Admin | Push export to GitHub |
| GET | `/api/admin/export/{id}/push-status` | Admin | Check push status |

---

## Acceptance Criteria

- [ ] Export pushed to configured GitHub repository and branch
- [ ] Push runs asynchronously via task queue
- [ ] Admin can check push status and see commit URL
- [ ] Static HTML pages generated (if enabled) with leaderboard and results
- [ ] No secrets present in pushed files (automated validation)
- [ ] Deterministic file content for meaningful Git diffs
- [ ] GitHub Pages serves the archive at the expected URL
- [ ] Token permissions validated before attempting push
- [ ] Push failure provides clear error message to admin

---

## Developer Notes

- Use the GitHub Git Data API (not the Contents API) for atomic multi-file commits
- `httpx` is recommended for async HTTP calls to GitHub API
- Test with a private repo first to avoid accidental public exposure
- The static site should be self-contained — no external CDN dependencies
- Consider adding a `CNAME` file support for custom domains on GitHub Pages
- Rate limit: GitHub API allows 5000 requests/hour with a token — plenty for export
- If the repo doesn't exist, provide a helpful error message (don't auto-create)
