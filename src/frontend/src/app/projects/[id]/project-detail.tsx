'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/page-header';
import { DitheredImage } from '../../../components/dithered-image';
import { RepositoriesPanel } from '../../../components/repositories-panel';
import { useStage } from '../../../lib/use-stage';

const STATUS_GLYPH: Record<string, string> = {
  draft: '▒',
  final: '◆',
  withdrawn: '✕',
};

const STATUS_TONE: Record<string, string> = {
  draft: 'text-fg-muted',
  final: 'text-primary',
  withdrawn: 'text-fg-dim line-through',
};

const clamp = (n: number) => Math.max(0, Math.min(100, n));

export function ProjectDetail() {
  const params = useParams();
  const data = useStage();
  const id = Number(params?.id);
  const project = data.proposals.find((p) => p.id === id) ?? data.proposals[0];

  if (!project) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-4">
          ritual.project(undefined)
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">Not yet forged</h1>
        <p className="ritual text-fg-muted">
          No project goes by that id in the current state of the ritual.
        </p>
      </section>
    );
  }

  const versions = data.submissions.filter((s) => s.projectId === project.id);

  // Deterministic per-criterion breakdown from the project's total score.
  // Real backend will replace this with persisted judging data.
  const breakdown =
    project.score != null
      ? [
          { label: 'craft', value: clamp(project.score + 1.5) },
          { label: 'originality', value: clamp(project.score - 0.9) },
          { label: 'reach', value: clamp(project.score + 0.3) },
          { label: 'fit-to-track', value: clamp(project.score - 1.1) },
        ]
      : null;

  return (
    <>
      <PageHeader
        prompt={`ritual.project('${project.title}')`}
        title={project.title}
        subtitle={project.blurb}
        chip={project.rank ? `◆ rank ${project.rank}` : `${versions.length} versions`}
        back="/projects/"
        backLabel="all projects"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-8">
          <DitheredImage
            seed={project.title}
            variant={project.imageVariant ?? 'bloom'}
            alt={project.title}
            className="aspect-[16/9] w-full"
            caption={`${project.title} · ${project.track}`}
          />

          <article className="ascii-frame p-6">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              about this project
            </p>
            <p className="text-fg-muted leading-relaxed text-[1rem]">
              {project.body ?? project.blurb}
            </p>
          </article>

          {breakdown && (
            <article className="ascii-frame p-6">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-4">
                the verdict, broken down
              </p>
              <ul className="space-y-3 font-mono text-[0.82rem]">
                {breakdown.map((b) => (
                  <li key={b.label}>
                    <div className="flex items-baseline justify-between gap-3 mb-1">
                      <span className="text-fg-muted uppercase tracking-wider text-[0.72rem]">
                        {b.label}
                      </span>
                      <span className="text-accent tabular-nums">{b.value.toFixed(1)}</span>
                    </div>
                    <div className="h-1 bg-rule overflow-hidden">
                      <div
                        className="h-full bg-accent"
                        style={{ width: `${b.value}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
              <p className="font-mono text-[0.7rem] text-fg-dim mt-4">
                ▒ scores out of 100. weighted average is the headline figure.
              </p>
            </article>
          )}

          <RepositoriesPanel projectId={String(project.id)} />

          <article className="ascii-frame p-6">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-4">
              the team
            </p>
            <p className="font-display italic text-2xl text-fg mb-1">
              {project.team ?? project.proposer}
            </p>
            <p className="font-mono text-[0.78rem] text-fg-muted uppercase tracking-wider mb-4">
              proposed by <span className="text-fg">{project.proposer}</span>
            </p>
            <Link
              href="/teams/"
              className="font-mono text-[0.78rem] text-primary hover:underline"
            >
              see the roster →
            </Link>
          </article>
        </div>

        <aside className="space-y-6">
          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-4">
              meta
            </p>
            <ul className="font-mono text-[0.78rem] space-y-2">
              <li><span className="text-fg-dim">track    </span><span className="text-warm">{project.track}</span></li>
              <li><span className="text-fg-dim">id       </span><span className="text-fg">#{String(project.id).padStart(3, '0')}</span></li>
              <li><span className="text-fg-dim">proposer </span><span className="text-fg">{project.proposer}</span></li>
              {project.team && (
                <li><span className="text-fg-dim">team     </span><span className="text-fg">{project.team}</span></li>
              )}
              {project.score && (
                <li><span className="text-fg-dim">score    </span><span className="text-accent tabular-nums">{project.score.toFixed(2)}</span></li>
              )}
              {project.rank && (
                <li><span className="text-fg-dim">rank     </span><span className="text-accent">◆ {project.rank}</span></li>
              )}
            </ul>
          </div>

          <div>
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              submissions
            </p>
            {versions.length === 0 ? (
              <p className="ritual text-fg-muted text-[0.95rem]">
                Nothing submitted yet for this project.
              </p>
            ) : (
              <ol className="font-mono text-[0.82rem]">
                {versions.map((s) => (
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
                    <p className="text-fg-dim text-[0.72rem] tabular-nums mb-1">
                      {s.modifiedAt}
                    </p>
                    {s.result && (
                      <p className="text-fg-muted text-[0.78rem] leading-snug">
                        {s.result}
                      </p>
                    )}
                    {s.score && (
                      <p className="text-accent text-[0.78rem] mt-1 tabular-nums">
                        score: {s.score.toFixed(1)}
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
