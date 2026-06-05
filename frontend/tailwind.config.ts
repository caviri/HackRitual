import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    // We DON'T extend the default palette — we *replace* it with semantic
    // tokens that resolve to CSS variables. Themes swap by changing
    // [data-theme] on <html>; no rebuild required.
    colors: {
      transparent: 'transparent',
      current: 'currentColor',

      // Surfaces
      bg: 'var(--bg)',
      'bg-elev': 'var(--bg-elev)',
      'bg-rule': 'var(--bg-rule)',

      // Foreground
      fg: 'var(--fg)',
      'fg-muted': 'var(--fg-muted)',
      'fg-dim': 'var(--fg-dim)',

      // Brand
      primary: 'var(--primary)',
      'primary-fg': 'var(--primary-fg)',
      accent: 'var(--accent)',
      warm: 'var(--warm)',

      // Lines
      rule: 'var(--rule)',
      'rule-bright': 'var(--rule-bright)',

      // Status
      danger: 'var(--danger)',
      success: 'var(--success)',
      warning: 'var(--warning)',
      info: 'var(--info)',
    },
    fontFamily: {
      mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      display: ['var(--font-display)', 'Georgia', 'serif'],
      sans: ['var(--font-mono)', 'ui-monospace', 'monospace'],
    },
    borderRadius: {
      none: '0',
      sm: 'var(--radius)',
      DEFAULT: 'var(--radius)',
      md: 'var(--radius-lg)',
      lg: 'var(--radius-lg)',
      full: '9999px',
    },
    extend: {
      letterSpacing: {
        wider: '0.08em',
        widest: '0.16em',
      },
      animation: {
        'pulse-glow': 'pulse-glow 3.4s ease-in-out infinite',
        'flicker': 'flicker 6s ease-in-out infinite',
        'cursor-blink': 'cursor-blink 1.1s steps(2, end) infinite',
        'scroll-log': 'scroll-log 22s linear infinite',
        'rise': 'rise 0.6s ease-out forwards',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '0.75', textShadow: '0 0 0 transparent' },
          '50%': { opacity: '1', textShadow: '0 0 14px var(--primary-glow)' },
        },
        'flicker': {
          '0%, 100%': { opacity: '1' },
          '47%': { opacity: '1' },
          '48%': { opacity: '0.55' },
          '49%': { opacity: '1' },
          '92%': { opacity: '1' },
          '93%': { opacity: '0.7' },
          '94%': { opacity: '1' },
        },
        'cursor-blink': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'scroll-log': {
          '0%': { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(calc(-50% - 0.5em))' },
        },
        'rise': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
