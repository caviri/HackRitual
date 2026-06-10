'use client';

import { PageHeader } from '../../../components/page-header';
import { useStage } from '../../../lib/use-stage';

export default function AdminTracksPage() {
  const data = useStage();
  return (
    <>
      <PageHeader
        prompt="ritual.admin.tracks()"
        title="Tracks"
        subtitle="The thematic groupings inside the event. Each project lives in at most one."
        chip={`${data.tracks.length} inscribed`}
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-4">
        {data.tracks.map((t) => (
          <article
            key={t.name}
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
        ))}
        <button type="button" className="btn">
          ◆ inscribe a new track
        </button>
      </section>
    </>
  );
}
