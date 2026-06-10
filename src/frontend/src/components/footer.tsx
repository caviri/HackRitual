'use client';

import { useEffect, useState } from 'react';
import { RitualLog } from './ritual-log';
import { ThemeSwitcher } from './theme-switcher';
import { getStageData, parseStageFromUrl, type LogEntry, type EventState } from '../lib/mocks';

const LOG_LABEL: Record<EventState, string> = {
  DRAFT: 'log · circle drawn',
  OPEN: 'log · the forge running',
  FROZEN: 'log · gates sealed',
  FINAL: 'log · verdict inscribed',
  ARCHIVED: 'log · record sealed',
};

export function Footer() {
  const [entries, setEntries] = useState<LogEntry[]>(getStageData('OPEN').ritualLog);
  const [state, setState] = useState<EventState>('OPEN');

  useEffect(() => {
    const s = parseStageFromUrl(window.location.search);
    setState(s);
    setEntries(getStageData(s).ritualLog);
  }, []);

  return (
    <footer className="border-t border-rule mt-32">
      <div className="mx-auto w-full max-w-6xl px-6 py-10 grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <div className="ascii-frame p-5">
          <RitualLog entries={entries} label={LOG_LABEL[state]} />
        </div>

        <div className="flex flex-col justify-between gap-6">
          <div className="font-mono text-[0.78rem] space-y-2 text-fg-muted">
            <div className="flex gap-3">
              <span className="text-fg-dim">$ ritual.info()</span>
            </div>
            <ul className="space-y-1 pl-3">
              <li>
                <span className="text-fg-dim">version  </span>
                <span className="text-fg">0.1.0</span>
              </li>
              <li>
                <span className="text-fg-dim">state    </span>
                <span className="text-primary">{state}</span>
              </li>
              <li>
                <span className="text-fg-dim">storage  </span>
                <span className="text-fg">/data/app.db</span>
              </li>
              <li>
                <span className="text-fg-dim">api      </span>
                <a href="/api/health" className="text-accent hover:underline">
                  /api/health ↗
                </a>
              </li>
              <li>
                <span className="text-fg-dim">handbook </span>
                <a href="/docs/" className="text-primary hover:underline">
                  the process ↗
                </a>
              </li>
              <li>
                <span className="text-fg-dim">api docs </span>
                <a href="/api/docs" className="text-primary hover:underline">
                  the spellbook ↗
                </a>
              </li>
              <li>
                <span className="text-fg-dim">privacy  </span>
                <a href="/privacy/" className="text-primary hover:underline">
                  what we remember ↗
                </a>
              </li>
              <li>
                <span className="text-fg-dim">source   </span>
                <span className="text-fg">single container · one ritual</span>
              </li>
            </ul>
          </div>

          <div className="flex items-end justify-between gap-4 pt-4 border-t border-rule">
            <p className="ritual text-fg-muted text-[0.95rem] max-w-xs">
              Forged from nothing. Exported as record. Dispelled when done.
            </p>
            <ThemeSwitcher />
          </div>
        </div>
      </div>
    </footer>
  );
}
