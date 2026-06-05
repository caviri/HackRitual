'use client';

import { PageHeader } from '../../../components/page-header';
import { useStage } from '../../../lib/use-stage';

export default function AdminPhasesPage() {
  const data = useStage();
  return (
    <>
      <PageHeader
        prompt="ritual.admin.phases()"
        title="Phases"
        subtitle="The sub-phases inside OPEN. Their starts and ends, and the page each one links to."
        chip={`${data.phases.length} scheduled`}
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-4">
        {data.phases.map((p) => (
          <article
            key={p.name}
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
        ))}
        <button type="button" className="btn">
          ◆ inscribe a new phase
        </button>
      </section>
    </>
  );
}
