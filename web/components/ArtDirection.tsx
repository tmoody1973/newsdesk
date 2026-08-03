"use client";

import { useState } from "react";

/**
 * Wizard step 2. Three curated pickers and no free text — the menu *is* the
 * policy boundary, which is why the footnote below is a statement of fact
 * rather than a warning.
 */

const THROUGH_LINES = [
  { id: "fuse", label: "Fuse", d: "M4 20c4-1 6-4 7-8m0 0c.5-2 1-5 5-8m-5 8h.01", extra: <circle cx="18" cy="5" r="2.5" /> },
  { id: "balloon", label: "Balloon", d: "M12 15v6", extra: <circle cx="12" cy="9" r="6" /> },
  { id: "tower-signal", label: "Tower signal", d: "M12 21V9m-4 12l4-12 4 12M7 6c3-3 7-3 10 0M9 3.5c2-1.5 4-1.5 6 0" },
  { id: "dollar-cut", label: "Dollar, cut", d: "M14 4l-8 16", extra: <rect x="3" y="8" width="18" height="9" /> },
  { id: "record", label: "Record", d: "", extra: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="2" /></> },
  { id: "scale", label: "Scale", d: "M12 4v16M5 8h14M7 8l-2 6h4zM17 8l-2 6h4z" },
];

// The diorama kit's own menu — ids must match brand-kit/diorama/through-lines.yaml,
// because Wall 1 refuses a through-line that is not in the story's kit's menu.
const DIORAMA_LINES = [
  { id: "keg-fuse", label: "Keg & fuse", d: "M6 21c5-2 7-6 8-10", extra: <rect x="13" y="3" width="8" height="8" /> },
  { id: "hourglass", label: "Hourglass", d: "M6 3h12L8 12 6 21h12l-10-9z" },
  { id: "stamped-document", label: "Stamped document", d: "M8 13h6", extra: <><rect x="4" y="3" width="16" height="18" /><circle cx="15" cy="16" r="3" /></> },
  { id: "note-stack", label: "Note stack", d: "M5 19h14M6 16h12M7 13h10M8 10h8" },
  { id: "censor-portraits", label: "Censor portraits", d: "M7 10h10", extra: <><circle cx="12" cy="9" r="5" /><path d="M6 21c1-4 4-6 6-6s5 2 6 6" /></> },
  { id: "paper-city", label: "Paper city", d: "M3 21V11h4v10M9 21V6h4v15M15 21V14h4v7M3 21h18" },
];

const KITS = [
  { id: "house", label: "House — mixed media", lines: THROUGH_LINES },
  { id: "diorama", label: "Paper diorama", lines: DIORAMA_LINES },
];

const MOTIFS = ["Prop with text", "Map", "Chart", "Ledger", "Cutout crowd", "Archival frame"];

// Defaults per through-line. The journalist adjusts; they do not compose.
const DEFAULTS: Record<string, string[]> = {
  "tower-signal": ["Prop with text", "Map", "Chart", "Ledger", "Cutout crowd", "Archival frame"],
  record: ["Prop with text", "Chart", "Cutout crowd", "Archival frame", "Ledger", "Map"],
};
const FALLBACK = ["Prop with text", "Map", "Chart", "Ledger", "Cutout crowd", "Archival frame"];

/** Controlled on the through-line, uncontrolled on the motifs.
 *
 *  The through-line lives in the wizard's draft because it decides the run's
 *  B2 prefix and has to survive the step-2 → step-3 → submit path. The motifs
 *  do not reach the backend yet — scene.py derives them from the through-line
 *  itself — so lifting them would be inventing state the pipeline ignores. When
 *  per-block motif overrides land, they move up too. */
