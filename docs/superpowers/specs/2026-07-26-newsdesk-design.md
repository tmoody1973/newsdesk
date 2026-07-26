# Newsdesk — Design Spec

**v1.0 · Jul 26, 2026 · Owner: Tarik Moody**
**Target: Backblaze Generative Media Hackathon · submit Aug 2 · deadline Aug 3, 5:00 PM EDT**

Companion to `newsdesk-prd.md` (requirements), `newsdesk-case-studies.md` (fixtures),
`newsdesk-ui-ux-spec.md` (screens). This document resolves the architecture, the craft
layer, and the build sequence those three left open.

---

## 1 · Context

Newsdesk turns verified facts into broadcast-style motion-graphics explainer videos,
with an editorial policy gate that rejects unethical generations before they are made,
a human approval gate before anything publishes, and a verifiable provenance receipt
embedded in every finished video.

**Constraints as of this document:**

- 8 calendar days remain (Jul 26 → Aug 2 submit). Zero code exists.
- Solo builder, ~8–10 hrs/day available (~65 hours).
- ~$25 generation budget.
- B2, GMI Cloud, ElevenLabs, and LMNT credentials are all provisioned.
- Local toolchain: `ffmpeg`, `uv`, `node`, `bun` present. Python pinned to **3.12**
  via uv (system 3.14 is ahead of provider wheel support).

**Judged criteria** (Devpost): Real-World Utility · Production Readiness ·
B2 Storage and Data Orchestration · Genblaze Usage.

---

## 2 · Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **CLI-first; web UI is a renderer** | Genblaze is Python-only. Building the governed pipeline as a CLI that emits run state to B2 proves the hard part by Day 4; the UI then reads that state. `newsdesk-ui-ux-spec.md §5` already assumed this. |
| D2 | **P1-1 (post-render vision check) is promoted to P0** | It is the strongest single evidence for both Genblaze Usage and Production Readiness. Built Day 5, while there is still room to cut something else instead. |
| D3 | **No database. B2 is the state store** | Fewer moving parts, and it converts the state layer into a fifth judged B2 use. |
| D4 | **Fly.io (Python) + Vercel (Next.js)** | Fly runs Docker with ffmpeg and tolerates 15-minute jobs. Vercel is the known surface for the frontend. |
| D5 | **Public demo mode + README access code** | Protects the ~$25 budget without gating the most important feature — policy refusals cost $0 and stay fully live to anonymous visitors. |
| D6 | **Import `vox-motion-graphics` craft wholesale** | The style tokens, block-prompt schema, NEGATIVE constant, script formula, and duration rules already exist and are field-tested. Newsdesk becomes the governed version of an existing working pipeline. |

---

## 3 · Architecture — three deterministic walls

The product thesis is "AI on a leash." The architecture is three walls the pipeline
cannot route around. Each is a pure function with **no provider access**, which is what
makes "zero policy-violating assets can reach publish" a structural claim rather than a
hopeful one.

| Wall | Enforces | Requirement |
|---|---|---|
| **1 · Facts** | Nothing enters the pipeline without a source | P0-1, P0-2 |
| **2 · Policy** | Nothing generates without passing the gate — rejection precedes any paid call | P0-3 |
| **3 · Approval** | Nothing assembles without a named human | P0-6 |

Because Wall 2 has no provider access, CS-4 (the red-team battery) runs fully offline
against a spend-counting fake provider and asserts a total of exactly `$0`.

---

## 4 · Repo layout

Monorepo, one git repo, two deployables.

