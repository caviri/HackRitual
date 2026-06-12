'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import {
  api,
  ApiError,
  type ImageEffect,
  type MeDTO,
  type ProjectDTO,
  type ScoreDTO,
  type SubmissionDTO,
  type SubmissionFileDTO,
  type SubmissionStatus,
} from '../../lib/api';

const STATUS_GLYPH: Record<SubmissionStatus, string> = {
  draft: '▒',
  final: '◆',
  withdrawn: '✕',
};

const STATUS_TONE: Record<SubmissionStatus, string> = {
  draft: 'text-warm',
  final: 'text-primary',
  withdrawn: 'text-fg-dim line-through',
};

const STATUS_PHRASE: Record<SubmissionStatus, string> = {
  draft: 'a draft — still editable',
  final: 'sealed — eligible for scoring',
  withdrawn: 'withdrawn — out of the running',
};

export default function SubmissionByQueryPage() {
  const [id, setId] = useState<string | null>(null);
  const [sub, setSub] = useState<SubmissionDTO | null | undefined>(undefined);
  const [project, setProject] = useState<ProjectDTO | null>(null);
  const [me, setMe] = useState<MeDTO | null>(null);
  const [scores, setScores] = useState<ScoreDTO[]>([]);

  // Editable form state — initialised from server on load
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [result, setResult] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  // Plates & evidence — attachments listed publicly by metadata; the bytes
  // stream through the gated download URL (owner/admin only).
  const [files, setFiles] = useState<SubmissionFileDTO[]>([]);
  const [effect, setEffect] = useState<ImageEffect>('dither');
  const [uploading, setUploading] = useState(false);
  const [plateError, setPlateError] = useState<string | null>(null);

  useEffect(() => {
    const u = new URL(window.location.href);
    const sid = u.searchParams.get('id');
    setId(sid);
    if (!sid) {
      setSub(null);
      return;
    }
    void (async () => {
      const [submission, myInfo] = await Promise.all([
        api.submission(sid),
        api.me(),
      ]);
      setSub(submission);
      setMe(myInfo);
      if (submission) {
        setTitle(submission.title ?? '');
        setDescription(submission.description ?? '');
        setResult(submission.result ?? '');
        void api.submissionFiles(sid).then(setFiles);
        if (submission.project_id) {
          void api.project(submission.project_id).then(setProject);
        }
        if (submission.status === 'final') {
          void api.listScores(sid).then(setScores);
        }
      }
    })();
  }, []);

  if (sub === undefined) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="font-mono text-fg-dim">summoning…</p>
      </section>
    );
  }

  if (sub === null) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
          ritual.submission({id ? JSON.stringify(id) : 'undefined'})
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">No such submission.</h1>
        <p className="ritual text-fg-muted mb-6">
          No version with that id is on record.
        </p>
        <Link href="/submissions/" className="btn">
          ← all submissions
        </Link>
      </section>
    );
  }

  const isOwner = !!me?.participant && me.participant.id === sub.participant_id;
  const isFinal = sub.status === 'final';
  const canEdit = isOwner && !isFinal;

  async function save() {
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      const updated = await api.updateSubmission(sub!.id, {
        title: title || undefined,
        description: description || undefined,
        result: result || undefined,
      });
      setSub(updated);
      setFlash('saved.');
    } catch (e) {
      setError(e instanceof ApiError ? e.body || `save failed (${e.status})` : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function uploadPlate(file: File) {
    if (!sub) return;
    setUploading(true);
    setPlateError(null);
    try {
      await api.uploadImage(file, sub.id, sub.participant_id, effect);
      setFiles(await api.submissionFiles(sub.id));
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setPlateError('the forge is not open — plates land while the event is OPEN.');
      } else {
        setPlateError(
          e instanceof ApiError ? e.body || `upload failed (${e.status})` : String(e),
        );
      }
    } finally {
      setUploading(false);
    }
  }

  async function removePlate(f: SubmissionFileDTO) {
    if (!sub) return;
    if (!confirm(`Remove "${f.filename}" from this submission?`)) return;
    setUploading(true);
    setPlateError(null);
    try {
      await api.deleteSubmissionFile(sub.id, f.id);
      setFiles((prev) => prev.filter((x) => x.id !== f.id));
    } catch (e) {
      setPlateError(
        e instanceof ApiError ? e.body || `remove failed (${e.status})` : String(e),
      );
    } finally {
      setUploading(false);
    }
  }

  async function transition(to: SubmissionStatus) {
    if (!sub) return;
    const verb = { final: 'seal as final', withdrawn: 'withdraw', draft: 'reopen as draft' }[to];
    if (!confirm(`${verb}? This may be irreversible.`)) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateSubmission(sub.id, { status: to });
      setSub(updated);
      setFlash(`now ${to}.`);
      if (to === 'final') {
        void api.listScores(sub.id).then(setScores);
      } else {
        setScores([]);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.body : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        prompt={`ritual.submission(v${sub.version})`}
        title={project?.title ?? title ?? `submission #${sub.id.slice(0, 6)}`}
        subtitle={STATUS_PHRASE[sub.status]}
        chip={`v${sub.version} · ${sub.status}`}
        back={project ? `/project/?id=${sub.project_id}` : '/submissions/'}
        backLabel={project ? 'project' : 'submissions'}
      />

      <section className="mx-auto w-full max-w-5xl px-6 py-12 grid gap-10 lg:grid-cols-[1.6fr_1fr]">
        {/* MAIN — form or readonly */}
        <div className="space-y-6">
          {!isOwner && (
            <p className="ascii-frame px-4 py-3 font-mono text-[0.78rem] text-fg-muted">
              ▒ viewing in read-only mode — sign in as the submitting participant to edit.
            </p>
          )}

          <article className="ascii-frame p-6">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-4">
              the submission
            </p>

            {canEdit ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void save();
                }}
                className="space-y-5"
              >
                <label className="block">
                  <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                    title
                  </span>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder={project?.title ?? 'a name for this version'}
                    className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-2 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                    description
                  </span>
                  <textarea
                    rows={5}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="what's in this version, what changed, what to look at first"
                    className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-2 text-[0.92rem] outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow resize-y"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                    result
                  </span>
                  <input
                    type="text"
                    value={result}
                    onChange={(e) => setResult(e.target.value)}
                    placeholder="https://… (repo, demo, paper) or short reference"
                    className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-2 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
                  />
                  <p className="font-mono text-[0.7rem] text-fg-dim mt-1">
                    ▒ a URL or short reference. shown to the judges and on the public verdict.
                  </p>
                </label>

                {error && (
                  <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
                    ✕ {error}
                  </p>
                )}
                {flash && (
                  <p className="font-mono text-[0.78rem] text-primary">◆ {flash}</p>
                )}

                <div className="flex items-center gap-3 pt-2">
                  <button type="submit" disabled={busy} className="btn">
                    {busy ? 'saving…' : 'save changes'}
                  </button>
                </div>
              </form>
            ) : (
              <dl className="space-y-4">
                <div>
                  <dt className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-1">
                    title
                  </dt>
                  <dd className="font-display italic text-2xl text-fg">
                    {sub.title || project?.title || '(no title)'}
                  </dd>
                </div>
                {sub.description && (
                  <div>
                    <dt className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-1">
                      description
                    </dt>
                    <dd className="text-fg-muted text-[0.95rem] whitespace-pre-wrap">
                      {sub.description}
                    </dd>
                  </div>
                )}
                {sub.result && (
                  <div>
                    <dt className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-1">
                      result
                    </dt>
                    <dd className="font-mono text-[0.92rem] text-fg break-all">
                      {sub.result}
                    </dd>
                  </div>
                )}
              </dl>
            )}
          </article>

          {/* plates & evidence */}
          {(files.length > 0 || canEdit) && (
            <article className="ascii-frame p-6">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-4">
                plates &amp; evidence · {files.length}
              </p>

              {files.length === 0 ? (
                <p className="ritual text-fg-muted text-[0.95rem] mb-4">
                  Nothing attached yet. The scorer weighs completeness — a
                  plate or a report strengthens the verdict.
                </p>
              ) : (
                <ul className="grid gap-3 sm:grid-cols-2 mb-4">
                  {files.map((f) => {
                    const isImage = f.mime_type.startsWith('image/');
                    const canSeeBlob = isOwner || me?.role === 'admin';
                    const blobUrl = `/api/submissions/${sub.id}/files/${f.id}`;
                    return (
                      <li key={f.id} className="border border-rule overflow-hidden">
                        {isImage && canSeeBlob && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={blobUrl}
                            alt={f.filename}
                            className="w-full aspect-[3/2] object-cover"
                          />
                        )}
                        <div className="p-3 flex items-baseline justify-between gap-2">
                          <div className="min-w-0">
                            {canSeeBlob ? (
                              <a
                                href={blobUrl}
                                className="font-mono text-[0.78rem] text-fg hover:text-primary truncate block"
                              >
                                {f.filename}
                              </a>
                            ) : (
                              <p className="font-mono text-[0.78rem] text-fg truncate">
                                {f.filename}
                              </p>
                            )}
                            <p className="font-mono text-[0.66rem] uppercase tracking-wider text-fg-dim">
                              {f.mime_type} · {(f.size_bytes / 1024).toFixed(1)} kb
                            </p>
                          </div>
                          {canEdit && (
                            <button
                              type="button"
                              disabled={uploading}
                              onClick={() => void removePlate(f)}
                              className="font-mono text-[0.72rem] text-danger hover:underline shrink-0"
                            >
                              ✕
                            </button>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}

              {canEdit && (
                <div className="pt-4 border-t border-rule space-y-3">
                  <div className="flex flex-wrap items-center gap-2 font-mono text-[0.72rem] uppercase tracking-widest">
                    <span className="text-fg-dim">effect</span>
                    {(['dither', 'halftone', 'none'] as ImageEffect[]).map((fx) => (
                      <button
                        key={fx}
                        type="button"
                        onClick={() => setEffect(fx)}
                        className={`border px-2.5 py-1 transition-colors ${
                          effect === fx
                            ? 'border-primary text-primary'
                            : 'border-rule text-fg-muted hover:text-fg'
                        }`}
                      >
                        {fx}
                      </button>
                    ))}
                  </div>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    disabled={uploading}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void uploadPlate(f);
                      e.target.value = '';
                    }}
                    className="font-mono text-[0.78rem] text-fg-muted file:btn file:btn-ghost file:mr-4 file:font-mono file:text-[0.72rem] file:uppercase file:tracking-widest"
                  />
                  {uploading && (
                    <p className="font-mono text-[0.72rem] text-warm">▸ forging the plate…</p>
                  )}
                  <p className="font-mono text-[0.7rem] text-fg-dim">
                    ▒ images are re-struck server-side (max 6 mb) and count
                    toward the completeness score
                  </p>
                </div>
              )}

              {plateError && (
                <p className="ascii-frame !border-danger px-3 py-2 mt-3 font-mono text-[0.78rem] text-danger">
                  ✕ {plateError}
                </p>
              )}
            </article>
          )}

          {/* scores when final */}
          {scores.length > 0 && (
            <article className="ascii-frame !border-accent p-6">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-accent mb-4">
                ✺ the verdict
              </p>
              {scores.map((s) => (
                <div key={s.id} className="space-y-3">
                  <p className="font-display italic text-4xl text-accent tabular-nums leading-none">
                    {s.score_value.toFixed(1)}
                  </p>
                  {Object.keys(s.breakdown).length > 0 && (
                    <ul className="grid sm:grid-cols-2 gap-3 mt-3">
                      {Object.entries(s.breakdown).map(([k, v]) => (
                        <li key={k}>
                          <div className="flex items-baseline justify-between mb-1">
                            <span className="font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim">
                              {k}
                            </span>
                            <span className="font-mono text-[0.85rem] text-accent tabular-nums">
                              {v.toFixed(1)}
                            </span>
                          </div>
                          <div className="h-1 bg-rule overflow-hidden">
                            <div className="h-full bg-accent" style={{ width: `${v}%` }} />
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                  {s.notes && (
                    <p className="ritual text-fg-muted text-[0.95rem] border-l-2 border-accent pl-3 mt-3">
                      {s.notes}
                    </p>
                  )}
                  <p className="font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim mt-3">
                    scored by {s.scorer_version}
                  </p>
                </div>
              ))}
            </article>
          )}
        </div>

        {/* SIDEBAR — meta + state machine */}
        <aside className="space-y-6">
          <div className="ascii-frame p-5">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
              meta
            </p>
            <ul className="font-mono text-[0.78rem] space-y-2">
              <li>
                <span className="text-fg-dim">version  </span>
                <span className="text-fg tabular-nums">v{sub.version}</span>
              </li>
              <li>
                <span className="text-fg-dim">status   </span>
                <span className={STATUS_TONE[sub.status]}>
                  {STATUS_GLYPH[sub.status]} {sub.status}
                </span>
              </li>
              <li>
                <span className="text-fg-dim">project  </span>
                {project ? (
                  <Link
                    href={`/project/?id=${sub.project_id}`}
                    className="text-fg hover:text-primary"
                  >
                    {project.title}
                  </Link>
                ) : (
                  <span className="text-fg break-all">{sub.project_id.slice(0, 8)}…</span>
                )}
              </li>
              <li>
                <span className="text-fg-dim">team     </span>
                <Link
                  href={`/participant/?id=${sub.participant_id}`}
                  className="text-fg hover:text-primary"
                >
                  {sub.participant_id.slice(0, 8)}…
                </Link>
              </li>
              <li>
                <span className="text-fg-dim">modified </span>
                <span className="text-fg-muted tabular-nums">
                  {sub.modified_at.replace('T', ' ').slice(0, 16)}
                </span>
              </li>
            </ul>
          </div>

          {/* state machine */}
          {isOwner && (
            <div className="ascii-frame p-5">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
                state machine
              </p>
              <p className="ritual text-fg-muted text-[0.95rem] mb-4">
                {sub.status === 'draft' &&
                  'Seal when ready. Judges only see final versions.'}
                {sub.status === 'final' &&
                  'Sealed. Withdraw it if you want to pull it back out of the running.'}
                {sub.status === 'withdrawn' &&
                  'Withdrawn. The submission stays in the audit log but is not scored.'}
              </p>
              <div className="flex flex-col gap-2">
                {sub.status === 'draft' && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => transition('final')}
                    className="btn justify-center"
                  >
                    ◆ seal as final
                  </button>
                )}
                {sub.status === 'final' && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => transition('withdrawn')}
                    className="btn btn-ghost justify-center !border-danger !text-danger"
                  >
                    ✕ withdraw
                  </button>
                )}
                {sub.status === 'withdrawn' && (
                  <p className="font-mono text-[0.72rem] text-fg-dim">
                    a new version can be started from the project page
                  </p>
                )}
              </div>
            </div>
          )}
        </aside>
      </section>
    </>
  );
}
