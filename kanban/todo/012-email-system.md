---
id: "012"
title: "Email System"
type: chore
status: todo
estimate: "2d"
size: S
depends_on: ["002"]
blocks: []
spec: "specs/specs/12-email-system.md"
tags: [email, smtp, notifications]
---

# Email System

Extend the existing SMTP email service (used for magic login codes) with event notification templates.

## Tasks

- [ ] Email template system: HTML + plain text, Jinja2 or f-string based
- [ ] `invitation` template — sent when admin invites a participant
- [ ] `submission_received` template — confirmation when submission is created
- [ ] `submission_scored` template — notify participant when score is available
- [ ] `event_opening` template — broadcast when event transitions to OPEN
- [ ] `event_closing` template — broadcast when event transitions to FROZEN
- [ ] `POST /api/admin/email/broadcast` — send custom email to all active participants
- [ ] Queue all outbound emails via Task model (async, retryable)
- [ ] Dev/console mode already implemented in Step 03; no changes needed there

## Notes

- `app/services/email.py` already has SMTP dispatch logic from Step 03
- The Task queue (Step 14) will handle retries for failed sends
- Console mode (`SMTP_HOST=localhost`) prints to stdout — useful in tests
