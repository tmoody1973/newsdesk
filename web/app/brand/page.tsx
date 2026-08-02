import type { Metadata } from "next";

export const metadata: Metadata = { title: "Brand — Newsdesk" };

/** The logo kit. Seventeen files under /brand, all derived by transform from
 *  the one traced source, so the ring and the letterforms are identical in
 *  every lockup rather than redrawn per file.
 *
 *  This is the app's own identity. It is deliberately not the Brand Kit at
 *  /brand-kit — that one is the video kit (voice, style key, subtitles,
 *  negatives) that dresses the output. Two different things, kept apart. */

type Ground = "paper" | "dark" | "red" | "app";

const GROUND: Record<Ground, React.CSSProperties> = {
  paper: { background: "#f9f6ee" },
  dark: { background: "#1a1917" },
  red: { background: "var(--color-accent)" },
  app: { background: "var(--color-bg)", outline: "2px solid var(--color-divider)", outlineOffset: -2 },
};

const LOCKUPS: { title: string; note: string; height: number; files: [string, string, Ground][] }[] = [
  {
    title: "Horizontal",
    note: "The primary lockup. Headers, footers, anywhere with more width than height.",
    height: 64,
    files: [
      ["newsdesk-horizontal-light", "light · on paper", "paper"],
      ["newsdesk-horizontal-light", "light · on app ground", "app"],
      ["newsdesk-horizontal-dark", "dark", "dark"],
      ["newsdesk-horizontal-mono-ink", "mono ink", "paper"],
      ["newsdesk-horizontal-mono-paper", "mono paper · knockout", "red"],
    ],
  },
  {
    title: "Stacked",
    note: "Square-ish spaces — social avatars, share cards, a title slide.",
    height: 150,
    files: [
      ["newsdesk-stacked-light", "light", "paper"],
      ["newsdesk-stacked-dark", "dark", "dark"],
      ["newsdesk-stacked-mono-ink", "mono ink", "paper"],
      ["newsdesk-stacked-mono-paper", "mono paper", "red"],
    ],
  },
  {
    title: "Wordmark",
    note: "When the mark is already present, or when the space is too short for it.",
    height: 52,
    files: [
      ["newsdesk-wordmark-light", "light", "paper"],
      ["newsdesk-wordmark-dark", "dark", "dark"],
      ["newsdesk-wordmark-mono-ink", "mono ink", "paper"],
      ["newsdesk-wordmark-mono-paper", "mono paper", "red"],
    ],
  },
  {
    title: "Mark",
    note: "Three bars. Holds down to about 32px — below that use the small mark.",
    height: 96,
    files: [
      ["newsdesk-mark-light", "light", "paper"],
      ["newsdesk-mark-dark", "dark", "dark"],
      ["newsdesk-mark-mono-ink", "mono ink", "paper"],
      ["newsdesk-mark-mono-paper", "mono paper", "red"],
    ],
  },
  {
    title: "Mark — small",
    note: "Two bars, thicker, wider gap. For 32px and below: favicon, the rail, a inline glyph.",
    height: 96,
    files: [
      ["newsdesk-mark-small-light", "light", "paper"],
      ["newsdesk-mark-small-dark", "dark", "dark"],
      ["newsdesk-mark-small-mono-ink", "mono ink", "paper"],
      ["newsdesk-mark-small-mono-paper", "mono paper", "red"],
    ],
  },
];

const PALETTE = [
  ["Ink", "#353334", "--color-text · --color-ink"],
  ["Red", "#f2322f", "--color-accent · --color-stamp-red"],
  ["Paper", "#f9f6ee", "--color-bg · --color-paper"],
  ["Graphite", "#7c7a74", "--color-neutral-600 · --color-graphite"],
  ["Approval blue", "#2b5da8", "--color-approval-blue"],
  ["Canary", "#f2c744", "--color-canary · selection only"],
];

const CONTRAST = [
  ["ink on paper", "11.61:1", "passes AAA"],
  ["paper on #1a1917", "16.27:1", "passes AAA"],
  ["red on paper", "3.69:1", "passes 3:1, non-text"],
  ["red on #1a1917", "4.41:1", "passes 3:1, non-text"],
];

const RULE = "2px solid var(--color-divider)";

