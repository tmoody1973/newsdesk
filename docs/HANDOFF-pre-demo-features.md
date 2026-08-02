# Handoff — Newsdesk pre-demo features, mid-execution

**Written** 2026-08-02 ~17:15 CDT · **Hard deadline** Aug 3, 5:00 PM EDT (~23h)
**Repo** `/Users/tarikmoody/Documents/Projects/newsdesk` · **Branch `pre-demo-features`** (main untouched, nothing pushed)
**Tests** `cd api && uv run pytest tests/ -q` → **381 passed**, $0, no network

## Read these first, in this order

1. `CLAUDE.md` — the repo's own rules. The central one: **read the primary sources before building**, and it names the file to open for each kind of work. This project has been burned by an agent building from summaries.
2. `docs/HANDOFF.md` — project state, the mandate, ~30 dead assumptions. **Two of its claims were stale and are now corrected in the file**; see "Corrections" below.
3. `docs/superpowers/specs/2026-08-02-pre-demo-features-design.md` — the approved design for the four features, with decisions and reasons.
4. `docs/superpowers/plans/2026-08-02-pre-demo-features.md` — the task-by-task plan you are executing.
5. `.superpowers/sdd/2026-08-02-pre-demo-features/progress.md` — **the ledger, 115 lines, and the most useful file here.** Every task outcome, review verdict, deferred minor, and ruling. Trust it and `git log` over anything written from memory.

## Skills for the next session

- **`superpowers:subagent-driven-development`** — the process mid-run: fresh implementer per task, task review after each, broad review at the end.
- **`superpowers:requesting-code-review`** for the final whole-branch review.
- **`superpowers:finishing-a-development-branch`** once Phase 1 is green.
- If you pick up the diorama (Phase 2), **read `~/.claude/skills/vox-motion-graphics/references/diorama-doc.md` in full first.** It carries a moderation map, the exact STYLE tokens and the fake-oner prompt shape — all of which a paraphrase drops.

## Where execution stopped

| Task | State |
|---|---|
| 1 — Caption model + deterministic checks | complete, reviewed clean |
| 2 — Caption generation + claim tracing | complete, reviewed clean |
| 3 — `caption` pipeline stage | complete, reviewed clean |
| 4 — Through-line suggestion | complete, reviewed clean — **but see the gap** |
| 5 — End-card validation (`0e842ae`) | **committed, NOT reviewed — resume here** |
| 6 — Render + concat the card | not started |
| 7 — `endcard` stage | not started |

**First action:** review Task 5, then continue.

```bash
SK=~/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development
"$SK/scripts/review-package" docs/superpowers/plans/2026-08-02-pre-demo-features.md 94dddc8 HEAD
```

Briefs for Tasks 3–7 are already generated in the workspace directory.

## The decision waiting for Tarik — ask, do not assume

After Tasks 6–7 the four requested features stand at:

1. **Captions** — done and wired
2. **Through-line suggestion** — code done, **no caller** (see gap below)
3. **Paper-diorama art direction** — **not started**, and the largest of the four
4. **End card** — done

**Also unstarted: the demo video**, which `docs/HANDOFF.md` build-order item 4 calls the top item and which is what a judge actually watches. `docs/CS-6-live-workflow-test.md` is the step-by-step protocol against the live site.

My recommendation, **not yet accepted by Tarik**: finish 6–7, then record the demo rather than build the diorama. He has not ruled. He has also said plainly that he does not want scope quietly cut — if he wants the diorama, build it.

## The one real gap, and it is the plan author's fault

`suggest_through_line()` (Task 4) is correct and tested, and **nothing calls it.** Verified today:

- `brand-kit/through-lines.yaml` stores `through_lines` as a **list** of 6 entries each carrying `id`; the function's `menu` param is `dict[str, Any]` keyed by id. **No converter exists.**
- `grep -rn suggest_through_line api/newsdesk/ web/` returns no caller.

Feature 2 is therefore a library function, not a usable feature. Closing it needs `menu_from_kit(doc) -> dict` plus one caller — a wizard step, or a CLI/worker entry point. **That placement is a product decision, so it was surfaced rather than silently added.** Not a defect, not a review finding.

## Corrections to `docs/HANDOFF.md`, both verified today

1. **This Mac CAN reach GMI now.** The Cloudflare 1010 block cleared. `api.gmi-serving.com` and `console.gmicloud.ai` both answer 200 locally. `curl` before routing diagnosis through the Fly worker — three `fly ssh` attempts were burned on a block that had already lifted.
2. **`fly deploy` runs from the repo root, not `api/`.** `fly.toml` lives at the root deliberately. Building from `api/` once produced a worker that came up healthy and then refused all six blocks of a live run.

## Landed on main earlier today, before this branch

- `bd54bc9`, `0c201b1` — the Claude 5 family rejects `temperature`, and reasons past its whole output budget, returning **200 OK with an empty string**. Both fixed in `script.py` and deployed. `NEWSDESK_SCRIPT_MODEL` is deliberately still `anthropic/claude-haiku-4.5`: sonnet-5 converges first-pass but produced a duplicated block and a tense error on its one sample.
- `seedance-2-0-fast-260128` now works on GMI (the 401 entitlement gap closed), but bills **per second** — $5.40 a run against `seedance-1-0-pro-fast`'s $0.13 flat. Do not swap it in.
- GMI credits: Tarik added $15 today. A `402 Insufficient credits` at submit is a free way to probe the balance; there is no API-readable balance endpoint.

## Calibration — how this session actually went

**The plan had eight defects. Every one was caught by the agents executing it, not by its author:**

- **Two tests that would have passed while testing nothing** — including the one guarding *"a model must never write a citation"*, the product's central claim.
- **One that would have made the test suite hit the network** — `self.state.save()` inside a stage reaches B2, and `api/.env` holds live credentials.
- Plus: `Pipeline.begin` and `stage_assembly` do not exist, `judged()` returns three values not two, a test that could not pass against the real fixture, and a rejected run that discarded the model's response.

**So: do not trust the plan's code snippets. Trust the codebase.** Tell each implementer explicitly that finding brief defects is wanted, and that a test which would still pass with its target behaviour deleted is decoration. That instruction is why the later tasks each caught their own.

**Verify load-bearing tests by sabotage.** Disabling the source-provenance check and the menu-membership guard each made the corresponding test fail; both were then restored. That turns "looks fine" into proof, twice.

## Operational notes that will otherwise cost you time

- **Subagents commit their work but their final messages frequently do not arrive.** After each idle notification, check `git log` and the report file directly rather than waiting. Instruct reviewers to deliver via `SendMessage` to `team-lead` — that path works; the final assistant message often does not.
- Never run two implementer subagents on overlapping files. A read-only reviewer alongside an implementer touching different files is fine and was done repeatedly here.
- `.superpowers/` is gitignored (added this session).
- **Assembly is not a pipeline stage.** It lives in `api/scripts/run_cs1_assemble.py`, imported by `cli.py`, and its call site says a second implementation would be *"a second thing to keep true"*. **Do not edit it.** Task 7 was redesigned as its own `endcard` stage for exactly this reason, on Tarik's ruling.

## Deliberate cut, already named to Tarik

The spec says the music bed's 2.5s fade should resolve **on** the end card. Task 6 concatenates the card after mastering instead, leaving `build_filtergraph()` untouched — that file produced the `0.0 LUFS` defect and the ffmpeg-5.1 `framelog` failure. **Criterion dropped: "music lands on the logo."** The bed fades under the last narration and the card holds in silence. Task 7b records the follow-up.
