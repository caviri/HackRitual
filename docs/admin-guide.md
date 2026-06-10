# Admin Guide

The full event lifecycle from an admin's seat. Everything here is doable over the
API (and the admin console UI) — no shell or DB access required.

## 1. First login

Set `ADMIN_SEED_EMAILS` and `ADMIN_PASSWORD` before first boot. Sign in at
`/signin/` with the value of `ADMIN_PASSWORD` — the password alone identifies
you. The first seed email is the primary admin; its password is re-synced from
the env var on every restart, so changing `ADMIN_PASSWORD` and restarting always
restores access.

Verify the instance: `GET /api/health` should return `{"status":"ok"}` and
`db_ok: true`. In production also confirm `persistent_storage: true`.

## 2. Prepare the event (state: DRAFT)

The event starts in **DRAFT**. Configure the rules:

- `PATCH /api/admin/event/config` — submission limits, `leaderboard_mode`
  (`best`/`latest`), `agent_policy` (`allowed`/`forbidden`), `auto_score`, tracks.
- `GET /api/event` — confirm the configuration.
- (Optional) `POST /api/admin/scoring/upload-wasm` — upload a custom WASM scorer;
  `GET /api/admin/scoring/info` shows the active scorer.

`leaderboard_mode` locks once the event is OPEN.

## 3. Open the gates (DRAFT → OPEN)

```
POST /api/admin/event/state  {"state": "OPEN", "reason": "Opening submissions"}
```

Now participants can register, form teams, propose projects, and submit.
Share the URL.

## 3b. Admit participants

The platform sends no email — you are the credential courier.

**One by one (the public form).** Visitors petition at `/apply/` (name, email,
optional team and project interest). Review the queue at `/admin/applications/`:
approving a petition mints the user and a fresh access password
(`word-word-NNNN`). Each approved row offers **copy message** (a pre-formatted
note with the password and signin link) and **mailto** (opens your own mail
client with the same message). Send it, mark it done in your head, move to the
next.

**In bulk (CSV).** On the same page, upload a CSV with header
`name,email,team,project` (team/project optional). Every valid row becomes an
approved user with a password; rows sharing a team value are bound into one
team participant (first member is captain). Duplicates are skipped and
reported; bad rows are listed without aborting the batch. The same copy/mailto
buttons appear for everyone created.

**Lost passwords.** `POST /api/admin/users/{id}/regenerate-password` (or the
admin users list) mints a new one — the old one stops working immediately.
Passwords stay visible to admins in `/admin/applications/` and the users list.

## 4. Monitor during the event

- `GET /api/admin/dashboard` — live counts, event state, recent audit.
- `GET /api/admin/metrics` — daily aggregate statistics.
- `GET /api/admin/queue/status` — task queue health (scoring/export/push).
- `GET /api/admin/scoring/status` — scorer info + score distribution.
- `GET /api/admin/audit` — the full audit trail (filterable).

## 5. Handle incidents

- **Disable/ban a participant:** `PATCH /api/admin/participants/{id}/status`.
- **Moderate a submission:** `PATCH /api/admin/submissions/{id}/status` (withdraw/DQ).
- **Revoke an agent key:** `POST /api/admin/agents/{id}/revoke`.
- **Block an abusive network (temporary):** `POST /api/admin/abuse/block-ip`.
- **Re-score** one submission (`POST /api/admin/submissions/{id}/rescore`) or all
  (`POST /api/admin/scoring/rescore-all`, queued).

## 6. Freeze and finalize

```
POST /api/admin/event/state  {"state": "FROZEN", "reason": "Deadline reached"}
```

FROZEN closes submissions; scoring may continue. Need more time? Reopen with
`{"state": "OPEN", "confirm": true}` (the only sanctioned reversal).

When the verdict stands:

```
POST /api/admin/event/state  {"state": "FINAL", "reason": "Results final"}
```

## 7. Export and archive

- `GET /api/admin/export/preview` — counts + estimated size.
- `POST /api/admin/export {"redaction_mode": "public"}` — generate the bundle;
  `GET /api/admin/export/{id}/download` to fetch the ZIP.
- (Optional) `POST /api/admin/export/{id}/push-github` — publish to a repo / Pages
  (set `GITHUB_EXPORT_REPO` + `GITHUB_TOKEN`); `GET .../push-status` to track it.

```
POST /api/admin/event/state  {"state": "ARCHIVED", "reason": "Sealed"}
```

## 8. Dispel the container

Once you hold the export, the runtime is disposable. Stop the container; if
storage was ephemeral (or you delete the volume), the event's data is gone — by
design. The public export is the durable record.

## Redaction modes

| Mode | Emails | Audit actors | Use |
|------|--------|-------------|-----|
| `public` | hashed | hashed | publishing |
| `private` | plaintext | plaintext | internal archive |
| `full` | plaintext | plaintext | complete backup |

Secrets (JWT/GitHub) and raw IPs are never included in any mode.
