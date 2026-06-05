'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { api, ApiError, type ImageEffect, type MeDTO } from '../../lib/api';

const EFFECTS: { id: ImageEffect; label: string; blurb: string }[] = [
  { id: 'dither', label: 'dither', blurb: 'two-tone ordered noise · low-bandwidth' },
  { id: 'halftone', label: 'halftone', blurb: 'newsprint dot grid · archival' },
  { id: 'none', label: 'none', blurb: 'pass-through · unaltered' },
];

export default function ProfilePage() {
  const [me, setMe] = useState<MeDTO | null | undefined>(undefined);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [effect, setEffect] = useState<ImageEffect>('dither');
  const [contrast, setContrast] = useState(1.8);
  const [brightness, setBrightness] = useState(0);
  // chunk in [0,1]: 0 = no downsample (fine dither), 1 = heavy downsample
  // (chunky dither). Internally we convert to `scale` for the backend so it
  // is intuitive in the UI: slide right → more chunk.
  const [chunk, setChunk] = useState(0.7);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    void api.me().then((u) => {
      setMe(u);
      if (u?.portrait) {
        if (u.portrait.effect) setEffect(u.portrait.effect);
        if (u.portrait.contrast != null) setContrast(u.portrait.contrast);
        if (u.portrait.brightness != null) setBrightness(u.portrait.brightness);
        if (u.portrait.scale != null) setChunk(scaleToChunk(u.portrait.scale));
      }
    });
  }, []);

  // Maintain an object URL for the picked file. When `file` becomes null
  // (after a successful save), CLEAR the preview so the real server-side
  // portrait shows through instead of a stale blob URL.
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function chooseFile(f: File | null) {
    setError(null);
    setFlash(null);
    if (!f) return;
    if (!/^image\//.test(f.type)) {
      setError('only images please — png, jpg, webp, gif');
      return;
    }
    if (f.size > 4 * 1024 * 1024) {
      setError('the ritual carries little weight — max 4MB');
      return;
    }
    setFile(f);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.[0]) chooseFile(e.dataTransfer.files[0]);
  }

  async function save() {
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      let updated: MeDTO;
      const scaleValue = chunkToScale(chunk);
      if (file) {
        updated = await api.uploadPortrait(file, effect, contrast, brightness, scaleValue);
      } else if (me?.portrait?.url) {
        updated = await api.retunePortrait(effect, contrast, brightness, scaleValue);
      } else {
        setError('pick a file first');
        setBusy(false);
        return;
      }
      setMe(updated);
      setFile(null);
      setPreviewUrl(null);
      setFlash('the portrait was inscribed.');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.body || `save failed (${err.status})`);
      } else {
        setError('no backend reachable — nothing was saved');
      }
    } finally {
      setBusy(false);
    }
  }

  async function dispel() {
    if (!confirm('dispel the portrait? this cannot be undone.')) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.deletePortrait();
      setMe(updated);
      setFile(null);
      setFlash('the portrait has been dispelled.');
    } catch (err) {
      if (err instanceof ApiError) setError(err.body || 'delete failed');
    } finally {
      setBusy(false);
    }
  }

  if (me === undefined) {
    return (
      <section className="mx-auto w-full max-w-3xl px-6 py-24">
        <p className="font-mono text-fg-dim">summoning…</p>
      </section>
    );
  }

  if (me === null) {
    return (
      <section className="mx-auto w-full max-w-2xl px-6 py-24">
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-3">
          ritual.profile()
        </p>
        <h1 className="font-display italic text-4xl text-fg mb-3">
          You are not yet in the circle.
        </h1>
        <p className="ritual text-fg-muted mb-6">
          Sign in to inscribe a portrait of your own.
        </p>
        <Link href="/signin/" className="btn">▸ step into the circle</Link>
      </section>
    );
  }

  // The current preview source:
  //  - the just-picked file (object URL) takes priority
  //  - else the saved server-side portrait
  //  - else nothing (the right pane will show a placeholder)
  const showingNewFile = !!previewUrl;
  const portraitUrl = previewUrl ?? me.portrait?.url ?? null;

  return (
    <>
      <PageHeader
        prompt="ritual.profile()"
        title="Your Portrait"
        subtitle="Press your face into the ritual. Pick a treatment, tune the weight, save."
        chip={me.role === 'admin' ? '✦ admin' : '◆ participant'}
        back="/overview/"
        backLabel="overview"
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-12 grid gap-10 lg:grid-cols-[1fr_1.1fr]">
        {/* LEFT — current portrait / live preview of selected file */}
        <aside>
          <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
            {showingNewFile
              ? 'preview · raw upload (effect applied on save)'
              : me.portrait?.url
                ? 'current portrait · saved'
                : 'no portrait yet'}
          </p>
          <div className="ascii-frame aspect-square overflow-hidden bg-bg-elev relative">
            {portraitUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={portraitUrl}
                alt={me.email}
                className="w-full h-full object-cover"
                style={{
                  imageRendering: showingNewFile ? 'auto' : 'pixelated',
                  filter: showingNewFile ? previewFilter(effect) : undefined,
                }}
              />
            ) : (
              <div className="absolute inset-0 grid place-items-center font-mono text-[0.78rem] text-fg-dim">
                ◇ awaiting your likeness ◇
              </div>
            )}
            {me.portrait && (
              <span className="absolute top-1.5 right-1.5 z-10 font-mono text-[0.6rem] uppercase tracking-widest bg-bg/80 text-fg-dim px-1.5 py-0.5 border border-rule">
                {me.portrait.effect ?? 'none'}
              </span>
            )}
          </div>

          {me.portrait?.url && !showingNewFile && (
            <ul className="mt-4 font-mono text-[0.78rem] space-y-1">
              <li><span className="text-fg-dim">effect    </span><span className="text-primary">{me.portrait.effect}</span></li>
              <li><span className="text-fg-dim">contrast  </span><span className="text-fg tabular-nums">{me.portrait.contrast?.toFixed(2)}</span></li>
              <li><span className="text-fg-dim">brightness</span><span className="text-fg tabular-nums">{me.portrait.brightness}</span></li>
              <li><span className="text-fg-dim">chunkiness</span><span className="text-fg tabular-nums">{me.portrait.scale?.toFixed(2)}</span></li>
            </ul>
          )}
        </aside>

        {/* RIGHT — controls */}
        <div className="space-y-8">
          {/* file pickup zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => fileInput.current?.click()}
            className={`ascii-frame px-5 py-8 text-center cursor-pointer transition-colors ${
              dragging ? 'border-primary' : ''
            }`}
          >
            <input
              ref={fileInput}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => chooseFile(e.target.files?.[0] ?? null)}
            />
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-2">
              {file ? '◆ file ready' : '▒ drop an image here'}
            </p>
            <p className="ritual text-fg-muted text-[1rem] leading-relaxed mb-1">
              {file ? file.name : 'or click to choose · png · jpg · webp · gif'}
            </p>
            {file && (
              <p className="font-mono text-[0.7rem] text-fg-dim">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            )}
          </div>

          {/* effect chips */}
          <div>
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-2">
              effect
            </p>
            <div className="grid gap-2 md:grid-cols-3">
              {EFFECTS.map((e) => {
                const active = e.id === effect;
                return (
                  <button
                    key={e.id}
                    type="button"
                    onClick={() => setEffect(e.id)}
                    aria-pressed={active}
                    className={`border px-3 py-2.5 text-left transition-colors ${
                      active ? 'border-primary' : 'border-rule hover:border-rule-bright'
                    }`}
                  >
                    <div className={`font-mono text-[0.82rem] ${active ? 'text-primary' : 'text-fg'}`}>
                      {active && <span className="mr-1.5">▸</span>}
                      {e.label}
                    </div>
                    <div className="font-mono text-[0.66rem] uppercase tracking-wider text-fg-dim mt-0.5">
                      {e.blurb}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* sliders */}
          <div className="space-y-5">
            <Slider
              label="chunkiness"
              value={chunk}
              min={0}
              max={1}
              step={0.02}
              fmt={(v) => `${Math.round(v * 100)}%`}
              onChange={setChunk}
              hint="slide right for bigger, more visible dither dots"
            />
            <Slider
              label="contrast"
              value={contrast}
              min={0.5}
              max={3}
              step={0.05}
              fmt={(v) => v.toFixed(2)}
              onChange={setContrast}
              hint="how hard the ritual presses the light against the dark"
            />
            <Slider
              label="brightness"
              value={brightness}
              min={-50}
              max={50}
              step={1}
              fmt={(v) => (v > 0 ? `+${v}` : String(v))}
              onChange={setBrightness}
              hint="shift the whole image toward day or toward dusk"
            />
          </div>

          {/* disclaimer */}
          <div className="ascii-frame p-4 font-mono text-[0.76rem] text-fg-muted leading-relaxed">
            <p>
              <span className="text-warm">▒ a note on weight.</span> The ritual carries little.
              Portraits are dithered to a few kilobytes of two-tone PNG, stored only for the
              life of this container. When the ritual is dispelled, your portrait dispels with
              it. Bring nothing you would not gladly leave behind.
            </p>
          </div>

          {/* status */}
          {error && (
            <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
              ✕ {error}
            </p>
          )}
          {flash && (
            <p className="ascii-frame px-3 py-2 font-mono text-[0.78rem] text-primary">
              ◆ {flash}
            </p>
          )}

          {/* actions */}
          <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-rule">
            <button onClick={save} disabled={busy} className="btn">
              {busy ? 'inscribing…' : file ? 'inscribe portrait →' : 'retune ▸'}
            </button>
            {me.portrait?.url && (
              <button onClick={dispel} disabled={busy} className="btn btn-ghost !border-danger !text-danger">
                ✕ dispel portrait
              </button>
            )}
          </div>
        </div>
      </section>
    </>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  fmt,
  onChange,
  hint,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  fmt: (n: number) => string;
  onChange: (v: number) => void;
  hint: string;
}) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <span className="font-mono text-[0.72rem] uppercase tracking-widest text-fg-dim">
          {label}
        </span>
        <span className="font-mono text-[0.82rem] text-primary tabular-nums">
          {fmt(value)}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-primary"
      />
      <p className="font-mono text-[0.7rem] text-fg-dim mt-1 leading-snug">{hint}</p>
    </label>
  );
}

/** Best-effort client preview filter — gives a *rough* sense of the effect.
 * The actual press happens server-side at upload time and is canonical. */
function previewFilter(effect: ImageEffect): string {
  if (effect === 'dither') return 'grayscale(1) contrast(2.2)';
  if (effect === 'halftone') return 'grayscale(1) contrast(1.8)';
  return 'none';
}

/** UI chunkiness (0..1, right=more) → backend scale (1.0..0.15, lower=chunkier). */
function chunkToScale(chunk: number): number {
  const clamped = Math.max(0, Math.min(1, chunk));
  return Math.max(0.1, Math.min(1, 1.0 - clamped * 0.85));
}

/** Backend scale (0.1..1.0) → UI chunkiness (0..1). */
function scaleToChunk(scale: number): number {
  const clamped = Math.max(0.1, Math.min(1, scale));
  return Math.max(0, Math.min(1, (1.0 - clamped) / 0.85));
}
