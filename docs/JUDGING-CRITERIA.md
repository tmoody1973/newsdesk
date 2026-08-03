# How Newsdesk meets the judging criteria

*Written 2 August 2026. Everything in here is checkable — links, commands and
file paths are given so you can confirm it rather than take our word.*

---

## First, what the thing is

A newsroom has a story. Someone types in the facts — each one with a source
behind it — and picks a visual style. Newsdesk turns that into a finished
vertical video with narration, animation and burned-in captions, and it embeds a
record inside the video file describing exactly how it was made: which models
ran, with which prompts, what they cost, and what got refused along the way.

The point is not that a computer can make a video. Lots of things do that. The
point is that a newsroom can **publish** it, because when someone asks "how did
you make this, and how do I know you didn't make it up," there is an answer that
survives being checked.

That framing matters for the criteria below, so it's worth stating plainly: the
governance is the product. The video is the output.

---

## Check it yourself

| What | Where |
|---|---|
| The live app | **https://newsdesk-rosy.vercel.app** — public, no sign-in |
| The render worker | **https://newsdesk-worker.fly.dev/health** — should say `ok: true` |
| The code | https://github.com/tmoody1973/newsdesk |

Two things you can run locally in under a minute:

```bash
cd api
uv run pytest tests/ -q                                    # 488 tests, no network, no cost
uv run python -m newsdesk ../stories/cs2.yaml --only gate  # runs the safety gate, spends $0
```

That second command is worth trying. It runs the part of the system that decides
whether a video is allowed to be made, and it needs no API keys and no money,
because it structurally cannot reach the internet. More on why below.

---

# Criterion 1 — Real-World Utility

> *Does the app solve a practical problem for a clear audience, and would that
> audience actually use it?*

## The audience is specific, and we are in it

Newsdesk was built by someone who works in a newsroom — public radio in
Milwaukee. It is not a guess about what newsrooms need.

The problem is concrete. Newsrooms are under real pressure to make short-form
video. The tools to generate it exist and are cheap. Almost none of them are
usable by a newsroom, because a newsroom cannot publish something it cannot
account for. If a fact in the video is wrong, "the AI wrote it" is not a defence
anyone in the business will accept. So the tools sit unused, or they get used
quietly and carefully by one person who checks everything by hand.

Newsdesk is built for the checking, not around it.

## How the checking actually works

There are three barriers, and they are deliberately different from each other.

**Wall 1 — nothing enters without a source.** Before anything is written or
generated, every fact must carry a source. A story with a bare assertion in it
will not load. This is enforced by the file parser itself
(`api/newsdesk/facts.py`, `api/newsdesk/storyfile.py`), so it isn't a check that
can be skipped — a story that fails Wall 1 never becomes a valid story object in
the first place.

**Wall 2 — the policy gate, which runs before any money is spent.** Seven rules,
written in plain language in `policy/policy.yaml`:

| | The rule |
|---|---|
| POL-1 | No real-person likenesses |
| POL-2 | The exclusion line is fixed |
| POL-3 | No fabricated news scenes |
| POL-4 | No readable text on screen |
| POL-5 | Narration fits its block |
| POL-6 | Output is checked, not just the request |
| POL-7 | A pasted URL is a story you reported, not one you're borrowing |

POL-6 is the one people miss. Most content filters check what you *asked for*.
This one also checks what *came back*, because a model can be asked for something
innocuous and return something that breaks a rule anyway.

POL-7 is newer and worth a note of its own: the app can now take a pasted link
and propose facts from it, and POL-7 draws the line between reporting a story and
lifting one.

If you run the gate command above you'll see it report `6 blocks x 4 rules`.
That's correct and worth explaining: four of the seven rules can be judged on the
request, before anything is generated, and those are the ones that save money by
refusing early. The rest are checked at other points — POL-6 against what
actually came back, POL-7 at the moment a link is ingested.

**Wall 3 — nothing publishes without a named human.** The finished video can only
be assembled through an `approve()` transition in `api/newsdesk/state.py`. There
is no second route to publication, and the approver's name lands in the record
embedded in the file. A person is not advised to check; the code has no path that
skips them.

