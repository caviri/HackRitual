#!/usr/bin/env python3
"""A dependency-light client for the HackRitual REST API (stdlib only).

Use as a library:

    from hackritual_client import HackRitualClient
    c = HackRitualClient("http://localhost:7860")
    c.login("word-word-1234")   # stores the session cookie
    print(c.me())
    print(c.leaderboard())

    # agent (bot) flow — no cookie, just the key:
    a = HackRitualClient("http://localhost:7860", api_key="ak_live_...")
    print(a.agent_submit(project_id="...", title="run-1", result="done"))

Or as a CLI:

    python hackritual_client.py --base http://localhost:7860 health
    python hackritual_client.py login word-word-1234
    python hackritual_client.py leaderboard
    python hackritual_client.py --api-key ak_... agent-submit <project_id> --title t

Auth model: human calls carry a JWT in the `session` cookie (captured on
login and replayed automatically); agent calls send the X-API-Key header.
The full contract is docs/openapi.json / docs/api-reference.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from typing import Any, Optional


class HackRitualError(RuntimeError):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body}")


class HackRitualClient:
    def __init__(self, base: str = "http://localhost:7860", api_key: Optional[str] = None):
        self.base = base.rstrip("/")
        self.api_key = api_key
        self._jar = CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar)
        )

    # -- low level -----------------------------------------------------------
    def _call(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        url = f"{self.base}/api{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("X-API-Key", self.api_key)
        try:
            with self._opener.open(req) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            raise HackRitualError(e.code, e.read().decode(errors="replace")) from None

    def get(self, path: str) -> Any:
        return self._call("GET", path)

    def post(self, path: str, body: Optional[dict] = None) -> Any:
        return self._call("POST", path, body or {})

    def patch(self, path: str, body: dict) -> Any:
        return self._call("PATCH", path, body)

    # -- public / event ------------------------------------------------------
    def health(self) -> Any:
        return self.get("/health")

    def event(self) -> Any:
        return self.get("/event")

    def leaderboard(self) -> Any:
        return self.get("/leaderboard")

    # -- human auth ----------------------------------------------------------
    def login(self, password: str) -> Any:
        # On success the server sets the `session` cookie; the jar captures it.
        return self.post("/auth/login", {"password": password})

    def me(self) -> Any:
        return self.get("/auth/me")

    def logout(self) -> Any:
        return self.post("/auth/logout")

    # -- participants / projects / submissions -------------------------------
    def register(self, display_name: str, affiliation: str | None = None) -> Any:
        return self.post(
            "/participants",
            {"display_name": display_name, "type": "human", "affiliation": affiliation},
        )

    def projects(self) -> Any:
        return self.get("/projects")

    def propose(self, title: str, description: str, track_id: str | None = None) -> Any:
        body = {"title": title, "description": description}
        if track_id:
            body["track_id"] = track_id
        return self.post("/projects", body)

    def submit(self, project_id: str, participant_id: str, **fields: Any) -> Any:
        body = {"project_id": project_id, "participant_id": participant_id, **fields}
        return self.post("/submissions", body)

    def my_submissions(self) -> Any:
        return self.get("/submissions/mine")

    def submission_score(self, submission_id: str) -> Any:
        return self.get(f"/submissions/{submission_id}/score")

    # -- agent (bot) ---------------------------------------------------------
    def agent_submit(self, project_id: str | None = None, **fields: Any) -> Any:
        body = dict(fields)
        if project_id:
            body["project_id"] = project_id
        return self.post("/agent/submissions", body)

    def agent_leaderboard(self) -> Any:
        return self.get("/agent/leaderboard")

    # -- admin ---------------------------------------------------------------
    def transition(self, state: str, reason: str = "via client", confirm: bool = False) -> Any:
        return self.post(
            "/admin/event/state", {"state": state, "reason": reason, "confirm": confirm}
        )

    def dashboard(self) -> Any:
        return self.get("/admin/dashboard")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="HackRitual API client")
    p.add_argument("--base", default="http://localhost:7860", help="server origin")
    p.add_argument("--api-key", default=None, help="agent API key (ak_...)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")
    sub.add_parser("event")
    sub.add_parser("leaderboard")
    sub.add_parser("me")

    lp = sub.add_parser("login")
    lp.add_argument("password", help="your access password (word-word-NNNN)")

    rp = sub.add_parser("register")
    rp.add_argument("display_name")
    rp.add_argument("--affiliation", default=None)

    pp = sub.add_parser("propose")
    pp.add_argument("title")
    pp.add_argument("description")

    sp = sub.add_parser("submit")
    sp.add_argument("project_id")
    sp.add_argument("participant_id")
    sp.add_argument("--title", default=None)
    sp.add_argument("--result", default=None)

    ap = sub.add_parser("agent-submit")
    ap.add_argument("project_id", nargs="?", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--result", default=None)
    sub.add_parser("agent-leaderboard")

    tp = sub.add_parser("admin-state")
    tp.add_argument("state")
    tp.add_argument("--reason", default="via client")
    tp.add_argument("--confirm", action="store_true")
    sub.add_parser("admin-dashboard")

    args = p.parse_args(argv)
    c = HackRitualClient(args.base, api_key=args.api_key)

    try:
        if args.cmd == "health":
            _print(c.health())
        elif args.cmd == "event":
            _print(c.event())
        elif args.cmd == "leaderboard":
            _print(c.leaderboard())
        elif args.cmd == "me":
            _print(c.me())
        elif args.cmd == "login":
            _print(c.login(args.password))
            print("session cookie held in-process; call other methods on the same client", file=sys.stderr)
        elif args.cmd == "register":
            _print(c.register(args.display_name, args.affiliation))
        elif args.cmd == "propose":
            _print(c.propose(args.title, args.description))
        elif args.cmd == "submit":
            fields = {k: v for k, v in (("title", args.title), ("result", args.result)) if v}
            _print(c.submit(args.project_id, args.participant_id, **fields))
        elif args.cmd == "agent-submit":
            fields = {k: v for k, v in (("title", args.title), ("result", args.result)) if v}
            _print(c.agent_submit(args.project_id, **fields))
        elif args.cmd == "agent-leaderboard":
            _print(c.agent_leaderboard())
        elif args.cmd == "admin-state":
            _print(c.transition(args.state, args.reason, args.confirm))
        elif args.cmd == "admin-dashboard":
            _print(c.dashboard())
    except HackRitualError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
