'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '../../components/page-header';
import { api, type LeaderboardDTO, type MeDTO } from '../../lib/api';

const TYPE_GLYPH: Record<string, string> = {
  human: '☺',
  agent: '⚙',
  team: '◈',
};

const RANK_TONE = (rank: number) =>
  rank === 1
    ? 'text-primary'
    : rank === 2
      ? 'text-accent'
      : rank === 3
        ? 'text-warm'
        : 'text-fg-muted';

export default function LeaderboardPage() {
  const [board, setBoard] = useState<LeaderboardDTO | null>(null);
  const [me, setMe] = useState<MeDTO | null>(null);

  async function load() {
    const [b, m] = await Promise.all([api.leaderboard(), api.me()]);
    setBoard(b);
    setMe(m);
  }

  useEffect(() => {
    void load();
  }, []);

  // Auto-refresh while the gates are open — the standing is still moving.
  useEffect(() => {
    if (board?.event_state !== 'OPEN') return;
    const t = setInterval(() => void load(), 30_000);
    return () => clearInterval(t);
  }, [board?.event_state]);

  const entries = board?.entries ?? [];
  const isFinal =
    board?.event_state === 'FINAL' || board?.event_state === 'ARCHIVED';
  const myParticipantId = me?.participant?.id;

  const subtitle = isFinal
    ? 'The verdict is inscribed. These marks are final.'
    : board?.event_state === 'FROZEN'
      ? 'The forge has cooled. Scoring is underway; the order may yet shift.'
      : `Ranked by ${board?.leaderboard_mode ?? 'best'} score. Refreshes while the gates are open.`;

  return (
    <>
      <PageHeader
        prompt="ritual.leaderboard()"
        title="Leaderboard"
        subtitle={subtitle}
        chip={`${entries.length} ranked`}
      />

      <section className="mx-auto w-full max-w-4xl px-6 py-10">
        {isFinal && (
          <div className="ascii-frame mb-6 p-4 text-center">
            <p className="font-mono text-[0.72rem] uppercase tracking-widest text-primary">
              ◆ final results ◆
            </p>
          </div>
        )}

        {entries.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ leaderboard.entries() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No scored offerings yet. Ranks appear once the forge runs and the
              first marks are inscribed.
            </p>
          </div>
        ) : (
          <div className="ascii-frame overflow-x-auto">
            <table className="w-full font-mono text-[0.82rem]">
              <thead className="border-b border-rule bg-bg-elev">
                <tr className="text-[0.66rem] uppercase tracking-widest text-fg-dim">
                  <th className="text-right p-3 font-normal w-16">rank</th>
                  <th className="text-left p-3 font-normal">participant</th>
                  <th className="text-left p-3 font-normal">project</th>
                  <th className="text-right p-3 font-normal">offers</th>
                  <th className="text-right p-3 font-normal">score</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => {
                  const mine = e.participant.id === myParticipantId;
                  return (
                    <tr
                      key={e.participant.id}
                      className={`border-t border-rule transition-colors ${
                        mine ? 'bg-primary/10' : 'hover:bg-bg-elev/60'
                      }`}
                    >
                      <td
                        className={`p-3 text-right tabular-nums font-semibold ${RANK_TONE(e.rank)}`}
                      >
                        {e.rank}
                      </td>
                      <td className="p-3">
                        <span className="mr-2 text-fg-dim" aria-hidden>
                          {TYPE_GLYPH[e.participant.type] ?? '•'}
                        </span>
                        <Link
                          href={`/participant/?id=${e.participant.id}`}
                          className="text-fg hover:text-primary transition-colors"
                        >
                          {e.participant.display_name}
                        </Link>
                        {mine && (
                          <span className="ml-2 text-[0.62rem] uppercase tracking-widest text-primary">
                            you
                          </span>
                        )}
                      </td>
                      <td className="p-3">
                        {e.project ? (
                          <Link
                            href={`/project/?id=${e.project.id}`}
                            className="text-fg-muted hover:text-primary transition-colors"
                          >
                            {e.project.title}
                          </Link>
                        ) : (
                          <span className="text-fg-dim">—</span>
                        )}
                      </td>
                      <td className="p-3 text-right text-fg-dim tabular-nums">
                        {e.submission_count}
                      </td>
                      <td className="p-3 text-right tabular-nums text-accent">
                        {e.score.toFixed(1)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
