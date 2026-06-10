'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { AsciiDivider } from '../components/ascii-divider';
import { StatusBadge } from '../components/status-badge';
import { LiveCountdown } from '../components/live-countdown';
import { WinnerShowcase } from '../components/winner-showcase';
import { DitheredImage } from '../components/dithered-image';
import { api, type AnnouncementDTO } from '../lib/api';
import type { ImageVariant } from '../lib/mocks';
import {
  STATES,
  type EventState,
  type StageData,
  getStageData,
  parseStageFromUrl,
} from '../lib/mocks';

/**
 * Landing — state-aware via ?stage= URL param.
 *
 * Every section reads from the active StageData: hero copy, phase grid,
 * proposals, participants, tracks, countdown. The page tells five distinct
 * stories — and the stage switcher in the top bar flips between them.
 */

const TITLE_ACCENT_CLASS: Record<StageData['hero']['titleAccent'], string> = {
  primary: 'text-primary',
  warm: 'text-warm',
  accent: 'text-accent',
  muted: 'text-fg-muted',
};

const COUNTDOWN_TONE: Record<StageData['hero']['titleAccent'], 'primary' | 'warm' | 'accent' | 'muted'> = {
  primary: 'primary',
  warm: 'warm',
  accent: 'accent',
  muted: 'muted',
};

/**
 * Per-stage specimen — the dithered hero image grows with the ritual.
 *  seed (a botanical motif)        →  variant
 *  DRAFT     'specimen·seed'       →  lattice (latent grid)
 *  OPEN      'specimen·sprout'     →  sprout (active growth)
 *  FROZEN    'specimen·bloom'      →  bloom (peak)
 *  FINAL     'specimen·fruit'      →  nucleus (the named)
 *  ARCHIVED  'specimen·dried'      →  lattice (pressed)
 */
const SPECIMEN_BY_STATE: Record<
  StageData['state'],
  { seed: string; variant: ImageVariant }
> = {
  DRAFT: { seed: 'specimen·seed', variant: 'lattice' },
  OPEN: { seed: 'specimen·sprout', variant: 'sprout' },
  FROZEN: { seed: 'specimen·bloom', variant: 'bloom' },
  FINAL: { seed: 'specimen·fruit', variant: 'nucleus' },
  ARCHIVED: { seed: 'specimen·dried', variant: 'lattice' },
};

