import Link from "next/link";

/* Hallmark · macrostructure: Long Document (numbered criteria) · genre: editorial
 * theme: system-managed (Newsdesk modernist DS) · enrichment: hand-built SVG
 * architecture diagram (Tier B) · honest copy: every number is measured;
 * source of truth: docs/JUDGING-CRITERIA.md, adapted not invented.
 */

export const metadata = {
  title: "Newsdesk — for the judges",
};

/** The architecture, drawn in the site's own ink: cream paper, 2px ink strokes,
 *  mono labels, stamp-red for the two things that make this system itself —
 *  the $0 refusal path and the refusal ledger folding into the manifest. */
function Architecture() {
  const ink = "var(--color-text)";
  const red = "var(--color-accent)";
  const mono = "var(--font-plex-mono, ui-monospace, monospace)";
  const box = { fill: "var(--color-surface)", stroke: ink, strokeWidth: 2 };
  const label = { fontFamily: mono, fontSize: 11, fill: ink };
  const small = { fontFamily: mono, fontSize: 9.5, fill: "var(--color-neutral-700)" };
  const arrow = { stroke: ink, strokeWidth: 1.5, markerEnd: "url(#arr)" };
  return (
    <figure style={{ margin: 0, overflowX: "auto" }}>
      <svg viewBox="0 0 720 560" style={{ width: "100%", minWidth: 560, maxWidth: 880, display: "block" }} role="img" aria-label="Newsdesk architecture: journalist to web app to worker, through three walls, through Genblaze to providers, everything landing in five B2 buckets, ending in an MP4 with an embedded, verifiable manifest.">
        <defs>
          <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0L10 5L0 10z" fill={ink} />
          </marker>
        </defs>

        {/* Row 1 — people and surfaces */}
        <rect x="12" y="14" width="150" height="44" {...box} />
        <text x="87" y="33" textAnchor="middle" style={label}>JOURNALIST</text>
        <text x="87" y="47" textAnchor="middle" style={small}>facts · sources · approval</text>

        <rect x="238" y="14" width="170" height="44" {...box} />
        <text x="323" y="33" textAnchor="middle" style={label}>WEB APP</text>
        <text x="323" y="47" textAnchor="middle" style={small}>Next.js · Vercel</text>

        <rect x="488" y="14" width="180" height="44" {...box} />
        <text x="578" y="33" textAnchor="middle" style={label}>RENDER WORKER</text>
        <text x="578" y="47" textAnchor="middle" style={small}>Python · Fly · own ffmpeg</text>

        <line x1="162" y1="36" x2="234" y2="36" {...arrow} />
        <line x1="408" y1="36" x2="484" y2="36" {...arrow} />
        <text x="446" y="28" textAnchor="middle" style={small}>POST /runs</text>

        {/* The three walls — a wall is drawn as a wall */}
        <rect x="488" y="86" width="180" height="118" fill="none" stroke={red} strokeWidth="2" strokeDasharray="1 0" />
        <text x="497" y="103" style={{ ...label, fill: red }}>THE THREE WALLS</text>
        <text x="497" y="122" style={small}>1 · no fact without a source</text>
        <text x="497" y="138" style={small}>2 · policy gate — no network,</text>
        <text x="509" y="151" style={small}>no credentials, $0 refusals</text>
        <text x="497" y="168" style={small}>3 · no publish without a</text>
        <text x="509" y="181" style={small}>named approver</text>
        <line x1="578" y1="58" x2="578" y2="82" {...arrow} />

        {/* Genblaze */}
        <rect x="238" y="120" width="170" height="52" {...box} />
        <text x="323" y="141" textAnchor="middle" style={label}>GENBLAZE</text>
        <text x="323" y="156" textAnchor="middle" style={small}>pipeline · manifest · verify</text>
        <line x1="484" y1="146" x2="412" y2="146" {...arrow} />
        <text x="447" y="139" textAnchor="middle" style={small}>every paid step</text>

        {/* Providers */}
        <rect x="12" y="96" width="150" height="40" {...box} />
        <text x="87" y="113" textAnchor="middle" style={label}>GMI CLOUD</text>
        <text x="87" y="127" textAnchor="middle" style={small}>stills · video · text</text>
        <rect x="12" y="146" width="150" height="40" {...box} />
        <text x="87" y="163" textAnchor="middle" style={label}>ELEVENLABS</text>
        <text x="87" y="177" textAnchor="middle" style={small}>narration voice</text>
        <rect x="12" y="196" width="150" height="40" {...box} />
        <text x="87" y="213" textAnchor="middle" style={label}>LMNT</text>
        <text x="87" y="227" textAnchor="middle" style={small}>fallback voice</text>
        <line x1="234" y1="146" x2="166" y2="116" {...arrow} />
        <line x1="234" y1="146" x2="166" y2="166" {...arrow} />
        <line x1="234" y1="152" x2="166" y2="212" {...arrow} />

        {/* The refusal ledger */}
        <rect x="238" y="216" width="170" height="52" {...box} />
        <text x="323" y="237" textAnchor="middle" style={{ ...label, fill: red }}>DECISION LEDGER</text>
        <text x="323" y="252" textAnchor="middle" style={small}>every refusal, and why</text>
        <line x1="530" y1="204" x2="380" y2="214" {...arrow} />
        <text x="470" y="224" textAnchor="middle" style={small}>pass · reject · revise</text>

        {/* B2 — the database */}
        <rect x="130" y="312" width="460" height="96" {...box} />
        <text x="360" y="334" textAnchor="middle" style={label}>BACKBLAZE B2 — FIVE BUCKETS, ONE JOB EACH</text>
        <text x="360" y="356" textAnchor="middle" style={small}>assets (public) · brand-kit (public) · runs · manifests · audit (private, enforced in code)</text>
        <text x="360" y="378" textAnchor="middle" style={small}>no other database exists — every page load reads B2,</text>
        <text x="360" y="392" textAnchor="middle" style={small}>every stage completion writes B2</text>
        <line x1="323" y1="268" x2="323" y2="308" {...arrow} />
        <line x1="578" y1="204" x2="578" y2="308" {...arrow} />
        <line x1="87" y1="236" x2="180" y2="308" {...arrow} />

        {/* The receipt */}
        <rect x="200" y="452" width="320" height="60" {...box} />
        <text x="360" y="474" textAnchor="middle" style={label}>PUBLISHED MP4</text>
        <text x="360" y="490" textAnchor="middle" style={small}>manifest embedded in the file · ledger digest folded in</text>
        <text x="360" y="503" textAnchor="middle" style={{ ...small, fill: red }}>edit one refusal afterwards → genblaze verify fails</text>
        <line x1="360" y1="408" x2="360" y2="448" {...arrow} />
        <text x="372" y="432" style={small}>assembly, only after a named approval</text>
      </svg>
      <figcaption className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)", marginTop: 8 }}>
        The shape of the system. Red marks what makes it Newsdesk: refusals cost $0
        and refusals are part of the tamper-evident record.
      </figcaption>
    </figure>
  );
}

