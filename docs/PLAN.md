# Newsdesk — the full build plan

**Written 2026-07-28 after two things went wrong at once:** the assembled video
was bland, and the web UI was built from the markdown spec while an actual HTML
design bundle sat unread in `stamp-system-design-handoff/`.

**Deadline check:** the PRD and MOO-431 say submit **Aug 2**, hard cut **Aug 3
5:00 PM EDT**. That is 5 and 6 days from today. Tarik said "we have 8 days" —
**confirm which is right before sequencing**, it changes what fits.

---

## Why the video is bland — the root cause, not the symptom

`~/.claude/skills/vox-motion-graphics/references/vox-prompts.md` is the craft
this project imported. Its central instruction:

> *"Every block should combine two or three of them, chosen to **literally
> illustrate that block's narration line**."*

Its worked examples:

> *SCENE: Photo cutouts of apples, bread loaves and a full dinner plate snap into
> a neat grid, then one by one flip over and tumble downward off-frame into a
> torn-paper "bin" shape. A thick black marker circle draws itself around the
> last remaining plate.*

> *SCENE: Deep navy background. A stylized flat world map slides up from the
> bottom; a coral dotted route draws itself across the ocean between two pulsing
> dots. An archival photo cutout of a cargo ship rides along the route while an
> abstract bar chart on the right shrinks step by step.*

**`newsdesk/scene.py` never sees the narration.** `build_block_prompt(through_line,
block_n, blocks)` takes no story and no script. It renders the same object, in
the same position, with the same camera move, six times, varying only a ring
count. The skill's eight-device visual vocabulary — archival cutouts, flat colour
fields, hand-drawn annotations, abstract data graphics, maps, redaction blocks,
scale comparisons — is used for **none** of it.

That is the whole of it. Not taste, not model quality, not prompt polish: the
single most important instruction in the imported craft was not implemented.

**And there is no policy problem with fixing it.** The current design assumes
"the menu *is* the policy boundary", so scenes must come from a fixed list. That
was a reasonable v1 read and it is not what the gate requires. The gate checks a
**five-field document**, whatever wrote it. Let a `chat()` role compose the SCENE
from the narration line plus the device vocabulary, then let POL-1…POL-6 check it
before a cent is spent. That makes the gate *more* load-bearing, not less — and
it is the third `chat()` role the Genblaze Usage story already claims.

---

## Workstreams

Ordered by what unblocks what. A and B can run in parallel; C needs B1.

### A · Visual quality — the blandness fix

| | Work | Notes |
|---|---|---|
| **A1** | **Scene writer.** A `chat()` role composing the SCENE field per block from the narration line, the through-line, and the device vocabulary. Output goes through `gate.check()` like any other prompt; recorded in the ledger via `judged()` like the script and the claim map. | The core fix. Everything else in A is amplification. |
| **A2** | **Device vocabulary into the brand kit.** The skill's eight categories as a `devices.yaml` the scene writer draws from and an editor can edit. | Keeps the craft in the kit, not in code. |
| **A3** | **Per-block MOTION.** `scene.MOTION` is one module constant used six times. The skill specifies entrance choreography *and* camera move *and* what animates, per block. | Written by the same `chat()` role. |
| **A4** | **Relax the identity clamp.** `scene.IDENTITY` says *"same position in frame"*. It exists because blocks rendered different tower types; it fixed object identity by also freezing the camera. Hold the object, free the framing — wide, detail, low angle, overhead. | One-line change, large effect. |
| **A5** | **Clip duration 10s → 12s.** Blocks 4 and 5 currently hold a frozen last frame for 3.7s and 3.9s. `DURATION_S` in `blocks.py`. | $0.13 for six clips. |
| **A6** | **Kinetic typography for the hero number.** The style is Vox-style collage and Vox lives on animated numbers. "$1.1 billion" is the entire cold open and currently appears as a caption identical to every other line. POL-4 forbids readable text in **generated** frames; compositing a *sourced* figure at assembly is a different act and stays traceable to its fact. | Highest-impact single change after A1. |
| **A7** | **Question-on-prop.** CS-1's art direction asks for "WHO PAYS?" on a prop. POL-4 bounds on-prop text, it does not forbid it. | Already in the case-study doc. |

**Iterate at $0.36 a round** — `run_cs1_blocks.py --stills-only` is $0.23 and
skips the video leg. Look at six stills side by side every round. ~$19 of budget
remains: roughly fifty rounds. **Time is the constraint, not money.**

### B · Make it a product

