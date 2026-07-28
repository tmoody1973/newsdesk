/**
 * The signature. Every consequential state change renders as a rubber stamp —
 * slightly rotated, uppercase Anton, ink-textured.
 *
 * Policy rejections do not appear as error toasts. They appear as a red stamp
 * slammed onto the card with the rule citation beneath in mono. That is the
 * plan-check ritual from an architecture practice applied to editorial review,
 * and it makes the product's most important feature — refusal — its most
 * memorable visual moment.
 *
 * Exactly four kinds. Resist a fifth.
 */
const KINDS = {
  approved: { color: "var(--color-approval-blue)", glyph: "✓" },
  blocked: { color: "var(--color-stamp-red)", glyph: "✕" },
  retry: { color: "var(--color-graphite)", glyph: "↻" },
  verified: { color: "var(--color-approval-blue)", glyph: "✓" },
} as const;

export type StampKind = keyof typeof KINDS;

export function Stamp({
  kind,
  label,
  suffix,
  rotate = -3,
}: {
  kind: StampKind;
  label: string;
  suffix?: string;
  rotate?: number;
}) {
  const { color, glyph } = KINDS[kind];
  return (
    <span
      // Never colour-only: each kind also carries a glyph and a text label, so
      // the state survives greyscale, colour-blindness and a screen reader.
      role="status"
      className="stamp-land inline-flex items-baseline gap-2 border-[3px] px-3 py-1 font-display uppercase tracking-wide"
      style={{
        color,
        borderColor: color,
        ["--stamp-rot" as string]: `${rotate}deg`,
        transform: `rotate(${rotate}deg)`,
        letterSpacing: "0.06em",
      }}
    >
      <span aria-hidden className="text-[0.8em]">{glyph}</span>
      <span>{label}</span>
      {suffix ? <span className="mono text-[0.62em] opacity-70">{suffix}</span> : null}
    </span>
  );
}
