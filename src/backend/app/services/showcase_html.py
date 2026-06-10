"""Standalone HTML showcase — single file you can host anywhere.

All theme tokens inlined. JSON digest embedded as `<script type="application/json">`
so the page is also machine-readable if someone wants to fork it. Fonts come
from Google Fonts via CDN — if hosted offline they degrade to system serif/mono.
"""

from __future__ import annotations

import html
import json
from typing import Any


def _esc(s: Any) -> str:
    """HTML-escape with None→empty."""
    return html.escape(str(s) if s is not None else "")


def _badge(s: str | None, tone: str = "muted") -> str:
    if not s:
        return ""
    return (
        f'<span class="badge badge--{tone}">'
        f'{_esc(s)}'
        f'</span>'
    )


def _project_card(p: dict[str, Any], rank: int | None = None) -> str:
    score = p.get("score")
    headline = score["value"] if score and score.get("value") is not None else None
    breakdown = score.get("breakdown") if score else None
    notes = score.get("notes") if score else None
    track = p.get("track") or "—"
    proposer = p.get("proposer") or "?"
    proposer_type = p.get("proposer_type") or ""
    repos = p.get("repos") or []
    submissions = p.get("submissions") or []

    rank_chip = ""
    if rank is not None:
        rank_chip = (
            f'<span class="rank rank--{rank}">'
            f'◆ {["first", "second", "third"][rank - 1]}'
            f'</span>'
        )

    score_block = ""
    if headline is not None:
        bars = ""
        if breakdown:
            for k, v in breakdown.items():
                pct = max(0, min(100, float(v)))
                bars += (
                    f'<li>'
                    f'<div class="bar-row">'
                    f'<span class="bar-label">{_esc(k)}</span>'
                    f'<span class="bar-value">{pct:.1f}</span>'
                    f'</div>'
                    f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
                    f'</li>'
                )
        notes_html = (
            f'<p class="notes">{_esc(notes)}</p>' if notes else ""
        )
        score_block = (
            f'<div class="score-block">'
            f'<div class="score-headline">{headline:.1f}</div>'
            f'<ul class="bars">{bars}</ul>'
            f'{notes_html}'
            f'</div>'
        )

    repo_block = ""
    if repos:
        repo_items = ""
        for r in repos[:2]:  # show up to 2 repos per card
            commits_html = ""
            for c in (r.get("commits") or [])[:4]:
                profile = c.get("author_profile_url")
                author_html = (
                    f'<a href="{_esc(profile)}" target="_blank" rel="noopener">{_esc(c.get("author_login") or c.get("author_name"))}</a>'
                    if profile
                    else _esc(c.get("author_login") or c.get("author_name"))
                )
                commits_html += (
                    f'<li class="commit">'
                    f'<span class="sha">{_esc(c.get("sha", "")[:7])}</span> '
                    f'<span class="author">{author_html}</span> '
                    f'<span class="msg">{_esc(c.get("message", ""))}</span>'
                    f'</li>'
                )
            repo_items += (
                f'<div class="repo">'
                f'<a href="{_esc(r.get("url"))}" target="_blank" rel="noopener" class="repo-link">'
                f'{_esc(r.get("owner"))}/{_esc(r.get("repo"))}'
                f'</a>'
                f'<ul class="commits">{commits_html}</ul>'
                f'</div>'
            )
        repo_block = f'<div class="repos"><p class="section-label">repositories</p>{repo_items}</div>'

    sub_block = ""
    if submissions:
        last = submissions[-1]
        if last.get("result"):
            sub_block = (
                f'<p class="result"><span class="label">result</span> {_esc(last["result"])}</p>'
            )

    return f"""<article class="project">
  <header>
    {rank_chip}
    {_badge(track, "warm")}
    {_badge(p.get("status"), "primary" if p.get("status") == "approved" else "muted")}
  </header>
  <h3>{_esc(p.get("title"))}</h3>
  <p class="proposer">by <strong>{_esc(proposer)}</strong> <span class="proposer-type">[{_esc(proposer_type)}]</span></p>
  <p class="desc">{_esc(p.get("description"))}</p>
  {sub_block}
  {score_block}
  {repo_block}
</article>"""


