# Handoff — Newsdesk, end of Day 3

**Repo:** `/Users/tarikmoody/Documents/Projects/newsdesk` · public at
[github.com/tmoody1973/newsdesk](https://github.com/tmoody1973/newsdesk), `main`, clean
**Linear:** [Newsdesk — Backblaze Generative Media Hackathon](https://linear.app/moodyco/project/newsdesk-backblaze-generative-media-hackathon-5f68ce40d2cc) · team `MOO`
**Deadline:** submit **Aug 2**, hard cut **Aug 3, 5:00 PM EDT** *(Tarik said "8 days" — confirm)*
**Spend:** ~$7 of ~$25 · `uv run pytest tests/ -q` → **277 passed**, zero network, $0

---

# ⛔ THE MANDATE — READ BEFORE PLANNING ANYTHING

**Build the full product. A visitor must be able to create a video.**

Tarik, 2026-07-28, verbatim:

> *"People should be able to create a video, stop being god damn lazy. I want to
> win this hackathon. You don't win for being lazy."*

> *"Why would I record a video if I can do a real video for real on the website?"*

An earlier session cut live generation and the wizard down to a read-only viewer
and called it prudence. That dropped **PRD P0-9**'s stated acceptance — *"a judge
can execute Case Study CS-2 end-to-end without help"* — without saying so, and
over-estimated what was left, since `state.json` polling already gives the
progress UI a live run needs.

## Rules

- **No scope cuts** without saying the word "cut" out loud and naming the
  criterion being dropped. Never present a cut as prudence.
- **"A judge can make a video on the site" is the bar.** Not "a judge can watch
  a video I made."
- **Read the sources before you build.** See `CLAUDE.md` in the repo root — it
  names the file to open for each kind of work. A markdown spec is a summary of
  a design bundle, never a replacement for it. This project lost most of a day
  to that mistake.
- **Verify with your eyes and ears.** View images at full size, listen to audio,
  screenshot the page. Several defects here were invisible to tests and obvious
  in one frame.

---

## Where the work stands

### The video pipeline works end to end and verifies

There is a finished, approved MP4: 72.61s, −16.0 LUFS, true peak −2.2 dBFS,
burned Anton captions, a ducked lo-fi bed with a four-movement arc, and an
embedded manifest naming the approver and tracing twelve claims to six facts.

```
uv run python scripts/run_cs1_assemble.py --approve "Your Name"
uv run genblaze verify --fetch out/assemble/cs1-embedded.mp4     # exit 0
```

One flipped byte → exit 1. Watched and signed off by Tarik.

### The pictures were bland; three rounds fixed most of it

Tarik: *"the video we created is bland!!!! I would never record that in a demo
video."* He was right. The cause was that `scene.py` implemented **one of the
five** items in the vox skill's section titled *"what separates a banger from
postcards"* — and contradicted two of them.

`scene.py` was rewritten (commits `9dc7329`, `25a6f4c`) and now carries:

- **fake-oner** — per-block entry and exit in motion blur so six hard cuts read
  as one unbroken shot
- **scale whiplash** — six different framings: extreme macro, wide, low angle,
  overhead flat-lay, macro detail, crane reveal
- **one impact and one speed ramp per block**, `MOTION` and `AUDIO` per block
  rather than one constant used six times
- **a motif per block** — map, chart, ledger, cutout crowd, archival frame
- **a silhouette bible** in `through-lines.yaml` that holds the object
- **a countable escalation** that renders monotonically

**Current state of the stills** (three rolls, $0.70 total, `--stills-only` is
$0.23 a round):

| | |
|---|---|
| object identity | **6/6** — the same four-legged lattice mast in every block |
| ring contraction | **reads** — decreasing legibly across the six for the first time |
| motifs | landing — map, chart, ledger, crowd, archival mount all visible |
| motion blur | present in frame |
| palette | consistent cream / charcoal / navy / coral |

**The one open defect:** block 1 draws its eight rings as **eight separate
circles scattered around the mast** rather than eight concentric rings. Eight is
too many to nest legibly, so the count instruction outran *"radiating from the
mast"*. Fix is a one-line kit change — `countable.start: 8 → 5`, and add
"concentric" to the noun. **Do this first; it is ten minutes and $0.23.**

**Then re-render the video** with the new stills so there is a good MP4 to show:
`run_cs1_blocks.py` (full, not stills-only) → `run_cs1_assemble.py`.

---

## GMI, as of 2026-07-28 17:00 CDT — verified by curl against the documented endpoint

Docs: https://docs.gmicloud.ai/llms.txt · submit endpoint is
`POST https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/requests`,
body `{"model": ..., "payload": {...}}`, poll `GET .../requests/{request_id}`.

| model | on this API key |
|---|---|
| `gemini-2.5-flash-image` | **DOWN** — times out, zero bytes, every attempt. This is why `IMAGE_MODEL` moved. |
| **`bria-fibo`** | **works**, returns **576×1024 true 9:16**. Current `IMAGE_MODEL`. |
| `seedream-5.0-lite` | works but returns **2048×2048** under both `aspect_ratio` and `ratio` — the old finding is confirmed, it genuinely ignores framing |
| `Flux2-Dev`, `Flux2-Klein` | accept, but slow — never returned inside the test window |
| `gpt-image-2` | "currently inactive". No OpenAI image model is reachable — `gpt-image-1`, `dall-e-3` do not exist on GMI. |
| `flux-kontext-pro` | 500 / 403 |
| `seedance-1-0-pro-fast-251015` | works — current `VIDEO_MODEL` |
| **`seedance-1-5-pro-251215`** | **works, and we have never used it.** Not in `SEEDANCE_SLUGS` or the fallback chain. Newer than what ships. **Test it.** |
| `seedance-2-0-260128` / `-fast-` | 500 "Backend error (401)" |

**Why seedance 2.0 works in Tarik's playground but not here:** the playground
authenticates with his console session; the code uses the API key in `.env`.
Same documented request, same endpoint — 1.0 and 1.5 return 200, 2.0 returns
401. **The key is not entitled to 2.0.** Regenerating it or asking GMI to add
2.0 would fix it, and it is worth doing: 2.0 is the engine that executes
in-prompt cuts and reads "speed ramp" and "FPV" literally, which is exactly what
the fake-oner wants.

---

## Build order

### 0. Ring count fix + re-render the video · ~$0.60, under an hour

Above. Gets a good MP4 on the board before anything else changes.

### 1. `newsdesk/pipeline.py` — the orchestrator · blocks everything else

There is **no `cli.py`, no orchestrator, no single entry point.** Five separate
scripts, each hardcoded to CS-1 (`RUN_ID = "cs1-narration"`,
`CLIP_PREFIX = "cs1-tower-signal/"`, `story = cs1_story()` **from the test
fixtures**). To make a second video today you hand-edit constants in four files
and run five commands in order.

Every core module already takes the story as a parameter — `Story.build()`,
`generate_script()`, `check()`, `run_block()`, `narrate()`, `plan_timeline()`,
`build_run()`. The engine is general; nothing can drive it. **This one gap blocks
CS-2, blocks P0-9, and blocks live generation.**

Also needs a **story format that is not a Python fixture** — YAML/JSON with
title, facts, sources → `Story.build()`. CS-1…CS-5 are written out in
`newsdesk-case-studies.md`.

### 2. Run CS-2 end to end · ~$0.62

A second video, a second receipt, a second through-line (`record`). CS-2 is the
judge's designated cold-start story **and** the false-positive control — no
policy landmines by design, so if it trips a gate the gate is miscalibrated.

### 3. URL ingest — *"paste a link to a story you reported"*

Tarik's idea and the best product idea on the board. Full design in
`docs/PLAN.md` §B4. It **strengthens** Wall 1: extraction proposes, the
journalist confirms each fact, every proposal carries the verbatim span it came
from and is dropped if that span is not in the fetched body, and editing a fact
drops its source until re-attached. `Source.url()` already exists.

Pair it with **Prompt 04's four tests** (`docs/design/PROMPT-PACK-NOTES.md`): a
story is explainable in sixty seconds only if it has one surprising hard number,
a twist, it shows with objects, and it matters to money/safety/work. Score the
pasted story against those four before a cent is spent. *"This story has no
twist"* is the most useful thing this product could tell a reporter.

### 4. The worker — Fly.io, Docker with ffmpeg **built with libass** and Anton

A run is ~5 min wall clock, which is why it cannot be a Vercel function. The web
app polls `state.json` from B2 — no queue, no websocket, no database. **The Run
Board is already the progress screen.**

### 5. The web product — rebuild against the design, which was never used

**`web/` was built from the markdown spec while the real design sat unread.**
Look at `docs/design/stamp-system-design-handoff.pdf` first — the whole design on
one sheet — then `stamp-system-design-handoff/project/Newsdesk Screens.dc.html`
(426 lines) and follow its imports to `project/_ds/modernist-*/styles.css`, which
carries the actual tokens and component classes.

Built so far: Desk, Run Board, Receipt, Policy, Red Team — read-only, and only
the Desk and the Art Direction step have been reconciled against the mockup.
Missing: **Brand Kit page**, wizard steps 1 and 3, Editor Review, live
generation, the access code and its 2-run cap.

**Ask Tarik which stamp treatment he wants** — the mockup offers four (`1a`
rubber classic, `1b` plan-check plate, `1c` outline oversized, `1d` registration
mark) and says pick one. It defaults to `1a`; the current build resembles `1a` by
accident, not by choice.

### 6. Deploy, README, demo video, submit

MOO-431. The demo video records the live product, not a substitute for it. Tarik
is making it in HyperFrames.

---

## Read these before building

| Building… | Open first, in full |
|---|---|
| **Any UI** | `docs/design/stamp-system-design-handoff.pdf`, then the `.dc.html` and its `_ds` stylesheet |
| **Block prompts / visual craft** | `docs/design/vox-explainer-prompt-pack.pdf`, `docs/design/PROMPT-PACK-NOTES.md`, and `~/.claude/skills/vox-motion-graphics/` — **all three files**, `SKILL.md` included |
| **Assembly** | design spec §6.6 in `docs/superpowers/specs/2026-07-26-newsdesk-design.md` |
| **Policy** | `policy/policy.yaml` — the live source. The mockup shows an older POL set; the YAML wins. |
| **Stories / fixtures** | `newsdesk-case-studies.md` — CS-1…CS-5 with art direction and motifs |
| **Plan** | `docs/PLAN.md` |

---

## Assumptions that died — do not resurrect them

### Scene and style

1. **Seedance has no style-reference slot.** Every GMI video family routes images
   to keyframe slots only. *(MOO-415)*
2. **Passing a style key as an image input makes consistency worse.** Naming the
   palette in text locked it. *(MOO-424)*
3. **`bria-fibo` accepts `reference_images`, `image` and `image_url`, returns 200
   on all three, and reads none of them.** Third instance on this project of GMI
   taking a parameter it does not use. **Accepted has never meant used.**
4. **"A tall broadcast tower" is three ambiguous words** and every model resolves
   them to a different landmark — one roll gave a lattice mast, two CN-Tower
   shapes, a pagoda and a spire across six blocks of one story. Fixed by the
   silhouette bible in `through-lines.yaml`.
5. **Negations are weak.** A silhouette ending "NO observation deck, NO disc, NO
   bulge, NO pod" still grew pods on 2 of 6. Describe what IS there.
   `scene-guidance.txt` already said this about text; it is just as true of shape.
6. **A percentage is not renderable.** "About eighty percent through that change"
   came back non-monotonic twice. Exact counts render; proportions of an abstract
   change do not.
7. **Freezing the camera to fix the object froze the video.** The old
   `IDENTITY` clamp said "same position in frame" — it held the object and
   produced six identical wides. Hold the object; free the framing.
8. **`seedream-5.0-lite` ignores aspect ratio** under both `aspect_ratio` and
   `ratio`. Re-tested 2026-07-28; the original finding stands.
9. **GMI reads `ratio`; genblaze emits `aspect_ratio`.** No alias.
   `register_seedance_ratio()` fixes it.
10. **`fallback_models` is inert against every real GMI failure** — it fires only
    on `MODEL_ERROR`, which the classifier reaches only for "not found" and only
    after auth/server checks have claimed anything with 401/403/400/5xx. GMI says
    "model X does not exist" over HTTP 404. `run_block` and `run_take` walk their
    chains themselves.
11. **The undated slug `seedance-1-0-pro-fast` does not exist.**
12. **The style key is documentation.** Published, wired into nothing. Deliberate.
13. **The prompt pack's "the style key is the whole game" is wrong on this
    stack.** Written for Higgsfield, which has an image-reference slot. GMI does
    not.

### Narration

14. **`eleven_v3` does not accept SSML `<break>`.** Break tags work on every
    ElevenLabs model *except* v3; v3 takes audio tags. `[pause]` buys ~0.36s per
    internal sentence boundary, `[long pause]` ~1.25s. They are interpreted, not
    spoken — `silencedetect` proves it and duration alone cannot. Word alignment
    is **not** a valid check: it aligns to input characters.
15. **`[short pause]` buys nothing.** Dropped.
16. **An overrun has no correction on this stack.** `voice_settings.speed` is not
    forwarded by the adapter; shortening a line edits words `claims.py` has
    traced to a fact.
17. **Six concurrent ElevenLabs calls return `code=rate_limit`** and push blocks
    onto LMNT — a narrator change we caused. `TTS_CONCURRENCY = 2`.
18. **`rate_limit` carries no status code.** `_TRANSIENT` held "429" and read the
    most transient failure there is as fatal.
19. **`register_pricing()` silently drops a connector's param contract** when the
    connector has no families — it would have swapped LMNT's narrator for the
    provider default while the manifest still named Nathan. Use `pricing._price()`.
20. **LMNT pads heavily** — one take came back 40.08s raw for 11.35s of words.
21. **The take window is 9.0–13.0s**, widened from 9.0–10.5 and **not** derived
    from POL-5: at the measured 1.94–2.80 w/s that implies 8.21–13.95s, wide
    enough that no compliant script could ever fail. Two tests hold the two
    published numbers against each other.

### Assembly

22. **Homebrew's core `ffmpeg` is built without libass** — no `subtitles` filter.
    `ffmpeg-full` is bottled and keg-only. `assembly.resolve_ffmpeg()` picks by
    **capability, not name**. Installing it upgraded x265 and broke the existing
    `ffmpeg` until `brew reinstall ffmpeg`. **The Fly image must build libass.**
23. **Anton must be installed** — `brew install --cask font-anton`, and in the
    Docker image. A missing face falls back **silently**.
24. **ffmpeg's ASS demuxer rejects anything before `[Script Info]`** and reports
    it as `Unable to open <path>` — which names the filename and says nothing
    about the content.
25. **Clip-to-block mapping is in each run's own `manifest.json`, not the path.**
    `run.name` carries `block-N`. Guessing from sort order pairs the wrong
    picture with the wrong line and reads as a style problem.
26. **`force_instrumental` works only with a bare `prompt`,** never with a plan.
27. **`music_v1` takes a `MusicPrompt` (sections); `music_v2` takes a
    `CompositionPlan` (chunks, no global styles).** Not interchangeable.
28. **The composed bed came back at −14.3 LUFS**, louder than the −17.4 LUFS
    narration. Gain is computed from a measurement, not picked.
29. **Platforms normalise down, not up.** Delivery is −16 LUFS, −1 dBTP ceiling,
    headroom caps the gain.
30. **A bed at 12–18 dB under dialogue is a speech-first mix and vanishes under
    lo-fi.** This one runs music-forward at 8.6 dB, ducked 5:1 not 9:1 — a 9:1
    ratio removes a bed rather than stepping it back.

### Governance

31. **`chat()` is not a Pipeline citizen** — hence `decisions.py`. *(MOO-433)*
32. **`arun()` returns `PipelineResult`, not `Run`.**
33. **`ctx.params` does not exist on `PricingContext`** — it carries
    `(step, assets, provider_payload)`.
34. **Approval is not publication.** `state.approve()` sets `awaiting_approval`;
    assembly sets `published` only after verify passes.

---

## Gotchas

- **`gate.py` must never import anything network-capable.** `test_structure.py`
  walks its import graph. Don't "fix" that test — it is what makes "$0 on a
  refusal" structural and the CS-4 battery runnable anywhere.
- **`asset.duration` is `None`** from the ElevenLabs adapter. `ffprobe` it.
- **`ObjectStorageSink.write_run()` re-fetches assets by URL** — 401s on a
  private bucket. Hence public `assets` and `brand-kit`.
- **`ParquetSink` needs `pyarrow`.** Don't remove it.
- **B2 bucket creation needs an all-buckets key.**
- **Keep the CS-2 false-positive control.** It caught a gate bug that would have
  blocked 100% of legitimate blocks while citing a real rule.
- **`web/.env.local` is gitignored** and holds live B2 keys. Vercel needs them as
  environment variables.
- **The stills path has no retry.** `run_cs1_blocks.py` calls the Pipeline
  directly; a transient GMI timeout fails all six at $0. `run_block` has the
  retry; the stills path should use it.

---

## Costs, measured

| | Rate | Six-block story |
|---|---|---|
| `bria-fibo` | $0.039/asset *(UNVERIFIED)* | $0.23 |
| `seedance-1-0-pro-fast-251015` | $0.022/asset | $0.13 |
| `kling-image2video-v2.1-master` (fallback) | $0.28/asset | $1.68 |
| `eleven_v3` direct | $0.22/1k chars *(UNVERIFIED)* | $0.26 |
| `lmnt` direct (fallback) | $0.15/1k chars | $0.15 |
| ElevenLabs Music | **unregistered — fix this** | ? |

**~$1.23 a story on the primary chain. ~$18 left — about fifteen more stories.
Time is the constraint, not money.**

---

## Open questions for Tarik

1. **Deadline** — Aug 2 per the PRD, or the 8 days he mentioned?
2. **Which stamp treatment** — `1a`, `1b`, `1c` or `1d`?
3. **GMI credit balance.** Asked repeatedly, never answered. `estimate_cost()`
   returns `None`; it can only come from the console.
4. **Regenerate the GMI API key** to get seedance 2.0? The playground has it, the
   key does not.
5. **ElevenLabs rates are guesses.** `eleven_v3` at $0.22/1k chars is UNVERIFIED
   and **Music is unregistered entirely**, so the bed currently reports as free.
   https://elevenlabs.io/app/settings/billing
6. **Clip duration is 10s but blocks can run 14s** — blocks 4 and 5 hold a frozen
   last frame for ~3.7s and ~3.9s. Signed off as acceptable. `DURATION_S` in
   `blocks.py`; six clips cost $0.13.
7. **Voice cloning for the demo only?** Tarik's own voice would be strong for the
   demo and wrong for the product — a provenance tool whose narrator is a clone
   of a real person invites the question POL-1 forecloses.
