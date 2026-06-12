"""
The Rite of Many Hands — a ritual simulator.

A cast of agents (humans and machines) is summoned, the gates are opened, teams
form, the forge runs and cools, a verdict is inscribed, and the record is sealed.
The whole lifecycle is driven over the real REST API exactly as a client would,
so this doubles as an end-to-end exercise of the platform and a living demo.

Agents authenticate with bearer tokens — the access path the middleware reserves
for API/agent callers. Tokens are minted directly from the auth service (the
console magic-code is not machine-readable), then every action goes through HTTP.

Run it three ways:

    hackritual simulate                       # narrated, in-process
    docker compose run --rm test \\
        python -m app.services.ritual_sim     # same, inside a container
    # or import run_ritual() from a test and assert on the RitualReport

The phase coordinator (`PHASES`) is data-driven: each phase names a target state
and the act that fills it, so new phases slot in without touching the engine.
"""

from __future__ import annotations

import asyncio
import io
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field

from httpx import ASGITransport, AsyncClient

# A narration sink: (kind, message). Kinds: phase, act, ward, ok, warn, chronicle.
Narrator = Callable[[str, str], None]


def _noop(kind: str, message: str) -> None:  # default: stay silent
    pass


# --------------------------------------------------------------------------- #
# The cast
# --------------------------------------------------------------------------- #
@dataclass
class Agent:
    """One summoned participant in the ritual."""

    name: str
    email: str
    kind: str  # "human" | "agent"
    token: str = ""
    participant_id: str | None = None

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}


# Humans and machines. The captain forms the team; the rest join by invite.
CAST: list[Agent] = [
    Agent("Ada Cole", "ada@rite.local", "human"),
    Agent("June K.", "june@rite.local", "human"),
    Agent("Photosym", "photosym@rite.local", "human"),
    Agent("marrowbot", "marrowbot@rite.local", "agent"),
    Agent("rendermouse", "rendermouse@rite.local", "agent"),
]

# A latecomer who arrives once the gates have closed — to prove the ward holds.
LATECOMER = Agent("the_straggler", "straggler@rite.local", "human")

ADMIN_EMAIL = "archivist@rite.local"


# --------------------------------------------------------------------------- #
# The chronicle of the run
# --------------------------------------------------------------------------- #
@dataclass
class RitualReport:
    """A structured account of what the ritual did — for tests and summaries."""

    final_state: str = ""
    states_visited: list[str] = field(default_factory=list)
    participants_created: int = 0
    teams_created: int = 0
    members_joined: int = 0
    projects_proposed: int = 0
    submissions_created: int = 0
    agent_submissions: int = 0
    files_attached: int = 0
    dashboard_participants: int = 0
    leaderboard_entries: int = 0
    scores_overridden: int = 0
    top_score: float = 0.0
    export_files: int = 0
    export_bytes: int = 0
    wards_held: int = 0          # operations correctly refused by the rules
    audit_entries: int = 0
    transcript: list[tuple[str, str]] = field(default_factory=list)

    def record(self, narrator: Narrator, kind: str, message: str) -> None:
        self.transcript.append((kind, message))
        narrator(kind, message)


# --------------------------------------------------------------------------- #
# Token minting (the only non-HTTP step)
# --------------------------------------------------------------------------- #
def _mint_token(email: str, name: str, role: str) -> str:
    """Create-or-fetch a user and return a signed bearer token."""
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).first()
        if user is None:
            user = User(email=email, role=role, display_name=name)
            db.add(user)
            db.commit()
            db.refresh(user)
        elif user.role != role:
            user.role = role
            db.commit()
        return create_jwt(user)


def _ensure_event(fresh: bool) -> None:
    """
    Make sure the singleton Event exists. When ``fresh`` is set, return it to
    DRAFT with default config so the ritual starts from the top — the simulator
    is a demo tool, so a clean slate is the friendly default.
    """
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event

    with SessionLocal() as db:
        event = db.get(Event, settings.event_id)
        if event is None:
            event = Event(
                id=settings.event_id,
                title=settings.event_title,
                type=settings.event_type,
                state="DRAFT",
                start_at=settings.event_start,
                end_at=settings.event_end,
            )
            db.add(event)
        if fresh:
            event.state = "DRAFT"
            event.config_json = None
        db.commit()


