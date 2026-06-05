'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import { EvolutionStream } from '../../components/evolution-stream';
import { fetchJson, type ParticipantDTO } from '../../lib/api';

export default function TeamByQueryPage() {
  const [id, setId] = useState<string | null>(null);
  const [team, setTeam] = useState<ParticipantDTO | null | undefined>(undefined);

  useEffect(() => {
    const url = new URL(window.location.href);
    const qid = url.searchParams.get('id');
    setId(qid);
    if (!qid) {
      setTeam(null);
      return;
    }
    void fetchJson<ParticipantDTO | null>(`/api/participants/${qid}`, null).then(setTeam);
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
        chip={`[team]`}
        back="/teams/"
        backLabel="all teams"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[1fr_2fr]">
        <aside className="space-y-6">
          <DitheredImage
            seed={team.display_name}
            variant="nucleus"
            alt={`${team.display_name} crest`}
            className="aspect-square w-full"
            caption={`@${team.display_name}`}
          />
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
          <EvolutionStream
            participantId={team.id}
            heading="evolution · commits across the team's projects"
          />
        </div>
      </section>
    </>
  );
}
