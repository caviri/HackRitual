'use client';

import { useState } from 'react';
import { api, ApiError } from '../../lib/api';

type Step = 'speak-key' | 'admitted';

export default function SignInPage() {
  const [step, setStep] = useState<Step>('speak-key');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submitPassword(e: React.FormEvent) {
    e.preventDefault();
    const value = password.trim();
    if (value.length < 4) {
      setError('Speak the full key you were handed.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(value);
      setEmail(res.user.email);
      setStep('admitted');
    } catch (err) {
      // 404 / 405 / network: no backend → demo-mode admit
      const transparentFailure =
        !(err instanceof ApiError) ||
        err.status === 404 ||
        err.status === 405 ||
        err.status === 0;
      if (transparentFailure) {
        setHint('demo mode — no backend reachable. any key admits.');
        setStep('admitted');
      } else if (err instanceof ApiError) {
        setError(
          err.status === 429
            ? 'Too many attempts. The gate rests a few minutes.'
            : 'The key was not recognised. Speak it again.',
        );
        setPassword('');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto w-full max-w-md px-6 py-20">
      <ol className="flex items-center gap-2 mb-10 font-mono text-[0.7rem] uppercase tracking-widest">
        {(['speak-key', 'admitted'] as Step[]).map((s, i) => {
          const idx = (['speak-key', 'admitted'] as Step[]).indexOf(step);
          const active = s === step;
          const done = i < idx;
          return (
            <li key={s} className="flex items-center gap-2">
              <span className={active ? 'text-primary' : done ? 'text-fg-muted' : 'text-fg-dim'}>
                <span aria-hidden className="mr-1.5">
                  {active ? '▸' : done ? '✓' : '◇'}
                </span>
                {s.replace('-', ' ')}
              </span>
              {i < 1 && <span className="text-fg-dim" aria-hidden>─</span>}
            </li>
          );
        })}
      </ol>

      {step === 'speak-key' && (
        <>
          <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
            ritual.auth.access_key()
          </p>
          <h1 className="font-display italic text-4xl text-fg mb-3">Speak your key.</h1>
          <p className="ritual text-fg-muted text-[1.02rem] mb-10 leading-relaxed">
            The organizers handed you an access key — three words bound by hyphens.
            It is your name and your passage. Haven&apos;t one?{' '}
            <a href="/apply/" className="text-primary underline-offset-4 hover:underline">
              Petition to join.
            </a>
          </p>

          <form onSubmit={submitPassword} className="space-y-4">
            <label className="block">
              <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
                access key
              </span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="ember-crow-7421"
                autoComplete="current-password"
                className="mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-3 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
                autoFocus
              />
            </label>
            {hint && (
              <p className="font-mono text-[0.72rem] text-warm">▸ {hint}</p>
            )}
            {error && (
              <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
                ✕ {error}
              </p>
            )}
            <button type="submit" className="btn w-full justify-center" disabled={busy}>
              {busy ? 'verifying…' : 'step through the gate →'}
            </button>
          </form>
        </>
      )}

      {step === 'admitted' && (
        <>
          <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
            ritual.auth.session_created()
          </p>
          <h1 className="font-display italic text-4xl text-fg mb-3">You are in the circle.</h1>
          <p className="ritual text-fg-muted text-[1.02rem] mb-8 leading-relaxed">
            A session has been forged. You may now propose, join a team, and submit. The forge does not sleep.
          </p>

          <div className="ascii-frame p-5 mb-6 font-mono text-[0.82rem]">
            <p className="text-primary mb-2">
              ▸ welcome, <span className="text-fg">{email || 'you'}</span>
            </p>
            <p className="text-fg-muted leading-relaxed">
              Your handle, team, and project will be on the overview. Take your time — the ritual will wait.
            </p>
          </div>

          <div className="flex gap-3">
            <a href="/overview/" className="btn flex-1 justify-center">
              ▸ to your overview
            </a>
            <a href="/projects/" className="btn btn-ghost flex-1 justify-center">
              browse projects
            </a>
          </div>
        </>
      )}
    </section>
  );
}
