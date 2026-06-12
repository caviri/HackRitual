'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../../components/page-header';
import { CMS_PAGES } from '../../../lib/mocks';
import { api, ApiError, backendPresent, type PageDTO } from '../../../lib/api';

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
  visible: boolean;
  dto?: PageDTO;
}

function describeError(err: unknown, verb: string): string {
  if (err instanceof ApiError) return err.body || `${verb} failed (${err.status})`;
  return String(err);
}

export default function AdminPagesPage() {
  const [live, setLive] = useState<boolean | null>(null);
  const [livePages, setLivePages] = useState<PageDTO[]>([]);

  // composer
  const [composing, setComposing] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [busy, setBusy] = useState(false);

  // inline edit
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void backendPresent().then(async (ok) => {
      if (ok) setLivePages(await api.pages());
      setLive(ok);
    });
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.createPage({
        title: title.trim(),
        content: content.trim(),
      });
      setLivePages((prev) => [...prev, created]);
      setTitle('');
      setContent('');
      setComposing(false);
    } catch (err) {
      setError(describeError(err, 'authoring'));
    } finally {
      setBusy(false);
    }
  }

  function beginEdit(p: PageDTO) {
    setEditingId(p.id);
    setEditTitle(p.title);
    setEditContent(p.content);
    setError(null);
  }

  async function saveEdit(e: React.FormEvent, p: PageDTO) {
    e.preventDefault();
    setBusyId(p.id);
    setError(null);
    try {
      const updated = await api.updatePage(p.id, {
        title: editTitle.trim(),
        content: editContent,
      });
      setLivePages((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      setEditingId(null);
    } catch (err) {
      setError(describeError(err, 'update'));
    } finally {
      setBusyId(null);
    }
  }

  async function toggleVisible(p: PageDTO) {
    setBusyId(p.id);
    setError(null);
    try {
      const updated = await api.updatePage(p.id, { visible: !p.visible });
      setLivePages((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      setError(describeError(err, 'update'));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(p: PageDTO) {
    if (!confirm(`Remove the page "${p.title}"?`)) return;
    setBusyId(p.id);
    setError(null);
    try {
      await api.deletePage(p.id);
      setLivePages((prev) => prev.filter((x) => x.id !== p.id));
      if (editingId === p.id) setEditingId(null);
    } catch (err) {
      setError(describeError(err, 'removal'));
    } finally {
      setBusyId(null);
    }
  }

  // live !== false → API data (even when empty); mocks only when backend absent
  const rows: Row[] =
    live !== false
      ? livePages.map((p) => ({
          key: p.id,
          slug: pageSlug(p.title),
          title: p.title,
          blurb: p.content.split(/\n\n+/)[0].slice(0, 160),
          visible: p.visible,
          dto: p,
        }))
      : Object.values(CMS_PAGES).map((p) => ({
          key: p.slug,
          slug: p.slug,
          title: p.title,
          blurb: p.blurb,
          visible: true,
        }));

  const fieldClass =
    'mt-2 w-full bg-bg-elev border border-rule text-fg font-mono px-3 py-2.5 outline-none focus:border-primary transition-colors';
  const labelClass = 'font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim';

  return (
    <>
      <PageHeader
        prompt="ritual.admin.pages()"
        title="Content Pages"
        subtitle="Long-form pages the organisers author. Rules, schedule, sponsor info. Rendered as prose."
        chip={`${rows.length} authored`}
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-4">
        {error && (
          <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
            ✕ {error}
          </p>
        )}
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
          rows.map((p) =>
            p.dto && editingId === p.dto.id ? (
              <form
                key={p.key}
                onSubmit={(e) => void saveEdit(e, p.dto as PageDTO)}
                className="ascii-frame p-5 space-y-4"
              >
                <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                  edit page
                </p>
                <label className="block">
                  <span className={labelClass}>title</span>
                  <input
                    type="text"
                    required
                    maxLength={200}
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className={fieldClass}
                  />
                </label>
                <label className="block">
                  <span className={labelClass}>content</span>
                  <textarea
                    required
                    rows={10}
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className={`${fieldClass} resize-y`}
                  />
                </label>
                <div className="flex gap-2">
                  <button type="submit" className="btn" disabled={busyId === p.dto.id}>
                    {busyId === p.dto.id ? 'inscribing…' : '◆ save'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={busyId === p.dto.id}
                    onClick={() => setEditingId(null)}
                  >
                    cancel
                  </button>
                </div>
              </form>
            ) : (
              <article
                key={p.key}
                className={`ascii-frame p-5 ${p.visible ? '' : 'opacity-60'}`}
              >
                <header className="flex flex-wrap items-baseline justify-between gap-3 mb-2">
                  <h2 className="font-display italic text-2xl text-fg">{p.title}</h2>
                  <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                    /pages/{p.slug}
                    {live === true && p.dto && (
                      <>
                        {' · '}
                        <span className={p.visible ? 'text-primary' : 'text-warm'}>
                          {p.visible ? '◆ visible' : '▒ hidden'}
                        </span>
                      </>
                    )}
                  </span>
                </header>
                <p className="text-fg-muted text-[0.92rem] mb-4">{p.blurb}</p>
                <div className="flex flex-wrap gap-3 font-mono text-[0.72rem] uppercase tracking-widest items-center">
                  <Link
                    href={`/pages/${p.slug}/`}
                    className="text-primary hover:underline"
                  >
                    ▸ view
                  </Link>
                  {live === true && p.dto && (
                    <>
                      <button
                        type="button"
                        disabled={busyId === p.dto.id}
                        onClick={() => beginEdit(p.dto as PageDTO)}
                        className="text-fg-muted hover:text-fg disabled:opacity-50"
                      >
                        ▸ edit
                      </button>
                      <button
                        type="button"
                        disabled={busyId === p.dto.id}
                        onClick={() => void toggleVisible(p.dto as PageDTO)}
                        className="text-fg-muted hover:text-fg disabled:opacity-50"
                      >
                        {p.visible ? '▒ hide' : '◆ show'}
                      </button>
                      <button
                        type="button"
                        disabled={busyId === p.dto.id}
                        onClick={() => void remove(p.dto as PageDTO)}
                        className="text-danger hover:underline disabled:opacity-50"
                      >
                        ✕ remove
                      </button>
                    </>
                  )}
                </div>
              </article>
            ),
          )
        )}
        {live === true &&
          (composing ? (
            <form onSubmit={create} className="ascii-frame p-5 space-y-4">
              <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
                author a new page
              </p>
              <label className="block">
                <span className={labelClass}>title</span>
                <input
                  type="text"
                  required
                  maxLength={200}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="The Rites"
                  className={fieldClass}
                />
              </label>
              <label className="block">
                <span className={labelClass}>content</span>
                <textarea
                  required
                  rows={10}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Write it as prose. The first paragraph becomes the blurb."
                  className={`${fieldClass} resize-y`}
                />
              </label>
              <div className="flex gap-2">
                <button type="submit" className="btn" disabled={busy}>
                  {busy ? 'inscribing…' : '◆ author page'}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={busy}
                  onClick={() => setComposing(false)}
                >
                  cancel
                </button>
              </div>
            </form>
          ) : (
            <button type="button" className="btn" onClick={() => setComposing(true)}>
              ◆ author a new page
            </button>
          ))}
      </section>
    </>
  );
}
