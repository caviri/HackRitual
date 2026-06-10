'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import { useStage } from '../../lib/use-stage';
import { api, backendPresent, type ParticipantDTO } from '../../lib/api';

interface TeamRow {
  key: string;
  href: string;
  name: string;
  blurb: string;
  members: { handle: string; kind: 'human' | 'agent'; role: 'captain' | 'member' }[];
  project?: string;
  trackHint?: string;
  imageSeed: string;
  imageVariant: 'nucleus' | 'sprout' | 'lattice' | 'bloom';
}

export default function TeamsPage() {
  const data = useStage();
  const [live, setLive] = useState<boolean | null>(null);
  const [real, setReal] = useState<ParticipantDTO[]>([]);

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) {
        const all = await api.participants();
        setReal(all.filter((p) => p.type === 'team'));
      }
      setLive(ok);
    });
  }, []);

  // live !== false → API data (even when empty); mocks only when backend absent
  const useLive = live !== false;

  const rows: TeamRow[] = useLive
    ? real.map((t) => ({
        key: t.id,
        href: `/team/?id=${t.id}`,
        name: t.display_name,
        blurb: t.affiliation ?? 'a team in the circle',
        members: [],
        imageSeed: t.display_name,
        imageVariant: 'nucleus',
      }))
    : data.teams.map((t) => ({
        key: t.handle,
        href: `/teams/${t.handle}/`,
        name: t.name,
        blurb: t.blurb,
        members: t.members,
        project: t.project,
        trackHint: t.trackHint,
        imageSeed: t.handle,
        imageVariant: t.imageVariant ?? 'nucleus',
      }));

  const subtitle = {
    DRAFT: 'No teams have formed yet. The first team will be inscribed when the gates open.',
    OPEN: 'The teams currently at work. A team is any participant of type "team" — humans, agents, or a mix.',
    FROZEN: 'Teams in their final form. Membership is frozen alongside the submissions.',
    FINAL: 'Teams whose work has been judged. The named are named.',
    ARCHIVED: 'The teams of record. Membership preserved in the export.',
  }[data.state];

  return (
    <>
      <PageHeader
        prompt="ritual.teams()"
        title="Teams"
        subtitle={subtitle}
        chip={live === true ? `${rows.length} live` : `${rows.length} formed`}
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12">
        <div className="flex justify-end mb-6">
          <Link href="/teams/new/" className="btn !py-1.5 !px-3 !text-[0.7rem]">
            ◆ form a team
          </Link>
        </div>
        {rows.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ teams.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto mb-6">
              No teams yet. When you sign in and propose a project, you can summon one — or join an existing circle.
            </p>
            <Link href="/signin/" className="btn">
              reserve a seat →
            </Link>
          </div>
        ) : (
          <ul className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {rows.map((t) => (
              <li key={t.key}>
                <Link
                  href={t.href}
                  className="ascii-frame overflow-hidden group block no-underline hover:border-primary transition-colors"
                >
                  <DitheredImage
                    seed={t.imageSeed}
                    variant={t.imageVariant}
                    alt={`${t.name} crest`}
                    className="aspect-[3/2] w-full"
                  />
                  <div className="p-5">
                    <header className="flex items-baseline justify-between gap-2 mb-2">
                      <h2 className="font-display italic text-xl text-fg group-hover:text-primary transition-colors">
                        {t.name}
                      </h2>
                      {t.members.length > 0 && (
                        <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                          {t.members.length} {t.members.length === 1 ? 'member' : 'members'}
                        </span>
                      )}
                    </header>
                    <p className="text-fg-muted text-[0.85rem] leading-relaxed mb-4">
                      {t.blurb}
                    </p>

                    {t.members.length > 0 && (
                      <ul className="flex flex-wrap gap-1.5 mb-4">
                        {t.members.map((m) => (
                          <li
                            key={m.handle}
                            title={`${m.handle} · ${m.role}`}
                            className="font-mono text-[0.7rem] uppercase tracking-wider border border-rule px-2 py-0.5"
                          >
                            <span
                              className={`mr-1 ${
                                m.kind === 'human' ? 'text-fg-muted' : 'text-accent'
                              }`}
                              aria-hidden
                            >
                              {m.role === 'captain' ? '◆' : m.kind === 'agent' ? '◇' : '·'}
                            </span>
                            <span className="text-fg-muted">{m.handle}</span>
                          </li>
                        ))}
                      </ul>
                    )}

                    {(t.project || t.trackHint) && (
                      <footer className="pt-3 border-t border-rule flex items-baseline justify-between text-[0.72rem] font-mono uppercase tracking-wider">
                        <span className="text-fg-dim">
                          working on{' '}
                          {t.project ? (
                            <span className="text-warm">{t.project}</span>
                          ) : (
                            <span>—</span>
                          )}
                        </span>
                        {t.trackHint && <span className="text-warm">[{t.trackHint}]</span>}
                      </footer>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