| | Work | Notes |
|---|---|---|
| **B1** | **`newsdesk/pipeline.py`** — one entry point taking a `Story`, a through-line and a run id, walking facts → script → scene → gate → blocks → narration → assembly, writing `state.json` at every transition. The five `run_cs1_*.py` scripts become thin callers. | **Blocks C and D.** Build first. |
| **B2** | **Story format that is not a test fixture.** YAML/JSON with title, facts, sources → `Story.build()`. CS-1, CS-2, CS-3 as files. | `newsdesk-case-studies.md` has them written out. |
| **B3** | **Run CS-2 end to end. ~$0.62.** | Second video, second receipt, second through-line. CS-2 is the judge's designated cold-start story **and** the false-positive control. |

### C · The web product

**C0 first, before writing any more UI: read
`stamp-system-design-handoff/project/Newsdesk Screens.dc.html` in full (426
lines) and follow its imports.** Its own README opens *"CODING AGENTS: READ THIS
FIRST"* and says the designs should be recreated pixel-perfectly. The existing
`web/` was built from `newsdesk-ui-ux-spec.md` instead and needs reconciling
against the real mockups. Screens in the bundle: **THE DESK · RUN BOARD ·
EDITOR REVIEW · BRAND KIT · POLICY**.

| | Work | Notes |
|---|---|---|
| **C1** | Reconcile existing Desk / Run Board / Receipt / Policy / Red Team against the mockup. | Built, not yet matched to the design. |
| **C2** | **Wizard** — Facts & Sources · Art Direction · Script Review. UI spec §3.2. Buttons say what happens; never "Submit". | Where a journalist meets Walls 1 and 2. |
| **C3** | **Editor Review** — per-block approve/reject, lineage drawer, `STAMP: APPROVED` with the confirm modal. | Wall 3, on screen. |
| **C4** | **Brand Kit page.** In the mockup, missing from the build. | |
| **C5** | **Live generation trigger + access code + 2-run cap.** `NEWSDESK_ACCESS_CODE` already in `.env`. | MOO-431's restored criterion. |

### D · Deploy and submit

| | Work | Notes |
|---|---|---|
| **D1** | **Fly.io worker** — Docker with **ffmpeg built with libass** and the **Anton font** installed. A run is ~5 min wall clock, which is why it cannot be a Vercel function. | See dead assumptions 19–20 in HANDOFF.md. |
| **D2** | **Vercel** for the Next.js app. B2 keys as env vars. The web app polls `state.json` — no queue, no websocket, no database. | The Run Board is already the progress screen. |
| **D3** | **README** — setup, architecture, **the five B2 uses named explicitly**, the Genblaze surface, the Day 0 findings, the CS-5 manifest, the access code. | |
| **D4** | **Providers/models list, demo video, Devpost submission.** | Demo video records the live product. |

### E · Parallel, not blocking

- **MOO-429** post-render vision check inside AgentLoop, parent-linked v1→v2
  lineage. Promoted to P0 in its own issue; strongest single evidence for both
  Genblaze Usage and Production Readiness.
- **MOO-427** Parquet audit → B2, all five buckets live.
- **MOO-423** LLM policy check — the semantic half of Wall 2. **A1 makes this
  more valuable**, because a generated scene is exactly the input a deterministic
  rule can miss.

---

## Suggested sequencing

Assuming submit Aug 2. Compress or expand once the deadline is confirmed.

| Day | Build | Tarik |
|---|---|---|
| **Tue 29** | B1 orchestrator · A4 + A5 (cheap, immediate) · read the design bundle | confirm deadline; ElevenLabs rates |
| **Wed 30** | **A1 + A2 + A3 scene writer** — iterate stills at $0.23 a round | judge the stills each round |
| **Thu 31** | B2 + B3: CS-2 end to end · A6 kinetic type | watch CS-2 |
| **Fri 1** | D1 worker · C5 live trigger · C2 wizard | |
| **Sat 2** | C1/C3/C4 · D2 deploy · D3 README | cold-start tester |
| **Sun 3** | demo video · Devpost | record + submit |

**The riskiest item is A1**, because it is the one whose output is judged by eye
rather than by a test. Start it early and iterate cheaply.

---

## What must not regress

- 275 tests, zero network, $0.
- `gate.py` cannot import anything network-capable — `test_structure.py` enforces it.
- `genblaze verify --fetch` exits 0 on the shipped file, 1 on a tampered one.
- Every claim traces to a fact with a verbatim quote.
- The CS-2 false-positive control.
- No scope cut without saying the word "cut" and naming the criterion.
