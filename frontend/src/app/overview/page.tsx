'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { DitheredImage } from '../../components/dithered-image';
import { useStage } from '../../lib/use-stage';
import {
  api,
  type MeDTO,
  type ProjectDTO,
  type SubmissionDTO,
} from '../../lib/api';

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

export default function OverviewPage() {
  const data = useStage();
  const [me, setMe] = useState<MeDTO | null | undefined>(undefined);
  const [myProjects, setMyProjects] = useState<ProjectDTO[]>([]);
  const [mySubs, setMySubs] = useState<SubmissionDTO[]>([]);

  useEffect(() => {
    void api.me().then(async (u) => {
      setMe(u);
      if (!u?.participant) return;
      const pid = u.participant.id;
      // All projects, then filter to those proposed by my participant
      const projects = await api.projects();
      setMyProjects(projects.filter((p) => p.proposed_by_participant_id === pid));
      // All submissions where I am the team-participant
      const subs = await api.submissions();
      setMySubs(subs.filter((s) => s.participant_id === pid));
    });
  }, []);

  const subtitle = {
    DRAFT: 'The ritual has not begun. Reserve your seat — the gates will open soon.',
    OPEN: 'Your team, your project, what is being asked of you next.',
    FROZEN: 'Your submission is sealed. The judges deliberate.',
    FINAL: 'The verdict, with you in it.',
    ARCHIVED: 'The record of what was. You may dispel this container at any time.',
  }[data.state];

  // ── REAL mode (authed user with participant) ──
  if (me && me.participant) {
    const handle = me.participant.display_name;
    return (
      <>
        <PageHeader
          prompt={`ritual.you('${handle}')`}
          title={`Welcome, ${handle}.`}
          subtitle={subtitle}
          chip={me.role === 'admin' ? '✦ admin' : `[${me.participant.type}]`}
        />

        <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-8 lg:grid-cols-[1.6fr_1fr]">
          <div className="space-y-8">
            {/* my projects */}
            <article>
              <div className="mb-4 flex items-baseline justify-between gap-4">
                <h2 className="font-display italic text-2xl text-fg">
                  your projects
                </h2>
                <Link
                  href="/projects/new/"
                  className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-muted hover:text-primary"
                >
                  ◆ propose one →
                </Link>
              </div>
              {myProjects.length === 0 ? (
                <div className="ascii-frame p-6 text-center">
                  <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-2">
                    $ you.projects() → []
                  </p>
                  <p className="ritual text-fg-muted text-[1rem] max-w-md mx-auto mb-4">
                    You have not proposed anything yet. Speak it plainly — others
                    will gather around it.
                  </p>
                  <Link href="/projects/new/" className="btn">
                    propose a project →
                  </Link>
                </div>
              ) : (
                <ul className="grid gap-4">
                  {myProjects.map((p) => (
                    <li key={p.id}>
                      <Link
                        href={`/project/?id=${p.id}`}
                        className="ascii-frame block overflow-hidden grid md:grid-cols-[1fr_2fr] group no-underline hover:border-primary transition-colors"
                      >
                        <DitheredImage
                          seed={p.title}
                          variant="bloom"
                          alt={p.title}
                          className="aspect-square md:aspect-auto md:h-full"
                        />
                        <div className="p-5">
                          <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-2">
                            your project ·{' '}
                            <span
                              className={
                                p.status === 'approved'
                                  ? 'text-primary'
                                  : p.status === 'rejected'
                                    ? 'text-danger'
                                    : 'text-warm'
                              }
                            >
                              {p.status}
                            </span>
                          </p>
                          <h3 className="font-display italic text-2xl text-fg group-hover:text-primary transition-colors mb-2">
                            {p.title}
                          </h3>
                          <p className="text-fg-muted text-[0.92rem] leading-relaxed">
                            {(p.description ?? '').split('\n')[0].slice(0, 200)}
                          </p>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </article>

            {/* my submissions */}
            <article>
              <h2 className="font-display italic text-2xl text-fg mb-4">
                your submissions
              </h2>
              {mySubs.length === 0 ? (
                <p className="ritual text-fg-muted">
                  No versions submitted yet. Edit one of your projects to begin
                  drafting.
                </p>
              ) : (
                <ol className="font-mono text-[0.85rem]">
                  {mySubs.map((s) => (
                    <li
                      key={s.id}
                      className="grid grid-cols-[auto_1fr_auto] items-baseline gap-x-4 py-3 border-t border-rule first:border-t-0"
                    >
                      <span className="text-fg tabular-nums">v{s.version}</span>
                      <div>
                        <Link
                          href={`/submission/?id=${s.id}`}
                          className="text-fg hover:text-primary"
                        >
                          {(s.title ?? '').slice(0, 60) ||
                            myProjects.find((p) => p.id === s.project_id)?.title ||
                            `#${s.id.slice(0, 6)}`}
                        </Link>
                        {s.result && (
                          <p className="text-fg-muted text-[0.78rem] mt-0.5 truncate">
                            {s.result}
                          </p>
                        )}
                      </div>
                      <span
                        className={`text-[0.7rem] uppercase tracking-widest ${STATUS_TONE[s.status]}`}
                      >
                        <span aria-hidden className="mr-1">
                          {STATUS_GLYPH[s.status]}
                        </span>
                        {s.status}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </article>

            {/* about the event */}
            <article className="ascii-frame p-6">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                about this ritual
              </p>
              <p className="text-fg-muted leading-relaxed text-[1rem] mb-4">
                One container · one event · one SQLite file. Three tracks, three
                phases. When the ritual ends, the artefact travels with you in a
                single zip.
              </p>
              <Link
                href="/pages/rites/"
                className="font-mono text-[0.78rem] text-primary hover:underline"
              >
                read the rites in full →
              </Link>
            </article>
          </div>

          {/* SIDEBAR */}
          <aside className="space-y-6">
            <div className="ascii-frame p-5">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                you
              </p>
              <ul className="font-mono text-[0.82rem] space-y-2">
                <li>
                  <span className="text-fg-dim">email    </span>
                  <span className="text-fg break-all">{me.email}</span>
                </li>
                <li>
                  <span className="text-fg-dim">handle   </span>
                  <span className="text-fg">{handle}</span>
                </li>
                <li>
                  <span className="text-fg-dim">type     </span>
                  <span className="text-fg-muted">[{me.participant.type}]</span>
                </li>
                <li>
                  <span className="text-fg-dim">status   </span>
                  <span className={me.participant.is_waiting ? 'text-warm' : 'text-primary'}>
                    {me.participant.is_waiting ? '▒ waitlist' : '◆ confirmed'}
                  </span>
                </li>
                {me.role === 'admin' && (
                  <li>
                    <span className="text-fg-dim">role     </span>
                    <span className="text-accent">✦ admin</span>
                  </li>
                )}
              </ul>
            </div>

            <div className="ascii-frame p-5">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                the ritual now
              </p>
              <ul className="font-mono text-[0.82rem] space-y-2">
                <li>
                  <span className="text-fg-dim">state   </span>
                  <span className="text-primary">{data.state}</span>
                </li>
                <li>
                  <span className="text-fg-dim">in      </span>
                  <span className="text-fg">{data.participantCount}</span>
                </li>
              </ul>
            </div>

            <div className="ascii-frame p-5">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                quick paths
              </p>
              <ul className="space-y-2 font-mono text-[0.85rem]">
                <li><Link href="/profile/" className="text-fg-muted hover:text-primary">▸ your portrait</Link></li>
                <li><Link href="/profile/agents/" className="text-fg-muted hover:text-primary">▸ your agents</Link></li>
                <li><Link href={`/participant/?id=${me.participant.id}`} className="text-fg-muted hover:text-primary">▸ your public page</Link></li>
                <li><Link href="/projects/" className="text-fg-muted hover:text-primary">▸ browse all projects</Link></li>
                <li><Link href="/log/" className="text-fg-muted hover:text-primary">▸ the ritual log</Link></li>
                {me.role === 'admin' && (
                  <li><Link href="/admin/" className="text-accent hover:text-primary">▸ admin console</Link></li>
                )}
              </ul>
            </div>
          </aside>
        </section>
      </>
    );
  }

  // ── MOCK / unauthed mode (existing demo content) ──
  const you = data.you;
  const youProject = data.proposals.find((p) => p.id === you?.projectId);

  return (
    <>
      <PageHeader
        prompt={`ritual.you('${you?.handle ?? 'guest'}')`}
        title={you?.handle === 'you' ? 'Welcome.' : `Welcome, ${you?.handle}.`}
        subtitle={subtitle}
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-8 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-8">
          <article className="ascii-frame overflow-hidden">
            {youProject ? (
              <div className="grid md:grid-cols-[1fr_2fr]">
                <DitheredImage
                  seed={youProject.title}
                  variant={youProject.imageVariant ?? 'bloom'}
                  alt={youProject.title}
                  className="aspect-square md:aspect-auto md:h-full"
                />
                <div className="p-6">
                  <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                    your project
                  </p>
                  <h2 className="font-display italic text-3xl text-fg mb-2">
                    {youProject.title}
                  </h2>
                  <p className="font-mono text-[0.78rem] uppercase tracking-wider text-warm mb-4">
                    [{youProject.track}] · team {you?.teamName}
                  </p>
                  <p className="text-fg-muted text-[0.95rem] leading-relaxed mb-5">
                    {youProject.body ?? youProject.blurb}
                  </p>
                  <div className="flex flex-wrap items-center gap-4 pt-4 border-t border-rule">
                    <span className="font-mono text-[0.78rem] text-fg">
                      <span className="text-fg-dim mr-2">status:</span>
                      {you?.projectStatus}
                    </span>
                    {you?.nextAction && (
                      <Link href={you.nextAction.href} className="btn ml-auto">
                        <span aria-hidden>▸</span>
                        {you.nextAction.label}
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center">
                <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                  you have not yet forged
                </p>
                <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto mb-6">
                  No team, no project — yet. Step into the circle and pick a track to begin.
                </p>
                <Link href="/signin/" className="btn">
                  step into the circle →
                </Link>
              </div>
            )}
          </article>

          <article className="ascii-frame p-6">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              about this ritual
            </p>
            <p className="text-fg-muted leading-relaxed text-[1rem] mb-4">
              The Forge of Light-and-Lichen is a 48-hour gathering for work that
              treats software like a garden — sown, tended, harvested.
            </p>
            <Link
              href="/pages/rites/"
              className="font-mono text-[0.78rem] text-primary hover:underline"
            >
              read the rites in full →
            </Link>
          </article>
        </div>

        <aside className="space-y-6">
          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              the ritual now
            </p>
            <ul className="font-mono text-[0.82rem] space-y-2">
              <li><span className="text-fg-dim">state    </span><span className="text-primary">{data.state}</span></li>
              <li><span className="text-fg-dim">in       </span><span className="text-fg">{data.participantCount}</span></li>
              <li><span className="text-fg-dim">on wait  </span><span className="text-warm">{data.waitlistCount}</span></li>
            </ul>
          </div>

          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              quick paths
            </p>
            <ul className="space-y-2 font-mono text-[0.85rem]">
              <li><Link href="/signin/" className="text-primary hover:underline">▸ sign in to claim a participant</Link></li>
              <li><Link href="/projects/" className="text-fg-muted hover:text-primary">▸ browse projects</Link></li>
              <li><Link href="/log/" className="text-fg-muted hover:text-primary">▸ the ritual log</Link></li>
            </ul>
          </div>
        </aside>
      </section>
    </>
  );
}
