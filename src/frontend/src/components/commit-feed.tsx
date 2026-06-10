'use client';

import { useMemo } from 'react';
import { DitheredImage } from './dithered-image';
import type { CommitDTO } from '../lib/api';

interface Props {
  commits: CommitDTO[];
  /** When true, omit branch labels (e.g. inside a single-branch context). */
  hideBranch?: boolean;
  /** Limit how many to show. */
  limit?: number;
}

/** Relative time in a short ritual-flavored unit. */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const s = Math.floor((now - then) / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 14) return `${d}d ago`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function CommitFeed({ commits, hideBranch, limit }: Props) {
  const shown = useMemo(
    () => (limit ? commits.slice(0, limit) : commits),
    [commits, limit],
  );

  if (shown.length === 0) {
    return (
      <p className="ritual text-fg-muted text-[0.98rem]">
        Quiet. No commits observed yet.
      </p>
    );
  }

  return (
    <ol className="space-y-0">
      {shown.map((c, i) => (
        <li
          key={c.sha}
          className="grid grid-cols-[auto_auto_1fr_auto] gap-x-3 items-baseline py-2 border-t border-rule first:border-t-0"
          style={{ animationDelay: `${i * 30}ms` }}
        >
          {/* author avatar (dithered) or fallback glyph */}
          <span className="font-mono text-fg-dim text-[0.72rem] tabular-nums select-all">
            {c.sha_short}
          </span>
          <span className="inline-flex items-center gap-2 min-w-0">
            {c.author_avatar_url ? (
              <span
                className="w-5 h-5 shrink-0 overflow-hidden border border-rule"
                aria-hidden
              >
                <DitheredImage
                  src={c.author_avatar_url}
                  alt={c.author_login ?? c.author_name}
                  seed={c.author_login ?? c.author_name}
                  className="w-full h-full"
                  effect="dither"
                />
              </span>
            ) : (
              <span aria-hidden className="text-fg-dim">·</span>
            )}
            {c.author_profile_url ? (
              <a
                href={c.author_profile_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[0.78rem] text-fg-muted hover:text-primary truncate"
                title={c.author_name}
              >
                {c.author_login ?? c.author_name}
              </a>
            ) : (
              <span
                className="font-mono text-[0.78rem] text-fg-muted truncate"
                title={c.author_name}
              >
                {c.author_name}
              </span>
            )}
          </span>
          <span className="text-fg-muted text-[0.88rem] truncate">
            <span className="ritual text-fg">{c.message_first_line || '(no message)'}</span>
          </span>
          <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim text-right whitespace-nowrap">
            {!hideBranch && c.branch && (
              <span className="text-warm mr-2">{c.branch}</span>
            )}
            {relativeTime(c.committed_at)}
          </span>
        </li>
      ))}
    </ol>
  );
}
