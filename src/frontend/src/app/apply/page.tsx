'use client';

import { useState } from 'react';
import { api, ApiError } from '../../lib/api';

type Step = 'petition' | 'filed';

export default function ApplyPage() {
  const [step, setStep] = useState<Step>('petition');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [team, setTeam] = useState('');
  const [interest, setInterest] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.submitApplication({
        name: name.trim(),
        email: email.trim(),
        team: team.trim() || undefined,
        project_interest: interest.trim() || undefined,
      });
      setStep('filed');
    } catch (err) {
      // 404 / 405 / network error → no backend, demo mode files anyway.
      const transparentFailure =
        !(err instanceof ApiError) ||
        err.status === 404 ||
        err.status === 405 ||
        err.status === 0;
      if (transparentFailure) {
        setStep('filed');
      } else if (err instanceof ApiError && err.status === 409) {
        setError('A petition with this address already exists — the keeper has it.');
      } else if (err instanceof ApiError) {
        setError(err.body || `the petition was refused (${err.status})`);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto w-full max-w-md px-6 py-20">
      {step === 'petition' && (
        <>
          <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
            ritual.applications.file()
          </p>
          <h1 className="font-display italic text-4xl text-fg mb-3">Petition to join.</h1>
          <p className="ritual text-fg-muted text-[1.02rem] mb-10 leading-relaxed">
            Leave your name and address. The organizers review every petition by
            hand; if approved, your access key arrives from them directly.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <label className="block">
              <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                name
              </span>
              <input
                type="text"
                required
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Mira Vale"
                className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
                autoFocus
              />
            </label>

            <label className="block">
              <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                email
              </span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@somewhere.green"
                className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
              />
            </label>

            <label className="block">
              <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                team <span className="normal-case text-fg-dim">(optional)</span>
              </span>
              <input
                type="text"
                maxLength={80}
                value={team}
                onChange={(e) => setTeam(e.target.value)}
                placeholder="The Foragers"
                className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
              />
            </label>

            <label className="block">
              <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                what would you build? <span className="normal-case text-fg-dim">(optional)</span>
              </span>
              <textarea
                rows={4}
                maxLength={2000}
                value={interest}
                onChange={(e) => setInterest(e.target.value)}
                placeholder="A sketch is enough."
                className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow resize-y"
              />
            </label>

            {error && (
              <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
                ✕ {error}
              </p>
            )}

            <button type="submit" className="btn w-full justify-center" disabled={busy}>
              {busy ? 'filing…' : 'file the petition →'}
            </button>

            <p className="font-mono text-[0.7rem] text-fg-dim pt-2 text-center">
              already hold a key?{' '}
              <a href="/signin/" className="text-primary hover:underline underline-offset-4">
                sign in
              </a>
            </p>
          </form>
        </>
      )}

      {step === 'filed' && (
        <>
          <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
            ritual.applications.filed()
          </p>
          <h1 className="font-display italic text-4xl text-fg mb-3">The petition is filed.</h1>
          <p className="ritual text-fg-muted text-[1.02rem] mb-8 leading-relaxed">
            The organizers will read it. If you are admitted, your access key
            will reach you from their own hands — watch your inbox.
          </p>

          <div className="ascii-frame p-5 mb-6 font-mono text-[0.82rem]">
            <p className="text-primary mb-2">
              ▸ filed for <span className="text-fg">{email || 'you'}</span>
            </p>
            <p className="text-fg-muted leading-relaxed">
              Nothing more is needed from you now. The ritual will call when it is ready.
            </p>
          </div>

          <a href="/" className="btn w-full justify-center">
            ← back to the grounds
          </a>
        </>
      )}
    </section>
  );
}
