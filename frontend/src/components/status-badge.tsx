type State = 'DRAFT' | 'OPEN' | 'FROZEN' | 'FINAL' | 'ARCHIVED';

const STATE_GLYPH: Record<State, string> = {
  DRAFT: '▒',
  OPEN: '◆',
  FROZEN: '◇',
  FINAL: '▰',
  ARCHIVED: '▢',
};

const STATE_PHRASE: Record<State, string> = {
  DRAFT: 'the circle is drawn',
  OPEN: 'the gates are open',
  FROZEN: 'the forge cools',
  FINAL: 'the verdict is inscribed',
  ARCHIVED: 'the ritual is sealed',
};

interface Props {
  state: State;
  phrase?: boolean;
  className?: string;
}

export function StatusBadge({ state, phrase = true, className = '' }: Props) {
  const live = state === 'OPEN';
  return (
    <span
      className={`inline-flex items-center gap-2 font-mono text-[0.72rem] uppercase tracking-widest ${className}`}
    >
      <span className="text-fg-dim">[</span>
      <span
        className={`${live ? 'text-primary animate-pulse-glow' : 'text-fg-muted'}`}
        aria-hidden
      >
        {STATE_GLYPH[state]}
      </span>
      <span className={live ? 'text-primary' : 'text-fg-muted'}>{state}</span>
      <span className="text-fg-dim">]</span>
      {phrase && (
        <span className="ritual text-fg-muted normal-case tracking-normal text-[0.95rem]">
          — {STATE_PHRASE[state]}
        </span>
      )}
    </span>
  );
}
