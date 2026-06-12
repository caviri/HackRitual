'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import { useStage } from '../../../lib/use-stage';
import { api, ApiError, backendPresent, type PhaseDTO } from '../../../lib/api';

interface Row {
  key: string;
  name: string;
  range: string;
  epigraph: string;
  status: 'completed' | 'active' | 'upcoming';
  dto?: PhaseDTO;
}

function phaseStatus(p: PhaseDTO, now: Date): Row['status'] {
  const start = p.starts_at ? new Date(p.starts_at) : null;
  const end = p.ends_at ? new Date(p.ends_at) : null;
  if (end && now > end) return 'completed';
  if (start && now >= start) return 'active';
  return 'upcoming';
}

function formatRange(p: PhaseDTO): string {
  const start = p.starts_at ? new Date(p.starts_at) : null;
  const end = p.ends_at ? new Date(p.ends_at) : null;
  const day = (d: Date) =>
    d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  const time = (d: Date) =>
    d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
  if (start && end) {
    return start.toDateString() === end.toDateString()
      ? `${day(start)} · ${time(start)} – ${time(end)}`
      : `${day(start)} ${time(start)} – ${day(end)} ${time(end)}`;
  }
  if (start) return `from ${day(start)} ${time(start)}`;
  if (end) return `until ${day(end)} ${time(end)}`;
  return 'unscheduled';
}

/** ISO string from the API → the local "YYYY-MM-DDTHH:mm" a datetime-local wants. */
function isoToLocal(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
}

/** datetime-local value → ISO for the API; empty field clears to null. */
function localToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return `${value}:00`;
}

function describeError(err: unknown, verb: string): string {
  if (err instanceof ApiError) return err.body || `${verb} failed (${err.status})`;
  return String(err);
}

