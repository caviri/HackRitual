'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '../../components/page-header';
import { api, type LogEntryDTO, type LogPageDTO } from '../../lib/api';

/** Predefined action filters — keeps the URL space discoverable. */
const ACTION_FACETS: { label: string; prefix?: string; glyph: string }[] = [
  { label: 'all', glyph: '◆' },
  { label: 'event', prefix: 'event.', glyph: '✺' },
  { label: 'user', prefix: 'user.', glyph: '·' },
  { label: 'participant', prefix: 'participant.', glyph: '◇' },
  { label: 'project', prefix: 'project.', glyph: '▰' },
  { label: 'submission', prefix: 'submission.', glyph: '▢' },
  { label: 'auth', prefix: 'auth.', glyph: '▒' },
];

/** Map action prefix → tone for the actor column / row glyph. */
function actionTone(action: string): { glyph: string; color: string } {
  if (action.startsWith('event.')) return { glyph: '✺', color: 'text-accent' };
  if (action.startsWith('user.admin')) return { glyph: '✦', color: 'text-accent' };
  if (action.startsWith('user.')) return { glyph: '·', color: 'text-fg-muted' };
  if (action.startsWith('participant.')) return { glyph: '◇', color: 'text-primary' };
  if (action.startsWith('project.')) return { glyph: '▰', color: 'text-warm' };
  if (action.startsWith('submission.')) return { glyph: '▢', color: 'text-primary' };
  if (action.startsWith('auth.')) return { glyph: '▒', color: 'text-fg-dim' };
  return { glyph: '·', color: 'text-fg-dim' };
}

function relativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  const s = Math.floor((Date.now() - t) / 1000);
  if (s < 5) return 'now';
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function actionPhrase(action: string): string {
  // Turn "event.transition" into "transitioned the event"
  // Best-effort prettifier — falls back to the raw action.
  const phrases: Record<string, string> = {
    'event.transition': 'moved the state machine',
    'user.admin_seeded': 'was seeded as admin',
    'user.role_changed': 'changed a role',
    'user.deactivated': 'was deactivated',
    'auth.login': 'entered the circle',
    'auth.code_requested': 'spoke their name',
    'auth.code_verified': 'crossed the gate',
    'participant.created': 'joined as a participant',
    'participant.updated': 'amended their record',
    'team.created': 'forged a team',
    'team.member_joined': 'joined a team',
    'project.proposed': 'proposed a project',
    'project.approved': 'approved a project',
    'project.rejected': 'rejected a project',
    'submission.created': 'submitted a version',
    'submission.finalized': 'sealed a submission',
  };
  return phrases[action] ?? action.replace(/^[^.]+\./, '').replace(/_/g, ' ');
}