```
newsdesk/
  README.md                    setup, architecture, judge access code, B2 use table
  policy/
    policy.yaml                POL-1..n — machine rules + plain-language names + "why"
  brand-kit/                   synced to b2://newsdesk-brand-kit
    style-key.png              generated once from the STYLE KEY prompt
    style-tokens.txt           verbatim from vox-motion-graphics
    block-template.txt         the 5-field block prompt schema
    negative.txt               the fixed NEGATIVE line (a policy constant)
    voice.json                 narrator voice_id + fallback voice_id
    subtitle.ass               Anton subtitle style
  api/                         python 3.12 · uv · Dockerfile w/ ffmpeg   -> fly.io
    pyproject.toml
    Dockerfile
    newsdesk/
      cli.py                   typer: run · approve · verify · seed
      server.py                FastAPI — thin, no logic, only CLI entrypoints
      state.py                 RunState <-> b2://newsdesk-runs/{run_id}/state.json
      facts.py                 P0-1 fact + source schema and validation
      script.py                P0-2 script generation + claim->fact validator
      blockprompt.py           parse / render / validate the 5-field template
      policy/
        gate.py                deterministic rules
        llm_check.py           genblaze chat() semantic check
        vision_check.py        post-render evaluation (P1-1, now P0)
      pipeline/
        blocks.py              Step: seedance-2.0 primary, fallback kling-i2v
        narration.py           ElevenLabs -> LMNT, take-duration verification
        loop.py                AgentLoop wiring, parent_run_id lineage
        assemble.py            ffmpeg stitch + subtitle burn + manifest embed
      audit.py                 ParquetSink -> b2://newsdesk-audit
    tests/
      fakes.py                 FakeProvider with a spend counter
      test_cs1.py … test_cs5.py
  web/                         next 15 · heroui pro                       -> vercel
    app/                       desk · wizard · run-board · review · receipt
    components/Stamp.tsx       four kinds only
  docs/superpowers/specs/      this document
```

---

## 5 · Data flow

```
facts + art direction
  └→ script.py ─ chat() ─→ claim→fact validator ──✗ BLOCK (P0-2)
       └→ 6 blocks (5-field prompt template)
            └→ Wall 2: gate.py → llm_check.py ──✗ BLOCKED stamp · $0 · audit row
                 └→ image step: i2i remix of the style key → styled still (§6.5)
                      └→ Step(seedance, first_frame=still, fallback_models=[kling])
                           └→ vision_check ──✗ AgentLoop retry, parent_run_id v1→v2
                           └→ narration(ElevenLabs → LMNT) → 9.0–10.5s verify → re-voice
                                └→ all 6 ready ═══ WALL 3: approve(name, timestamp) ═══
                                     └→ ffmpeg stitch + burn → manifest embed
                                          → genblaze verify → receipt
```

Every arrow that can fail writes exactly one audit row. The Run Board is that log rendered.

---

## 6 · The craft layer (imported from `vox-motion-graphics`)

The existing skill at `~/.claude/skills/vox-motion-graphics/` holds the production
knowledge the PRD referenced but never carried over. It is imported as first-class
artifacts, not rewritten.

### 6.1 Block prompt schema — the gate's data structure

Every block prompt is a five-field labeled document. **No free-form text ever reaches a
provider.** The gate parses this structure; it does not scan prose.

```
Block {N}
STYLE REFERENCE: Match the attached style key EXACTLY — {style-tokens.txt}
SCENE: {collage composition illustrating this block's narration line}
MOTION: {entrance choreography + camera move + what animates}
AUDIO: {ambient bed + 1–2 SFX — no voice, no narration}
NEGATIVE: {negative.txt, verbatim and unmodified}
```

`negative.txt` is a **policy constant**, not a prompt suggestion:

```
readable text, letters, words, numbers, captions, subtitles, watermark, logo,
photorealism, live-action footage, 3D render, lip-sync, talking characters, color drift
```

### 6.2 Script formula (P0-2 structure)

Six blocks, ~20–24 words each. Cold open (the surprising number, stated flat) → stakes →
two evidence beats, each anchored to a concrete fact → the turn → kicker that reframes
block 1. Numbers spelled out. Single flowing sentences preferred over choppy clauses.

### 6.3 Take-duration rule (origin of P0-5)

Target **9.0–10.5s** per take. The skill documents *why* this is unpredictable: narrator
voices pause ~0.7s at every period, so name-heavy choppy lines read ~1.8 words/s while a
flowing comma-joined sentence reads ~2.5 words/s — the same word count can vary by 4+
seconds. Overrun is corrected by raising speech rate or shortening the line; short takes
are worse than slight overruns because the assembler centers them and they read as desync.

### 6.4 Retry strategy (P1-1 / AgentLoop)

Verbatim from the skill's failure handling: on off-style output, **re-attach the style
key, tighten the STYLE and NEGATIVE lines, and re-run that block only.** Two identical
failures means the prompt is wrong, not the seed — stop and surface to the editor with
both takes and the drift note. This is the AgentLoop's tightening function and its
stop condition.

