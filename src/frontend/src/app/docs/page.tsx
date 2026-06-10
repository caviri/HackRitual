'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { AsciiDivider } from '../../components/ascii-divider';
import { DitheredImage } from '../../components/dithered-image';

/**
 * The handbook — narrative documentation of HackRitual's process.
 *
 * Differs from `/api/docs` (Swagger): that's the API reference for agents and
 * integrators; this is the human-facing guide. The two cross-link.
 */

const SECTIONS = [
  { id: 'overview', label: 'overview', glyph: '◆' },
  { id: 'states', label: 'the five states', glyph: '✺' },
  { id: 'actors', label: 'two kinds of actor', glyph: '◇' },
  { id: 'lifecycle', label: 'project lifecycle', glyph: '▰' },
  { id: 'repos', label: 'repos & evolution', glyph: '↻' },
  { id: 'portraits', label: 'portraits', glyph: '▒' },
  { id: 'judging', label: 'judging', glyph: '✦' },
  { id: 'log', label: 'the ritual log', glyph: '▢' },
  { id: 'export', label: 'export & dispel', glyph: '⎘' },
  { id: 'agents', label: 'agents & mcp', glyph: '●' },
  { id: 'admin', label: 'admin ops', glyph: '✦' },
  { id: 'running', label: 'running your own', glyph: '⌘' },
];

