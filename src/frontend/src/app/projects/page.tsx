'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import { useStage } from '../../lib/use-stage';
import {
  api,
  backendPresent,
  type ParticipantDTO,
  type ProjectDTO,
  type TrackDTO,
} from '../../lib/api';

/** Display shape used by the render — built from either real backend rows or mocks. */
interface ProjectRow {
  key: string;
  idLabel: string;
  title: string;
  blurb: string;
  track: string;
  proposer: string;
  href: string;
  rank?: number;
  score?: number;
  status?: string;
  versions?: number;
  imageSeed: string;
  imageSrc?: string;
}

export default function ProjectsPage() {
  const data = useStage();
  const [track, setTrack] = useState<string | null>(null);
  const [live, setLive] = useState<boolean | null>(null);
  const [real, setReal] = useState<{
    projects: ProjectDTO[];
    tracks: TrackDTO[];
    participants: ParticipantDTO[];
  }>({ projects: [], tracks: [], participants: [] });

  useEffect(() => {
    const url = new URL(window.location.href);
    setTrack(url.searchParams.get('track'));
    void backendPresent().then(async (ok) => {
      if (ok) {
        const [projects, tracks, participants] = await Promise.all([
          api.projects(),
          api.tracks(),
          api.participants(),
        ]);
        setReal({ projects, tracks, participants });
      }
      setLive(ok);
    });
  }, []);

  // live !== false → API data (even when empty); mocks only when backend absent
  const useLive = live !== false;

  // ── Filter chips: live tracks (counts from live projects) or stage's mocks
  const filterChips = useLive
    ? real.tracks.map((t) => ({
        name: t.name,
        glyph: '◆',
        count: real.projects.filter((p) => p.track_id === t.id).length,
      }))
    : data.tracks.map((t) => ({
        name: t.name,
        glyph: t.glyph,
        count: t.count,
      }));

  // ── Build display rows
  const rows: ProjectRow[] = useLive
    ? real.projects
        .map((p) => ({
          key: p.id,
          idLabel: `#${p.id.slice(0, 6)}`,
          title: p.title,
          blurb: (p.description ?? '').split('\n')[0].slice(0, 160),
          track:
            real.tracks.find((t) => t.id === p.track_id)?.name ?? '—',
          proposer:
            real.participants.find(
              (pa) => pa.id === p.proposed_by_participant_id,
            )?.display_name ?? '?',
          href: `/project/?id=${p.id}`,
          status: p.status,
          imageSeed: p.title,
          imageSrc: p.image ?? undefined,
        }))
    : data.proposals.map((p) => ({
        key: String(p.id),
        idLabel: `#${String(p.id).padStart(3, '0')}`,
        title: p.title,
        blurb: p.blurb,
        track: p.track,
        proposer: p.proposer,
        href: `/projects/${p.id}/`,
        rank: p.rank,
        score: p.score,
        versions: p.versions,
        imageSeed: p.title,
      }));

  const filtered = track ? rows.filter((r) => r.track === track) : rows;

  const stageSubtitle = {
    DRAFT: 'No projects yet. The tracks are inscribed; the proposals will follow.',
    OPEN: 'Projects proposed during the forge. Filter by track. Each row is a thing being built.',
    FROZEN: 'Submissions are sealed. Each project shown is awaiting the verdict.',
    FINAL: 'Ranked by score. The named are named.',
    ARCHIVED: 'The record of what was made. Read-only.',
  }[data.state];

  return (
    <>
      <PageHeader
        prompt={`ritual.projects(${track ? `track='${track}'` : ''})`}
        title="Projects"
        subtitle={stageSubtitle}
        chip={
          live === true
            ? `${filtered.length} of ${rows.length} · live`
            : `${filtered.length} of ${rows.length}`
        }
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="flex flex-wrap items-center gap-2 mb-10 font-mono text-[0.72rem] uppercase tracking-widest">
          <button
            type="button"
            onClick={() => {
              const u = new URL(window.location.href);
              u.searchParams.delete('track');
              window.location.href = u.toString();
            }}
            className={`border px-3 py-1.5 transition-colors ${
              !track
                ? 'border-primary text-primary'
                : 'border-rule text-fg-muted hover:text-fg'
            }`}
          >
            <span aria-hidden className="mr-1.5">◆</span>
            all {rows.length}
          </button>
          {filterChips.map((t) => (
            <button
              key={t.name}
              type="button"
              onClick={() => {
                const u = new URL(window.location.href);
                u.searchParams.set('track', t.name);
                window.location.href = u.toString();
              }}
              className={`border px-3 py-1.5 transition-colors ${
                track === t.name
                  ? 'border-primary text-primary'
                  : 'border-rule text-fg-muted hover:text-fg'
              }`}
            >
              <span aria-hidden className="mr-1.5 text-warm">{t.glyph}</span>
              {t.name}
              <span className="text-fg-dim ml-2">{t.count}</span>
            </button>
          ))}
          <span className="flex-1" />
          <Link href="/projects/new/" className="btn !py-1.5 !px-3 !text-[0.7rem]">
            ◆ propose
          </Link>
        </div>

        {filtered.length === 0 ? (
          <EmptyProjects state={data.state} />
        ) : (
          <ol className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((p) => (
              <li key={p.key}>
                <Link
                  href={p.href}
                  className="ascii-frame block no-underline group transition-colors hover:border-primary h-full"
                >
                  <DitheredImage
                    seed={p.imageSeed}
                    src={p.imageSrc}
                    variant="bloom"
                    alt={p.title}
                    className="aspect-[4/3] w-full"
                    caption={`${p.title} · ${p.track}`}
                  />
                  <div className="p-4">
                    <header className="flex items-baseline justify-between gap-3 mb-1.5">
                      <span className="font-mono text-[0.72rem] text-fg-dim tabular-nums">
                        {p.rank ? (
                          <span className="text-accent">#{p.rank}</span>
                        ) : (
                          p.idLabel
                        )}
                      </span>
                      <span className="font-mono text-[0.66rem] uppercase tracking-widest text-warm">
                        [{p.track}]
                      </span>
                    </header>
                    <h2 className="font-display italic text-xl text-fg group-hover:text-primary transition-colors mb-1.5 leading-tight">
                      {p.title}
                    </h2>
                    <p className="text-fg-muted text-[0.82rem] leading-snug mb-3 line-clamp-3">
                      {p.blurb}
                    </p>
                    <footer className="flex items-center justify-between font-mono text-[0.68rem] text-fg-dim uppercase tracking-wider pt-2 border-t border-rule">
                      <span className="truncate">
                        by <span className="text-fg-muted">{p.proposer}</span>
                      </span>
                      <span className="flex items-center gap-2 shrink-0">
                        {p.status && (
                          <span
                            className={
                              p.status === 'approved'
                                ? 'text-primary'
                                : p.status === 'rejected'
                                  ? 'text-danger'
                                  : 'text-warm'
                            }
                          >
                            {p.status}
                          </span>
                        )}
                        {p.versions && <span>v{p.versions}</span>}
                        {p.score && (
                          <span className="text-accent tabular-nums">
                            {p.score.toFixed(1)}
                          </span>
                        )}
                      </span>
                    </footer>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}

function EmptyProjects({ state }: { state: string }) {
  return (
    <div className="ascii-frame p-10 text-center">
      <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-4">
        $ projects.list() → []
      </p>
      <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
        {state === 'DRAFT'
          ? 'Nothing has been forged yet. The seeds wait for the appointed hour.'
          : 'No projects match this filter. Try another track.'}
      </p>
    </div>
  );
}
