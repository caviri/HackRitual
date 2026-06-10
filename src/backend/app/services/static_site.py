"""
Static-site generation for the export archive (Step 17).

A minimal, self-contained set of HTML pages built from the live data — no
framework, no CDN, no JavaScript required. Suitable for GitHub Pages. Plain
string templates (the project's house style for generated HTML), with values
HTML-escaped.
"""

from __future__ import annotations

from html import escape

from sqlalchemy.orm import Session

from app.config import settings
from app.models.event import Event
from app.services.event import load_config
from app.services.leaderboard import build_leaderboard

_CSS = """\
:root { --bg:#0a0c07; --fg:#e8e6d8; --muted:#8a8f78; --accent:#7c9858; --rule:#1a2410; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font-family: -apple-system, Segoe UI, Roboto, sans-serif; line-height:1.6; }
main { max-width: 860px; margin: 0 auto; padding: 48px 20px 80px; }
h1 { font-size: 2.4rem; margin: 0 0 4px; }
h1 em { font-style: italic; color: var(--accent); }
.sub { color: var(--muted); margin: 0 0 32px; }
a { color: var(--accent); }
nav { margin: 0 0 32px; font-size: .9rem; }
nav a { margin-right: 16px; }
table { width:100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align:left; padding:10px 12px; border-bottom:1px solid var(--rule); }
th { color: var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.1em; }
.rank { color: var(--accent); font-weight: 600; }
.cards { display:flex; gap:16px; flex-wrap:wrap; margin:24px 0; }
.card { border:1px solid var(--rule); padding:16px 20px; min-width:140px; }
.card .n { font-size:1.8rem; color: var(--accent); }
.card .l { color: var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }
footer { margin-top:48px; color:var(--muted); font-size:.8rem; border-top:1px solid var(--rule); padding-top:16px; }
"""


def _page(title: str, body: str) -> bytes:
    html = (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title><link rel=stylesheet href=style.css></head>"
        f"<body><main>{body}"
        "<footer>Powered by <strong>HackRitual</strong> — one container, one ritual.</footer>"
        "</main></body></html>"
    )
    return html.encode("utf-8")


def _nav() -> str:
    return (
        "<nav><a href=index.html>overview</a><a href=leaderboard.html>leaderboard</a>"
        "<a href=participants.html>participants</a><a href=submissions.html>submissions</a></nav>"
    )


def generate(db: Session) -> dict[str, bytes]:
    """Return {filename: bytes} for the static site."""
    from app.models.participant import Participant
    from app.models.submission import Submission

    event = db.get(Event, settings.event_id) or db.query(Event).first()
    title = event.title if event else settings.event_title
    state = event.state if event else "UNKNOWN"
    mode = load_config(event).get("leaderboard_mode", "best") if event else "best"

    rows = build_leaderboard(db, settings.event_id, mode=mode, limit=1000)
    participants = (
        db.query(Participant)
        .filter(Participant.event_id == settings.event_id)
        .order_by(Participant.display_name)
        .all()
    )
    submissions = (
        db.query(Submission)
        .filter(
            Submission.event_id == settings.event_id,
            Submission.status != "withdrawn",
        )
        .all()
    )

    # ── index ──
    top_rows = "".join(
        f"<tr><td class=rank>{i}</td><td>{escape(r.participant.display_name)}</td>"
        f"<td>{r.score:.1f}</td></tr>"
        for i, r in enumerate(rows[:10], 1)
    )
    index_body = (
        f"<h1>{escape(title)}</h1>"
        f"<p class=sub>state: {escape(state)} · leaderboard mode: {escape(mode)}</p>"
        f"{_nav()}"
        "<div class=cards>"
        f"<div class=card><div class=n>{len(participants)}</div><div class=l>participants</div></div>"
        f"<div class=card><div class=n>{len(submissions)}</div><div class=l>submissions</div></div>"
        f"<div class=card><div class=n>{len(rows)}</div><div class=l>ranked</div></div>"
        "</div>"
        "<h2>Top 10</h2>"
        f"<table><thead><tr><th>rank</th><th>participant</th><th>score</th></tr></thead>"
        f"<tbody>{top_rows or '<tr><td colspan=3>no scored entries</td></tr>'}</tbody></table>"
        "<p><a href=leaderboard.html>Full leaderboard →</a></p>"
    )

    # ── leaderboard ──
    lb_rows = "".join(
        f"<tr><td class=rank>{i}</td><td>{escape(r.participant.display_name)}</td>"
        f"<td>{escape(r.participant.type)}</td><td>{r.submission_count}</td>"
        f"<td>{r.score:.1f}</td></tr>"
        for i, r in enumerate(rows, 1)
    )
    lb_body = (
        f"<h1>Leaderboard</h1><p class=sub>{escape(title)} — {len(rows)} ranked</p>{_nav()}"
        "<table><thead><tr><th>rank</th><th>participant</th><th>type</th>"
        "<th>subs</th><th>score</th></tr></thead>"
        f"<tbody>{lb_rows or '<tr><td colspan=5>no scored entries</td></tr>'}</tbody></table>"
    )

    # ── participants ──
    p_rows = "".join(
        f"<tr><td>{escape(p.display_name)}</td><td>{escape(p.type)}</td>"
        f"<td>{escape(p.affiliation or '')}</td><td>{escape(p.status)}</td></tr>"
        for p in participants
    )
    p_body = (
        f"<h1>Participants</h1><p class=sub>{len(participants)} gathered</p>{_nav()}"
        "<table><thead><tr><th>name</th><th>type</th><th>affiliation</th>"
        f"<th>status</th></tr></thead><tbody>{p_rows}</tbody></table>"
    )

    # ── submissions ──
    s_rows = "".join(
        f"<tr><td>{escape(s.title or '(untitled)')}</td><td>v{s.version}</td>"
        f"<td>{escape(s.status)}</td></tr>"
        for s in submissions
    )
    s_body = (
        f"<h1>Submissions</h1><p class=sub>{len(submissions)} offered</p>{_nav()}"
        "<table><thead><tr><th>title</th><th>version</th><th>status</th>"
        f"</tr></thead><tbody>{s_rows}</tbody></table>"
    )

    return {
        "index.html": _page(title, index_body),
        "leaderboard.html": _page(f"Leaderboard — {title}", lb_body),
        "participants.html": _page(f"Participants — {title}", p_body),
        "submissions.html": _page(f"Submissions — {title}", s_body),
        "style.css": _CSS.encode("utf-8"),
    }
