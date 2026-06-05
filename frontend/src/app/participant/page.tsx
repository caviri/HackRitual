'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import { EvolutionStream } from '../../components/evolution-stream';
import { fetchJson, type ParticipantDTO } from '../../lib/api';

const KIND_CLASS: Record<string, string> = {
  human: 'text-fg-muted',
  agent: 'text-accent',
  team: 'text-primary',
};

const VARIANT_FOR: Record<string, 'sprout' | 'lattice' | 'nucleus'> = {
  human: 'sprout',
  agent: 'lattice',
  team: 'nucleus',
};

export default function ParticipantByQueryPage() {
  const [id, setId] = useState<string | null>(null);
  const [p, setP] = useState<ParticipantDTO | null | undefined>(undefined);

  useEffect(() => {
    const url = new URL(window.location.href);
    const qid = url.searchParams.get('id');
    setId(qid);
    if (!qid) {
      setP(null);
      return;
    }
    void fetchJson<ParticipantDTO | null>(`/api/participants/${qid}`, null).then(setP);
  }, []);

  if (p === undefined) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="font-mono text-fg-dim">summoning…</p>
      </section>
    );
  }

  if (p === null) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
          ritual.participant({id ? JSON.stringify(id) : 'undefined'})
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">Unknown participant.</h1>
        <p className="ritual text-fg-muted mb-6">
          No participant by that id is in the circle right now.
        </p>
        <Link href="/participants/" className="btn">
          ← back to the roster
        </Link>
      </section>
    );
  }

  return (
    <>
      <PageHeader
        prompt={`ritual.participant('${p.display_name}')`}
        title={p.display_name}
        subtitle={p.affiliation ?? `a ${p.type} in the circle`}
        chip={`[${p.type}]`}
        back="/participants/"
        backLabel="all participants"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[1fr_2fr]">
        <aside className="space-y-6">
          <DitheredImage
            seed={p.display_name}
            variant={VARIANT_FOR[p.type] ?? 'sprout'}
            alt={p.display_name}
            className="aspect-square w-full"
            caption={`#${p.id.slice(0, 6)}`}
          />
          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              meta
            </p>
            <ul className="font-mono text-[0.78rem] space-y-2">
              <li>
                <span className="text-fg-dim">kind        </span>
                <span className={KIND_CLASS[p.type] ?? 'text-fg-muted'}>[{p.type}]</span>
              </li>
              {p.affiliation && (
                <li>
                  <span className="text-fg-dim">affiliation </span>
                  <span className="text-fg">{p.affiliation}</span>
                </li>
              )}
              <li>
                <span className="text-fg-dim">status      </span>
                <span className={p.is_waiting ? 'text-warm' : 'text-primary'}>
                  {p.is_waiting ? '▒ waitlist' : '◆ confirmed'}
                </span>
              </li>
              <li>
                <span className="text-fg-dim">id          </span>
                <span className="text-fg break-all">{p.id.slice(0, 12)}…</span>
              </li>
            </ul>
          </div>
        </aside>

        <div className="space-y-8">
          <EvolutionStream participantId={p.id} />
        </div>
      </section>
    </>
  );
}
