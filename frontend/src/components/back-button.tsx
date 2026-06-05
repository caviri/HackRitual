'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface Props {
  /**
   * - Omit or `true` → router.back() (uses browser history)
   * - A string      → renders as a Link to that path
   * - `false`       → not rendered (parent shouldn't include the button)
   */
  to?: string | boolean;
  label?: string;
}

/**
 * Slim back affordance — terminal-styled, sits inline above the page header.
 * When given an explicit `to`, behaves as an anchor (better for screen readers
 * and middle-click). When omitted, uses router.back() — falls back to "/"
 * if there is no history (e.g. cold page load).
 */
export function BackButton({ to, label = 'back' }: Props) {
  const router = useRouter();
  if (to === false) return null;

  const className =
    'inline-flex items-center gap-1.5 font-mono text-[0.72rem] uppercase tracking-widest text-fg-muted hover:text-primary transition-colors';

  if (typeof to === 'string') {
    return (
      <Link href={to} className={className}>
        <span aria-hidden>←</span> {label}
      </Link>
    );
  }

  function onClick(e: React.MouseEvent) {
    e.preventDefault();
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back();
    } else {
      router.push('/');
    }
  }

  return (
    <a href="/" onClick={onClick} className={className}>
      <span aria-hidden>←</span> {label}
    </a>
  );
}
