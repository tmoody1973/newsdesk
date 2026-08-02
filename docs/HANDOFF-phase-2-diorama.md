# Handoff — Phase 2: the paper-diorama art direction

**Written** 2026-08-02 ~18:05 CDT · **Hard deadline** Aug 3, 5:00 PM EDT
**Branch** `main`, clean, **401 tests passing**, **26 commits ahead of origin — NOT pushed**
**Phase 1 is merged** (`fcb7ae7`). Phase 2 is **zero code**: no `brand-kit/diorama/`, no `brand-kit/floor.txt`, no `kit_prefix`/`platform_floor`/`KNOWN_KITS`.

Phase 2 is the current priority. The demo video is not yet recorded;
`docs/CS-6-live-workflow-test.md` holds its protocol when it comes up.

## ▶ START HERE — exact state at handoff

**Branch `phase-2-diorama`**, cut from `main` at `d7b8243`. **Tree is clean.**

**Task 8 (keyed kit resolution) is COMMITTED but NOT REVIEWED** — `79f3981`,
*"feat(brandkit): kits are keyed, and nothing migrates"*.

Verified by the controller on the committed tree, not taken from its report:

- **407 tests passing** (401 before Task 8)
- **`tests/test_structure.py` 12/12** — Wall 2 intact
- `grep` confirms `blockprompt.py` does **not** import `brandkit.py`. `HOUSE_KIT`
  and `KNOWN_KITS` live in `blockprompt.py` and the other two import from there.
  That is the trap avoided; do not let a later task reverse it.

**Your first action: review Task 8, then continue to Task 9.**

```bash
SK=~/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development
"$SK/scripts/review-package" docs/superpowers/plans/2026-08-02-pre-demo-features.md d7b8243 HEAD
"$SK/scripts/task-brief"     docs/superpowers/plans/2026-08-02-pre-demo-features.md 9
```

**Carry this into Task 9 or 11 — Task 8's implementer flagged it:** `cli.py:166`
and `pipeline.py:45` both call `brandkit.load()` with **no `kit_id`**, so the run
path stays house-only until something threads `kit_id` through from the story
file. Keyed resolution exists; nothing uses the key yet.

The workspace and ledger are at
`.superpowers/sdd/2026-08-02-pre-demo-features/` — the ledger carries every
Phase 1 ruling. Briefs for Tasks 3–8 are already generated there.

---

## Read these before writing anything

1. **`~/.claude/skills/vox-motion-graphics/references/diorama-doc.md` — IN FULL.**
   This is the source. `CLAUDE.md` names it for exactly this work. It carries
   three things no paraphrase has: the engine choice and its parameters, a
   **moderation map** that cost someone an afternoon, and the fake-oner block
   prompt shape. Do not build the kit from any summary, including this document.
2. `CLAUDE.md` — the repo's own rules. The one that matters most here: **verify
   against real output.** On this project that rule has now caught defects that
   tests, careful code review, and official documentation all missed.
3. `docs/superpowers/plans/2026-08-02-pre-demo-features.md` — **Tasks 8–12 are
   Phase 2.** Task 12 (authoring interview) is explicitly deferred.
4. `docs/HANDOFF-pre-demo-features.md` — Phase 1's record, including **the defect
   pattern**, which is the single most useful thing to carry forward.
5. `docs/HANDOFF.md` — project state. Two of its claims were corrected today; see
   "Corrections" there.

## Skills

- **`superpowers:subagent-driven-development`** — the process. Fresh implementer
  per task, task review after each, whole-branch review at the end.
- **`superpowers:using-git-worktrees`** or a feature branch — do not build on
  `main`. Phase 1 used branch `pre-demo-features` in the main working copy so
  `fly deploy` / `vercel --prod` kept working; that worked well, repeat it.
- **`superpowers:finishing-a-development-branch`** at the end.

---

## What Phase 2 actually is

Four pieces, in dependency order. The plan has them as Tasks 8–11.

### Task 8 — keyed kit resolution

B2 keys are flat, so `kit/negative.txt` and `kit/diorama/negative.txt` coexist.
**The house kit never moves and never re-syncs.**

```
kit_prefix(kit_id) → "kit/"            when kit_id is None or "house"
                   → f"kit/{kit_id}/"  otherwise
```

`brandkit.load(kit_id="house")`. Story files gain `kit: diorama`; an unknown kit
is refused at Wall 1 (422, no run, nothing spent).

