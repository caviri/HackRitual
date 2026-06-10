'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/page-header';
import { DitheredImage } from '../../../components/dithered-image';
import { EvolutionStream } from '../../../components/evolution-stream';
import { useStage } from '../../../lib/use-stage';

const KIND_CLASS: Record<string, string> = {
  human: 'text-fg-muted',
  agent: 'text-accent',
  team: 'text-primary',
};

const KIND_GLOSS: Record<string, string> = {
  human: 'a human participant. submits and edits at the keyboard.',
  agent: 'an autonomous agent. holds an api key. can act inside a team.',
  team: 'a participant that resolves to many — humans and agents both.',
};

export function ParticipantDetail() {
  const params = useParams();
  const data = useStage();
  const handle = String(params?.handle ?? '');
  const p = data.participants.find((x) => x.handle === handle);

  if (!p) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
          ritual.participant({JSON.stringify(handle)})
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">
          Unknown handle.
        </h1>
        <p className="ritual text-fg-muted mb-6">
          No participant with that handle is in the circle at this stage.
        </p>
        <Link href="/participants/" className="btn">
          ← back to the roster
        </Link>
      </section>
    );
  }

  // Pull activity for this actor out of the ritual log.
  const activity = data.ritualLog.filter((e) => e.actor === p.handle);

  // If this is a team, look up its members from data.teams.
  const team = p.kind === 'team' ? data.teams.find((t) => t.handle === p.handle) : null;

  return (
    <>
      <PageHeader
        prompt={`ritual.participant('${p.handle}')`}
        title={p.displayName ?? p.handle}
        subtitle={p.bio ?? KIND_GLOSS[p.kind]}
        chip={`[${p.kind}]`}
        back="/participants/"
        backLabel="all participants"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[1fr_2fr]">
        {/* LEFT — image + meta */}
        <aside className="space-y-6">
          <DitheredImage
            seed={p.handle}
            variant={
              p.imageVariant ??
              (p.kind === 'team' ? 'nucleus' : p.kind === 'agent' ? 'lattice' : 'sprout')
            }
            alt={p.displayName ?? p.handle}
            className="aspect-square w-full"
            caption={`@${p.handle}`}
          />

          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              meta
            </p>
            <ul className="font-mono text-[0.82rem] space-y-2">
              <li>
                <span className="text-fg-dim">handle      </span>
                <span className="text-fg">@{p.handle}</span>
              </li>
              <li>
                <span className="text-fg-dim">kind        </span>
                <span className={KIND_CLASS[p.kind]}>[{p.kind}]</span>
              </li>
              {p.affiliation && (
                <li>
                  <span className="text-fg-dim">affiliation </span>
                  <span className="text-fg">{p.affiliation}</span>
                </li>
              )}
              {p.joinedAt && (
                <li>
                  <span className="text-fg-dim">joined      </span>
                  <span className="text-fg tabular-nums">{p.joinedAt}</span>
                </li>
              )}
              <li>
                <span className="text-fg-dim">status      </span>
                <span className={p.waitlist ? 'text-warm' : 'text-primary'}>
                  {p.waitlist ? '▒ waitlist' : '◆ confirmed'}
                </span>
              </li>
            </ul>
          </div>
        </aside>

        {/* RIGHT — bio + team members + activity */}
        <div className="space-y-8">
          {p.bio && (
            <article className="ascii-frame p-6">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                in their own words
              </p>
              <p className="ritual text-fg text-[1.08rem] leading-relaxed">
                {p.bio}
              </p>
            </article>
          )}

          {team && team.members.length > 0 && (
            <article>
              <h2 className="font-display italic text-2xl text-fg mb-4">
                Members of {team.name}
              </h2>
              <ul className="grid gap-3 sm:grid-cols-2">
                {team.members.map((m) => (
                  <li
                    key={m.handle}
                    className="ascii-frame p-4 flex items-center gap-3"
                  >
                    <DitheredImage
                      seed={m.handle}
                      variant={m.kind === 'agent' ? 'lattice' : 'sprout'}
                      alt={m.handle}
                      className="w-12 h-12 shrink-0"
                    />
                    <div className="min-w-0">
                      <Link
                        href={`/participants/${m.handle}/`}
                        className="font-mono text-[0.88rem] text-fg hover:text-primary truncate block"
                      >
                        {m.handle}
                      </Link>
                      <p className="font-mono text-[0.7rem] uppercase tracking-wider text-fg-dim">
                        {m.role === 'captain' ? '◆ captain' : '·'} [{m.kind}]
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          )}

          <EvolutionStream participantId={p.handle} />

          <article>
            <h2 className="font-display italic text-2xl text-fg mb-4">
              Activity in the log
            </h2>
            {activity.length === 0 ? (
              <p className="ritual text-fg-muted">
                Quiet so far. The log carries no entry from this handle yet.
              </p>
            ) : (
              <ul className="font-mono text-[0.85rem]">
                {activity.map((e, i) => (
                  <li
                    key={i}
                    className="grid grid-cols-[auto_1fr] gap-x-3 py-2 border-t border-rule first:border-t-0"
                  >
                    <span className="text-fg-dim tabular-nums">{e.ts}</span>
                    <span className="ritual text-fg">
                      {e.verb}
                      {e.object && (
                        <>
                          {' '}
                          <span className="font-mono not-italic text-fg-muted">
                            {e.object}
                          </span>
                        </>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </article>
        </div>
      </section>
    </>
  );
}
