'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader } from '../../../components/page-header';
import { CMS_PAGES } from '../../../lib/mocks';

export function CmsView() {
  const params = useParams();
  const slug = String(params?.slug ?? 'rites');
  const page = CMS_PAGES[slug] ?? CMS_PAGES.rites;

  return (
    <>
      <PageHeader
        prompt={`ritual.page('${page.slug}')`}
        title={page.title}
        subtitle={page.blurb}
        back="/"
        backLabel="back to circle"
      />

      <article className="mx-auto w-full max-w-2xl px-6 py-16 prose-ritual">
        {page.body.map((para, i) => (
          <p
            key={i}
            className="text-fg leading-[1.75] text-[1.05rem] mb-6"
            dangerouslySetInnerHTML={{
              __html: para
                .replace(/\*\*(.+?)\*\*/g, '<strong class="text-primary font-mono uppercase tracking-wider text-[0.92em]">$1</strong>')
                .replace(/`([^`]+)`/g, '<code class="font-mono text-[0.85em] text-warm">$1</code>'),
            }}
          />
        ))}

        <nav className="mt-12 pt-8 border-t border-rule flex flex-wrap gap-3 font-mono text-[0.78rem] text-fg-muted">
          <span className="text-fg-dim mr-2">other pages:</span>
          {Object.values(CMS_PAGES)
            .filter((p) => p.slug !== page.slug)
            .map((p) => (
              <Link
                key={p.slug}
                href={`/pages/${p.slug}/`}
                className="text-primary hover:underline"
              >
                ▸ {p.title}
              </Link>
            ))}
        </nav>
      </article>
    </>
  );
}
