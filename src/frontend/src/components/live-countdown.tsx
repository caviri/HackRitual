'use client';

import { useEffect, useState } from 'react';

interface Props {
  /** Seconds from "now" the target moment lies in the future. */
  secondsAhead: number;
  /** Short prefix shown above the digits. e.g. "forge closes in" */
  label: string;
  /** Visual emphasis — defaults to primary. */
  tone?: 'primary' | 'warm' | 'accent' | 'muted';
}

const TONE_CLASS: Record<NonNullable<Props['tone']>, string> = {
  primary: 'text-primary',
  warm: 'text-warm',
  accent: 'text-accent',
  muted: 'text-fg-muted',
};

function pad(n: number) {
  return String(Math.max(0, Math.floor(n))).padStart(2, '0');
}

export function LiveCountdown({ secondsAhead, label, tone = 'primary' }: Props) {
  const [remaining, setRemaining] = useState(secondsAhead);

  useEffect(() => {
    setRemaining(secondsAhead);
    const t = setInterval(() => setRemaining((r) => Math.max(0, r - 1)), 1000);
    return () => clearInterval(t);
  }, [secondsAhead]);

  const d = Math.floor(remaining / 86400);
  const h = Math.floor((remaining % 86400) / 3600);
  const m = Math.floor((remaining % 3600) / 60);
  const s = remaining % 60;

  return (
    <div
      className="inline-flex items-baseline gap-3 font-mono tabular-nums"
      role="timer"
      aria-live="polite"
    >
      <span className="text-[0.68rem] uppercase tracking-widest text-fg-dim">
        {label}
      </span>
      <span className={`text-[1.1rem] ${TONE_CLASS[tone]}`}>
        {d > 0 && (
          <>
            <span>{pad(d)}</span>
            <span className="text-fg-dim mx-1">d</span>
          </>
        )}
        <span>{pad(h)}</span>
        <span className="text-fg-dim mx-1">:</span>
        <span>{pad(m)}</span>
        <span className="text-fg-dim mx-1">:</span>
        <span className="opacity-80">{pad(s)}</span>
      </span>
    </div>
  );
}
