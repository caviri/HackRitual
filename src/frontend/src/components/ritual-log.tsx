'use client';

/**
 * Ritual Log — the showpiece of the chrome.
 *
 * A tailing syslog-style log of events, but the messages are written in
 * EB Garamond italic, like a liturgy. Terminal meets incantation.
 *
 * Entries are passed in from the current stage dataset so the log itself
 * tells the story of the ritual: whispers in DRAFT, clatter in OPEN,
 * hush in FROZEN, procession in FINAL, silence in ARCHIVED.
 */

import { useEffect, useState } from 'react';
import type { LogEntry } from '../lib/mocks';

interface Props {
  entries: LogEntry[];
  /** Override the header label — defaults to "ritual log". */
  label?: string;
}

export function RitualLog({ entries, label = 'ritual log' }: Props) {
  const [visible, setVisible] = useState(1);

  // Stagger-reveal on mount so the log feels alive on every page load.
  useEffect(() => {
    setVisible(1);
    const t = setInterval(() => {
      setVisible((v) => {
        if (v >= entries.length) {
          clearInterval(t);
          return v;
        }
        return v + 1;
      });
    }, 280);
    return () => clearInterval(t);
  }, [entries]);

  return (
    <div className="font-mono text-[0.78rem] leading-relaxed">
      <div className="flex items-center gap-2 mb-2 text-fg-dim uppercase tracking-widest text-[0.7rem]">
        <a
          href="/log/"
          className="inline-flex items-center gap-2 hover:text-primary transition-colors"
          aria-label="open the full ritual log"
        >
          <span className="text-primary" aria-hidden>◆</span>
          <span>{label}</span>
        </a>
        <span className="flex-1 h-px bg-rule" />
        <a
          href="/log/"
          className="text-fg-dim hover:text-primary transition-colors inline-flex items-center gap-1"
        >
          <span>expand</span>
          <span aria-hidden>↗</span>
        </a>
      </div>
      <ul className="space-y-1">
        {entries.slice(0, visible).map((e, i) => (
          <li
            key={`${e.ts}-${i}`}
            className="grid grid-cols-[auto_auto_1fr] gap-x-3 animate-rise"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <span className="text-fg-dim tabular-nums">{e.ts}</span>
            <span
              className={
                e.tone === 'primary'
                  ? 'text-primary'
                  : e.tone === 'warm'
                  ? 'text-warm'
                  : e.tone === 'accent'
                  ? 'text-accent'
                  : 'text-fg-muted'
              }
            >
              {e.actor}
            </span>
            <span className="ritual text-fg">
              {e.verb}
              {e.object && (
                <>
                  {' '}
                  <span className="font-mono not-italic text-fg-muted">{e.object}</span>
                </>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
