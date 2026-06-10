'use client';

import { useEffect } from 'react';
import Link from 'next/link';

/**
 * Global error boundary — replaces Next.js's "Application error" generic page.
 * Shows the real error message + a stack frame so debugging on the deployed
 * site is possible without opening DevTools.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // surface to the browser console too
    // eslint-disable-next-line no-console
    console.error('hackritual error boundary:', error);
  }, [error]);

  const firstFrame = (error.stack ?? '').split('\n').slice(0, 6).join('\n');

  return (
    <section className="mx-auto w-full max-w-2xl px-6 py-24">
      <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
        ritual.error()
      </p>
      <h1 className="font-display italic text-4xl text-fg mb-3">
        The ritual stumbled.
      </h1>
      <p className="ritual text-fg-muted text-[1.05rem] mb-6">
        An error broke the page. Nothing important was lost — the ritual
        continues in the background.
      </p>

      <pre className="ascii-frame !border-danger p-4 mb-4 font-mono text-[0.78rem] text-danger whitespace-pre-wrap break-all">
        {error.message || 'no message'}
        {error.digest && (
          <>
            {'\n\n'}
            <span className="text-fg-dim">digest </span>
            {error.digest}
          </>
        )}
      </pre>

      {firstFrame && (
        <details className="font-mono text-[0.72rem] text-fg-muted mb-6">
          <summary className="cursor-pointer text-fg-dim uppercase tracking-widest mb-2">
            ▸ stack (top frames)
          </summary>
          <pre className="border border-rule p-3 whitespace-pre-wrap break-all">{firstFrame}</pre>
        </details>
      )}

      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={reset} className="btn">
          ↺ try again
        </button>
        <Link href="/" className="btn btn-ghost">
          back to the circle
        </Link>
      </div>
    </section>
  );
}
