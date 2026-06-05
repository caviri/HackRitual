'use client';

import { useStage } from '../lib/use-stage';
import { BackButton } from './back-button';

interface Props {
  /** ritual.foo(...) — the terminal-style command line at top */
  prompt: string;
  /** Big italic display title */
  title: string;
  /** Optional ritual subtitle */
  subtitle?: string;
  /** Right-aligned chip text — usually a count */
  chip?: string;
  /**
   * Back-button target. `true` → router.back(). `false` → no button.
   * A string → Link to that path. Default: no button.
   */
  back?: string | boolean;
  /** Label for the back button (default "back"). */
  backLabel?: string;
}

/**
 * Consistent page header for content routes. Reads the current stage so
 * the chip can adapt (e.g. "21 archived" vs "16 active").
 */
export function PageHeader({
  prompt,
  title,
  subtitle,
  chip,
  back,
  backLabel,
}: Props) {
  const data = useStage();
  return (
    <header className="border-b border-rule">
      <div className="mx-auto w-full max-w-6xl px-6 pt-10 pb-10">
        {back !== undefined && back !== false && (
          <div className="mb-4">
            <BackButton to={back} label={backLabel} />
          </div>
        )}
        <div className="flex flex-wrap items-baseline justify-between gap-4 mb-4">
          <p className="prompt font-mono text-[0.78rem] text-fg-muted tracking-wider">
            {prompt}
            <span className="animate-cursor-blink text-primary ml-0.5">▍</span>
          </p>
          {chip && (
            <span className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim border border-rule px-2 py-1">
              <span className="text-warm mr-1">{data.state.toLowerCase()}</span>· {chip}
            </span>
          )}
        </div>
        <h1 className="font-display italic text-[clamp(2.2rem,5vw,3.6rem)] leading-none text-fg">
          {title}
        </h1>
        {subtitle && (
          <p className="ritual mt-3 text-fg-muted text-[1.05rem] max-w-2xl">{subtitle}</p>
        )}
      </div>
    </header>
  );
}
