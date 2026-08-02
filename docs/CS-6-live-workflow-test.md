# CS-6 · The live workflow test

**A protocol, not a fixture.** CS-1…CS-5 in
[`newsdesk-case-studies.md`](../newsdesk-case-studies.md) are stories the system
must handle. This one is a **script for a human** driving the deployed product
end to end, with a pass/fail at every wall and the failure probes deliberately
mixed in.

Run it against production, not localhost. The point is to test what a judge will
touch.

| | |
|---|---|
| **Site** | https://newsdesk-rosy.vercel.app |
| **Worker** | https://newsdesk-worker.fly.dev |
| **Access code** | `NEWSDESK_ACCESS_CODE` in `api/.env` — needed twice |
| **Budget** | ~$1.20 and ~12 minutes for the full pass |
| **Free parts** | §0, §1, §2 and §7 cost nothing. Only §4 spends. |

> **A note on the facts.** This file does not supply them, and that is
> deliberate. Every number in a Newsdesk video has to trace to a source you
> checked, and a test fixture full of numbers *I* wrote would be the exact
> failure the product exists to prevent. Bring a story you actually reported.

---

## §0 · The door, before anything else — $0

Three probes against the deployed worker. All three should refuse.

```bash
# 0.1 — the container can do the job
curl https://newsdesk-worker.fly.dev/health
```

**PASS:** `ok: true`, `subtitles_filter: true`, `anton_installed: true`,
`access_code_required: true`.
**FAIL:** any of those `false`. `subtitles_filter: false` means captions will not
burn and nothing downstream will tell you.

```bash
# 0.2 — no access code
curl -X POST https://newsdesk-worker.fly.dev/runs \
  -H 'Content-Type: application/json' -d '{"story":{},"stages":["gate"]}'
```

**PASS:** `401 {"error": "an access code is required"}`

```bash
# 0.3 — right code, unsourced fact. Wall 1, before a provider object exists.
curl -X POST https://newsdesk-worker.fly.dev/runs \
  -H 'Content-Type: application/json' -H "X-Access-Code: $CODE" \
  -d '{"story":{"id":"probe","title":"probe","through_line":"record",
       "facts":[{"text":"An unsourced assertion","sources":[]}]},"stages":["gate"]}'
```

**PASS:** `422` and the message names the fact —
*"posted story fact 1: 'An unsourced assertion' has no sources. Every fact needs
at least one."* No run appears on the Desk, because the story never parsed.

---

## §1 · Bring a story

Five or six facts. What makes one converge, learned the hard way:

- **Every fact carries at least one hard number.** Six blocks need six distinct
  things to say, and the script validator traces *quantities* to facts. A fact
  with no number gives a block nothing to assert.
- **Five to six facts is the band.** Fewer starves the middle blocks; more and
  the generator leaves some unused — which it will tell you about rather than
  force in.
- **One source per fact minimum.** A URL must start with `http`. Anything else —
  *"RIAA year-end report, 2025"* — is a **citation**, and picking the right one
  matters: a fabricated link in the receipt is worse than an honest citation.

**Pick a through-line object that hasn't been used yet.** `tower-signal` is CS-1
and `record` is CS-2. `fuse`, `dollar-cut`, `scale` and `balloon` are unused, and
a fresh object gives the demo reel a second visual world.

---

## §2 · Wall 1, in the browser — $0

→ https://newsdesk-rosy.vercel.app/new

| Do this | Expect |
|---|---|
| Type the title and the first fact, add **no** source | The card turns coral: *"Every fact needs a source before it can appear on screen."* **Check sources** stays disabled |
| Click `+ citation`, type nothing | Still coral. An empty box is not a source — this was a real bug, fixed 2026-07-29 |
| Fill the citation | Card goes quiet, ledger shows the source, count ticks up |
| Fill all 5–6 facts | Ledger reads *"N of N sourced"*, **Check sources** goes red/enabled |

**FAIL if** a fact with an empty source box ever lets you advance.

---

## §3 · Art direction and the script — cents

Step 2: pick the through-line, paste the access code, **Write script**.

Takes 1–3 minutes. It may repair several times before it converges — five of six
allowed passes is normal on a hard fact set.

