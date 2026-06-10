'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '../../../components/page-header';
import {
  api,
  ApiError,
  type MeDTO,
  type ProjectDTO,
} from '../../../lib/api';

/**
 * Offer a submission to the forge.
 *
 * Pairs a participant with a project and posts a versioned submission. The
 * server gates this on the event being OPEN and on the per-participant cap;
 * those failures surface here as the keeper's message, not a stack trace.
 */
export default function NewSubmissionPage() {
  const [me, setMe] = useState<MeDTO | null>(null);
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [projectId, setProjectId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [result, setResult] = useState('');
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ id: string; version: number } | null>(
    null,
  );

  useEffect(() => {
    void Promise.all([api.me(), api.projects()]).then(([meRes, projRes]) => {
      setMe(meRes);
      // Only approved projects can receive submissions; fall back to all if the
      // backend hasn't tagged any (demo data).
      const approved = projRes.filter((p) => p.status === 'approved');
      const usable = approved.length > 0 ? approved : projRes;
      setProjects(usable);
      if (usable.length > 0) setProjectId(usable[0].id);
      setLoaded(true);
    });
  }, []);

  const participantId = me?.participant?.id ?? null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId) {
      setError('choose a project to submit against.');
      return;
    }
    if (!participantId) {
      setError('you need a participant profile before you can submit.');
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const sub = await api.createSubmission({
        project_id: projectId,
        participant_id: participantId,
        title: title || undefined,
        description: description || undefined,
        result: result || undefined,
      });
      setCreated({ id: sub.id, version: sub.version });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('you must be signed in to submit.');
      } else if (err instanceof ApiError && err.status === 403) {
        setError('the forge is not open — submissions are closed in this state.');
      } else if (err instanceof ApiError && err.status === 429) {
        setError('submission cap reached for this window. wait, then offer again.');
      } else if (err instanceof ApiError) {
        setError(err.body || `submission failed (${err.status})`);
      } else {
        setError(String(err));
      }
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <>
        <PageHeader
          prompt="ritual.submission.offered()"
          title="The work is offered."
          subtitle="Your submission is in the forge. It will be scored when the verdict is cast."
        />
        <section className="mx-auto w-full max-w-2xl px-6 py-12">
          <div className="ascii-frame p-6 mb-6 font-mono text-[0.85rem]">
            <p className="text-primary mb-2">▸ accepted · version {created.version}</p>
            <p className="text-fg-muted leading-relaxed">
              The submission is recorded. You can revise it while the forge is
              open — each save is a new version. View it under{' '}
              <Link href="/submissions/" className="text-primary hover:underline">
                /submissions/
              </Link>
              .
            </p>
          </div>
          <div className="flex gap-3">
            <Link href="/submissions/" className="btn">
              ▸ all submissions
            </Link>
            <Link href={`/submission/?id=${created.id}`} className="btn btn-ghost">
              open this one
            </Link>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <PageHeader
        prompt="ritual.submission.offer()"
        title="Offer to the forge."
        subtitle="Bind your work to a project and submit it. You can revise while the forge is open."
        back="/submissions/"
        backLabel="all submissions"
      />

      <section className="mx-auto w-full max-w-2xl px-6 py-12">
        {loaded && !participantId && (
          <div className="ascii-frame !border-warm p-5 mb-8 font-mono text-[0.82rem]">
            <p className="text-warm mb-2">▒ no participant profile</p>
            <p className="text-fg-muted leading-relaxed">
              Submissions are made as a participant. Join the circle first —
              register from your{' '}
              <Link href="/overview/" className="text-primary hover:underline">
                overview
              </Link>
              .
            </p>
          </div>
        )}

        <form onSubmit={submit} className="space-y-6">
          <fieldset>
            <legend className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim mb-2">
              project
            </legend>
            {projects.length === 0 ? (
              <p className="font-mono text-[0.72rem] text-fg-dim">
                (no projects available — propose or approve one first)
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {projects.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setProjectId(p.id)}
                    className={`border px-3 py-1.5 font-mono text-[0.78rem] transition-colors ${
                      projectId === p.id
                        ? 'border-primary text-primary'
                        : 'border-rule text-fg-muted hover:text-fg'
                    }`}
                  >
                    ◆ {p.title}
                  </button>
                ))}
              </div>
            )}
          </fieldset>

          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              title <span className="text-fg-dim normal-case">(optional)</span>
            </span>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="first working slice"
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
            />
          </label>

          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              description <span className="text-fg-dim normal-case">(optional)</span>
            </span>
            <textarea
              rows={5}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What you built, what works, what's next…"
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow resize-y"
            />
          </label>

          <label className="block">
            <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
              result <span className="text-fg-dim normal-case">(optional — a link, a demo url, a one-line outcome)</span>
            </span>
            <input
              type="text"
              value={result}
              onChange={(e) => setResult(e.target.value)}
              placeholder="https://… or 'reduced latency 40%'"
              className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
            />
          </label>

          {error && (
            <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
              ✕ {error}
            </p>
          )}

          <div className="flex items-center gap-3 pt-4 border-t border-rule">
            <button
              type="submit"
              className="btn"
              disabled={busy || projects.length === 0}
            >
              {busy ? 'offering…' : 'offer →'}
            </button>
            <Link
              href="/submissions/"
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
