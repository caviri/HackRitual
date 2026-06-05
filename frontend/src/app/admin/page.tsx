'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import {
  IMAGE_EFFECTS,
  ImageEffect,
  readSettings,
  writeSettings,
} from '../../lib/settings';
import { useStage } from '../../lib/use-stage';
import {
  api,
  type EventDTO,
  type ProjectDTO,
  type SubmissionDTO,
  type TrackDTO,
  type PhaseDTO,
  type ParticipantDTO,
} from '../../lib/api';

const STATE_TRANSITIONS: Record<
  string,
  { label: string; to: string; tone: 'primary' | 'warm' | 'accent' | 'danger' }[]
> = {
  DRAFT: [{ label: 'open the gates', to: 'OPEN', tone: 'primary' }],
  OPEN: [{ label: 'seal the forge', to: 'FROZEN', tone: 'warm' }],
  FROZEN: [{ label: 'inscribe the verdict', to: 'FINAL', tone: 'accent' }],
  FINAL: [{ label: 'seal the record', to: 'ARCHIVED', tone: 'primary' }],
  ARCHIVED: [],
};

export default function AdminPage() {
  const data = useStage();
  const [effect, setEffect] = useState<ImageEffect>('dither');
  const [event, setEvent] = useState<EventDTO | null>(null);
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [participants, setParticipants] = useState<ParticipantDTO[]>([]);
  const [submissions, setSubmissions] = useState<SubmissionDTO[]>([]);
  const [tracks, setTracks] = useState<TrackDTO[]>([]);
  const [phases, setPhases] = useState<PhaseDTO[]>([]);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  useEffect(() => {
    setEffect(readSettings().imageEffect);
    void Promise.all([
      api.event().then(setEvent),
      api.projects().then(setProjects),
      api.participants().then(setParticipants),
      api.submissions().then(setSubmissions),
      api.tracks().then(setTracks),
      api.phases().then(setPhases),
    ]);
  }, []);

  function chooseEffect(id: ImageEffect) {
    setEffect(id);
    writeSettings({ imageEffect: id });
  }

  async function doTransition(to: string) {
    if (!confirm(`Transition the event to ${to}? Irreversible.`)) return;
    setBusy(true);
    try {
      const res = await fetch('/api/event/transitions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ to }),
      });
      if (!res.ok) throw new Error(await res.text());
      const updated = (await res.json()) as EventDTO;
      setEvent(updated);
      setFlash(`the ritual moved to ${updated.state}.`);
    } catch (err) {
      setFlash(`transition failed: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  }

  const stateLive = event?.state ?? data.state;
  const proposedCount = projects.filter((p) => p.status === 'proposed').length;
  const approvedCount = projects.filter((p) => p.status === 'approved').length;
  const finalSubs = submissions.filter((s) => s.status === 'final').length;
  const draftSubs = submissions.filter((s) => s.status === 'draft').length;
  const waitlist = (participants as ParticipantDTO[]).filter(
    (p) => (p as unknown as { is_waiting?: boolean }).is_waiting,
  ).length;

  return (
    <>
      <PageHeader
        prompt="ritual.admin()"
        title="Admin console"
        subtitle="The keeper's view of the ritual. Move the state machine. Approve proposals. Mint agents."
        chip={`state: ${stateLive}`}
      />

      {/* ───── headline stats strip ───── */}
      <section className="border-b border-rule">
        <div className="mx-auto w-full max-w-6xl px-6 py-6 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          <Stat label="state" value={stateLive} tone="primary" />
          <Stat label="participants" value={String(participants.length)} />
          <Stat label="waitlist" value={String(waitlist)} tone="warm" />
          <Stat label="projects" value={String(projects.length)} />
          <Stat
            label="proposed"
            value={String(proposedCount)}
            tone={proposedCount > 0 ? 'accent' : 'muted'}
          />
          <Stat
            label="submissions (final)"
            value={`${finalSubs} / ${submissions.length}`}
          />
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[2fr_1fr]">
        {/* ───── MAIN ───── */}
        <div className="space-y-10">
          {/* state machine */}
          <article className="ascii-frame p-6">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              the state machine
            </p>
            <p className="font-display italic text-2xl text-fg mb-2">
              The ritual is in {stateLive}.
            </p>
            <p className="text-fg-muted text-[0.95rem] leading-relaxed mb-6">
              Each transition is irreversible. The audit log records who moved
              the state and when.
            </p>
            <div className="flex flex-wrap gap-3 items-center">
              {(STATE_TRANSITIONS[stateLive] ?? []).length === 0 ? (
                <p className="font-mono text-[0.78rem] text-fg-muted">
                  ▒ no forward transitions available from this state
                </p>
              ) : (
                (STATE_TRANSITIONS[stateLive] ?? []).map((t) => (
                  <button
                    key={t.to}
                    type="button"
                    disabled={busy}
                    onClick={() => doTransition(t.to)}
                    className={`btn ${t.tone === 'danger' ? '!border-danger !text-danger' : ''}`}
                  >
                    <span aria-hidden>▸</span>
                    {t.label}
                  </button>
                ))
              )}
              {flash && (
                <span className="font-mono text-[0.78rem] text-warm ml-2">▸ {flash}</span>
              )}
            </div>
          </article>

          {/* awaiting your action */}
          <article>
            <h2 className="font-display italic text-2xl text-fg mb-4">
              Awaiting your action
            </h2>
            <ul className="grid gap-3 sm:grid-cols-2">
              <ActionCard
                title="review proposals"
                count={proposedCount}
                blurb="projects waiting to be approved or rejected"
                href="/admin/proposals/"
                tone={proposedCount > 0 ? 'accent' : 'muted'}
                glyph="◇"
              />
              <ActionCard
                title="agents"
                count={participants.filter((p) => p.type === 'agent').length}
                blurb="mint API keys for autonomous participants"
                href="/admin/agents/"
                tone="primary"
                glyph="◆"
              />
              <ActionCard
                title="tracks"
                count={tracks.length}
                blurb="thematic groupings for projects"
                href="/admin/tracks/"
                glyph="▰"
              />
              <ActionCard
                title="phases"
                count={phases.length}
                blurb="temporal sub-phases within OPEN"
                href="/admin/phases/"
                glyph="▢"
              />
            </ul>
          </article>

          {/* image effect — live preview */}
          <article className="ascii-frame p-6">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-4">
              image rites · default treatment
            </p>
            <p className="font-display italic text-2xl text-fg mb-2">
              How uploads are pressed.
            </p>
            <p className="text-fg-muted text-[0.95rem] leading-relaxed mb-6">
              The default effect runs at upload time on the server. Two-tone
              dither for the lowest bandwidth and a terminal feel; ink-on-paper
              halftone for an archival look; or pass-through for raw uploads.
              Override per-upload in the profile / new-submission forms.
            </p>
            <div className="grid gap-4 md:grid-cols-3 mb-4">
              {IMAGE_EFFECTS.map((e) => {
                const active = e.id === effect;
                return (
                  <button
                    key={e.id}
                    type="button"
                    onClick={() => chooseEffect(e.id)}
                    aria-pressed={active}
                    className={`text-left border p-3 transition-colors ${
                      active ? 'border-primary' : 'border-rule hover:border-rule-bright'
                    }`}
                  >
                    <DitheredImage
                      seed={`admin-preview-${e.id}`}
                      variant="bloom"
                      alt={`${e.id} preview`}
                      effect={e.id}
                      className="aspect-[4/3] w-full mb-3"
                    />
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className={`font-mono text-[0.85rem] ${active ? 'text-primary' : 'text-fg'}`}
                      >
                        {active && <span className="mr-1.5">▸</span>}
                        {e.label}
                      </span>
                    </div>
                    <p className="text-fg-muted text-[0.78rem] leading-snug">
                      {e.blurb}
                    </p>
                  </button>
                );
              })}
            </div>
          </article>
        </div>

        {/* ───── SIDEBAR ───── */}
        <aside className="space-y-6">
          <nav className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              admin paths
            </p>
            <ul className="space-y-2 font-mono text-[0.85rem]">
              <li>
                <Link href="/admin/proposals/" className="text-fg-muted hover:text-primary">
                  ▸ proposals
                  {proposedCount > 0 && (
                    <span className="text-accent ml-2">[{proposedCount}]</span>
                  )}
                </Link>
              </li>
              <li><Link href="/admin/agents/" className="text-fg-muted hover:text-primary">▸ agents</Link></li>
              <li><Link href="/admin/tracks/" className="text-fg-muted hover:text-primary">▸ tracks</Link></li>
              <li><Link href="/admin/phases/" className="text-fg-muted hover:text-primary">▸ phases</Link></li>
              <li><Link href="/admin/pages/" className="text-fg-muted hover:text-primary">▸ content pages</Link></li>
            </ul>
          </nav>

          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              counts
            </p>
            <ul className="font-mono text-[0.82rem] space-y-2">
              <li><span className="text-fg-dim">in        </span><span className="text-fg tabular-nums">{participants.length}</span></li>
              <li><span className="text-fg-dim">wait      </span><span className="text-warm tabular-nums">{waitlist}</span></li>
              <li><span className="text-fg-dim">teams     </span><span className="text-fg tabular-nums">{participants.filter((p) => p.type === 'team').length}</span></li>
              <li><span className="text-fg-dim">agents    </span><span className="text-accent tabular-nums">{participants.filter((p) => p.type === 'agent').length}</span></li>
              <li><span className="text-fg-dim">proposed  </span><span className="text-fg tabular-nums">{proposedCount}</span></li>
              <li><span className="text-fg-dim">approved  </span><span className="text-fg tabular-nums">{approvedCount}</span></li>
              <li><span className="text-fg-dim">final subs</span><span className="text-primary tabular-nums">{finalSubs}</span></li>
              <li><span className="text-fg-dim">draft subs</span><span className="text-fg-muted tabular-nums">{draftSubs}</span></li>
            </ul>
          </div>

          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              demo data
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setFlash(null);
                try {
                  const counts = await api.seedDemoData();
                  setFlash(
                    `seeded · ${Object.entries(counts)
                      .filter(([, v]) => v > 0)
                      .map(([k, v]) => `${k.replace('_created', '')}=${v}`)
                      .join(' · ') || 'nothing new (already seeded)'}`,
                  );
                  // reload the lists so the tables update
                  void Promise.all([
                    api.projects().then(setProjects),
                    api.participants().then(setParticipants),
                    api.submissions().then(setSubmissions),
                    api.tracks().then(setTracks),
                    api.phases().then(setPhases),
                  ]);
                } catch (err) {
                  setFlash(`seed failed: ${String(err)}`);
                } finally {
                  setBusy(false);
                }
              }}
              className="btn w-full justify-center mb-3"
            >
              ◆ seed demo data
            </button>
            <p className="font-mono text-[0.7rem] text-fg-dim leading-relaxed mb-3">
              idempotent — only adds what's missing. tracks · phases · pages ·
              participants · projects · submissions.
            </p>
          </div>

          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              showcase · public-safe
            </p>
            <p className="font-mono text-[0.7rem] text-fg-dim leading-relaxed mb-3">
              the digest. no emails, no IPs, no admin metadata. drop on a static
              site as a reminder.
            </p>
            <a
              href="/api/export/showcase.html"
              target="_blank"
              rel="noopener"
              className="btn w-full justify-center mb-2 !text-[0.72rem]"
            >
              ◆ preview / download showcase.html
            </a>
            <a
              href="/api/export/showcase.json"
              className="btn btn-ghost w-full justify-center !text-[0.72rem]"
            >
              ▰ download showcase.json
            </a>
          </div>

          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              backup · full bundle
            </p>
            <p className="font-mono text-[0.7rem] text-fg-dim leading-relaxed mb-3">
              SQLite snapshot · all uploads · audit log · showcase files · manifest
              with sha256s. one zip, available in FINAL/ARCHIVED.
            </p>
            <a
              href="/api/export.zip"
              className="btn btn-ghost w-full justify-center !text-[0.72rem]"
            >
              ⎘ download bundle.zip
            </a>
          </div>
        </aside>
      </section>
    </>
  );
}

function Stat({
  label,
  value,
  tone = 'normal',
}: {
  label: string;
  value: string;
  tone?: 'primary' | 'accent' | 'warm' | 'muted' | 'normal';
}) {
  const tones: Record<string, string> = {
    primary: 'text-primary',
    accent: 'text-accent',
    warm: 'text-warm',
    muted: 'text-fg-muted',
    normal: 'text-fg',
  };
  return (
    <div className="border border-rule px-3 py-2.5">
      <p className="font-mono text-[0.62rem] uppercase tracking-widest text-fg-dim mb-1">
        {label}
      </p>
      <p className={`font-display italic text-2xl leading-none ${tones[tone]}`}>
        {value}
      </p>
    </div>
  );
}

function ActionCard({
  title,
  count,
  blurb,
  href,
  tone = 'normal',
  glyph,
}: {
  title: string;
  count: number;
  blurb: string;
  href: string;
  tone?: 'primary' | 'accent' | 'warm' | 'muted' | 'normal';
  glyph: string;
}) {
  const accentMap: Record<string, string> = {
    primary: 'text-primary',
    accent: 'text-accent animate-pulse-glow',
    warm: 'text-warm',
    muted: 'text-fg-dim',
    normal: 'text-fg-muted',
  };
  return (
    <li>
      <Link
        href={href}
        className="ascii-frame block p-4 no-underline group hover:border-primary transition-colors"
      >
        <header className="flex items-baseline justify-between gap-3 mb-1.5">
          <span className={`text-xl ${accentMap[tone]}`} aria-hidden>
            {glyph}
          </span>
          <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim tabular-nums">
            {count}
          </span>
        </header>
        <p className="font-display italic text-lg text-fg group-hover:text-primary transition-colors">
          {title}
        </p>
        <p className="text-fg-muted text-[0.78rem] leading-snug mt-1">{blurb}</p>
      </Link>
    </li>
  );
}