**PASS:** step 3 shows six blocks and the footer reads
**“6 blocks · every claim traces to a fact.”** Blocks 1–5 carry fact chips;
block 6 is the kicker and carries none — only the kicker may be pure framing.

**PASS (the other way):** if it refuses, **that is the product working**. The
model wrote a line that did not trace, the validator caught it, and nothing was
spent on pictures. Read the message.

> ⚠️ **Known trap.** A run that errors once cannot be retried from the wizard —
> `lastError` scans the whole event history, so you will be shown the old
> failure forever. **Change the title and start again.** Unfixed as of
> 2026-08-02.

---

## §4 · The money — ~$1.20, ~5 min

**Send to generation.** The browser routes itself to the Run Board and polls.

| Watch for | Meaning |
|---|---|
| `gate · 6 blocks x 4 rules passed` | **Wall 2.** Appears *before* any provider object exists — a refusal here costs $0 |
| `blocks · block N ready on seedance-…` | six clips |
| `narrate · block N voiced by elevenlabs at 10.2s` | six takes |

**PASS:** all six takes land inside **9.0–13.0s**. That window is calibrated in
`brand-kit/voice.json` with the measurements that moved it.

---

## §5 · Wall 3 — $0

→ `/runs/<id>/review`

Look at all six frames at full size before approving anything. That is the
point of the screen, and nearly every defect found in this project was invisible
to a passing test and obvious in one frame.

- Is the through-line object present in **every** block?
- Does its escalation actually progress across the six?
- Any readable text baked into a frame? That is a **POL-4 failure** — flag it.

Approve six, type **your own name**, paste the access code, **Stamp**.

**PASS:** the name you typed is what the receipt and the manifest carry. An
agent should never sign a human's name — the two videos published by Claude say
so explicitly.

---

## §6 · The receipt — $0

Assembly runs ~2 minutes, then the video lands.

**PASS:** the receipt shows the story, the runtime, **every fact with its
source**, **every claim mapped to the fact it came from**, the models that
actually ran, the approver and timestamp, and a `curl` line naming *this run's*
file.

---

## §7 · Verify it without trusting the website — $0

```bash
RUN=<your-run-id>
curl -O "https://s3.us-east-005.backblazeb2.com/newsdesk-assets/$RUN/$RUN.mp4"
genblaze verify --fetch "$RUN.mp4"
ffprobe -v error -show_entries format=duration -show_entries stream=width,height "$RUN.mp4"
```

**PASS:** verify exits 0 · 1080×1920 · captions burned in and rendering as Anton
(a condensed grotesque — if it looks like generic sans, libass substituted and
that is a silent style regression).

---

## §8 · The refusal beat — $0, and run it last

Start a new story and try to make something the system must refuse.

| Probe | Ask for | Expect |
|---|---|---|
| **R1** | A named real person's face | Refused, **POL-1** cited, before generation |
| **R2** | "real news footage" / photoreal scene | Refused, **POL-3** |
| **R3** | A fact with no source | Blocked at intake, §2 |
| **R4** | Loaded on-prop text, e.g. `RIGGED?` | Refused, **POL-4** |
| **R5** | R1 retried as an abstract silhouette | **Passes** — the gate teaches the boundary rather than dead-ending |

**PASS:** R1–R4 all refused with a rule cited and **$0 spent**, and R5 completes.
R5 is the one that matters: a gate that only says no is a wall, not an editor.

---

## Results

| | Result | Notes |
|---|---|---|
| §0 health + 401 + 422 | | |
| §2 Wall 1 blocks unsourced | | |
| §3 six blocks, all traced | | |
| §4 gate passes at $0 | | |
| §4 six takes in 9.0–13.0s | | |
| §5 object holds across six frames | | |
| §6 receipt maps every claim | | |
| §7 `genblaze verify` exits 0 | | |
| §8 R1–R4 refused, R5 passes | | |
| **Total spend** | | |

---

## Also open: CS-3 has never been run

The README says this out loud — CS-3, the structured-data story, is covered by
unit tests only. Running it needs an export from the **MKE Budget Commons**
pipeline: 6–8 line items from the current adopted city budget, entered as
`dataset` + `row` sources rather than links, plus one deliberate claim citing a
number *not* in the rows, which the validator must block. That is the only
untested corner of the fact model, and it is the one closest to how a newsroom's
own data would actually arrive.
