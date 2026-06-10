'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import { RepositoriesPanel } from '../../components/repositories-panel';
import { api, type ProjectDTO, type ScoreDTO, type SubmissionDTO } from '../../lib/api';

/**
 * Real-data project detail. Uses ?id=<uuid> instead of /[id]/ because
 * static-export dynamic routes can only pre-render concrete params at build
 * time, and real seeded UUIDs are not knowable then. The /projects/[id]/ route
 * still exists for the demo mock IDs (1, 2, 3, 7).
 */

const STATUS_TONE: Record<string, string> = {
  draft: 'text-fg-muted',
  final: 'text-primary',
  withdrawn: 'text-fg-dim line-through',
};

const STATUS_GLYPH: Record<string, string> = {
  draft: '▒',
  final: '◆',
  withdrawn: '✕',
};

export default function ProjectByQueryPage() {
  const [id, setId] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectDTO | null | undefined>(undefined);
  const [subs, setSubs] = useState<SubmissionDTO[]>([]);
  const [scoresBySub, setScoresBySub] = useState<Record<string, ScoreDTO[]>>({});

  useEffect(() => {
    const url = new URL(window.location.href);
    const queryId = url.searchParams.get('id');
    setId(queryId);
    if (!queryId) {
      setProject(null);
      return;
    }
    void api.project(queryId).then(setProject);
    void api.submissions(queryId).then(async (s) => {
      setSubs(s);
      // Fetch scores for final submissions so the verdict shows publicly.
      const finals = s.filter((sub) => sub.status === 'final');
      if (finals.length === 0) return;
      const results = await Promise.all(
        finals.map(async (sub) => [sub.id, await api.listScores(sub.id)] as const),
      );
      setScoresBySub(Object.fromEntries(results));
    });
  }, []);

  if (project === undefined) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="font-mono text-fg-dim">summoning…</p>
      </section>
    );
  }

  if (project === null) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
          ritual.project({id ? JSON.stringify(id) : 'undefined'})
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">Not in the circle.</h1>
        <p className="ritual text-fg-muted mb-6">
          No project with that id is registered against the running event.
        </p>
        <Link href="/admin/proposals/" className="btn">
          ← back to proposals
        </Link>
      </section>
    );
  }

  return (
    <>
      <PageHeader
        prompt={`ritual.project('${project.title}')`}
        title={project.title}
        subtitle={(project.description ?? '').split('\n')[0].slice(0, 200)}
        chip={`${subs.length} submission${subs.length === 1 ? '' : 's'}`}
        back="/admin/proposals/"
        backLabel="proposals"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-8">
          <DitheredImage
            seed={project.title}
            variant="bloom"
            alt={project.title}
            className="aspect-[16/9] w-full"
            caption={`${project.title} · ${project.status}`}
          />

          {/* Verdict — surface scores from any final submission */}
          {(() => {
            const finalScores: ScoreDTO[] = subs
              .filter((s) => s.status === 'final')
              .flatMap((s) => scoresBySub[s.id] ?? []);
            if (finalScores.length === 0) return null;
            // Take the latest score; the breakdown is its breakdown.
            const top = finalScores[0];
            const criteria = Object.entries(top.breakdown);
            return (
              <article className="ascii-frame !border-accent p-6">
                <div className="flex items-baseline justify-between gap-3 mb-4">
                  <p className="font-mono text-[0.7rem] uppercase tracking-widest text-accent">
                    ✺ the verdict
                  </p>
                  <span className="font-display italic text-4xl text-accent tabular-nums leading-none">
                    {top.score_value.toFixed(1)}
                  </span>
                </div>
                {criteria.length > 0 && (
                  <ul className="grid sm:grid-cols-2 gap-3 mb-3">
                    {criteria.map(([k, v]) => (
                      <li key={k}>
                        <div className="flex items-baseline justify-between gap-2 mb-1">
                          <span className="font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim">
                            {k}
                          </span>
                          <span className="font-mono text-[0.85rem] text-accent tabular-nums">
                            {v.toFixed(1)}
                          </span>
                        </div>
                        <div className="h-1 bg-rule overflow-hidden">
                          <div
                            className="h-full bg-accent"
                            style={{ width: `${v}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
                {top.notes && (
                  <p className="ritual text-fg-muted text-[0.95rem] border-l-2 border-accent pl-3 mt-3">
                    {top.notes}
                  </p>
                )}
                <p className="font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim mt-3">
                  scored by {top.scorer_version ?? '—'}
                </p>
              </article>
            );
          })()}

          <article className="ascii-frame p-6">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              about this project
            </p>
            <p className="text-fg-muted leading-relaxed text-[1rem] whitespace-pre-wrap">
              {project.description}
            </p>
          </article>

          <RepositoriesPanel projectId={project.id} />
        </div>

        <aside className="space-y-6">
          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              meta
            </p>
            <ul className="font-mono text-[0.78rem] space-y-2">
              <li>
                <span className="text-fg-dim">id        </span>
                <span className="text-fg break-all">{project.id.slice(0, 8)}…</span>
              </li>
              <li>
                <span className="text-fg-dim">status    </span>
                <span className={
                  project.status === 'approved' ? 'text-primary'
                  : project.status === 'rejected' ? 'text-danger'
                  : 'text-warm'
                }>
                  {project.status}
                </span>
              </li>
              <li>
                <span className="text-fg-dim">track     </span>
                <span className="text-warm">{project.track_id?.slice(0, 8) ?? '—'}</span>
              </li>
              <li>
                <span className="text-fg-dim">proposer  </span>
                <span className="text-fg">{project.proposed_by_participant_id.slice(0, 8)}…</span>
              </li>
            </ul>
          </div>

          <div>
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              submissions
            </p>
            {subs.length === 0 ? (
              <p className="ritual text-fg-muted text-[0.95rem]">
                No versions submitted yet.
              </p>
            ) : (
              <ol className="font-mono text-[0.82rem]">
                {subs.map((s) => (
                  <li
                    key={s.id}
                    className="border-l-2 border-rule pl-4 py-3 ml-3 relative"
                  >
                    <span
                      className={`absolute -left-[7px] top-3.5 text-sm ${STATUS_TONE[s.status]}`}
                      aria-hidden
                    >
                      {STATUS_GLYPH[s.status]}
                    </span>
                    <header className="flex items-baseline justify-between gap-3 mb-1">
                      <span className="text-fg tabular-nums">v{s.version}</span>
                      <span className={`text-[0.7rem] uppercase tracking-widest ${STATUS_TONE[s.status]}`}>
                        {s.status}
                      </span>
                    </header>
                    {s.result && (
                      <p className="text-fg-muted text-[0.78rem] leading-snug">
                        {s.result}
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </aside>
      </section>
    </>
  );
}