## The evidence that it does real work

The strongest thing we can show is not a video. It's a catch.

On 2 August we built a story about Milwaukee's lead water pipes — real
reporting, six facts, sources fetched the same day from The Daily Reporter and
Milwaukee Neighbourhood News Service. The first script the system wrote said
the city *"replaced roughly 3,300 in 2025"* and, a few seconds later, that it
*"passed 10,000 replacements that year."*

Both statements were true. Both were sourced. Read together they look like a
contradiction, because one number was annual and the other was cumulative.

**Wall 1 could not catch this, and that is the interesting part.** The ambiguity
wasn't in the script — it was in the fact. The fact was correctly sourced and
correctly transcribed and still misleading. This is exactly the class of error
that automated checking misses and an editor catches, which is why there is a
human review screen at all. The fact was rewritten to say *"since the program
began, including roughly 3,300 in 2025"*, and the original wording is kept in the
file's header so the correction stays visible.

A second thing happened on the same story. The system worked out arithmetic
nobody gave it: 65,000 remaining pipes at 5,000 replaced per year does not finish
by the city's 2037 target. That conclusion was deliberately left out of the
facts to see whether the model would find it. It did, tagged the claim back to
the two facts it came from, and the validator confirmed the claim traced. The
caption reads **"THE MATH DOESN'T CLOSE."**

## Where this is honestly thin

One newsroom has used it — ours. No second organisation has tried it, so we
cannot tell you how it behaves in someone else's editorial process.

Also worth knowing before you look at the published videos: every one of them
records its approver as `"Claude (agent) — UNREVIEWED, pending Tarik Moody"`.
That is deliberate and we would defend it. An agent must not sign a human being's
name to a provenance record. The human re-stamps it on the review screen and the
video re-cuts at no cost. It looks unfinished; it is the opposite.

---

# Criterion 2 — Production Readiness

> *Does the app function reliably and support real-world workflows beyond a
> simple demo?*

## It is deployed, in two pieces, and both are up

The web app runs on Vercel. The renderer runs separately on Fly, in a container
that carries its own copy of `ffmpeg` with subtitle support and the Anton
typeface installed, because burning captions needs both and neither can be
assumed present.

The worker's health endpoint doesn't just say "ok" — it reports what it actually
found:

```json
{"ok": true, "ffmpeg_with_libass": "/usr/bin/ffmpeg", "subtitles_filter": true,
 "anton_installed": true, "access_code_required": true, "running": [], "capacity": 3}
```

That is deliberate. A health check that only says "ok" tells you the process is
alive. This one tells you the process can do its job.

## The test suite is fast, offline, and free

**488 tests, 18 seconds, zero network calls, $0.**

The "zero network" part is not a convention we try to keep — it's enforced.
`tests/test_structure.py` contains a test called
`test_gate_cannot_reach_the_network()` which walks the safety gate's import
graph and fails the build if anything network-capable appears anywhere in it.

This is what makes the claim "a refusal costs nothing" structural rather than
aspirational. The gate *cannot* spend money, because it cannot reach anything
that charges.

There is even a test called `test_scan_would_catch_a_violation()` — a test that
checks the test works, by feeding it a deliberate violation and confirming it
fails.

## The pipeline is resumable, which matters more than it sounds

Five stages: **script → gate → blocks → narration → assembly.** Each one can be
run on its own, and state is saved after each stage completes. If the narration
step fails, you re-run narration — you don't re-run and re-pay for the images.

For a system where a single run costs real money, this is the difference between
a tool and a demo.

## It has failed in production, correctly, four times

The most useful thing we can tell you about reliability is what happened when
things broke.

On 2 August, for about forty minutes, the model provider's entire
Anthropic-on-Bedrock path returned errors. Not our bug — an upstream outage.

Here is what the system did: the claim checker couldn't run, so it could not
confirm that claims traced to facts, so **the gate refused every block.** Nine
script attempts in a row. Total cost: **$0.**

