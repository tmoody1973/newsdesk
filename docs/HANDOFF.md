# Handoff — Newsdesk, Day 6 · SUBMISSION DAY (2026-08-02)

**Repo:** `/Users/tarikmoody/Documents/Projects/newsdesk` · public at
[github.com/tmoody1973/newsdesk](https://github.com/tmoody1973/newsdesk), `main`
**Linear:** [Newsdesk — Backblaze Generative Media Hackathon](https://linear.app/moodyco/project/newsdesk-backblaze-generative-media-hackathon-5f68ce40d2cc) · team `MOO`
**Deadline:** submit **TODAY, Aug 2**, hard cut **Aug 3, 5:00 PM EDT**
**Tests:** `cd api && uv run pytest tests/ -q` → **328 passed**, zero network, $0
**Spend:** ~$13.75 of ~$25 · **~$11 left**, roughly eight more stories

## ▶ LIVE — check these first

| | |
|---|---|
| **Site** | **https://newsdesk-rosy.vercel.app** — public, no sign-in |
| **Worker** | **https://newsdesk-worker.fly.dev** — `/health` should read `ok: true` |

The other two Vercel aliases (`*-tmoody1973s-projects.vercel.app`) 302 to SSO.
**`newsdesk-rosy` is the one to give a judge.**

**Four videos are published.** All four carry the approver string
`"Claude (agent) — UNREVIEWED, pending Tarik Moody"` in their embedded manifests,
deliberately: an agent must not sign a human's name to a provenance record. Tarik
re-stamps on Editor Review and it re-cuts at $0 — it does write a new approval
timestamp over the original, which is a known wart.

| run | s | LUFS | cost | note |
|---|---|---|---|---|
| `cs1-narration` | 72.6 | −16.0 | — | the legacy CS-1 video, placeholder approver |
| `what-a-billion-dollars-of-vinyl-says-abo` | 69.80 | −16.0 | $1.2116 | first browser-start-to-finish |
| `who-pays-when-the-signal-goes-quiet` | 71.47 | −16.0 | $1.2251 | first cut on the **deployed** worker |
| `the-65-000-pipes-under-milwaukee` | 68.77 | −16.1 | $1.3125 | **Day 6.** Real Milwaukee reporting, sources fetched same day |

Three through-lines used: `tower-signal`, `record`, `fuse`. Unused: `dollar-cut`,
`scale`, `balloon`.

## ⚙️ WORKER SECRET STATE — check before debugging anything

`fly secrets list --app newsdesk-worker`. As of Day 6 the script role is set to:

| secret | value | why |
|---|---|---|
| `NEWSDESK_SCRIPT_PROVIDER` | `gmicloud` | reverted after the outage cleared; keeps text on Genblaze |
| `NEWSDESK_SCRIPT_MODEL` | `anthropic/claude-haiku-4.5` | the one that maps claims first-pass |
| `ANTHROPIC_API_KEY` | set | powers the escape hatch below; **currently dormant** |
| `NEWSDESK_SCRIPT_TIMEOUT` | **unset** | was 600 for a DeepSeek experiment; not needed on haiku |

Plus the seven originals (GMI, ElevenLabs, LMNT, B2 ×3, access code).

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

### Proven on Day 6 — real reporting, sourced the same day

`the-65-000-pipes-under-milwaukee` is the first story that is **not a fixture**.
Milwaukee's lead service lines: six facts, every one carrying a number, verified
by fetching two articles — The Daily Reporter (6 May 2026) and Milwaukee NNS
(15 Mar 2026) — rather than recalled. Story file at
`stories/the-65-000-pipes-under-milwaukee.yaml`, `fuse` through-line.

**Two findings worth more than the video:**

1. **Script Review caught a real journalism error before a dollar was spent.**
   The first script put *"replaced roughly 3,300 in 2025"* beside *"passed 10,000
   replacements that year"* — two numbers for one year, reading as a
   contradiction. Both were true, both were sourced, so **Wall 1 could not catch
   it**: the ambiguity was in the FACT, not the script. F5 was rewritten to say
   "since the program began, including roughly 3,300 in 2025", and the old
   wording is kept in the file's header. That is the review screen doing exactly
   what it exists for.
2. **The model derived the arithmetic nobody entered.** 65,000 remaining at 5,000
   a year does not reach 2037. That conclusion was deliberately withheld from the
   facts; block 5 found it, tagged it to F1 and F2, and the validator made it
   trace. The caption reads **"THE MATH DOESN'T CLOSE."** over a cutout crowd.

Also: **a re-run needs a NEW title.** `stage_script` skips when every block
already has narration, so re-posting the same run id hands back the same flawed
script. And `test_shipped_story_ids_are_unique_and_match_their_filenames` will
fail the build if the story file's name and its `id` disagree — two stories
sharing an id share a B2 prefix and a RunState key.

---

---

## 🔥 DAY 6 — the GMI outage, and what it taught

**For ~40 minutes on Aug 2, the live demo's script stage was dead.** Not our bug.

```
GMICloud chat failed (400): "InvokeModel: operation error Bedrock Run…"
— blocked rather than assumed safe
```

**GMI's entire Anthropic-on-Bedrock path was failing.** Both
`anthropic/claude-haiku-4.5` and `anthropic/claude-sonnet-4.5` returned the same
400. The claim checker could not run, so the gate refused every block — correctly
— and **nine consecutive script attempts cost $0**. That is the fourth
fail-closed of this project and the fourth time it was right.

**What it was NOT:** `deepseek-ai/DeepSeek-V3-0324` reached the model fine and
returned ordinary POL-5 word-count complaints. That is how the diagnosis was
made — a different backend, a different error.

**What fixed it: GMI recovered on its own.** The Anthropic escape hatch (below)
was built, tested, deployed — and **never fired**. The ledger proves it: the
successful run records `prov= gmicloud`. Do not let anyone claim otherwise.

### The escape hatch, dormant but ready

`NEWSDESK_SCRIPT_PROVIDER=anthropic` routes the script call to the Anthropic API
directly, bypassing GMI. `script.py::_anthropic_chat`, `urllib` not the SDK — no
new dependency, no lockfile churn, nothing new in any import graph.

**The rules allow it.** Entrants must use Backblaze B2 **and Genblaze**; no
provider or model is mandated, only *disclosed*. Genblaze still carries all four
media legs — stills, video, voice, and the fallback chains this app walks
itself — so routing one text call direct costs the Genblaze story nothing. The
provider name flows into `judged()`, so the receipt names whichever actually ran.

**It is off by default and should stay off while GMI works** — three `chat()`
roles on Genblaze is the better "Use of Genblaze" story.

### Two things that cost time and will again

1. **`fly secrets set` alone does not ship code.** Setting
   `NEWSDESK_SCRIPT_PROVIDER=anthropic` on an image built before the hatch
   existed does exactly nothing. **`fly deploy` too.** Nearly reported a fix
   that hadn't shipped.
2. **Never change secrets while a run is rendering.** A restart mid-`blocks`
   spends the money and saves nothing — state is written *after* each stage.

### ~~This Mac cannot reach GMI at all~~ · **CLEARED 2026-08-02, probe it before believing it**

The old note, kept because it was true for six days: `403, Cloudflare error 1010`
on every model including DeepSeek, Spectrum Security Shield, first recorded
2026-07-27, *"only the Fly worker can talk to GMI"*.

**It is no longer true.** Measured Aug 2 ~15:10 CDT from this Mac:
`GET api.gmi-serving.com/v1/models` → **200 in 0.33s**, and
`GET console.gmicloud.ai/api/v1/ie/requestqueue/apikey/requests` → **200 in 1.8s**.
Both probes below ran locally. **Spend ten seconds on a `curl` before routing
diagnosis through the worker** — three `fly ssh`/`fly machine exec` attempts were
burned on a block that had already lifted.

Two flyctl facts learned in the process, if the block ever returns:
`fly ssh console` hangs after `Connecting to fdaa:…` on this machine (wireguard),
but **`fly machine exec <id> --app newsdesk-worker "<cmd>"` works** — it goes over
the Machines API. It **strips quote characters** from the command, though, so
nothing containing a string literal survives; `python -cprint(1+1)` runs,
`python -cprint("hi")` becomes `print(hi)`.

`curl` to `newsdesk-worker.fly.dev` still needs
`--resolve newsdesk-worker.fly.dev:443:66.241.125.20` — stale NXDOMAIN in this
machine's resolver. Chrome is fine.

### Browser automation

**The Claude-in-Chrome extension is disconnected** (dropped over a multi-day
gap). **Playwright MCP works** and drove the whole Day 6 run against production.
It writes scratch into the repo root; `.playwright-mcp/` and `cs6-*.png` are now
gitignored. To *record* a demo you need the extension back, or drive it by hand.

---

## ⚠️ RISK — read before planning

**Script generation is materially hard and can fail outright.**

Day 4 added a rule: every block except the kicker must trace to a fact. Right
rule, but it stacks on 23–27 words, 2–3 sentences, whole-assertion mapping, and
every fact used.

Day 6 evidence: **both stories converged, and both used 5 of the 6 allowed
repair passes.** One attempt of headroom. Do not lower `MAX_ATTEMPTS`.

If it bites, **the lever is `MAX_ATTEMPTS` (currently 6, not env-overridable) or
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
- **`text-graphite`, `border-ink`, `bg-pasteboard`, `text-approval-blue` and
  `text-stamp-red` emit no CSS.** They are defined nowhere and used across the
  Desk, Policy, Receipt and Red team pages, which look right only because
  `_ds/modernist.css` carries the palette underneath. `/brand-kit` deliberately
  does not follow that pattern — it uses the design system's own custom
  properties. Defining the missing names would change four pages that currently
  render correctly, so it was left alone.
- **`outputFileTracingIncludes` is per route.** A new page reading
  `policy/policy.yaml` needs its own entry in `next.config.mjs` or it works
  locally and 500s in production.
- **The validator traces quantities, not qualities.** Day 6, block 2 of the
  Milwaukee story asserted *"Now we know they poison the water they deliver"*
  tagged to a fact that is only counts and a deadline. It rode along untraced
  because there was no number in it.
- **Synthesised arithmetic can pass on a partial trace.** Day 5, a block claiming
  *"the pace must nearly double"* was tagged to one fact when the arithmetic
  needs two.
- **`POST /runs` with `assembly` demands an `approver`** even when the run is
  already approved in B2, and re-stamping writes a new timestamp over the
  original approval time.

### ~~3. README~~ · **DONE, Day 6**

Rewritten. Live URL first, two public receipts, the 401/422 probes a reader can
reproduce, the real per-run costs, and what has **not** been run (CS-3 is
unit-covered only). `/brand-kit` also built — the left rail linked to a 404 on
every page.

### 4. **DEMO VIDEO — the top item, today**

There is real material now: four published films, four receipts, a red-team page,
and the refusal beat. `docs/CS-6-live-workflow-test.md` is the step-by-step
protocol against the live site, with the $0 sections marked.

**Suggested spine** (from `newsdesk-case-studies.md`): a receipt tease → one full
flow with the rejection beat → CS-4 refusals rapid-fire → live `genblaze verify`
on a published MP4 → close.

**Blocked on:** the Chrome extension being reconnected, or Tarik driving it.

### 5. Submit

Disclose every provider and model — that is an explicit rule requirement, and
after Day 6 the list must include Anthropic-direct as an available fallback even
though it is currently dormant.

### ~~6. Open experiments, both cheap, neither run~~ · **BOTH PROBED, Day 6 ~15:10 CDT, ≈$1.00**

> Cost correction: this was first reported as ~$0.21, which was wrong — it priced
> `seedance-2-0-fast-260128` as a flat rate. It bills **per second**, so one 5s
> probe clip was $0.45, not $0.02. The mistake is the same one that makes the
> swap unaffordable below, and it is kept here because a probe budget that is
> wrong by 5× is exactly how a cheap experiment stops being cheap.

Neither is *adopted* — both are now answered, and each carries one blocker that
would have looked like something else if adopted blind.

#### Probe 1 — Sonnet 5 for the script role: **available, cheaper, and it will 400 on the current code**

`anthropic/claude-sonnet-5` **is on this contract**, at **$2/$10 per M** against
sonnet-4.5's $3/$15 — newer *and* cheaper. Twelve Anthropic slugs are catalogued,
including `claude-opus-5` ($5/$25), `claude-fable-5` ($10/$50), opus-4.5→4.8 and
sonnet-4.6. A 16-token probe returns `'ok'` in ~3.6s. The haiku-4.5 control also
answered in 2.1s, so **GMI's Anthropic-on-Bedrock path is fully recovered.**

**The blocker: the Claude 5 family rejects `temperature`.**

```
anthropic/claude-sonnet-5   temperature=0.2  → 400  "`temperature` is deprecated for this model."
anthropic/claude-opus-5     temperature=0.2  → 400  same
anthropic/claude-sonnet-5   omitted          → 200  'ok'
anthropic/claude-sonnet-5   temperature=1.0  → 200  'ok'
```

`script.py` passes `temperature=0.2` (line 699) and `0.4` (line 498). So setting
`NEWSDESK_SCRIPT_MODEL=anthropic/claude-sonnet-5` **on its own fails every
attempt with a 400 — which `judged()` records as a *reject*.** It would read as
the claim checker refusing six blocks, not as a bad request. That is precisely
the failure mode the `TIMEOUT_S` comment two lines above already warns about:
*a timeout is recorded as a reject, so too short a value does not fail loudly.*
The same trap, a different parameter.

**FIXED, Day 6.** `script.py::accepts_temperature()` drops the kwarg for the
Claude 5 family in `chat()` — the one funnel both call sites (`:498` at 0.4,
`:699` at 0.2) route through, so neither caller had to change. `_anthropic_chat`
now omits `temperature` from the body when it is `None` rather than defaulting
to 0.2, or dropping it upstream would not have reached the wire. Matched on the
family (`claude-<tier>-5`) rather than by slug so the next Claude 5 does not
reintroduce it; 13 tests in `test_script.py` pin both directions, including that
`claude-haiku-4.5` and `claude-sonnet-4.6` keep their temperature — *a guard
that fires on everything is a guard that gets deleted.* **341 passing**, still
$0 and no network.

Verified live against GMI, not only against the fake: `chat("anthropic/claude-
sonnet-5", temperature=0.2)` → `'Ok'` in 2.4s with the kwarg dropped, and
`claude-haiku-4.5` still sends 0.2 and answers in 1.1s.

**Not switched on.** `NEWSDESK_SCRIPT_MODEL` is still `anthropic/claude-haiku-4.5`.
Flipping it is now a one-line secret change and safe, and costs **~$0.02 → ~$0.04**
a run (sonnet-5 is exactly 2× haiku's rate, not the 3–4× §6 originally assumed).
Run it against one real story before the demo — Day 6's defects were *writing*
failures, which is the whole reason to want it, and that is not something a
16-token probe can tell you.

#### Probe 2 — `seedance-2.0`: **the 401 is gone; the fast variant runs end to end**

| slug | submit | result |
|---|---|---|
| `seedance-2-0-fast-260128` | **200** | `success` — real MP4, **720×1280 true 9:16**, 5.04s, 24fps, 2.2 MB |
| `seedance-1-0-pro-fast-251015` (control) | 200 | `success` — 704×1248, 5.04s, 6.8 MB |
| `seedance-2-0-260128` | **402** | `Insufficient credits` |
| `seedance-2-0-260128-upscale` | **402** | `Insufficient credits` |

Not 401 anywhere. **The entitlement gap that GMI support had to provision is
closed for the fast variant.** `ratio: "9:16"` was honoured, so
`register_seedance_ratio` already covers it — `seedance-2-0-fast-260128` is
in `SEEDANCE_SLUGS`. A frame was pulled and looked at: a lit paper-cutout city,
genuine and on-brand, at a higher resolution than 1.0 delivers.

**Do not swap `VIDEO_MODEL`. The economics kill it before the quality argument
starts.** `pricing.py` already carries the rates and they are not comparable:

| model | rate | six 10s blocks |
|---|---|---|
| `seedance-1-0-pro-fast-251015` | $0.022 **flat** | **$0.13** |
| `seedance-2-0-260128` | $0.052 **per second** | **$3.12** |
| `seedance-2-0-fast-260128` | $0.09 **per second** | **$5.40** |

**41× the video cost, and 5.6× the entire current GMI cost of a run** — a $0.98
video becomes $6.25. The 2.0 rate is per-second and 1.0-pro-fast's is flat, which
is what makes the gap enormous rather than merely large. (The $0.09/s is marked
UNVERIFIED in `pricing.py`, from GMI's pricing post; even at half it loses.)

Two further caveats, if the price ever moves:

1. **It is ~4× slower.** 134s to 1.0-pro-fast's 34s, on every one of six blocks.
2. **This probe was text-to-video.** The app's path is image-to-video with the
   still in `first_frame`, which is what carries style consistency across six
   blocks. **That path is untested on 2.0** and is the only thing that matters —
   consistency, not one pretty frame.

So the answer to *"is 2.0 better?"* is: **yes, and irrelevant.** It renders at
720×1280 against 704×1248 and looks it. It is not worth 5.6× a run.

#### 💰 Found while probing: **`402 Insufficient credits` — and how to read the balance without the console**

Open question 2 has never been answerable because `estimate_cost()` returns
`None` and no API-key-readable balance endpoint exists — `/billing/credits`
answers `401 Invalid access token` to an API key, so the console really is the
only place the number lives. **But a 402 at submit is a free probe.** Submitting
a model you know the price of and reading 402-vs-200 brackets the balance at $0.

Measured that way at ~15:12 CDT: the production chain all cleared
(`gemini-3-pro-image-preview` 200, `bria-fibo` 200,
`seedance-1-0-pro-fast-251015` 200) while `seedance-2-0-260128` 402'd. **Tarik
topped up $15 at ~15:17 and both previously-402 models went 200.** So the
balance is healthy now, and the technique is on the shelf for next time.

**What a run actually costs in GMI credits** — narration is ElevenLabs and is
billed elsewhere, so it is *not* in this number:

| leg | | |
|---|---|---|
| 6 stills | `gemini-3-pro-image-preview` @ $0.134 | $0.804 |
| 6 clips | `seedance-1-0-pro-fast-251015` @ $0.022 flat | $0.132 |
| script | haiku-4.5 ≈ $0.02 · sonnet-5 ≈ $0.04 | ~$0.03 |
| | **GMI per video** | **≈ $0.98** |

**$15 buys roughly 15 more videos.** Submission needs maybe three or four. The
image leg is 82% of it, so if credits ever get tight the lever is
`NEWSDESK_IMAGE_FALLBACK=bria-fibo` ($0.039 → $0.23 a run) at a real quality
cost — that is a **cut**, and it drops the 768×1376 stills the Day 4 note says
are the reason the pictures stopped being bland.

#### Not a defect — a probe artifact worth not re-chasing

A raw POST for `kling-image2video-v2.1-master` returns **404 "model does not
exist"**, because the queue catalogue now spells it `Kling-Image2Video-V2.1-Master`.
**The app is fine:** `_submit_request` calls `resolve_canonical()` first, and it
maps the lowercase slug to the capitalised one — verified. The video fallback
chain is intact. The 404 only appears when the SDK is bypassed, as this probe did.

### 7. If time allows

CS-3 (never run end to end) · per-block approvals persisted · "Reject with note"
· the lineage drawer · **URL ingest** (designed in `docs/PLAN.md` §B4, unbuilt —
Tarik's own idea and the plan calls it the highest-leverage one on the board).

### 8. Paused mid-design: multi-outlet brand kits

A `superpowers:brainstorming` session was **interrupted after design sections
1–3**, awaiting "does this look right?". Five decisions are locked:

1. Spec the whole feature, ship a slice
2. **Exclusions are add-only** — a kit may append prohibitions, never remove
   them; `blockprompt.negative_is_intact()` already accepts `base + ","`
3. Authoring is **interview → AI drafts → human publishes**, same shape as Wall 1
4. **Layered**: one object library per outlet, several looks on top
5. **Bake at publish** — flatten layers into an immutable versioned kit in B2

The one non-obvious safety point already worked out: **the prompt is built from
the kit; POL-2's check is made against the platform base**, read from a location
the outlet cannot write. Otherwise a kit is compared against itself and always
passes. Nothing is written to disk yet.

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
4. ~~**seedance 2.0 still 401s** — the key is not entitled. 1.0 and 1.5 return 200
   on identical requests. Only GMI support can fix it.~~ **Overturned Day 6:**
   `seedance-2-0-fast-260128` submits 200 and completes `success` on this same
   key. Entitlement was provisioned upstream at some point between 07-28 and
   08-02. The full `seedance-2-0-260128` now fails 402, not 401 — a balance
   problem, not an access one. Wrong version kept because "only GMI support can
   fix it" was read as permanent and it was not.
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
   returns `None` and it can only come from the console. **Day 6 update:** a
   `402 Insufficient credits` on `seedance-2-0-260128` proves it is *low but not
   empty* — the production chain still submits. Still needs a console number.
3. ~~**Regenerate the GMI key** to get seedance 2.0 entitlement?~~ **Moot** —
   `seedance-2-0-fast-260128` returns 200 and completes on the current key.
4. **ElevenLabs rates are guesses.** `eleven_v3` at $0.22/1k chars is UNVERIFIED
   and **Music is unregistered entirely**, so the bed reports as free.
5. **Voice cloning for the demo only?** A provenance tool narrated by a clone of a
   real person invites the question POL-1 forecloses.

**Decided on Day 4:** stamp treatment **1a** (rubber classic) · claims must
**trace every assertion**, not only numbers.
