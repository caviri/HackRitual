'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import { EvolutionStream } from '../../components/evolution-stream';
import { fetchJson, type ParticipantDetailDTO } from '../../lib/api';

export default function TeamByQueryPage() {
  const [id, setId] = useState<string | null>(null);
  const [team, setTeam] = useState<ParticipantDetailDTO | null | undefined>(undefined);

  useEffect(() => {
    const url = new URL(window.location.href);
    const qid = url.searchParams.get('id');
    setId(qid);
    if (!qid) {
      setTeam(null);
      return;
    }
    void fetchJson<ParticipantDetailDTO | null>(`/api/participants/${qid}`, null).then(setTeam);
  }, []);

  if (team === undefined) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="font-mono text-fg-dim">summoning…</p>
      </section>
    );
  }

  if (team === null || team.type !== 'team') {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
          ritual.team({id ? JSON.stringify(id) : 'undefined'})
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">No such team.</h1>
        <p className="ritual text-fg-muted mb-6">
          {team && team.type !== 'team'
            ? `That id belongs to a ${team.type}, not a team.`
            : 'No team with that id is in the circle right now.'}
        </p>
        <Link href="/teams/" className="btn">
          ← back to teams
        </Link>
      </section>
    );
  }

  return (
    <>
      <PageHeader
        prompt={`ritual.team('${team.display_name}')`}
        title={team.display_name}
        subtitle={team.affiliation ?? 'a team in the circle'}
        chip={`${team.members.length} ${team.members.length === 1 ? 'member' : 'members'}`}
        back="/teams/"
        backLabel="all teams"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[1fr_2fr]">
        <aside className="space-y-6">
          <DitheredImage
            seed={team.display_name}
            src={team.image ?? undefined}
            variant="nucleus"
            alt={`${team.display_name} crest`}
            className="aspect-square w-full"
            caption={`@${team.display_name}`}
          />

          {team.members.length > 0 && (
            <div>
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                the roster
              </p>
              <ul className="space-y-2">
                {team.members.map((m) => (
                  <li
                    key={m.display_name}
                    className="ascii-frame p-3 flex items-center gap-3"
                  >
                    <DitheredImage
                      seed={m.display_name}
                      variant={m.kind === 'agent' ? 'lattice' : 'sprout'}
                      alt={m.display_name}
                      className="w-10 h-10 shrink-0"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-[0.85rem] text-fg truncate">
                        {m.display_name}
                      </p>
                      <p className="font-mono text-[0.7rem] uppercase tracking-wider text-fg-dim">
                        {m.role_in_team === 'captain' ? (
                          <span className="text-primary mr-1">◆ captain</span>
                        ) : (
                          '·'
                        )}{' '}
                        <span className={m.kind === 'agent' ? 'text-accent' : ''}>
                          [{m.kind}]
                        </span>
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              meta
            </p>
            <ul className="font-mono text-[0.78rem] space-y-2">
              <li>
                <span className="text-fg-dim">handle      </span>
                <span className="text-fg">{team.display_name}</span>
              </li>
              <li>
                <span className="text-fg-dim">status      </span>
                <span className="text-primary">{team.status}</span>
              </li>
              {team.affiliation && (
                <li>
                  <span className="text-fg-dim">affiliation </span>
                  <span className="text-fg">{team.affiliation}</span>
                </li>
              )}
              <li>
                <span className="text-fg-dim">id          </span>
                <span className="text-fg break-all">{team.id.slice(0, 12)}…</span>
              </li>
            </ul>
          </div>
        </aside>

        <div className="space-y-8">
          {team.projects.length > 0 && (
            <article>
              <h2 className="font-display italic text-2xl text-fg mb-4">
                Projects from this team
              </h2>
              <ul className="space-y-1.5 font-mono text-[0.9rem]">
                {team.projects.map((pr) => (
                  <li key={pr.id}>
                    <Link
                      href={`/project/?id=${pr.id}`}
                      className="text-fg hover:text-primary transition-colors"
                    >
                      ▸ {pr.title}
                    </Link>
                    <span
                      className={`text-[0.72rem] uppercase tracking-wider ml-2 ${
                        pr.status === 'approved'
                          ? 'text-primary'
                          : pr.status === 'rejected'
                            ? 'text-danger'
                            : 'text-warm'
                      }`}
                    >
                      [{pr.status}]
                    </span>
                  </li>
                ))}
              </ul>
            </article>
          )}

          <EvolutionStream
            participantId={team.id}
            heading="evolution · commits across the team's projects"
          />
        </div>
      </section>
    </>
  );
}
