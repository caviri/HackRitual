"""
Full autonomous hackathon test — against the LIVE production server.

Runs inside the running `app` container and drives the real uvicorn instance over
HTTP (http://localhost:7860) with the whole production stack active: migrations,
the queue worker, the rate-limit middleware, the static frontend.

Reuses the ritual orchestrator (admin + human participants + an autonomous agent)
and adds production-only checks: rate-limit headers, the async worker draining the
queue, the health probe, and the admin dashboard/metrics.

    docker compose exec -T -w /app/backend app python scripts/live_hackathon.py
"""

from __future__ import annotations

import asyncio
import sys

from httpx import AsyncClient

from app.services.ritual_sim import PHASES, Ritual, _ensure_event

BASE = "http://localhost:7860"

_results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    _results.append((bool(ok), label))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")


def say(msg: str) -> None:
    print(msg)


async def wait_for_health(client: AsyncClient, tries: int = 30) -> dict:
    for _ in range(tries):
        try:
            r = await client.get("/api/health")
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        await asyncio.sleep(1)
    raise RuntimeError("server never became healthy")


async def main() -> int:
    print("\n=== HackRitual — full autonomous hackathon test (LIVE) ===\n")
    _ensure_event(fresh=True)  # reset the live event to DRAFT

    async with AsyncClient(base_url=BASE, timeout=30) as client:
        # ── Infrastructure ────────────────────────────────────────────────
        print("· Infrastructure")
        health = await wait_for_health(client)
        check(health.get("status") == "ok", "health endpoint returns ok")
        check(health.get("db_ok") is True, "database reachable (migrated)")
        check(health.get("event_id") == "hackritual-live-test", "correct event seeded")

        ev = await client.get("/api/event")
        check(
            "x-ratelimit-limit" in {k.lower() for k in ev.headers},
            "rate-limit headers present on API responses",
        )

        # ── The ritual: admin + participants + agent, full lifecycle ───────
        print("\n· Running the ritual (admin, participants, agent)")
        rite = Ritual(client, lambda kind, message: say(f"    {message}"))
        await rite.summon_cast()
        for title, method in PHASES:
            say(f"\n  ── {title} ──")
            await getattr(rite, method)()
        await rite.chronicle()
        rep = rite.report
        rep.final_state = rep.states_visited[-1] if rep.states_visited else ""

        print("\n· Lifecycle assertions")
        check(rep.states_visited == ["OPEN", "FROZEN", "FINAL", "ARCHIVED"],
              "event walked OPEN → FROZEN → FINAL → ARCHIVED")
        check(rep.participants_created >= 3, f"participants registered ({rep.participants_created})")
        check(rep.teams_created >= 1 and rep.members_joined >= 1, "team formed and joined")
        check(rep.projects_proposed >= 2, f"projects proposed ({rep.projects_proposed})")
        check(rep.submissions_created >= 3, f"submissions offered ({rep.submissions_created})")
        check(rep.agent_submissions >= 1, "autonomous agent submitted via API key")
        check(rep.files_attached >= 1, "file attached to a submission")
        check(rep.dashboard_participants >= 1, "admin dashboard reported live metrics")
        check(rep.leaderboard_entries >= 1, "leaderboard ranked the offerings")
        check(rep.scores_overridden >= 1 and rep.top_score >= 95.0, "admin score override applied")
        check(rep.export_files >= 6, f"export artefact built ({rep.export_files} files)")
        check(rep.emails_sent >= 4, f"notices dispatched ({rep.emails_sent})")
        check(rep.wards_held >= 4, f"state-machine wards held ({rep.wards_held})")
        check(rep.audit_entries >= 5, f"audit log inscribed ({rep.audit_entries})")

        # ── Async worker (production-only) ─────────────────────────────────
        print("\n· Async task queue + worker")
        admin = rite.admin_headers
        rescore = await client.post("/api/admin/scoring/rescore-all", headers=admin)
        queued = rescore.json().get("queued", 0) if rescore.status_code == 200 else 0
        check(queued >= 1, f"rescore-all enqueued tasks ({queued})")

        drained = False
        for _ in range(30):
            await asyncio.sleep(1)
            st = await client.get("/api/admin/queue/status", headers=admin)
            if st.status_code == 200:
                s = st.json()
                if s.get("queued", 0) == 0 and s.get("running", 0) == 0 and s.get("done", 0) >= queued:
                    drained = True
                    break
        check(drained, "worker drained the queue (tasks processed to done)")

        # ── Metrics dashboard ──────────────────────────────────────────────
        print("\n· Metrics")
        m = await client.get("/api/admin/metrics", headers=admin)
        mok = m.status_code == 200 and m.json()["totals"]["submissions"] >= 1
        check(mok, "metrics dashboard reflects the event")

    # ── Verdict ────────────────────────────────────────────────────────────
    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n=== {passed}/{total} checks passed ===")
    failed = [label for ok, label in _results if not ok]
    if failed:
        print("FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print("All checks passed — the ritual runs end to end on the live stack.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