**A kit is these six files** (`brandkit.REQUIRED_TEXT`), and absent any one it is
not a kit: `negative.txt`, `style-tokens.txt`, `scene-guidance.txt`,
`through-lines.yaml`, `voice.json`, `subtitle.ass`.

**⚠️ The trap that will bite you.** `blockprompt.py` **must never import
`brandkit.py`**. `gate.py` imports `blockprompt`, and `tests/test_structure.py`
walks that graph and fails the build if anything network-capable appears —
`brandkit` reaches `config.backend`. **That import is what makes "$0 spent on a
refusal" structural rather than promised.** So define `HOUSE_KIT` and
`KNOWN_KITS` in `blockprompt.py` and have `brandkit` and `storyfile` import them
from there. Run `uv run pytest tests/test_structure.py -q` before committing.

Also: `_read(name, directory)` takes a **full path string**, not a subdirectory
name. `kit_dir()` is overridable via `NEWSDESK_BRAND_KIT_DIR`.

### Task 9 — split the exclusion constant. **This is the hard part, and it is a policy change.**

`brand-kit/negative.txt` today, byte-for-byte:

```
readable text, letters, words, numbers, captions, subtitles, watermark, logo, photorealism, live-action footage, 3D render, lip-sync, talking characters, color drift, repeated text, doubled text, two lines of identical text
```

HANDOFF §8 locked **exclusions are add-only** — a kit may append prohibitions,
never remove them. The diorama's signature is a letterpress label on a prop,
fenced as `No text anywhere except "<LABEL>"`. **A fence is a narrowing, and
narrowing is the one move add-only forbids.** The label is structurally
impossible without this change.

**The split Tarik approved:**

| tier | contents | may a kit change it |
|---|---|---|
| **Platform floor** (`brand-kit/floor.txt`) | photorealism · live-action footage · 3D render · lip-sync · talking characters · watermark · logo | **Never** |
| **House text default** (`negative.txt`) | readable text · letters · words · numbers · captions · subtitles · repeated/doubled text · color drift | Narrowable, under POL-4's conditions |

The floor is the harms POL-1 and POL-3 exist for. Nothing relaxes those.

**A kit narrows the text default only by inheriting POL-4's existing
conditions** — which already permit on-prop text at **≤3 elements, ≤4 words,
each mapped to an entered fact ID**. The diorama label is one element of three
words. **It has always fit the budget; what it needed was permission to be asked
for.**

```
platform_floor()      read from the kit ROOT, never a kit subdirectory —
                      that is what makes it a floor
kit negative          platform_floor() + "," + the kit's own additions
negative_is_intact()  the emitted NEGATIVE must START with platform_floor(),
                      byte-for-byte
```

Without the base/kit split a kit is compared against itself and passes
trivially. `negative_is_intact()` already accepts `base + ","` — it needs the new
source of truth, not new logic.

`policy.yaml` POL-2 and POL-4 both gain changelog entries, and **the pre-split
wording stays in the file beside the new one.** That is this repo's standing
rule — see POL-2's existing `changelog` and `voice.json`'s
`why_the_window_moved`.

### Task 10 — labels validated like claims

`ScriptBlock` gains `label: str | None`. **The script stage emits it**, beside
`narration` and `claims` — not the prompt builder, not a human. `claims.py`
validates it exactly as it validates narration: **≤4 words, and it must map to a
fact ID already entered.** A block whose label traces to nothing is rejected and
repaired at $0, before a picture is bought.

For the house kit `label` stays `None` and nothing changes.

**This is what keeps the Task 9 split honest.** The letterpress word on a prop is
held to the same standard as the sentence spoken over it. That is the only
version of "readable text is allowed here" that does not cost the product its
argument.

### Task 11 — author the diorama kit

Six files under `brand-kit/diorama/`, then `scripts/sync_brand_kit.py` (the kit
is read from **B2**, not the working copy — editing the files without syncing
does nothing) and `scripts/verify_brand_kit.py`.

Contents come from `diorama-doc.md`, **read in full**, not from this list:
style tokens verbatim; its own through-line menu built on the burnt-orange object
that escalates; the war-report narrator in `voice.json`; bold condensed sans in
`subtitle.ass`; negative additions plus the fenced label clause; and
`scene-guidance.txt` carrying the fake-oner shape, the **moderation map**, and
the 9:16 deviation note.

The house through-line menu is 6 entries with keys
`id, label, use_when, framing, silhouette, escalation, countable, lettering_risk`
— read it before authoring the diorama's, because its comments record why each
field exists.

