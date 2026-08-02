# Four pre-demo features — design

**Date:** 2026-08-02 · **Status:** approved, unimplemented
**Sources read before designing** (per `CLAUDE.md`, in full, not summarised):
`~/Downloads/vox_style_caption_guide.md` ·
`~/.claude/skills/vox-motion-graphics/references/diorama-doc.md` ·
`~/.claude/skills/vox-motion-graphics/references/vox-prompts.md` ·
`brand-kit/through-lines.yaml` · `brand-kit/negative.txt` · `policy/policy.yaml` ·
`api/newsdesk/{blockprompt,brandkit,assembly}.py`

Four features were requested before the demo:

1. Social captions for LinkedIn / YouTube Shorts, generated after the video
2. Customisable brand kit — a through-line the user can pick or author
3. A second art direction: the **paper-diorama documentary**
4. A brand-image end card with an optional website URL

## The finding that shaped everything: 2 and 3 are one feature

The paper-diorama style **is** a second brand kit — a different exclusion line,
different style tokens, a different through-line menu, and, decisively, a
different narrator. That is the multi-outlet brand-kit feature paused mid-design
with five decisions already locked (`docs/HANDOFF.md` §8). Feature 3 is feature
2's first real consumer, which is the best possible way to build it: a second
implementation is what proves an abstraction, and this one exists already.

## What the pasted brief dropped, and the real source carries

The request paraphrased the diorama style from memory. `diorama-doc.md` carries
three things the paraphrase did not, all of them expensive to rediscover:

- **The engine is `seedance_2_0`**, `genre: noir`, `generate_audio: true`. On
  2026-08-02 seedance 2.0 was proven reachable on GMI for the first time since
  July — and priced **per second**, $5.40 for six 10s clips against
  `seedance-1-0-pro-fast`'s $0.13 flat.
- **A moderation map.** Named politicians submit fine and die at render. "Mushroom
  cloud" trips an NSFW flag. Close-up statesman faces fail on seedance and render
  on the fallback. Censor bars over eyes both sell the look and defuse likeness.
- **The fake-oner prompt shape** and the exact STYLE token line.

Any of the three, re-derived from prose, would have cost a render cycle.

---

## Decisions taken

| # | Question | Decision |
|---|---|---|
| 1 | Diorama aspect ratio | **9:16**, forced. One pipeline, assembly untouched. The kit records that it deviates from its 16:9 reference deliberately. |
| 2 | What "customisable through-line" means | **Suggest first, author later.** Model recommends from the existing menu; the interview-authoring path is specified here and built after. |
| 3 | Do captions get governed | **Generated, then claim-validated.** Same tracing rule as a script block. |
| 4 | End-card posture | **Chrome, declared.** No gate; the manifest records it as supplied by a human and not generated. |
| 5 | Architecture | **Second kit, own B2 prefix.** Not a style variant, not a hardcoded constant. |
| 6 | The exclusion line | **Split** into an immutable platform floor and a narrowable house text default. |

---

## Section 1 — Kit resolution

**No migration.** B2 keys are flat, so `kit/negative.txt` and
`kit/diorama/negative.txt` coexist. The existing kit never moves and never
re-syncs.

```
kit_prefix(kit_id) → "kit/"              when kit_id is None or "house"
                   → f"kit/{kit_id}/"    otherwise
```

`brandkit.load(kit_id="house")`. One parameter.

The story file gains one field, defaulting to today's behaviour:

```yaml
id: the-65-000-pipes-under-milwaukee
kit: house          # or: diorama
through_line: fuse
```

An unknown kit id is refused at **Wall 1** — 422 at the door, no run created,
nothing spent. Kit resolution happens before any provider is constructed, so a
bad kit id costs $0.

### What travels with a kit, and why each file must

| file | why per-kit |
|---|---|
| `negative.txt` | additions only; the floor is fixed (see Section 2) |
| `style-tokens.txt` | sepia newsprint vs warm-cream collage |
| `scene-guidance.txt` | the diorama's rules are not the collage's |
| `through-lines.yaml` | its own menu — the burnt-orange object |
| `voice.json` | **why a style variant inside one kit cannot work** — the diorama narrator reads a war report |
| `subtitle.ass` | bold condensed sans vs Anton |

