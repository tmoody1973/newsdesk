import Link from "next/link";

/**
 * The plain-English page. Written for someone who has never seen Newsdesk —
 * a judge, a new journalist, a skeptical editor. No term appears without its
 * meaning; no claim appears that the product does not enforce in code.
 */

export const metadata = {
  title: "How Newsdesk works",
};

function Section({
  kicker,
  title,
  children,
}: {
  kicker: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginTop: 40 }}>
      <span className="card-kicker">{kicker}</span>
      <h2 className="font-display" style={{ fontSize: 26, textTransform: "uppercase", margin: "6px 0 12px" }}>
        {title}
      </h2>
      <div style={{ maxWidth: 720, fontSize: 15, lineHeight: 1.65 }}>{children}</div>
    </section>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ padding: "16px 20px", marginTop: 12 }}>
      <p style={{ margin: 0, fontWeight: 600 }}>
        <span className="mono" style={{ color: "var(--color-accent)", marginRight: 10 }}>{n}</span>
        {title}
      </p>
      <p style={{ margin: "6px 0 0", fontSize: 14, lineHeight: 1.6, color: "var(--color-neutral-700)" }}>
        {children}
      </p>
    </div>
  );
}

export default function About() {
  return (
    <main style={{ paddingBottom: 80 }}>
      <h1 className="font-display" style={{ fontSize: 44, textTransform: "uppercase", lineHeight: 1.05, maxWidth: 800 }}>
        A newsroom video tool that refuses to say what it cannot prove.
      </h1>
      <p style={{ maxWidth: 720, fontSize: 17, lineHeight: 1.6, marginTop: 16 }}>
        Newsdesk turns a reporter&apos;s verified facts into a short vertical news video —
        script, pictures, narration, subtitles — for about a dollar, in about ten minutes.
        What makes it different is what it <em>won&apos;t</em> do: it will not put a single
        sentence on screen that can&apos;t be traced, word for word, to a fact a named
        journalist entered. When it can&apos;t prove a line, it refuses — for free —
        and tells you what to do about it.
      </p>
      <div style={{ marginTop: 20, display: "flex", gap: 12 }}>
        <Link href="/new" className="btn btn-primary">Start a story</Link>
        <Link href="/" className="btn btn-secondary">See the desk</Link>
      </div>

      <Section kicker="The journalist's path" title="How a story becomes a video">
        <Step n={1} title="Start with facts — yours.">
          Paste a link to a story you reported. Newsdesk reads that page and proposes
          facts, each with the exact quote it came from — a proposal whose quote is not
          on the page character-for-character is dropped, not shown. You confirm each
          fact yourself; nothing is ever added for you. You can also just type facts by
          hand. Either way, <strong>every fact needs a source</strong> — that&apos;s the
          first wall, and a story can&apos;t exist without passing it.
        </Step>
        <Step n={2} title="Pick the look.">
          A <strong>brand kit</strong> is a visual style your newsroom owns — the house
          mixed-media collage, or the paper-diorama documentary style (sepia newsprint
          worlds, one burnt-orange object, censor-bar figures). The{" "}
          <strong>through-line object</strong> is one physical thing — a fuse, an
          hourglass, a stack of notes — that appears in every scene and carries the
          story&apos;s escalation. Pick one of each. Requests outside the menu are
          checked against policy; real people&apos;s likenesses and fake photoreal news
          scenes are blocked.
        </Step>
        <Step n={3} title="It writes the script — and checks every sentence.">
          The video is six 10-second blocks. Each narrated line must fit the voice
          window (23–27 words — that&apos;s what fills ten seconds at the narrator&apos;s
          measured pace), and every claim, number, and name in it must trace to one of
          your facts with the supporting words matching <em>verbatim</em>. Drafts that
          fail are refused and redrafted automatically, up to eight times, at no cost.
          If none survives, you see exactly which sentence broke which rule — and what
          to do next.
        </Step>
        <Step n={4} title="It renders the pictures and the voice.">
          Only after the script survives every check does money get spent: six video
          clips (~$1 total) and a measured narration take per block. The Run Board
          shows each stage live — writing the script, rendering pictures, recording
          narration — with every cost on the screen.
        </Step>
        <Step n={5} title="A human signs it.">
          Nothing publishes without a named editor approving on the review screen.
          That&apos;s the third wall: the approval — with the approver&apos;s name — is
          written into the record before assembly will even run.
        </Step>
        <Step n={6} title="The receipt travels with the video.">
          Every published video carries a manifest: every fact and its source, every
          model decision, every refusal and retry, every dollar spent, the approver&apos;s
          name, and a cryptographic fingerprint of the file. Anyone can verify that the
          video they&apos;re watching is the one that was approved.
        </Step>
      </Section>

      <Section kicker="Why you can trust it" title="The three walls">
        <p>
          <strong>Wall 1 — no fact without a source.</strong> The same parser checks a
          story whether it comes from the browser, a file, or a link. A fact with no
          source is refused at the door, by name.
        </p>
        <p>
          <strong>Wall 2 — the policy gate, before any spend.</strong> Every scene
          description is checked against written policy — no photorealism that could
          pass for camera footage, no real person&apos;s likeness, no text on screen
          that doesn&apos;t trace to an entered fact. The gate runs with no network and
          no credentials, which is what makes &quot;$0 spent on a refusal&quot;
          structural rather than a promise.
        </p>
        <p>
          <strong>Wall 3 — no publish without a name.</strong> Assembly will not run
          for a story with no named approver. The name is in the receipt.
        </p>
      </Section>

      <Section kicker="When it says no" title="A refusal is the product working">
        <p>
          The machine never judges whether your reporting is true — that&apos;s your
          byline, not its. What it judges is whether it can <em>prove</em> each
          sentence it wants to say, against your own entered words. When it can&apos;t,
          it refuses before spending anything, names the exact sentence and rule, and
          ends with the remedy: <span className="mono" style={{ fontSize: 13 }}>
          &quot;What to do: retry — refusals are free&quot;</span> — or, when a fact is
          simply too long to speak inside one ten-second line, <em>which</em> fact to
          trim. The alternative is a tool that would have aired the sentence anyway.
          Corrections have your name on them; refusals don&apos;t.
        </p>
      </Section>

      <Section kicker="The numbers" title="What it costs">
        <p>
          A full run — script, six clips, narration, assembly — costs about{" "}
          <strong>$1.30</strong> and takes about ten minutes. Refused scripts cost{" "}
          <strong>$0</strong>. Every cost appears in the run&apos;s own log, and the
          total is printed on the receipt.
        </p>
      </Section>

      <div style={{ marginTop: 48, display: "flex", gap: 12 }}>
        <Link href="/new" className="btn btn-primary">Start a story</Link>
        <Link href="/policy" className="btn btn-secondary">Read the policy</Link>
      </div>
    </main>
  );
}
