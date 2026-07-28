# Newsdesk

**Governed generative video for newsrooms.** A journalist enters verified facts
and their sources; Newsdesk returns a sixty-second explainer video with an
editorial policy gate in front of it, a named human approval in the middle of
it, and a provenance record embedded in the file itself.

Built for the [Backblaze Generative Media Hackathon](https://www.backblaze.com/)
on [Genblaze](https://github.com/backblaze-labs/genblaze) and Backblaze B2.

> Its most important feature is what it refuses to make.

---

## Why

Generative video crossed the broadcast quality threshold while newsroom trust in
AI fell through the floor. That leaves small newsrooms with a false choice: ban
the tools, or use them ungoverned. Newsdesk is the third option — the tools, on a
leash, with receipts.

The leash is not a prompt asking a model to behave. It is three deterministic
walls the pipeline cannot route around:

| Wall | What it stops | How it is enforced |
|---|---|---|
| **1 — Facts** | A claim with no source | `facts.py` refuses to validate a story where any fact lacks a citation. Nothing reaches a paid call before this passes. |
| **2 — Policy** | A prompt that violates editorial standards | `policy/gate.py` checks every block prompt against `policy/policy.yaml` **before generation**, so a rejected prompt costs $0. |
| **3 — Approval** | Publication without a human | `state.py` exposes assembly only through an `approve()` transition. There is no other path, and the approver's name lands in the manifest. |

Wall 2 is enforced by a test, not by discipline. `tests/test_structure.py` walks
the gate's transitive import graph and fails the build if anything
network-capable appears in it — so "zero paid API calls on a blocked prompt" is a
structural property rather than a promise.

---

## The editorial policy

`policy/policy.yaml` is the standards desk, in a file, versioned, with its
reasoning and its changelog attached to each rule.

| Rule | |
|---|---|
| **POL-1** | No real-person likenesses |
| **POL-2** | The exclusion line is fixed — the prompt's negative clause is byte-compared against the published brand kit |
| **POL-3** | No fabricated news scenes |
| **POL-4** | No readable text on screen, beyond a bounded on-prop question |
| **POL-5** | Narration fits its block |
| **POL-6** | Output is checked, not just the request |

Rules carry `why_changed` and `changelog` fields. When testing kills an
assumption, the wrong version stays in the record next to the right one.

---

## Pipeline

```
facts ──▶ script ──▶ policy gate ──▶ blocks ──▶ narration ──▶ approval ──▶ assembly
 │          │            │             │            │            │            │
 │          │            │             │            │            │            └─ ffmpeg + embedded manifest
 │          │            │             │            │            └─ named human, recorded
 │          │            │             │            └─ ElevenLabs ─▶ LMNT
 │          │            │             └─ gemini-2.5-flash-image ─▶ seedance ─▶ kling
 │          │            └─ deterministic, $0, cannot reach a provider
 │          └─ every claim traced to a fact, verbatim
 └─ every fact carries a source
```

Six blocks, one per beat: cold open, stakes, evidence, evidence, turn, kicker.

**Fallback chains are walked by this application, not by the SDK.** Genblaze's
`fallback_models` fires only on `MODEL_ERROR`, a branch its classifier reaches
only for "not found" / "not available" and only after auth and server checks have
claimed anything containing 401, 403, 400 or 5xx. GMI says "model X does not
exist" over HTTP 404, which lands in `UNKNOWN` — so the chain never engages.
Measured, not assumed. `blocks.run_block` and `narration.run_take` each walk the
chain themselves, with a same-model retry first, because a transient 401 clears
about half the time and answering it with a provider switch abandons a working
model and bills the fallback's higher rate.

Every substitution is disclosed. The manifest records the model that *ran*, not
the one that was asked first.

---

## Backblaze B2

Five distinct uses, one per data class:

| Bucket | Visibility | What lives there |
|---|---|---|
| `newsdesk-assets` | public | stills, clips, narration takes, the final MP4 — public because the receipt tells a fact-checker to verify the file themselves |
| `newsdesk-brand-kit` | public | the published house style; a run styled by an unpublished kit is refused outright |
| `newsdesk-manifests` | private | per-run provenance |
| `newsdesk-audit` | private | Parquet tables of every generation and every refusal, in one queryable shape |
| `newsdesk-runs` | private | run state — the application's only datastore. No database. |

The brand kit is loaded from B2 at runtime and **never falls back to a local
default**. A run that quietly used an unpublished style is worse than a run that
did not happen: the video ships, the receipt claims it followed the brand kit,
and nothing in the record shows it didn't.

---

## Measured cost

Real numbers from real runs, not estimates.

| | Rate | Six-block story |
|---|---|---|
| `gemini-2.5-flash-image` | $0.039 / asset | $0.23 |
| `seedance-1-0-pro-fast-251015` | $0.022 / asset | $0.13 |
| `kling-image2video-v2.1-master` (fallback) | $0.28 / asset | $1.68 |
| `eleven_v3` direct | $0.22 / 1k chars *(unverified)* | $0.26 |
| `lmnt` direct (fallback) | $0.15 / 1k chars | $0.15 |

**A full story on the primary chain is $1.23**, against the design's projected
$3.95. No model is left unpriced — an unpriced model reports `cost_usd = None`
and the run looks free, which happened twice during the build and is why
`pricing.py` carries an explicitly-labelled UNVERIFIED rate rather than a blank.

---

## Case studies

The five fixtures in [`newsdesk-case-studies.md`](newsdesk-case-studies.md) *are*
the test suite.

| | Story | What it proves |
|---|---|---|
| **CS-1** | Who pays when public radio goes dark? | The flagship happy path, plus the rejection beat |
| **CS-2** | Vinyl now outsells CDs three to one | Cold-start, zero policy landmines — the **false-positive control**. If CS-2 trips a gate, the gate is miscalibrated. |
| **CS-3** | Where does your Milwaukee property-tax dollar go? | Source traceability against structured data |
| **CS-4** | Election-night red team | **Must not produce a video.** 100% of probes rejected, $0 spent, every refusal human-readable |
| **CS-5** | Resilience run | Sabotaged providers; the run finishes on the fallback and the manifest says so |

---

## Running it

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), and `ffmpeg` /
`ffprobe` on PATH.

```bash
cd api
cp .env.example .env          # B2, GMI, ElevenLabs, LMNT keys
uv sync
uv run pytest tests/ -q       # 209 passed — zero network, $0
```

The whole suite runs offline and costs nothing. Provider calls are injected, and
the audio fixtures are generated by ffmpeg at test time rather than committed, so
the silence-trim assertions run against real waveforms.

Paid runs are separate and each one names its cost:

```bash
uv run python scripts/verify_brand_kit.py              # $0
uv run python scripts/run_cs1_script.py                # cents — text only
uv run python scripts/run_cs1_blocks.py --stills-only  # ~$0.23
uv run python scripts/run_cs1_narration.py             # ~$0.26
uv run python scripts/run_cs1_narration.py --sabotage  # CS-5's TTS leg
uv run python scripts/run_cs5_sabotage.py              # CS-5's video leg
```

---

## Status

Facts, script, policy gate, blocks and narration run end to end and are verified
against real output. Assembly is the remaining piece. Current state, open
questions and the list of assumptions that died under testing are in
[`docs/HANDOFF.md`](docs/HANDOFF.md) — read it before changing anything, because
several of those assumptions were expensive.

## Documents

| | |
|---|---|
| [`newsdesk-prd.md`](newsdesk-prd.md) | Brief, requirements P0-1…P0-9, non-goals |
| [`newsdesk-case-studies.md`](newsdesk-case-studies.md) | The five fixtures |
| [`newsdesk-ui-ux-spec.md`](newsdesk-ui-ux-spec.md) | Screens, stamp system, tokens |
| [`policy/policy.yaml`](policy/policy.yaml) | POL-1…POL-6 with reasoning and changelog |
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | Where the work stands |

## License

MIT — see [LICENSE](LICENSE).

Newsdesk is a personal project. It is not a publication of, nor a communication
from, any newsroom or public body referenced in its fixtures.
