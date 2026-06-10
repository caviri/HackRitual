'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../lib/api';
import { backendAvailable } from '../lib/use-stage';

type Gate = 'checking' | 'allowed' | 'denied';

/**
 * Client-side gate for the keeper's console.
 *
 * The app ships as a static export, so there is no server-side auth boundary —
 * the real wall is the API (`require_admin` on every `/api/admin/*` route).
 * This guard is the matching front-of-house: it asks `/api/auth/me` and only
 * renders the console for an admin session.
 *
 * Demo mode is preserved deliberately. When no backend is reachable (the static
 * export served on its own, `event_id === 'demo'`), the guard lets the UI
 * through so the console can still be explored. A live backend with a
 * non-admin (or absent) session is redirected to the gate.
 */
export function AuthGuard({
  children,
  role = 'admin',
  redirectTo = '/signin/',
}: {
  children: React.ReactNode;
  role?: string;
  redirectTo?: string;
}) {
  const router = useRouter();
  const [gate, setGate] = useState<Gate>('checking');

  useEffect(() => {
    let cancelled = false;

    async function check() {
      const me = await api.me();
      if (cancelled) return;

      if (me?.role === role) {
        setGate('allowed');
        return;
      }

      // No matching session. If there's no live backend, this is the static
      // demo — let it through rather than trapping the visitor at the gate.
      const live = await backendAvailable();
      if (cancelled) return;

      if (!live) {
        setGate('allowed');
        return;
      }

      setGate('denied');
      router.replace(redirectTo);
    }

    void check();
    return () => {
      cancelled = true;
    };
  }, [role, redirectTo, router]);

  if (gate === 'allowed') return <>{children}</>;

  return (
    <section className="mx-auto w-full max-w-md px-6 py-24 text-center">
      <p className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim mb-3">
        ritual.auth.guard()
      </p>
      {gate === 'checking' ? (
        <p className="ritual text-fg-muted text-[1.05rem]">
          ▸ checking the seal…
        </p>
      ) : (
        <p className="ritual text-fg-muted text-[1.05rem]">
          ✕ the keeper&apos;s console is sealed. redirecting to the gate…
        </p>
      )}
    </section>
  );
}
