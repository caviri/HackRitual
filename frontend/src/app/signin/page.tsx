'use client';

import { useRef, useState } from 'react';
import { api, ApiError } from '../../lib/api';

type Step = 'speak-name' | 'speak-code' | 'admitted';

export default function SignInPage() {
  const [step, setStep] = useState<Step>('speak-name');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState<string[]>(Array(6).fill(''));
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  async function submitEmail(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.requestCode(email);
      setHint('a real code was sent to your inbox (or to stdout in dev mode)');
    } catch (err) {
      // 404 / 405 / network error → backend not present, slip into demo mode.
      // Other 4xx/5xx (e.g. 429 rate limit) → surface the real error.
      const transparentFailure =
        !(err instanceof ApiError) ||
        err.status === 404 ||
        err.status === 405 ||
        err.status === 0;
      if (transparentFailure) {
        setHint('demo mode — no backend reachable. any non-zero code admits.');
      } else if (err instanceof ApiError) {
        setError(err.body || `request failed (${err.status})`);
        setBusy(false);
        return;
      }
    }
    setStep('speak-code');
    setBusy(false);
    setTimeout(() => inputs.current[0]?.focus(), 50);
  }

  function setCodeAt(i: number, v: string) {
    const clean = v.replace(/\D/g, '').slice(-1);
    setCode((prev) => {
      const next = [...prev];
      next[i] = clean;
      return next;
    });
    if (clean && i < 5) inputs.current[i + 1]?.focus();
  }

  function onCodeKey(i: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !code[i] && i > 0) {
      inputs.current[i - 1]?.focus();
    } else if (e.key === 'ArrowLeft' && i > 0) {
      inputs.current[i - 1]?.focus();
    } else if (e.key === 'ArrowRight' && i < 5) {
      inputs.current[i + 1]?.focus();
    }
  }

  function onCodePaste(e: React.ClipboardEvent<HTMLInputElement>) {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;
    e.preventDefault();
    const next = pasted.split('').concat(Array(6 - pasted.length).fill(''));
    setCode(next);
    inputs.current[Math.min(pasted.length, 5)]?.focus();
  }

  async function submitCode(e: React.FormEvent) {
    e.preventDefault();
    const value = code.join('');
    if (value.length < 6) {
      setError('Six glyphs are required.');
      return;
    }
    if (value === '000000') {
      setError('The code was not recognised. Speak it again.');
      setCode(Array(6).fill(''));
      inputs.current[0]?.focus();
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.verifyCode(email, value);
      setStep('admitted');
    } catch (err) {
      // 404 / 405 / network: no backend → demo-mode admit
      const transparentFailure =
        !(err instanceof ApiError) ||
        err.status === 404 ||
        err.status === 405 ||
        err.status === 0;
      if (transparentFailure) {
        setStep('admitted');
      } else if (err instanceof ApiError) {
        setError(err.body || `verification failed (${err.status})`);
        setCode(Array(6).fill(''));
        inputs.current[0]?.focus();
      }
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setStep('speak-name');
    setCode(Array(6).fill(''));
    setError(null);
    setHint(null);
  }

  return (
    <section className="mx-auto w-full max-w-md px-6 py-20">
      <ol className="flex items-center gap-2 mb-10 font-mono text-[0.7rem] uppercase tracking-widest">
        {(['speak-name', 'speak-code', 'admitted'] as Step[]).map((s, i) => {
          const idx = (['speak-name', 'speak-code', 'admitted'] as Step[]).indexOf(step);
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
              {i < 2 && <span className="text-fg-dim" aria-hidden>─</span>}
            </li>
          );
        })}
      </ol>

      {step === 'speak-name' && (
        <>
          <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
            ritual.auth.magic_link()
          </p>
          <h1 className="font-display italic text-4xl text-fg mb-3">Speak your name.</h1>
          <p className="ritual text-fg-muted text-[1.02rem] mb-10 leading-relaxed">
            We send a six-glyph code to your address. No passwords — the ritual does not require them.
          </p>

          <form onSubmit={submitEmail} className="space-y-4">
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
                autoFocus
              />
            </label>
            {error && (
              <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
                ✕ {error}
              </p>
            )}
            <button type="submit" className="btn w-full justify-center" disabled={busy}>
              {busy ? 'sending…' : 'send the code →'}
            </button>
          </form>
        </>
      )}

      {step === 'speak-code' && (
        <>
          <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
            ritual.auth.verify({JSON.stringify(email || 'you@somewhere.green')})
          </p>
          <h1 className="font-display italic text-4xl text-fg mb-3">Speak the six glyphs.</h1>
          <p className="ritual text-fg-muted text-[1.02rem] mb-8 leading-relaxed">
            A code has been sent to{' '}
            <span className="font-mono not-italic text-fg">{email || 'your inbox'}</span>.
            It holds for ten minutes.
          </p>

          {hint && (
            <p className="font-mono text-[0.72rem] text-warm mb-4">▸ {hint}</p>
          )}

          <form onSubmit={submitCode}>
            <div className="flex justify-between gap-2 mb-3" role="group" aria-label="six-glyph code">
              {code.map((v, i) => (
                <input
                  key={i}
                  ref={(el) => {
                    inputs.current[i] = el;
                  }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={v}
                  onChange={(e) => setCodeAt(i, e.target.value)}
                  onKeyDown={(e) => onCodeKey(i, e)}
                  onPaste={onCodePaste}
                  aria-label={`glyph ${i + 1} of 6`}
                  className="w-12 h-14 text-center bg-bg-elev border border-rule text-fg font-mono text-2xl tabular-nums outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
                />
              ))}
            </div>

            <p className="font-mono text-[0.7rem] text-fg-dim mb-6">
              ▒ paste a 6-digit code to fill all slots ·{' '}
              <span className="text-warm">try 000000 to feel a rejection</span>
            </p>

            {error && (
              <p className="ascii-frame !border-danger px-3 py-2 mb-4 font-mono text-[0.78rem] text-danger">
                ✕ {error}
              </p>
            )}

            <div className="flex flex-col gap-2">
              <button type="submit" className="btn w-full justify-center" disabled={busy}>
                {busy ? 'verifying…' : 'step through the gate →'}
              </button>
              <button
                type="button"
                onClick={reset}
                className="font-mono text-[0.72rem] text-fg-muted hover:text-fg uppercase tracking-widest text-center pt-2"
              >
                ← use a different name
              </button>
            </div>
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
