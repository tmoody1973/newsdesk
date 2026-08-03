import Link from "next/link";

/* Hallmark · macrostructure: Masthead front page · genre: editorial
 * theme: system-managed (Newsdesk modernist DS — cream paper · ink · stamp-red)
 * nav: N3 side-rail (preserved app chrome) · footer: Ft5 statement
 * enrichment: brand wordmark + mark (real assets, web/public/brand)
 * pre-emit critique: P5 H5 E4 S5 R5 V4
 * honest copy: every number on this page is a measured value from real runs.
 */

export const metadata = {
  title: "Newsdesk — governed generative video for newsrooms",
};

/** The front page. A judge or a first-time journalist lands here; the page's
 *  one job is to make the product's argument in plain English and route them
 *  to the desk or the wizard. Structured like the thing it serves: a paper. */

function Rule({ double = false }: { double?: boolean }) {
  return (
    <div
      aria-hidden
      style={{
        borderTop: "2px solid var(--color-text)",
        borderBottom: double ? "1px solid var(--color-text)" : "none",
        height: double ? 5 : 0,
        margin: "0 0 4px",
      }}
    />
  );
}

const STEPS: Array<{ title: string; body: string }> = [
  {
    title: "Start with facts — yours.",
    body: "Paste a link to a story you reported and Newsdesk proposes facts, each carrying the exact quote it came from — a proposal whose quote is not on the page character-for-character is dropped, not shown. You confirm every fact yourself, or type them by hand. Every fact needs a source before a story can exist.",
  },
  {
    title: "Pick the look.",
    body: "A brand kit is a visual style your newsroom owns — the house mixed-media collage, or the paper-diorama documentary world. The through-line object is one physical thing that appears in every scene and carries the escalation, so six clips read as one film.",
  },
  {
    title: "It writes the script — and checks every sentence.",
    body: "Six ten-second blocks. Each narrated line must fit the narrator's measured pace (23–27 words), and every claim in it must trace to one of your facts with the supporting words matching verbatim. Failed drafts are refused and redrafted, up to eight times, at no cost — and a surviving refusal names the sentence, the rule, and what to do next.",
  },
  {
    title: "It renders the pictures and the voice.",
    body: "Money is spent only after the script survives every check: six clips and a measured narration take per block. The Run Board shows each stage live, with every cost on screen.",
  },
  {
    title: "A human signs it.",
    body: "Nothing publishes without a named editor approving on the review screen. The approval — with the approver's name — is written into the record before assembly will run.",
  },
  {
    title: "The receipt travels with the video.",
    body: "Every published video carries a manifest: every fact and source, every refusal and retry, every dollar, the approver's name, and a cryptographic fingerprint of the file itself.",
  },
];

const WALLS = [
  {
    n: "WALL 1",
    title: "No fact without a source",
    body: "The same parser checks a story whether it arrives from the browser, a file, or a link. A fact with no source is refused at the door, by name.",
  },
  {
    n: "WALL 2",
    title: "The policy gate, before any spend",
    body: "Every scene is checked against written policy — no camera-passable photorealism, no real person's likeness, no on-screen text that traces to nothing. The gate runs with no network and no credentials: “$0 spent on a refusal” is structural, not a promise.",
  },
  {
    n: "WALL 3",
    title: "No publish without a name",
    body: "Assembly will not run for a story with no named approver. The name is in the receipt.",
  },
];

