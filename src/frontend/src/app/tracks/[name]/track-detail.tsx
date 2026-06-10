'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/page-header';
import { DitheredImage } from '../../../components/dithered-image';
import { useStage } from '../../../lib/use-stage';

export function TrackDetail() {
  const params = useParams();
  const data = useStage();
  const name = String(params?.name ?? '');
  const track = data.tracks.find((t) => t.name === name);
  const projects = data.proposals.filter((p) => p.track === name);

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
              <li key={p.id}>
                <Link
                  href={`/projects/${p.id}/`}
                  className="ascii-frame block no-underline group transition-colors hover:border-primary h-full"
                >
                  <DitheredImage
                    seed={p.title}
                    variant={p.imageVariant ?? 'bloom'}
                    alt={p.title}
                    className="aspect-[4/3] w-full"
                    caption={p.title}
                  />
                  <div className="p-4">
                    <header className="flex items-baseline justify-between gap-3 mb-1.5">
                      <span className="font-mono text-[0.72rem] text-fg-dim tabular-nums">
                        {p.rank ? <span className="text-accent">#{p.rank}</span> : `#${String(p.id).padStart(3, '0')}`}
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
          {data.tracks
            .filter((t) => t.name !== name)
            .map((t) => (
              <Link
                key={t.name}
                href={`/tracks/${t.name}/`}
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
