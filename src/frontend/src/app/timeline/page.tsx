'use client';

import { PageHeader } from '../../components/page-header';
import { useStage } from '../../lib/use-stage';

const STATUS_COLOR: Record<string, string> = {
  completed: 'text-fg-muted',
  active: 'text-primary',
  upcoming: 'text-fg-dim',
};

const STATUS_LABEL: Record<string, string> = {
  completed: 'done',
  active: 'live',
  upcoming: 'soon',
};

export default function TimelinePage() {
  const data = useStage();

  const subtitle = {
    DRAFT: 'The phases, scheduled but not yet under way.',
    OPEN: 'Where we are inside the ritual. The breathing line below marks the hour.',
    FROZEN: 'Ideation is past. The forge has cooled. Judging is under way.',
    FINAL: 'All phases complete. The verdict is in.',
    ARCHIVED: 'The phases, frozen as record.',
  }[data.state];

  return (
    <>
      <PageHeader
        prompt="ritual.timeline()"
        title="Timeline"
        subtitle={subtitle}
        chip={data.phases.find((p) => p.status === 'active')?.name ?? 'idle'}
      />

      <section className="mx-auto w-full max-w-5xl px-6 py-16">
        {/* the breathing line */}
        <div className="mb-12">
          <div className="relative h-1 bg-rule">
            {data.phases.map((p, i) => {
              const pos = (i / (data.phases.length - 1)) * 100;
              return (
                <span
                  key={p.name}
                  className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 ${
                    p.status === 'active' ? 'text-primary animate-pulse-glow' : STATUS_COLOR[p.status]
                  }`}
                  style={{ left: `${pos}%` }}
                  aria-hidden
                >
                  {p.status === 'active' ? '●' : '◆'}
                </span>
              );
            })}
          </div>
        </div>

        {/* phase cards as vertical timeline */}
        <ol className="space-y-6">
          {data.phases.map((p, i) => {
            const live = p.status === 'active';
            return (
              <li key={p.name} className="grid grid-cols-[auto_1fr] gap-6">
                <div className="flex flex-col items-center">
                  <span
                    className={`text-2xl ${
                      live ? 'text-primary animate-pulse-glow' : STATUS_COLOR[p.status]
                    }`}
                    aria-hidden
                  >
                    {p.glyph}
                  </span>
                  {i < data.phases.length - 1 && (
                    <span
                      aria-hidden
                      className="w-px flex-1 bg-rule mt-3 mb-1"
                      style={{ minHeight: '4rem' }}
                    />
                  )}
                </div>
                <article
                  className={`ascii-frame p-5 mb-2 ${
                    live ? 'border-primary' : ''
                  }`}
                >
                  <header className="flex items-baseline justify-between gap-3 mb-2">
                    <h2
                      className={`font-display italic text-2xl ${
                        live ? 'text-fg' : 'text-fg-muted'
                      }`}
                    >
                      {p.name}
                    </h2>
                    <span
                      className={`font-mono text-[0.7rem] uppercase tracking-widest ${
                        STATUS_COLOR[p.status]
                      }`}
                    >
                      ▸ {STATUS_LABEL[p.status]}
                    </span>
                  </header>
                  <p className="font-mono text-[0.78rem] text-fg-muted tabular-nums mb-3">
                    {p.range}
                  </p>
                  <p className="ritual text-fg-muted text-[1.02rem]">{p.epigraph}</p>
                </article>
              </li>
            );
          })}
        </ol>
      </section>
    </>
  );
}
