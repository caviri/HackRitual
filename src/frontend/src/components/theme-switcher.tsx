'use client';

import { useEffect, useState } from 'react';
import { THEMES, ThemeId, applyTheme, readTheme } from '../lib/theme';

export function ThemeSwitcher() {
  const [theme, setTheme] = useState<ThemeId>('hacker-solarpunk');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const t = readTheme();
    setTheme(t);
    applyTheme(t);
  }, []);

  function choose(id: ThemeId) {
    setTheme(id);
    applyTheme(id);
    setOpen(false);
  }

  const current = THEMES.find((t) => t.id === theme) ?? THEMES[0];

  return (
    <div className="relative inline-block text-[0.72rem]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 font-mono uppercase tracking-widest text-fg-muted hover:text-fg transition-colors"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="text-fg-dim">theme:</span>
        <span>{current.label}</span>
        <span aria-hidden className="text-fg-dim">{open ? '▴' : '▾'}</span>
      </button>
      {open && (
        <ul
          role="listbox"
          className="absolute right-0 bottom-full mb-2 w-72 ascii-frame z-50 animate-rise"
        >
          {THEMES.map((t) => (
            <li key={t.id} role="option" aria-selected={t.id === theme}>
              <button
                type="button"
                onClick={() => choose(t.id)}
                className={`w-full flex flex-col gap-0.5 px-4 py-3 text-left transition-colors hover:bg-bg-elev ${
                  t.id === theme ? 'text-primary' : 'text-fg'
                }`}
              >
                <span className="font-mono lowercase tracking-wider">
                  {t.id === theme ? '▸ ' : '  '}
                  {t.label}
                </span>
                <span className="ritual text-fg-muted normal-case text-[0.95rem]">
                  {t.hint}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
