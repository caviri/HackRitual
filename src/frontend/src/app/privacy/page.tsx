'use client';

import { PageHeader } from '../../components/page-header';

export default function PrivacyPage() {
  return (
    <>
      <PageHeader
        prompt="ritual.privacy()"
        title="Privacy"
        subtitle="What the ritual remembers, and what it deliberately forgets."
      />

      <section className="mx-auto w-full max-w-2xl px-6 py-10 ritual text-fg-muted text-[1.02rem] leading-relaxed space-y-8">
        <div>
          <h2 className="font-display italic text-[1.5rem] text-fg mb-2">
            One cookie, session only
          </h2>
          <p>
            When you sign in, the ritual sets a single HTTP-only cookie that
            holds your session. It is not a tracker. It carries no advertising
            identity. It expires, and clearing it signs you out. There are no
            third-party cookies and no analytics beacons.
          </p>
        </div>

        <div>
          <h2 className="font-display italic text-[1.5rem] text-fg mb-2">
            What we collect
          </h2>
          <ul className="list-none space-y-2">
            <li>
              <span className="text-primary mr-2" aria-hidden>
                ◆
              </span>
              Your email address — to send login codes and event notices.
            </li>
            <li>
              <span className="text-primary mr-2" aria-hidden>
                ◆
              </span>
              What you create — your participant profile, teams, submissions,
              and scores.
            </li>
            <li>
              <span className="text-primary mr-2" aria-hidden>
                ◆
              </span>
              An audit trail of consequential admin actions, for accountability.
            </li>
          </ul>
        </div>

        <div>
          <h2 className="font-display italic text-[1.5rem] text-fg mb-2">
            What we do not do
          </h2>
          <p>
            No behavioural tracking, no fingerprinting, no selling of data, no
            sending your address to anyone. Email content and recipient
            addresses are never written to server logs — only aggregate counts.
          </p>
        </div>

        <div>
          <h2 className="font-display italic text-[1.5rem] text-fg mb-2">
            The export, and forgetting
          </h2>
          <p>
            When the ritual ends, the organiser may export a structured archive.
            In its public form, email addresses are reduced to a one-way hash —
            stable within the event, impossible to reverse. When the container
            is dispelled and its storage released, the record is gone with it.
          </p>
        </div>

        <p className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim pt-4 border-t border-rule">
          ▒ the ritual keeps only what the work requires
        </p>
      </section>
    </>
  );
}
