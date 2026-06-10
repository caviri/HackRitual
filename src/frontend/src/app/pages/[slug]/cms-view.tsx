'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
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

/** "The Rites" → "rites", "A Few Questions" → "few-questions" / "questions". */
function slugCandidates(title: string): string[] {
  const stripped = title.replace(/^(the|a few|a|an)\s+/i, '');
  return [slugify(title), slugify(stripped)];
}

function matchesSlug(slug: string, title: string): boolean {
  return slugCandidates(title).includes(slug);
}

/** The slug we link a live page under — title minus its leading article. */
function pageSlug(title: string): string {
  const candidates = slugCandidates(title);
  return candidates[candidates.length - 1];
}

export function CmsView() {
  const params = useParams();
  const slug = String(params?.slug ?? 'rites');
  const [live, setLive] = useState<boolean | null>(null);
  const [livePages, setLivePages] = useState<PageDTO[]>([]);

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) {
        const pages = await api.pages();
        setLivePages(pages.filter((p) => p.visible !== false));
      }
      setLive(ok);
    });
  }, []);

  // Probe in flight — brief blank rather than a mock (or not-found) flash.
  if (live === null) return null;

  // ── LIVE backend: render the CMS rows, even when the slug is unknown ──
  if (live === true) {
    const page = livePages.find((p) => matchesSlug(slug, p.title));
    if (!page) {
      return (
        <section className="mx-auto w-full max-w-2xl px-6 py-24">
          <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
            ritual.page({JSON.stringify(slug)})
          </p>
          <h1 className="font-display italic text-4xl text-fg mb-3">Unknown page.</h1>
          <p className="ritual text-fg-muted mb-6">
            No page by that name is inscribed in this ritual.
          </p>
          <Link href="/" className="btn">
            ← back to circle
          </Link>
        </section>
      );
    }

    const paragraphs = page.content
      .split(/\n\n+/)
      .map((p) => p.trim())
      .filter(Boolean);

    return (
      <>
        <PageHeader
          prompt={`ritual.page('${pageSlug(page.title)}')`}
          title={page.title}
          back="/"
          backLabel="back to circle"
        />

        <article className="mx-auto w-full max-w-2xl px-6 py-16 prose-ritual">
          {paragraphs.map((para, i) => (
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
            {livePages
              .filter((p) => p.id !== page.id)
              .map((p) => (
                <Link
                  key={p.id}
                  href={`/pages/${pageSlug(p.title)}/`}
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

  // ── MOCK mode (backend absent) ──
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