### 6.5 Style key discipline — resolved, and it changed the pipeline

**Resolved Jul 26 (MOO-415), from the installed registry source. No budget spent.**

The skill is emphatic that the style key must attach to **every single clip**, and that
framing and style do *not* reliably inherit (a documented real run with a 9:16 key still
produced 16:9 clips; aspect ratio must be passed explicitly on every call).

Moving that from Higgsfield to Genblaze/GMICloud does not survive contact:
**no GMI video model exposes a style-reference slot.** Every video family in
`genblaze_gmicloud/models/video.py` uses one of two image routings —

```
route_images(slots=("image",))                     pixverse · veo · kling · wan · fallback
route_images(slots=("first_frame", "last_frame"))  seedance
```

`route_images` supports an `array_slot="reference_images"`, but no family uses it.
Higgsfield's `medias:[{role:"image"}]` means *look like this*; Seedance's `first_frame`
means *start from this*. Passing the style key as `first_frame` would open all six
blocks on the same swatch — a different mechanism, not a smaller one. Kling does not
rescue it either; `slots=("image",)` is also a keyframe.

**Adopted: a two-step chain per block**, using `gmi-image-edit`
(`reve-remix-20250915`, `seededit-3-0-i2i-250628`) to carry the style:

```
style key (b2://newsdesk-brand-kit, public)
  └→ image step  — i2i remix into house style, per block  → styled still
       └→ video step — seedance, first_frame = that still → 10s clip
```

This is stronger than the Higgsfield arrangement, not a workaround: the clip *begins* on
a frame that is the style rather than being asked to resemble one. It also widens the
Genblaze surface materially — multi-step `Pipeline`, `input_from` fan-in, and two
modalities inside one run.

Three consequences worth carrying:

- Cost is ~2× calls per block. Images are the cheap half.
- The styled still doubles as the **Run Board thumbnail**, so the UI gets a real preview
  before the clip exists.
- On a policy or vision rejection, the still is the cheap thing to re-roll first — which
  makes the AgentLoop retry in §6.4 materially cheaper than regenerating video blind.

The brand-kit bucket is public specifically so the style key is fetchable by GMI.

### 6.6 Provider moderation is not a substitute for the gate

The skill records that moderation behaves differently per model — named politicians fail
on one engine and render on another. Newsdesk's position: **provider moderation is
inconsistent by model, which is precisely why POL-1 must be an owned pre-generation gate.**
This argument belongs in the README.

---

## 7 · Policy model

`policy/policy.yaml` holds numbered rules with a machine check, a plain-language name,
and a one-line "why." The Policy page renders it directly, so the file doubles as the
newsroom-standards artifact.

| Rule | Check | Layer |
|---|---|---|
| POL-1 | No real-person likeness — named individuals, or descriptions resolving to one | deterministic + LLM |
| POL-2 | NEGATIVE line present and byte-identical to `negative.txt` | deterministic |
| POL-3 | No fabricated news scenes; no photoreal style requests in STYLE/SCENE | deterministic + LLM |
| POL-4 | No readable text in SCENE; on-prop text must map to an entered fact | deterministic |
| POL-5 | Narration 20–24 words, estimated take ≤ 9.5s | deterministic |
| POL-6 | Post-render: output is not photoreal and not live-action | vision check |

Deterministic checks run first and are free. The LLM check (Genblaze `chat()`) runs only
on prompts that pass deterministically. **No paid generation call occurs until every
applicable rule passes.** Every evaluation — pass or fail — writes an audit row carrying
the rule ID, timestamp, and run ID.

Rejections are human-readable and cite the rule, because the gate's job is to teach the
boundary (CS-4/R5 proves a compliant retry succeeds), not to dead-end the journalist.

---

## 8 · State model and B2 layout

One `state.json` per run is the entire datastore. The CLI writes it, FastAPI appends
events, the web app polls it.

```
b2://newsdesk-runs/{run_id}/state.json
  run_id · parent_run_id · story · facts[] · script[] · art_direction
  blocks[6]: status · prompt · model · provider · attempts[] · policy_results[]
             · asset_uri · sha256 · narration{take_uri, duration_s, provider}
  events[]: ts · kind · rule_id · message
  approval: {approver, ts} | null
  final: {mp4_uri, manifest_uri, canonical_hash, verified} | null
```

