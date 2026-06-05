'use client';

import { useEffect, useState } from 'react';
import { CommitFeed } from './commit-feed';
import { api, type CommitDTO } from '../lib/api';

interface Props {
  participantId: string;
  /** Heading for the section. Defaults to "evolution · recent commits". */
  heading?: string;
}

/**
 * Aggregated commit stream across every project a participant (or team)
 * has proposed. Pulls from `GET /api/feed/participant/{id}`.
 */
export function EvolutionStream({ participantId, heading }: Props) {
  const [commits, setCommits] = useState<CommitDTO[] | null>(null);

  useEffect(() => {
    void api.participantFeed(participantId).then(setCommits);
  }, [participantId]);

  return (
    <article>
      <header className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-display italic text-2xl text-fg">
          {heading ?? 'evolution · recent commits'}
        </h2>
        {commits && commits.length > 0 && (
          <span className="font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim">
            {commits.length} commits
          </span>
        )}
      </header>
      <div className="ascii-frame p-5">
        {commits === null ? (
          <p className="font-mono text-[0.78rem] text-fg-dim">summoning…</p>
        ) : (
          <CommitFeed commits={commits} limit={20} />
        )}
        {commits && commits.length === 0 && (
          <p className="font-mono text-[0.7rem] text-fg-dim mt-2 leading-relaxed">
            ▒ no repositories linked to this participant&apos;s projects yet. each
            project page has a &ldquo;repositories&rdquo; section where the
            evolution gets attached.
          </p>
        )}
      </div>
    </article>
  );
}
