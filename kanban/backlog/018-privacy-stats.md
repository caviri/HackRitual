---
id: "018"
title: "Privacy & Statistics"
type: chore
status: backlog
estimate: "2d"
size: M
depends_on: []
blocks: []
spec: "specs/specs/18-privacy-statistics.md"
tags: [privacy, statistics, cross-cutting]
---

# Privacy & Statistics

Data minimisation, anonymisation options, and aggregate statistics for the event.

## Tasks

- [ ] Anonymisation mode: replace participant identifiers with pseudonyms in export
- [ ] `GET /api/stats/public` — aggregate stats safe for public display (counts, not PII)
- [ ] `GET /api/admin/stats` — full stats including email domains, submission rates, timing
- [ ] Data retention policy: configurable purge schedule for PII after ARCHIVED state
- [ ] `DELETE /api/admin/participants/{id}/purge-pii` — remove email from soft-deleted user
- [ ] Audit log redaction for sensitive fields (mask emails in log entries)
- [ ] GDPR-aligned export: participant can request their own data bundle

## Notes

- Integrate incrementally alongside other steps
- Anonymisation applies to JSON export (Step 11) and GitHub export (Step 17)
- No external analytics or tracking — all stats computed from local DB
