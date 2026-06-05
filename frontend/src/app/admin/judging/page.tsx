'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import {
  api,
  ApiError,
  type ProjectDTO,
  type ScoreDTO,
  type SubmissionDTO,
  type ParticipantDTO,
} from '../../../lib/api';

/** Default per-criterion weights. The judge can override any value, or set
 * blanks to skip a criterion. */
const CRITERIA = [
  { key: 'craft', label: 'craft', hint: 'how well it is made' },
  { key: 'originality', label: 'originality', hint: 'how rare the idea' },
  { key: 'reach', label: 'reach', hint: 'how far the work travels' },
  { key: 'fit-to-track', label: 'fit-to-track', hint: 'how well it sits in its track' },
];

interface FinalRow {
  submission: SubmissionDTO;
  project: ProjectDTO | undefined;
  participant: ParticipantDTO | undefined;
  scores: ScoreDTO[];
}

export default function JudgingPage() {
  const [rows, setRows] = useState<FinalRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [projects, subs, parts] = await Promise.all([
      api.projects(),
      api.submissions(),
      api.participants(),
    ]);
    const finals = subs.filter((s) => s.status === 'final');
    const projectById = new Map(projects.map((p) => [p.id, p]));
    const partById = new Map(parts.map((p) => [p.id, p]));

    const withScores = await Promise.all(
      finals.map(async (s) => ({
        submission: s,
        project: projectById.get(s.project_id),
        participant: partById.get(s.participant_id),
        scores: await api.listScores(s.id),
      })),
    );

    // Sort: unscored first, then by recency
    withScores.sort((a, b) => {
      const aScored = a.scores.length > 0 ? 1 : 0;
      const bScored = b.scores.length > 0 ? 1 : 0;
      if (aScored !== bScored) return aScored - bScored;
      return b.submission.modified_at.localeCompare(a.submission.modified_at);
    });
    setRows(withScores);
  }

  useEffect(() => {
    void load().catch((e) => setError(String(e)));
  }, []);

  const unscored = rows?.filter((r) => r.scores.length === 0).length ?? 0;
  const scored = rows?.filter((r) => r.scores.length > 0).length ?? 0;

  return (
    <>
      <PageHeader
        prompt="ritual.admin.judging()"
        title="Judging"
        subtitle="Score the final submissions. Each criterion goes 0–100. The headline is the mean unless you override it. Drafts and withdrawn versions are not shown."
        chip={`${unscored} unscored · ${scored} done`}
      />

      <section className="mx-auto w-full max-w-5xl px-6 py-10 space-y-6">
        {error && (
          <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
            ✕ {error}
          </p>
        )}
        {rows === null ? (
          <p className="font-mono text-fg-dim">summoning…</p>
        ) : rows.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ submissions.list(status=&apos;final&apos;) → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No final submissions yet. Teams need to mark a submission as
              <span className="text-primary"> final </span>
              before it can be scored.
            </p>
          </div>
        ) : (
          rows.map((row) => (
            <JudgingRow key={row.submission.id} row={row} onChanged={load} />
          ))
        )}
      </section>
    </>
  );
}

