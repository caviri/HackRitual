'use client';

import { useEffect, useState } from 'react';
import { defaultImageEffect, ImageEffect } from '../lib/settings';
import { ImagePlaceholder } from './image-placeholder';

interface Props {
  src?: string;
  seed?: string;
  alt: string;
  variant?: 'bloom' | 'nucleus' | 'sprout' | 'lattice';
  effect?: ImageEffect;        // override the global setting
  className?: string;
  /** Overlays a small caption strip on the bottom of the image. */
  caption?: string;
}

/**
 * <DitheredImage>
 *
 * Wraps any image (or a generated placeholder) with the current image
 * effect — `dither`, `halftone`, or `none`. The effect is read from the
 * user's stored settings unless overridden via the `effect` prop.
 *
 * When `src` is undefined, a deterministic SVG placeholder is rendered
 * from `seed`. The placeholder ALSO passes through the effect filter, so
 * before any real images are uploaded the platform still looks like itself.
 */
export function DitheredImage({
  src,
  seed,
  alt,
  variant = 'bloom',
  effect,
  className = '',
  caption,
}: Props) {
  // Hydrate effect from settings after mount (avoid SSR mismatch).
  const [active, setActive] = useState<ImageEffect>(effect ?? 'dither');
  useEffect(() => {
    if (effect) return; // explicit override sticks
    setActive(defaultImageEffect());
    function onChange(e: Event) {
      const detail = (e as CustomEvent).detail as { imageEffect?: ImageEffect };
      if (detail?.imageEffect) setActive(detail.imageEffect);
    }
    window.addEventListener('hackritual:settings', onChange);
    return () => window.removeEventListener('hackritual:settings', onChange);
  }, [effect]);

  const filterStyle =
    active === 'dither'
      ? { filter: 'url(#ritual-dither)' }
      : active === 'halftone'
      ? { filter: 'url(#ritual-halftone)' }
      : undefined;

  const halftoneClass = active === 'halftone' ? 'halftone-mask' : '';

  return (
    <figure
      className={`relative overflow-hidden bg-bg-elev ${className}`}
      aria-label={alt}
    >
      <div className="absolute inset-0" style={filterStyle}>
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={alt} className="w-full h-full object-cover" />
        ) : (
          <ImagePlaceholder
            seed={seed ?? alt}
            variant={variant}
            className="w-full h-full"
          />
        )}
      </div>

      {/* halftone dot mask sits ABOVE the filtered image */}
      {active === 'halftone' && (
        <div
          aria-hidden
          className={`absolute inset-0 ${halftoneClass}`}
        />
      )}

      {/* effect badge — tiny, top-right */}
      <span className="absolute top-1.5 right-1.5 z-10 font-mono text-[0.6rem] uppercase tracking-widest bg-bg/80 text-fg-dim px-1.5 py-0.5 border border-rule">
        {active}
      </span>

      {caption && (
        <figcaption className="absolute bottom-0 left-0 right-0 z-10 bg-bg/85 backdrop-blur-[1px] border-t border-rule px-2.5 py-1.5 font-mono text-[0.7rem] text-fg-muted">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}
