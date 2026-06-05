---
id: "017"
title: "GitHub Export & Static Site"
type: feature
status: backlog
estimate: "4d"
size: L
depends_on: ["011"]
blocks: []
spec: "specs/specs/17-github-export.md"
tags: [export, github, static-site]
---

# GitHub Export & Static Site

Push the event archive (from Step 11) to a GitHub repository and optionally generate a GitHub Pages static site.

## Tasks

- [ ] `POST /api/export/github` — push JSON bundle to `GITHUB_EXPORT_REPO` via GitHub API
- [ ] GitHub API integration using `GITHUB_TOKEN` (configured in env)
- [ ] Generate static HTML summary page from bundle (leaderboard + results)
- [ ] Push static site to `gh-pages` branch for GitHub Pages hosting
- [ ] `GET /api/export/github/status` — check push status via Task model
- [ ] Handle rate limits and large file uploads via chunked GitHub API calls

## Env Vars Required

```
GITHUB_EXPORT_REPO=owner/repo
GITHUB_TOKEN=ghp_...
```

## Notes

- Optional feature (skipped if env vars not set)
- Export bundle (Step 11) must be complete before GitHub push
- Task queue (Step 14) handles the async push with retry logic
- Token stored securely; masked in `hackritual info` output