export default function LogPage() {
  const [page, setPage] = useState<LogPageDTO | null>(null);
  const [busy, setBusy] = useState(false);
  const [actorFilter, setActorFilter] = useState('');
  const [activeAction, setActiveAction] = useState<string>('all');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [offset, setOffset] = useState(0);
  const limit = 50;
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    const facet = ACTION_FACETS.find((f) => f.label === activeAction);
    const result = await api.logPage({
      limit,
      offset,
      action_prefix: facet?.prefix,
      actor: actorFilter.trim() || undefined,
    });
    setPage(result);
    setBusy(false);
  }, [activeAction, actorFilter, offset]);

  useEffect(() => {
    void load();
  }, [load]);

  // Auto-refresh: every 8s if enabled and we're on page 0 with no filter
  useEffect(() => {
    if (!autoRefresh) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    timerRef.current = setInterval(() => {
      if (offset === 0) void load();
    }, 8000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [autoRefresh, offset, load]);

  function pickFacet(label: string) {
    setActiveAction(label);
    setOffset(0);
  }

  function submitActor(e: React.FormEvent) {
    e.preventDefault();
    setOffset(0);
    void load();
  }

  const entries = page?.entries ?? [];
  const total = page?.total ?? 0;

  return (
    <>
      <PageHeader
        prompt="ritual.log()"
        title="The Ritual Log"
        subtitle="Every gate, every commit, every word inscribed. The tail you see in the footer, expanded."
        chip={`${total} entries`}
        back="/"
        backLabel="back to circle"
      />

      <section className="mx-auto w-full max-w-5xl px-6 py-8">
        {/* facets */}
        <div className="flex flex-wrap gap-2 mb-4 font-mono text-[0.72rem] uppercase tracking-widest">
          {ACTION_FACETS.map((f) => {
            const active = f.label === activeAction;
            return (
              <button
                key={f.label}
                type="button"
                onClick={() => pickFacet(f.label)}
                className={`border px-3 py-1.5 transition-colors ${
                  active
                    ? 'border-primary text-primary'
                    : 'border-rule text-fg-muted hover:text-fg'
                }`}
              >
                <span aria-hidden className="mr-1.5 text-warm">{f.glyph}</span>
                {f.label}
              </button>
            );
          })}
        </div>

        {/* actor filter + auto-refresh toggle */}
        <div className="flex flex-wrap items-center gap-3 mb-8">
          <form onSubmit={submitActor} className="flex gap-2 flex-1 min-w-[260px]">
            <input
              type="text"
              value={actorFilter}
              onChange={(e) => setActorFilter(e.target.value)}
              placeholder="filter by actor (email or handle)…"
              className="flex-1 bg-bg-elev border border-rule text-fg font-mono px-3 py-1.5 text-[0.78rem] outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
            />
            <button
              type="submit"
              className="btn !py-1 !px-3 !text-[0.7rem] whitespace-nowrap"
            >
              filter
            </button>
          </form>
          <label className="inline-flex items-center gap-2 font-mono text-[0.7rem] uppercase tracking-widest text-fg-muted">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-primary"
            />
            tail -f (auto-refresh)
          </label>
        </div>

        {/* the feed */}
        <div className="ascii-frame overflow-hidden">
          <header className="flex items-center gap-2 px-4 py-2 border-b border-rule text-[0.7rem] font-mono uppercase tracking-widest text-fg-dim">
            <span className="text-primary" aria-hidden>◆</span>
            <span>ritual log</span>
            <span className="flex-1" />
            {busy && <span className="text-warm">… polling</span>}
            {!busy && page && (
              <span>{Math.min(offset + entries.length, total)} / {total}</span>
            )}
          </header>

          {entries.length === 0 ? (
            <p className="ritual text-fg-muted text-center py-10 px-4">
              The register is empty under this filter.
            </p>
          ) : (
            <ol>
              {entries.map((e, i) => (
                <LogRow key={e.id} entry={e} highlight={i === 0 && offset === 0 && autoRefresh} />
              ))}
            </ol>
          )}

          {/* paging */}
          <footer className="flex items-center gap-3 px-4 py-2 border-t border-rule font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
            <button
              type="button"
              disabled={offset === 0 || busy}
              onClick={() => setOffset(Math.max(0, offset - limit))}
              className="text-fg-muted hover:text-fg disabled:text-fg-dim"
            >
              ← newer
            </button>
            <span className="flex-1 text-center">
              {entries.length > 0 && (
                <>page {Math.floor(offset / limit) + 1}</>
              )}
            </span>
            <button
              type="button"
              disabled={offset + entries.length >= total || busy}
              onClick={() => setOffset(offset + limit)}
              className="text-fg-muted hover:text-fg disabled:text-fg-dim"
            >
              older →
            </button>
          </footer>
        </div>

        <p className="font-mono text-[0.66rem] text-fg-dim mt-4 leading-relaxed">
          ▒ this feed is what the footer ticker tails. the full audit log is
          exported in the FINAL/ARCHIVED bundle. <Link href="/admin/" className="text-primary hover:underline">admin</Link>{' '}
          can see entries with sensitive metadata.
        </p>
      </section>
    </>
  );
}

function LogRow({ entry, highlight }: { entry: LogEntryDTO; highlight?: boolean }) {
  const tone = actionTone(entry.action);
  return (
    <li
      className={`grid grid-cols-[auto_auto_1fr_auto] items-baseline gap-x-3 px-4 py-2 border-t border-rule first:border-t-0 font-mono text-[0.82rem] ${
        highlight ? 'animate-rise' : ''
      }`}
    >
      <span className="text-fg-dim tabular-nums">
        {new Date(entry.ts).toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        })}
      </span>
      <span className="inline-flex items-center gap-1.5 min-w-0">
        <span aria-hidden className={tone.color}>{tone.glyph}</span>
        {entry.actor ? (
          <Link
            href={`/participants/?actor=${encodeURIComponent(entry.actor)}`}
            className="text-fg-muted hover:text-primary truncate"
            title={entry.actor_id ?? ''}
          >
            {entry.actor}
          </Link>
        ) : (
          <span className="text-fg-dim">system</span>
        )}
      </span>
      <span className="text-fg truncate min-w-0">
        <span className="ritual">{actionPhrase(entry.action)}</span>
        {entry.target_type && (
          <>
            {' '}
            <span className="font-mono not-italic text-fg-dim text-[0.72rem]">
              ▸ {entry.target_type}
              {entry.target_id ? ` #${entry.target_id.slice(0, 6)}` : ''}
            </span>
          </>
        )}
        {entry.summary && (
          <>
            {' '}
            <span className="font-mono not-italic text-fg-muted text-[0.72rem]">
              · {entry.summary}
            </span>
          </>
        )}
      </span>
      <span className="text-fg-dim text-[0.7rem] uppercase tracking-widest whitespace-nowrap text-right">
        {relativeTime(entry.ts)}
      </span>
    </li>
  );
}