# --------------------------------------------------------------------------- #
# The orchestrator
# --------------------------------------------------------------------------- #
class Ritual:
    """Drives one event through its whole lifecycle over the API."""

    def __init__(self, client: AsyncClient, narrator: Narrator = _noop) -> None:
        self.client = client
        self.narrator = narrator
        self.report = RitualReport()
        self.admin_headers: dict = {}
        self.team_invite: str | None = None
        self.team_id: str | None = None
        self.marrow_project: str | None = None  # reused to test the FROZEN ward
        self.sealed_submission_id: str | None = None  # the team's final offering

    # -- narration helpers --------------------------------------------------- #
    def _say(self, kind: str, message: str) -> None:
        self.report.record(self.narrator, kind, message)

    # -- transitions --------------------------------------------------------- #
    async def _transition(self, to: str, reason: str, confirm: bool = False) -> None:
        r = await self.client.post(
            "/api/admin/event/state",
            json={"state": to, "reason": reason, "confirm": confirm},
            headers=self.admin_headers,
        )
        r.raise_for_status()
        data = r.json()
        self.report.states_visited.append(data["state"])
        self._say(
            "phase",
            f"{data['previous_state']} → {data['state']}  ·  {reason}",
        )

    # -- phases -------------------------------------------------------------- #
    async def phase_draft(self) -> None:
        """DRAFT — the circle is drawn and the rules inscribed."""
        self._say("act", "The Archivist draws the circle and inscribes the rules.")
        r = await self.client.patch(
            "/api/admin/event/config",
            json={
                "submission_limit_per_participant": 3,
                "leaderboard_mode": "best",
                "agent_policy": "allowed",
                "tracks": [
                    {"id": "open", "name": "Open Track", "description": "anything goes"},
                    {"id": "tools", "name": "Small Tools", "description": "one-file rituals"},
                ],
            },
            headers=self.admin_headers,
        )
        r.raise_for_status()
        cfg = r.json()["config"]
        self._say(
            "ok",
            f"Config bound: {len(cfg['tracks'])} tracks, "
            f"limit {cfg['submission_limit_per_participant']}, "
            f"agents {cfg['agent_policy']}.",
        )

    async def phase_open(self) -> None:
        """OPEN — the gates open; the gathered register and teams form."""
        await self._transition("OPEN", "Opening the gates for the gathered")

        # The leaderboard mode is now locked — prove the ward refuses the change.
        r = await self.client.patch(
            "/api/admin/event/config",
            json={"leaderboard_mode": "latest"},
            headers=self.admin_headers,
        )
        if r.status_code == 409:
            self.report.wards_held += 1
            self._say("ward", "leaderboard_mode is sealed once OPEN — the change is refused (409).")

        # Each agent registers a solo participant.
        for agent in CAST:
            r = await self.client.post(
                "/api/participants",
                json={
                    "type": agent.kind,
                    "display_name": agent.name,
                    "affiliation": "summoned for the rite",
                },
                headers=agent.headers,
            )
            if r.status_code in (200, 201):
                agent.participant_id = r.json()["id"]
                self.report.participants_created += 1
                self._say("act", f"{agent.name} ({agent.kind}) steps into the circle.")
            elif r.status_code == 400:
                # Already gathered (re-run) — tolerate it.
                self._say("warn", f"{agent.name} was already among the gathered.")

        # The captain forms a team; two others join by invite.
        captain, *rest = CAST
        r = await self.client.post(
            "/api/teams",
            json={"display_name": "the_owls", "affiliation": "Lisbon collective"},
            headers=captain.headers,
        )
        if r.status_code in (200, 201):
            body = r.json()
            self.team_id = body["id"]
            self.team_invite = body.get("invite_code")
            self.report.teams_created += 1
            self._say("act", f"{captain.name} forms the team 'the_owls' (invite {self.team_invite}).")

        if self.team_invite:
            for joiner in rest[:2]:
                r = await self.client.post(
                    "/api/teams/join",
                    params={"invite_code": self.team_invite},
                    headers=joiner.headers,
                )
                if r.status_code in (200, 201):
                    self.report.members_joined += 1
                    self._say("act", f"{joiner.name} joins 'the_owls'.")

    async def _propose(self, agent: Agent, participant_id: str, title: str, desc: str) -> str | None:
        r = await self.client.post(
            "/api/projects",
            json={
                "title": title,
                "description": desc,
                "proposed_by_participant_id": participant_id,
            },
            headers=agent.headers,
        )
        if r.status_code in (200, 201):
            self.report.projects_proposed += 1
            self._say("act", f"{agent.name} proposes '{title}'.")
            return r.json()["id"]
        return None

    async def _offer(
        self, agent: Agent, project_id: str, participant_id: str, title: str, result: str
    ) -> str | None:
        r = await self.client.post(
            "/api/submissions",
            json={
                "project_id": project_id,
                "participant_id": participant_id,
                "title": title,
                "description": f"{agent.name}'s offering toward {title}",
                "result": result,
            },
            headers=agent.headers,
        )
        if r.status_code in (200, 201):
            self.report.submissions_created += 1
            self._say("act", f"{agent.name} offers '{title}'.")
            return r.json()["id"]
        return None

    async def phase_forge(self) -> None:
        """OPEN — the forge runs hot: projects are proposed, work is offered."""
        captain, marrow, render = CAST[0], CAST[3], CAST[4]

        # The team offers its work and seals it as final.
        if self.team_id:
            proj = await self._propose(
                captain, self.team_id, "mycelium-mesh",
                "gossip protocols modelled on fungal nutrient routing",
            )
            if proj:
                sub_id = await self._offer(
                    captain, proj, self.team_id, "mycelium-mesh", "demo.mp4 · report.pdf"
                )
                if sub_id:
                    self.sealed_submission_id = sub_id
                    r = await self.client.patch(
                        f"/api/submissions/{sub_id}",
                        json={"status": "final"},
                        headers=captain.headers,
                    )
                    if r.status_code == 200:
                        self._say("act", "the_owls seal 'mycelium-mesh' as final.")
                    # Attach the artefact's evidence — a report file.
                    fr = await self.client.post(
                        f"/api/submissions/{sub_id}/files",
                        files={
                            "file": (
                                "report.md",
                                b"# mycelium-mesh\ngossip over fungal routing.\n",
                                "text/markdown",
                            )
                        },
                        headers=captain.headers,
                    )
                    if fr.status_code == 201:
                        self.report.files_attached += 1
                        self._say("act", "the_owls attach report.md to their offering.")

        # A solo agent offers its work.
        if render.participant_id:
            proj = await self._propose(
                render, render.participant_id, "fern-fold",
                "tensor folding inspired by leaf phyllotaxis",
            )
            if proj:
                await self._offer(render, proj, render.participant_id, "fern-fold", "wip")

        # An autonomous agent is summoned and submits over the API (X-API-Key).
        ar = await self.client.post(
            "/api/agents", json={"name": "scout-bot"}, headers=captain.headers
        )
        if ar.status_code == 201:
            key = ar.json()["api_key"]
            self._say("act", "Ada Cole summons the agent 'scout-bot' (key issued once).")
            sr = await self.client.post(
                "/api/agent/submissions",
                json={
                    "title": "scout-run",
                    "description": "an autonomous sweep",
                    "payload": {"model": "v1", "runs": 3},
                },
                headers={"X-API-Key": key},
            )
            if sr.status_code == 201:
                self.report.agent_submissions += 1
                self.report.submissions_created += 1
                self._say("act", "scout-bot offers its run over the agent API.")

        # marrowbot pushes past the per-participant submission cap — the ward must hold.
        if marrow.participant_id:
            self.marrow_project = await self._propose(
                marrow, marrow.participant_id, "spore-print",
                "datasets fingerprinted as cellular-automata states",
            )
            if self.marrow_project:
                for _ in range(6):
                    r = await self.client.post(
                        "/api/submissions",
                        json={
                            "project_id": self.marrow_project,
                            "participant_id": marrow.participant_id,
                            "title": "spore-print",
                            "result": "iteration",
                        },
                        headers=marrow.headers,
                    )
                    if r.status_code == 429:
                        self.report.wards_held += 1
                        self._say("ward", "the submission cap (3/window) holds — further offering refused (429).")
                        break
                    if r.status_code in (200, 201):
                        self.report.submissions_created += 1

        r = await self.client.get("/api/submissions")
        on_record = len(r.json()) if r.status_code == 200 else 0
        self._say(
            "ok",
            f"The forge runs hot. {self.report.submissions_created} offerings made, "
            f"{on_record} on record.",
        )

    async def phase_freeze(self) -> None:
        """FROZEN — the forge cools; the gates close. The wards are tested."""
        await self._transition("FROZEN", "Deadline reached — the forge cools")

        # Ward: configuration is sealed once the event leaves DRAFT/OPEN.
        r = await self.client.patch(
            "/api/admin/event/config",
            json={"registration_open": False},
            headers=self.admin_headers,
        )
        if r.status_code == 409:
            self.report.wards_held += 1
            self._say("ward", "Configuration is sealed while FROZEN — the edit is refused (409).")

        # Ward: the state machine refuses to walk backwards.
        r = await self.client.post(
            "/api/admin/event/state",
            json={"state": "DRAFT"},
            headers=self.admin_headers,
        )
        if r.status_code == 409:
            self.report.wards_held += 1
            self._say("ward", "FROZEN cannot fall back to DRAFT — the transition is refused (409).")

        # Ward: the forge is shut — no new work is accepted while FROZEN.
        if self.marrow_project and CAST[3].participant_id:
            r = await self.client.post(
                "/api/submissions",
                json={
                    "project_id": self.marrow_project,
                    "participant_id": CAST[3].participant_id,
                    "title": "too late",
                    "result": "x",
                },
                headers=CAST[3].headers,
            )
            if r.status_code == 409:
                self.report.wards_held += 1
                self._say("ward", "the forge is shut — an offering while FROZEN is refused (409).")

        # A latecomer tries to register after the gates have closed. (Best-effort
        # demonstration — gating lives in the participant service, not the event
        # machine, so it is narrated but not relied upon.)
        await self._summon(LATECOMER, role="user")
        r = await self.client.post(
            "/api/participants",
            json={"type": "human", "display_name": LATECOMER.name},
            headers=LATECOMER.headers,
        )
        if r.status_code in (400, 409):
            self._say("act", f"{LATECOMER.name} arrives too late — registration refused.")

    async def _read_leaderboard(self) -> list[dict]:
        r = await self.client.get("/api/leaderboard")
        return r.json().get("entries", []) if r.status_code == 200 else []

    async def phase_score(self) -> None:
        """FROZEN — the offerings are weighed. Scoring is permitted; the gates are not."""
        # The Archivist consults the console before judging.
        dash = await self.client.get("/api/admin/dashboard", headers=self.admin_headers)
        if dash.status_code == 200:
            m = dash.json()["metrics"]
            self.report.dashboard_participants = m["participants_total"]
            self._say(
                "act",
                f"The console reads: {m['participants_total']} gathered, "
                f"{m['submissions_total']} offerings, "
                f"{m['scoring_queue_depth']} awaiting a score.",
            )

        # Submissions were auto-scored on creation; read the standing.
        entries = await self._read_leaderboard()
        self.report.leaderboard_entries = len(entries)
        if entries:
            top = entries[0]
            self._say(
                "act",
                f"The board stands: {top['participant']['display_name']} "
                f"leads at {top['score']}.",
            )

        # The Archivist lifts the sealed offering by hand — an override, logged.
        if self.sealed_submission_id:
            sr = await self.client.get(
                f"/api/submissions/{self.sealed_submission_id}/score"
            )
            if sr.status_code == 200:
                score_id = sr.json()["id"]
                o = await self.client.patch(
                    f"/api/admin/scores/{score_id}",
                    json={"score_value": 95, "reason": "judged best in show"},
                    headers=self.admin_headers,
                )
                if o.status_code == 200:
                    self.report.scores_overridden += 1
                    self._say("act", "The Archivist raises 'mycelium-mesh' to 95 by hand.")

        # Re-read — the override reshapes the order.
        entries = await self._read_leaderboard()
        if entries:
            top = entries[0]
            self.report.top_score = top["score"]
            self._say(
                "ok",
                f"Final standing: {top['participant']['display_name']} at {top['score']}.",
            )

    async def phase_final(self) -> None:
        """FINAL — the verdict is inscribed."""
        await self._transition("FINAL", "The verdict is inscribed")

    async def phase_archive(self) -> None:
        """ARCHIVED — the record is sealed."""
        await self._transition("ARCHIVED", "The ritual is complete; the record is sealed")

    async def phase_export(self) -> None:
        """The artefact is drawn from the sealed record — a structured bundle."""
        prev = await self.client.get(
            "/api/admin/export/preview", headers=self.admin_headers
        )
        if prev.status_code == 200:
            counts = prev.json()["counts"]
            self._say(
                "act",
                f"Preview: {counts['participants']} participants, "
                f"{counts['submissions']} submissions, {counts['scores']} scores.",
            )

        gen = await self.client.post(
            "/api/admin/export",
            json={"redaction_mode": "public"},
            headers=self.admin_headers,
        )
        if gen.status_code != 200:
            self._say("warn", "the artefact could not be drawn.")
            return
        export_id = gen.json()["export_id"]
        self._say("act", f"Bundle forged (public redaction, {gen.json()['size_bytes']} bytes).")

        dl = await self.client.get(
            f"/api/admin/export/{export_id}/download", headers=self.admin_headers
        )
        if dl.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(dl.content)) as zf:
                names = zf.namelist()
            self.report.export_files = len(names)
            self.report.export_bytes = len(dl.content)
            self._say(
                "ok",
                f"The artefact holds {len(names)} files: {', '.join(sorted(names))}.",
            )

    async def chronicle(self) -> None:
        """Read back the audit log — the register every gate kept."""
        r = await self.client.get("/api/admin/event/audit", headers=self.admin_headers)
        if r.status_code == 200:
            entries = r.json()
            self.report.audit_entries = len(entries)
            self._say("chronicle", f"The chronicle holds {len(entries)} inscribed acts:")
            # Oldest first reads like a story.
            for e in reversed(entries):
                meta = e.get("metadata") or {}
                if e["action"] == "event.transition":
                    self._say(
                        "chronicle",
                        f"  · {meta.get('from')} → {meta.get('to')}  ({meta.get('reason')})",
                    )
                else:
                    self._say(
                        "chronicle",
                        f"  · config touched: {', '.join(meta.get('fields', []))}",
                    )

    # -- setup --------------------------------------------------------------- #
    async def _summon(self, agent: Agent, role: str) -> None:
        agent.token = _mint_token(agent.email, agent.name, role)

    async def summon_cast(self) -> None:
        self.admin_headers = {
            "Authorization": f"Bearer {_mint_token(ADMIN_EMAIL, 'The Archivist', 'admin')}"
        }
        for agent in CAST:
            await self._summon(agent, role="user")
        self._say("ok", f"The Archivist and {len(CAST)} agents are summoned.")


