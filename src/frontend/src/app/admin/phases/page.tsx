'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import { useStage } from '../../../lib/use-stage';
import { api, backendPresent, type PhaseDTO } from '../../../lib/api';

interface Row {
  key: string;
  name: string;
  range: string;
  epigraph: string;
  status: 'completed' | 'active' | 'upcoming';
}

function phaseStatus(p: PhaseDTO, now: Date): Row['status'] {
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

export default function AdminPhasesPage() {
  const data = useStage();
  const [live, setLive] = useState<boolean | null>(null);
  const [livePhases, setLivePhases] = useState<Row[]>([]);

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) {
        const phases = await api.phases();
        const now = new Date();
        setLivePhases(
          phases.map((p) => ({
            key: p.id,
            name: p.name,
            range: formatRange(p),
            epigraph: p.description ?? '',
            status: phaseStatus(p, now),
          })),
        );
      }
      setLive(ok);
    });
  }, []);

  // live !== false → API data (even when empty); mocks only when backend absent
  const rows: Row[] =
    live !== false
      ? livePhases
      : data.phases.map((p) => ({
          key: p.name,
          name: p.name,
          range: p.range,
          epigraph: p.epigraph,
          status: p.status,
        }));

  return (
    <>
      <PageHeader
        prompt="ritual.admin.phases()"
        title="Phases"
        subtitle="The sub-phases inside OPEN. Their starts and ends, and the page each one links to."
        chip={`${rows.length} scheduled`}
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-4">
        {rows.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ phases.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No phases have been inscribed yet.
            </p>
          </div>
        ) : (
          rows.map((p) => (
            <article
              key={p.key}
              className="ascii-frame p-5 grid gap-3 md:grid-cols-[1fr_auto]"
            >
              <div>
                <header className="flex items-baseline gap-3 mb-1">
                  <h2 className="font-display italic text-2xl text-fg">{p.name}</h2>
                  <span
                    className={`font-mono text-[0.7rem] uppercase tracking-widest ${
                      p.status === 'active'
                        ? 'text-primary'
                        : p.status === 'completed'
                        ? 'text-fg-muted'
                        : 'text-fg-dim'
                    }`}
                  >
                    ▸ {p.status}
                  </span>
                </header>
                <p className="font-mono text-[0.78rem] text-fg-muted tabular-nums mb-2">
                  {p.range}
                </p>
                <p className="ritual text-fg-muted">{p.epigraph}</p>
              </div>
              <div className="flex md:flex-col gap-2 items-start md:items-end">
                <button type="button" className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem]">
                  edit times
                </button>
                <button type="button" className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem]">
                  attach page
                </button>
              </div>
            </article>
          ))
        )}
        <button type="button" className="btn">
          ◆ inscribe a new phase
        </button>
      </section>
    </>
  );
}