A kit missing any of its six files raises `BrandKitError` and is never
substituted with a default. Existing rule, unchanged.

---

## Section 2 — The diorama kit, and the constant split

### The conflict

`brand-kit/negative.txt`, byte-for-byte:

```
readable text, letters, words, numbers, captions, subtitles, watermark, logo,
photorealism, live-action footage, 3D render, lip-sync, talking characters,
color drift, repeated text, doubled text, two lines of identical text
```

HANDOFF §8 decision 2: **exclusions are add-only** — a kit may append
prohibitions, never remove them. The diorama's signature is a letterpress label
on a prop, fenced as `No text anywhere except "<LABEL>"`. That is a *narrowing*,
and narrowing is the one move add-only forbids. **The label is structurally
impossible under the architecture of Section 1.**

Granting the kit a blanket override would turn the exclusion line back into a
suggestion, which is the exact sentence POL-2 exists to prevent.

### The split

| tier | contents | may a kit change it |
|---|---|---|
| **Platform floor** | photorealism · live-action footage · 3D render · lip-sync · talking characters · watermark · logo | **Never** |
| **House text default** | readable text · letters · words · numbers · captions · subtitles · repeated/doubled text | Narrowable, under conditions |

The floor is the set of harms POL-1 and POL-3 exist for: a frame mistakable for
a camera, or for a real person. Nothing relaxes those.

The text half is different, and POL-4 already says why the harm is bounded:
*"Words rendered inside a frame read as quotation. AI lettering also garbles,
which turns a garbled word into an apparent misquote."* That rule **already**
permits on-prop text — at most **three text elements per scene, at most four
words each, and any on-prop text must map to an entered fact ID**. A diorama
label is one element of three words. It has always fit inside the budget.

**A kit narrows the text default only by inheriting POL-4's conditions:** a
single fenced label, within the element budget, **mapped to a fact**. A label
that traces to nothing is refused exactly like a block that traces to nothing.

### Who writes the label

**The script stage does, as a per-block field beside `narration` and `claims`** —
not the prompt builder, and not a human. The label is a claim in three words, so
it belongs where claims are made and validated.

`ScriptBlock` gains `label: str | None`. For a kit whose text default is
narrowed, the generator is asked for one label per block, and `claims.py`
validates it exactly as it validates narration: **≤4 words, and it must map to a
fact ID already entered.** A block whose label traces to nothing is rejected and
repaired like any other untraced claim, at $0, before a picture is bought.

For the house kit, `label` stays `None` and nothing changes.

This is what keeps the narrowing honest. The letterpress word on a prop is held
to the same standard as the sentence spoken over it, which is the only version of
"we allow readable text here" that does not cost the product its argument.

### POL-2 enforcement after the split

```
platform_floor()      read from a path an outlet cannot write (baked into the
                      image, as negative.txt is today)
kit negative          platform_floor() + "," + the kit's own additions
negative_is_intact()  the emitted NEGATIVE must START with platform_floor(),
                      byte-for-byte, before any addition
```

Without the base/kit split a kit is compared against itself and always passes.
`negative_is_intact()` already accepts `base + ","`, so the check needs the new
source of truth, not new logic.

`policy.yaml` POL-2 and POL-4 both gain a changelog entry. Per the standing
rule, **the pre-split wording stays in the file next to the new one** — the same
treatment POL-2 v2 and `voice.json`'s `why_the_window_moved` already get.

### Kit contents, from `diorama-doc.md`

- **style-tokens** — the source's STYLE line verbatim: cinematic vintage paper
  diorama, aged sepia newsprint world, monochrome halftone print, archival cutout
  figures with black censor bars, single burnt-orange accent, distressed
  letterpress, warm tungsten light, macro tilt-shift, film grain, handcrafted
  stop-motion paper feel, non-photorealistic, no live-action
- **through-lines** — its own menu, built on the burnt-orange object that rides
  through all six blocks and escalates. Same schema as the house menu:
  `framing`, `silhouette`, `escalation`, `countable`, `lettering_risk`,
  `surface` — and here, additionally, `label` guidance
- **voice.json** — deep, measured documentary narrator; 9–10.5s per line
- **subtitle.ass** — bold condensed sans
- **negative** — floor + `bright saturated colors`, `color photography` + the
  fenced label clause
