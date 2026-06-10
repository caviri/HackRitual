"""HackRitual-themed docs page.

Overrides FastAPI's default `/docs` (Swagger UI) with HTML that uses the same
visual language as the front-end: EB Garamond display, IBM Plex Mono body,
moss/biolume/mycelium palette on a forest-floor background.

We disable FastAPI's automatic `/docs` and `/redoc` in `main.py` and route to
the functions below instead.
"""

from __future__ import annotations

from fastapi.responses import HTMLResponse

API_DESCRIPTION = """
*The API behind the ritual.* One container · one event · one SQLite file.

### Authentication — two kinds of actor

- **Humans** sign in with an admin-distributed access password, receive a
  `session` HTTP-only cookie carrying a JWT.
- **Agents** present `X-API-Key: ak_…` (or `Authorization: Bearer ak_…`)
  on every request. Each agent is a participant in its own right —
  it can propose projects and create submissions just like a human.

The same endpoints accept both. The handler distinguishes via
`get_current_actor` and applies the correct attribution.

### The state machine — DRAFT → OPEN → FROZEN → FINAL → ARCHIVED

Most write operations are state-gated. The event advances forward only
(with one sanctioned reversal, FROZEN → OPEN), via
`POST /api/admin/event/state` (admin). Each transition is inscribed in the
audit log. A `409 Conflict` means the event is in the wrong state for the call.

### Rate limits

Every `/api/*` response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
and `X-RateLimit-Reset`. A `429` carries `Retry-After` (seconds). Keyed by
truncated IP (public), session (users), or API-key hash (agents) — never a
stored full IP.

### Scoring & export

Submissions are scored server-side (the default Python scorer, or an uploaded
WASM module) and ranked on `/api/leaderboard`. The structured export
(`/api/admin/export`) is a curated, redacted JSON archive — emails hashed in
public mode — downloadable as a zip or pushable to GitHub Pages.
"""

OPENAPI_TAGS = [
    {"name": "system", "description": "Health, status, persistent-storage probe."},
    {"name": "auth", "description": "*Speak the password you were handed, step into the circle.*"},
    {"name": "event", "description": "The singleton event. The state machine of the ritual."},
    {"name": "users", "description": "Humans inside the ritual. Email, role, status."},
    {"name": "applications", "description": "Petitions to join — filed publicly, decided by the keeper."},
    {"name": "announcements", "description": "Dispatches from the keeper, shown under the hero."},
    {"name": "me", "description": "What you can do to your own identity — portrait, settings."},
    {"name": "participants", "description": "Polymorphic. A participant is a human, an agent, or a team."},
    {"name": "agents", "description": "Autonomous actors. Hold an API key. The `/api/agent/*` API."},
    {"name": "tracks", "description": "Thematic groupings that hold projects."},
    {"name": "phases", "description": "Sub-phases inside the event lifecycle."},
    {"name": "pages", "description": "Long-form authored content (rites, rules, faq)."},
    {"name": "projects", "description": "Proposals — what is being forged. Project ≠ submission."},
    {"name": "submissions", "description": "Versioned snapshots of work, with file attachments."},
    {"name": "scores", "description": "Scores and the public leaderboard."},
    {"name": "scoring", "description": "Admin: the active scorer and uploaded WASM modules."},
    {"name": "uploads", "description": "Image uploads dithered or halftoned at intake."},
    {"name": "repositories", "description": "Linked git repos and their commit feeds."},
    {"name": "export", "description": "The artefact bundle — download or push to GitHub."},
    {"name": "queue", "description": "Admin: the task queue (scoring, export, push)."},
    {"name": "metrics", "description": "Admin: aggregate daily statistics."},
    {"name": "abuse", "description": "Admin: rate-limit stats and temporary IP blocks."},
    {"name": "privacy", "description": "What is collected, and what never is."},
    {"name": "log", "description": "The audit log — every consequential act."},
    {"name": "admin", "description": "Operations only the keeper can perform."},
    {"name": "scaffold", "description": "Dev companion — tickets and docs browsing."},
]


