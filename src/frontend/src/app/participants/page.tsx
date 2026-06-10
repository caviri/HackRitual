'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import { useStage } from '../../lib/use-stage';
import { api, type ParticipantDTO } from '../../lib/api';
import type { ParticipantMock } from '../../lib/mocks';

type Filter = 'all' | 'human' | 'agent' | 'team';

const FILTER_GLYPH: Record<Filter, string> = {
  all: '◆',
  human: '·',
  agent: '◇',
  team: '▰',
};

/** Display shape — built from either real backend rows or mocks. */
interface PRow {
  key: string;
  href: string;
  displayName: string;
  meta: string;
  kind: 'human' | 'agent' | 'team';
  affiliation?: string;
  bio?: string;
  imageVariant: 'sprout' | 'lattice' | 'nucleus' | 'bloom';
  waitlist: boolean;
  imageSeed: string;
}

export default function ParticipantsPage() {
  const data = useStage();
  const [filter, setFilter] = useState<Filter>('all');
  const [real, setReal] = useState<ParticipantDTO[] | null>(null);

  useEffect(() => {
    void api.participants().then((p) => {
      if (p.length > 0) setReal(p);
    });
  }, []);

  // Build display rows
  const rows: PRow[] = real
    ? real.map((p) => ({
        key: p.id,
        href: `/participant/?id=${p.id}`,
        displayName: p.display_name,
        meta: p.affiliation ?? '',
        kind: p.type,
        affiliation: p.affiliation ?? undefined,
        imageVariant: p.type === 'team' ? 'nucleus' : p.type === 'agent' ? 'lattice' : 'sprout',
        waitlist: !!p.is_waiting,
        imageSeed: p.display_name,
      }))
    : data.participants.map((p: ParticipantMock) => ({
        key: p.handle,
        href: `/participants/${p.handle}/`,
        displayName: p.displayName ?? p.handle,
        meta: p.affiliation ?? p.meta,
        kind: p.kind,
        affiliation: p.affiliation,
        bio: p.bio,
        imageVariant: p.imageVariant ?? (p.kind === 'team' ? 'nucleus' : p.kind === 'agent' ? 'lattice' : 'sprout'),
        waitlist: !!p.waitlist,
        imageSeed: p.handle,
      }));

  const confirmed = rows.filter((r) => !r.waitlist);
  const waitlist = rows.filter((r) => r.waitlist);
  const visible = filter === 'all' ? confirmed : confirmed.filter((r) => r.kind === filter);

  const totalLabel = real
    ? `${rows.length} live`
    : `${data.participantCount} in · ${data.waitlistCount} wait`;

  const subtitle = {
    DRAFT: 'No one has stepped into the circle yet. The waitlist holds those who arrived early.',
    OPEN: 'Everyone — and everything — in the circle. Humans, agents, teams. Confirmed and waitlisted.',
    FROZEN: 'The circle is sealed. No more entries until the gates open again.',
    FINAL: 'The named, in order of standing.',
    ARCHIVED: 'The roster of record. Frozen in the export.',
  }[data.state];

  return (
    <>
      <PageHeader
        prompt={`ritual.participants(filter='${filter}')`}
        title="Participants"
        subtitle={subtitle}
        chip={totalLabel}
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-10">
        {/* filter chips */}
        <div className="flex flex-wrap gap-2 mb-10 font-mono text-[0.72rem] uppercase tracking-widest">
          {(['all', 'human', 'agent', 'team'] as Filter[]).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={`border px-3 py-1.5 transition-colors ${
                filter === f
                  ? 'border-primary text-primary'
                  : 'border-rule text-fg-muted hover:text-fg'
              }`}
            >
              <span aria-hidden className="mr-1.5 text-warm">{FILTER_GLYPH[f]}</span>
              {f}
            </button>
          ))}
        </div>

        {visible.length === 0 ? (
          <p className="ritual text-fg-muted">No one matches this filter.</p>
        ) : (
          <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {visible.map((p) => (
              <ParticipantCard key={p.key} p={p} />
            ))}
          </ul>
        )}

        {waitlist.length > 0 && (
          <>
            <div className="divider mt-16 mb-8">
              <span aria-hidden>▒</span>
              <span>waitlist · {waitlist.length}</span>
              <span aria-hidden>▒</span>
            </div>
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {waitlist.map((p) => (
                <li
                  key={p.key}
                  className="flex items-center gap-4 border border-rule p-3 opacity-80"
                >
                  <DitheredImage
                    seed={p.imageSeed}
                    variant={p.imageVariant}
                    alt={p.displayName}
                    className="w-12 h-12 shrink-0"
                  />
                  <div className="min-w-0 flex-1">
                    <Link
                      href={p.href}
                      className="font-mono text-[0.85rem] text-fg-muted hover:text-primary truncate block"
                    >
                      {p.displayName}
                    </Link>
                    <p className="font-mono text-[0.7rem] uppercase tracking-wider text-fg-dim truncate">
                      {p.meta}
                    </p>
                  </div>
                  <span className="font-mono text-[0.66rem] uppercase tracking-widest text-warm">
                    ▒ wait
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}

function ParticipantCard({ p }: { p: PRow }) {
  const kindClass =
    p.kind === 'human'
      ? 'text-fg-muted'
      : p.kind === 'agent'
        ? 'text-accent'
        : 'text-primary';
  return (
    <li>
      <Link
        href={p.href}
        className="ascii-frame block overflow-hidden group no-underline hover:border-primary transition-colors"
      >
        <div className="flex">
          <DitheredImage
            seed={p.imageSeed}
            variant={p.imageVariant}
            alt={p.displayName}
            className="w-24 h-24 shrink-0"
          />
          <div className="p-4 flex-1 min-w-0">
            <header className="flex items-baseline justify-between gap-2 mb-1">
              <p className="font-display italic text-lg text-fg group-hover:text-primary transition-colors truncate">
                {p.displayName}
              </p>
              <span className={`font-mono text-[0.66rem] uppercase tracking-widest ${kindClass} shrink-0`}>
                [{p.kind}]
              </span>
            </header>
            <p className="font-mono text-[0.72rem] uppercase tracking-wider text-fg-dim truncate">
              {p.meta || '—'}
            </p>
          </div>
        </div>
        {p.bio && (
          <p className="px-4 pb-4 pt-2 text-fg-muted text-[0.82rem] leading-relaxed border-t border-rule">
            {p.bio}
          </p>
        )}
      </Link>
    </li>
  );
}