const CRITERIA: Array<{ n: string; title: string; ask: string; body: React.ReactNode }> = [
  {
    n: "1",
    title: "Real-world utility",
    ask: "Does the app solve a practical problem for a clear audience?",
    body: (
      <>
        <p>
          Built by a working public-radio newsroom in Milwaukee, for the reason
          newsrooms don&apos;t use generative video today: a newsroom cannot publish
          what it cannot account for. Newsdesk is built for the checking, not around
          it — three walls between a fact and a frame.
        </p>
        <p>
          The best evidence is a catch, not a video. On the Milwaukee lead-pipes
          story, the system&apos;s first script contained two correctly-sourced numbers
          that read as a contradiction (annual vs cumulative replacements). The wall
          surfaced it, the editor rewrote the fact, and the original wording stays in
          the file — corrections stay in the record. On the same story it also did
          arithmetic nobody entered — 65,000 pipes at 5,000 a year misses the 2037
          target — traced it to the two facts it came from, and captioned it{" "}
          <span className="mono">&quot;THE MATH DOESN&apos;T CLOSE.&quot;</span>
        </p>
        <p style={{ color: "var(--color-neutral-700)" }}>
          Thin spot, stated plainly: one newsroom has used it — ours.
        </p>
      </>
    ),
  },
  {
    n: "2",
    title: "Production readiness",
    ask: "Does it function reliably beyond a demo?",
    body: (
      <>
        <p>
          Deployed in two pieces — the app on Vercel, the renderer on Fly with its
          own ffmpeg and typeface, and a health check that reports what it can
          actually do, not just that it&apos;s alive. <strong>488 tests in ~18
          seconds, zero network, $0</strong> — enforced, not promised: a structure
          test walks the safety gate&apos;s import graph and fails the build if
          anything network-capable appears. The pipeline is resumable stage by
          stage, so a narration failure never re-buys the pictures.
        </p>
        <p>
          It has failed in production, correctly: during a real upstream outage the
          claim-checker couldn&apos;t run, so the gate refused every block — nine
          attempts, $0 spent. &quot;I can&apos;t verify this&quot; is treated as
          &quot;I won&apos;t ship this.&quot;
        </p>
      </>
    ),
  },
  {
    n: "3",
    title: "B2 storage & data orchestration",
    ask: "Is Backblaze B2 used meaningfully?",
    body: (
      <>
        <p>
          <strong>B2 is the database, not the file cabinet.</strong> There is no
          Postgres, no SQLite — the live state of every story is a{" "}
          <span className="mono">state.json</span> in the runs bucket; the desk you
          see is rendered from B2 on every load. Five buckets, one job each:
          assets and brand-kit (public), runs, manifests, and audit (private) —
          and the public/private split is a frozen set in code, so a bucket
          can&apos;t drift public by someone forgetting.
        </p>
        <p>
          The audit bucket is the unusual one: a durable record of what the system{" "}
          <em>refused</em> to do, kept separately, and cryptographically tied to the
          finished video.
        </p>
      </>
    ),
  },
  {
    n: "4",
    title: "Use of Genblaze",
    ask: "Is Genblaze used meaningfully across models, providers, steps?",
    body: (
      <>
        <p>
          Every generative step rides Genblaze: five providers across four
          modalities — stills, video, and text on GMI Cloud, voice on ElevenLabs
          with an LMNT fallback the app walks by itself — landing in B2 through{" "}
          <span className="mono">ObjectStorageSink</span>, with the manifest
          embedded in the MP4 and validated by{" "}
          <span className="mono">genblaze verify</span>.
        </p>
        <p>
          <strong>The contribution we&apos;re proudest of:</strong> Genblaze&apos;s
          manifest records everything that runs through a pipeline — but plain{" "}
          <span className="mono">chat()</span> calls can&apos;t ride one, and in this
          product those calls <em>are</em> the governance. A provenance record that
          only lists successes is a brochure. So we built the missing half: every
          judgement — pass, reject, revise — lands in a decision ledger, and at
          assembly a digest of that ledger is folded into the manifest Genblaze
          embeds. Changing a single refusal afterwards breaks{" "}
          <span className="mono">genblaze verify</span> on the video. Not consuming
          the framework — closing a real hole in it, with its own verification.
        </p>
      </>
    ),
  },
];

