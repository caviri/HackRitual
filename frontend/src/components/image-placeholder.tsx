/**
 * Generative SVG placeholder.
 *
 * Hashes a seed string into deterministic geometry — botanical, vaguely
 * specimen-like. Designed to read well after dithering or halftone.
 *
 * Variants:
 *   `bloom`     — bursting radial shape (proposals, projects)
 *   `nucleus`   — orbiting rings (teams)
 *   `sprout`    — branching stem (participants — looks avatar-ish)
 *   `lattice`   — grid + dot field (admin tiles, abstract content)
 */

type Variant = 'bloom' | 'nucleus' | 'sprout' | 'lattice';

function hash(s: string): number {
  let h = 5381 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h = (((h * 33) >>> 0) ^ s.charCodeAt(i)) >>> 0;
  }
  return h >>> 0;
}

function lcg(seedInt: number) {
  let v = (seedInt || 1) >>> 0;
  return () => {
    v = (v * 1664525 + 1013904223) >>> 0;
    return v / 0x100000000;
  };
}

interface Props {
  seed: string;
  variant?: Variant;
  className?: string;
}

export function ImagePlaceholder({ seed, variant = 'bloom', className = '' }: Props) {
  const h = hash(seed);
  const rand = lcg(h);

  // Two foreground tones cycled through CSS variables so dithering reads well
  // and themes can swap. fg-light is the bright element; fg-dark is the field.
  const fgLight = 'var(--fg)';
  const fgMid = 'var(--fg-muted)';
  const fgDim = 'var(--fg-dim)';
  const fg = ['var(--primary)', 'var(--accent)', 'var(--warm)'][h % 3];

  const W = 200;
  const H = 200;

  let body: React.ReactNode = null;

  if (variant === 'bloom') {
    const center = { x: W / 2 + (rand() - 0.5) * 30, y: H / 2 + (rand() - 0.5) * 30 };
    const petals = 5 + (h % 7);
    const rOuter = 50 + rand() * 25;
    const rInner = 14 + rand() * 8;
    body = (
      <>
        {Array.from({ length: petals }).map((_, i) => {
          const t = (i / petals) * Math.PI * 2;
          return (
            <circle
              key={i}
              cx={center.x + Math.cos(t) * rOuter * 0.6}
              cy={center.y + Math.sin(t) * rOuter * 0.6}
              r={12 + rand() * 18}
              fill={fg}
              opacity={0.55 + rand() * 0.4}
            />
          );
        })}
        <circle cx={center.x} cy={center.y} r={rInner} fill={fgLight} />
      </>
    );
  } else if (variant === 'nucleus') {
    const rings = 4 + (h % 4);
    body = (
      <>
        {Array.from({ length: rings }).map((_, i) => {
          const r = 18 + i * (12 + rand() * 8);
          return (
            <circle
              key={i}
              cx={W / 2}
              cy={H / 2}
              r={r}
              fill="none"
              stroke={i % 2 ? fg : fgMid}
              strokeWidth={1 + (i === rings - 1 ? 1.5 : 0)}
              strokeDasharray={i % 2 ? '3 4' : '0'}
              opacity={0.9 - i * 0.1}
            />
          );
        })}
        <circle cx={W / 2} cy={H / 2} r={6} fill={fgLight} />
      </>
    );
  } else if (variant === 'sprout') {
    const trunk = { x: W / 2, y: H - 20 };
    const tip = { x: W / 2 + (rand() - 0.5) * 30, y: 30 + rand() * 20 };
    const branches = 3 + (h % 4);
    body = (
      <>
        <line
          x1={trunk.x}
          y1={trunk.y}
          x2={tip.x}
          y2={tip.y}
          stroke={fgMid}
          strokeWidth="2"
        />
        {Array.from({ length: branches }).map((_, i) => {
          const t = (i + 1) / (branches + 1);
          const cx = trunk.x + (tip.x - trunk.x) * t;
          const cy = trunk.y + (tip.y - trunk.y) * t;
          const side = i % 2 ? 1 : -1;
          const len = 28 + rand() * 18;
          return (
            <g key={i}>
              <line
                x1={cx}
                y1={cy}
                x2={cx + side * len}
                y2={cy - len * 0.5}
                stroke={fgMid}
                strokeWidth="1.5"
              />
              <circle
                cx={cx + side * len}
                cy={cy - len * 0.5}
                r={6 + rand() * 8}
                fill={fg}
                opacity={0.85}
              />
            </g>
          );
        })}
        <circle cx={tip.x} cy={tip.y} r={9} fill={fgLight} />
      </>
    );
  } else {
    // lattice
    const step = 16;
    const dots: React.ReactNode[] = [];
    for (let x = step; x < W; x += step) {
      for (let y = step; y < H; y += step) {
        const v = rand();
        if (v < 0.15) continue;
        dots.push(
          <circle
            key={`${x}-${y}`}
            cx={x}
            cy={y}
            r={v < 0.4 ? 1.6 : v < 0.7 ? 2.8 : 4}
            fill={v < 0.85 ? fgMid : fg}
            opacity={0.5 + v * 0.5}
          />,
        );
      }
    }
    body = <>{dots}</>;
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid slice"
      className={className}
      aria-hidden
    >
      <rect width={W} height={H} fill="var(--bg-elev)" />
      {/* faint grid */}
      <g stroke={fgDim} strokeWidth="0.5" opacity="0.25">
        {Array.from({ length: 5 }).map((_, i) => (
          <line key={`v${i}`} x1={(i + 1) * (W / 5)} y1={0} x2={(i + 1) * (W / 5)} y2={H} />
        ))}
        {Array.from({ length: 5 }).map((_, i) => (
          <line key={`h${i}`} x1={0} y1={(i + 1) * (H / 5)} x2={W} y2={(i + 1) * (H / 5)} />
        ))}
      </g>
      {body}
      {/* hairline frame */}
      <rect x="0.5" y="0.5" width={W - 1} height={H - 1} fill="none" stroke={fgDim} />
    </svg>
  );
}
