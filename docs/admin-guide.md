# Admin Guide

The full event lifecycle from an admin's seat. Everything here is doable over the
API (and the admin console UI) — no shell or DB access required.

## 1. First login

Set `ADMIN_SEED_EMAILS` before first boot. Sign in with that email (you receive a
six-digit code by email; in dev SMTP mode it prints to the server log). On first
login your user is granted the `admin` role.

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

Now participants can register, form teams, propose projects, and submit. A
phase-change notice goes out to everyone in the event. Share the URL.

## 4. Monitor during the event

- `GET /api/admin/dashboard` — live counts, event state, recent audit.
- `GET /api/admin/metrics` — daily aggregate statistics.
- `GET /api/admin/queue/status` — task queue health (scoring/email/export).
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

Secrets (JWT/SMTP/GitHub) and raw IPs are never included in any mode.