export default function FrontPage() {
  return (
    <main style={{ maxWidth: 980, paddingBottom: 72 }}>
      {/* Masthead */}
      <header style={{ paddingTop: 8 }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/newsdesk-horizontal-light.svg" alt="Newsdesk" style={{ height: 52, width: "auto" }} />
          <p className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)", margin: 0, textAlign: "right" }}>
            governed generative video for newsrooms
            <br />
            every video ships with its receipt
          </p>
        </div>
        <div style={{ marginTop: 14 }}>
          <Rule double />
        </div>
      </header>

      {/* Lede */}
      <section style={{ marginTop: 28 }}>
        <h1
          className="anton"
          style={{
            fontSize: "clamp(34px, 6vw, 64px)",
            lineHeight: 1.04,
            textTransform: "uppercase",
            letterSpacing: ".005em",
            margin: 0,
            maxWidth: 860,
            overflowWrap: "anywhere",
          }}
        >
          It refuses to say what it cannot prove.
        </h1>
        <p style={{ maxWidth: 660, fontSize: 17, lineHeight: 1.6, marginTop: 18 }}>
          Newsdesk turns a reporter&apos;s verified facts into a short vertical news video —
          script, pictures, narration, subtitles — for about a dollar, in about ten
          minutes. It will not put a sentence on screen that can&apos;t be traced, word for
          word, to a fact a named journalist entered. When it can&apos;t prove a line, it
          refuses — for free — and says what to do about it.
        </p>
        <div style={{ marginTop: 22, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link href="/new" className="btn btn-primary">Start a story</Link>
          <Link href="/desk" className="btn btn-secondary">See the desk</Link>
        </div>
      </section>

      {/* The numbers — measured, not invented */}
      <section style={{ marginTop: 40 }}>
        <Rule />
        <div
          className="mono"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "10px 36px",
            fontSize: 12,
            color: "var(--color-neutral-700)",
            padding: "10px 0",
          }}
        >
          <span><strong style={{ color: "var(--color-text)" }}>~$1.30</strong> a finished video</span>
          <span><strong style={{ color: "var(--color-accent)" }}>$0</strong> spent on a refusal</span>
          <span><strong style={{ color: "var(--color-text)" }}>23–27</strong> words per narrated line</span>
          <span><strong style={{ color: "var(--color-text)" }}>8</strong> free redrafts before surfacing</span>
          <span><strong style={{ color: "var(--color-text)" }}>3</strong> walls between a fact and a frame</span>
        </div>
        <Rule />
      </section>

      {/* The path — front-page index */}
      <section style={{ marginTop: 44 }}>
        <span className="card-kicker">The journalist&apos;s path</span>
        <h2 className="anton" style={{ fontSize: 30, textTransform: "uppercase", margin: "6px 0 6px" }}>
          How a story becomes a video
        </h2>
        <div>
          {STEPS.map((s, i) => (
            <article
              key={s.title}
              style={{
                display: "grid",
                gridTemplateColumns: "56px minmax(0, 1fr)",
                gap: 18,
                padding: "18px 0",
                borderTop: i === 0 ? "none" : "1px solid var(--color-divider)",
              }}
            >
              <span
                className="anton"
                aria-hidden
                style={{ fontSize: 34, lineHeight: 1, color: "var(--color-accent)" }}
              >
                {i + 1}
              </span>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{s.title}</h3>
                <p style={{ fontSize: 14, lineHeight: 1.65, color: "var(--color-neutral-800)", margin: "6px 0 0", maxWidth: 640 }}>
                  {s.body}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* The walls */}
      <section style={{ marginTop: 44 }}>
        <span className="card-kicker">Why you can trust it</span>
        <h2 className="anton" style={{ fontSize: 30, textTransform: "uppercase", margin: "6px 0 16px" }}>
          Three walls
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(260px, 100%), 1fr))",
            gap: 14,
          }}
        >
          {WALLS.map((w) => (
            <div key={w.n} className="card" style={{ padding: "18px 20px", borderTop: "3px solid var(--color-text)" }}>
              <span className="mono" style={{ fontSize: 11, color: "var(--color-accent)", letterSpacing: ".08em" }}>{w.n}</span>
              <h3 style={{ fontSize: 15, fontWeight: 600, margin: "8px 0 0" }}>{w.title}</h3>
              <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--color-neutral-700)", margin: "8px 0 0" }}>{w.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Refusals */}
      <section style={{ marginTop: 44, maxWidth: 720 }}>
        <span className="card-kicker">When it says no</span>
        <h2 className="anton" style={{ fontSize: 30, textTransform: "uppercase", margin: "6px 0 12px" }}>
          A refusal is the product working
        </h2>
        <p style={{ fontSize: 15, lineHeight: 1.65 }}>
          The machine never judges whether your reporting is true — that&apos;s your byline,
          not its. It judges whether it can <em>prove</em> each sentence against your own
          entered words. When it can&apos;t, it refuses before spending anything, names the
          exact sentence and rule, and ends with the remedy:
        </p>
        <p
          className="mono"
          style={{
            fontSize: 13,
            lineHeight: 1.6,
            background: "var(--color-surface)",
            borderLeft: "3px solid var(--color-accent)",
            padding: "12px 16px",
            margin: "12px 0 0",
          }}
        >
          What to do: retry — refusals are free and the model redrafts. If it keeps
          refusing, trim F3 (27 words) to one spoken sentence.
        </p>
        <p style={{ fontSize: 15, lineHeight: 1.65, marginTop: 12 }}>
          The alternative is a tool that would have aired the sentence anyway.
          Corrections have your name on them; refusals don&apos;t.
        </p>
      </section>

      {/* Statement footer */}
      <footer style={{ marginTop: 56 }}>
        <Rule double />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, paddingTop: 16, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/newsdesk-mark-small-light.svg" alt="" aria-hidden style={{ height: 28, width: 28 }} />
            <span className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)" }}>
              Newsdesk — every claim starts with a source.
            </span>
          </div>
          <nav aria-label="Front page" style={{ display: "flex", gap: 16 }}>
            <Link href="/desk" className="mono" style={{ fontSize: 11, color: "var(--color-text)" }}>The desk</Link>
            <Link href="/policy" className="mono" style={{ fontSize: 11, color: "var(--color-text)" }}>Policy</Link>
            <Link href="/brand-kit" className="mono" style={{ fontSize: 11, color: "var(--color-text)" }}>Brand kit</Link>
            <Link href="/judges" className="mono" style={{ fontSize: 11, color: "var(--color-text)" }}>For the judges</Link>
            <Link href="/new" className="mono" style={{ fontSize: 11, color: "var(--color-accent)" }}>Start a story</Link>
          </nav>
        </div>
      </footer>
    </main>
  );
}
