# Handoff — Newsdesk, end of Day 0/1

**Repo:** `/Users/tarikmoody/Documents/Projects/newsdesk`
**Linear:** [Newsdesk — Backblaze Generative Media Hackathon](https://linear.app/moodyco/project/newsdesk-backblaze-generative-media-hackathon-5f68ce40d2cc) · team `MOO`
**Deadline:** submit **Aug 2**, hard cut **Aug 3, 5:00 PM EDT**
**Spend:** ~$0.80 of a ~$25 generation budget

## Where to read first

Don't re-derive any of this — it's all written down:

| What | Where |
|---|---|
| Architecture, decisions, budget, day plan | `docs/superpowers/specs/2026-07-26-newsdesk-design.md` |
| Requirements (P0-1…P0-9) | `newsdesk-prd.md` |
| Fixtures CS-1…CS-5 (they *are* the test suite) | `newsdesk-case-studies.md` |
| Screens, stamp system, tokens | `newsdesk-ui-ux-spec.md` |
| Editorial rules POL-1…POL-6, with thresholds and reasoning | `policy/policy.yaml` |
| Why text bleeds into frames and how to prompt around it | `brand-kit/scene-guidance.txt` |
| Narrator choice + measured pacing data | `brand-kit/voice.json` |
| Art-direction menu (framing language per option) | `brand-kit/through-lines.yaml` |

Every Linear issue carries Intent / Acceptance / Verification, and the closed ones have
evidence comments with real output. **Read the issue before building it** — several were
rewritten mid-session when testing killed an assumption.

## Status

**Done:** MOO-415, 416, 417, 418, 420, 421, 422, 432, 433 — plus MOO-425 partially.
**Open:** MOO-419, 423, 424, 425, 426, 427, 428, 429, 430, 431.

Days 0 and 1 complete, roughly one day ahead — but the day gained is the *predictable*
half. Nothing has generated a video yet; narration timing, ffmpeg assembly, manifest
embed and `verify` are all untouched.

The governance core is done and tested offline: both walls, the decision ledger, the
prompt schema. `uv run pytest tests/ -q` → **17 passed**, zero network, `$0` asserted.
**CS-4 (the refusal demo) already works before any video exists.**

## Immediate next work

### MOO-425 — finish the brand kit (in progress, ~$0)

Done: `negative.txt`, `style-tokens.txt`, `scene-guidance.txt`, `through-lines.yaml`,
`voice.json`.

Remaining, per the issue's rewritten acceptance criteria:
- `brand-kit/subtitle.ass` — Anton, matching the burned-subtitle look and the app's stamps
- `brand-kit/style-key.png` — pick the best of six candidates already in
  `b2://newsdesk-brand-kit/style-key-candidates/`. **Documentation only, not a pipeline
  input** (see "Assumptions that died" below)
- `newsdesk/brandkit.py` — load the kit **from B2 at runtime**, and fail loudly on a
  missing kit rather than falling back to defaults
- `scripts/sync_brand_kit.py` — idempotent push of the local kit to B2

### MOO-419 — script generation + claim→fact validator

First real `chat()` call. Text-only, so cents. Completes facts → script → gate end to end,
which is the first genuinely demoable path.

**Must route through `newsdesk/decisions.py::judged()`** — see MOO-433 below. That's the
whole reason this issue was sequenced after the ledger.

Script shape is imported, not invented: `brand-kit/` + design spec §6.2. Note POL-5 now
wants **23–27 words across 2–3 sentences**, not the vox skill's 20–24 in one sentence.

## Assumptions that died this session — do not resurrect them

Each cost real money to disprove. The Linear comments have the evidence.

1. **Seedance has no style-reference slot.** Every GMI video family routes images to
   keyframe slots only (`first_frame`/`last_frame`, or `image`). Kling doesn't rescue it.
   *(MOO-415)*
2. **Passing a style key as an image input makes consistency worse.** Two scenes off one
   key produced a solid-blue ground and a warm-tan ground. **Naming the palette explicitly
   in text locked it.** So: no i2i step, one image call per block, style lives in
   `style-tokens.txt`. *(MOO-424)*
3. **`seedream-5.0-lite` silently ignores `aspect_ratio`.** Returns 2048×2048 regardless.
   **`gemini-2.5-flash-image` honours it** (768×1344). That's the image model.
4. **Negation phrasing is not what drives text bleed — framing is.** "archival photo
   cutout of a radio dial" → numerals legible at normal size. "dial face of matte cream
   card" → clean. Same prompt otherwise, no negation in either. An earlier hypothesis
   about negation mechanics was tested and **refuted**; `scene-guidance.txt` records the
   refutation deliberately.
5. **The vox skill's pacing rule is backwards for our voice.** It says prefer one flowing
   sentence; four measured takes show flowing lines run *short* and sentence-end pauses
   fill the window. *(POL-5 recalibrated — `policy.yaml` has the numbers)*
6. **`chat()` is not a Pipeline citizen** — it cannot ride `.step()` and produces no
   manifest. Since all three of our `chat()` uses are governance, the decisions would have
   been the only unrecorded part of a provenance product. `newsdesk/decisions.py` fixes
   this: decisions are hashed into a ledger whose digest enters the master manifest.
   *(MOO-433)*

## Gotchas that will bite

- **`ParquetSink` needs `pyarrow`** — exported in `__all__` but raises without it. Already
  added; don't remove it.
- **Direct ElevenLabs wants `eleven_v3`**, not the GMI slug `ElevenLabs-TTS-v3`. Which
  means the ElevenLabs rate in `newsdesk/pricing.py` is the *GMI* rate and doesn't apply
  to the direct path. **Unresolved — worth fixing before MOO-426.**
- **`asset.duration` is `None`** from the ElevenLabs adapter. Take length must be measured
  with `ffprobe`.
- **`ObjectStorageSink.write_run()` re-fetches assets by URL**, so it 401s on a private
  bucket. Fine for real provider outputs; bit the smoke test.
- **`ObjectStorageSink` rejects `URLPolicy.PRESIGNED` by design** — "manifests outlive
  presigned URLs". Hence public `assets` and `brand-kit` buckets.
- **B2 bucket creation needs an all-buckets key**; a bucket-scoped one fails even with
  `writeBuckets`.
- **Cost is not reported by GMI.** `newsdesk/pricing.py` registers rates so `cost_usd`
  populates. Rates are a 2026-05-04 snapshot — contract-specific, verify against console.
- **Budget lever:** `seedance-1-0-pro-fast` is **$0.022/asset** vs seedance-2.0's
  **$0.52** for a 10s clip. Iterate on pro-fast; spend on 2.0 only for the hero run and
  the demo video. Full story ≈ $3.95 on 2.0, $0.94 on pro-fast.
- **`gate.py` must never import anything network-capable.** `tests/test_structure.py`
  walks its import graph and fails the build. Don't "fix" that test.
- **Keep the CS-2 false-positive control.** It caught a gate bug on first run that would
  have blocked 100% of legitimate blocks while citing a real rule.

## Working agreements observed this session

- Verify with real output before claiming anything. View images at zoom rather than
  trusting a thumbnail — that caught two things a downsampled view missed.
- Read the SDK source / docs before spending. MOO-415 was answered for **$0** from the
  installed registry.
- Make the first paid call produce something needed anyway — the concurrency spike also
  produced the style-key candidates.
- Move Linear issues to Done **as work completes**; the board drifted once this session.
- Corrections are stated plainly and the wrong version is left in the record (see
  `scene-guidance.txt`).

## Suggested skills for the next session

- **`find-docs`** (context7) — before any SDK/API assumption. Settled the Gemini
  negative-prompt question authoritatively.
- **`superpowers:test-driven-development`** — MOO-419's validator is exactly the shape
  (fixtures exist as CS-1/CS-3).
- **`linear-build`** — already in use; keep the issue-as-contract loop.
- Not needed: brainstorming (design is settled and committed), writing-plans (the board
  is the plan).

## Open questions for Tarik

1. **Listen to `scratchpad/narrator_sample.mp3`** before six blocks get built on Marcus
   Louis. Voice is a brand call, not a technical one.
2. **GMI credit balance** — asked twice, never answered. It's the real budget ceiling and
   `estimate_cost()` returns `None`, so it can only come from the console.
3. **Direct-ElevenLabs vs via-GMI for TTS.** Direct gives two distinct provider adapters
   (better for the Genblaze Usage criterion) but sits outside the registered pricing.