export default function AdminPhasesPage() {
  const data = useStage();
  const [live, setLive] = useState<boolean | null>(null);
  const [livePhases, setLivePhases] = useState<PhaseDTO[]>([]);

  // composer
  const [composing, setComposing] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [busy, setBusy] = useState(false);

  // inline edit
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editStartsAt, setEditStartsAt] = useState('');
  const [editEndsAt, setEditEndsAt] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) setLivePhases(await api.phases());
      setLive(ok);
    });
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.createPhase({
        name: name.trim(),
        description: description.trim() || null,
        starts_at: localToIso(startsAt),
        ends_at: localToIso(endsAt),
      });
      setLivePhases((prev) => [...prev, created]);
      setName('');
      setDescription('');
      setStartsAt('');
      setEndsAt('');
      setComposing(false);
    } catch (err) {
      setError(describeError(err, 'inscription'));
    } finally {
      setBusy(false);
    }
  }

  function beginEdit(p: PhaseDTO) {
    setEditingId(p.id);
    setEditName(p.name);
    setEditDescription(p.description ?? '');
    setEditStartsAt(isoToLocal(p.starts_at));
    setEditEndsAt(isoToLocal(p.ends_at));
    setError(null);
  }

  async function saveEdit(e: React.FormEvent, p: PhaseDTO) {
    e.preventDefault();
    setBusyId(p.id);
    setError(null);
    try {
      const updated = await api.updatePhase(p.id, {
        name: editName.trim(),
        description: editDescription.trim() || null,
        starts_at: localToIso(editStartsAt),
        ends_at: localToIso(editEndsAt),
      });
      setLivePhases((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      setEditingId(null);
    } catch (err) {
      setError(describeError(err, 'update'));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(p: PhaseDTO) {
    if (!confirm(`Remove the phase "${p.name}"?`)) return;
    setBusyId(p.id);
    setError(null);
    try {
      await api.deletePhase(p.id);
      setLivePhases((prev) => prev.filter((x) => x.id !== p.id));
      if (editingId === p.id) setEditingId(null);
    } catch (err) {
      setError(describeError(err, 'removal'));
    } finally {
      setBusyId(null);
    }
  }

  const now = new Date();

  // live !== false → API data (even when empty); mocks only when backend absent
  const rows: Row[] =
    live !== false
      ? livePhases.map((p) => ({
          key: p.id,
          name: p.name,
          range: formatRange(p),
          epigraph: p.description ?? '',
          status: phaseStatus(p, now),
          dto: p,
        }))
      : data.phases.map((p) => ({
          key: p.name,
          name: p.name,
          range: p.range,
          epigraph: p.epigraph,
          status: p.status,
        }));

  const fieldClass =
    'mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-2.5 outline-none focus:border-primary transition-colors';
  const labelClass = 'font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim';

  return (
    <>
      <PageHeader
        prompt="ritual.admin.phases()"
        title="Phases"
        subtitle="The sub-phases inside OPEN. Their starts and ends, and the page each one links to."
        chip={`${rows.length} scheduled`}
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
              $ phases.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No phases have been inscribed yet.
            </p>
          </div>
        ) : (
          rows.map((p) =>
            p.dto && editingId === p.dto.id ? (
              <form
                key={p.key}
                onSubmit={(e) => void saveEdit(e, p.dto as PhaseDTO)}
                className="ascii-frame p-5 space-y-4"
              >
                <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                  edit phase
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
                    rows={2}
                    maxLength={500}
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    className={`${fieldClass} resize-y`}
                  />
                </label>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className={labelClass}>starts at</span>
                    <input
                      type="datetime-local"
                      value={editStartsAt}
                      onChange={(e) => setEditStartsAt(e.target.value)}
                      className={fieldClass}
                    />
                  </label>
                  <label className="block">
                    <span className={labelClass}>ends at</span>
                    <input
                      type="datetime-local"
                      value={editEndsAt}
                      onChange={(e) => setEditEndsAt(e.target.value)}
                      className={fieldClass}
                    />
                  </label>
                </div>
                <div className="flex gap-2">
                  <button type="submit" className="btn" disabled={busyId === p.dto.id}>
                    {busyId === p.dto.id ? 'inscribing…' : '◆ save'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={busyId === p.dto.id}
                    onClick={() => setEditingId(null)}
                  >
                    cancel
                  </button>
                </div>
              </form>
            ) : (
              <article
                key={p.key}
                className="ascii-frame p-5 grid gap-3 md:grid-cols-[1fr_auto]"
              >
                <div>
                  <header className="flex items-baseline gap-3 mb-1">
                    <h2 className="font-display italic text-2xl text-fg">{p.name}</h2>
                    <span
                      className={`font-mono text-[0.7rem] uppercase tracking-widest ${
                        p.status === 'active'
                          ? 'text-primary'
                          : p.status === 'completed'
                          ? 'text-fg-muted'
                          : 'text-fg-dim'
                      }`}
                    >
                      ▸ {p.status}
                    </span>
                  </header>
                  <p className="font-mono text-[0.78rem] text-fg-muted tabular-nums mb-2">
                    {p.range}
                  </p>
                  <p className="ritual text-fg-muted">{p.epigraph}</p>
                </div>
                {live === true && p.dto && (
                  <div className="flex md:flex-col gap-2 items-start md:items-end">
                    <button
                      type="button"
                      disabled={busyId === p.dto.id}
                      onClick={() => beginEdit(p.dto as PhaseDTO)}
                      className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem]"
                    >
                      edit times
                    </button>
                    <button
                      type="button"
                      disabled={busyId === p.dto.id}
                      onClick={() => void remove(p.dto as PhaseDTO)}
                      className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem] !text-danger"
                    >
                      ✕ remove
                    </button>
                  </div>
                )}
              </article>
            ),
          )
        )}
        {live === true &&
          (composing ? (
            <form onSubmit={create} className="ascii-frame p-5 space-y-4">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                inscribe a new phase
              </p>
              <label className="block">
                <span className={labelClass}>name</span>
                <input
                  type="text"
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="The long building"
                  className={fieldClass}
                />
              </label>
              <label className="block">
                <span className={labelClass}>description</span>
                <textarea
                  rows={2}
                  maxLength={500}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="One line on what this stretch of time is for."
                  className={`${fieldClass} resize-y`}
                />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className={labelClass}>starts at</span>
                  <input
                    type="datetime-local"
                    value={startsAt}
                    onChange={(e) => setStartsAt(e.target.value)}
                    className={fieldClass}
                  />
                </label>
                <label className="block">
                  <span className={labelClass}>ends at</span>
                  <input
                    type="datetime-local"
                    value={endsAt}
                    onChange={(e) => setEndsAt(e.target.value)}
                    className={fieldClass}
                  />
                </label>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn" disabled={busy}>
                  {busy ? 'inscribing…' : '◆ inscribe phase'}
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
              ◆ inscribe a new phase
            </button>
          ))}
      </section>
    </>
  );
}
