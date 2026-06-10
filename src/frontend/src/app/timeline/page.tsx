'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { useStage } from '../../lib/use-stage';
import { api, backendPresent, type PhaseDTO } from '../../lib/api';

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

interface PhaseRow {
  name: string;
  glyph: string;
  range: string;
  epigraph: string;
  status: 'completed' | 'active' | 'upcoming';
}

const PHASE_GLYPHS = ['◇', '◆', '▢'];

function phaseStatus(p: PhaseDTO, now: Date): PhaseRow['status'] {
  const start = p.starts_at ? new Date(p.starts_at) : null;
  const end = p.ends_at ? new Date(p.ends_at) : null;
  if (end && now > end) return 'completed';
  if (start && now >= start) return 'active';
  return 'upcoming';
}

function formatRange(p: PhaseDTO): string {
  const start = p.starts_at ? new Date(p.starts_at) : null;
  const end = p.ends_at ? new Date(p.ends_at) : null;
  const day = (d: Date) =>
    d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  const time = (d: Date) =>
    d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
  if (start && end) {
    return start.toDateString() === end.toDateString()
      ? `${day(start)} · ${time(start)} – ${time(end)}`
      : `${day(start)} ${time(start)} – ${day(end)} ${time(end)}`;
  }
  if (start) return `from ${day(start)} ${time(start)}`;
  if (end) return `until ${day(end)} ${time(end)}`;
  return 'unscheduled';
}

function toRow(p: PhaseDTO, i: number, now: Date): PhaseRow {
  return {
    name: p.name,
    glyph: PHASE_GLYPHS[i % PHASE_GLYPHS.length],
    range: formatRange(p),
    epigraph: p.description ?? '',
    status: phaseStatus(p, now),
  };
}

export default function TimelinePage() {
  const data = useStage();
  const [live, setLive] = useState<boolean | null>(null);
  const [livePhases, setLivePhases] = useState<PhaseRow[]>([]);

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) {
        const phases = await api.phases();
        const now = new Date();
        setLivePhases(phases.map((p, i) => toRow(p, i, now)));
      }
      setLive(ok);
    });
  }, []);

  // live !== false → API phases (even when empty); mocks only when backend absent
  const phases: PhaseRow[] = live !== false ? livePhases : data.phases;

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
        chip={phases.find((p) => p.status === 'active')?.name ?? 'idle'}
      />

      <section className="mx-auto w-full max-w-5xl px-6 py-16">
        {phases.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ phases.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No phases have been inscribed yet. The schedule arrives before the ritual does.
            </p>
          </div>
        ) : (
          <>
            {/* the breathing line */}
            <div className="mb-12">
              <div className="relative h-1 bg-rule">
                {phases.map((p, i) => {
                  const pos =
                    phases.length > 1 ? (i / (phases.length - 1)) * 100 : 50;
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
              {phases.map((p, i) => {
                const isActive = p.status === 'active';
                return (
                  <li key={p.name} className="grid grid-cols-[auto_1fr] gap-6">
                    <div className="flex flex-col items-center">
                      <span
                        className={`text-2xl ${
                          isActive ? 'text-primary animate-pulse-glow' : STATUS_COLOR[p.status]
                        }`}
                        aria-hidden
                      >
                        {p.glyph}
                      </span>
                      {i < phases.length - 1 && (
                        <span
                          aria-hidden
                          className="w-px flex-1 bg-rule mt-3 mb-1"
                          style={{ minHeight: '4rem' }}
                        />
                      )}
                    </div>
                    <article
                      className={`ascii-frame p-5 mb-2 ${
                        isActive ? 'border-primary' : ''
                      }`}
                    >
                      <header className="flex items-baseline justify-between gap-3 mb-2">
                        <h2
                          className={`font-display italic text-2xl ${
                            isActive ? 'text-fg' : 'text-fg-muted'
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
          </>
        )}
      </section>
    </>
  );
}