_THEME_CSS = """
:root {
  --bg: #050603;
  --bg-elev: #11140d;
  --rule: #1a2410;
  --rule-bright: #4a6234;
  --fg: #f1f1e8;
  --fg-muted: #8a8f78;
  --fg-dim: #545848;
  --primary: #7c9858;
  --accent: #5cd9c5;
  --warm: #b8842f;
}
* { box-sizing: border-box; }
html, body { background: var(--bg); color: var(--fg); margin: 0; }
body {
  font-family: 'IBM Plex Mono', ui-monospace, Menlo, Consolas, monospace;
  font-size: 15px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.container { max-width: 960px; margin: 0 auto; padding: 48px 24px; }

/* atmospheric grain — pure CSS SVG */
body::before {
  content: '';
  position: fixed; inset: 0;
  pointer-events: none; z-index: 100;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
  opacity: 0.08;
  mix-blend-mode: overlay;
}

/* hero */
.hero {
  border-bottom: 1px solid var(--rule);
  padding-bottom: 28px;
  margin-bottom: 32px;
}
.brand {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--fg-dim);
  margin: 0 0 16px 0;
}
.brand .diamond { color: var(--primary); }
.hero h1 {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: clamp(2.4rem, 6vw, 4.6rem);
  color: var(--fg);
  line-height: 0.98;
  margin: 0 0 12px 0;
  letter-spacing: -0.01em;
}
.hero .dates {
  font-size: 14px;
  color: var(--fg-muted);
}
.hero .state {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--primary);
  border: 1px solid var(--primary);
  padding: 2px 8px;
  margin-left: 8px;
}

/* stats strip */
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 12px;
  margin-bottom: 40px;
}
.stat {
  border: 1px solid var(--rule);
  padding: 10px 12px;
}
.stat-label {
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--fg-dim);
  margin-bottom: 2px;
}
.stat-value {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 28px;
  color: var(--fg);
  line-height: 1;
}

/* section blocks */
section { margin-bottom: 56px; }
.section-title {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: 2rem;
  color: var(--fg);
  border-bottom: 1px solid var(--rule);
  padding-bottom: 8px;
  margin: 0 0 20px 0;
}
.section-label {
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--fg-dim);
  margin: 0 0 6px 0;
}

/* badges + chips */
.badge {
  display: inline-block;
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  padding: 2px 8px;
  border: 1px solid;
  margin-right: 6px;
}
.badge--warm    { color: var(--warm);    border-color: var(--warm); }
.badge--primary { color: var(--primary); border-color: var(--primary); }
.badge--muted   { color: var(--fg-muted); border-color: var(--rule); }
.rank {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  padding: 2px 8px;
  margin-right: 6px;
  border: 1px solid;
}
.rank--1 { color: var(--accent);  border-color: var(--accent);  }
.rank--2 { color: var(--primary); border-color: var(--primary); }
.rank--3 { color: var(--warm);    border-color: var(--warm);    }

/* project card */
.projects-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}
@media (min-width: 700px) {
  .projects-grid { grid-template-columns: 1fr 1fr; }
}
.project {
  border: 1px solid var(--rule);
  background: color-mix(in oklab, var(--bg-elev) 70%, transparent);
  padding: 20px;
  position: relative;
}
.project header { margin-bottom: 10px; }
.project h3 {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: 1.6rem;
  color: var(--fg);
  margin: 0 0 6px 0;
}
.project .proposer {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-dim);
  margin: 0 0 12px 0;
}
.project .proposer strong { color: var(--fg-muted); font-weight: 500; }
.project .proposer-type { color: var(--fg-dim); }
.project .desc {
  font-size: 14px;
  color: var(--fg-muted);
  line-height: 1.6;
  margin: 0 0 12px 0;
}
.project .result {
  font-size: 13px;
  color: var(--fg);
  word-break: break-all;
  margin: 12px 0;
}
.project .result .label {
  color: var(--fg-dim);
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.16em;
  margin-right: 6px;
}

/* score block */
.score-block {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
}
.score-headline {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 2.6rem;
  color: var(--accent);
  line-height: 1;
  margin-bottom: 12px;
}
.bars { list-style: none; padding: 0; margin: 0; }
.bars li { margin-bottom: 8px; }
.bar-row {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-dim);
  margin-bottom: 3px;
}
.bar-row .bar-value { color: var(--accent); font-variant-numeric: tabular-nums; }
.bar-track {
  height: 3px;
  background: var(--rule);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: var(--accent);
}
.notes {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 14px;
  color: var(--fg-muted);
  border-left: 2px solid var(--accent);
  padding-left: 10px;
  margin: 12px 0 0;
}

/* repos */
.repos {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
}
.repo { margin-bottom: 14px; }
.repo:last-child { margin-bottom: 0; }
.repo-link {
  font-size: 13px;
  color: var(--fg);
  display: block;
  margin-bottom: 6px;
}
.repo-link:hover { color: var(--primary); }
.commits {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 12px;
}
.commit {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 8px;
  padding: 2px 0;
  align-items: baseline;
  color: var(--fg-muted);
}
.commit .sha { color: var(--fg-dim); font-variant-numeric: tabular-nums; }
.commit .author { color: var(--fg-muted); }
.commit .author a { color: var(--accent); }
.commit .msg { color: var(--fg); font-style: italic; font-family: 'EB Garamond', Georgia, serif; font-size: 14px; line-height: 1.4; }

/* participants */
.participants-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
  list-style: none;
  padding: 0;
}
.participant {
  border: 1px solid var(--rule);
  padding: 10px 12px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: start;
}
.participant.no-portrait {
  display: block;
}
.participant .portrait {
  width: 40px; height: 40px;
  border: 1px solid var(--rule);
  background: var(--bg-elev);
  image-rendering: pixelated;
  display: block;
  object-fit: cover;
}
.participant .name { color: var(--fg); font-size: 14px; }
.participant .kind {
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-dim);
  margin-top: 2px;
}
.participant .kind--agent { color: var(--accent); }
.participant .kind--team  { color: var(--primary); }
.participant .affiliation {
  font-size: 11px;
  color: var(--fg-dim);
  margin-top: 4px;
}

/* tracks + phases */
.kv {
  border: 1px solid var(--rule);
  padding: 14px 16px;
  margin-bottom: 10px;
}
.kv h4 {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: 1.3rem;
  color: var(--fg);
  margin: 0 0 4px 0;
}
.kv .descr { font-size: 13px; color: var(--fg-muted); }
.kv .when { font-size: 11px; color: var(--fg-dim); letter-spacing: 0.14em; text-transform: uppercase; margin-top: 6px; }

/* footer */
.outro {
  margin-top: 56px;
  padding-top: 24px;
  border-top: 1px solid var(--rule);
  text-align: center;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--fg-dim);
}
.outro p { margin: 4px 0; }
"""


