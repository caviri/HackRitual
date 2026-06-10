'use client';

import Link from 'next/link';
import { PageHeader } from '../../../components/page-header';
import { CMS_PAGES } from '../../../lib/mocks';

export default function AdminPagesPage() {
  const pages = Object.values(CMS_PAGES);
  return (
    <>
      <PageHeader
        prompt="ritual.admin.pages()"
        title="Content Pages"
        subtitle="Long-form pages the organisers author. Rules, schedule, sponsor info. Rendered as prose."
        chip={`${pages.length} authored`}
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-4">
        {pages.map((p) => (
          <article key={p.slug} className="ascii-frame p-5">
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
        ))}
        <button type="button" className="btn">
          ◆ author a new page
        </button>
      </section>
    </>
  );
}
