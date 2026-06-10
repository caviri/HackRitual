'use client';

export type ThemeId = 'hacker-solarpunk' | 'paper-grimoire';

export const THEMES: { id: ThemeId; label: string; hint: string }[] = [
  {
    id: 'hacker-solarpunk',
    label: 'hacker-solarpunk',
    hint: 'a terminal that grew lichens',
  },
  {
    id: 'paper-grimoire',
    label: 'paper-grimoire',
    hint: 'iron-gall ink on cream rag',
  },
];

const STORAGE_KEY = 'hackritual:theme';

export function readTheme(): ThemeId {
  if (typeof window === 'undefined') return 'hacker-solarpunk';
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === 'hacker-solarpunk' || stored === 'paper-grimoire') return stored;
  return 'hacker-solarpunk';
}

export function applyTheme(id: ThemeId) {
  if (typeof window === 'undefined') return;
  document.documentElement.setAttribute('data-theme', id);
  window.localStorage.setItem(STORAGE_KEY, id);
}
