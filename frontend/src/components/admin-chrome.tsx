'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface BandProps {
  top?: boolean;
  message: string;
}

/**
 * Jurassic-Park-style hazard band: ochre + soil diagonal stripes with a
 * scrolling animation, plus a centered mono-uppercase banner inset that says
 * "you are in the keeper's zone".
 *
 * Two heights are exposed via the `top` flag — the top band sits flush under
 * the global nav; the bottom band acts as a closing seal.
 */
export function WarningBand({ message }: BandProps) {
  return (
    <div className="warning-band" role="presentation">
      <span className="warning-band__text">{message}</span>
    </div>
  );
}

const ADMIN_LINKS = [
  { href: '/admin/', label: 'overview', glyph: '◆' },
  { href: '/admin/proposals/', label: 'proposals', glyph: '◇' },
  { href: '/admin/judging/', label: 'judging', glyph: '✺' },
  { href: '/admin/agents/', label: 'agents', glyph: '▰' },
  { href: '/admin/tracks/', label: 'tracks', glyph: '✦' },
  { href: '/admin/phases/', label: 'phases', glyph: '▢' },
  { href: '/admin/pages/', label: 'pages', glyph: '▒' },
];

export function AdminSubNav() {
  const pathname = usePathname() ?? '';
  return (
    <nav
      aria-label="admin sections"
      className="border-b border-rule bg-bg-elev"
    >
      <ul className="mx-auto w-full max-w-6xl px-6 py-2 flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-[0.72rem] uppercase tracking-widest">
        <li className="text-fg-dim mr-2">
          <span className="text-warm">✦</span> keeper&apos;s console
        </li>
        {ADMIN_LINKS.map((l) => {
          const active =
            l.href === '/admin/'
              ? pathname === '/admin' || pathname === '/admin/'
              : pathname.startsWith(l.href.replace(/\/$/, ''));
          return (
            <li key={l.href}>
              <Link
                href={l.href}
                className={`inline-flex items-center gap-1.5 transition-colors ${
                  active
                    ? 'text-primary'
                    : 'text-fg-muted hover:text-fg'
                }`}
              >
                <span
                  aria-hidden
                  className={active ? 'text-primary' : 'text-fg-dim'}
                >
                  {l.glyph}
                </span>
                {l.label}
                {active && (
                  <span aria-hidden className="text-primary ml-0.5">
                    ▸
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
