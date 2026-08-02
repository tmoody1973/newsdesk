import Link from "next/link";
import fs from "node:fs/promises";
import path from "node:path";

import { parse } from "yaml";

import { BUCKETS, brandKitFile, publicUrl } from "@/lib/b2";

export const dynamic = "force-dynamic";

/**
 * Brand Kit & Policy — mockup 1l, "read-mostly".
 *
 * Every value here is fetched from the PUBLISHED kit in B2, never from the
 * working copy beside the code. That is the rule `brandkit.py` enforces on a
 * run, and it is the only version of this page worth having: a kit page reading
 * the repo would show a house style no video was ever made with.
 *
 * Colours come from the vendored design system's own custom properties rather
 * than Tailwind names. The older pages in this app use `text-graphite`,
 * `border-ink` and friends, which are defined nowhere and emit no CSS — they
 * look right only because `_ds/modernist.css` carries the palette underneath.
 * Following that pattern here would have meant inventing hex values for a
 * palette the design system already publishes.
 *
 * Where the mockup and the live files disagree, the files win. The mockup's
 * voice card says 9.0–10.5s per take; `voice.json` says 9.0–13.0, with the six
 * measurements that moved it. That correction is put on screen rather than
 * smoothed over — it is the sort of thing this project claims to keep.
 */

type ThroughLine = { id: string; label: string; use_when?: string };
type Rule = { id: string; name: string; why?: string };

type Voice = {
  brief?: string;
  primary?: { model?: string; voice_name?: string; provider?: string };
  fallback?: { model?: string; voice_name?: string; provider?: string };
  delivery?: {
    target_take_seconds?: [number, number];
    words_per_block?: [number, number];
    why_the_window_moved?: { was?: [number, number]; what_happened?: string };
  };
};

const MUTED = "var(--color-neutral-600)";
const DIVIDER = "var(--color-divider)";