export function ArtDirection({
  value,
  onChange,
  kit = "house",
  onKitChange,
}: {
  value: string;
  onChange: (id: string) => void;
  kit?: string;
  onKitChange?: (kit: string, firstThroughLine: string) => void;
}) {
  const chosen = value;
  const [motifs, setMotifs] = useState<string[]>(DEFAULTS[value] ?? FALLBACK);
  const lines = (KITS.find((k) => k.id === kit) ?? KITS[0]).lines;

  function pick(id: string) {
    onChange(id);
    setMotifs(DEFAULTS[id] ?? FALLBACK);
  }

  return (
    <div style={{ padding: "32px 0 0", display: "flex", flexDirection: "column", gap: 28 }}>
      {onKitChange && (
        <section>
          <h6 style={{ marginBottom: 12 }}>Brand kit · every kit brings its own objects</h6>
          <div style={{ display: "flex", gap: 14 }}>
            {KITS.map((k) => {
              const on = k.id === kit;
              return (
                <button
                  key={k.id}
                  type="button"
                  aria-pressed={on}
                  // Switching kits must switch the object too — Wall 1 refuses
                  // a through-line that is not in the story's kit's menu.
                  onClick={() => onKitChange(k.id, k.lines[0].id)}
                  style={{
                    border: on ? "3px solid #F2C744" : "1px solid var(--color-divider)",
                    padding: "10px 18px", cursor: "pointer",
                    background: "var(--color-surface)", font: "inherit",
                    fontWeight: on ? 600 : 400,
                  }}
                >
                  {k.label}
                </button>
              );
            })}
          </div>
        </section>
      )}
      <section>
        <h6 style={{ marginBottom: 12 }}>Through-line object · pick one</h6>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 14 }}>
          {lines.map((tl) => {
            const on = tl.id === chosen;
            return (
              <button
                key={tl.id}
                type="button"
                onClick={() => pick(tl.id)}
                aria-pressed={on}
                style={{
                  border: on ? "3px solid #F2C744" : "1px solid var(--color-divider)",
                  padding: 14, textAlign: "left", cursor: "pointer",
                  background: "var(--color-surface)", font: "inherit",
                }}
              >
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
                     stroke={on ? "#1a1917" : "#6B675F"} strokeWidth="1.5">
                  {tl.d ? <path d={tl.d} /> : null}
                  {tl.extra}
                </svg>
                <p style={{
                  fontSize: 12, fontWeight: on ? 600 : 400, margin: "8px 0 0",
                  color: on ? undefined : "var(--color-neutral-700)",
                }}>
                  {tl.label}
                </p>
              </button>
            );
          })}
        </div>
      </section>

      {kit !== "house" && (
        <p className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)", margin: 0 }}>
          The diorama composes its own six beats around the object — sepia newsprint
          world, one burnt-orange accent, censor-bar cutouts, letterpress labels.
        </p>
      )}
      {kit === "house" && (
      <section>
        <h6 style={{ marginBottom: 12 }}>Motif per block · defaults from the through-line</h6>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 14 }}>
          {motifs.map((motif, i) => (
            <div key={i} style={{
              border: "1px solid var(--color-divider)", padding: "10px 12px",
              background: "var(--color-surface)",
            }}>
              <span className="mono" style={{ fontSize: 10, color: "var(--color-neutral-600)" }}>
                B{i + 1}
              </span>
              <select
                value={motif}
                onChange={(e) => setMotifs(motifs.map((m, j) => (j === i ? e.target.value : m)))}
                aria-label={`Motif for block ${i + 1}`}
                style={{
                  display: "block", width: "100%", marginTop: 2, border: 0, padding: 0,
                  background: "transparent", font: "inherit", fontSize: 13, fontWeight: 600,
                  color: "inherit", cursor: "pointer", appearance: "none",
                  textOverflow: "ellipsis",
                }}
              >
                {MOTIFS.map((m) => <option key={m}>{m}</option>)}
              </select>
            </div>
          ))}
        </div>
      </section>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: 32, alignItems: "stretch" }}>
        <label style={{
          border: "2px dashed var(--color-divider)", padding: 28,
          display: "flex", gap: 16, alignItems: "center", cursor: "pointer",
        }}>
          <input type="file" accept="image/*" style={{ display: "none" }} />
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6B675F" strokeWidth="1.5">
            <path d="M12 16V5m0 0l-4 4m4-4l4 4M4 19h16" />
          </svg>
          <div>
            <p style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>Add a photo from your reporting.</p>
            <p style={{ fontSize: 12, color: "var(--color-neutral-700)", margin: "2px 0 0" }}>
              It appears as a cutout and is labeled authentic in the receipt.
            </p>
          </div>
        </label>
        <div aria-hidden style={{
          background: "linear-gradient(135deg,#bbb,#777)", filter: "grayscale(1)",
        }} />
      </section>

      {/* The mockup's footer — the policy note and `Write script` — used to
          live here. It moved to the wizard shell when this became a controlled
          step, because the shell owns the access code, the busy state and the
          call to the worker. Leaving a copy behind rendered two `Write script`
          buttons, one of them dead. */}
    </div>
  );
}
