'use client';

import { useEffect, useRef, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import {
  api,
  ApiError,
  type ApplicationDTO,
  type ApplicationStatus,
  type CsvImportResultDTO,
} from '../../../lib/api';
import {
  credentialBody,
  credentialMailto,
  credentialSubject,
} from '../../../lib/credentials';

type Filter = ApplicationStatus | 'all';

const STATUS_TONE: Record<string, string> = {
  pending: 'text-warm',
  approved: 'text-primary',
  rejected: 'text-danger',
};

const STATUS_GLYPH: Record<string, string> = {
  pending: '▒',
  approved: '◆',
  rejected: '✕',
};

function CredentialButtons({
  name,
  email,
  password,
  eventTitle,
}: {
  name: string;
  email: string;
  password: string;
  eventTitle: string;
}) {
  const [copied, setCopied] = useState(false);

  async function copyMessage() {
    const body = `Subject: ${credentialSubject(eventTitle)}\n\n${credentialBody({
      name,
      password,
      eventTitle,
    })}`;
    try {
      await navigator.clipboard.writeText(body);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — the mailto button still works */
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <code className="font-mono text-[0.8rem] text-primary bg-bg-elev border border-rule px-2 py-1">
        {password}
      </code>
      <button
        type="button"
        onClick={() => void copyMessage()}
        className="btn btn-ghost !px-3 !py-1 font-mono text-[0.72rem] uppercase tracking-widest"
      >
        {copied ? '✓ copied' : '⧉ copy message'}
      </button>
      <a
        href={credentialMailto(email, { name, password, eventTitle })}
        className="btn btn-ghost !px-3 !py-1 font-mono text-[0.72rem] uppercase tracking-widest"
      >
        ✉ mailto
      </a>
    </div>
  );
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<ApplicationDTO[]>([]);
  const [counts, setCounts] = useState<Record<ApplicationStatus, number>>({
    pending: 0,
    approved: 0,
    rejected: 0,
  });
  const [filter, setFilter] = useState<Filter>('pending');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [eventTitle, setEventTitle] = useState('the event');
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<CsvImportResultDTO | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);

  async function reload() {
    try {
      const res = await api.adminApplications();
      setApplications(res.applications);
      setCounts(res.counts);
    } catch (err) {
      if (err instanceof ApiError) setError(err.body || `load failed (${err.status})`);
    }
  }

  useEffect(() => {
    void reload();
    void api.event().then((e) => {
      if (e?.title) setEventTitle(e.title);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function decide(a: ApplicationDTO, action: 'approve' | 'reject') {
    setBusyId(a.id);
    setError(null);
    try {
      const updated =
        action === 'approve'
          ? await api.approveApplication(a.id)
          : await api.rejectApplication(a.id);
      setApplications((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      setCounts((prev) => ({
        ...prev,
        pending: Math.max(0, prev.pending - 1),
        [updated.status]: (prev[updated.status as ApplicationStatus] ?? 0) + 1,
      }));
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.body || `${action} failed (${err.status})`);
      } else {
        setError(String(err));
      }
    } finally {
      setBusyId(null);
    }
  }

  async function importCsv(file: File) {
    setImporting(true);
    setError(null);
    setImportResult(null);
    try {
      const result = await api.importUsersCsv(file);
      setImportResult(result);
      await reload();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.body || `import failed (${err.status})`);
      } else {
        setError(String(err));
      }
    } finally {
      setImporting(false);
      if (fileInput.current) fileInput.current.value = '';
    }
  }

  const filtered =
    filter === 'all' ? applications : applications.filter((a) => a.status === filter);
  const allCount = applications.length;

  return (
    <>
      <PageHeader
        prompt="ritual.admin.applications()"
        title="Applications"
        subtitle="Approve a petition and the forge mints an access key. You deliver it — copy the message or open your mail client."
        chip={`${counts.pending} awaiting`}
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-8">
        {/* filter chips */}
        <div className="flex flex-wrap gap-2 mb-8 font-mono text-[0.72rem] uppercase tracking-widest">
          {(['pending', 'approved', 'rejected', 'all'] as Filter[]).map((f) => {
            const active = f === filter;
            const count = f === 'all' ? allCount : counts[f];
            return (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`border px-3 py-1.5 transition-colors ${
                  active
                    ? 'border-primary text-primary'
                    : 'border-rule text-fg-muted hover:text-fg'
                }`}
              >
                <span className={`mr-1.5 ${STATUS_TONE[f] ?? 'text-fg-muted'}`}>
                  {STATUS_GLYPH[f] ?? '◇'}
                </span>
                {f}
                <span className="text-fg-dim ml-2">{count}</span>
              </button>
            );
          })}
        </div>

        {error && (
          <p className="ascii-frame !border-danger px-3 py-2 mb-6 font-mono text-[0.78rem] text-danger">
            ✕ {error}
          </p>
        )}

        {filtered.length === 0 ? (
          <div className="ascii-frame p-10 text-center mb-10">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ applications.list({JSON.stringify(filter)}) → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem]">
              {filter === 'pending'
                ? 'no petitions waiting for the keeper. quiet.'
                : `no applications in ${filter}.`}
            </p>
          </div>
        ) : (
          <ul className="space-y-4 mb-10">
            {filtered.map((a) => (
              <li key={a.id} className="ascii-frame p-4">
                <header className="flex flex-wrap items-baseline justify-between gap-3 mb-1.5">
                  <h2 className="font-display italic text-xl text-fg">
                    {a.name}
                  </h2>
                  <span
                    className={`font-mono text-[0.7rem] uppercase tracking-widest ${STATUS_TONE[a.status]}`}
                  >
                    {STATUS_GLYPH[a.status]} {a.status}
                    {a.source === 'import' && <span className="text-fg-dim"> · imported</span>}
                  </span>
                </header>
                <p className="font-mono text-[0.72rem] uppercase tracking-wider text-fg-dim mb-2">
                  <span className="text-fg-muted normal-case">{a.email}</span>
                  {a.team && (
                    <>
                      {' '}· team: <span className="text-warm normal-case">{a.team}</span>
                    </>
                  )}
                  {' '}· filed {new Date(a.created_at).toLocaleDateString()}
                </p>
                {a.project_interest && (
                  <p className="text-fg-muted text-[0.88rem] leading-relaxed line-clamp-3 mb-3">
                    {a.project_interest}
                  </p>
                )}

                {a.status === 'pending' && (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={busyId === a.id}
                      onClick={() => void decide(a, 'approve')}
                      className="btn !px-4 !py-1.5 font-mono text-[0.72rem] uppercase tracking-widest"
                    >
                      {busyId === a.id ? '…' : '◆ approve'}
                    </button>
                    <button
                      type="button"
                      disabled={busyId === a.id}
                      onClick={() => void decide(a, 'reject')}
                      className="btn btn-ghost !px-4 !py-1.5 font-mono text-[0.72rem] uppercase tracking-widest !text-danger"
                    >
                      ✕ reject
                    </button>
                  </div>
                )}

                {a.status === 'approved' && a.user?.access_password && (
                  <CredentialButtons
                    name={a.name}
                    email={a.email}
                    password={a.user.access_password}
                    eventTitle={eventTitle}
                  />
                )}
              </li>
            ))}
          </ul>
        )}

        {/* CSV import */}
        <div className="ascii-frame p-5">
          <h2 className="font-display italic text-2xl text-fg mb-2">Bulk import</h2>
          <p className="text-fg-muted text-[0.88rem] leading-relaxed mb-4">
            Upload a CSV with header{' '}
            <code className="font-mono text-[0.8rem] text-warm">name,email,team,project</code>{' '}
            (team and project optional). Every valid row becomes an approved user
            with a fresh access key; rows sharing a team are bound into one team.
          </p>
          <input
            ref={fileInput}
            type="file"
            accept=".csv,text/csv"
            disabled={importing}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void importCsv(f);
            }}
            className="font-mono text-[0.78rem] text-fg-muted file:btn file:btn-ghost file:mr-4 file:font-mono file:text-[0.72rem] file:uppercase file:tracking-widest"
          />
          {importing && (
            <p className="font-mono text-[0.72rem] text-warm mt-3">▸ importing…</p>
          )}

          {importResult && (
            <div className="mt-5 space-y-4">
              <p className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-muted">
                ◆ {importResult.created.length} created ·{' '}
                ▒ {importResult.skipped.length} skipped ·{' '}
                ✕ {importResult.errors.length} errors
              </p>

              {importResult.created.length > 0 && (
                <ul className="space-y-3">
                  {importResult.created.map((row) => (
                    <li key={row.user_id} className="border border-rule p-3">
                      <p className="font-mono text-[0.78rem] text-fg mb-2">
                        {row.name}{' '}
                        <span className="text-fg-dim">· {row.email}</span>
                        {row.team && <span className="text-warm"> · {row.team}</span>}
                      </p>
                      <CredentialButtons
                        name={row.name}
                        email={row.email}
                        password={row.access_password}
                        eventTitle={eventTitle}
                      />
                    </li>
                  ))}
                </ul>
              )}

              {importResult.skipped.length > 0 && (
                <div className="font-mono text-[0.72rem] text-fg-dim">
                  {importResult.skipped.map((s2) => (
                    <p key={`${s2.row}-${s2.email}`}>
                      ▒ row {s2.row}: {s2.email} — {s2.reason}
                    </p>
                  ))}
                </div>
              )}

              {importResult.errors.length > 0 && (
                <div className="font-mono text-[0.72rem] text-danger">
                  {importResult.errors.map((er) => (
                    <p key={er.row}>✕ row {er.row}: {er.reason}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
