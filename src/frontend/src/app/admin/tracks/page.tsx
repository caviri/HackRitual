'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import { useStage } from '../../../lib/use-stage';
import {
  api,
  ApiError,
  backendPresent,
  type ProjectDTO,
  type TrackDTO,
} from '../../../lib/api';

interface Row {
  key: string;
  name: string;
  glyph: string;
  blurb: string;
  count: number;
  dto?: TrackDTO;
}

function describeError(err: unknown, verb: string): string {
  if (err instanceof ApiError) return err.body || `${verb} failed (${err.status})`;
  return String(err);
}

export default function AdminTracksPage() {
  const data = useStage();
  const [live, setLive] = useState<boolean | null>(null);
  const [real, setReal] = useState<{
    tracks: TrackDTO[];
    projects: ProjectDTO[];
  }>({ tracks: [], projects: [] });

  // composer
  const [composing, setComposing] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);

  // inline edit
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) {
        const [tracks, projects] = await Promise.all([
          api.tracks(),
          api.projects(),
        ]);
        setReal({ tracks, projects });
      }
      setLive(ok);
    });
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.createTrack({
        name: name.trim(),
        description: description.trim() || null,
      });
      setReal((prev) => ({ ...prev, tracks: [...prev.tracks, created] }));
      setName('');
      setDescription('');
      setComposing(false);
    } catch (err) {
      setError(describeError(err, 'inscription'));
    } finally {
      setBusy(false);
    }
  }

  function beginEdit(t: TrackDTO) {
    setEditingId(t.id);
    setEditName(t.name);
    setEditDescription(t.description ?? '');
    setError(null);
  }

  async function saveEdit(e: React.FormEvent, t: TrackDTO) {
    e.preventDefault();
    setBusyId(t.id);
    setError(null);
    try {
      const updated = await api.updateTrack(t.id, {
        name: editName.trim(),
        description: editDescription.trim() || null,
      });
      setReal((prev) => ({
        ...prev,
        tracks: prev.tracks.map((x) => (x.id === updated.id ? updated : x)),
      }));
      setEditingId(null);
    } catch (err) {
      setError(describeError(err, 'update'));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(t: TrackDTO) {
    if (!confirm(`Remove the track "${t.name}"?`)) return;
    setBusyId(t.id);
    setError(null);
    try {
      await api.deleteTrack(t.id);
      setReal((prev) => ({
        ...prev,
        tracks: prev.tracks.filter((x) => x.id !== t.id),
      }));
      if (editingId === t.id) setEditingId(null);
    } catch (err) {
      setError(describeError(err, 'removal'));
    } finally {
      setBusyId(null);
    }
  }

  // live !== false → API data (even when empty); mocks only when backend absent
  const rows: Row[] =
    live !== false
      ? real.tracks.map((t) => ({
          key: t.id,
          name: t.name,
          glyph: '◆',
          blurb: t.description ?? '',
          count: real.projects.filter((p) => p.track_id === t.id).length,
          dto: t,
        }))
      : data.tracks.map((t) => ({
          key: t.name,
          name: t.name,
          glyph: t.glyph,
          blurb: t.blurb,
          count: t.count,
        }));

  const fieldClass =
    'mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-2.5 outline-none focus:border-primary transition-colors';
  const labelClass = 'font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim';

  return (
    <>
      <PageHeader
        prompt="ritual.admin.tracks()"
        title="Tracks"
        subtitle="The thematic groupings inside the event. Each project lives in at most one."
        chip={`${rows.length} inscribed`}
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-4">
        {error && (
          <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
            ✕ {error}
          </p>
        )}
        {rows.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ tracks.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No tracks have been inscribed yet.
            </p>
          </div>
        ) : (
          rows.map((t) =>
            t.dto && editingId === t.dto.id ? (
              <form
                key={t.key}
                onSubmit={(e) => void saveEdit(e, t.dto as TrackDTO)}
                className="ascii-frame p-5 space-y-4"
              >
                <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                  edit track
                </p>
                <label className="block">
                  <span className={labelClass}>name</span>
                  <input
                    type="text"
                    required
                    maxLength={80}
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className={fieldClass}
                  />
                </label>
                <label className="block">
                  <span className={labelClass}>description</span>
                  <textarea
                    rows={3}
                    maxLength={500}
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    className={`${fieldClass} resize-y`}
                  />
                </label>
                <div className="flex gap-2">
                  <button type="submit" className="btn" disabled={busyId === t.dto.id}>
                    {busyId === t.dto.id ? 'inscribing…' : '◆ save'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={busyId === t.dto.id}
                    onClick={() => setEditingId(null)}
                  >
                    cancel
                  </button>
                </div>
              </form>
            ) : (
              <article
                key={t.key}
                className="ascii-frame p-5 flex flex-wrap items-baseline justify-between gap-4"
              >
                <div className="min-w-0">
                  <h2 className="font-display italic text-2xl text-fg mb-1">
                    <span aria-hidden className="text-primary mr-2">{t.glyph}</span>
                    {t.name}
                  </h2>
                  <p className="text-fg-muted text-[0.92rem] max-w-2xl">{t.blurb}</p>
                </div>
                <div className="flex items-center gap-3 font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                  <span>{t.count} projects</span>
                  {live === true && t.dto && (
                    <>
                      <button
                        type="button"
                        disabled={busyId === t.dto.id}
                        onClick={() => beginEdit(t.dto as TrackDTO)}
                        className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem]"
                      >
                        edit
                      </button>
                      <button
                        type="button"
                        disabled={busyId === t.dto.id}
                        onClick={() => void remove(t.dto as TrackDTO)}
                        className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem] !text-danger"
                      >
                        ✕ remove
                      </button>
                    </>
                  )}
                </div>
              </article>
            ),
          )
        )}
        {live === true &&
          (composing ? (
            <form onSubmit={create} className="ascii-frame p-5 space-y-4">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                inscribe a new track
              </p>
              <label className="block">
                <span className={labelClass}>name</span>
                <input
                  type="text"
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Tools for the long night"
                  className={fieldClass}
                />
              </label>
              <label className="block">
                <span className={labelClass}>description</span>
                <textarea
                  rows={3}
                  maxLength={500}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="One line on what belongs here."
                  className={`${fieldClass} resize-y`}
                />
              </label>
              <div className="flex gap-2">
                <button type="submit" className="btn" disabled={busy}>
                  {busy ? 'inscribing…' : '◆ inscribe track'}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={busy}
                  onClick={() => setComposing(false)}
                >
                  cancel
                </button>
              </div>
            </form>
          ) : (
            <button type="button" className="btn" onClick={() => setComposing(true)}>
              ◆ inscribe a new track
            </button>
          ))}
      </section>
    </>
  );
}