# Inlined so we have one file to deploy, no extra mount needed.
_SWAGGER_THEME_CSS = """
/* ============================================================ *
 * HackRitual theme overrides for Swagger UI                    *
 * ============================================================ */
:root, [data-theme="hacker-solarpunk"] {
  --bg:         #050603;
  --bg-elev:    #11140d;
  --rule:       #1a2410;
  --rule-bright:#4a6234;
  --fg:         #f1f1e8;
  --fg-muted:   #8a8f78;
  --fg-dim:     #545848;
  --moss:       #7c9858;
  --moss-dark:  #4a6234;
  --bio:        #5cd9c5;
  --warm:       #b8842f;
  --danger:     #c7493a;
}
[data-theme="paper-grimoire"] {
  --bg: #f4ecd7; --bg-elev: #ece2c5;
  --rule: #cabf9c; --rule-bright: #a89978;
  --fg: #1c1814; --fg-muted: #5a4f3c; --fg-dim: #8a7e64;
  --moss: #6a2a1a; --moss-dark: #4a1a0e;
  --bio: #2a4a30; --warm: #8e6a1d; --danger: #8e2218;
}

html, body { background: var(--bg); margin: 0; }
body {
  color: var(--fg);
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
}

/* atmospheric: grain overlay */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 100;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
  opacity: 0.08;
  mix-blend-mode: overlay;
}

/* ───── HackRitual header (the part we control above swagger-ui) ───── */
.hr-header {
  border-bottom: 1px solid var(--rule);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.hr-brand {
  display: inline-flex;
  align-items: baseline;
  gap: 10px;
}
.hr-brand .hr-diamond { color: var(--moss); font-size: 1.2rem; }
.hr-brand .hr-name {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: 1.4rem;
  font-style: italic;
  letter-spacing: -0.01em;
}
.hr-brand .hr-sub {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--fg-dim);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
}
.hr-back {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--fg-muted);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.hr-back:hover { color: var(--moss); }
.hr-theme-toggle {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--fg-dim);
  background: transparent;
  border: 1px solid var(--rule);
  padding: 4px 10px;
  cursor: pointer;
}
.hr-theme-toggle:hover { color: var(--fg); border-color: var(--rule-bright); }

/* ───── Swagger UI top bar — hide it, we have our own ───── */
.swagger-ui .topbar { display: none; }

/* ───── Info block ───── */
.swagger-ui { color: var(--fg); }
.swagger-ui, .swagger-ui .info, .swagger-ui .info .markdown,
.swagger-ui .info .markdown p, .swagger-ui .info li,
.swagger-ui .opblock-tag-section, .swagger-ui .opblock,
.swagger-ui .opblock-description-wrapper {
  color: var(--fg);
}
.swagger-ui .info hgroup.main .title,
.swagger-ui .info .title {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  color: var(--fg);
  font-weight: 400;
  font-size: 2.6rem;
  letter-spacing: -0.01em;
}
.swagger-ui .info .title small {
  background: var(--rule);
  color: var(--moss);
  border-radius: 0;
}
.swagger-ui .info .description, .swagger-ui .markdown p {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.86rem;
  color: var(--fg-muted);
  line-height: 1.65;
}
.swagger-ui .info .description h3, .swagger-ui .markdown h3 {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  color: var(--fg);
  border-bottom: 1px solid var(--rule);
  padding-bottom: 6px;
  margin-top: 28px;
}
.swagger-ui .markdown code, .swagger-ui .info .description code {
  color: var(--warm);
  background: rgba(184, 132, 47, 0.08);
  border: 1px solid var(--rule);
  padding: 1px 5px;
  font-size: 0.78rem;
}
.swagger-ui .info a, .swagger-ui a { color: var(--bio); }

/* ───── Operation tag headers ───── */
.swagger-ui .opblock-tag {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  color: var(--fg);
  border-bottom: 1px solid var(--rule);
  padding-bottom: 8px;
  margin-top: 32px;
  font-size: 1.7rem;
  font-weight: 400;
}
.swagger-ui .opblock-tag small {
  color: var(--fg-muted);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  font-style: normal;
}

/* ───── Operation blocks ───── */
.swagger-ui .opblock {
  background: color-mix(in oklab, var(--bg-elev) 70%, transparent);
  border: 1px solid var(--rule);
  border-radius: 2px;
  box-shadow: none;
  margin: 0 0 10px;
}
.swagger-ui .opblock .opblock-summary {
  border: none;
  padding: 6px 10px;
}
.swagger-ui .opblock .opblock-summary-method {
  font-family: 'IBM Plex Mono', monospace;
  border-radius: 2px;
  background: var(--moss);
  color: var(--bg);
  font-size: 0.72rem;
  padding: 6px 10px;
  min-width: 78px;
  text-align: center;
  text-shadow: none;
}
.swagger-ui .opblock.opblock-get { border-color: var(--moss); }
.swagger-ui .opblock.opblock-get .opblock-summary-method { background: var(--moss); }
.swagger-ui .opblock.opblock-post .opblock-summary-method { background: var(--bio); color: #02110d; }
.swagger-ui .opblock.opblock-post { border-color: var(--bio); }
.swagger-ui .opblock.opblock-put .opblock-summary-method,
.swagger-ui .opblock.opblock-patch .opblock-summary-method { background: var(--warm); }
.swagger-ui .opblock.opblock-put, .swagger-ui .opblock.opblock-patch { border-color: var(--warm); }
.swagger-ui .opblock.opblock-delete .opblock-summary-method { background: var(--danger); }
.swagger-ui .opblock.opblock-delete { border-color: var(--danger); }
.swagger-ui .opblock.is-open { background: var(--bg-elev); }

.swagger-ui .opblock .opblock-summary-path {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--fg);
  font-weight: 500;
  font-size: 0.92rem;
}
.swagger-ui .opblock .opblock-summary-path__deprecated { color: var(--fg-dim); }
.swagger-ui .opblock .opblock-summary-description {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  color: var(--fg-muted);
  font-size: 0.95rem;
}

/* ───── Section headers inside an operation ───── */
.swagger-ui .opblock-section-header {
  background: color-mix(in oklab, var(--bg) 60%, transparent);
  box-shadow: none;
  border-bottom: 1px solid var(--rule);
}
.swagger-ui .opblock-section-header h4 {
  font-family: 'IBM Plex Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.72rem;
  color: var(--fg-muted);
}

/* ───── Tables (parameters, responses) ───── */
.swagger-ui table { background: transparent; }
.swagger-ui table thead tr th {
  color: var(--fg-muted);
  border-bottom: 1px solid var(--rule);
  font-family: 'IBM Plex Mono', monospace;
  text-transform: uppercase;
  font-size: 0.66rem;
  letter-spacing: 0.16em;
}
.swagger-ui table tbody tr td { border-bottom: 1px solid var(--rule); }
.swagger-ui .parameter__name { color: var(--fg); font-weight: 500; }
.swagger-ui .parameter__name.required::after { color: var(--danger); }
.swagger-ui .parameter__type { color: var(--bio); font-family: 'IBM Plex Mono', monospace; }
.swagger-ui .parameter__deprecated, .swagger-ui .parameter__in { color: var(--fg-dim); }
.swagger-ui .response-col_status { color: var(--moss); font-family: 'IBM Plex Mono', monospace; }
.swagger-ui .response-col_description__inner div.markdown,
.swagger-ui .response-col_description__inner div.renderedMarkdown,
.swagger-ui .response-col_description__inner { color: var(--fg-muted); }

/* ───── Buttons ───── */
.swagger-ui .btn {
  background: transparent;
  border: 1px solid var(--moss);
  color: var(--moss);
  font-family: 'IBM Plex Mono', monospace;
  text-transform: lowercase;
  letter-spacing: 0.05em;
  border-radius: 2px;
  font-size: 0.78rem;
  box-shadow: none;
}
.swagger-ui .btn:hover { background: var(--moss); color: var(--bg); box-shadow: 0 0 0 4px rgba(124, 152, 88, 0.2); }
.swagger-ui .btn.execute, .swagger-ui .btn.authorize {
  background: var(--moss);
  color: var(--bg);
  border-color: var(--moss);
}
.swagger-ui .btn.execute:hover, .swagger-ui .btn.authorize:hover {
  background: transparent;
  color: var(--moss);
}
.swagger-ui .btn.cancel { border-color: var(--danger); color: var(--danger); }
.swagger-ui .btn-clear { border-color: var(--warm); color: var(--warm); }
.swagger-ui .copy-to-clipboard, .swagger-ui .copy-to-clipboard button {
  background: transparent;
  border: 1px solid var(--rule);
}
.swagger-ui .copy-to-clipboard button { color: var(--fg-muted); }

/* ───── Inputs ───── */
.swagger-ui input[type=text], .swagger-ui input[type=password],
.swagger-ui input[type=email], .swagger-ui input[type=file],
.swagger-ui input[type=search], .swagger-ui input[type=number],
.swagger-ui textarea, .swagger-ui select {
  background: var(--bg-elev);
  border: 1px solid var(--rule);
  color: var(--fg);
  font-family: 'IBM Plex Mono', monospace;
  border-radius: 2px;
  box-shadow: none;
}
.swagger-ui input[type=text]:focus, .swagger-ui input:focus,
.swagger-ui textarea:focus, .swagger-ui select:focus {
  border-color: var(--moss);
  box-shadow: 0 0 0 3px rgba(124, 152, 88, 0.25);
  outline: none;
}

/* ───── Code blocks ───── */
.swagger-ui pre, .swagger-ui .highlight-code,
.swagger-ui .microlight, .swagger-ui .body-param__example,
.swagger-ui .responses-inner pre, .swagger-ui .opblock-body pre {
  background: var(--bg) !important;
  border: 1px solid var(--rule);
  color: var(--fg);
  font-family: 'IBM Plex Mono', monospace;
}
.swagger-ui .microlight .hljs-string { color: var(--bio); }
.swagger-ui .microlight .hljs-number { color: var(--warm); }
.swagger-ui .microlight .hljs-attr { color: var(--moss); }

/* ───── Models section ───── */
.swagger-ui section.models {
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 2px;
}
.swagger-ui section.models h4 {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  color: var(--fg);
}
.swagger-ui .model-toggle { color: var(--moss); }
.swagger-ui .model-box { background: transparent; }
.swagger-ui .model, .swagger-ui .model .property {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--fg-muted);
}
.swagger-ui .model-title { color: var(--fg); }
.swagger-ui .prop-type { color: var(--bio); }
.swagger-ui .prop-format { color: var(--fg-dim); }

/* ───── Filter input ───── */
.swagger-ui .filter-container { background: transparent; padding: 8px 0; }
.swagger-ui .filter .operation-filter-input {
  background: var(--bg-elev);
  border: 1px solid var(--rule);
}

/* ───── Auth dialog ───── */
.swagger-ui .auth-container {
  background: var(--bg-elev);
  border: 1px solid var(--rule);
}
.swagger-ui .dialog-ux .modal-ux {
  background: var(--bg-elev);
  border: 1px solid var(--rule-bright);
}

/* ───── Misc ───── */
.swagger-ui .scheme-container {
  background: transparent;
  border-top: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
  box-shadow: none;
  padding: 12px 0;
}
.swagger-ui .servers-title { color: var(--fg-muted); }
.swagger-ui hr { border-color: var(--rule); }
.swagger-ui .opblock-deprecated { background: rgba(135, 94, 30, 0.1); }

/* ───── HackRitual footer ───── */
.hr-footer {
  border-top: 1px solid var(--rule);
  padding: 20px 24px;
  text-align: center;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  color: var(--fg-dim);
}
.hr-footer a {
  color: var(--moss);
  text-decoration: none;
  margin: 0 6px;
}
.hr-footer a:hover { text-decoration: underline; }
"""


