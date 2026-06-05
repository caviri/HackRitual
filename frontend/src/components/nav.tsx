'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';

const LINKS = [
  { href: '/overview/', label: 'overview' },
  { href: '/projects/', label: 'projects' },
  { href: '/teams/', label: 'teams' },
  { href: '/participants/', label: 'participants' },
  { href: '/timeline/', label: 'timeline' },
  { href: '/docs/', label: 'handbook' },
];

interface Me {
  id: string;
  email: string;
  role: string;
  display_name?: string | null;
  participant?: { id: string; display_name: string; type: string } | null;
  portrait?: {
    url: string | null;
    effect: string | null;
    contrast: number | null;
    brightness: number | null;
  } | null;
}

export function Nav() {
  const [me, setMe] = useState<Me | null | undefined>(undefined); // undefined = loading
  const [open, setOpen] = useState(false);
  const popRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void api.me().then((u) => setMe(u as Me | null));
  }, []);

  // close dropdown on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!popRef.current?.contains(e.target as Node)) setOpen(false);
    }
    if (open) window.addEventListener('mousedown', onClick);
    return () => window.removeEventListener('mousedown', onClick);
  }, [open]);

  async function signOut() {
    await api.logout();
    window.location.href = '/';
  }

  const rawHandle =
    me?.participant?.display_name ||
    me?.email?.split('@')[0] ||
    '';
  const handleBase =
    rawHandle.length > 12 ? rawHandle.slice(0, 11) + '…' : rawHandle;
  const isAdmin = me?.role === 'admin';

  return (
    <header className="border-b border-rule">
      <div className="mx-auto w-full max-w-6xl flex items-center justify-between gap-4 px-6 py-4">
        <Link href="/" className="group inline-flex items-center gap-2.5 no-underline">
          <span className="text-primary text-lg" aria-hidden>◆</span>
          <span className="font-display text-xl leading-none text-fg group-hover:text-primary transition-colors glow-rule">
            HackRitual
          </span>
          <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim ml-2">
            v0.1
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-5 lg:gap-6 font-mono text-[0.78rem] uppercase tracking-wider min-w-0">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-fg-muted hover:text-fg transition-colors whitespace-nowrap hidden lg:inline"
            >
              {l.label}
            </Link>
          ))}
          {/* on md (below lg) we keep just the core 3 to leave room for the chip */}
          {LINKS.slice(0, 3).map((l) => (
            <Link
              key={`md-${l.href}`}
              href={l.href}
              className="text-fg-muted hover:text-fg transition-colors whitespace-nowrap lg:hidden"
            >
              {l.label}
            </Link>
          ))}

          {/* identity slot */}
          {me === undefined && (
            <span className="font-mono text-[0.7rem] text-fg-dim animate-pulse">
              …
            </span>
          )}

          {me === null && (
            <Link href="/signin/" className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem]">
              sign in
            </Link>
          )}

          {me && (
            <div ref={popRef} className="relative">
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className="inline-flex items-center gap-1.5 border border-rule hover:border-primary transition-colors px-2 py-1 text-[0.7rem] tracking-wider whitespace-nowrap max-w-[14rem]"
                aria-haspopup="menu"
                aria-expanded={open}
                title={me?.email}
              >
                {me.portrait?.url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={me.portrait.url}
                    alt=""
                    className="w-5 h-5 object-cover border border-rule"
                    style={{ imageRendering: 'pixelated' }}
                    aria-hidden
                  />
                ) : (
                  <span
                    className={isAdmin ? 'text-accent' : 'text-primary'}
                    aria-hidden
                  >
                    {isAdmin ? '✦' : '◆'}
                  </span>
                )}
                <span className="text-fg font-mono lowercase tracking-normal truncate">
                  {handleBase}
                </span>
                <span className="text-fg-dim" aria-hidden>
                  {open ? '▴' : '▾'}
                </span>
              </button>

              {open && (
                <div
                  role="menu"
                  className="absolute right-0 top-full mt-2 w-64 ascii-frame z-50 animate-rise"
                >
                  <div className="px-4 py-3 border-b border-rule">
                    <p className="font-mono text-[0.78rem] text-fg truncate">
                      {me.email}
                    </p>
                    <p className="font-mono text-[0.66rem] uppercase tracking-widest text-fg-dim mt-0.5">
                      {isAdmin ? '✦ admin' : '◆ participant'}
                      {me.participant && (
                        <> · {me.participant.display_name}</>
                      )}
                    </p>
                  </div>
                  <ul className="py-1.5 font-mono text-[0.85rem]">
                    <li>
                      <Link
                        href="/overview/"
                        onClick={() => setOpen(false)}
                        className="block px-4 py-2 text-fg-muted hover:text-primary hover:bg-bg-elev transition-colors"
                      >
                        ▸ your overview
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/profile/"
                        onClick={() => setOpen(false)}
                        className="block px-4 py-2 text-fg-muted hover:text-primary hover:bg-bg-elev transition-colors"
                      >
                        ▸ your portrait
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/profile/agents/"
                        onClick={() => setOpen(false)}
                        className="block px-4 py-2 text-fg-muted hover:text-primary hover:bg-bg-elev transition-colors"
                      >
                        ▸ your agents
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/projects/"
                        onClick={() => setOpen(false)}
                        className="block px-4 py-2 text-fg-muted hover:text-primary hover:bg-bg-elev transition-colors"
                      >
                        ▸ browse projects
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/projects/new/"
                        onClick={() => setOpen(false)}
                        className="block px-4 py-2 text-fg-muted hover:text-primary hover:bg-bg-elev transition-colors"
                      >
                        ◆ propose a project
                      </Link>
                    </li>
                    {isAdmin && (
                      <li>
                        <Link
                          href="/admin/"
                          onClick={() => setOpen(false)}
                          className="block px-4 py-2 text-accent hover:text-primary hover:bg-bg-elev transition-colors"
                        >
                          ✦ admin console
                        </Link>
                      </li>
                    )}
                  </ul>
                  <div className="border-t border-rule">
                    <button
                      type="button"
                      onClick={signOut}
                      className="w-full text-left px-4 py-2.5 font-mono text-[0.78rem] text-danger hover:bg-bg-elev transition-colors"
                    >
                      ✕ sign out
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
