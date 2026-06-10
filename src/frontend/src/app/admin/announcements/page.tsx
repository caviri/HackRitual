'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import { api, ApiError, type AnnouncementDTO } from '../../../lib/api';

export default function AnnouncementsPage() {
  const [rows, setRows] = useState<AnnouncementDTO[]>([]);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api
      .adminAnnouncements()
      .then(setRows)
      .catch((err) => {
        if (err instanceof ApiError) setError(err.body || `load failed (${err.status})`);
      });
  }, []);

  async function publish(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.createAnnouncement({
        title: title.trim(),
        body: body.trim(),
      });
      setRows((prev) => [created, ...prev]);
      setTitle('');
      setBody('');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.body || `publish failed (${err.status})`);
      } else {
        setError(String(err));
      }
    } finally {
      setBusy(false);
    }
  }

  async function toggle(a: AnnouncementDTO) {
    setBusyId(a.id);
    setError(null);
    try {
      const updated = await api.updateAnnouncement(a.id, { visible: !a.visible });
      setRows((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      if (err instanceof ApiError) setError(err.body || `update failed (${err.status})`);
    } finally {
      setBusyId(null);
    }
  }

  async function remove(a: AnnouncementDTO) {
    if (!confirm(`Remove the dispatch "${a.title}"?`)) return;
    setBusyId(a.id);
    setError(null);
    try {
      await api.deleteAnnouncement(a.id);
      setRows((prev) => prev.filter((x) => x.id !== a.id));
    } catch (err) {
      if (err instanceof ApiError) setError(err.body || `delete failed (${err.status})`);
    } finally {
      setBusyId(null);
    }
  }

  const visibleCount = rows.filter((r) => r.visible).length;

  return (
    <>
      <PageHeader
        prompt="ritual.admin.announcements()"
        title="Dispatches"
        subtitle="Short news from the keeper, shown under the homepage hero. The section hides itself when nothing is published."
        chip={`${visibleCount} visible`}
      />

      <section className="mx-auto w-full max-w-4xl px-6 py-8 space-y-8">
        {/* composer */}
        <form onSubmit={publish} className="ascii-frame p-5 space-y-4">
          <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
            write a dispatch
          </p>
          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              title
            </span>
            <input
              type="text"
              required
              maxLength={200}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="The gates open at nine"
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-2.5 outline-none focus:border-primary transition-colors"
            />
          </label>
          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              body
            </span>
            <textarea
              required
              rows={4}
              maxLength={4000}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Say it plainly. The gathered will read it on the front page."
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-2.5 outline-none focus:border-primary transition-colors resize-y"
            />
          </label>
          {error && (
            <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
              ✕ {error}
            </p>
          )}
          <button type="submit" className="btn" disabled={busy}>
            {busy ? 'inscribing…' : '◆ publish dispatch'}
          </button>
        </form>

        {/* list */}
        {rows.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ announcements.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem]">
              nothing published yet. the front page holds its silence.
            </p>
          </div>
        ) : (
          <ul className="space-y-4">
            {rows.map((a) => (
              <li key={a.id} className={`ascii-frame p-4 ${a.visible ? '' : 'opacity-60'}`}>
                <header className="flex flex-wrap items-baseline justify-between gap-3 mb-1.5">
                  <h2 className="font-display italic text-xl text-fg">{a.title}</h2>
                  <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                    {new Date(a.created_at).toLocaleString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                    {' · '}
                    <span className={a.visible ? 'text-primary' : 'text-warm'}>
                      {a.visible ? '◆ visible' : '▒ hidden'}
                    </span>
                  </span>
                </header>
                <p className="text-fg-muted text-[0.9rem] leading-relaxed whitespace-pre-line mb-3">
                  {a.body}
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busyId === a.id}
                    onClick={() => void toggle(a)}
                    className="btn btn-ghost !px-3 !py-1 font-mono text-[0.72rem] uppercase tracking-widest"
                  >
                    {a.visible ? '▒ hide' : '◆ show'}
                  </button>
                  <button
                    type="button"
                    disabled={busyId === a.id}
                    onClick={() => void remove(a)}
                    className="btn btn-ghost !px-3 !py-1 font-mono text-[0.72rem] uppercase tracking-widest !text-danger"
                  >
                    ✕ remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
