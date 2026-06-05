/**
 * Global SVG filter definitions mounted once in the root layout.
 *
 * The filters are the heart of the image pipeline — they turn any uploaded
 * (or generated) image into a stylised glyph that matches the rest of the
 * platform. Two flavours:
 *
 *  - #ritual-dither   : grayscale + contrast + noise + 2-step posterize.
 *                       Output: two-tone "terminal" look.
 *
 *  - #ritual-halftone : grayscale + boosted contrast + radial-mask dots
 *                       (the dot pattern lives in CSS — the filter only
 *                       posterizes so the dots have clean edges).
 *
 * Tinting is done in CSS via `mix-blend-mode: multiply/screen` so the
 * effect picks up the current theme tokens.
 */

export function SvgFilters() {
  return (
    <svg
      width="0"
      height="0"
      style={{ position: 'absolute', pointerEvents: 'none' }}
      aria-hidden
    >
      <defs>
        {/* ── DITHER ──────────────────────────────────────── */}
        <filter id="ritual-dither" colorInterpolationFilters="sRGB">
          {/* 1 — desaturate to luminance */}
          <feColorMatrix
            type="matrix"
            values="
              0.2126 0.7152 0.0722 0 0
              0.2126 0.7152 0.0722 0 0
              0.2126 0.7152 0.0722 0 0
              0      0      0      1 0"
          />
          {/* 2 — boost contrast */}
          <feComponentTransfer>
            <feFuncR type="linear" slope="2.2" intercept="-0.6" />
            <feFuncG type="linear" slope="2.2" intercept="-0.6" />
            <feFuncB type="linear" slope="2.2" intercept="-0.6" />
          </feComponentTransfer>
          {/* 3 — fractal noise — high freq, single octave */}
          <feTurbulence
            type="fractalNoise"
            baseFrequency="4"
            numOctaves="1"
            seed="7"
            result="noise"
          />
          {/* 4 — blend SourceGraphic with noise (additive offset) */}
          <feComposite
            in="SourceGraphic"
            in2="noise"
            operator="arithmetic"
            k1="0"
            k2="0.65"
            k3="0.35"
            k4="-0.05"
            result="mixed"
          />
          {/* 5 — posterize to two values */}
          <feComponentTransfer in="mixed">
            <feFuncR type="discrete" tableValues="0 1" />
            <feFuncG type="discrete" tableValues="0 1" />
            <feFuncB type="discrete" tableValues="0 1" />
          </feComponentTransfer>
        </filter>

        {/* ── HALFTONE ────────────────────────────────────── */}
        <filter id="ritual-halftone" colorInterpolationFilters="sRGB">
          {/* 1 — desaturate */}
          <feColorMatrix
            type="matrix"
            values="
              0.2126 0.7152 0.0722 0 0
              0.2126 0.7152 0.0722 0 0
              0.2126 0.7152 0.0722 0 0
              0      0      0      1 0"
          />
          {/* 2 — heavy contrast (so the CSS dot mask renders cleanly) */}
          <feComponentTransfer>
            <feFuncR type="linear" slope="2.8" intercept="-0.9" />
            <feFuncG type="linear" slope="2.8" intercept="-0.9" />
            <feFuncB type="linear" slope="2.8" intercept="-0.9" />
          </feComponentTransfer>
          {/* 3 — light posterize (4 levels) for printable bands */}
          <feComponentTransfer>
            <feFuncR type="discrete" tableValues="0 0.4 0.7 1" />
            <feFuncG type="discrete" tableValues="0 0.4 0.7 1" />
            <feFuncB type="discrete" tableValues="0 0.4 0.7 1" />
          </feComponentTransfer>
        </filter>
      </defs>
    </svg>
  );
}
