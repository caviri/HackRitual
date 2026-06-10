'use client';

/**
 * Persistent settings stored in localStorage.
 *
 * Today: image effect (default treatment applied to uploads + placeholders).
 * Tomorrow: anything else that should survive across pages without round-tripping
 * through the server.
 */

export type ImageEffect = 'none' | 'dither' | 'halftone';

export const IMAGE_EFFECTS: { id: ImageEffect; label: string; blurb: string }[] = [
  {
    id: 'dither',
    label: 'dither',
    blurb: 'two-tone ordered noise — terminal, pixelated, low-bandwidth.',
  },
  {
    id: 'halftone',
    label: 'halftone',
    blurb: 'newsprint dot grid — solid, ink-on-paper, archival.',
  },
  {
    id: 'none',
    label: 'none',
    blurb: 'pass through — keep the original pixels untouched.',
  },
];

interface Settings {
  imageEffect: ImageEffect;
}

const DEFAULTS: Settings = {
  imageEffect: 'dither',
};

const STORAGE_KEY = 'hackritual:settings';

export function readSettings(): Settings {
  if (typeof window === 'undefined') return DEFAULTS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw) as Partial<Settings>;
    return { ...DEFAULTS, ...parsed };
  } catch {
    return DEFAULTS;
  }
}

export function writeSettings(s: Partial<Settings>) {
  if (typeof window === 'undefined') return;
  const merged = { ...readSettings(), ...s };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  // Notify other components on this page (settings panel can update previews).
  window.dispatchEvent(new CustomEvent('hackritual:settings', { detail: merged }));
}

export function defaultImageEffect(): ImageEffect {
  return readSettings().imageEffect;
}
