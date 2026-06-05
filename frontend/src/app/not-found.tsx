import Link from 'next/link';

const TANGLE = `
        ,
       / \\
      /   \\
     |  ◇  |
      \\   /
   ╲━━━╳━━━╲
       ╲┃╱
       ╱┃╲
   ╱━━━╳━━━╱
      /   \\
     |  .  |
      \\   /
       \\ /
`;

export default function NotFound() {
  return (
    <section className="mx-auto w-full max-w-2xl px-6 py-24 grid gap-10 md:grid-cols-[auto_1fr] items-start">
      <pre
        aria-hidden
        className="text-fg-dim text-[10px] leading-[1.05] select-none whitespace-pre font-mono"
      >
        {TANGLE}
      </pre>
      <div>
        <p className="prompt font-mono text-[0.78rem] text-fg-muted mb-4">
          ritual.path(undefined)
        </p>
        <h1 className="font-display italic text-5xl text-fg mb-4 leading-[0.95]">
          Off the path.
        </h1>
        <p className="ritual text-fg-muted text-[1.05rem] leading-relaxed mb-8">
          What you sought is not in the circle, or not at this address. The
          ritual goes on. Step back to the gate and find your way again.
        </p>

        <div className="flex flex-wrap gap-3">
          <Link href="/" className="btn">
            <span aria-hidden>▸</span>
            back to the circle
          </Link>
          <Link href="/projects/" className="btn btn-ghost">
            browse projects
          </Link>
        </div>

        <pre className="mt-12 font-mono text-[0.78rem] text-fg-dim border-l border-rule pl-4 leading-relaxed whitespace-pre-wrap">
{`# status  404 — no such route
# state   the ritual continues
# action  return to /, or seek a new path
`}
        </pre>
      </div>
    </section>
  );
}