**Five distinct B2 uses** (the judged criterion, counted explicitly in the README):

| Bucket | Contents |
|---|---|
| `newsdesk-assets` | Generated clips, audio takes, final MP4 — `KeyStrategy.HIERARCHICAL` |
| `newsdesk-brand-kit` | Style key, style tokens, block template, negative constant, voice config, subtitle style |
| `newsdesk-manifests` | Per-step Genblaze manifests plus the master manifest |
| `newsdesk-audit` | `ParquetSink` run tables — every generation, rejection, retry, approval |
| `newsdesk-runs` | Run state JSON — the application's only datastore |

---

## 9 · Genblaze surface

Every primitive below is load-bearing for the product, not added for rubric coverage.

- `Pipeline` / `Step` — multi-step generation, with `input_from` chaining the styled
  still into the video step (§6.5)
- `fallback_models=[...]` — on **both** video (seedance → kling-i2v) and audio
  (ElevenLabs → LMNT)
- `AgentLoop` with `parent_run_id` — policy-driven regeneration with queryable v1→v2 lineage
- `chat()` in three distinct roles — script generation, policy semantic check, vision evaluation
- `ObjectStorageSink` + `S3StorageBackend.for_backblaze` + `KeyStrategy.HIERARCHICAL`
- `ParquetSink` — the audit trail
- `EmbedPolicy` — redacted public receipt vs. full internal manifest
- Manifest embed into MP4 + `genblaze verify --fetch`
- Two modalities from one adapter — `GMICloudImageProvider` (style) and
  `GMICloudVideoProvider` (motion) — plus `genblaze-elevenlabs` and `genblaze-lmnt`

One caveat: `EmbedPolicy` is used from Day 4 to write the embedded manifest. The *dual
receipt* feature built on top of it (P1-3, redacted public vs. full internal) is on the
scope-cut ladder in §14; cutting it leaves `EmbedPolicy` in place with a single policy.

---

## 10 · Failure handling

| Failure | Behavior |
|---|---|
| Primary video provider returns MODEL_ERROR | `fallback_models` completes the block; the manifest records the **actual** provider, honestly |
| Both video providers fail | Block → `FAILED`, run pauses, UI offers retry. Never silently proceeds |
| Narration take outside 9.0–10.5s | Re-voice with rate adjustment, max 2 attempts, then flag for human |
| Vision check fails twice on the same block | Surface to the editor with both takes and the drift note — a human decides |
| `verify()` fails at assembly | Publish blocked. Red stamp: *"This file doesn't match its manifest. Don't publish it."* |
| Style key rejected by provider | Hard stop with a named error. Silent style drift is worse than a failed run |

Error copy is direct and never apologizes: *"Seedance didn't respond. Block 3 is retrying
on Kling."*

---

## 11 · Testing

The five case studies **are** the test suite. `pytest` runs against `FakeProvider` for
everything except one real end-to-end run per day.

| Fixture | Type | Asserts |
|---|---|---|
| CS-4 red-team | Unit, **offline** | R1–R4 rejected with rule citations; spend counter reads exactly `$0`; R5 compliant retry passes |
| CS-2 vinyl | Integration | Full 6-block run; cold-start completion from README alone; `authentic: true` on the uploaded asset |
| CS-1 public radio | End-to-end | All 6 claims trace to F1–F6; `genblaze verify` passes on the final MP4 |
| CS-3 property tax | Traceability | Every claim maps to a Budget Commons row ID; the unsourced claim is blocked |
| CS-5 chaos | Resilience | Blocks 3–4 complete via fallback with zero manual intervention; manifest shows mixed lineage |

CS-5 is driven by environment-variable sabotage (invalid model ID / revoked key), so it
runs from a shell script and is reproducible by a judge.

---

## 12 · Web application

Per `newsdesk-ui-ux-spec.md`. The frontend is a **renderer over `state.json`** — no
pipeline logic crosses into Next.js.

**Build order** (highest demo value first): Run Board → Editor Review → Receipt →
Desk → Wizard. The `<Stamp>` component ships with the Run Board and has exactly four
kinds: `APPROVED`, `BLOCKED`, `RETRY n`, `VERIFIED`.