export default async function BrandKit() {
  const [tokens, negative, voiceRaw, throughRaw, policyRaw] = await Promise.all([
    brandKitFile("style-tokens.txt"),
    brandKitFile("negative.txt"),
    brandKitFile("voice.json"),
    brandKitFile("through-lines.yaml"),
    fs.readFile(path.join(process.cwd(), "..", "policy", "policy.yaml"), "utf-8"),
  ]);

  const voice = (voiceRaw ? (JSON.parse(voiceRaw) as Voice) : {}) as Voice;
  const throughLines =
    (throughRaw
      ? (parse(throughRaw) as { through_lines?: ThroughLine[] }).through_lines
      : []) ?? [];
  const rules = ((parse(policyRaw) as { rules?: Rule[] }).rules ?? []) as Rule[];

  // `style-tokens.txt` is one paragraph with three labelled clauses — GROUND,
  // ACCENTS, ELEMENTS. Split on the labels rather than restating them here, so
  // an edit to the published kit shows up on this page instead of drifting from it.
  const parts = (tokens ?? "")
    .split(/(?=\b(?:GROUND|ACCENTS|ELEMENTS):)/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const m = /^(GROUND|ACCENTS|ELEMENTS):\s*([\s\S]+)$/.exec(chunk);
      return m ? { label: m[1], text: m[2].trim() } : { label: "Overall", text: chunk };
    });

  const take = voice.delivery?.target_take_seconds;
  const words = voice.delivery?.words_per_block;
  const moved = voice.delivery?.why_the_window_moved;

  return (
    <main className="grid gap-12 lg:grid-cols-[3fr_2fr]">
      <section>
        <h1 className="font-display text-4xl uppercase tracking-wide">Brand kit</h1>
        <p className="mono mt-2 text-xs" style={{ color: MUTED }}>
          Read from the published kit in B2, not from this checkout. A run styled by an
          unpublished kit is refused outright.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <article className="card">
            <span className="card-kicker">Style key</span>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={publicUrl(BUCKETS.brandKit, "kit/style-key.png")}
              alt="The published style key — the reference every block is rendered against"
              className="w-full"
              style={{ border: `1px solid ${DIVIDER}` }}
            />
            <span className="card-meta mono">kit/style-key.png</span>
          </article>

          <article className="card">
            <span className="card-kicker">Voice</span>
            <p style={{ fontSize: 13 }}>{voice.brief ?? "—"}</p>
            <div className="mono" style={{ fontSize: 11 }}>
              <div>
                {voice.primary?.provider} · {voice.primary?.model} ·{" "}
                <span style={{ color: "#2b5da8" }}>{voice.primary?.voice_name}</span>
              </div>
              <div style={{ color: MUTED }}>
                fallback · {voice.fallback?.provider} · {voice.fallback?.voice_name}
              </div>
            </div>
            <span className="card-meta mono">
              {take ? `${take[0]}–${take[1]}s per take` : "—"}
              {words ? ` · ${words[0]}–${words[1]} words` : ""}
            </span>
          </article>

          <article className="card">
            <span className="card-kicker">Subtitle face</span>
            <p className="font-display text-3xl uppercase leading-none">Anton — burned in</p>
            <p style={{ fontSize: 13 }}>
              The same face as the stamps, burned into the picture rather than
              side-loaded, so the caption travels with the file.
            </p>
            <span className="card-meta mono">
              libass substitutes another face without a word — /health checks for both
            </span>
          </article>

          <article className="card">
            <span className="card-kicker">The look</span>
            {parts.length ? (
              <div className="flex flex-col gap-2">
                {parts.map(({ label, text }) => (
                  <div key={label}>
                    <div
                      className="mono uppercase"
                      style={{ fontSize: 9, letterSpacing: "0.12em", color: MUTED }}
                    >
                      {label}
                    </div>
                    <p style={{ fontSize: 12, lineHeight: 1.45 }}>{text}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mono" style={{ fontSize: 11 }}>
                — could not read kit/style-tokens.txt
              </p>
            )}
            <span className="card-meta mono">kit/style-tokens.txt</span>
          </article>
        </div>

        {tokens ? (
          <details className="mt-6">
            <summary
              className="mono cursor-pointer text-xs uppercase tracking-widest"
              style={{ color: "#2b5da8" }}
            >
              The style tokens, verbatim — this string is in every block prompt
            </summary>
            <p
              className="mono mt-3 pl-3 text-xs leading-relaxed"
              style={{ borderLeft: `2px solid ${DIVIDER}`, color: MUTED }}
            >
              {tokens}
            </p>
          </details>
        ) : null}

        <h2 className="mt-12 pt-4 font-display text-2xl uppercase" style={{ borderTop: "2px solid var(--color-text)" }}>
          Through-line objects
        </h2>
        <p className="mono mt-1 text-xs" style={{ color: MUTED }}>
          One object carries a story across six independent renders. Each entry names a
          silhouette in enough detail that six separate generations agree on it.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {throughLines.map((tl) => (
            <div
              key={tl.id}
              style={{ border: `1px solid ${DIVIDER}`, background: "var(--color-surface)", padding: 12 }}
            >
              <div
                className="mono uppercase"
                style={{ fontSize: 10, letterSpacing: "0.1em", color: "var(--color-accent)" }}
              >
                {tl.id}
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{tl.label}</div>
              {tl.use_when ? (
                <p style={{ fontSize: 12, marginTop: 4, color: MUTED }}>{tl.use_when}</p>
              ) : null}
            </div>
          ))}
        </div>

        <h2 className="mt-12 pt-4 font-display text-2xl uppercase" style={{ borderTop: "2px solid var(--color-text)" }}>
          The exclusion line
        </h2>
        <p className="mt-2 max-w-2xl" style={{ fontSize: 14 }}>
          POL-2 does not ask a prompt to avoid these things. It byte-compares the
          prompt&apos;s NEGATIVE clause against this file. If a caller can edit the line,
          the prohibitions are advisory.
        </p>
        <pre
          className="mono mt-3 overflow-x-auto p-3"
          style={{
            border: "2px solid var(--color-text)",
            background: "var(--color-surface)",
            fontSize: 11,
            whiteSpace: "pre-wrap",
          }}
        >
          {negative ?? "— could not read kit/negative.txt"}
        </pre>
      </section>

      <section>
        <h1 className="font-display text-4xl uppercase tracking-wide">Policy</h1>
        <p className="mono mt-2 text-xs" style={{ color: MUTED }}>
          Rendered from the same policy.yaml the gate enforces.
        </p>

        <div className="mt-8 flex flex-col">
          {rules.map((rule) => (
            <div key={rule.id} style={{ padding: "14px 0", borderBottom: `1px solid ${DIVIDER}` }}>
              <span
                className="mono"
                style={{ fontSize: 12, fontWeight: 500, color: "var(--color-accent)" }}
              >
                {rule.id}
              </span>{" "}
              <span style={{ fontSize: 14, fontWeight: 600 }}>{rule.name}</span>
              {rule.why ? (
                <p style={{ fontSize: 12, marginTop: 4, color: "var(--color-neutral-700)" }}>
                  {rule.why}
                </p>
              ) : null}
            </div>
          ))}
        </div>

        <Link
          href="/policy"
          className="mono mt-4 inline-block text-xs underline"
          style={{ color: "#2b5da8" }}
        >
          Every rule, with its reasoning and its changelog →
        </Link>

        {moved?.was && take ? (
          <div className="mt-10 p-4" style={{ border: "2px solid var(--color-text)" }}>
            <div
              className="mono uppercase"
              style={{ fontSize: 10, letterSpacing: "0.12em", color: "var(--color-accent)" }}
            >
              A number that changed
            </div>
            <p className="mt-2" style={{ fontSize: 14 }}>
              The take window was {moved.was[0]}–{moved.was[1]}s. It is now {take[0]}–{take[1]}s.
            </p>
            {moved.what_happened ? (
              <p className="mt-2" style={{ fontSize: 12, color: MUTED }}>
                {moved.what_happened}
              </p>
            ) : null}
            <p className="mono mt-3" style={{ fontSize: 11, color: MUTED }}>
              The old value stays in the file beside the new one. A standards document that
              quietly edits itself is not one anybody should trust.
            </p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
