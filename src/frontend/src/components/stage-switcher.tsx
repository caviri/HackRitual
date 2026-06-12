'use client';

import { useEffect, useState } from 'react';
import { STATES, EventState, parseStageFromUrl } from '../lib/mocks';
import { api, currentDemoStage, setDemoStage } from '../lib/api';

const GLYPH: Record<EventState, string> = {
  DRAFT: '▒',
  OPEN: '◆',
  FROZEN: '◇',
  FINAL: '▰',
  ARCHIVED: '▢',
};

/**
 * Demo bar pinned to the top of every page.
 *
 * Shows in two situations:
 * - no live backend (pure-mock demo) — flips ?stage= and the mock datasets;
 * - DEMO_STAGES=true on the backend — flips the demo_stage cookie too, so
 *   every API call routes to that stage's own SQLite snapshot.
 */
export function StageSwitcher() {
  const [current, setCurrent] = useState<EventState>('OPEN');
  // null = probing; 'mock' = no backend; 'live-stages' = DEMO_STAGES backend;
  // 'hidden' = live single-DB backend.
  const [mode, setMode] = useState<'mock' | 'live-stages' | 'hidden' | null>(null);

  useEffect(() => {
    const chosen = currentDemoStage();
    setCurrent(
      chosen && (STATES as string[]).includes(chosen)
        ? (chosen as EventState)
        : parseStageFromUrl(window.location.search),
    );

    void api.health().then((h) => {
      if (h.demo_stages) setMode('live-stages');
      else if (h.event_id === 'demo' || !h.db_ok) setMode('mock');
      else setMode('hidden');
    });
  }, []);

  function go(s: EventState) {
    setDemoStage(s);
    const url = new URL(window.location.href);
    url.searchParams.set('stage', s);
    window.location.href = url.toString();
  }

  function goLive() {
    setDemoStage(null);
    const url = new URL(window.location.href);
    url.searchParams.delete('stage');
    // The stage hook pins ?stage= in sessionStorage — clear it too.
    try {
      sessionStorage.clear();
    } catch {
      /* ignore */
    }
    window.location.href = url.toString();
  }

  if (mode === null || mode === 'hidden') return null;

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
        {mode === 'live-stages' && (
          <button
            type="button"
            onClick={goLive}
            className="font-mono uppercase tracking-widest px-2 py-0.5 border border-transparent text-fg-muted hover:text-fg hover:border-rule-bright"
            title="leave the demo stages — back to the live event"
          >
            ✕ live
          </button>
        )}
        <span className="flex-1" />
        <span className="hidden md:inline ritual text-fg-muted normal-case text-[0.85rem]">
          {mode === 'live-stages'
            ? 'five states, five small worlds.'
            : 'five states, one container.'}
        </span>
      </div>
    </div>
  );
}