Approval identity is a name entered at approval time and recorded in the manifest. No
Clerk, no multi-tenant auth — consistent with PRD non-goals, and honest about it in the README.

---

## 13 · Deployment and judge access

**Fly.io** runs the Python service from a Docker image with ffmpeg and genblaze, on a
persistent volume for scratch space. **Vercel** runs Next.js. No database.

Judge access is two-tier:

| Tier | Available |
|---|---|
| **Public, no code** | Browse completed CS-1 / CS-2 runs with real B2 state and real manifests; open the lineage drawer and receipt; run `genblaze verify`; **run the CS-4 red-team battery live** — refusals never call a provider, so this costs `$0` |
| **README access code** | Full live generation, hard-capped at 2 runs per code |

The most important feature — refusal — is never gated.

---

## 14 · Schedule

| Day | Deliverable |
|---|---|
| **0** · Jul 26 (tonight) | Repo init, uv/3.12, genblaze installed, quickstart smoke test against B2 + GMI. **Resolve §15 blockers.** |
| **1** · Jul 27 | P0-1 facts, P0-2 script + claim validator, `policy.yaml`, deterministic gate, `blockprompt.py`, CLI `run`, state in B2 |
| **2** · Jul 28 | POL LLM check, P0-4 block pipeline + fallback chain, brand kit to B2, first real render |
| **3** · Jul 29 | P0-5 narration + duration verify, Parquet audit, all five buckets live |
| **4** · Jul 30 | **⬛ CHECKPOINT: full CS-1 six-block run, CLI end-to-end.** P0-6 approval, P0-7 assemble + embed + verify. CS-4 green |
| **5** · Jul 31 | Vision evaluation in AgentLoop (D2), CS-5 chaos run, P1-2 authentic upload |
| **6** · Aug 1 | Web: Run Board, Editor Review, Receipt, `<Stamp>` |
| **7** · Aug 2 | AM: Desk, wizard, deploy both, access code, README. PM: demo video, **submit** |

**Aug 3 is buffer, not a workday.**

**Scope-cut ladder** — named now so it is not negotiated under pressure. Cut strictly in
this order: Desk list screen → wizard Step 2 art-direction cards (fall back to a JSON
fixture) → P1-2 upload → P1-3 dual receipts → P1-4 per-block reject. The vision check
(D2) is **not** on this ladder.

**Floor:** if the web app cannot ship, the Python service serves the Receipt page directly
and the demo video carries the UX story.

---

## 15 · Day 0 blockers

1. ~~**Does GMI's Seedance endpoint accept an image/style reference through Genblaze
   `Step` params?**~~ **Answered Jul 26 — no.** No GMI video model exposes a
   style-reference slot; only keyframe slots exist. Resolved by adopting the two-step
   image→video chain in §6.5. Settled from registry source at $0.
2. **What is the `abatch_run()` concurrency ceiling on GMI?** Determines whether six
   blocks run parallel or sequential, which sets the wall-clock target for a run. Now
   slightly more consequential: the two-step chain means 12 calls per story rather
   than 6.

Answers are recorded in the README architecture section either way — a documented
limitation is production-readiness evidence, not a weakness.

**Also resolved Jul 26 (MOO-417, MOO-432), out of band:**

- `ParquetSink` is exported by `genblaze_core` but raises without the optional `pyarrow`
  dependency. Added.
- `ObjectStorageSink.write_run()` re-fetches each asset by URL to transfer it, so an
  asset already sitting in a private bucket 401s. Correct behavior for real provider
  outputs; only affects contrived cases.
- `ObjectStorageSink` **rejects** `URLPolicy.PRESIGNED` deliberately — *"manifests
  outlive presigned SigV4 URLs, so persisting them breaks provenance."* This is the same
  principle the product is built on, so the assets and brand-kit buckets are public
  rather than presigned.
- B2 refuses to create public buckets until an account has payment history. Cleared.

---

## 16 · Out of scope

Photorealistic output of any kind (permanent, not a v1 limitation) · fully automated
publishing · breaking-news speed · multi-tenant auth and roles · custom style authoring UI ·
C2PA signing · multi-style brand kits · RSS and social publishing targets ·
a `genblaze-higgsfield` adapter.