def render_showcase_html(data: dict[str, Any]) -> str:
    """Render a fully self-contained HTML showcase from a digest dict."""
    event = data.get("event", {})
    stats = data.get("stats", {})
    winners = data.get("winners", []) or []
    projects = data.get("projects", []) or []
    participants = data.get("participants", []) or []
    tracks = data.get("tracks", []) or []
    phases = data.get("phases", []) or []

    # Hero
    dates_str = ""
    if event.get("start_at") and event.get("end_at"):
        try:
            from datetime import datetime as _dt
            start = _dt.fromisoformat(event["start_at"].replace("Z", "+00:00"))
            end = _dt.fromisoformat(event["end_at"].replace("Z", "+00:00"))
            dates_str = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
        except Exception:
            dates_str = f"{event.get('start_at')} → {event.get('end_at')}"

    # Stats strip
    stat_items = [
        ("participants", stats.get("participants", 0)),
        ("humans", stats.get("humans", 0)),
        ("agents", stats.get("agents", 0)),
        ("teams", stats.get("teams", 0)),
        ("projects", stats.get("projects", 0)),
        ("submissions", stats.get("final_submissions", 0)),
        ("repos linked", stats.get("linked_repos", 0)),
        ("portraits", stats.get("portraits", 0)),
    ]
    stats_html = "".join(
        f'<div class="stat"><div class="stat-label">{_esc(label)}</div>'
        f'<div class="stat-value">{_esc(value)}</div></div>'
        for label, value in stat_items
    )

    # Winners
    winners_html = ""
    if winners:
        cards = "".join(
            _project_card(p, rank=i + 1) for i, p in enumerate(winners)
        )
        winners_html = f"""<section>
  <h2 class="section-title">The verdict</h2>
  <div class="projects-grid">{cards}</div>
</section>"""

    # All projects (excluding winners to avoid repetition)
    winner_ids = {p["id"] for p in winners}
    other_projects = [p for p in projects if p["id"] not in winner_ids]
    projects_html = ""
    if other_projects:
        cards = "".join(_project_card(p) for p in other_projects)
        projects_html = f"""<section>
  <h2 class="section-title">{'Every other project' if winners else 'Every project'}</h2>
  <div class="projects-grid">{cards}</div>
</section>"""

    # Participants
    participants_html = ""
    if participants:
        items_list = []
        for p in participants:
            portrait_uri = p.get("portrait")
            portrait_html = ""
            if portrait_uri:
                portrait_html = (
                    f'<img src="{_esc(portrait_uri)}" alt="" class="portrait" '
                    f'loading="lazy">'
                )
            details_html = (
                f'<div>'
                f'<div class="name">{_esc(p["display_name"])}</div>'
                f'<div class="kind kind--{_esc(p["type"])}">[{_esc(p["type"])}]</div>'
                + (f'<div class="affiliation">{_esc(p["affiliation"])}</div>'
                   if p.get("affiliation") else "")
                + '</div>'
            )
            wrapper_class = "participant" if portrait_uri else "participant no-portrait"
            items_list.append(
                f'<li class="{wrapper_class}">{portrait_html}{details_html}</li>'
            )
        items = "".join(items_list)
        participants_html = f"""<section>
  <h2 class="section-title">The circle</h2>
  <ul class="participants-grid">{items}</ul>
</section>"""

    # Tracks
    tracks_html = ""
    if tracks:
        items = "".join(
            f'<div class="kv"><h4>{_esc(t["name"])}</h4>'
            f'<div class="descr">{_esc(t.get("description") or "")}</div></div>'
            for t in tracks
        )
        tracks_html = f"""<section>
  <h2 class="section-title">Tracks</h2>
  {items}
</section>"""

    # Phases
    phases_html = ""
    if phases:
        items = ""
        for p in phases:
            when = ""
            if p.get("starts_at") and p.get("ends_at"):
                try:
                    from datetime import datetime as _dt
                    s = _dt.fromisoformat(p["starts_at"].replace("Z", "+00:00"))
                    e = _dt.fromisoformat(p["ends_at"].replace("Z", "+00:00"))
                    when = f'{s.strftime("%b %d · %H:%M")} – {e.strftime("%H:%M")}'
                except Exception:
                    when = f'{p["starts_at"]} → {p["ends_at"]}'
            items += (
                f'<div class="kv"><h4>{_esc(p["name"])}</h4>'
                f'<div class="descr">{_esc(p.get("description") or "")}</div>'
                + (f'<div class="when">{_esc(when)}</div>' if when else "")
                + '</div>'
            )
        phases_html = f"""<section>
  <h2 class="section-title">Phases</h2>
  {items}
</section>"""

    # Embed the full JSON digest so the page is self-describing.
    embedded_json = json.dumps(data, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(event.get("title", "HackRitual"))} · showcase</title>
  <meta name="description" content="HackRitual showcase — {_esc(event.get("title", "an event"))}, exported {_esc(data.get("exported_at"))}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
  <style>{_THEME_CSS}</style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <p class="brand"><span class="diamond">◆</span>&nbsp;&nbsp;HackRitual&nbsp;&nbsp;·&nbsp;&nbsp;showcase</p>
      <h1>{_esc(event.get("title", "Untitled ritual"))}</h1>
      <p class="dates">
        {_esc(dates_str)}
        {f'<span class="state">{_esc(event.get("state"))}</span>' if event.get("state") else ""}
      </p>
    </header>

    <div class="stats">{stats_html}</div>

    {winners_html}
    {projects_html}
    {participants_html}
    {tracks_html}
    {phases_html}

    <footer class="outro">
      <p>exported {_esc(data.get("exported_at"))}</p>
      <p>HackRitual · single container · one ritual</p>
    </footer>
  </div>

  <script type="application/json" id="hackritual-showcase">
{embedded_json}
  </script>
</body>
</html>"""