It did not assume the content was fine because the checker was unavailable. It
treated "I can't verify this" as "I won't ship this." That is the fourth time
this system has failed closed and the fourth time that was the right call.

We also built a bypass during the outage — a way to route that one text call
directly to Anthropic instead of through the provider. It was written, tested and
deployed. **It never fired**, because the provider recovered first, and the
ledger proves it: the successful run records the original provider. It is switched
off and should stay off.

## Two known warts, stated plainly

1. When a human re-stamps an already-published video, the new approval timestamp
   overwrites the original rather than appending. The approver name is right;
   the history of *when* is lossy.
2. Re-running a story under the same title hands back the same script, because
   the script stage skips when narration already exists. A re-run needs a new
   title. This bit us once and is now documented.

## The real risk, if you are going to try it

Rendering costs money — **$1.21, $1.23 and $1.31** on the three published runs
where cost was recorded, against a $1.20 estimate. The project has about **$11
of credit left**, which is around eight more videos.

If several judges each generate a video, it runs dry. The four already-published
videos are the reliable path; generating a fresh one is possible but finite. We
would rather say this than have it fail silently in front of you.

---

# Criterion 3 — B2 Storage and Data Orchestration

> *Does the app use Backblaze B2 meaningfully to store, organize, serve, or
> manage generated media, metadata, provenance, or app assets?*

## Five buckets, each with one job

This is not one bucket with everything thrown in it.

| Bucket | What lives there | Public? |
|---|---|---|
| `newsdesk-assets` | generated images, video clips, audio | yes |
| `newsdesk-brand-kit` | voice settings, style key, subtitle rules, story through-lines | yes |
| `newsdesk-manifests` | the provenance records | no |
| `newsdesk-audit` | the decision ledger — every refusal and why | no |
| `newsdesk-runs` | the live state of every story | no |

The public/private split is code, not habit. `api/newsdesk/config.py` declares
`PUBLIC_BUCKETS` as a fixed, unchangeable set containing exactly two entries. A
bucket cannot drift into being public by someone forgetting.

Generated media is filed hierarchically under a per-run prefix
(`KeyStrategy.HIERARCHICAL` in `api/newsdesk/blocks.py`), so everything belonging
to one story sits together and can be found, served or deleted as a unit.

## B2 is the database, not the file cabinet

This is the part worth pausing on.

There is no Postgres in this project. There is no MySQL, no SQLite, no hosted
database of any kind.

The state of every story — its status, its blocks, its costs, its approver, its
decisions — is a `state.json` object written to the `newsdesk-runs` bucket
(`api/newsdesk/state.py`) and read back by the worker (`api/newsdesk/server.py`).
The board you see when you open the app is rendered directly from B2.

So B2 isn't where the finished files are parked at the end. It is the thing the
application runs on. Every page load is a read from B2; every stage completion is
a write to B2.

## The audit bucket is the unusual one

Most systems log what they did. This one keeps a durable, separate record of what
it **refused** to do, and why, in its own bucket — and that record is
cryptographically tied to the finished video. Details in the next section,
because it's really a Genblaze story.

## Where this is thin

There is no lifecycle or retention policy configured on the buckets yet. For a
newsroom running this for a year, old run state and superseded assets would
accumulate. It's a settings problem rather than an architecture problem, but we
haven't done it.

---

# Criterion 4 — Use of Genblaze

> *Does the app use Genblaze meaningfully to build, connect, or orchestrate
> generative media workflows across models, providers, or steps?*

## Five providers, four kinds of media, one framework

Every generative step in this app goes through Genblaze:

| Genblaze piece | What it does here |
|---|---|
| `genblaze_core` — `Pipeline`, `Asset`, `Modality`, `ObjectStorageSink` | orchestrates every generation step and lands the result in B2 |
| `genblaze_s3` | the B2 connection itself |
| `genblaze_gmicloud` | still images, video clips, and text |
| `genblaze_elevenlabs` | narration voice |
| `genblaze_lmnt` | the fallback voice, if the first one fails |
| `genblaze_core.media.Mp4Handler` | writes the provenance record *inside* the finished MP4 |
| `genblaze_core.models` — `Manifest`, `Run`, `Step` | the shape of that record |
| `genblaze_core.providers` | cost accounting, so the receipt shows real money |