export default function Judges() {
  return (
    <main style={{ maxWidth: 900, paddingBottom: 72 }}>
      <header>
        <span className="card-kicker">For the judges</span>
        <h1 className="anton" style={{ fontSize: "clamp(30px, 5vw, 48px)", textTransform: "uppercase", lineHeight: 1.05, margin: "6px 0 0", overflowWrap: "anywhere" }}>
          How Newsdesk meets the criteria
        </h1>
        <p style={{ maxWidth: 680, fontSize: 15, lineHeight: 1.65, marginTop: 14 }}>
          Everything below is checkable — the live app, the worker, and the code are
          public, and the claims carry the commands that verify them. The framing
          that matters: <strong>the governance is the product; the video is the
          output.</strong>
        </p>
      </header>

      {/* Check it yourself */}
      <section className="card" style={{ marginTop: 24, padding: "16px 20px" }}>
        <span className="card-kicker">Check it yourself</span>
        <div className="mono" style={{ fontSize: 12.5, lineHeight: 2, marginTop: 6 }}>
          <div>live app · <a href="https://newsdesk-rosy.vercel.app" style={{ color: "var(--color-accent)" }}>newsdesk-rosy.vercel.app</a> — no sign-in</div>
          <div>worker · <a href="https://newsdesk-worker.fly.dev/health" style={{ color: "var(--color-accent)" }}>newsdesk-worker.fly.dev/health</a></div>
          <div>code · <a href="https://github.com/tmoody1973/newsdesk" style={{ color: "var(--color-accent)" }}>github.com/tmoody1973/newsdesk</a></div>
          <div style={{ marginTop: 6 }}>cd api && uv run pytest tests/ -q <span style={{ color: "var(--color-neutral-600)" }}># 488 tests, no network, $0</span></div>
          <div>uv run python -m newsdesk ../stories/cs2.yaml --only gate <span style={{ color: "var(--color-neutral-600)" }}># the gate, free, no keys</span></div>
        </div>
      </section>

      {/* Architecture */}
      <section style={{ marginTop: 40 }}>
        <span className="card-kicker">The shape of it</span>
        <h2 className="anton" style={{ fontSize: 28, textTransform: "uppercase", margin: "6px 0 14px" }}>Architecture</h2>
        <Architecture />
      </section>

      {/* Criteria */}
      <section style={{ marginTop: 40 }}>
        {CRITERIA.map((c) => (
          <article key={c.n} style={{ borderTop: "2px solid var(--color-text)", padding: "18px 0 26px", marginTop: c.n === "1" ? 0 : 8 }}>
            <div style={{ display: "grid", gridTemplateColumns: "56px minmax(0,1fr)", gap: 18 }}>
              <span className="anton" aria-hidden style={{ fontSize: 40, lineHeight: 1, color: "var(--color-accent)" }}>{c.n}</span>
              <div style={{ maxWidth: 660 }}>
                <h3 className="anton" style={{ fontSize: 22, textTransform: "uppercase", margin: 0 }}>{c.title}</h3>
                <p className="mono" style={{ fontSize: 11.5, color: "var(--color-neutral-600)", margin: "4px 0 10px" }}>{c.ask}</p>
                <div style={{ fontSize: 14.5, lineHeight: 1.65, display: "flex", flexDirection: "column", gap: 10 }}>{c.body}</div>
              </div>
            </div>
          </article>
        ))}
      </section>

      {/* What to look at first */}
      <section style={{ marginTop: 32 }}>
        <span className="card-kicker">If you look at four things</span>
        <ol style={{ fontSize: 14.5, lineHeight: 1.8, maxWidth: 660, margin: "10px 0 0", paddingLeft: 22 }}>
          <li>Run the gate command above — the refusal machinery, free, no credentials.</li>
          <li>Read <span className="mono">api/newsdesk/decisions.py</span> — the refusal-ledger design, explained at the source.</li>
          <li>Open the Milwaukee lead-pipes video and read its receipt.</li>
          <li>Read the Day-6 section of <span className="mono">docs/HANDOFF.md</span> — the journalism error the wall caught, written up as it happened.</li>
        </ol>
        <div style={{ marginTop: 22, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link href="/desk" className="btn btn-primary">See the published runs</Link>
          <Link href="/" className="btn btn-secondary">The front page</Link>
        </div>
      </section>
    </main>
  );
}
