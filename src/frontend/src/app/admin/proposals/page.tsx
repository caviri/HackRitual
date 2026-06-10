'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '../../../components/page-header';
import { DitheredImage } from '../../../components/dithered-image';
import { api, ApiError, type ProjectDTO } from '../../../lib/api';

type Filter = 'proposed' | 'approved' | 'rejected' | 'all';

const STATUS_TONE: Record<string, string> = {
  proposed: 'text-warm',
  approved: 'text-primary',
  rejected: 'text-danger',
};

const STATUS_GLYPH: Record<string, string> = {
  proposed: '▒',
  approved: '◆',
  rejected: '✕',
};

export default function ProposalsPage() {
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [filter, setFilter] = useState<Filter>('proposed');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.projects().then(setProjects);
  }, []);

  async function setStatus(p: ProjectDTO, status: 'approved' | 'rejected' | 'proposed') {
    setBusyId(p.id);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${p.id}/status`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new ApiError(res.status, await res.text());
      const updated = (await res.json()) as ProjectDTO;
      setProjects((prev) =>
        prev.map((x) => (x.id === updated.id ? updated : x)),
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.body || `update failed (${err.status})`);
      } else {
        setError(String(err));
      }
    } finally {
      setBusyId(null);
    }
  }

  const filtered =
    filter === 'all' ? projects : projects.filter((p) => p.status === filter);

  const counts = {
    proposed: projects.filter((p) => p.status === 'proposed').length,
    approved: projects.filter((p) => p.status === 'approved').length,
    rejected: projects.filter((p) => p.status === 'rejected').length,
    all: projects.length,
  };

  return (
    <>
      <PageHeader
        prompt="ritual.admin.proposals()"
        title="Project proposals"
        subtitle="Approve what should run. Reject what shouldn't. The author is notified either way."
        chip={`${counts.proposed} awaiting`}
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-8">
        {/* filter chips */}
        <div className="flex flex-wrap gap-2 mb-8 font-mono text-[0.72rem] uppercase tracking-widest">
          {(['proposed', 'approved', 'rejected', 'all'] as Filter[]).map((f) => {
            const active = f === filter;
            return (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`border px-3 py-1.5 transition-colors ${
                  active
                    ? 'border-primary text-primary'
                    : 'border-rule text-fg-muted hover:text-fg'
                }`}
              >
                {f === 'proposed' && <span className="text-warm mr-1.5">▒</span>}
                {f === 'approved' && <span className="text-primary mr-1.5">◆</span>}
                {f === 'rejected' && <span className="text-danger mr-1.5">✕</span>}
                {f === 'all' && <span className="text-fg-muted mr-1.5">◇</span>}
                {f}
                <span className="text-fg-dim ml-2">{counts[f]}</span>
              </button>
            );
          })}
        </div>

        {error && (
          <p className="ascii-frame !border-danger px-3 py-2 mb-6 font-mono text-[0.78rem] text-danger">
            ✕ {error}
          </p>
        )}

        {filtered.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ proposals.list({JSON.stringify(filter)}) → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem]">
              {filter === 'proposed'
                ? 'no proposals waiting for the keeper. quiet.'
                : `no projects in ${filter}.`}
            </p>
          </div>
        ) : (
          <ul className="space-y-4">
            {filtered.map((p) => (
              <li
                key={p.id}
                className="ascii-frame overflow-hidden grid md:grid-cols-[180px_1fr_auto]"
              >
                <DitheredImage
                  seed={p.title}
                  variant="bloom"
                  alt={p.title}
                  className="aspect-[4/3] md:aspect-square w-full"
                />
                <div className="p-4 min-w-0">
                  <header className="flex items-baseline justify-between gap-3 mb-1.5">
                    <h2 className="font-display italic text-xl text-fg truncate">
                      {p.title}
                    </h2>
                    <span
                      className={`font-mono text-[0.7rem] uppercase tracking-widest ${STATUS_TONE[p.status]}`}
                    >
                      {STATUS_GLYPH[p.status]} {p.status}
                    </span>
                  </header>
                  <p className="font-mono text-[0.72rem] uppercase tracking-wider text-fg-dim mb-2">
                    track: <span className="text-warm">{p.track_id ?? '—'}</span>{' '}
                    · by <span className="text-fg-muted">{p.proposed_by_participant_id.slice(0, 8)}…</span>
                  </p>
                  <p className="text-fg-muted text-[0.88rem] leading-relaxed line-clamp-3 mb-3">
                    {p.description}
                  </p>
                  <Link
                    href={`/project/?id=${p.id}`}
                    className="font-mono text-[0.72rem] uppercase tracking-widest text-primary hover:underline"
                  >
                    open detail →
                  </Link>
                </div>
                <div className="border-t md:border-t-0 md:border-l border-rule p-4 flex md:flex-col gap-2 items-stretch justify-center">
                  {p.status === 'proposed' ? (
                    <>
                      <button
                        type="button"
                        disabled={busyId === p.id}
                        onClick={() => setStatus(p, 'approved')}
                        className="btn flex-1 justify-center"
                      >
                        ◆ approve
                      </button>
                      <button
                        type="button"
                        disabled={busyId === p.id}
                        onClick={() => setStatus(p, 'rejected')}
                        className="btn btn-ghost flex-1 justify-center !border-danger !text-danger"
                      >
                        ✕ reject
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      disabled={busyId === p.id}
                      onClick={() => setStatus(p, 'proposed')}
                      className="btn btn-ghost flex-1 justify-center"
                    >
                      ↺ reopen
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