That's images, video, speech and text — four modalities — across five providers,
with a fallback chain the app walks by itself when a provider fails.

The finished file is validated with `genblaze verify`, which exits 0. That's the
acceptance test: not "does it play" but "does its own record of how it was made
still check out."

## The part we're most proud of: making Genblaze record refusals

Here is a real gap we hit, and what we did about it.

Genblaze keeps a detailed record of everything that runs through
`Pipeline.step()` — the model, the prompt, the parameters, timestamps, hashes —
and embeds it in the finished video. Excellent, and exactly what a newsroom
needs.

But `chat()` — the plain text call — is a normal function, not a provider object.
It can't ride a Pipeline. So nothing about a `chat()` call reaches the record.

For most applications that's a footnote. For this one it's the whole product,
because **all three of our `chat()` calls are governance**: validating the script
against the facts, the judgement half of the policy gate, and looking at the
rendered frames afterwards to check what actually came out.

Left alone, the receipt inside the video would have documented every image we
made and said nothing about anything we refused. A provenance record that only
lists successes is a brochure.

So we built the missing half (`api/newsdesk/decisions.py`). Every judgement — pass,
reject, revise — is recorded with its model, its reasoning and its verdict, and
written to the `newsdesk-audit` bucket alongside the places Genblaze keeps its
own records.

Then the important step: **at assembly, a digest of that ledger is folded into
the master manifest that Genblaze embeds in the MP4.**

That is what makes it provenance instead of logging. Without that fold, the
ledger is a text file anyone could quietly edit afterwards. With it, changing a
single rejection after the fact breaks `genblaze verify` on the video.

We think this is the interesting contribution: not consuming the framework, but
finding a real hole in its provenance model and closing it *using the framework's
own verification*.

## Full disclosure on the one bypass

As described under Production Readiness, there is a switch that routes one text
call directly to Anthropic instead of through Genblaze, built during an upstream
outage. The contest rules require Backblaze B2 and Genblaze but do not mandate
any particular model or provider — only that choices are disclosed. So: it
exists, it is off, it has never been used in a published run, and every receipt
names whichever provider actually ran. All four media legs — stills, video,
voice and the fallback chain — go through Genblaze regardless.

We are mentioning it because we would rather disclose it than have it found.

---

# Summary

| Criterion | Where we think we stand |
|---|---|
| **Real-World Utility** | Built inside a working newsroom for a problem that stops newsrooms publishing today. Demonstrated catching a genuine journalism error before any money was spent. Thin on outside validation. |
| **Production Readiness** | Deployed, live, resumable, 488 offline tests, four correct failures under real outage conditions. Constrained by remaining credit. |
| **B2 Storage** | Five purpose-separated buckets with an enforced public/private split, and B2 serving as the application's actual database rather than its file store. |
| **Use of Genblaze** | Five providers across four modalities, plus an extension that makes Genblaze's tamper-evident manifest cover refusals as well as generations. |

## What we would look at first if we were judging

1. Run `uv run python -m newsdesk ../stories/cs2.yaml --only gate` — the safety
   gate, working, at no cost and with no credentials.
2. Read `api/newsdesk/decisions.py`. The comment at the top explains the
   refusal-ledger design better than this document does.
3. Open the Milwaukee lead-pipes video and read its receipt page.
4. Read the Day 6 section of `docs/HANDOFF.md` for the journalism error that got
   caught, written up at the time rather than reconstructed afterwards.

## Related reading in this repo

- `docs/HANDOFF.md` — current state, and thirty assumptions that testing killed
- `docs/PLAN.md` — the build plan
- `policy/policy.yaml` — the seven rules, in plain language, as the live source
- `newsdesk-case-studies.md` — the five fixture stories used as the test suite
- `README.md` — setup and architecture