def render_redoc_html(openapi_url: str = "/api/openapi.json") -> HTMLResponse:
    """A minimal ReDoc page (the spec's alternate reference view)."""
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>HackRitual · API reference</title>
  <link rel="icon" href="/icon.svg" type="image/svg+xml" />
  <style>body {{ margin: 0; background: #050603; }}</style>
</head>
<body>
  <redoc spec-url="{openapi_url}"
         theme='{{"colors":{{"primary":{{"main":"#7c9858"}}}}}}'></redoc>
  <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js"></script>
</body>
</html>"""
    return HTMLResponse(html)


def render_docs_html(openapi_url: str = "/openapi.json") -> HTMLResponse:
    """Return the HackRitual-themed Swagger UI page."""
    html = f"""<!doctype html>
<html lang="en" data-theme="hacker-solarpunk">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>HackRitual · API</title>
  <link rel="icon" href="/icon.svg" type="image/svg+xml" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400;1,500&family=IBM+Plex+Mono:wght@400;500;600&display=swap" />
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css" />
  <style>{_SWAGGER_THEME_CSS}</style>
</head>
<body>
  <header class="hr-header">
    <a href="/" class="hr-back">← back to the ritual</a>
    <div class="hr-brand">
      <span class="hr-diamond">◆</span>
      <span class="hr-name">HackRitual</span>
      <span class="hr-sub">/ the spellbook</span>
    </div>
    <button type="button" class="hr-theme-toggle" id="hr-theme-toggle">▾ theme</button>
  </header>
  <main>
    <div id="swagger-ui"></div>
  </main>
  <footer class="hr-footer">
    <span>v0.1.0</span>
    <span>·</span>
    <a href="{openapi_url}">openapi.json</a>
    <span>·</span>
    <a href="/api/health">health</a>
    <span>·</span>
    <a href="/">back to the ritual</a>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"
          crossorigin></script>
  <script>
    window.addEventListener('load', function () {{
      const stored = (() => {{
        try {{ return localStorage.getItem('hackritual:theme') || 'hacker-solarpunk'; }}
        catch {{ return 'hacker-solarpunk'; }}
      }})();
      document.documentElement.setAttribute('data-theme', stored);

      document.getElementById('hr-theme-toggle').addEventListener('click', function () {{
        const cur = document.documentElement.getAttribute('data-theme');
        const next = cur === 'hacker-solarpunk' ? 'paper-grimoire' : 'hacker-solarpunk';
        document.documentElement.setAttribute('data-theme', next);
        try {{ localStorage.setItem('hackritual:theme', next); }} catch {{}}
      }});

      SwaggerUIBundle({{
        url: '{openapi_url}',
        dom_id: '#swagger-ui',
        presets: [SwaggerUIBundle.presets.apis],
        layout: 'BaseLayout',
        deepLinking: true,
        filter: true,
        docExpansion: 'list',
        tryItOutEnabled: true,
        syntaxHighlight: {{ activate: true, theme: 'agate' }},
        defaultModelsExpandDepth: 0,
      }});
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(html)
