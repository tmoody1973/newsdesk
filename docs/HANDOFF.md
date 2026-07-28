# Handoff — Newsdesk, end of Day 3

**Repo:** `/Users/tarikmoody/Documents/Projects/newsdesk` · public at
[github.com/tmoody1973/newsdesk](https://github.com/tmoody1973/newsdesk), `main`
**Linear:** [Newsdesk — Backblaze Generative Media Hackathon](https://linear.app/moodyco/project/newsdesk-backblaze-generative-media-hackathon-5f68ce40d2cc) · team `MOO`
**Deadline:** submit **Aug 2**, hard cut **Aug 3, 5:00 PM EDT**
**Spend:** ~$6 of ~$25 · `uv run pytest tests/ -q` → **275 passed**, zero network, $0

---

# ⛔ THE MANDATE — READ THIS BEFORE PLANNING ANYTHING

**Build the full product. A visitor must be able to create a video.**

Tarik, 2026-07-28, verbatim:

> *"People should be able to create a video, stop being god damn lazy. I want to
> win this hackathon. You don't win for being lazy."*

> *"Why would I record a video if I can do a real video for real on the website?"*

This **reverses a scope call made earlier the same day**, and the reversal is
correct. A previous session recommended cutting live generation and the wizard
down to a read-only viewer, arguing that a half-finished form is worse than a
working viewer. That was wrong twice:

1. **It dropped a stated P0 criterion without saying so.** PRD **P0-9**'s
   acceptance is *"a judge can execute Case Study CS-2 end-to-end without
   help."* A read-only site cannot satisfy that. MOO-431 separately lists
   *"full live generation, hard-capped at 2 runs per code"* as its own
   criterion — the two were folded together and cut as one thing.
2. **It over-estimated what was left.** The progress UI a live run needs already
   exists: `state.json` is written to B2 at every transition and the Run Board
   already renders it. The genuinely missing pieces are an orchestrator and a
   worker.

## Rules for this build

- **No scope cuts.** If something genuinely cannot ship, say the word "cut" out
  loud, name the criterion being dropped, and let Tarik decide. Never present a
  cut as prudence.
- **"A judge can make a video on the site" is the bar.** Not "a judge can watch
  a video I made."
- The read-only site that exists is the **floor, not the goal**. Keep it working
  as a fallback; do not stop there.

---

## The one thing that matters

**The engine is general. Nothing can drive it.**

Every core module already takes the story as a parameter — `Story.build()`,
`generate_script()`, `check()`, `run_block()`, `narrate()`, `plan_timeline()`,
`build_run()`. None of them know they are running CS-1.

But there is **no `cli.py`, no orchestrator, no single entry point.** Five
separate scripts, each hardcoded:

```
run_cs1_script.py      story = cs1_story()          # from the TEST FIXTURES
run_cs1_blocks.py      sink(f"cs1-{tl_id}")
run_cs1_narration.py   RUN_ID = "cs1-narration"
map_cs1_claims.py      RUN_ID = "cs1-narration"
run_cs1_assemble.py    RUN_ID, CLIP_PREFIX = "cs1-narration", "cs1-tower-signal/"
```

To make a second video today you would hand-edit constants in four files and run
five commands in the right order. **This single gap blocks CS-2, blocks P0-9,
and blocks live generation on the web.** Build it first.

---

## Build order

Each step leaves a working system. Do not start the next until the current one
runs end to end.

### 1. `newsdesk/pipeline.py` — the orchestrator (blocks everything else)

One entry point taking a `Story`, a through-line id and a run id, walking
facts → script → gate → blocks → narration → assembly and writing `state.json`
at every transition. Mostly wiring calls that already exist and are tested; the
five `run_cs1_*.py` scripts become thin callers rather than parallel
implementations.

Needs a **story format that is not a Python fixture** — YAML or JSON with title,
facts and sources, loaded through `Story.build()`. `newsdesk-case-studies.md`
has CS-1…CS-5 written out; CS-2 and CS-3 should become files.

### 2. Run CS-2 end to end from the CLI — **~$0.62**

`$0.23` stills + `$0.13` clips + `$0.26` narration + `$0` assembly. This is the
proof that the product is a product: a second video, a second receipt, a second
through-line (`record` — a record growing). CS-2 is the judge's designated
cold-start story **and** the false-positive control — it has no policy landmines
by design, so if it trips a gate, the gate is miscalibrated.

### 3. The worker — Fly.io, Docker with ffmpeg + Anton

Design spec §13. A run is ~5 minutes wall clock (blocks 2m14s, narration ~1m,
assembly ~1m), which is why it cannot be a Vercel function. The web app polls
`state.json` from B2 — no job queue, no websocket, no database. **The Run Board
is already the progress screen.** The Docker image needs ffmpeg *with libass*
and the Anton font (see dead assumptions 19–20).

### 4. Live generation from the web + access code

`NEWSDESK_ACCESS_CODE` is already in `.env`. Hard cap of 2 runs per code so a
visitor cannot drain the budget. MOO-431's criterion, restored.

### 5. The wizard — three steps

Facts & Sources · Art Direction · Script Review, per UI spec §3.2. Buttons say
what happens (`Add fact`, `Check sources`, `Write script`), never "Submit". The
unsourced-fact chip and the unmapped-claim chip are where the walls become
visible to a journalist rather than to a test — that is the demo.

### 6. Deploy, README, demo video, submit

MOO-431's remaining criteria. The demo video is a **recording of the live
product**, not a substitute for it. Tarik is making it in HyperFrames.

---

## What works, verified against real output

- **A finished MP4 exists and verifies.** 72.61s, −16.0 LUFS, true peak −2.2 dBFS.
  `genblaze verify --fetch out/assemble/cs1-embedded.mp4` → **exit 0**; one
  flipped byte → **exit 1**. Watched and signed off by Tarik.
- **Script** — `chat()` on `anthropic/claude-haiku-4.5` via GMI. Six blocks,
  every claim traced to verbatim evidence, after repair passes.
- **Blocks** — `gemini-2.5-flash-image` 768×1344 → `seedance-1-0-pro-fast-251015`
  704×1248 true 9:16. Six blocks, $0.366. Stills read as one video from text
  alone, no style-key image anywhere.
- **Narration** — six takes on `eleven_v3` / Marcus Louis, silence stripped,
  `ffprobe`d, $0.256, 64.0s. CS-5's TTS leg passes: a revoked key puts all six on
  LMNT with the manifest naming the substitution.
- **Music** — lo-fi bed, four movements on block boundaries, ducked under the
  voice, C2PA-signed, licensed-catalogue model.
- **Receipt** — 15 steps, 6 facts, 12 claims each quoting its fact verbatim,
  approver named, embedded in the MP4.
- **Web (read-only so far)** — Desk, Run Board, Receipt, Policy, Red Team.
  `cd web && npm run build && npm start`.
- **Brand kit** — published to `b2://newsdesk-brand-kit/kit/`, loads at runtime,
  refuses to fall back on a missing kit. `scripts/verify_brand_kit.py` → 4/4.

**Done:** MOO-415…422, 424, 425, 426, 428, 432, 433.
**Open:** MOO-423, 427, 429, 430, **431**.

---

## Where to read first

Don't re-derive any of this.

| What | Where |
|---|---|
| Architecture, budget, day plan | `docs/superpowers/specs/2026-07-26-newsdesk-design.md` |
| **Assembly timing model** §6.6 | same file — read before touching assembly |
| Requirements P0-1…P0-9 | `newsdesk-prd.md` |
| Fixtures CS-1…CS-5 (they *are* the test suite) | `newsdesk-case-studies.md` |
| Screens, stamp system, tokens | `newsdesk-ui-ux-spec.md` |
| Editorial rules POL-1…POL-6 | `policy/policy.yaml` |
| Narrator, pacing, assembly contract | `brand-kit/voice.json` |
| Why text bleeds into frames | `brand-kit/scene-guidance.txt` |
| Art-direction menu (6 through-lines) | `brand-kit/through-lines.yaml` |

Every Linear issue carries Intent / Acceptance / Verification, and the closed
ones have evidence comments with real output. **Read the issue before building
it** — most were rewritten when testing killed an assumption.

---

## Assumptions that died — do not resurrect them

Each cost real money or a real run.

### Generation

1. **Seedance has no style-reference slot.** Every GMI video family routes images
   to keyframe slots only. *(MOO-415)*
2. **Passing a style key as an image input makes consistency worse.** Naming the
   palette in text locked it. *(MOO-424)*
3. **`seedream-5.0-lite` ignores `aspect_ratio`;** `gemini-2.5-flash-image`
   honours it.
4. **GMI reads `ratio`; genblaze emits `aspect_ratio`.** No alias between them —
   why a clip came back landscape with a portrait `first_frame`.
   `register_seedance_ratio()` fixes it.
5. **`fallback_models` is inert against every real GMI failure.** It fires only
   on `MODEL_ERROR`, which the classifier reaches only for "not found" and only
   after auth/server checks have claimed anything with 401/403/400/5xx. GMI says
   "model X does not exist" over HTTP 404 → `UNKNOWN` → no fallback. `run_block`
   and `run_take` walk their chains themselves.
6. **Seedance 2.0 is flaky, not unavailable.** Ten raw submits gave five 200s and
   five 500s. Hence same-model retry before falling down the chain.
7. **The undated slug `seedance-1-0-pro-fast` does not exist.**
8. **`arun()` returns `PipelineResult`, not `Run`.**
9. **`ctx.params` does not exist on `PricingContext`** — it carries
   `(step, assets, provider_payload)`.
10. **The style key is documentation.** Committed, published, wired into nothing.
    Deliberate.
11. **The visuals never see the script.** `build_block_prompt(through_line,
    block_n, blocks)` takes no story and no narration. The pictures come entirely
    from the through-line menu — by design, because POL-3 and POL-4 mean the
    visuals are metaphor and never depiction. **Consequence: two stories sharing
    a through-line produce identical pictures.** Per-block motifs are specified
    in UI spec §3.2 and are **NOT built**. For a product where visitors bring
    their own stories, this is real work and probably belongs in the wizard's
    Art Direction step.

### Narration

12. **`eleven_v3` does not accept SSML `<break>`.** Break tags work on every
    ElevenLabs model *except* v3; v3 takes audio tags. `[pause]` buys ~0.36s per
    internal sentence boundary, `[long pause]` ~1.25s. They are interpreted, not
    spoken — `silencedetect` proves that and duration alone cannot. Word-level
    alignment is **not** a valid check: it aligns to input characters, so the tag
    appears whether it was voiced or not.
13. **`[short pause]` buys nothing.** Dropped from the ladder.
14. **An overrun has no correction on this stack.** `voice_settings.speed` is not
    forwarded by the genblaze adapter, and shortening a line edits words
    `claims.py` has traced to a fact. Re-rendering was priced: eight extra
    renders, one landed, ~$0.25.
15. **Six concurrent ElevenLabs calls return `code=rate_limit`** and push blocks
    onto LMNT — a narrator change we caused ourselves. `TTS_CONCURRENCY = 2`.
16. **`rate_limit` carries no status code.** `_TRANSIENT` held "429" and read the
    most transient failure there is as fatal.
17. **`register_pricing()` silently drops a connector's param contract** when the
    connector has no model families. It would have swapped LMNT's narrator for
    the provider default while the manifest still named Nathan. Use
    `pricing._price()`.
18. **LMNT pads heavily** — one take came back 40.08s raw for 11.35s of words.
    This is why silence is stripped before measuring.

### Assembly

19. **Homebrew's core `ffmpeg` bottle is built without libass** — no `subtitles`
    filter at all. `ffmpeg-full` is the same tap, bottled, keg-only.
    `assembly.resolve_ffmpeg()` picks a binary **by capability, not by name**.
    Installing `ffmpeg-full` upgraded x265 and broke the existing `ffmpeg` until
    `brew reinstall ffmpeg`. **The Fly.io image must build ffmpeg with libass.**
20. **Anton must be installed** — `brew install --cask font-anton` locally, and
    in the Docker image. ffmpeg does not embed a face and a missing one falls
    back **silently**.
21. **ffmpeg's ASS demuxer rejects a file with anything before `[Script Info]`**
    and reports it as `Unable to open <path>` — which names the filename and says
    nothing about the content.
22. **The clip-to-block mapping is in each run's own `manifest.json`, not in the
    path.** The HIERARCHICAL sink names folders by run UUID; `run.name` carries
    `block-N`. Guessing from sort order pairs the wrong picture with the wrong
    line and reads as a style problem.
23. **`force_instrumental` works only with a bare `prompt`,** never with a plan.
24. **`music_v1` takes a `MusicPrompt` (sections); `music_v2` takes a
    `CompositionPlan` (chunks, styles per chunk, no global layer).** Not
    interchangeable; the error names the parameter, not the mismatch.
25. **The composed bed came back at −14.3 LUFS — louder than the −17.4 LUFS
    narration.** Gain is computed from a measurement, not picked.
26. **Platforms normalise down, not up.** A quiet file just plays quiet. Delivery
    is −16 LUFS with a −1 dBTP ceiling, and headroom caps the gain.

### Governance

27. **`chat()` is not a Pipeline citizen** — hence `decisions.py`. *(MOO-433)*
28. **The vox pacing rule is backwards for our voice.** POL-5 is 23–27 words
    across 2–3 sentences.
29. **The take window is 9.0–13.0s**, widened from 9.0–10.5s and **not** derived
    from POL-5: at the measured 1.94–2.80 w/s that implies 8.21–13.95s, wide
    enough that no compliant script could ever fail. Two tests hold the two
    published numbers against each other.
30. **The prompt pack's "style key is the whole game" is wrong on this stack.**
    Written for Higgsfield.

---

## Gotchas that will bite

- **`gate.py` must never import anything network-capable.** `test_structure.py`
  walks its import graph. Don't "fix" that test. This is why `brandkit.py` cannot
  be imported by `blockprompt.py` — they meet at `NEWSDESK_BRAND_KIT_DIR`. It is
  also what makes the CS-4 battery runnable anywhere for $0.
- **`asset.duration` is `None`** from the ElevenLabs adapter. `ffprobe` it.
- **`ObjectStorageSink.write_run()` re-fetches assets by URL**, so it 401s on a
  private bucket. Hence public `assets` and `brand-kit`.
- **`ParquetSink` needs `pyarrow`.** Already added; don't remove it.
- **B2 bucket creation needs an all-buckets key.**
- **A fictional slug matching `^seedance-` raises at preflight and costs $0.** One
  matching no family runs permissively and costs an image first.
- **Keep the CS-2 false-positive control.** It caught a gate bug that would have
  blocked 100% of legitimate blocks while citing a real rule.
- **`web/.env.local` is gitignored** and holds live B2 keys. Vercel needs them as
  environment variables.
- **Approval is not publication.** `state.approve()` sets `awaiting_approval`;
  assembly sets `published` only after verify passes.

---

## Costs, measured

| | Rate | Six-block story |
|---|---|---|
| `gemini-2.5-flash-image` | $0.039/asset | $0.23 |
| `seedance-1-0-pro-fast-251015` | $0.022/asset | $0.13 |
| `kling-image2video-v2.1-master` (fallback) | $0.28/asset | $1.68 |
| `eleven_v3` direct | $0.22/1k chars *(UNVERIFIED)* | $0.26 |
| `lmnt` direct (fallback) | $0.15/1k chars | $0.15 |
| ElevenLabs Music | *(unregistered — fix this)* | ? |

**A full story on the primary chain is ~$1.23.** ~$19 remains — roughly fifteen
more stories. **Iterate freely; the budget is not the constraint, time is.**

---

## Working agreements observed

- Verify with real output before claiming anything. **View images at full size;
  listen to audio.** Several bugs this session were invisible to tests and
  obvious in a screenshot.
- Read the provider's own docs before trusting the SDK's vocabulary. The most
  expensive mistakes were the SDK and the provider disagreeing about a name.
- Make the first paid call produce something needed anyway.
- Move Linear issues as work completes; attach evidence comments with real output.
- Corrections are stated plainly and the wrong version stays in the record — see
  design spec §6.3, `policy.yaml` POL-2 `changelog`, `voice.json`
  `why_the_window_moved`.
- **Encode the convention, not the value.** Where a number was tuned by ear or by
  eye, the test asserts the named band it must sit in, and says why.

---

## Open questions for Tarik

1. **GMI credit balance.** Asked repeatedly, never answered. `estimate_cost()`
   returns `None`, so it can only come from the console. ~$6 spent of an assumed
   $25.
2. **The ElevenLabs rates are guesses.** `eleven_v3` is registered at $0.22/1k
   characters, marked UNVERIFIED; ElevenLabs **Music is unregistered entirely**,
   so the bed currently reports as free. Real figures:
   https://elevenlabs.io/app/settings/billing
3. **Clip duration is 10s but blocks can run 14s**, so blocks 4 and 5 hold a
   frozen last frame for ~3.7s and ~3.9s. Signed off as acceptable.
   `DURATION_S = 10` in `blocks.py`; six seedance clips cost $0.13.
4. **Ring contraction doesn't read** across the six blocks. Cosmetic, $0.23 a
   round. Likely fix is explicit counts ("five of eight rings visible") rather
   than percentages — models handle countable things better than proportional
   ones.
5. **Per-block motifs** (dead assumption 11) — needed if visitors bringing their
   own stories should get visually distinct videos rather than the same six
   pictures per through-line.
6. **Voice cloning for the demo only?** Tarik's own voice would be strong for the
   demo. It would be wrong for the product — a provenance tool whose narrator is
   a clone of a real person invites the question POL-1 forecloses.