# The phase coordinator: name → the act that fills it. Ordered.
PHASES: list[tuple[str, str]] = [
    ("Draw the circle", "phase_draft"),
    ("Open the gates", "phase_open"),
    ("The forge runs hot", "phase_forge"),
    ("The forge cools", "phase_freeze"),
    ("Weigh the offerings", "phase_score"),
    ("The verdict", "phase_final"),
    ("Seal the record", "phase_archive"),
    ("Export the artefact", "phase_export"),
]


async def run_ritual(narrator: Narrator = _noop, fresh: bool = True) -> RitualReport:
    """
    Summon the cast and walk the event through every phase. Returns a
    :class:`RitualReport` describing what happened — assert on it in tests, or
    narrate it on the way past for a demo.
    """
    # Ensure the schema exists so the tool runs standalone (no-op on a
    # migrated DB). Importing app.models registers every table on Base.
    import app.models  # noqa: F401
    from app.database import Base, engine
    from app.main import create_app
    Base.metadata.create_all(engine)

    _ensure_event(fresh=fresh)
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://rite"
    ) as client:
        rite = Ritual(client, narrator)
        await rite.summon_cast()
        for title, method in PHASES:
            rite._say("phase", f"━━ {title} ━━")
            await getattr(rite, method)()
        await rite.chronicle()

    rite.report.final_state = (
        rite.report.states_visited[-1] if rite.report.states_visited else ""
    )
    return rite.report


# --------------------------------------------------------------------------- #
# Standalone entry — `python -m app.services.ritual_sim`
# --------------------------------------------------------------------------- #
def _plain_narrator(kind: str, message: str) -> None:
    prefix = {
        "phase": "\n",
        "ward": "  ⛨ ",
        "ok": "  ✓ ",
        "warn": "  ! ",
        "chronicle": "  ",
    }.get(kind, "  · ")
    print(f"{prefix}{message}")


if __name__ == "__main__":
    report = asyncio.run(run_ritual(narrator=_plain_narrator))
    print(
        f"\nFinal state: {report.final_state}  ·  "
        f"{report.participants_created} participants, "
        f"{report.teams_created} team(s), "
        f"{report.projects_proposed} projects, "
        f"{report.submissions_created} submissions, "
        f"top score {report.top_score}, "
        f"artefact {report.export_files} files / {report.export_bytes} bytes, "
        f"{report.wards_held} wards held, "
        f"{report.audit_entries} audit entries."
    )
