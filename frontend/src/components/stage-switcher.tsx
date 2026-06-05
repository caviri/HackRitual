'use client';

import { useEffect, useState } from 'react';
import { STATES, EventState, parseStageFromUrl } from '../lib/mocks';

const GLYPH: Record<EventState, string> = {
  DRAFT: '▒',
  OPEN: '◆',
  FROZEN: '◇',
  FINAL: '▰',
  ARCHIVED: '▢',
};

/**
 * Demo-mode bar pinned to the top of every page during the proposal phase.
 * Flips the ?stage= query param and reloads — keeps the URL shareable, so
 * any stage screenshot or tunnel link is reproducible.
 */
export function StageSwitcher() {
  const [current, setCurrent] = useState<EventState>('OPEN');

  useEffect(() => {
    setCurrent(parseStageFromUrl(window.location.search));
  }, []);

  function go(s: EventState) {
    const url = new URL(window.location.href);
    url.searchParams.set('stage', s);
    window.location.href = url.toString();
  }

  return (
    <div className="bg-bg-elev border-b border-rule text-[0.68rem]">
      <div className="mx-auto w-full max-w-6xl px-6 py-1.5 flex items-center gap-2 flex-wrap">
        <span className="font-mono uppercase tracking-widest text-fg-dim mr-1">
          <span className="text-warm">▸</span> demo · stage:
        </span>
        {STATES.map((s) => {
          const active = s === current;
          return (
            <button
              key={s}
              type="button"
              onClick={() => go(s)}
              className={`font-mono uppercase tracking-widest px-2 py-0.5 transition-colors border ${
                active
                  ? 'border-primary text-primary'
                  : 'border-transparent text-fg-muted hover:text-fg hover:border-rule-bright'
              }`}
              aria-pressed={active}
            >
              <span aria-hidden className="mr-1">{GLYPH[s]}</span>
              {s.toLowerCase()}
            </button>
          );
        })}
        <span className="flex-1" />
        <span className="hidden md:inline ritual text-fg-muted normal-case text-[0.85rem]">
          five states, one container.
        </span>
      </div>
    </div>
  );
}