export default function HomePage() {
  const [data, setData] = useState<StageData>(getStageData('OPEN'));
  const [announcements, setAnnouncements] = useState<AnnouncementDTO[]>([]);

  useEffect(() => {
    setData(getStageData(parseStageFromUrl(window.location.search)));
    void api.announcements().then(setAnnouncements);
  }, []);

  const { state, hero, phases, proposals, participants, tracks, winners } = data;

  const heroAccent = TITLE_ACCENT_CLASS[hero.titleAccent];

  return (
    <div>
      {/* ━━━━━━━━━━━━━━━━━━━━━━ HERO ━━━━━━━━━━━━━━━━━━━━━━ */}
      <section className="relative overflow-hidden border-b border-rule">
        <div aria-hidden className="absolute inset-0 grid-bg opacity-50" />

        {/* corner botanical, swapped per stage */}
        <pre
          aria-hidden
          className="hidden md:block absolute left-3 bottom-4 text-fg-dim text-[10px] leading-[1.05] select-none pointer-events-none whitespace-pre opacity-70"
        >
          {data.botanical}
        </pre>

        {/* faint stage label, behind the title */}
        <span
          aria-hidden
          className={`absolute right-6 top-12 font-mono text-[clamp(4rem,12vw,12rem)] leading-none ${heroAccent} opacity-[0.04] pointer-events-none select-none uppercase tracking-tighter`}
        >
          {state}
        </span>

        <div className="relative mx-auto w-full max-w-6xl px-6 py-24 lg:py-32 grid gap-10 lg:grid-cols-[1.6fr_1fr] items-center">
        <div>
          <p className="prompt font-mono text-[0.8rem] text-fg-muted tracking-wider mb-6">
            {hero.eyebrowCall}
            <span className="animate-cursor-blink text-primary">▍</span>
          </p>

          <h1 className="font-display italic text-fg leading-[0.95] mb-8 max-w-4xl">
            <span className="block text-[clamp(2.2rem,6.5vw,5.2rem)] text-fg-muted">
              {hero.titleTop}
            </span>
            <span
              className={`block text-[clamp(2.8rem,8.5vw,6.6rem)] ${heroAccent} ${
                hero.flicker ? 'animate-flicker' : ''
              }`}
            >
              {hero.titleBottom}
            </span>
          </h1>

          <div className="space-y-3 font-mono text-[0.85rem] text-fg-muted mb-10">
            <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="text-fg-dim">when</span>
              <span className="text-fg">May 14 – May 16, 2026</span>
              <span className="text-fg-dim">/</span>
              <span className="text-fg-dim">where</span>
              <span className="text-fg">a single container, anywhere</span>
            </p>
            <StatusBadge state={state} />
            {hero.countdown && (
              <LiveCountdown
                label={hero.countdown.label}
                secondsAhead={hero.countdown.secondsAhead}
                tone={COUNTDOWN_TONE[hero.titleAccent]}
              />
            )}
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <Link href={hero.primaryCta.href} className="btn">
              <span aria-hidden>▸</span>
              {hero.primaryCta.label}
            </Link>
            <Link href={hero.secondaryCta.href} className="btn btn-ghost">
              {hero.secondaryCta.label}
            </Link>
          </div>

          <p className="ritual mt-16 max-w-xl text-fg-muted text-[1.05rem] leading-relaxed">
            {hero.epigraph}
          </p>
        </div>

        {/* the specimen — dithered, stage-aware */}
        <aside className="hidden lg:block relative">
          <div className="ascii-frame overflow-hidden">
            <DitheredImage
              seed={SPECIMEN_BY_STATE[state].seed}
              variant={SPECIMEN_BY_STATE[state].variant}
              alt={`${state} specimen`}
              className="aspect-square w-full"
              caption={`specimen · ${state.toLowerCase()}`}
            />
          </div>
          <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mt-3 text-center">
            ◇ &nbsp; the ritual&apos;s specimen at this stage &nbsp; ◇
          </p>
        </aside>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━━━━ DISPATCHES ━━━━━━━━━━━━━━━━━ */}
      {announcements.length > 0 && (
        <section className="border-b border-rule bg-bg-elev/40">
          <div className="mx-auto w-full max-w-6xl px-6 py-10">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-5">
              ▸ dispatches from the keeper
            </p>
            <ul
              className={`grid gap-4 ${
                announcements.length >= 3
                  ? 'md:grid-cols-3'
                  : announcements.length === 2
                    ? 'md:grid-cols-2'
                    : ''
              }`}
            >
              {announcements.slice(0, 3).map((a) => (
                <li key={a.id} className="ascii-frame p-5">
                  <p className="font-mono text-[0.68rem] uppercase tracking-widest text-fg-dim mb-2">
                    {new Date(a.created_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </p>
                  <h2 className="font-display italic text-xl text-fg mb-2">{a.title}</h2>
                  <p className="text-fg-muted text-[0.9rem] leading-relaxed whitespace-pre-line">
                    {a.body}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* ━━━━━━━━━━━━━━━━━━━━━━ STATE STRIP ━━━━━━━━━━━━━━━━ */}
      <section className="border-b border-rule">
        <div className="mx-auto w-full max-w-6xl px-6 py-7 flex flex-wrap items-center gap-x-6 gap-y-3">
          <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
            the five states
          </span>
          <ol className="flex flex-wrap items-center gap-x-3 gap-y-2 font-mono text-[0.78rem] uppercase tracking-wider">
            {STATES.map((s, i) => {
              const isCurrent = s === state;
              const isPast = STATES.indexOf(s) < STATES.indexOf(state);
              return (
                <li key={s} className="inline-flex items-center gap-3">
                  <span
                    className={
                      isCurrent
                        ? 'text-primary'
                        : isPast
                          ? 'text-fg-muted line-through decoration-rule decoration-[0.5px]'
                          : 'text-fg-dim'
                    }
                  >
                    {isCurrent && <span aria-hidden className="mr-1">▸</span>}
                    {s.toLowerCase()}
                  </span>
                  {i < STATES.length - 1 && (
                    <span className="text-fg-dim" aria-hidden>─</span>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━━━━━━━ WINNERS (FINAL & ARCHIVED) ━━━━ */}
      {winners && winners.length > 0 && <WinnerShowcase winners={winners} />}

      {/* ━━━━━━━━━━━━━━━━━━━━━━ PHASES ━━━━━━━━━━━━━━━━━━━━━ */}
      <section className="mx-auto w-full max-w-6xl px-6 py-16">
        <AsciiDivider label="the phases within" />

        <div className="grid gap-5 md:grid-cols-3">
          {phases.map((p) => {
            const live = p.status === 'active';
            const done = p.status === 'completed';
            return (
              <article
                key={p.name}
                className={`ascii-frame p-6 transition-colors ${
                  live ? 'border-primary' : ''
                }`}
              >
                <header className="flex items-center justify-between mb-4">
                  <span
                    className={`font-mono uppercase tracking-widest text-[0.7rem] ${
                      live ? 'text-primary' : done ? 'text-fg-muted' : 'text-fg-dim'
                    }`}
                  >
                    {live ? '▸ live' : p.status}
                  </span>
                  <span
                    className={`text-2xl ${
                      live ? 'text-primary animate-pulse-glow' : done ? 'text-fg-muted' : 'text-fg-dim'
                    }`}
                    aria-hidden
                  >
                    {p.glyph}
                  </span>
                </header>
                <h3
                  className={`font-display italic text-2xl mb-1.5 ${
                    done ? 'text-fg-muted' : 'text-fg'
                  }`}
                >
                  {p.name}
                </h3>
                <p className="font-mono text-[0.75rem] text-fg-muted mb-3 tabular-nums">
                  {p.range}
                </p>
                <p className="ritual text-fg-muted text-[0.98rem]">{p.epigraph}</p>
              </article>
            );
          })}
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━━━━━━━ FORGE STATUS ━━━━━━━━━━━━━━ */}
      <section className="mx-auto w-full max-w-6xl px-6 pb-16">
        <AsciiDivider label="from the forge" glyph="▰" />

        <div className="grid gap-8 lg:grid-cols-2">
          {/* proposals */}
          <div>
            <div className="mb-4 flex items-baseline justify-between gap-4">
              <h2 className="font-display italic text-2xl text-fg">
                {data.proposalsHeading}
              </h2>
              <Link
                href={data.proposalsSeeAll.href}
                className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-muted hover:text-primary"
              >
                {data.proposalsSeeAll.label}
              </Link>
            </div>
            {proposals.length === 0 ? (
              <p className="ritual text-fg-muted text-[1rem] leading-relaxed">
                Nothing has been forged yet. The seeds wait for the appointed hour.
              </p>
            ) : (
              <ol className="font-mono text-[0.85rem]">
                {proposals.map((p) => (
                  <li
                    key={p.id}
                    className="grid grid-cols-[auto_1fr_auto] items-baseline gap-x-4 py-4 border-t border-rule first:border-t-0 group"
                  >
                    <span className="text-fg-dim tabular-nums">
                      {p.rank ? (
                        <span className="text-accent">#{p.rank}</span>
                      ) : (
                        String(p.id).padStart(3, '0')
                      )}
                    </span>
                    <div>
                      <Link
                        href={`/projects/${p.id}/`}
                        className="text-fg group-hover:text-primary transition-colors"
                      >
                        {p.title}
                      </Link>
                      <p className="text-fg-muted text-[0.78rem] mt-1 leading-snug">
                        {p.blurb}
                      </p>
                      <p className="text-fg-dim text-[0.72rem] mt-1 uppercase tracking-wider">
                        by {p.proposer}
                        {p.score && (
                          <span className="text-accent tabular-nums">
                            {' · '}
                            {p.score.toFixed(1)}
                          </span>
                        )}
                      </p>
                    </div>
                    <span className="font-mono text-[0.7rem] uppercase tracking-widest text-warm">
                      [{p.track}]
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </div>

          {/* participants */}
          <div>
            <div className="mb-4 flex items-baseline justify-between gap-4">
              <h2 className="font-display italic text-2xl text-fg">
                {data.participantsHeading}
              </h2>
              <Link
                href="/participants/"
                className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-muted hover:text-primary"
              >
                see all {data.participantCount} →
              </Link>
            </div>
            {participants.length === 0 ? (
              <p className="ritual text-fg-muted text-[1rem]">
                The circle stands empty. It will not be so for long.
              </p>
            ) : (
              <ul className="font-mono text-[0.85rem]">
                {participants.map((p) => (
                  <li
                    key={p.handle}
                    className="grid grid-cols-[1fr_auto_auto] items-baseline gap-x-4 py-3 border-t border-rule first:border-t-0"
                  >
                    <span className="text-fg">{p.handle}</span>
                    <span className="text-fg-dim text-[0.72rem] uppercase tracking-wider">
                      {p.meta}
                    </span>
                    <span
                      className={`text-[0.7rem] uppercase tracking-widest font-mono ${
                        p.kind === 'human'
                          ? 'text-fg-muted'
                          : p.kind === 'agent'
                            ? 'text-accent'
                            : 'text-primary'
                      }`}
                    >
                      [{p.kind}]
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {data.waitlistCount > 0 && (
              <p className="mt-4 font-mono text-[0.72rem] text-fg-dim uppercase tracking-widest">
                waitlist <span className="text-warm">{data.waitlistCount} pending</span>
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━━━━━━━ TRACKS ━━━━━━━━━━━━━━━━━━━━━ */}
      <section className="mx-auto w-full max-w-6xl px-6 pb-20">
        <AsciiDivider label="the tracks" />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tracks.map((t) => (
            <Link
              key={t.name}
              href={`/tracks/${t.name}/`}
              className="ascii-frame p-5 group no-underline transition-colors hover:border-primary"
            >
              <div className="flex items-center justify-between mb-2">
                <span
                  aria-hidden
                  className="text-primary text-2xl group-hover:animate-pulse-glow"
                >
                  {t.glyph}
                </span>
                <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                  {t.count} {t.count === 1 ? 'proposal' : 'proposals'}
                </span>
              </div>
              <h3 className="font-mono text-[0.95rem] text-fg group-hover:text-primary transition-colors">
                {t.name}
              </h3>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
