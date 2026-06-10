'use client';

import { useEffect, useState } from 'react';
import {
  getStageData,
  parseStageFromUrl,
  STATES,
  type EventState,
  type StageData,
} from './mocks';
import { api } from './api';

/**
 * Shared hook — returns the active StageData.
 *
 * Resolution order on every mount:
 *   1. URL ?stage=… (demo override) — applied always, cached so subsequent
 *      pages within the same tab keep the demo state without re-fetching.
 *   2. In-memory + sessionStorage cache — used synchronously in the
 *      useState initializer so subsequent navigations show the right
 *      content from the FIRST paint (no flash from a stale OPEN default).
 *   3. /api/event — fetched in the background to refresh the cache.
 *
 * If the API reports a different state than the cached one, the page
 * re-renders. If it matches, no visible change.
 */

const CACHE_KEY = 'hackritual:stage';
let memCache: EventState | null = null;
let memTitle: string | null = null;

function readCache(): { state: EventState; title: string | null } | null {
  if (typeof window === 'undefined') return null;
  if (memCache) return { state: memCache, title: memTitle };
  try {
    const raw = window.sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { state?: string; title?: string };
    if (parsed.state && (STATES as readonly string[]).includes(parsed.state)) {
      memCache = parsed.state as EventState;
      memTitle = parsed.title ?? null;
      return { state: memCache, title: memTitle };
    }
  } catch {
    /* ignore parse errors */
  }
  return null;
}

function writeCache(state: EventState, title: string | null) {
  memCache = state;
  memTitle = title;
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(CACHE_KEY, JSON.stringify({ state, title }));
  } catch {
    /* quota / safari private mode — best-effort */
  }
}

function applyTitle(base: StageData, title: string | null): StageData {
  if (!title) return base;
  return {
    ...base,
    hero: { ...base.hero, titleBottom: title },
  };
}

export function useStage(): StageData {
  // Synchronous initial value: prefer URL override > cache > OPEN default.
  // This is what kills the flash — by the time React paints the first
  // frame, we already have the right dataset selected.
  const [data, setData] = useState<StageData>(() => {
    if (typeof window === 'undefined') return getStageData('OPEN');
    const params = new URLSearchParams(window.location.search);
    const override = params.get('stage');
    if (override) {
      const s = parseStageFromUrl(window.location.search);
      const cached = readCache();
      return applyTitle(getStageData(s), cached?.title ?? null);
    }
    const cached = readCache();
    if (cached) return applyTitle(getStageData(cached.state), cached.title);
    return getStageData('OPEN');
  });

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      // URL override pinned the state — cache it and stop.
      const params = new URLSearchParams(window.location.search);
      const override = params.get('stage');
      if (override) {
        const s = parseStageFromUrl(window.location.search);
        writeCache(s, memTitle); // keep current title if known
        return;
      }
      // Otherwise consult the backend.
      const event = await api.event();
      if (cancelled || !event) return;
      const title = event.title ?? null;
      writeCache(event.state, title);
      setData((prev) => {
        // Avoid an unnecessary re-render if nothing material changed.
        if (
          prev.state === event.state &&
          prev.hero.titleBottom === (title ?? prev.hero.titleBottom)
        ) {
          return prev;
        }
        return applyTitle(getStageData(event.state), title);
      });
    }

    void refresh();
    return () => {
      cancelled = true;
    };
  }, []);

  return data;
}

/** Reachability probe — used by forms to decide between live API and demo mode. */
export async function backendAvailable(): Promise<boolean> {
  try {
    const h = await api.health();
    return h.db_ok === true && h.event_id !== 'demo';
  } catch {
    return false;
  }
}
