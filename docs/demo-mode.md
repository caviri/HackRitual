# Demo Mode

> *Five states, five small worlds. The ritual, shown at every hour of its life.*

A live event can only ever be in one state, holding one set of data. That is
correct for a real rite — and useless for showing one. Demo mode exists for the
showing: with `DEMO_STAGES=true`, the instance carries **five sandbox
databases**, one per state, each a complete SQLite snapshot pre-seeded to look
the way the ritual actually looks at that hour.

```
/data/app.db              ← the live event (the only DB a real rite uses)
/data/demo/draft.db       ← the circle being drawn
/data/demo/open.db        ← the forge running hot
/data/demo/frozen.db      ← the forge cooling, verdicts pending
/data/demo/final.db       ← the verdict inscribed
/data/demo/archived.db    ← the record sealed
```

---

## The stage bar — a demo instrument, not an event control

The stage selector at the top of every page exists **only for demo mode**. Its
purpose is to jump among *versions* of the rite — to see, side by side, what
DRAFT looks like before the gates open and what ARCHIVED looks like after the
record seals. It does not advance the event; the real state machine moves only
through `POST /api/admin/event/state`, forward, one gate at a time.

The bar appears in exactly two situations:

| Situation | What the bar flips |
|-----------|--------------------|
| `DEMO_STAGES=true` on the backend | The `demo_stage` cookie — every API call routes to that stage's snapshot |
| No backend reachable (static export) | Frontend mock datasets only |

On a live single-database deployment the bar stays hidden. If you are running a
real event, you should never see it — and your participants never will.

> Each visitor flips stages independently: the `demo_stage` cookie (or a
> `?stage=` query param, which wins) routes *their* requests. Two visitors can
> stand in different hours of the ritual at the same time. The **✕ live** chip
> clears the cookie and returns to the real event.

---

## What each snapshot holds

| State | The scene |
|-------|-----------|
| `DRAFT` | The circle is being drawn. Petitions wait at the desk; every participant still on the waitlist. No projects, no offerings. |
| `OPEN` | The gates are open. Twelve proposals with their covers, drafts in flight, one withdrawal. Nothing scored yet. |
| `FROZEN` | The forge cools. Finals sealed with plates and reports; the scorer has rendered its ladder — 90 / 80 / 60 / 50, no ties. |
| `FINAL` | The verdict is inscribed. Same sealed record, results public. |
| `ARCHIVED` | The ritual is complete. The record reads, nothing writes anew. |

---

## Walking the worlds

Sandboxes are **writable**. Step into a stage and sign in — the keeper's
`ADMIN_PASSWORD` opens every snapshot, and the demo cast holds fixed keys:

| Who | Key | Role |
|-----|-----|------|
| Ada Cole | `fern-lantern-4821` | participant |
| June K. | `moss-quill-7305` | participant |
| Photosym | `cedar-prism-1184` | participant |
| Jane Tu | `briar-comet-6592` | participant |
| Aram J. | `rowan-sigil-2417` | judge |
| Mila A. | `heron-ember-9038` | judge |

Whatever is written inside a stage stays inside that stage — and a session
forged in one snapshot does not carry into another (each holds its own users;
sign in again where you land).

When a sandbox grows messy, raze and regrow all five:

```
POST /api/admin/demo/rebuild
```

The tables are dropped and reseeded in place; the snapshot returns to its
appointed scene.

---

## What sandboxes will not do

The background worker, the export bundle, GitHub pushes, and queue retries
serve the **live database only** — inside a sandbox those endpoints answer
`409`. Scoring on submission create still works (it runs in-request), so the
forge feels alive; only the machinery that produces real artefacts is fenced.

---

## Summoning it

```
DEMO_STAGES=true
```

Set the variable and restart. The first boot builds the five snapshots (a few
seconds of carving); later boots find them in place and pass. See
[Configuration](configuration.md) for the full variable reference.