---

## Decisions already made — do not relitigate

| | |
|---|---|
| **Aspect** | **9:16**, not the reference's 16:9. One pipeline, assembly untouched, Shorts-native. Record the deviation in `scene-guidance.txt`, **not** `style-tokens.txt` — the latter is sent to the provider verbatim, so an explanation of ourselves would ship inside the prompt. |
| **Engine** | **`seedance-1-0-pro-fast-251015` first.** It bills **$0.022 flat**; `seedance-2-0-fast-260128` bills **per second** — $5.40 for six 10s blocks against $0.13. That is 41× the video cost and 5.6× the whole run. 2.0 works now (the 401 cleared today) and is genuinely better-looking. **It is not worth 5.6× a run.** Escalate only if the look demonstrably fails on 1.0. |
| **Style reference** | The block's own still via `first_frame`, **not** image references. MOO-424: passing a style key as an image input made consistency *worse*, and `bria-fibo` accepts `reference_images` and reads none of them. The text lock is what works here. |
| **Labels** | Emitted by the script stage, validated by `claims.py`, must trace to a fact. |

---

## The guard that matters most, from Phase 1

Thirteen defects were caught during Phase 1. They share **one** cause:

> **The code was written against the shape of the data in the test, and the
> fixture was chosen because it made the test pass.**

One instance survived into merged code and is why the end card was cut:
`Path(final["uri"])` against an `https://` URL.

**The rule:**

> When a value crosses from one module to another, the test must supply what the
> **producing** module actually produces — traced to the line that writes it.
> Otherwise the test proves only that the two halves agree with the fixture.

**And the harder lesson.** A reviewer hand-traced ffmpeg's drawtext escaping
against the **official documentation**, cited it, and concluded in writing that
it was correct. It was wrong — the docs did not match the build, and the "fixed"
code was silently burning the filter string into the visible frame. No review
caught it. **Rendering a frame and reading it did.**

For Phase 2 this is not optional: the diorama is judged entirely by eye. Use the
source's own VERIFY step — pull a frame from each clip, confirm every scene reads
as newsprint with **exactly one** orange accent, confirm each label rendered
correctly and is not misspelled, confirm the through-line object appears six
times. Fix and re-render before delivering.

**Tell every implementer that finding defects in its own brief is wanted**, and
that a test which would still pass with its target behaviour deleted is
decoration. That instruction is why Phase 1's later tasks each caught their own.

---

## Operational notes that will otherwise cost you time

- **Subagents commit their work but their final messages frequently do not
  arrive.** After each idle notification, check `git log` and the report file
  directly. Instruct reviewers to deliver via `SendMessage` to `team-lead` —
  that path works.
- Never run two implementer subagents on overlapping files. A read-only reviewer
  alongside an implementer touching different files is fine.
- **This Mac CAN reach GMI now** — the Cloudflare 1010 block cleared today.
  `curl` before routing diagnosis through the Fly worker.
- **`fly deploy` runs from the repo root, not `api/`.**
- The system `ffmpeg` on PATH has **no `drawtext` filter**; only
  `/opt/homebrew/opt/ffmpeg-full` does. `resolve_ffmpeg(needs_subtitles=False)`
  checks only for `subtitles`, so it will hand you a binary that cannot draw
  text. Known, unfixed, filed.
- GMI credits: Tarik added $15 today. A `402` at submit is a free balance probe;
  there is no API-readable balance endpoint. A run costs **≈ $0.98** in GMI
  credits, so that is roughly 15 videos.

## Unfinished from Phase 1, if you have spare time

- **`suggest_through_line` has no caller** and `through-lines.yaml` stores a
  *list* where the function takes a *dict* keyed by id. Needs
  `menu_from_kit(doc) -> dict` plus a caller. **Phase 2 touches this exact area**
  — closing it while you are in the kit code is cheap.
- The end card is cut and inert; `docs/HANDOFF-pre-demo-features.md` records
  exactly what finishing it requires.
- **`main` is 26 commits ahead of origin and unpushed.**

## If time runs out

Cut in this order, and **say the word "cut" out loud** with the criterion
dropped, per the mandate at the top of `docs/HANDOFF.md`:

1. Task 12, the authoring interview — already deferred, no loss.
2. Task 11's polish — ship the kit with fewer render iterations, and say the look
   is unproven rather than implying it was verified.
3. **The whole of Phase 2**, and pick it up after submission.
