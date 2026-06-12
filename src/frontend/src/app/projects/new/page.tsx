'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '../../../components/page-header';
import { api, ApiError, type TrackDTO } from '../../../lib/api';

export default function NewProjectPage() {
  const [tracks, setTracks] = useState<TrackDTO[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [trackId, setTrackId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ id: string; title: string } | null>(null);

  const [participantId, setParticipantId] = useState<string | null>(null);

  useEffect(() => {
    void api.tracks().then(setTracks);
    void api.me().then((m) => setParticipantId(m?.participant?.id ?? null));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title || !description) {
      setError('a title and description are required.');
      return;
    }
    setError(null);
    setBusy(true);
    try {
      if (!participantId) {
        // Live backend but no participant on the session yet.
        const live = await import('../../../lib/api').then((m) => m.backendPresent());
        if (live) {
          setError('sign in first — proposals are bound to your participant.');
          setBusy(false);
          return;
        }
      }
      const result = await api.createProject({
        title,
        description,
        track_id: trackId || undefined,
        proposed_by_participant_id: participantId ?? 'demo-participant',
      });
      setCreated({ id: result.id, title: result.title });
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setError('you must be signed in (with your own participant) to propose.');
      } else if (err instanceof ApiError) {
        setError(err.body || `proposal failed (${err.status})`);
      } else {
        // Network unavailable — demo mode success
        setCreated({ id: 'demo-' + Date.now(), title });
      }
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <>
        <PageHeader
          prompt="ritual.project.proposed()"
          title="It has been proposed."
          subtitle="The proposal is now in the circle. Admins will review and approve."
        />
        <section className="mx-auto w-full max-w-2xl px-6 py-12">
          <div className="ascii-frame p-6 mb-6 font-mono text-[0.85rem]">
            <p className="text-primary mb-2">▸ accepted</p>
            <p className="text-fg-muted leading-relaxed">
              <span className="text-fg">{created.title}</span> is now visible to all
              participants under <Link href="/projects/" className="text-primary hover:underline">/projects/</Link>.
              Its status begins as <span className="text-warm">proposed</span> and moves to <span className="text-primary">approved</span> once an admin signs off.
            </p>
          </div>
          <div className="flex gap-3">
            <Link href="/projects/" className="btn">
              ▸ see all projects
            </Link>
            <Link href="/projects/new/" className="btn btn-ghost">
              propose another
            </Link>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <PageHeader
        prompt="ritual.project.propose()"
        title="Propose a project."
        subtitle="What do you want to build? Speak it plainly. Others will gather around it."
        back="/projects/"
        backLabel="all projects"
      />

      <section className="mx-auto w-full max-w-2xl px-6 py-12">
        <form onSubmit={submit} className="space-y-6">
          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              title
            </span>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="mycelium-mesh"
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
              autoFocus
            />
          </label>

          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              description
            </span>
            <textarea
              required
              rows={6}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A peer-to-peer protocol that treats each node like a hyphal tip…"
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow resize-y"
            />
            <p className="font-mono text-[0.7rem] text-fg-dim mt-1">
              ▒ plain prose. mention what it does, what it might become, and how
              it relates to the track.
            </p>
          </label>

          <fieldset>
            <legend className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim mb-2">
              track
            </legend>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setTrackId('')}
                className={`border px-3 py-1.5 font-mono text-[0.78rem] transition-colors ${
                  !trackId ? 'border-primary text-primary' : 'border-rule text-fg-muted hover:text-fg'
                }`}
              >
                ◇ no track
              </button>
              {tracks.length === 0 ? (
                <span className="font-mono text-[0.72rem] text-fg-dim self-center">
                  (no tracks defined yet — the project will be unsorted)
                </span>
              ) : (
                tracks.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTrackId(t.id)}
                    className={`border px-3 py-1.5 font-mono text-[0.78rem] transition-colors ${
                      trackId === t.id
                        ? 'border-primary text-primary'
                        : 'border-rule text-fg-muted hover:text-fg'
                    }`}
                  >
                    ◆ {t.name}
                  </button>
                ))
              )}
            </div>
          </fieldset>

          {error && (
            <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
              ✕ {error}
            </p>
          )}

          <div className="flex items-center gap-3 pt-4 border-t border-rule">
            <button type="submit" className="btn" disabled={busy}>
              {busy ? 'proposing…' : 'propose →'}
            </button>
            <Link
              href="/projects/"
              className="font-mono text-[0.78rem] text-fg-muted hover:text-fg uppercase tracking-widest"
            >
              ← cancel
            </Link>
          </div>
        </form>
      </section>
    </>
  );
}
