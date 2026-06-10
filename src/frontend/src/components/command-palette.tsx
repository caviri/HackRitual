'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CMS_PAGES,
  getStageData,
  parseStageFromUrl,
  type StageData,
} from '../lib/mocks';

interface Item {
  kind: 'project' | 'team' | 'participant' | 'page' | 'route';
  label: string;
  sublabel: string;
  href: string;
  glyph: string;
}

const ROUTE_ITEMS: Item[] = [
  { kind: 'route', label: 'overview', sublabel: 'your participation', href: '/overview/', glyph: '▰' },
  { kind: 'route', label: 'projects', sublabel: 'browse the forged', href: '/projects/', glyph: '◆' },
  { kind: 'route', label: 'teams', sublabel: 'the circles', href: '/teams/', glyph: '◇' },
  { kind: 'route', label: 'participants', sublabel: 'humans, agents, teams', href: '/participants/', glyph: '·' },
  { kind: 'route', label: 'submissions', sublabel: 'versioned snapshots', href: '/submissions/', glyph: '▒' },
  { kind: 'route', label: 'timeline', sublabel: 'the phases', href: '/timeline/', glyph: '▢' },
  { kind: 'route', label: 'admin', sublabel: "the keeper's console", href: '/admin/', glyph: '✦' },
  { kind: 'route', label: 'propose a project', sublabel: 'new', href: '/projects/new/', glyph: '◆' },
  { kind: 'route', label: 'form a team', sublabel: 'new', href: '/teams/new/', glyph: '◇' },
];

const KIND_TONE: Record<Item['kind'], string> = {
  project: 'text-primary',
  team: 'text-primary',
  participant: 'text-fg-muted',
  page: 'text-warm',
  route: 'text-accent',
};

/** Tiny fuzzy match — returns 0 = no match, higher = better. */
function score(haystack: string, needle: string): number {
  if (!needle) return 1;
  const h = haystack.toLowerCase();
  const n = needle.toLowerCase();
  if (h === n) return 1000;
  if (h.startsWith(n)) return 500;
  if (h.includes(n)) return 200;
  // sub-sequence match
  let hi = 0;
  let ni = 0;
  while (hi < h.length && ni < n.length) {
    if (h[hi] === n[ni]) ni++;
    hi++;
  }
  return ni === n.length ? 50 : 0;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const [stage, setStage] = useState<StageData>(getStageData('OPEN'));
  const input = useRef<HTMLInputElement | null>(null);

  // Hydrate stage data once on mount.
  useEffect(() => {
    setStage(getStageData(parseStageFromUrl(window.location.search)));
  }, []);

  // Keyboard listener — Cmd-K / Ctrl-K toggles; Esc closes.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === 'Escape') {
        setOpen(false);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery('');
      setCursor(0);
      setTimeout(() => input.current?.focus(), 30);
    }
  }, [open]);

  const items: Item[] = useMemo(() => {
    const all: Item[] = [
      ...ROUTE_ITEMS,
      ...stage.proposals.map<Item>((p) => ({
        kind: 'project',
        label: p.title,
        sublabel: `#${String(p.id).padStart(3, '0')} · ${p.track}`,
        href: `/projects/${p.id}/`,
        glyph: '◆',
      })),
      ...stage.teams.map<Item>((t) => ({
        kind: 'team',
        label: t.name,
        sublabel: `team · ${t.members.length} members`,
        href: `/teams/${t.handle}/`,
        glyph: '◇',
      })),
      ...stage.participants.map<Item>((p) => ({
        kind: 'participant',
        label: p.displayName ?? p.handle,
        sublabel: `[${p.kind}] · ${p.affiliation ?? p.meta}`,
        href: `/participants/${p.handle}/`,
        glyph: '·',
      })),
      ...Object.values(CMS_PAGES).map<Item>((p) => ({
        kind: 'page',
        label: p.title,
        sublabel: `page · ${p.blurb}`,
        href: `/pages/${p.slug}/`,
        glyph: '▰',
      })),
    ];
    if (!query) return all.slice(0, 16);
    return all
      .map((it) => ({ it, s: Math.max(score(it.label, query), score(it.sublabel, query) - 5) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 16)
      .map((x) => x.it);
  }, [stage, query]);

  const choose = useCallback((href: string) => {
    setOpen(false);
    window.location.href = href;
  }, []);

  function onInputKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setCursor((c) => Math.min(items.length - 1, c + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setCursor((c) => Math.max(0, c - 1));
    } else if (e.key === 'Enter' && items[cursor]) {
      e.preventDefault();
      choose(items[cursor].href);
    }
  }

  if (!open) {
    return (
      <div className="fixed bottom-3 right-3 z-40 pointer-events-none">
        <span className="hidden md:inline-flex items-center gap-1.5 font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim bg-bg/70 backdrop-blur-sm border border-rule px-2 py-1 pointer-events-auto">
          <kbd className="font-mono text-[0.6rem] border border-rule px-1">⌘</kbd>
          <kbd className="font-mono text-[0.6rem] border border-rule px-1">K</kbd>
          summon
        </span>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-24 bg-bg/85 backdrop-blur-sm animate-rise"
      role="dialog"
      aria-modal="true"
      onClick={() => setOpen(false)}
    >
      <div
        className="ascii-frame w-full max-w-xl bg-bg-elev overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-rule px-4 py-3 flex items-center gap-3">
          <span className="text-primary font-mono" aria-hidden>▸</span>
          <input
            ref={input}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setCursor(0);
            }}
            onKeyDown={onInputKey}
            placeholder="search projects, teams, people, pages…"
            className="flex-1 bg-transparent outline-none font-mono text-[0.95rem] text-fg placeholder:text-fg-dim"
          />
          <kbd className="font-mono text-[0.6rem] text-fg-dim border border-rule px-1">esc</kbd>
        </div>

        <ul className="max-h-[60vh] overflow-y-auto">
          {items.length === 0 ? (
            <li className="px-4 py-6 ritual text-fg-muted text-center">
              Nothing in the circle goes by that name.
            </li>
          ) : (
            items.map((it, i) => (
              <li
                key={it.href}
                onMouseEnter={() => setCursor(i)}
                onClick={() => choose(it.href)}
                className={`flex items-baseline gap-3 px-4 py-2.5 cursor-pointer font-mono text-[0.85rem] ${
                  cursor === i ? 'bg-bg/40' : ''
                }`}
              >
                <span aria-hidden className={`${KIND_TONE[it.kind]} w-4 text-center`}>
                  {it.glyph}
                </span>
                <span className={`${cursor === i ? 'text-primary' : 'text-fg'}`}>
                  {it.label}
                </span>
                <span className="text-fg-dim text-[0.72rem] truncate flex-1">
                  {it.sublabel}
                </span>
                <span className="font-mono text-[0.62rem] uppercase tracking-widest text-fg-dim">
                  {it.kind}
                </span>
              </li>
            ))
          )}
        </ul>

        <footer className="border-t border-rule px-4 py-2 flex items-center gap-3 font-mono text-[0.62rem] text-fg-dim uppercase tracking-widest">
          <span>
            <kbd className="border border-rule px-1 mr-1">↑↓</kbd> navigate
          </span>
          <span>
            <kbd className="border border-rule px-1 mr-1">↵</kbd> open
          </span>
          <span>
            <kbd className="border border-rule px-1 mr-1">esc</kbd> close
          </span>
          <span className="flex-1" />
          <span>cmd-k from anywhere</span>
        </footer>
      </div>
    </div>
  );
}