- **scene-guidance** — the fake-oner shape (one continuous FPV move, every
  boundary hidden in motion blur, one impact moment every ~3s, ends
  motion-blurred) **and the moderation map**, which belongs in the kit rather
  than in anyone's memory

### Deviations from the reference, recorded on purpose

Recorded in the diorama kit's **`scene-guidance.txt`**, which is guidance for
prompt authors rather than a wire payload — `style-tokens.txt` is sent to the
provider verbatim, so a note explaining ourselves would end up in the prompt.

| reference says | we do | why |
|---|---|---|
| 16:9 | **9:16** | Decision 1. One pipeline, Shorts-native. |
| `seedance_2_0` | **`seedance-1-0-pro-fast-251015` first** | 2.0 bills per second: $5.40/run vs $0.13. Escalate only if the look demonstrably fails. |
| style key + prop assets as `image_references` | the block's own **still via `first_frame`** | MOO-424: passing a style key as an image input made consistency *worse*; `bria-fibo` accepts `reference_images` and reads none of them. The text lock is what works here. |

---

## Section 3 — Caption generator

**New module `caption.py`, new resumable stage `caption`, running after
`assembly`.** `--only caption` re-runs for cents.

**The guide covers Instagram Reels and YouTube Shorts, not LinkedIn.** Its
Instagram shape — *"a short editorial abstract from a magazine"* — is the closest
register and is what LinkedIn adapts from. This is an adaptation, and is labelled
as one rather than presented as prescribed.

**Both platforms every run, two options each — four captions.** No platform
picker, no extra wizard step; the human picks from what is there. Four short
generations cost about $0.01 in total, which is cheaper than the UI that would
save half of them.

### The line between assembled and generated

| assembled, never generated | generated, then validated |
|---|---|
| **the Sources block** — real URLs copied from the story file | hook, body, twist tease, CTA |
| `#Shorts`, appended for YouTube | the other 3–4 hashtags |
| character budgets, hashtag count enforcement | |

**A model must never write a citation.** The guide asks for a Sources section
because it *"adds immense credibility"* — which is precisely why it cannot be
generated. The real URLs already exist in the story file; they are copied.

### Validation

Every claim in the caption runs `claims.py`'s tracing rule. The guide instructs
the caption to *"lead with the surprising number"*, so the hook is a claim by
construction: it traces or the caption is refused and repaired, like a script.

Deterministic pre-checks, before any model output is trusted: hook fits 125 (IG)
/ 150 (YT) characters before truncation · exactly 3–5 hashtags · `#Shorts`
present for YouTube · no all-caps, no exclamation runs, zero emoji — the guide is
explicit that shouting breaks the sepia aesthetic.

The through-line object is handed to the prompt from the kit rather than guessed,
so the caption can use it as metaphor as the guide asks.

**The fourth `chat()` role**, routed through `judged()` like the other three — a
refused caption lands in the ledger beside a refused script. ~$0.01 a run.

**Failure rule:** a caption that cannot be made to trace within its repair passes
is returned as **no caption**, with the reason in the ledger — never as a caption
with a warning attached. `script.py`'s rule, for its stated reason: a warning is
something a tired editor clicks past at eleven at night.

Surfaces on the Receipt with copy buttons, and in the run manifest.

---

## Section 4 — End card

**Duration is 2.5s, matching `assembly.BED_FADE_OUT_S`**, which already exists.
Today the bed fades out under the last narration; with the card the fade resolves
*on* the card. Better than current behaviour, at no cost, because the constant is
already the right length.

```
upload image + optional URL  →  runs/<run_id>/endcard.png (private bucket)
                             →  assembly appends a 2.5s card
                             →  manifest records it SUPPLIED, not generated
```

**Composited, not generated — and that is the whole POL-4 answer.** The URL is
drawn by ffmpeg from the typed string. No model touches it, so it cannot garble,
and a garbled word read as a misquote is the entire harm POL-4 names. Generated
text and composited text are different things; the distinction is stated once
here so it is not re-argued later.

**Validated at the door** (never trust external data): the image must decode as
an image, is size- and dimension-capped; the URL must parse and is length-capped.
Both refused at upload with a named reason, before a run exists.

```json
"end_card": { "image": "b2://…/endcard.png", "url": "radiomilwaukee.org",
              "supplied_by": "Tarik Moody", "generated": false }
```