function JudgingRow({ row, onChanged }: { row: FinalRow; onChanged: () => void }) {
  const { submission: s, project, participant, scores } = row;
  const [breakdown, setBreakdown] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const headline = scores[0]?.score_value;
  const has = scores.length > 0;

  async function score() {
    setBusy(true);
    setErr(null);
    try {
      const parsed: Record<string, number> = {};
      for (const k of Object.keys(breakdown)) {
        const n = Number(breakdown[k]);
        if (!Number.isFinite(n)) continue;
        parsed[k] = Math.max(0, Math.min(100, n));
      }
      await api.createScore(s.id, {
        breakdown: Object.keys(parsed).length ? parsed : undefined,
        notes: notes || undefined,
      });
      setBreakdown({});
      setNotes('');
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.body || `score failed (${e.status})` : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function unscore(id: string) {
    if (!confirm('Discard this score? An audit row is kept.')) return;
    setBusy(true);
    try {
      await api.deleteScore(id);
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.body : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="ascii-frame overflow-hidden">
      <header className="p-5 border-b border-rule grid md:grid-cols-[1fr_auto] gap-3 items-start">
        <div className="min-w-0">
          <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-1">
            #{s.project_id.slice(0, 6)} · v{s.version}
          </p>
          <h2 className="font-display italic text-2xl text-fg mb-1">
            {project?.title ?? '?'}
          </h2>
          <p className="font-mono text-[0.78rem] text-fg-muted">
            by{' '}
            <Link
              href={`/participant/?id=${s.participant_id}`}
              className="text-fg hover:text-primary"
            >
              {participant?.display_name ?? s.participant_id.slice(0, 8)}
            </Link>
            {s.result && (
              <>
                {' · '}
                <span className="text-fg-muted">{s.result.slice(0, 100)}</span>
              </>
            )}
          </p>
        </div>
        <div className="text-right">
          {has ? (
            <div>
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-accent">
                ◆ scored
              </p>
              <p className="font-display italic text-4xl text-accent tabular-nums">
                {headline!.toFixed(1)}
              </p>
            </div>
          ) : (
            <span className="font-mono text-[0.7rem] uppercase tracking-widest text-warm">
              ▒ awaiting
            </span>
          )}
        </div>
      </header>

      {has ? (
        <div className="p-5 space-y-3">
          {scores.map((sc) => (
            <div key={sc.id} className="space-y-2">
              <div className="grid sm:grid-cols-4 gap-2">
                {Object.entries(sc.breakdown).map(([k, v]) => (
                  <div key={k} className="border border-rule px-3 py-2">
                    <p className="font-mono text-[0.62rem] uppercase tracking-widest text-fg-dim">
                      {k}
                    </p>
                    <p className="font-mono text-[0.95rem] text-fg tabular-nums">
                      {v.toFixed(1)}
                    </p>
                  </div>
                ))}
              </div>
              {sc.notes && (
                <p className="ritual text-fg-muted text-[0.95rem] border-l-2 border-rule pl-3">
                  {sc.notes}
                </p>
              )}
              <div className="flex items-center gap-3 font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                <span>{sc.scorer_version}</span>
                {sc.scored_at && (
                  <span>
                    · {new Date(sc.scored_at).toLocaleString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                )}
                <span className="flex-1" />
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => unscore(sc.id)}
                  className="text-fg-muted hover:text-danger transition-colors"
                >
                  ✕ discard
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-5 space-y-4">
          <div className="grid sm:grid-cols-4 gap-3">
            {CRITERIA.map((c) => (
              <label key={c.key} className="block">
                <span className="font-mono text-[0.62rem] uppercase tracking-widest text-fg-dim">
                  {c.label}
                </span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step="0.1"
                  value={breakdown[c.key] ?? ''}
                  placeholder="0–100"
                  onChange={(e) =>
                    setBreakdown((prev) => ({ ...prev, [c.key]: e.target.value }))
                  }
                  className="mt-1 w-full bg-bg-elev border border-rule text-fg font-mono px-2 py-1.5 text-[0.9rem] tabular-nums outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
                />
                <p className="font-mono text-[0.6rem] text-fg-dim mt-0.5">{c.hint}</p>
              </label>
            ))}
          </div>
          <label className="block">
            <span className="font-mono text-[0.62rem] uppercase tracking-widest text-fg-dim">
              notes (optional)
            </span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="what stood out, what to mention to the team..."
              className="mt-1 w-full bg-bg-elev border border-rule text-fg font-mono px-2 py-1.5 text-[0.85rem] outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow resize-y"
            />
          </label>
          {err && (
            <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.72rem] text-danger">
              ✕ {err}
            </p>
          )}
          <div className="flex items-center gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={score}
              className="btn"
            >
              ◆ inscribe score
            </button>
            <Link
              href={`/project/?id=${s.project_id}`}
              className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-muted hover:text-primary"
            >
              open project →
            </Link>
          </div>
        </div>
      )}
    </article>
  );
}
