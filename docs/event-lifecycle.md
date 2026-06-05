# Event Lifecycle (The Ritual)

Every HackRitual deployment follows a linear state machine called **the Ritual**.
Only admins can advance the state. Transitions are logged to the audit log.

---

## State Machine

```
                        ┌─────────┐
         deploy +       │         │
         configure ────►│  DRAFT  │
                        │         │
                        └────┬────┘
                             │
                    admin opens event
                             │
                        ┌────▼────┐
                        │         │  ← participants register
                        │  OPEN   │  ← submissions accepted
                        │         │  ← scoring runs live
                        └────┬────┘
                             │
                   admin freezes event
                   (deadline reached)
                             │
                        ┌────▼────┐
                        │         │  ← no new submissions
                        │ FROZEN  │  ← scoring backlog drains
                        │         │  ← disputes resolved
                        └────┬────┘
                             │
                   admin finalises results
                             │
                        ┌────▼────┐
                        │         │  ← leaderboard locked
                        │  FINAL  │  ← scores immutable
                        │         │  ← export can be triggered
                        └────┬────┘
                             │
                   admin exports + archives
                             │
                        ┌────▼────┐
                        │         │  ← read-only
                        │ARCHIVED │  ← export bundle available
                        │         │  ← container can be removed
                        └─────────┘
```

---

## Permitted Operations by State

| Operation | DRAFT | OPEN | FROZEN | FINAL | ARCHIVED |
|-----------|-------|------|--------|-------|----------|
| Edit event metadata | admin | — | — | — | — |
| Register participant | admin | admin + self | — | — | — |
| Create submission | — | yes | — | — | — |
| Score submission | — | yes | yes | — | — |
| View leaderboard | admin | yes | yes | yes | yes |
| Freeze event | — | admin | — | — | — |
| Finalise results | — | — | admin | — | — |
| Export bundle | admin | admin | admin | admin | yes |
| Archive | — | — | — | admin | — |
| Any write | yes | yes | yes | — | — |

---

## State Transition Detail

### DRAFT → OPEN (Summon → Gather)

**Who:** Admin only

**Pre-conditions:**
- Event metadata configured (title, start, end, type)
- At least one scoring module or function defined
- Admin has reviewed participant registration settings

**Side effects:**
- Audit log entry: `event.opened`
- (Optional) notification email to registered participants

---

### OPEN → FROZEN (Create → Conclude)

**Who:** Admin only (typically at submission deadline)

**Pre-conditions:**
- Event is `OPEN`

**Side effects:**
- All in-flight scoring tasks continue running
- New submission attempts return `403 Forbidden`
- Audit log entry: `event.frozen`

---

### FROZEN → FINAL

**Who:** Admin only

**Pre-conditions:**
- Scoring backlog is empty (all submissions have a `SCORED` or `FAILED` status)
- Disputes resolved / disqualifications applied

**Side effects:**
- Leaderboard is locked (scores become immutable)
- Any re-score triggered after this point requires un-finalising (admin action, logged)
- Audit log entry: `event.finalised`

---

### FINAL → ARCHIVED

**Who:** Admin only

**Pre-conditions:**
- Export bundle generated successfully (or admin explicitly skips)

**Side effects:**
- All write endpoints return `423 Locked`
- Export bundle marked as final
- (Optional) push to GitHub repository
- Audit log entry: `event.archived`

---

## The Ritual Metaphor

| Phase | State | Meaning |
|-------|-------|---------|
| **Summon** | DRAFT → OPEN | The ritual circle is drawn; participants are called |
| **Gather** | OPEN (early) | Participants arrive and form their groups |
| **Create** | OPEN (active) | The forge is hot; work is submitted and scored |
| **Conclude** | OPEN → FROZEN → FINAL | The hammer falls; results are locked |
| **Archive** | FINAL → ARCHIVED | The ritual is inscribed and the circle released |

---

## Re-scoring

Re-scoring (triggering scoring again for all or selected submissions) is allowed:
- Any time in `OPEN` or `FROZEN`
- In `FINAL` only after an explicit admin "un-finalise" action (logged)

Re-scores update the `scores` table with a new `scorer_version` and timestamp.
The original scores are not deleted — a full audit trail is preserved.