The Receipt renders it as supplied by a human, not made by a model — the one
frame no model produced is the frame the receipt is loudest about.

**If the end-card image is missing or will not decode at assembly time, assembly
refuses.** It does not quietly render without it. A silently dropped end card
means a publisher believes their brand shipped on a video where it did not, and
learns otherwise from someone else.

Layout follows the kit: the kit's ground colour behind the logo, the kit's
subtitle font for the URL. No extra asset per kit.

---

## Section 5 — Through-line suggestion

**The suggestion picks from the menu; it never writes one.** The model returns an
**id**, and an id outside the kit's menu is refused rather than coerced. No free
text reaches a prompt, so `through-lines.yaml`'s stated property holds: *"The menu
IS the policy boundary. A journalist picks a label and a meaning — they never
write framing language."*

The menu was already built for this. Every entry carries a `use_when`
(`fuse` — *"A deadline, a countdown, an inevitability"*). The prompt is: here are
the facts, here are the ids and their `use_when`, pick one and say why in one
line.

**Its own `judged()` decision**, so the receipt can record *why this through-line*
— the art-direction choice joins the provenance record instead of being an
unexplained menu click. ~$0.002.

**Trap to avoid**, from HANDOFF's dead-assumption list item 5: a dict default does
not fire on an empty value. A suggestion returning `""` must fall through to
no-suggestion, not to menu item zero. Use `or`, and validate membership.

### The authoring path (specified, built after)

HANDOFF §8 decision 3: **interview → AI drafts → human publishes**, the same shape
as Wall 1. The user describes an object in plain language; the model drafts the
full entry — `framing`, `silhouette`, `escalation`, `countable`, `surface` — which
then passes the same gate every block prompt passes before it can be used, and a
human publishes it.

This path is why the boundary matters. `through-lines.yaml` records that
`dollar-cut` once read *"labelled paper strips"* — **a POL-4 violation written into
the menu by its own authors.** If experts put a violation in there, a journalist
authoring one at 11pm will too. The draft is gated, never trusted.

Per §8 decision 5, an authored kit is **baked at publish**: layers flatten into an
immutable versioned kit in B2. A run cannot edit its own style.

---

## Testing

Conventions, not values:

| test | what it protects |
|---|---|
| every kit carries all six required files | a kit is not a kit without them |
| every kit's negative **starts with** the platform floor | the whole POL-2 argument; fails loudly if anyone narrows the floor |
| a diorama label is ≤3 words, ≤3 elements, and maps to a fact id | the narrowing stays gated |
| a caption source URL absent from the story file is refused | a model must never write a citation |
| a caption claim that does not trace is refused, not warned | matches `script.py` |
| a suggested through-line id outside the menu is refused | the menu stays the boundary |
| assembly refuses a missing or undecodable end-card image | silence would mislead the publisher |
| `gate.py` still imports nothing network-capable | `test_structure.py`, unchanged |

Every test stays at $0 with no network, the property the suite already has.

---

## Build order

1, 2 and 3 depend on nothing and may land in any order.

| # | feature | depends on |
|---|---|---|
| 1 | Caption stage | — |
| 2 | End card | — |
| 3 | Through-line suggestion | — |
| 4 | Kit resolution + constant split | — |
| 5 | Diorama kit | 4 |
| 6 | Through-line authoring interview | 4 |

**Sizing, honestly.** 1–3 are comfortable in an afternoon. 4–5 are the real work,
and 5 needs render iterations that can only be judged by looking at frames. If
time runs out mid-list it runs out with working features behind it rather than a
half-built kit system.

**Verification for the diorama, from the source's own VERIFY step:** pull a frame
from each clip; confirm every scene reads as newsprint with exactly one orange
accent; confirm each label rendered correctly on a prop and is not misspelled;
confirm the through-line object appears six times. Fix and re-render before
delivering. This matches the standing rule in `CLAUDE.md` — verify against real
output, several bugs here were invisible to tests and obvious in a screenshot.

## Open questions

- **Does the diorama look survive on `seedance-1-0-pro-fast`?** Unknown until
  rendered. The answer decides whether the style costs $0.13 or $5.40 a run.
- **Instagram Reels** is in the caption guide and was not requested. The module
  should not be built in a way that makes adding it a rewrite.
