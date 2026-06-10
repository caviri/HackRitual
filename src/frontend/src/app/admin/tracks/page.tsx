'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import { useStage } from '../../../lib/use-stage';
import {
  api,
  backendPresent,
  type ProjectDTO,
  type TrackDTO,
} from '../../../lib/api';

interface Row {
  key: string;
  name: string;
  glyph: string;
  blurb: string;
  count: number;
}

export default function AdminTracksPage() {
  const data = useStage();
  const [live, setLive] = useState<boolean | null>(null);
  const [real, setReal] = useState<{
    tracks: TrackDTO[];
    projects: ProjectDTO[];
  }>({ tracks: [], projects: [] });

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) {
        const [tracks, projects] = await Promise.all([
          api.tracks(),
          api.projects(),
        ]);
        setReal({ tracks, projects });
      }
      setLive(ok);
    });
  }, []);

  // live !== false → API data (even when empty); mocks only when backend absent
  const rows: Row[] =
    live !== false
      ? real.tracks.map((t) => ({
          key: t.id,
          name: t.name,
          glyph: '◆',
          blurb: t.description ?? '',
          count: real.projects.filter((p) => p.track_id === t.id).length,
        }))
      : data.tracks.map((t) => ({
          key: t.name,
          name: t.name,
          glyph: t.glyph,
          blurb: t.blurb,
          count: t.count,
        }));

  return (
    <>
      <PageHeader
        prompt="ritual.admin.tracks()"
        title="Tracks"
        subtitle="The thematic groupings inside the event. Each project lives in at most one."
        chip={`${rows.length} inscribed`}
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-4">
        {rows.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ tracks.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No tracks have been inscribed yet.
            </p>
          </div>
        ) : (
          rows.map((t) => (
            <article
              key={t.key}
              className="ascii-frame p-5 flex flex-wrap items-baseline justify-between gap-4"
            >
              <div className="min-w-0">
                <h2 className="font-display italic text-2xl text-fg mb-1">
                  <span aria-hidden className="text-primary mr-2">{t.glyph}</span>
                  {t.name}
                </h2>
                <p className="text-fg-muted text-[0.92rem] max-w-2xl">{t.blurb}</p>
              </div>
              <div className="flex items-center gap-3 font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                <span>{t.count} projects</span>
                <button type="button" className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem]">
                  edit
                </button>
              </div>
            </article>
          ))
        )}
        <button type="button" className="btn">
          ◆ inscribe a new track
        </button>
      </section>
    </>
  );
}
