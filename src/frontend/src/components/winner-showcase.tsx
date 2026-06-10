import { AsciiDivider } from './ascii-divider';
import type { ProposalMock } from '../lib/mocks';

interface Props {
  winners: ProposalMock[];
}

const RANK_GLYPH = ['◆', '◇', '▰'];
const RANK_LABEL = ['first', 'second', 'third'];

export function WinnerShowcase({ winners }: Props) {
  return (
    <section className="mx-auto w-full max-w-6xl px-6 py-16">
      <AsciiDivider label="the named" glyph="◆" />

      <div className="grid gap-4 md:grid-cols-3">
        {winners.slice(0, 3).map((w, i) => {
          const tone = i === 0 ? 'border-accent' : i === 1 ? 'border-primary' : 'border-warm';
          const fontColor = i === 0 ? 'text-accent' : i === 1 ? 'text-primary' : 'text-warm';
          return (
            <article
              key={w.id}
              className={`ascii-frame p-6 border-l-2 ${tone} relative overflow-hidden`}
            >
              <div className={`absolute -right-3 -top-3 text-7xl ${fontColor} opacity-15 pointer-events-none select-none`}>
                {RANK_GLYPH[i] ?? '◆'}
              </div>

              <header className="flex items-center justify-between mb-4 relative">
                <span className={`font-mono uppercase tracking-widest text-[0.7rem] ${fontColor}`}>
                  {RANK_GLYPH[i]} {RANK_LABEL[i]}
                </span>
                {w.score && (
                  <span className="font-mono text-[0.78rem] tabular-nums text-fg-muted">
                    {w.score.toFixed(1)}
                  </span>
                )}
              </header>

              <h3 className="font-display italic text-2xl mb-2 text-fg relative">
                {w.title}
              </h3>
              <p className="font-mono text-[0.72rem] uppercase tracking-wider text-warm mb-3">
                [{w.track}]
              </p>
              <p className="text-fg-muted text-[0.85rem] leading-relaxed mb-4">
                {w.blurb}
              </p>
              <p className="font-mono text-[0.78rem] text-fg-dim">
                by <span className="text-fg">{w.proposer}</span>
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
