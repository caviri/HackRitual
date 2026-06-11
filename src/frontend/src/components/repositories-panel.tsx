'use client';

import { useEffect, useState } from 'react';
import { CommitFeed } from './commit-feed';
import { api, ApiError, type RepoDTO } from '../lib/api';

interface Props {
  projectId: string;
}

export function RepositoriesPanel({ projectId }: Props) {
  const [repos, setRepos] = useState<RepoDTO[] | null>(null);
  const [canEdit, setCanEdit] = useState(false);
  const [busy, setBusy] = useState(false);
  const [newUrl, setNewUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  useEffect(() => {
    void api.projectRepos(projectId).then((res) => {
      setRepos(res.repositories);
      setCanEdit(res.can_edit);
    });
  }, [projectId]);

  async function attach(e: React.FormEvent) {
    e.preventDefault();
    if (!newUrl.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const repo = await api.attachRepo(projectId, newUrl.trim());
      setRepos((prev) => [...(prev ?? []), repo]);
      setNewUrl('');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.body || `attach failed (${err.status})`);
      } else {
        setError('attach failed — backend unreachable?');
      }
    } finally {
      setBusy(false);
    }
  }

  async function refresh(repo: RepoDTO) {
    setRefreshingId(repo.id);
    try {
      const updated = await api.refreshRepo(projectId, repo.id);
      setRepos((prev) =>
        (prev ?? []).map((r) => (r.id === updated.id ? updated : r)),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.body : String(err));
    } finally {
      setRefreshingId(null);
    }
  }

  async function detach(repo: RepoDTO) {
    if (!confirm(`Detach ${repo.owner}/${repo.repo}? Cached commits will be discarded.`)) return;
    setBusy(true);
    try {
      await api.detachRepo(projectId, repo.id);
      setRepos((prev) => (prev ?? []).filter((r) => r.id !== repo.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.body : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="ascii-frame p-6">
      <header className="flex items-baseline justify-between gap-3 mb-3">
        <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
          repositories · the evolution
        </p>
        {repos && repos.length > 0 && (
          <span className="font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim">
            {repos.length} linked
          </span>
        )}
      </header>

      {repos === null ? (
        <p className="font-mono text-[0.78rem] text-fg-dim">summoning…</p>
      ) : repos.length === 0 ? (
        <p className="ritual text-fg-muted text-[1rem] mb-4">
          No repositories linked yet.{' '}
          {canEdit ? 'Paste a GitHub URL below to start tracking' : "The project's participant can link one to start tracking"}
          the project&apos;s commits — branches, messages, contributors all
          visible in one stream.
        </p>
      ) : (
        <ul className="space-y-6 mb-6">
          {repos.map((r) => (
            <li key={r.id} className="border-t border-rule pt-4 first:border-t-0 first:pt-0">
              <header className="flex flex-wrap items-baseline justify-between gap-3 mb-2">
                <div className="min-w-0 flex-1">
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-[0.92rem] text-fg hover:text-primary truncate inline-block max-w-full"
                  >
                    {r.owner}/{r.repo}
                  </a>
                  {r.description && (
                    <p className="text-fg-muted text-[0.82rem] mt-1 leading-snug">
                      {r.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim">
                  {r.default_branch && (
                    <span><span className="text-fg-dim">branch </span><span className="text-warm">{r.default_branch}</span></span>
                  )}
                  {r.stars != null && (
                    <span>· <span className="text-fg">{r.stars}</span> ★</span>
                  )}
                </div>
              </header>

              {r.polling_error ? (
                <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.72rem] text-danger mb-3">
                  ✕ {r.polling_error}
                </p>
              ) : null}

              <CommitFeed commits={r.commits} limit={10} />

              <footer className="mt-3 flex items-center gap-3 font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                {canEdit && (
                  <button
                    type="button"
                    disabled={refreshingId === r.id || busy}
                    onClick={() => refresh(r)}
                    className="text-fg-muted hover:text-primary transition-colors"
                  >
                    {refreshingId === r.id ? '↻ polling…' : '↻ refresh'}
                  </button>
                )}
                {canEdit && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => detach(r)}
                    className="text-fg-muted hover:text-danger transition-colors"
                  >
                    ✕ detach
                  </button>
                )}
                <span className="flex-1" />
                {r.last_polled_at && (
                  <span>polled {new Date(r.last_polled_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
                )}
              </footer>
            </li>
          ))}
        </ul>
      )}

      {/* attach form — the project's own people (or the keeper) only */}
      {!canEdit && (repos?.length ?? 0) === 0 && (
        <p className="font-mono text-[0.72rem] text-fg-dim mt-2">
          ▒ only the project&apos;s participant may link repositories.
        </p>
      )}
      {canEdit && (
      <form onSubmit={attach} className="flex flex-col sm:flex-row gap-2 mt-2">
        <input
          type="url"
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="flex-1 bg-bg-elev border border-rule text-fg font-mono px-3 py-2 text-[0.85rem] outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
        />
        <button
          type="submit"
          disabled={busy || !newUrl.trim()}
          className="btn !py-1.5 !px-3 !text-[0.72rem] whitespace-nowrap"
        >
          ◆ link repo
        </button>
      </form>
      )}
      {error && (
        <p className="ascii-frame !border-danger px-3 py-2 mt-3 font-mono text-[0.72rem] text-danger">
          ✕ {error}
        </p>
      )}
      <p className="font-mono text-[0.66rem] text-fg-dim mt-2 leading-relaxed">
        ▒ public github repos only · commits cached locally · refreshes on every page load
        (TTL 5 min) · authors link to their profile.
      </p>
    </article>
  );
}