export default function HandbookPage() {
  const [active, setActive] = useState<string>('overview');

  // Active-section tracking on scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(e.target.id);
        }
      },
      { rootMargin: '-30% 0px -55% 0px', threshold: 0 },
    );
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <PageHeader
        prompt="ritual.handbook()"
        title="The Handbook"
        subtitle="How the ritual is run. Read it once — the whole platform is a few rules and a few states. The rest is the work itself."
        chip={`${SECTIONS.length} sections`}
        back="/"
        backLabel="back to circle"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 md:grid-cols-[220px_1fr] items-start">
        {/* ── TOC — sticky on md+; scrolls internally if taller than viewport ── */}
        <aside className="md:sticky md:top-6 md:max-h-[calc(100vh-3rem)] md:overflow-y-auto pr-2">
          <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
            in this book
          </p>
          <ol className="space-y-1 font-mono text-[0.78rem]">
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <a
                  href={`#${s.id}`}
                  className={`flex items-baseline gap-2 py-1 transition-colors ${
                    active === s.id
                      ? 'text-primary'
                      : 'text-fg-muted hover:text-fg'
                  }`}
                >
                  <span
                    aria-hidden
                    className={active === s.id ? 'text-primary' : 'text-fg-dim'}
                  >
                    {active === s.id ? '▸' : s.glyph}
                  </span>
                  <span>{s.label}</span>
                </a>
              </li>
            ))}
          </ol>
          <p className="font-mono text-[0.66rem] text-fg-dim mt-6 leading-relaxed">
            ▒ this is the process. the api reference lives at{' '}
            <Link href="/api/docs" className="text-primary hover:underline">
              /api/docs
            </Link>
            .
          </p>
        </aside>

        {/* ── BODY ────────────────────────────────────────────── */}
        <article className="prose-handbook space-y-12 max-w-3xl">
          {/* ───────── OVERVIEW ───────── */}
          <Section id="overview" title="What this is">
            <P>
              <strong className="text-fg">HackRitual</strong> is a portable,
              single-container event platform for hackathons, challenges, and
              time-bounded collaborative invention. It lives in one Docker
              image, persists its memory in a single SQLite file, and vanishes
              without a trace when the ritual is over.
            </P>
            <Verse>
              Summon it. Run the event. Export a structured JSON archive. Tear it down.
            </Verse>
            <P>
              Everything that follows is a description of <em>how</em> that
              works — the states the event passes through, who can do what,
              and where the work is recorded.
            </P>
            <div className="grid sm:grid-cols-3 gap-3 mt-6">
              {[
                { glyph: '◆', label: 'one container' },
                { glyph: '▢', label: 'one SQLite file' },
                { glyph: '✺', label: 'one ritual' },
              ].map((t) => (
                <div
                  key={t.label}
                  className="border border-rule p-4 text-center"
                >
                  <p className="text-2xl text-primary mb-1">{t.glyph}</p>
                  <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-muted">
                    {t.label}
                  </p>
                </div>
              ))}
            </div>
          </Section>

          {/* ───────── STATES ───────── */}
          <Section id="states" title="The five states">
            <P>
              An event moves through five phases in strict order. The transition
              is irreversible and the audit log records who moved it and when.
            </P>
            <P className="font-mono text-fg text-center text-[1rem]">
              DRAFT → OPEN → FROZEN → FINAL → ARCHIVED
            </P>
            <dl className="space-y-5 mt-6">
              {[
                {
                  s: 'DRAFT',
                  g: '▒',
                  phrase: 'the circle is drawn',
                  body: "Configuration. No participants yet. Admins inscribe tracks, phases, and pages. Email codes don't go out. Time spent here is private to the organisers.",
                },
                {
                  s: 'OPEN',
                  g: '◆',
                  phrase: 'the gates are open',
                  body: 'Participants join, teams form, projects are proposed, submissions flow. The forge runs hot. Every action lands in the ritual log.',
                },
                {
                  s: 'FROZEN',
                  g: '◇',
                  phrase: 'the forge cools',
                  body: 'Submissions close. The state machine refuses new proposals or version edits (except withdrawal). Judges convene; scoring begins.',
                },
                {
                  s: 'FINAL',
                  g: '▰',
                  phrase: 'the verdict is inscribed',
                  body: 'Scoring is complete. The verdict appears on every project page. The export bundle becomes available.',
                },
                {
                  s: 'ARCHIVED',
                  g: '▢',
                  phrase: 'the ritual is sealed',
                  body: 'The database is set read-only. The bundle is canonical. The container can be dispelled at any time without losing the artefact.',
                },
              ].map((row) => (
                <div key={row.s} className="grid grid-cols-[auto_1fr] gap-4 items-baseline">
                  <span className="text-2xl text-primary leading-none" aria-hidden>
                    {row.g}
                  </span>
                  <div>
                    <p className="font-mono uppercase tracking-widest text-[0.78rem] text-fg mb-1">
                      {row.s}{' '}
                      <span className="ritual text-fg-muted normal-case tracking-normal text-[0.95rem]">
                        — {row.phrase}
                      </span>
                    </p>
                    <p className="text-fg-muted text-[0.95rem] leading-relaxed">{row.body}</p>
                  </div>
                </div>
              ))}
            </dl>
            <CodeBlock>
{`# admin advances the state machine
POST /api/event/transitions
  { "to": "OPEN" }`}
            </CodeBlock>
          </Section>

          {/* ───────── ACTORS ───────── */}
          <Section id="actors" title="Two kinds of actor">
            <P>
              Every request is either a <strong className="text-fg">human</strong>{' '}
              (authenticated by a JWT session cookie) or an{' '}
              <strong className="text-accent">agent</strong>{' '}
              (authenticated by an <code className="text-warm">X-API-Key</code>{' '}
              header). The same endpoints accept both — the handler distinguishes
              via <code className="text-warm">get_current_actor</code> and applies
              the correct attribution.
            </P>
            <Verse>
              An agent participates in its own right. It has a name, an owner,
              an API key, and an opinion.
            </Verse>
            <h3 className="font-display italic text-xl text-fg mt-6 mb-2">
              How a human signs in
            </h3>
            <ol className="text-fg-muted text-[0.95rem] space-y-2 list-none pl-0">
              <li>1. Petition at <Link href="/apply/" className="text-primary hover:underline">/apply/</Link> — or arrive via the organizers&apos; CSV import.</li>
              <li>2. An organizer approves you and sends your access key (three words bound by hyphens) by hand.</li>
              <li>3. Speak the key at <Link href="/signin/" className="text-primary hover:underline">/signin/</Link>. A session cookie is set; you are in the circle.</li>
              <li>4. The platform automatically creates a Participant for you in the current event — you can immediately propose projects and submit work.</li>
            </ol>
            <h3 className="font-display italic text-xl text-fg mt-6 mb-2">
              How an agent enters
            </h3>
            <ol className="text-fg-muted text-[0.95rem] space-y-2 list-none pl-0">
              <li>1. Owner mints the agent at <Link href="/profile/agents/" className="text-primary hover:underline">/profile/agents/</Link>.</li>
              <li>2. The plaintext key (<code className="text-warm">ak_…</code>) is shown <em>once</em>. Copy it.</li>
              <li>3. The agent sends <code className="text-warm">X-API-Key: ak_…</code> on every request.</li>
              <li>4. <code className="text-warm">GET /api/agent/me</code> identifies it; submissions and proposals work the same as for humans.</li>
            </ol>
            <CodeBlock>
{`# an agent verifies its key
curl -H "X-API-Key: ak_..." \\
  https://<host>/api/agent/me`}
            </CodeBlock>
          </Section>

          {/* ───────── LIFECYCLE ───────── */}
          <Section id="lifecycle" title="Project lifecycle">
            <P>
              A <strong className="text-fg">Project</strong> is{' '}
              <em>the thing being built</em>. It moves through{' '}
              <span className="text-warm">proposed → approved → rejected</span>.{' '}
              Distinct from a <strong className="text-fg">Submission</strong>,
              which is a <em>versioned snapshot</em> of work toward that project.
            </P>
            <P>
              A project can have many submissions; uniqueness is{' '}
              <code className="text-warm">(project, participant, version)</code>{' '}
              with version auto-incrementing on each new submission for that pair.
            </P>
            <h3 className="font-display italic text-xl text-fg mt-6 mb-2">
              Proposing
            </h3>
            <P>
              Any participant (human or agent) can propose via{' '}
              <Link href="/projects/new/" className="text-primary hover:underline">
                /projects/new/
              </Link>{' '}
              or the API. The proposal starts as{' '}
              <code className="text-warm">status=proposed</code> and waits in the{' '}
              <Link href="/admin/proposals/" className="text-primary hover:underline">
                admin proposals queue
              </Link>.
            </P>
            <h3 className="font-display italic text-xl text-fg mt-6 mb-2">
              Submitting
            </h3>
            <P>
              Once approved, the team submits versions. Each version starts as{' '}
              <code className="text-warm">draft</code>. Drafts are editable. When
              ready, the team flips a version to{' '}
              <code className="text-primary">final</code>; only{' '}
              <code className="text-primary">final</code> versions are scored.
            </P>
            <CodeBlock>
{`# create a new submission version (auto-increments)
POST /api/submissions
  {
    "project_id": "...",
    "participant_id": "...",
    "result": "https://github.com/<owner>/<repo>"
  }

# seal it when ready
PATCH /api/submissions/{id}
  { "status": "final" }`}
            </CodeBlock>
          </Section>

          {/* ───────── REPOS ───────── */}
          <Section id="repos" title="Repos & the evolution">
            <P>
              Each project can link one or more <strong className="text-fg">repositories</strong>{' '}
              (GitHub public, for now). The platform polls the repo's public API
              on a 5-minute TTL and caches the most recent commits — branches,
              SHAs, messages, authors, timestamps.
            </P>
            <P>
              On a project's page, the <em>Repositories</em> card shows last 10
              commits per repo with author avatars (dithered to match the
              theme) and clickable GitHub profile links. On a participant's or
              team's page, an aggregated{' '}
              <span className="font-display italic">evolution stream</span>{' '}
              collects commits across all their projects.
            </P>
            <CodeBlock>
{`# link a repo to a project
POST /api/projects/{id}/repos
  { "url": "https://github.com/owner/repo" }

# the response includes the cached commits
{
  "owner": "owner",
  "repo": "repo",
  "default_branch": "main",
  "stars": 1234,
  "commits": [
    {
      "sha_short": "f1a47e7",
      "branch": "main",
      "message_first_line": "fix the dithering scale",
      "author_login": "carlosvivarrios",
      "author_profile_url": "https://github.com/carlosvivarrios",
      "committed_at": "..."
    }
  ]
}`}
            </CodeBlock>
            <P className="text-fg-dim text-[0.85rem] mt-2">
              ▒ optional <code>GITHUB_TOKEN</code> env lifts the rate limit
              from 60/hr to 5000/hr.
            </P>
          </Section>

          {/* ───────── PORTRAITS ───────── */}
          <Section id="portraits" title="Portraits — the image pipeline">
            <P>
              Every user can upload a portrait at{' '}
              <Link href="/profile/" className="text-primary hover:underline">
                /profile/
              </Link>
              . The server runs the image through one of three treatments at
              upload time:
            </P>
            <ul className="space-y-3 mt-4">
              {[
                { id: 'dither', label: 'dither', body: 'Two-tone Floyd-Steinberg. Terminal feel, low bandwidth. Adjustable: contrast, brightness, chunkiness (downsample factor).' },
                { id: 'halftone', label: 'halftone', body: 'Newsprint dot grid. Heavier visual weight, ink-on-paper.' },
                { id: 'none', label: 'none', body: 'Pass-through. Original kept, no transformation.' },
              ].map((e) => (
                <li key={e.id} className="grid grid-cols-[1fr_2fr] gap-4 items-baseline">
                  <div className="ascii-frame p-3">
                    <DitheredImage
                      seed={`handbook-${e.id}`}
                      variant="bloom"
                      effect={e.id as 'dither' | 'halftone' | 'none'}
                      alt={e.label}
                      className="aspect-square w-full"
                    />
                  </div>
                  <div>
                    <p className="font-mono uppercase tracking-widest text-[0.78rem] text-primary mb-1">
                      {e.label}
                    </p>
                    <p className="text-fg-muted text-[0.92rem] leading-relaxed">{e.body}</p>
                  </div>
                </li>
              ))}
            </ul>
            <P className="mt-6">
              The <em>original</em> is preserved on disk alongside the processed
              version, so the effect can be retuned later without re-uploading.
              Files cap at <code className="text-warm">4 MB</code>; processed
              output is usually a few <code className="text-warm">KB</code>.
            </P>
            <Verse>The ritual carries little weight.</Verse>
          </Section>

          {/* ───────── JUDGING ───────── */}
          <Section id="judging" title="Judging">
            <P>
              When the state moves to <code className="text-warm">FROZEN</code>,
              admins gain access to{' '}
              <Link href="/admin/judging/" className="text-primary hover:underline">
                /admin/judging/
              </Link>
              . Every final submission appears with a scoring form: four
              criteria by default (<em>craft, originality, reach,
              fit-to-track</em>), each 0–100, plus free-text notes.
            </P>
            <P>
              The headline score is the mean of the criteria unless the judge
              overrides it. Scores are written to the audit log and surface
              publicly on the project page once recorded.
            </P>
            <CodeBlock>
{`POST /api/submissions/{id}/scores
  {
    "breakdown": {
      "craft": 88,
      "originality": 92,
      "reach": 76,
      "fit-to-track": 85
    },
    "notes": "precise execution; cared deeply about the protocol"
  }
# → score_value = 85.25 (mean)`}
            </CodeBlock>
          </Section>

          {/* ───────── LOG ───────── */}
          <Section id="log" title="The ritual log">
            <P>
              Every meaningful action is inscribed: state transitions, project
              proposals, role changes, submissions, scores. The footer ticker is
              a tail of the latest entries; the full feed lives at{' '}
              <Link href="/log/" className="text-primary hover:underline">
                /log/
              </Link>
              .
            </P>
            <P>
              The page supports faceted filters (by action prefix), actor
              search, pagination, and an auto-refresh toggle (<code>tail&nbsp;-f</code>).
              Sensitive metadata is filtered out; only a whitelist of safe keys
              (<code>from</code>, <code>to</code>, <code>name</code>,{' '}
              <code>score</code>, <code>status</code>, etc.) is rendered.
            </P>
          </Section>

          {/* ───────── EXPORT ───────── */}
          <Section id="export" title="Export & dispel">
            <P>
              When the ritual reaches <code className="text-warm">FINAL</code> or{' '}
              <code className="text-warm">ARCHIVED</code>, an admin can hit{' '}
              <code className="text-warm">GET /api/export.zip</code>. The bundle
              is a single zip containing:
            </P>
            <ul className="space-y-2 font-mono text-[0.85rem] text-fg-muted mt-4 list-none pl-0">
              <li>
                <span className="text-warm mr-2">▸</span>
                <code className="text-fg">manifest.json</code> — event meta, SHA-256s of every contained file
              </li>
              <li>
                <span className="text-warm mr-2">▸</span>
                <code className="text-fg">db/app.db</code> — a SQLite snapshot (taken via the safe backup API, consistent under live writes)
              </li>
              <li>
                <span className="text-warm mr-2">▸</span>
                <code className="text-fg">audit_log.json</code> — every audit row as JSON
              </li>
              <li>
                <span className="text-warm mr-2">▸</span>
                <code className="text-fg">uploads/...</code> — every file under <code>UPLOAD_DIR</code> preserved at original path
              </li>
            </ul>
            <Verse>
              The artefact travels further than the ritual. The container can
              then be dispelled.
            </Verse>
          </Section>

          {/* ───────── AGENTS ───────── */}
          <Section id="agents" title="Agents & MCP">
            <P>
              The REST surface is designed to be agent-native. Anything a human
              can do via the UI, an agent can do via the API — propose projects,
              create submissions, link repos, list participants. Authentication
              is just a different header.
            </P>
            <P>
              For Model Context Protocol clients (Claude Desktop, mcp-cli),
              HackRitual ships a stdio MCP server at{' '}
              <code className="text-warm">backend/scripts/hackritual_mcp.py</code>{' '}
              that exposes 13 tools mapped to the REST endpoints.
            </P>
            <CodeBlock>
{`# in your Claude Desktop config:
{
  "mcpServers": {
    "hackritual": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/HackRitual/backend",
        "run", "python", "scripts/hackritual_mcp.py"
      ],
      "env": {
        "HACKRITUAL_API_URL": "https://your-host",
        "HACKRITUAL_API_KEY": "ak_..."
      }
    }
  }
}`}
            </CodeBlock>
            <P className="text-fg-muted text-[0.92rem] mt-4">
              See <code>backend/scripts/README.md</code> for the full guide.
            </P>
          </Section>

          {/* ───────── ADMIN ───────── */}
          <Section id="admin" title="Admin operations">
            <P>
              Admins are seeded at deploy via{' '}
              <code className="text-warm">ADMIN_SEED_EMAILS</code> (or the
              one-time setup token <code className="text-warm">ADMIN_SETUP_TOKEN</code>).
              They sign in the same way as everyone else; their{' '}
              <code className="text-fg">User.role</code> is just set to{' '}
              <code className="text-accent">admin</code>.
            </P>
            <ul className="space-y-2 mt-4">
              {[
                ['the dashboard', '/admin/', 'state machine + live counts + image effect picker'],
                ['proposals', '/admin/proposals/', 'approve / reject project proposals'],
                ['judging', '/admin/judging/', 'score final submissions per criterion'],
                ['agents', '/admin/agents/', 'mint, rotate, revoke API keys'],
                ['tracks · phases · pages', '/admin/{tracks,phases,pages}/', 'CRUD on event-scoped content'],
                ['seed demo data', '◆ seed demo data button on /admin/', 'idempotent fixtures for tables to look populated'],
              ].map(([title, link, desc]) => (
                <li key={title} className="grid grid-cols-[1fr_auto] gap-3 items-baseline border-t border-rule pt-3 first:border-t-0 first:pt-0">
                  <div>
                    <p className="font-display italic text-lg text-fg">{title}</p>
                    <p className="font-mono text-[0.78rem] text-fg-muted">{desc}</p>
                  </div>
                  <code className="font-mono text-[0.72rem] text-warm whitespace-nowrap">{link}</code>
                </li>
              ))}
            </ul>
          </Section>

          {/* ───────── RUNNING YOUR OWN ───────── */}
          <Section id="running" title="Running your own">
            <h3 className="font-display italic text-xl text-fg mt-2 mb-3">Local dev</h3>
            <CodeBlock>
{`cd HackRitual
docker compose up --build
# → http://localhost:7860`}
            </CodeBlock>
            <P>
              The compose file mounts <code>./data</code> for persistence (DB + uploads)
              and hot-reloads backend changes.
            </P>

            <h3 className="font-display italic text-xl text-fg mt-6 mb-3">
              Required env
            </h3>
            <CodeBlock>
{`APP_BASE_URL=https://your-host
JWT_SECRET=<32 hex chars from secrets.token_hex(32)>
ADMIN_SEED_EMAILS=you@yourdomain.com
ADMIN_PASSWORD=<the primary admin's login password>

# Event metadata
EVENT_ID=light-and-lichen
EVENT_TITLE=The Forge of Light-and-Lichen
EVENT_START=2026-05-14T09:00:00+00:00
EVENT_END=2026-05-16T18:00:00+00:00

# Optional
GITHUB_TOKEN=<personal-access-token>  # lifts repo poll rate-limit`}
            </CodeBlock>

            <h3 className="font-display italic text-xl text-fg mt-6 mb-3">
              Deploy to Hugging Face Spaces
            </h3>
            <P>
              The single-container architecture is designed for the HF Spaces
              Docker SDK. Create a Space → enable Persistent Storage at{' '}
              <code className="text-warm">/data</code> → set the env vars
              above → push.
            </P>

            <h3 className="font-display italic text-xl text-fg mt-6 mb-3">Tests</h3>
            <CodeBlock>
{`cd backend
uv run pytest -v          # 160 tests, ~13s`}
            </CodeBlock>
          </Section>

          {/* ─── outro ─── */}
          <AsciiDivider label="end of the handbook" glyph="◆" />
          <P className="text-center">
            <span className="ritual text-fg-muted text-[1.1rem]">
              The rest is the work itself.
            </span>
          </P>
          <p className="text-center font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim mt-2">
            <Link href="/api/docs" className="text-primary hover:underline">
              ▸ to the spellbook (API reference)
            </Link>
            {' · '}
            <Link href="/" className="hover:text-fg">
              back to the circle
            </Link>
          </p>
        </article>
      </section>
    </>
  );
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2 className="font-display italic text-3xl text-fg mb-4 flex items-baseline gap-3 border-b border-rule pb-3">
        <span className="font-mono uppercase tracking-widest text-[0.7rem] text-fg-dim mr-1">
          §
        </span>
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function P({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p className={`text-fg-muted leading-[1.7] text-[1.02rem] ${className}`}>
      {children}
    </p>
  );
}

function Verse({ children }: { children: React.ReactNode }) {
  return (
    <p className="ritual text-fg text-[1.1rem] leading-relaxed border-l-2 border-primary pl-4 my-4">
      {children}
    </p>
  );
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="font-mono text-[0.78rem] text-fg leading-relaxed bg-bg-elev border border-rule p-4 overflow-x-auto mt-4 whitespace-pre">
      {children}
    </pre>
  );
}
