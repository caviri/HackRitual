# HackRitual — Writing Style Guide

> *Words are part of the ritual. Use them with intention.*

This guide defines the voice, vocabulary, and tone for all HackRitual documentation,
changelogs, comments, and user-facing text. The project has a personality — lean into it.

---

## The Voice

HackRitual sits at the intersection of **hacker culture** and **ritualistic ceremony**.
Think: a wizard who also reads RFCs. Earnest, a little strange, technically precise,
never corporate.

The tone is:
- **Purposeful** — every word earns its place
- **Slightly arcane** — the metaphors are ritual, alchemical, incantatory
- **Never whimsical for its own sake** — the ritual framing must still make technical sense
- **Dry, not theatrical** — no exclamation marks, no emoji, no marketing speak

If a sentence could appear in a SaaS landing page, rewrite it.

---

## The Core Metaphor

A hackathon is a **ritual**. This is not decoration — it shapes every choice of word.

| Technical concept | Ritual framing |
|-------------------|----------------|
| Deploy the container | Summon / invoke |
| Tear down the container | Dispel / dissolve |
| Run the event | Perform the ritual |
| Participants | Participants (or *the gathered*) |
| Submit a project | Offer a submission |
| Admin setup | Inscribe / bind the configuration |
| Database migrations | Bind the schema / carve the tables |
| Seed initial data | Invoke / invoke the first record |
| Event state changes | The ritual advances |
| Export the JSON archive | Seal the artefact |
| Health check | Vital signs / heartbeat |
| Docker image | The vessel / the container |
| Configuration | The inscription / the binding |
| First admin user | The summoner |
| JWT secret | The signing key / the seal |

Use these sparingly and consistently. One well-placed ritual word per sentence is enough.
Do not stack metaphors.

---

## Event States

The five states are always written in `ALL_CAPS`. Their descriptions follow this register:

| State | Phrasing |
|-------|---------|
| `DRAFT` | The circle is drawn. The configuration is being set. |
| `OPEN` | The gates are open. Participants gather, submissions flow. |
| `FROZEN` | The forge cools. Submissions are closed; scoring begins. |
| `FINAL` | The verdict is inscribed. Results are public. |
| `ARCHIVED` | The ritual is complete. The artefact is sealed. |

---

## Changelog Entries

Use **"Bound"** instead of "Added". Use **"Unbound"** instead of "Removed".
Use **"Recast"** instead of "Changed". Use **"Mended"** instead of "Fixed".

Each entry opens with a one- or two-sentence scene-setter in the ritual voice,
then bullets of plain technical facts.

**Good:**
```markdown
### Bound — MVP-1 Step 02: Database Layer (2026-03-06)

The schema is inscribed. The SQLite stone is carved with 12 tables,
all relationships sealed with foreign keys.

- `backend/app/database.py` — WAL mode, busy_timeout, FK enforcement
- Initial Alembic migration: all 12 tables
```

**Bad:**
```markdown
### Added — Database Layer

Added SQLAlchemy models and Alembic migrations for the database layer.
```

---

## README / Documentation

- Section headings should feel like chapter titles, not nav labels.
  - Good: `Deploy to Hugging Face Spaces`, `The Ritual States`, `Invoke the Dev Server`
  - Bad: `Installation`, `Usage`, `Getting Started`
- Code blocks are plain. No ritual language inside shell commands or code.
- Bullet lists are factual. The prose around them carries the voice.

---

## Code Comments

In code, the ritual tone is used sparingly — only in module-level docstrings
and high-level architectural comments. Function docstrings are plain and technical.

**Good (module docstring):**
```python
"""
SQLite database engine, session factory, and FastAPI dependency.

The memory of the ritual — WAL mode, foreign keys enforced, busy_timeout
set so brief lock contention never halts the ceremony.
"""
```

**Good (function docstring — plain):**
```python
def check_db() -> bool:
    """Return True if DB is reachable via a SELECT 1."""
```

**Bad (overloaded):**
```python
def check_db() -> bool:
    """Consult the oracle. Return True if the stone speaks."""
```

---

## Things to Avoid

- **Exclamation marks.** The ritual is serious.
- **Emoji.** Not in docs, comments, or changelogs. Ever.
- **Marketing language.** "Powerful", "seamless", "robust", "next-gen" — none of these.
- **Passive voice in changelogs.** "Was added" → "Bound".
- **Over-stacking metaphors.** One ritual word per clause is enough. Two is too many.
- **Forced ritual words for mundane things.** If something is just a config file, say config file.

---

## Quick Reference

| Instead of… | Write… |
|-------------|--------|
| Deploy | Summon / invoke |
| Tear down | Dispel |
| Install dependencies | Bind the dependencies |
| Configure | Inscribe |
| Run migrations | Bind the schema |
| Export | Seal / export the artefact |
| The event | The ritual |
| Getting started | Quick start / invocation |
| Added (changelog) | Bound |
| Removed (changelog) | Unbound |
| Changed (changelog) | Recast |
| Fixed (changelog) | Mended |
| The whole system | The vessel |

---

*When in doubt: one strange word in an otherwise plain sentence lands harder than
a sentence drowning in metaphor.*
