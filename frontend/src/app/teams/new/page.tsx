'use client';

import { useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '../../../components/page-header';

/**
 * Team formation form.
 *
 * In HackRitual the canonical identity is `participants` with type='team'.
 * Backend endpoint to mint one is /api/participants — for the proposal
 * phase this form just collects intent and routes to the projects flow.
 */
export default function NewTeamPage() {
  const [name, setName] = useState('');
  const [blurb, setBlurb] = useState('');
  const [done, setDone] = useState(false);

  if (done) {
    return (
      <>
        <PageHeader
          prompt="ritual.team.formed()"
          title="A circle inside the circle."
          subtitle="Your team is formed. Invite members, then propose what you'll build together."
        />
        <section className="mx-auto w-full max-w-2xl px-6 py-12">
          <div className="ascii-frame p-6 mb-6">
            <p className="font-mono text-[0.78rem] text-primary mb-3">▸ team summoned</p>
            <p className="font-display italic text-2xl text-fg mb-1">{name}</p>
            <p className="text-fg-muted text-[0.95rem] leading-relaxed mb-4">
              {blurb || 'No blurb yet — you can write one any time.'}
            </p>
            <div className="font-mono text-[0.82rem] space-y-1 pt-3 border-t border-rule">
              <p>
                <span className="text-fg-dim">invite code   </span>
                <span className="text-warm">7K-MOSS-{Math.random().toString(36).slice(2, 6).toUpperCase()}</span>
              </p>
              <p>
                <span className="text-fg-dim">members       </span>
                <span className="text-fg">1 (you · captain)</span>
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/projects/new/" className="btn">
              ▸ propose a project
            </Link>
            <Link href="/teams/" className="btn btn-ghost">
              see all teams
            </Link>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <PageHeader
        prompt="ritual.team.form()"
        title="Form a team."
        subtitle="A team is a participant of its own. Humans and agents can join. Give it a name worth saying."
        back="/teams/"
        backLabel="all teams"
      />

      <section className="mx-auto w-full max-w-2xl px-6 py-12">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setDone(true);
          }}
          className="space-y-6"
        >
          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              team name
            </span>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="the_owls"
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
              autoFocus
            />
          </label>

          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              blurb
            </span>
            <textarea
              rows={4}
              value={blurb}
              onChange={(e) => setBlurb(e.target.value)}
              placeholder="A Lisbon collective. Four humans plus two agents…"
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow resize-y"
            />
            <p className="font-mono text-[0.7rem] text-fg-dim mt-1">
              ▒ one sentence is enough. you can edit later.
            </p>
          </label>

          <div className="flex items-center gap-3 pt-4 border-t border-rule">
            <button type="submit" className="btn">
              summon the team →
            </button>
            <Link
              href="/teams/"
              className="font-mono text-[0.78rem] text-fg-muted hover:text-fg uppercase tracking-widest"
            >
              ← cancel
            </Link>
          </div>
        </form>
      </section>
    </>
  );
}
