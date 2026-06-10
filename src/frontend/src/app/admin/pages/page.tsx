'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import { CMS_PAGES } from '../../../lib/mocks';
import { api, backendPresent, type PageDTO } from '../../../lib/api';

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/** "The Rites" → "rites" — the slug the public /pages/ route resolves. */
function pageSlug(title: string): string {
  return slugify(title.replace(/^(the|a few|a|an)\s+/i, ''));
}

interface Row {
  key: string;
  slug: string;
  title: string;
  blurb: string;
}

export default function AdminPagesPage() {
  const [live, setLive] = useState<boolean | null>(null);
  const [livePages, setLivePages] = useState<PageDTO[]>([]);

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) setLivePages(await api.pages());
      setLive(ok);
    });
  }, []);

  // live !== false → API data (even when empty); mocks only when backend absent
  const rows: Row[] =
    live !== false
      ? livePages.map((p) => ({
          key: p.id,
          slug: pageSlug(p.title),
          title: p.title,
          blurb: p.content.split(/\n\n+/)[0].slice(0, 160),
        }))
      : Object.values(CMS_PAGES).map((p) => ({
          key: p.slug,
          slug: p.slug,
          title: p.title,
          blurb: p.blurb,
        }));

  return (
    <>
      <PageHeader
        prompt="ritual.admin.pages()"
        title="Content Pages"
        subtitle="Long-form pages the organisers author. Rules, schedule, sponsor info. Rendered as prose."
        chip={`${rows.length} authored`}
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-4">
        {rows.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ pages.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No pages have been authored yet.
            </p>
          </div>
        ) : (
          rows.map((p) => (
            <article key={p.key} className="ascii-frame p-5">
              <header className="flex flex-wrap items-baseline justify-between gap-3 mb-2">
                <h2 className="font-display italic text-2xl text-fg">{p.title}</h2>
                <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                  /pages/{p.slug}
                </span>
              </header>
              <p className="text-fg-muted text-[0.92rem] mb-4">{p.blurb}</p>
              <div className="flex gap-3 font-mono text-[0.72rem] uppercase tracking-widest">
                <Link
                  href={`/pages/${p.slug}/`}
                  className="text-primary hover:underline"
                >
                  ▸ view
                </Link>
                <button type="button" className="text-fg-muted hover:text-fg">
                  ▸ edit
                </button>
                <button type="button" className="text-fg-muted hover:text-fg">
                  ▸ toggle visibility
                </button>
              </div>
            </article>
          ))
        )}
        <button type="button" className="btn">
          ◆ author a new page
        </button>
      </section>
    </>
  );
}
