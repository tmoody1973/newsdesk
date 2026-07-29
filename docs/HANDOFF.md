# Handoff — Newsdesk, end of Day 4 (2026-07-28)

**Repo:** `/Users/tarikmoody/Documents/Projects/newsdesk` · public at
[github.com/tmoody1973/newsdesk](https://github.com/tmoody1973/newsdesk), `main`
**Linear:** [Newsdesk — Backblaze Generative Media Hackathon](https://linear.app/moodyco/project/newsdesk-backblaze-generative-media-hackathon-5f68ce40d2cc) · team `MOO`
**Deadline:** submit **Aug 2**, hard cut **Aug 3, 5:00 PM EDT** — four days left
**Tests:** `cd api && uv run pytest tests/ -q` → **318 passed**, zero network, $0
**Spend:** ~$10 of ~$25 · ~$15 left, roughly twelve more stories

---

# ⛔ THE MANDATE — unchanged

**Build the full product. A visitor must be able to create a video.**

> *"People should be able to create a video, stop being god damn lazy. I want to
> win this hackathon. You don't win for being lazy."* — Tarik, 2026-07-28

**No scope cuts without saying the word "cut" out loud** and naming the criterion
dropped. **Read the sources before you build** — see `CLAUDE.md`, which names the
file to open for each kind of work. **Verify with your eyes and ears**: view
images at full size, listen, screenshot the page. Nearly every defect found on
Day 4 was invisible to tests and obvious in one frame.

---

## What exists now

A story becomes a receipted video through **one command or one browser**:

```bash
cd api
uv run python -m newsdesk ../stories/cs2.yaml --only gate      # $0, no credentials
uv run python -m newsdesk ../stories/cs2.yaml                  # all five stages
```

Five stages, resumable and individually addressable:
**script → gate → blocks → narration → assembly**

| Layer | Where |
|---|---|
| Orchestrator | `api/newsdesk/pipeline.py`, CLI in `cli.py` |
| Story as data | `api/newsdesk/storyfile.py`, files in `stories/*.yaml` |
| Worker (HTTP) | `api/newsdesk/server.py`, `api/Dockerfile`, `api/fly.toml` |
| Web | `web/` — Desk, 3-step wizard, Run Board, Editor Review, Receipt |

### Proven on Day 4

- **CS-2 became a real video** — 68.95s, −16.0 LUFS, `genblaze verify` exit 0.
- **A video was published from the browser** — Editor Review → stamp → assembly
  → published, and the manifest carries the name typed into the browser.
- **The container was built and a caption burned inside it**, and the frame was
  looked at. Anton renders; it is not a fallback face.

### Proven on Day 5 — the gap is closed

**A story went browser-start to browser-finish.** No CLI command touched the
run. `what-a-billion-dollars-of-vinyl-says-abo`: five facts typed into the
wizard, `record` picked from the menu, script written and repaired three times
until every claim traced, gate passed at $0, six clips, six takes, six per-block
approvals, stamped on Editor Review, published.

- **69.80s · −16.0 LUFS · −1.8 dBTP · 1080×1920 h264+aac · 75 MB**
- **$1.2116** — $0.936 pictures, $0.276 voice — against the $1.20 estimate
- Two frames pulled at 6s and 42s and looked at. Anton renders as Anton.

The demo now exists as a thing that happened, not a thing that should work.

---

## Run state in B2, right now

| run | status | note |
|---|---|---|
| `cs1-narration` | published | the legacy CS-1 video. Approver is a placeholder. |
| `cs2` | drafting | **fresh script, 6/6 traced.** Old clips in B2 no longer match these lines. |
| `cs1` | drafting | 0 blocks — script did not converge. See RISK below. |
| `vinyl-outsold-cds-three-to-one` | drafting | the browser-typed story, script only |

**Both published videos carry the approver string
`"Claude (agent) — UNREVIEWED, pending Tarik Moody"`** in their embedded
manifests. That is deliberate — an agent must not sign a human's name to a
provenance record. Tarik re-stamps them on Editor Review; it re-cuts at $0.

---

## ⚠️ RISK — read before planning

**Script generation is now materially harder and can fail outright.**

Day 4 added a rule: every block except the kicker must trace to a fact. It is
the right rule (see below), but it stacks on top of an already tight set —
23–27 words, 2–3 sentences, whole-assertion mapping, every fact used.

- CS-2 converges.
- **CS-1 did not converge on its last attempt** — one block at 29 words after
  six repair rounds.

If this bites before the deadline, **the lever is `MAX_ATTEMPTS` (currently 6) or
the POL-5 word window — not the tracing rule.** The tracing rule is the product's
whole argument. Widening the window is a calibration; dropping the rule is a cut.

---

## Build order from here

### ~~1. One story, browser start to finish~~ · **DONE, Day 5, $1.2116**

```bash
cd api && uv run python -m newsdesk.server   # reads NEWSDESK_ACCESS_CODE from api/.env
cd web && npm run dev                        # needs NEXT_PUBLIC_WORKER_URL=http://localhost:8080
```

### ~~2. Deploy · Fly (worker) + Vercel (web)~~ · **LIVE, Day 5**

| | |
|---|---|
| **Site** | **https://newsdesk-rosy.vercel.app** — public, 200 |
| **Worker** | **https://newsdesk-worker.fly.dev** — 2 machines in `ord`, checks passing |

`vercel --prod` from the **repo root**. `fly deploy` from `api/`. Both projects
are already linked and their secrets are set — 7 on Fly, 4 on Vercel.

**Three things about this deploy that will bite whoever touches it next:**

1. **The Vercel Root Directory is `web`, and the whole repo is uploaded.**
   `web/app/policy/page.tsx` reads `process.cwd()/../policy/policy.yaml` and
   `next.config.mjs` traces from the repo root — both deliberate, so the Policy
   page cannot drift from the file the gate enforces. Deploying `web/` alone
   fails with a doubled `path0/path0` output path. Root Directory is a project
   setting, not expressible in `vercel.json`; it was set with
   `PATCH /v9/projects/{id}`. `.vercelignore` keeps `policy/` and drops the rest.
2. **Vercel refuses to deploy a vulnerable Next.** 15.5.4 was blocked *after a
   clean build*. Pinned to **15.5.22**. Delete `.next` after any Next bump or the
   next build dies on `Cannot find module for page: /_not-found`.
3. **This Mac's resolver has a stale NXDOMAIN for `newsdesk-worker.fly.dev`.**
   `dig` is correct, `curl` is not — use `--resolve …:443:66.241.125.20` from the
   shell. Chrome resolves it fine, so it is a local cache, not a deploy problem.

**Proven against the live URLs, from the deployed origin:**

- `POST /runs` with no code → **401**; with a wrong code → **401**
- `POST /runs` with the right code and an unsourced fact → **422**, *"has no
  sources. Every fact needs at least one."* Wall 1 holds in production, and no
  run was created, so this probe left nothing on the Desk.
- `fetch()` from `https://newsdesk-rosy.vercel.app` to the worker's `/health` →
  **200** with `access_code_required: true`. CORS and DNS both work browser-side.
- Policy, Desk and Receipt all render — the Desk reads the **private** runs
  bucket server-side, so the B2 keys on Vercel are good.

**A paid run went end-to-end on the deployed worker.**
`who-pays-when-the-signal-goes-quiet` — the CPB rescission, six facts typed into
the deployed wizard, `tower-signal`, **$1.2251**, published from Fly at
**71.47s / −16.0 LUFS / −3.0 dBTP**, 1080×1920. GMI, ElevenLabs and B2 all
reachable from `ord`. Frames pulled at 8s and 55s and looked at: the tower holds
across six independent renders, rings contract, Anton captions burned in.

### Three ways the container is not your Mac

All three found by running a real story against the deployed worker, all three
**failed closed** — which is why they cost cents rather than a wrong video.

1. **`gate.py` resolved `/policy/policy.yaml`.** `parents[3]` is right in the
   repo and one level too deep in the container, where `newsdesk/` sits directly
   under `/app`. Now searches upward.
2. **`blockprompt.py` resolved `/brand-kit/style-tokens.txt`** — identical fault,
   `parents[2]`, one directory over. Also searches upward. Both files also had to
   be **copied into the image**: Wall 2 must work with no credentials at all, so
   the gate cannot wait on a B2 sync of the kit.
3. **Debian bookworm ships ffmpeg 5.1, whose `ebur128` rejects `framelog`.** The
   filter failed to initialise, the summary read `0.0 LUFS` / `-inf dBFS`, and
   `master()` refused to guess a gain. Option dropped; `parse_ebur128` now reads
   the **last** `I:` in the log, because without `framelog=quiet` every frame
   prints a running one and the first is 0.4s in and wrong by ~14 dB.

The lesson is cheap and repeatable: **run the gate stage inside the built image
before deploying.** `docker run --rm --env-file ./api/.env -v "$PWD/stories:/app/stories:ro"
<image> python -m newsdesk /app/stories/cs1.yaml --only gate` costs $0 and would
have caught the first two. It does not catch the third — a full assembly under
Docker Desktop on an ARM Mac ran past ten minutes and had to be abandoned.

### Known, not fixed

- **A run that ever errored cannot be retried from the wizard.** `lastError`
  scans the whole event history and `waitFor` returns on any error event, so the
  journalist is shown a previous attempt's failure. A refused script is a
  *normal* outcome here, so this breaks the loop the product is built around.
- **Per-block approvals are not persisted** — re-opening Editor Review resets all
  six to pending. Already on the "if time allows" list; confirmed in production.
- **`POST /runs` with `assembly` demands an `approver`** even when the run is
  already approved in B2, and re-stamping writes a new timestamp over the
  original approval time.

### 3. README, demo video, submit

The demo now has something real to record: a story typed into a browser becoming
a receipted video.

### 4. If time allows

CS-1 convergence · per-block approvals persisted · "Reject with note" · the
lineage drawer · URL ingest (designed in `docs/PLAN.md` §B4, unbuilt).

---

## Day 5 — four defects the browser found that the tests could not

Every one was invisible to 318 passing tests and obvious on a screen.

1. **A blank `+ citation` row counted as a source.** `factProblem` tested
   `sources.length === 0` and never the value, so an empty box turned the fact
   green and the ledger read *"1 of 1 sourced"* over nothing. The backend does
   refuse `{citation: ""}` — its `present` check is truthiness — so this was a
   round trip, not a hole. Fixed with `filledSources`.
2. **`slugify` cut the run id mid-word.** This story's id is
   `what-a-billion-dollars-of-vinyl-says-abo`, and that fragment is printed on
   the receipt and is the B2 prefix. Now cuts back to a whole word. Existing
   runs keep their stored ids; only new stories change.
3. **The receipt told every reader to verify `cs1.mp4`.** Hardcoded. The one
   instruction on the page whose whole point is *"do not trust our website"*
   was the one thing on it that was wrong. Now reads the run's own filename.
4. **"Made by" named only ElevenLabs** on a run whose six clips were seedance,
   because `stage_narration` **replaces** a block's `attempts` tuple and
   `stage_blocks` never writes one. The receipt now reads the event log, which
   is the audit trail and carries the model that ran on every stage.

**Still open, both in `pipeline.py`:** `stage_narration` overwriting `attempts`
is unfixed — #4 routes around it rather than repairing it. And the still's model
(`gemini-3-pro-image-preview`) is **never logged at all** — only `video_model`
reaches the record, so no receipt can name the model that made the picture.

## What changed on Day 4, and why

### The pictures stopped being bland

`IMAGE_MODEL` was `gemini-2.5-flash-image`, which had been **down for a day** —
runs were driven by an inline env var, so the committed default rendered 0/6 from
a fresh clone. Moved to **`gemini-3-pro-image-preview` (Nano Banana Pro)**:
768×1376 true 9:16, against bria-fibo's 576×1024. First roll where the map motif
rendered as an actual map and the crowd motif as archival cutouts.

The ring defect is fixed: `countable` is **6→1**, not the 5→2 the last handoff
proposed, because six blocks need six *distinct* counts. Arrangement is stated
positively — "concentric", "nested one inside the next", "common centre".

### Claims now trace assertions, not only numbers

The validator used to check that every **number** traced to a fact. The first
story through the new orchestrator produced:

> *"Vinyl revenue hit one point zero four billion dollars. For the first time
> since nineteen eighty-three, records outsold every other physical format
> combined."*

Both numbers traced perfectly. *"Records outsold every other physical format
combined"* is in none of the five facts, and nothing objected.

The rule is **sentence-scoped**: a sentence with no claim is framing and the
human at Wall 3 owns it; a sentence carrying a traced claim is presenting itself
as reporting, so everything else in it must trace too. Whole-line coverage was
tried first and was wrong — it flagged the CS-1 kicker and emitted shards like
"already" and "took". `test_prose_without_numbers_needs_no_claim` had the answer
in its docstring: *a validator that fires on everything gets switched off.*

Then the generator found the escape hatch on its own — a block with **no claims
at all** passes, because every sentence reads as framing. So: **every block
except the kicker must trace.** Scoped by role, not position.

### Six bugs, every one found by looking at real output

1. `IMAGE_MODEL` default was a dead model — 0/6 from a fresh clone.
2. The image leg had **no retry**; one transient timeout failed a block at $0.
   `run_still()` now walks the same chain `run_block` always did.
3. Assembly picked clips by **sort order across runs** — the tiebreaker was a
   random UUID. A re-render could cost a dollar and ship the *old* video, and
   the receipt's lineage could come from a `--stills-only` run.
4. The assembly stage saved the approval to B2, then the pipeline wrote its
   **stale in-memory copy over the top** — erasing Wall 3's record seconds
   after it was made.
5. `stage_blocks` recorded cost and status and **threw away `still_uri` /
   `clip_uri`**, so every screen that shows a frame rendered grey rectangles.
6. `--only script` **saved nothing** — printed "ok script 6 blocks" and
   discarded them, because the save was gated on B2 creds being in the stage
   list and `script` only needs `GMI_API_KEY`.

---

## Assumptions that died — do not resurrect

Carried forward from Day 3 and still true: seedance has no style-reference slot ·
passing a style key as an image input makes consistency *worse* · `bria-fibo`
accepts `reference_images` and reads none of them · negations are weak, describe
what IS there · a percentage is not renderable, exact counts are · freezing the
camera to fix the object froze the video · `seedream-5.0-lite` ignores aspect
ratio · GMI reads `ratio`, genblaze emits `aspect_ratio` · `fallback_models` is
inert against every real GMI failure · `eleven_v3` does not accept SSML
`<break>` · six concurrent ElevenLabs calls hit `rate_limit` · LMNT pads heavily ·
Homebrew's core `ffmpeg` has no libass · Anton falls back **silently** ·
clip-to-block mapping lives in each run's `manifest.json` · a bed 12–18 dB under
dialogue vanishes under lo-fi · **approval is not publication**.

**New on Day 4:**

1. **`gemini-2.5-flash-image` is down** on this key — times out, zero bytes,
   every attempt. `gemini-3-pro-image-preview` is the successor and works.
2. **Nano Banana Pro is slower to submit** and drops ~2 of 6 concurrent submits
   to a read timeout. Retry the slow good model; do not swap in a faster worse one.
3. **`nano-banana`, `nano-banana-2`, `nano-banana-pro` are all 404 on GMI.** The
   slug is the Gemini one.
4. **seedance 2.0 still 401s** — the key is not entitled. 1.0 and 1.5 return 200
   on identical requests. Only GMI support can fix it.
5. **A dict default does not fire on an empty value.** `b.get("role", ROLES[i-1])`
   returns `""` when the model sends `"role": ""`. Use `or`.
6. **Length and tracing oscillate.** Told to lengthen a line that must trace, the
   model adds framing prose, which traces to nothing, which breaks it again. The
   repair prompt must say where the extra words come from: widen an existing claim.
7. **Six distinct counts are needed for six blocks** — `test_a_countable_
   escalation_falls_by_a_whole_unit` forbids two blocks sharing a count.
8. **GMI publishes no rate for `gemini-3-pro-image`.** Registered at Google's list
   price ($0.134) as a labelled estimate, because a receipt reporting $0.000 for
   six images is worse than one carrying an estimate.

---

## Gotchas

- **`gate.py` must never import anything network-capable.** `test_structure.py`
  walks its import graph. That is what makes "$0 on a refusal" structural.
- **`--fresh` discards state**, including backfilled asset URIs. `cs2`'s clips
  still sit in B2 under `cs2-record/` but no longer match the current script.
- **The brand kit is read from B2, not from the working copy.** Edit
  `brand-kit/through-lines.yaml` → run `scripts/sync_brand_kit.py` → verify with
  `scripts/verify_brand_kit.py`, or the change does nothing.
- **`web/.env.local` is gitignored** and holds live B2 keys plus
  `NEXT_PUBLIC_WORKER_URL`.
- **Keep the CS-2 false-positive control.** It has already caught a gate bug that
  would have blocked 100% of legitimate blocks while citing a real rule.
- **An agent must not type a human's name into an approval.** Both published
  videos carry `UNREVIEWED` for exactly this reason.

---

## Open questions for Tarik

1. **Deadline** — Aug 2 per the PRD, or the 8 days mentioned?
2. **GMI credit balance.** Asked repeatedly, never answered; `estimate_cost()`
   returns `None` and it can only come from the console.
3. **Regenerate the GMI key** to get seedance 2.0 entitlement?
4. **ElevenLabs rates are guesses.** `eleven_v3` at $0.22/1k chars is UNVERIFIED
   and **Music is unregistered entirely**, so the bed reports as free.
5. **Voice cloning for the demo only?** A provenance tool narrated by a clone of a
   real person invites the question POL-1 forecloses.

**Decided on Day 4:** stamp treatment **1a** (rubber classic) · claims must
**trace every assertion**, not only numbers.
