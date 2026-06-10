'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/page-header';
import { DitheredImage } from '../../../components/dithered-image';
import { EvolutionStream } from '../../../components/evolution-stream';
import { useStage } from '../../../lib/use-stage';

const STATUS_GLYPH: Record<string, string> = {
  draft: '▒',
  final: '◆',
  withdrawn: '✕',
};

const STATUS_TONE: Record<string, string> = {
  draft: 'text-fg-muted',
  final: 'text-primary',
  withdrawn: 'text-fg-dim',
};

export function TeamDetail() {
  const params = useParams();
  const data = useStage();
  const handle = String(params?.handle ?? '');
  const team = data.teams.find((t) => t.handle === handle);

  if (!team) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
          ritual.team({JSON.stringify(handle)})
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">
          No such circle.
        </h1>
        <p className="ritual text-fg-muted mb-6">
          No team carries that handle in this state of the ritual.
        </p>
        <Link href="/teams/" className="btn">
          ← back to the teams
        </Link>
      </section>
    );
  }

  const project = data.proposals.find((p) => p.title === team.project);
  const teamSubs = data.submissions.filter((s) => s.team === team.handle);

  return (
    <>
      <PageHeader
        prompt={`ritual.team('${team.handle}')`}
        title={team.name}
        subtitle={team.blurb}
        chip={`${team.members.length} members`}
        back="/teams/"
        backLabel="all teams"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[1fr_2fr]">
        {/* LEFT — crest + roster */}
        <aside className="space-y-6">
          <DitheredImage
            seed={team.handle}
            variant={team.imageVariant ?? 'nucleus'}
            alt={`${team.name} crest`}
            className="aspect-square w-full"
            caption={`@${team.handle}`}
          />

          <div>
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              the roster
            </p>
            <ul className="space-y-2">
              {team.members.map((m) => (
                <li
                  key={m.handle}
                  className="ascii-frame p-3 flex items-center gap-3"
                >
                  <DitheredImage
                    seed={m.handle}
                    variant={m.kind === 'agent' ? 'lattice' : 'sprout'}
                    alt={m.handle}
                    className="w-10 h-10 shrink-0"
                  />
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/participants/${m.handle}/`}
                      className="font-mono text-[0.85rem] text-fg hover:text-primary truncate block"
                    >
                      {m.handle}
                    </Link>
                    <p className="font-mono text-[0.7rem] uppercase tracking-wider text-fg-dim">
                      {m.role === 'captain' ? (
                        <span className="text-primary mr-1">◆ captain</span>
                      ) : (
                        '·'
                      )}{' '}
                      [{m.kind}]
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        {/* RIGHT — project + submissions */}
        <div className="space-y-8">
          {project ? (
            <article className="ascii-frame overflow-hidden">
              <div className="grid md:grid-cols-[1fr_2fr]">
                <DitheredImage
                  seed={project.title}
                  variant={project.imageVariant ?? 'bloom'}
                  alt={project.title}
                  className="aspect-square md:aspect-auto md:h-full"
                />
                <div className="p-5">
                  <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-2">
                    working on
                  </p>
                  <h2 className="font-display italic text-3xl text-fg mb-2">
                    {project.title}
                  </h2>
                  <p className="font-mono text-[0.78rem] uppercase tracking-wider text-warm mb-3">
                    [{project.track}]
                    {project.rank && (
                      <span className="text-accent ml-3">◆ rank {project.rank}</span>
                    )}
                  </p>
                  <p className="text-fg-muted text-[0.95rem] leading-relaxed mb-4">
                    {project.body ?? project.blurb}
                  </p>
                  <Link
                    href={`/projects/${project.id}/`}
                    className="font-mono text-[0.78rem] text-primary hover:underline"
                  >
                    see the project →
                  </Link>
                </div>
              </div>
            </article>
          ) : (
            <article className="ascii-frame p-6">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-2">
                project
              </p>
              <p className="ritual text-fg-muted">
                Not yet attached to a project. The circle is gathering.
              </p>
            </article>
          )}

          <EvolutionStream
            participantId={team.handle}
            heading="evolution · commits across the team's projects"
          />

          <article>
            <h2 className="font-display italic text-2xl text-fg mb-4">
              Submissions from this team
            </h2>
            {teamSubs.length === 0 ? (
              <p className="ritual text-fg-muted">
                Nothing submitted yet. The work is in progress.
              </p>
            ) : (
              <ol className="font-mono text-[0.85rem]">
                {teamSubs.map((s) => (
                  <li
                    key={s.id}
                    className="grid grid-cols-[auto_1fr_auto] items-baseline gap-x-4 py-3 border-t border-rule first:border-t-0"
                  >
                    <span className="text-fg tabular-nums">v{s.version}</span>
                    <div>
                      <p>
                        <Link
                          href={`/projects/${s.projectId}/`}
                          className="text-fg hover:text-primary"
                        >
                          {s.projectTitle}
                        </Link>
                        {s.result && (
                          <span className="text-fg-muted text-[0.78rem] ml-2">
                            — {s.result}
                          </span>
                        )}
                      </p>
                      <p className="text-fg-dim text-[0.72rem] tabular-nums mt-0.5">
                        {s.modifiedAt}
                      </p>
                    </div>
                    <span
                      className={`text-[0.7rem] uppercase tracking-widest ${STATUS_TONE[s.status]}`}
                    >
                      <span aria-hidden className="mr-1">{STATUS_GLYPH[s.status]}</span>
                      {s.status}
                      {s.score && (
                        <span className="text-accent ml-2 tabular-nums">
                          {s.score.toFixed(1)}
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </article>
        </div>
      </section>
    </>
  );
}
