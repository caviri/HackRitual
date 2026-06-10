'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import { DitheredImage } from '../../../components/dithered-image';
import { useStage } from '../../../lib/use-stage';
import {
  api,
  backendPresent,
  type ParticipantDTO,
  type ProjectDTO,
  type TrackDTO,
} from '../../../lib/api';

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

interface Row {
  key: string;
  href: string;
  idLabel: string;
  title: string;
  blurb: string;
  proposer: string;
  rank?: number;
  score?: number;
  imageSeed: string;
  imageVariant?: 'sprout' | 'lattice' | 'nucleus' | 'bloom';
  imageSrc?: string;
}

export function TrackDetail() {
  const params = useParams();
  const data = useStage();
  const name = String(params?.name ?? '');
  const [live, setLive] = useState<boolean | null>(null);
  const [real, setReal] = useState<{
    tracks: TrackDTO[];
    projects: ProjectDTO[];
    participants: ParticipantDTO[];
  }>({ tracks: [], projects: [], participants: [] });

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) {
        const [tracks, projects, participants] = await Promise.all([
          api.tracks(),
          api.projects(),
          api.participants(),
        ]);
        setReal({ tracks, projects, participants });
      }
      setLive(ok);
    });
  }, []);

  // Probe in flight — brief blank rather than a mock (or not-found) flash.
  if (live === null) return null;

  const useLive = live === true;

  const liveTrack = useLive
    ? real.tracks.find((t) => t.name === name || slugify(t.name) === name)
    : undefined;
  const mockTrack = useLive
    ? undefined
    : data.tracks.find((t) => t.name === name);

  const track = useLive
    ? liveTrack && { name: liveTrack.name, blurb: liveTrack.description ?? '' }
    : mockTrack && { name: mockTrack.name, blurb: mockTrack.blurb };

  if (!track) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
          ritual.track({JSON.stringify(name)})
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">Unknown track.</h1>
        <p className="ritual text-fg-muted mb-6">
          No track by that name is inscribed in this ritual.
        </p>
        <Link href="/projects/" className="btn">
          ← all projects
        </Link>
      </section>
    );
  }

  const projects: Row[] = useLive
    ? real.projects
        .filter((p) => p.track_id === liveTrack?.id)
        .map((p) => ({
          key: p.id,
          href: `/project/?id=${p.id}`,
          idLabel: `#${p.id.slice(0, 6)}`,
          title: p.title,
          blurb: (p.description ?? '').split('\n')[0].slice(0, 160),
          proposer:
            real.participants.find(
              (pa) => pa.id === p.proposed_by_participant_id,
            )?.display_name ?? '?',
          imageSeed: p.title,
          imageSrc: p.image ?? undefined,
        }))
    : data.proposals
        .filter((p) => p.track === name)
        .map((p) => ({
          key: String(p.id),
          href: `/projects/${p.id}/`,
          idLabel: `#${String(p.id).padStart(3, '0')}`,
          title: p.title,
          blurb: p.blurb,
          proposer: p.proposer,
          rank: p.rank,
          score: p.score,
          imageSeed: p.title,
          imageVariant: p.imageVariant,
        }));

  const otherTracks: { name: string; href: string }[] = useLive
    ? real.tracks
        .filter((t) => t.id !== liveTrack?.id)
        .map((t) => ({ name: t.name, href: `/tracks/${slugify(t.name)}/` }))
    : data.tracks
        .filter((t) => t.name !== name)
        .map((t) => ({ name: t.name, href: `/tracks/${t.name}/` }));

  return (
    <>
      <PageHeader
        prompt={`ritual.track('${track.name}')`}
        title={track.name}
        subtitle={track.blurb}
        chip={`${projects.length} ${projects.length === 1 ? 'project' : 'projects'}`}
        back="/"
        backLabel="back to circle"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-10">
        {projects.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ track.projects() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto mb-6">
              Nothing has been proposed in this track yet. Be the first.
            </p>
            <Link href="/projects/new/" className="btn">
              propose a project →
            </Link>
          </div>
        ) : (
          <ol className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <li key={p.key}>
                <Link
                  href={p.href}
                  className="ascii-frame block no-underline group transition-colors hover:border-primary h-full"
                >
                  <DitheredImage
                    seed={p.imageSeed}
                    src={p.imageSrc}
                    variant={p.imageVariant ?? 'bloom'}
                    alt={p.title}
                    className="aspect-[4/3] w-full"
                    caption={p.title}
                  />
                  <div className="p-4">
                    <header className="flex items-baseline justify-between gap-3 mb-1.5">
                      <span className="font-mono text-[0.72rem] text-fg-dim tabular-nums">
                        {p.rank ? <span className="text-accent">#{p.rank}</span> : p.idLabel}
                      </span>
                      {p.score && (
                        <span className="font-mono text-[0.7rem] text-accent tabular-nums">
                          {p.score.toFixed(1)}
                        </span>
                      )}
                    </header>
                    <h2 className="font-display italic text-xl text-fg group-hover:text-primary transition-colors mb-1.5 leading-tight">
                      {p.title}
                    </h2>
                    <p className="text-fg-muted text-[0.82rem] leading-snug mb-3 line-clamp-3">
                      {p.blurb}
                    </p>
                    <footer className="font-mono text-[0.68rem] text-fg-dim uppercase tracking-wider pt-2 border-t border-rule">
                      by <span className="text-fg-muted">{p.proposer}</span>
                    </footer>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        )}

        <nav className="mt-12 pt-6 border-t border-rule flex flex-wrap gap-3 font-mono text-[0.72rem] uppercase tracking-widest text-fg-muted">
          <span className="text-fg-dim">other tracks:</span>
          {otherTracks.map((t) => (
            <Link
              key={t.name}
              href={t.href}
              className="text-primary hover:underline"
            >
              ▸ {t.name}
            </Link>
          ))}
        </nav>
      </section>
    </>
  );
}