function H({ children, note }: { children: React.ReactNode; note?: string }) {
  return (
    <>
      <h2
        className="anton"
        style={{ fontSize: 15, letterSpacing: ".08em", textTransform: "uppercase",
                 margin: "44px 0 0", paddingBottom: 8, borderBottom: RULE }}
      >
        {children}
      </h2>
      {note && <p className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)", margin: "8px 0 14px" }}>{note}</p>}
    </>
  );
}

export default function Brand() {
  return (
    <main style={{ maxWidth: 1180 }}>
      <h1 className="anton" style={{ fontSize: 30, textTransform: "uppercase", letterSpacing: ".04em", margin: 0 }}>
        Brand
      </h1>
      <p className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)", margin: "6px 0 0" }}>
        21 files under /brand · derived by transform from one source, geometry never redrawn
      </p>
      <p style={{ fontSize: 13, maxWidth: 620, marginTop: 14 }}>
        This is the app&rsquo;s identity. The <strong>Brand Kit</strong> section is a different
        thing — the voice, style key and subtitle rules that dress the video output.
      </p>

      {LOCKUPS.map((group) => (
        <section key={group.title}>
          <H note={group.note}>{group.title}</H>
          <div style={{ display: "grid", gap: 2, gridTemplateColumns: "repeat(auto-fill,minmax(230px,1fr))" }}>
            {group.files.map(([file, caption, ground], i) => (
              <figure key={`${file}-${i}`} style={{ margin: 0 }}>
                <div style={{ ...GROUND[ground], display: "grid", placeItems: "center", padding: 28, minHeight: group.height + 56 }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={`/brand/${file}.svg`} alt="" style={{ maxWidth: "100%", height: group.height }} />
                </div>
                <figcaption className="mono" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: ".04em",
                                                      color: "var(--color-neutral-600)", padding: "6px 0 14px" }}>
                  {caption}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      ))}

      <H note="The full mark's bars are 11.6% of its height with 4.8% gaps — 1.9px and 0.8px at 16px. Rendered at 2x it holds at 64 and 48, is marginal at 32, muds at 24 and fails at 16. The small mark is the answer below 32.">
        Reduction
      </H>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 36, background: "#f9f6ee", padding: 28 }}>
        {[64, 48, 32, 24, 16].map((s) => (
          <figure key={s} style={{ margin: 0, textAlign: "center" }}>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 10 }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/brand/newsdesk-mark-light.svg" alt={`full mark at ${s}px`} width={s} height={s} />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/brand/newsdesk-mark-small-light.svg" alt={`small mark at ${s}px`} width={s} height={s} />
            </div>
            <figcaption className="mono" style={{ fontSize: 10, color: "var(--color-neutral-600)", paddingTop: 8 }}>{s}</figcaption>
          </figure>
        ))}
        <p className="mono" style={{ fontSize: 10, color: "var(--color-neutral-600)", margin: 0, alignSelf: "flex-end" }}>
          full · small
        </p>
      </div>

      <H note="The app was retuned onto the logo rather than the reverse. Modernist shipped #201e1d / #ec3013 / #f3f2f2 — a cooler system whose red sat four degrees of hue from the logo's, close enough to read as a mistake. Ramps keep their original OKLCH lightness and are re-hued onto the new base.">
        Palette
      </H>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
        {PALETTE.map(([name, hex, token]) => (
          <div key={hex} style={{ background: hex, width: 186, padding: "18px 14px",
                                  color: hex === "#353334" || hex === "#2b5da8" ? "#f9f6ee" : "#1a1917" }}>
            <div className="mono" style={{ fontSize: 11, fontWeight: 500 }}>{name}</div>
            <div className="mono" style={{ fontSize: 11 }}>{hex}</div>
            <div className="mono" style={{ fontSize: 9, opacity: 0.75, paddingTop: 6 }}>{token}</div>
          </div>
        ))}
      </div>

      <table className="mono" style={{ borderCollapse: "collapse", fontSize: 11, marginTop: 22 }}>
        <tbody>
          {CONTRAST.map(([pair, ratio, verdict]) => (
            <tr key={pair}>
              <td style={{ border: RULE, padding: "6px 14px" }}>{pair}</td>
              <td style={{ border: RULE, padding: "6px 14px" }}>{ratio}</td>
              <td style={{ border: RULE, padding: "6px 14px", color: "var(--color-neutral-600)" }}>{verdict}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
