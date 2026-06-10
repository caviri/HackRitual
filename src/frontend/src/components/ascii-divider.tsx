interface Props {
  label?: string;
  glyph?: string;
}

/**
 * Botanical divider: thin gradient rule on either side, an ASCII glyph at
 * centre, optional label. Used to break sections without heavy chrome.
 */
export function AsciiDivider({ label, glyph = '◆' }: Props) {
  return (
    <div className="divider my-10">
      <span aria-hidden className="select-none">
        {glyph}
      </span>
      {label ? <span>{label}</span> : null}
      <span aria-hidden className="select-none">
        {glyph}
      </span>
    </div>
  );
}
