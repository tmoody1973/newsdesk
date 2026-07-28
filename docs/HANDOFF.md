# Handoff — Newsdesk, end of Day 2

**Repo:** `/Users/tarikmoody/Documents/Projects/newsdesk`
**Branch:** `tarikjmoody/moo-425-moo-419-brand-kit-and-script` (11 commits ahead of `main`)
**Linear:** [Newsdesk — Backblaze Generative Media Hackathon](https://linear.app/moodyco/project/newsdesk-backblaze-generative-media-hackathon-5f68ce40d2cc) · team `MOO`
**Deadline:** submit **Aug 2**, hard cut **Aug 3, 5:00 PM EDT**
**Spend:** ~$5 of ~$25 · `uv run pytest tests/ -q` → **209 passed**, zero network, $0

## The one thing that matters

**Nothing has produced a finished MP4 yet.** Facts, script, stills, clips *and
now voice* all work end to end. What is missing is assembly.

**MOO-428 (approval + assemble + embed + verify) is the only thing on the
critical path.** Do not start the vision check, the web UI, the Parquet audit or
the second policy check before it. Everything it needs already exists: six clips
in `b2://newsdesk-assets/cs1-{through-line}/`, six trimmed takes in
`b2://newsdesk-assets/cs1-narration/`, and `voice_duration_s` per block in
`b2://newsdesk-runs/cs1-narration/state.json`.

## Where to read first

Don't re-derive any of this — it is all written down.

| What | Where |
|---|---|
| Architecture, budget, day plan | `docs/superpowers/specs/2026-07-26-newsdesk-design.md` |
| **Assembly timing model** (new, §6.6) | same file — read this before touching MOO-428 |
| Requirements (P0-1…P0-9) | `newsdesk-prd.md` |
| Fixtures CS-1…CS-5 (they *are* the test suite) | `newsdesk-case-studies.md` |
| Screens, stamp system, tokens | `newsdesk-ui-ux-spec.md` |
| Editorial rules POL-1…POL-6, **now v2** | `policy/policy.yaml` |
| Narrator, pacing data, **assembly contract** | `brand-kit/voice.json` |
| Why text bleeds into frames | `brand-kit/scene-guidance.txt` |
| Art-direction menu | `brand-kit/through-lines.yaml` |

Every Linear issue carries Intent / Acceptance / Verification, and the closed
ones have evidence comments with real output. **Read the issue before building
it** — MOO-419, 424, 425, 426 and 428 were all rewritten when testing killed an
assumption.

## Status

**Done:** MOO-415, 416, 417, 418, **419**, 420, 421, 422, **425**, **426**, 432, 433.
**Effectively done:** MOO-424 — six blocks generate end to end and CS-5 passes;
only ring-contraction legibility is open, and it is cosmetic.
**Open:** MOO-423, **428**, 427, 429, 430, 431.

What works, verified against real output:

- **Script** — `chat()` on `anthropic/claude-haiku-4.5` via GMI. CS-1 passes in
  28s: six blocks at 23–27 words, every claim traced to verbatim evidence, zero
  orphan facts, after two repair passes.
- **Blocks** — `gemini-2.5-flash-image` 768×1344 → `seedance-1-0-pro-fast-251015`
  704×1248 true 9:16, 10.0s. Six blocks, $0.366, 2m14s. Stills read as one video
  **from text alone**, no style-key image anywhere.
- **CS-5** — sabotaged blocks complete on the Kling fallback with the manifest
  naming the model that ran; a fully-dead chain fails closed; healthy blocks stay
  on the primary.
- **Narration** — six takes on `eleven_v3` / Marcus Louis, silence stripped,
  `ffprobe`d, uploaded, $0.256, 64.0s of runtime. CS-5's TTS leg passes: a
  revoked ElevenLabs key puts all six on LMNT with the manifest naming the
  substitution, $0.15. Run it with `scripts/run_cs1_narration.py [--reuse]
  [--sabotage]`.
- **Brand kit** — published to `b2://newsdesk-brand-kit/kit/`, loads at runtime,
  refuses to fall back on a missing kit. `scripts/verify_brand_kit.py` → 4/4.

## Immediate next work

### MOO-428 — approval, assembly, embed, verify

The assembly criteria were rewritten today against design spec **§6.6**. The old
ones prescribed a fixed ten-second window with short takes centred, which is
itself a named failure mode. The model now is **audio leads, picture follows**:

1. strip leading/trailing silence *before any timing decision*
2. measure the trimmed file with `ffprobe` (`asset.duration` is `None`)
3. narration starts **0.4s after its cut**, not on it
4. block length = `0.4 + take + tail(0.5–1.5s)`; gaps **allowed to be uneven**
5. clip longer → trim it; shorter → **hold the last frame**
6. music is an arc, not a loop
7. subtitles ≤ 2 lines, timed to the trimmed audio

Never: speed-compress the voice, stretch video, squeeze audio to fill a window,
centre a take, space gaps evenly. The numbers live in `voice.json`'s
`assembly_contract` block, not in code constants.

Everything assembly needs is measured and saved. Read `voice_duration_s` off the
run state rather than re-probing — it is already the trimmed number. The takes in
B2 are the trimmed files; the raw ones were never uploaded, and
`raw_duration_s` in the state is what makes "we stripped the silence" checkable.

**Before you plan the timeline, read the open question at the bottom about the
two windows.** Three of six blocks currently land at 10.9-12.6s against a
published 9.0-10.5s window, so a six-block piece runs ~64s rather than ~60s.
Nothing is broken by that — §6.6 derives block length from the take — but the
number you budget the piece against should be the measured one.

## Assumptions that died — do not resurrect them

Each cost real money or a real run. Linear comments have the evidence.

**From earlier sessions, still true:**

1. **Seedance has no style-reference slot.** Every GMI video family routes images
   to keyframe slots only. *(MOO-415)*
2. **Passing a style key as an image input makes consistency worse.** Naming the
   palette in text locked it. Confirmed again today: six text-only stills read as
   one video. *(MOO-424)*
3. **`seedream-5.0-lite` ignores `aspect_ratio`;** `gemini-2.5-flash-image`
   honours it.
4. **Framing, not negation, drives text bleed.** *(scene-guidance.txt)*
5. **The vox pacing rule is backwards for our voice.** POL-5 is 23–27 words
   across 2–3 sentences.
6. **`chat()` is not a Pipeline citizen** — hence `decisions.py`. *(MOO-433)*

**New today, and several are corrections to corrections:**

7. **GMI reads `ratio`; genblaze emits `aspect_ratio`.** No alias between them.
   This is why a clip came back 1248×704 landscape with a portrait `first_frame`
   — the parameter arrived under a name nothing read. `register_seedance_ratio()`
   fixes it. **I first recorded this as "seedance ignores aspect ratio" and
   inverted the whole chain to Kling on that basis** — which would have shipped
   every clip on a model costing 12.7× more.
8. **`fallback_models` is inert against every real GMI failure.** It fires only
   on `MODEL_ERROR`, a branch the classifier reaches only for "not found" /
   "not available", *after* auth and server checks have claimed anything with
   401/403/400/5xx in it. GMI says "model X does not exist" over HTTP 404 →
   `UNKNOWN` → no fallback. **CS-5 would have passed by never engaging.**
   `run_block` walks the chain itself.
9. **Seedance 2.0 is flaky, not unavailable.** Ten raw submits to
   `seedance-2-0-fast-260128` gave five 200s and five 500 "Backend error (401)".
   **This repo recorded "not entitled" twice before the retest.** Hence
   same-model retry before falling down the chain.
10. **The undated slug `seedance-1-0-pro-fast` does not exist.** GMI carries
    dated builds; the registry's `example_slugs` are the real names.
11. **`arun()` returns `PipelineResult`, not `Run`.** Reading `.steps` off it
    silently yields nothing.
12. **`ctx.params` does not exist on `PricingContext`** — it carries
    `(step, assets, provider_payload)`. The `AttributeError` was swallowed inside
    the pricing hook, so every per-second model priced at `None` while looking
    configured.
13. **The style key is documentation.** Committed, published, and wired into
    nothing. Deliberate.
14. **The prompt pack's "style key is the whole game" is wrong on this stack.**
    Written for Higgsfield. See `docs/` and the MOO-428 comment.

**Narration, 2026-07-28 (MOO-426):**

15. **`eleven_v3` does not accept SSML `<break>`.** ElevenLabs documents break
    tags on every model *except* v3; v3 takes audio tags. `[pause]` buys ~0.36s
    at each internal sentence boundary, `[long pause]` ~1.25s, and they are
    interpreted rather than spoken — which `silencedetect` proves and duration
    alone cannot. Word-level alignment is **not** a valid check: it aligns
    against input characters, so the tag appears whether it was voiced or not.
16. **`[short pause]` buys nothing** and was removed from the ladder. v3's audio
    tags are probabilistic and the smallest notch is the most likely to be
    ignored.
17. **Six concurrent ElevenLabs calls return `code=rate_limit`** and push four of
    six blocks onto LMNT — a narrator change we caused ourselves, recorded as
    though the provider had failed. `TTS_CONCURRENCY = 2`.
18. **`rate_limit` carries no status code.** `_TRANSIENT` held "429" and read the
    most transient failure there is as fatal.
19. **`register_pricing()` silently drops a connector's param contract** when the
    connector has no model families. It would have swapped LMNT's narrator for
    the provider default while the manifest still named Nathan. Use
    `pricing._price()`.
20. **LMNT pads heavily** — one take came back 40.08s raw for 11.35s of words.
21. **An overrun has no correction on this stack.** `voice_settings.speed` is not
    forwarded by the adapter, and shortening a line would edit words `claims.py`
    has already traced to a fact. Re-rendering was tried and priced: eight extra
    renders, one landed, ~$0.25.

## Gotchas that will bite

- **`gate.py` must never import anything network-capable.** `test_structure.py`
  walks its import graph. Don't "fix" that test. This is why `brandkit.py` cannot
  be imported by `blockprompt.py` — they meet at `NEWSDESK_BRAND_KIT_DIR`.
- **`asset.duration` is `None`** from the ElevenLabs adapter. `ffprobe` it.
- **Every catalogued seedance slug tested works through genblaze**, including the
  `-upscale` one, because `input_from` supplies the `first_frame` it wants. The
  only reliable sabotage is a fictional slug — which is also what CS-5 prescribes.
- **A fictional slug matching `^seedance-` raises at *preflight*** (family match →
  probe → NOT_FOUND) and costs $0. One that matches no family runs permissively
  and costs an image before failing at the wire. Both are handled; know which
  you're testing.
- **GMI throttles rapid sequential calls** — a clean script run makes four and the
  fourth 429s. `script.py` has backoff; narration will need the same.
- **`judged()` records the exception message now, not just its type.** Keep it —
  a rate limit, a bad slug and a revoked key were previously indistinguishable in
  the ledger, and all three read as the checker working.
- **`ObjectStorageSink.write_run()` re-fetches assets by URL**, so it 401s on a
  private bucket. Hence public `assets` and `brand-kit`.
- **`ParquetSink` needs `pyarrow`.** Already added; don't remove it.
- **B2 bucket creation needs an all-buckets key.**
- **Anton must be resolvable by libass at burn time.** ffmpeg does not embed it
  and a missing face falls back *silently*. `fc-list | grep -i anton`.
- **Keep the CS-2 false-positive control.** It caught a gate bug that would have
  blocked 100% of legitimate blocks while citing a real rule.

## Costs, measured

| | Rate | Six-block story |
|---|---|---|
| `gemini-2.5-flash-image` | $0.039/asset | $0.23 |
| `seedance-1-0-pro-fast-251015` | $0.022/asset | $0.13 |
| `kling-image2video-v2.1-master` (fallback) | $0.28/asset | $1.68 |
| `eleven_v3` direct | $0.22/1k chars (UNVERIFIED) | $0.26 |
| `lmnt` direct (fallback) | $0.15/1k chars | $0.15 |

A full story on the primary chain is **$1.23** — $0.97 of picture plus $0.26 of
voice — against the design's projected $3.95. Iterate freely. The narration
figure is measured, not modelled: it is what
`scripts/run_cs1_narration.py --reuse` actually billed.

## Working agreements observed

- Verify with real output before claiming anything. View images at full size.
- Read the provider's own docs before trusting the SDK's vocabulary. Both of
  today's most expensive mistakes were the SDK and GMI disagreeing about a name.
- Make the first paid call produce something needed anyway.
- Move Linear issues as work completes; attach evidence comments with real output.
- Corrections are stated plainly and the wrong version stays in the record — see
  design spec §6.3, `policy.yaml` POL-2 `changelog` and POL-5 `why_changed`.

## Open questions for Tarik

1. **GMI credit balance.** Asked three times, never answered. `estimate_cost()`
   returns `None`, so it can only come from the console. ~$4 spent of an assumed
   $25.
2. **Seedance 2.0 access.** Flaky at ~50%, not absent. Worth one email to
   [GMI support](https://www.gmicloud.ai/contact#sales) quoting a failing
   `request_id` and the 500/401 body — it looks like an upstream pool member
   without credentials. Not blocking; the primary chain works.
3. **Ring contraction doesn't read** across the six blocks even with per-block
   percentages. Cosmetic, $0.23 a round to iterate. Worth doing *after* an MP4
   exists.
4. **Voice cloning for the demo video only?** Your own voice would be strong for
   MOO-431's demo. It would be wrong for the product — a provenance tool whose
   narrator is a clone of a real person invites the question POL-1 forecloses.
5. **The two published windows disagree, and it is an editorial call.** POL-5
   admits 23-27 words; on this narrator that produced 9.25-12.56s across six
   blocks against a 9.0-10.5s take window. Three of six miss, all long, and no
   correction reaches them. Either widen `target_take_seconds` to ~9.0-12.5s and
   accept a ~65s piece, or narrow POL-5 to ~22-25 words and keep ~60s. The
   measurements and both options are in `voice.json` under
   `delivery.measured_2026_07_28_narration`.
6. **The ElevenLabs rate is a guess.** `eleven_v3` is registered at $0.22/1k
   characters — Creator tier, the most expensive plausible number, marked
   UNVERIFIED. The real figure is at
   https://elevenlabs.io/app/settings/billing.
7. **Two takes need a listen.** Back to back for the same voice, and one paced
   take to confirm the `[pause]` tag is not audible as a word. The instruments
   say silence; only ears close it.
