# Four Pre-Demo Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship social captions, a branded end card, a through-line suggestion, and a second paper-diorama art direction, without weakening the governance argument any of them touch.

**Architecture:** Phase 1 (Tasks 1–7) adds three independent features that touch no existing behaviour — a new `caption` stage after assembly, an end-card segment concatenated after mastering, and an art-direction suggestion that returns a menu id. Phase 2 (Tasks 8–13) generalises the brand kit into a keyed prefix, splits the POL-2 exclusion constant into an immutable floor and a narrowable text default, and authors the diorama kit against it.

**Tech Stack:** Python 3.12 · `uv` · pytest · genblaze on GMICloud · ffmpeg/ffprobe · Backblaze B2 · Next.js 15.5.22 web

**Spec:** `docs/superpowers/specs/2026-08-02-pre-demo-features-design.md`

## Global Constraints

- **`gate.py` must never import anything network-capable.** `tests/test_structure.py` walks its import graph. This is what makes "$0 spent on a refusal" structural.
- **The whole suite stays at $0 with no network.** Every test injects a fake `chat_fn` or a fixture. No test may reach a provider.
- **Immutability.** Every dataclass in `newsdesk/` is `@dataclass(frozen=True)`. Return new objects with `dataclasses.replace`; never mutate.
- **Aspect ratio is 9:16 everywhere.** `blocks.ASPECT_RATIO = "9:16"`, delivery is 1080×1920. The diorama kit does not change this.
- **Exclusions are add-only.** A kit may append prohibitions, never remove them, except through the Phase 2 split, and then only under POL-4's conditions.
- **A model must never write a citation.** Source URLs are copied from the story file, never generated.
- **Refuse, never warn.** Anything that cannot be made to trace is returned as absent, with the reason in the ledger. Never as content with a warning attached.
- **No new dependencies.** Use the stdlib, or `ffprobe`, which `assembly.py` already requires.
- **Commit messages:** conventional commits (`feat:`, `fix:`, `docs:`, `test:`). No `Co-Authored-By` trailer — this repo carries none.
- **Run tests with:** `cd api && uv run pytest tests/ -q`

## Deliberate cut, named

The spec says the music bed's 2.5s fade-out should resolve **on** the end card. This plan concatenates the end card as a separately-encoded segment **after** mastering instead, which leaves `build_filtergraph()` and `render()` untouched. **The cut is: the bed still fades under the last narration, and the card holds in silence.** The criterion dropped is "music lands on the logo."

Reason: moving the fade means editing the filtergraph, which is the file that produced the `0.0 LUFS` / `-inf dBFS` defect and the ffmpeg-5.1 `framelog` failure. On a deadline that is the wrong file to open for a refinement. Task 7b records the follow-up.

## File Structure

| File | Responsibility |
|---|---|
| `api/newsdesk/caption.py` | **create** — Caption model, deterministic checks, source assembly, generation + claim validation |
| `api/newsdesk/artdirection.py` | **create** — through-line suggestion; returns a menu id or None |
| `api/newsdesk/endcard.py` | **create** — upload validation (ffprobe), card rendering, concat |
| `api/newsdesk/pipeline.py` | **modify** — `STAGES` gains `endcard` and `caption`; new `stage_endcard` and `stage_caption`. **There is no `stage_assembly`** — the cut lives in `api/scripts/run_cs1_assemble.py` and is not to be edited |
| `api/newsdesk/cli.py` | **modify** — dispatch `caption` |
| `api/newsdesk/brandkit.py` | **modify** — `kit_prefix(kit_id)`, `load(kit_id=...)` |
| `api/newsdesk/blockprompt.py` | **modify** — `platform_floor()`, `negative_is_intact()` against the floor |
| `api/newsdesk/claims.py` | **modify** — `ScriptBlock.label`, label validation |
| `api/newsdesk/storyfile.py` | **modify** — `kit:` field, refused at Wall 1 |
| `policy/policy.yaml` | **modify** — POL-2 and POL-4 changelog entries, old wording retained |
| `brand-kit/floor.txt` | **create** — the immutable platform exclusion floor |
| `brand-kit/diorama/*` | **create** — the six kit files |
| `api/tests/test_caption.py`, `test_endcard.py`, `test_artdirection.py`, `test_kits.py` | **create** |

---

# PHASE 1 — independent, shippable alone

Nothing in Phase 1 changes existing behaviour. If work stops after Task 7, three features ship and the kit system is untouched.

---

### Task 1: Caption model and deterministic checks

**Files:**
- Create: `api/newsdesk/caption.py`
- Test: `api/tests/test_caption.py`

**Interfaces:**
- Consumes: `newsdesk.facts.Story`, `newsdesk.claims.Claim`
- Produces: `Caption` dataclass · `HOOK_LIMIT: dict[str,int]` · `sources_for(story: Story) -> tuple[str, ...]` · `caption_problems(c: Caption) -> tuple[str, ...]`

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_caption.py
"""Caption generation and the checks that run before any model output is trusted.

Every test injects a fake chat_fn or builds a Caption by hand. Nothing here
reaches a provider, so the suite stays at $0 with no network.
"""
from __future__ import annotations

import pytest
from fixtures import cs1_story

from newsdesk.caption import (
    HOOK_LIMIT,
    Caption,
    caption_problems,
    sources_for,
)


def _caption(**over) -> Caption:
    base = dict(
        platform="youtube",
        variant=1,
        hook="Milwaukee has sixty-five thousand lead pipes and a 2037 deadline.",
        body="The city replaced roughly three thousand three hundred lines in 2025.",
        cta="Subscribe for more data-driven explainers.",
        hashtags=("#Infrastructure", "#PublicHealth", "#Shorts"),
        sources=("https://dailyreporter.com/2026/05/06/",),
    )
    base.update(over)
    return Caption(**base)


def test_a_clean_youtube_caption_has_no_problems():
    assert caption_problems(_caption()) == ()


def test_a_hook_past_the_platform_limit_is_a_problem():
    """The hook is the search snippet. Past the limit it truncates mid-sentence."""
    long_hook = "x" * (HOOK_LIMIT["youtube"] + 1)
    problems = caption_problems(_caption(hook=long_hook))
    assert any("hook" in p for p in problems)


def test_youtube_without_the_shorts_tag_is_a_problem():
    """The guide is explicit: #Shorts signals categorisation to the algorithm."""
    problems = caption_problems(_caption(hashtags=("#A", "#B", "#C")))
    assert any("#Shorts" in p for p in problems)


def test_linkedin_does_not_require_the_shorts_tag():
    c = _caption(platform="linkedin", hashtags=("#A", "#B", "#C"))
    assert caption_problems(c) == ()


@pytest.mark.parametrize("tags", [("#A", "#B"), ("#A", "#B", "#C", "#D", "#E", "#F")])
def test_hashtag_count_outside_three_to_five_is_a_problem(tags):
    """The guide treats hashtags as category labels, not reach boosters."""
    problems = caption_problems(_caption(platform="linkedin", hashtags=tags))
    assert any("hashtag" in p for p in problems)


def test_shouting_is_a_problem():
    """All-caps and exclamation runs break the sepia aesthetic the guide protects."""
    assert any("caps" in p for p in caption_problems(_caption(body="THIS IS URGENT")))
    assert any("exclamation" in p for p in caption_problems(_caption(body="Wow!!")))


def test_emoji_are_a_problem():
    assert any("emoji" in p for p in caption_problems(_caption(body="Big news 🚨")))


def test_sources_come_from_the_story_verbatim():
    """A model must never write a citation. These are copied, not composed.

    Asserted against the fixture's own values rather than a shape test — a
    check that only asks "does it look like a URL" would pass on an invented
    one, which is the single thing this function exists to prevent.
    """
    story = cs1_story()
    expected = tuple(
        dict.fromkeys(s.value for f in story.facts for s in f.sources)
    )
    assert sources_for(story) == expected
    assert len(expected) == len(set(expected)), "deduped, order preserved"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_caption.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'newsdesk.caption'`

- [ ] **Step 3: Write the implementation**

```python
# api/newsdesk/caption.py
"""Social captions for a finished run, held to the same standard as the script.

The caption guide asks a caption to "lead with the surprising number" and to
carry a Sources section. Both are claims leaving the building, which is why
this module reuses claims.py rather than trusting prose: a caption that says a
number the facts do not support is the same failure as a block that does, on a
surface nobody was checking.

The Sources block is assembled, never generated. The guide wants sources
because they "add immense credibility" — which is exactly why a model cannot
be the one to write them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from newsdesk.claims import Claim
from newsdesk.facts import Story

PLATFORMS = ("linkedin", "youtube")

# Characters visible before the platform truncates. The hook has to land whole
# inside this or the surprising number is cut off mid-sentence, which is the one
# thing the guide says must not happen.
HOOK_LIMIT = {"linkedin": 125, "youtube": 150}

MIN_HASHTAGS = 3
MAX_HASHTAGS = 5

# YouTube only. The guide: "You must include #Shorts as one of these tags to
# signal proper categorisation to the algorithm."
REQUIRED_TAG = {"youtube": "#Shorts"}

_ALL_CAPS_RE = re.compile(r"\b[A-Z]{4,}\b")
_EXCLAIM_RUN_RE = re.compile(r"!\s*!|!.*!", re.DOTALL)
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)


@dataclass(frozen=True)
class Caption:
    """One option for one platform. Immutable; a run cannot edit its own caption."""

    platform: str
    variant: int
    hook: str
    body: str
    cta: str
    hashtags: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    claims: tuple[Claim, ...] = field(default_factory=tuple)

    @property
    def prose(self) -> str:
        """The claim-bearing text. Hashtags and sources are not prose and are
        not generated, so they are excluded from tracing."""
        return f"{self.hook}\n\n{self.body}\n\n{self.cta}"

    @property
    def text(self) -> str:
        parts = [self.hook, self.body, self.cta]
        if self.sources:
            parts.append("Sources:\n" + "\n".join(f"- {s}" for s in self.sources))
        if self.hashtags:
            parts.append(" ".join(self.hashtags))
        return "\n\n".join(parts)


def sources_for(story: Story) -> tuple[str, ...]:
    """Every source in the story, deduped, order preserved.

    Copied verbatim. Nothing here is generated and nothing may be added later:
    a caption source that is not in this tuple is refused.
    """
    seen: list[str] = []
    for fact in story.facts:
        for source in fact.sources:
            if source.value not in seen:
                seen.append(source.value)
    return tuple(seen)


def caption_problems(c: Caption) -> tuple[str, ...]:
    """Deterministic checks. Run before any model output is trusted, and free."""
    problems: list[str] = []

    limit = HOOK_LIMIT.get(c.platform)
    if limit is None:
        problems.append(f"unknown platform '{c.platform}'")
    elif len(c.hook) > limit:
        problems.append(
            f"hook is {len(c.hook)} characters; {c.platform} truncates at {limit}"
        )

    if not MIN_HASHTAGS <= len(c.hashtags) <= MAX_HASHTAGS:
        problems.append(
            f"{len(c.hashtags)} hashtags; the guide asks for "
            f"{MIN_HASHTAGS}-{MAX_HASHTAGS}"
        )

    required = REQUIRED_TAG.get(c.platform)
    if required and required not in c.hashtags:
        problems.append(f"{c.platform} captions must carry {required}")

    prose = c.prose
    if _ALL_CAPS_RE.search(prose):
        problems.append("all-caps shouting; the guide forbids it")
    if _EXCLAIM_RUN_RE.search(prose):
        problems.append("exclamation runs; the guide forbids them")
    if _EMOJI_RE.search(prose):
        problems.append("emoji; the guide keeps them at zero for this aesthetic")

    return tuple(problems)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd api && uv run pytest tests/test_caption.py -q`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add api/newsdesk/caption.py api/tests/test_caption.py
git commit -m "feat(caption): the Caption model and the checks that cost nothing

The guide's numbers, encoded: 125/150 character hooks, three to five hashtags
treated as category labels rather than reach boosters, #Shorts mandatory on
YouTube, and no shouting — all-caps and exclamation runs break the sepia
aesthetic the video spent a dollar establishing.

sources_for() copies every source out of the story and dedupes. A model must
never write a citation; the guide asks for sources precisely because they add
credibility, which is the reason generating them would be the worst possible
place to let a model improvise."
```

---

### Task 2: Caption generation with claim tracing

**Files:**
- Modify: `api/newsdesk/caption.py`
- Test: `api/tests/test_caption.py`

**Interfaces:**
- Consumes: `Caption`, `caption_problems`, `sources_for` from Task 1; `newsdesk.claims.validate_block`, `ScriptBlock`, `Claim`; `newsdesk.decisions.Ledger`, `judged`; `newsdesk.state.RunState`
- Produces: `generate_captions(state, ledger, story, blocks, *, through_line, chat_fn=None, model=None) -> tuple[RunState, Ledger, tuple[Caption, ...]]` · `CaptionError`

- [ ] **Step 1: Write the failing test**

```python
# append to api/tests/test_caption.py
import json

from newsdesk.caption import generate_captions
from newsdesk.claims import ScriptBlock
from newsdesk.decisions import Ledger
from newsdesk.state import RunState


def _run() -> RunState:
    return RunState(run_id="cap-test", story="Who pays when public radio goes dark?")


def _payload(story, *, hook=None, source=None) -> str:
    """Four captions the model would return: two per platform."""
    fact = story.facts[0]
    real_source = source or fact.sources[0].value
    out = []
    for platform in ("linkedin", "youtube"):
        for variant in (1, 2):
            tags = ["#PublicMedia", "#Budget", "#Policy"]
            if platform == "youtube":
                tags.append("#Shorts")
            out.append({
                "platform": platform,
                "variant": variant,
                "hook": hook or fact.text[:100],
                "body": "The cut lands on stations that carry the least advertising.",
                "cta": "What surprised you most? Let's discuss below.",
                "hashtags": tags,
                "sources": [real_source],
                "claims": [{"spoken": fact.text[:40], "fact_id": fact.id,
                            "evidence": fact.text}],
            })
    return json.dumps({"captions": out})


def _fake_chat(payload: str):
    def _chat(model, **kwargs):
        return type("R", (), {"text": payload})()
    return _chat


def test_four_captions_are_returned_two_per_platform():
    story = cs1_story()
    _, _, caps = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal",
        chat_fn=_fake_chat(_payload(story)),
    )
    assert len(caps) == 4
    assert {c.platform for c in caps} == {"linkedin", "youtube"}
    assert sorted(c.variant for c in caps if c.platform == "youtube") == [1, 2]


def test_a_clean_caption_records_a_pass_decision():
    story = cs1_story()
    _, ledger, _ = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal",
        chat_fn=_fake_chat(_payload(story)),
    )
    assert [d.verdict for d in ledger.decisions] == ["pass"]
    assert ledger.decisions[0].role == "caption"


def test_a_source_not_in_the_story_is_refused():
    """A model must never write a citation. This is that rule, enforced."""
    story = cs1_story()
    payload = _payload(story, source="https://invented.example/article")
    _, ledger, caps = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal",
        chat_fn=_fake_chat(payload),
    )
    assert caps == ()
    assert ledger.decisions[-1].verdict == "reject"
    assert "source" in ledger.decisions[-1].reason.lower()


def test_an_untraceable_claim_is_refused_not_warned():
    """Same rule as script.py: no caption beats a caption with a warning on it."""
    story = cs1_story()
    payload = json.loads(_payload(story))
    for c in payload["captions"]:
        c["claims"] = [{"spoken": "nine hundred trillion dollars",
                        "fact_id": story.facts[0].id, "evidence": "nothing"}]
    _, ledger, caps = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal",
        chat_fn=_fake_chat(json.dumps(payload)),
    )
    assert caps == ()
    assert ledger.decisions[-1].verdict == "reject"


def test_an_unreachable_model_records_a_reject_rather_than_passing():
    def _boom(model, **kwargs):
        raise RuntimeError("provider down")

    story = cs1_story()
    _, ledger, caps = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal", chat_fn=_boom,
    )
    assert caps == ()
    assert ledger.decisions[-1].verdict == "reject"


def test_the_prompt_names_the_through_line_object():
    """The guide asks the caption to reference the object that rides through
    all six scenes. The kit knows what it is, so it is handed over, not guessed."""
    seen = {}

    def _spy(model, **kwargs):
        seen.update(kwargs)
        return type("R", (), {"text": _payload(cs1_story())})()

    generate_captions(_run(), Ledger(), cs1_story(), (),
                      through_line="tower-signal", chat_fn=_spy)
    assert "tower-signal" in seen["prompt"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_caption.py -q -k "captions or source or claim or unreachable or through_line"`
Expected: FAIL — `ImportError: cannot import name 'generate_captions'`

- [ ] **Step 3: Write the implementation**

Append to `api/newsdesk/caption.py`:

```python
import json
from dataclasses import replace
from typing import Any, Callable

from newsdesk.claims import ScriptBlock, validate_block
from newsdesk.decisions import Ledger, judged
from newsdesk.script import MODEL, PROVIDER, TIMEOUT_S, chat
from newsdesk.state import RunState

MAX_ATTEMPTS = 3

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class CaptionError(ValueError):
    """The model did not return usable captions."""


def build_prompt(story: Story, *, through_line: str, problems: str = "") -> str:
    facts = "\n".join(f"{f.id}: {f.text}" for f in story.facts)
    repair = f"\n\nThe previous attempt was rejected:\n{problems}\n" if problems else ""
    return f"""Write social captions for a finished 60-second explainer.

STORY: {story.title}

FACTS — every claim you make must map to one of these by id:
{facts}

THROUGH-LINE OBJECT: {through_line}. The video carries this object through all
six scenes. You may reference it once as a metaphor.

Write FOUR captions: two for linkedin, two for youtube.

RULES
- The hook leads with the single most surprising real number, and must fit
  {HOOK_LIMIT['linkedin']} characters for linkedin, {HOOK_LIMIT['youtube']} for youtube.
- Short punchy sentences. Documentary tone, warm but not promotional.
- Tease the turn without giving it away.
- {MIN_HASHTAGS}-{MAX_HASHTAGS} hashtags, niche and specific, as category labels.
  youtube captions must include "#Shorts".
- No emoji. No all-caps. No exclamation runs.
- Do NOT write source URLs. Sources are attached by the system.
- Every claim you make goes in "claims" with the fact id it comes from and the
  supporting text copied verbatim from that fact.{repair}

Return JSON only:
{{"captions": [{{"platform": "linkedin", "variant": 1, "hook": "...",
  "body": "...", "cta": "...", "hashtags": ["#A"],
  "claims": [{{"spoken": "...", "fact_id": "F1", "evidence": "..."}}]}}]}}"""


def parse_captions(text: str) -> tuple[Caption, ...]:
    fenced = _FENCE_RE.search(text or "")
    raw = fenced.group(1) if fenced else (text or "")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError:
        raise CaptionError(
            f"the model did not return JSON. First 200 characters: {raw[:200]!r}"
        ) from None
    entries = doc.get("captions") or []
    if len(entries) != 4:
        raise CaptionError(f"expected 4 captions, got {len(entries)}")
    out: list[Caption] = []
    for e in entries:
        out.append(Caption(
            # `or` not a dict default: a model sending "" would otherwise pass
            # the default straight through. See HANDOFF dead assumption 5.
            platform=(e.get("platform") or "").strip().lower(),
            variant=int(e.get("variant") or 0),
            hook=(e.get("hook") or "").strip(),
            body=(e.get("body") or "").strip(),
            cta=(e.get("cta") or "").strip(),
            hashtags=tuple(t.strip() for t in (e.get("hashtags") or []) if t.strip()),
            claims=tuple(
                Claim(spoken=(c.get("spoken") or "").strip(),
                      fact_id=(c.get("fact_id") or "").strip(),
                      evidence=(c.get("evidence") or "").strip())
                for c in (e.get("claims") or [])
            ),
        ))
    return tuple(out)


def _problems(story: Story, caps: tuple[Caption, ...]) -> tuple[str, ...]:
    """Deterministic checks, then the same tracing rule the script runs."""
    allowed = set(sources_for(story))
    found: list[str] = []
    for c in caps:
        found.extend(f"{c.platform}/{c.variant}: {p}" for p in caption_problems(c))
        for s in c.sources:
            if s not in allowed:
                found.append(
                    f"{c.platform}/{c.variant}: source {s!r} is not in the story. "
                    "Sources are copied from the facts, never written."
                )
        for problem in validate_block(
            story, ScriptBlock(n=c.variant, narration=c.prose, claims=c.claims)
        ):
            found.append(f"{c.platform}/{c.variant}: {problem.message}")
    return tuple(found)


def generate_captions(
    state: RunState,
    ledger: Ledger,
    story: Story,
    blocks: tuple[Any, ...] = (),
    *,
    through_line: str,
    chat_fn: Callable[..., Any] | None = None,
    model: str | None = None,
) -> tuple[RunState, Ledger, tuple[Caption, ...]]:
    """Four captions, or none. Never four captions with a warning attached."""
    chat_fn = chat_fn or chat
    model = model or MODEL
    attached = sources_for(story)
    accepted: tuple[Caption, ...] = ()
    problems = ""

    def _call() -> tuple[str, str, str]:
        nonlocal accepted, problems
        for _ in range(MAX_ATTEMPTS):
            ask = build_prompt(story, through_line=through_line, problems=problems)
            response = chat_fn(model, prompt=ask, temperature=0.4,
                              max_tokens=2000, timeout=TIMEOUT_S)
            raw = getattr(response, "text", "") or ""
            caps = parse_captions(raw)
            # Sources are attached here, not taken from the model. A model that
            # sent them anyway is caught by _problems and the run is refused —
            # silently overwriting them would hide a model doing the one thing
            # it was told never to do.
            model_sources = tuple(
                s for c in caps for s in getattr(c, "sources", ()) or ()
            )
            # `replace`, per the immutability constraint — never __dict__ splat.
            caps = tuple(
                replace(c, sources=model_sources or attached) for c in caps
            )
            found = _problems(story, caps)
            if not found:
                accepted = tuple(replace(c, sources=attached) for c in caps)
                return "pass", f"{len(accepted)} captions, every claim traced", raw
            problems = "\n".join(found)
        return "reject", problems, ""

    state, ledger = judged(
        state, ledger, role="caption", model=model, provider=PROVIDER, call=_call
    )
    return state, ledger, accepted
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd api && uv run pytest tests/test_caption.py -q`
Expected: PASS, 15 tests

- [ ] **Step 5: Run the whole suite for regressions**

Run: `cd api && uv run pytest tests/ -q`
Expected: PASS, 345 + 15 = 360

- [ ] **Step 6: Commit**

```bash
git add api/newsdesk/caption.py api/tests/test_caption.py
git commit -m "feat(caption): captions trace like blocks, or they do not ship

The guide tells a caption to lead with the surprising number, which makes the
hook a claim by construction. So the caption runs the same validate_block the
script runs — a caption asserting something the facts do not support is the
Day 4 defect on a surface nobody was watching.

The source rule is enforced rather than assumed. A model that writes a URL is
not silently corrected; the run is refused and the ledger says why. Silently
replacing an invented citation with a real one would hide a model doing the one
thing it was explicitly told not to do, and hiding it is how you find out later.

Four captions or none, never four with a warning attached — script.py's rule,
for script.py's stated reason. The fourth chat() role, through judged()."
```

---

### Task 3: The `caption` stage

**Files:**
- Modify: `api/newsdesk/pipeline.py` (`STAGES` at :57, add `stage_caption`)
- Modify: `api/newsdesk/cli.py` (:143-171 dispatch)
- Test: `api/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `generate_captions` from Task 2
- Produces: `Pipeline.stage_caption(*, chat_fn=None) -> StageResult`; `STAGES == ("script","gate","blocks","narration","assembly","caption")`; captions stored at `RunState.final["captions"]`

- [ ] **Step 1: Write the failing test**

```python
# append to api/tests/test_pipeline.py
def test_caption_is_the_last_stage():
    """After the video is done, per the request. --only caption re-runs for cents."""
    from newsdesk.pipeline import STAGES
    assert STAGES[-1] == "caption"
    assert STAGES.index("caption") > STAGES.index("assembly")


def test_caption_stage_stores_captions_on_the_run(cs2, monkeypatch):
    from newsdesk.caption import Caption

    def _fake(state, ledger, story, blocks, *, through_line, chat_fn=None, model=None):
        return state, ledger, (Caption(platform="linkedin", variant=1, hook="h",
                                       body="b", cta="c",
                                       hashtags=("#A", "#B", "#C")),)

    monkeypatch.setattr("newsdesk.pipeline.generate_captions", _fake)
    pipe = _fresh(cs2)
    result = pipe.stage_caption()
    assert result.ok
    assert pipe.state.final["captions"][0]["platform"] == "linkedin"


def test_caption_stage_is_ok_but_empty_when_nothing_traced(cs2, monkeypatch):
    """A refusal is a normal outcome, not a stage failure — the ledger carries why."""
    def _none(state, ledger, story, blocks, *, through_line, chat_fn=None, model=None):
        return state, ledger, ()

    monkeypatch.setattr("newsdesk.pipeline.generate_captions", _none)
    pipe = _fresh(cs2)
    result = pipe.stage_caption()
    assert result.ok and result.detail == "no caption traced"
    assert pipe.state.final.get("captions") == []
```

**Use the existing helpers.** `tests/test_pipeline.py` already has a `cs2`
fixture (`load_story(STORIES / "cs2.yaml")`) and `_fresh(story_file)`, which
calls **`Pipeline.start(story_file, resume=False)`**. There is no
`Pipeline.begin` and no `_story_file()` — do not invent either.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_pipeline.py -q -k caption`
Expected: FAIL — `AssertionError` on `STAGES[-1]`

- [ ] **Step 3: Write the implementation**

In `api/newsdesk/pipeline.py`:

```python
# at :57 — replace
STAGES = ("script", "gate", "blocks", "narration", "assembly", "caption")

# with the other imports
from newsdesk.caption import generate_captions

# as a new method on Pipeline, after stage_gate. Sync, like stage_script and
# stage_gate — stage_blocks and stage_narration are async, this does not need to be.
    def stage_caption(self, *, chat_fn: Callable[..., Any] | None = None) -> StageResult:
        """Social captions for a finished run. Text only — about a cent.

        Runs after assembly because the request was for captions once the video
        exists. It reads the script, not the video, so it is safe to re-run with
        `--only caption` without touching a single rendered frame.
        """
        self.state, self.ledger, caps = generate_captions(
            self.state,
            self.ledger,
            self.story_file.story,
            tuple(self.state.blocks),
            through_line=self.state.art_direction.get("through_line", ""),
            chat_fn=chat_fn,
        )
        payload = [
            {"platform": c.platform, "variant": c.variant, "hook": c.hook,
             "body": c.body, "cta": c.cta, "hashtags": list(c.hashtags),
             "sources": list(c.sources), "text": c.text}
            for c in caps
        ]
        self.state = replace(
            self.state, final={**(self.state.final or {}), "captions": payload}
        )
        self.state.save()
        return StageResult(
            name="caption",
            ok=True,
            detail=f"{len(caps)} captions" if caps else "no caption traced",
        )
```

In `api/newsdesk/cli.py`, after the `stage_narration` branch:

```python
        if stage == "caption":
            return pipe.stage_caption()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd api && uv run pytest tests/test_pipeline.py -q -k caption`
Expected: PASS, 3 tests

- [ ] **Step 5: Run the whole suite**

Run: `cd api && uv run pytest tests/ -q`
Expected: PASS, 363

- [ ] **Step 6: Commit**

```bash
git add api/newsdesk/pipeline.py api/newsdesk/cli.py api/tests/test_pipeline.py
git commit -m "feat(pipeline): a resumable caption stage after assembly

Last in STAGES, so a default run produces captions and --only caption re-runs
them for about a cent without touching a rendered frame — it reads the script,
not the video.

A refusal is StageResult(ok=True) with an empty list, not a stage failure. No
caption that traced is a normal outcome here, the same way a refused script is,
and reporting it as a crash would train whoever sees it to ignore the one signal
that matters."
```

---

### Task 4: Through-line suggestion

**Files:**
- Create: `api/newsdesk/artdirection.py`
- Test: `api/tests/test_artdirection.py`

**Interfaces:**
- Consumes: `newsdesk.facts.Story`, `newsdesk.decisions.Ledger`/`judged`, `newsdesk.state.RunState`
- Produces: `suggest_through_line(state, ledger, story, menu, *, chat_fn=None, model=None) -> tuple[RunState, Ledger, tuple[str, str] | None]`

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_artdirection.py
"""The through-line suggestion. It picks from the menu; it never writes one.

through-lines.yaml states the property this protects: "The menu IS the policy
boundary. A journalist picks a label and a meaning — they never write framing
language." A model returning free text would step straight over that line, so
the only thing it is allowed to return is an id that already exists.
"""
from __future__ import annotations

import json

from fixtures import cs1_story

from newsdesk.artdirection import suggest_through_line
from newsdesk.decisions import Ledger
from newsdesk.state import RunState

MENU = {
    "tower-signal": {"use_when": "Reach, coverage, or a service going dark."},
    "fuse": {"use_when": "A deadline, a countdown, an inevitability."},
}


def _run() -> RunState:
    return RunState(run_id="ad-test", story="Who pays when public radio goes dark?")


def _chat(payload: str):
    def _c(model, **kwargs):
        return type("R", (), {"text": payload})()
    return _c


def test_a_valid_id_is_returned_with_its_reason():
    _, _, got = suggest_through_line(
        _run(), Ledger(), cs1_story(), MENU,
        chat_fn=_chat(json.dumps({"through_line": "fuse", "why": "a deadline story"})),
    )
    assert got == ("fuse", "a deadline story")


def test_an_id_outside_the_menu_is_refused_not_coerced():
    _, ledger, got = suggest_through_line(
        _run(), Ledger(), cs1_story(), MENU,
        chat_fn=_chat(json.dumps({"through_line": "a burning pipe", "why": "x"})),
    )
    assert got is None
    assert ledger.decisions[-1].verdict == "reject"


def test_an_empty_id_falls_through_to_no_suggestion():
    """A dict default does not fire on an empty value — HANDOFF dead assumption 5.
    An empty string must become None, never menu item zero."""
    _, _, got = suggest_through_line(
        _run(), Ledger(), cs1_story(), MENU,
        chat_fn=_chat(json.dumps({"through_line": "", "why": ""})),
    )
    assert got is None


def test_an_unreachable_model_suggests_nothing_rather_than_guessing():
    def _boom(model, **kwargs):
        raise RuntimeError("provider down")

    _, ledger, got = suggest_through_line(
        _run(), Ledger(), cs1_story(), MENU, chat_fn=_boom
    )
    assert got is None
    assert ledger.decisions[-1].verdict == "reject"


def test_the_prompt_offers_every_menu_id_and_its_use_when():
    seen = {}

    def _spy(model, **kwargs):
        seen.update(kwargs)
        return type("R", (), {"text": json.dumps({"through_line": "fuse", "why": "d"})})()

    suggest_through_line(_run(), Ledger(), cs1_story(), MENU, chat_fn=_spy)
    for tid, entry in MENU.items():
        assert tid in seen["prompt"]
        assert entry["use_when"] in seen["prompt"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_artdirection.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'newsdesk.artdirection'`

- [ ] **Step 3: Write the implementation**

```python
# api/newsdesk/artdirection.py
"""Suggesting a through-line, without letting anyone author one.

through-lines.yaml is explicit about what it is: "The menu IS the policy
boundary. A journalist picks a label and a meaning — they never write framing
language, and they never learn why a tower renders as a paper cutout rather
than a photograph."

So this returns an ID or nothing. Free text never reaches a prompt. The menu's
`use_when` fields were written as human guidance and turn out to be exactly the
input this needs — whoever wrote them wrote this feature's prompt.

Routed through judged() so the receipt can record WHY a through-line was chosen.
An art-direction decision that appears in the provenance record beats an
unexplained menu click.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from newsdesk.decisions import Ledger, judged
from newsdesk.facts import Story
from newsdesk.script import MODEL, PROVIDER, TIMEOUT_S, chat
from newsdesk.state import RunState

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def build_prompt(story: Story, menu: dict[str, Any]) -> str:
    options = "\n".join(
        f"- {tid}: {(entry or {}).get('use_when', '')}" for tid, entry in menu.items()
    )
    facts = "\n".join(f"{f.id}: {f.text}" for f in story.facts)
    return f"""Choose the through-line object for this story.

STORY: {story.title}

FACTS:
{facts}

MENU — you must choose one of these ids exactly. Do not invent one:
{options}

Return JSON only: {{"through_line": "<id from the menu>", "why": "one short sentence"}}"""


def suggest_through_line(
    state: RunState,
    ledger: Ledger,
    story: Story,
    menu: dict[str, Any],
    *,
    chat_fn: Callable[..., Any] | None = None,
    model: str | None = None,
) -> tuple[RunState, Ledger, tuple[str, str] | None]:
    """(id, why) from the menu, or None. Never an id the menu does not carry."""
    chat_fn = chat_fn or chat
    model = model or MODEL
    chosen: tuple[str, str] | None = None

    def _call() -> tuple[str, str, str]:
        nonlocal chosen
        response = chat_fn(model, prompt=build_prompt(story, menu),
                          temperature=0.2, max_tokens=200, timeout=TIMEOUT_S)
        raw = getattr(response, "text", "") or ""
        fenced = _FENCE_RE.search(raw)
        doc = json.loads(fenced.group(1) if fenced else raw)
        # `or ""` rather than a dict default: a model sending "through_line": ""
        # would otherwise sail past .get()'s default. HANDOFF dead assumption 5.
        tid = (doc.get("through_line") or "").strip()
        why = (doc.get("why") or "").strip()
        if not tid:
            return "reject", "the model suggested no through-line", raw
        if tid not in menu:
            return "reject", (
                f"{tid!r} is not in the menu. The menu is the policy boundary; "
                "a suggestion outside it is refused rather than coerced."
            ), raw
        chosen = (tid, why)
        return "pass", f"{tid}: {why}", raw

    state, ledger = judged(
        state, ledger, role="art-direction", model=model, provider=PROVIDER, call=_call
    )
    return state, ledger, chosen
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd api && uv run pytest tests/test_artdirection.py -q`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
git add api/newsdesk/artdirection.py api/tests/test_artdirection.py
git commit -m "feat(artdirection): suggest a through-line by id, never by writing one

through-lines.yaml says the menu IS the policy boundary — a journalist picks a
label and never writes framing language. So the model returns an id and an id
outside the menu is refused rather than coerced to the nearest match. Coercion
would be the same bug with a friendlier face.

The use_when fields turned out to be the prompt. They were written as human
guidance months ago and needed no change to serve as model input.

Through judged(), so the receipt can say why this through-line was chosen. An
art-direction decision in the provenance record beats an unexplained click."
```

---

### Task 5: End-card upload validation

**Files:**
- Create: `api/newsdesk/endcard.py`
- Test: `api/tests/test_endcard.py`

**Interfaces:**
- Consumes: `newsdesk.assembly.AssemblyError` pattern, `ffprobe`
- Produces: `EndCardError` · `MAX_IMAGE_BYTES` · `MAX_URL_CHARS` · `probe_image(path: Path) -> tuple[int, int]` · `validate_url(raw: str) -> str` · `EndCard` dataclass

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_endcard.py
"""End-card validation. Nothing here renders; ffprobe reads a fixture.

The end card is the first frame in a Newsdesk video that no model produced.
That makes validation a trust-boundary job rather than an editorial one: the
publisher owns the content, we own refusing anything that will not decode.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from newsdesk.endcard import (
    MAX_URL_CHARS,
    EndCard,
    EndCardError,
    probe_image,
    validate_url,
)

# A 1x1 PNG, base64 rather than hex so the literal survives line wrapping.
# Smallest thing ffprobe will agree is an image.
import base64

_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def png(tmp_path: Path) -> Path:
    p = tmp_path / "logo.png"
    p.write_bytes(_PNG_1X1)
    return p


def test_a_real_image_reports_its_dimensions(png: Path):
    assert probe_image(png) == (1, 1)


def test_a_file_that_is_not_an_image_is_refused(tmp_path: Path):
    bad = tmp_path / "logo.png"
    bad.write_bytes(b"this is not a png")
    with pytest.raises(EndCardError, match="not an image"):
        probe_image(bad)


def test_a_missing_file_is_refused(tmp_path: Path):
    with pytest.raises(EndCardError, match="not an image"):
        probe_image(tmp_path / "absent.png")


@pytest.mark.parametrize("raw,expected", [
    ("radiomilwaukee.org", "radiomilwaukee.org"),
    ("https://radiomilwaukee.org", "radiomilwaukee.org"),
    ("https://radiomilwaukee.org/", "radiomilwaukee.org"),
    ("  radiomilwaukee.org  ", "radiomilwaukee.org"),
])
def test_a_url_is_normalised_to_what_a_viewer_should_read(raw, expected):
    """The card shows a domain, not a protocol. Nobody types https:// off a video."""
    assert validate_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "not a url at all", "x" * (MAX_URL_CHARS + 1)])
def test_an_unusable_url_is_refused(raw):
    with pytest.raises(EndCardError):
        validate_url(raw)


def test_an_end_card_records_that_no_model_made_it():
    card = EndCard(image_uri="b2://runs/x/endcard.png", url="radiomilwaukee.org",
                   supplied_by="Tarik Moody")
    assert card.manifest_entry()["generated"] is False
    assert card.manifest_entry()["supplied_by"] == "Tarik Moody"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_endcard.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'newsdesk.endcard'`

- [ ] **Step 3: Write the implementation**

```python
# api/newsdesk/endcard.py
"""The publisher's own mark, and the one frame no model made.

POL-1 and POL-4 govern generated frames. This one is composited: the URL is
drawn by ffmpeg from a string a human typed, so it cannot garble, and a garbled
word read as a misquote is the entire harm POL-4 names. Generated text and
composited text are different things — stated here once so it is not re-argued.

What we do owe is honesty in the record. The manifest says generated: false and
names the human who supplied it, because a receipt that accounts for every frame
except one is a receipt that misleads by omission.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 2.5s, matching assembly.BED_FADE_OUT_S. Not a coincidence and not arbitrary:
# it is the length the bed already fades over, so the two agree by construction.
DURATION_S = 2.5

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_EDGE = 4096
MAX_URL_CHARS = 100

_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)
_DOMAINISH_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}(/\S*)?$", re.IGNORECASE)


class EndCardError(ValueError):
    """The supplied image or URL cannot be used. Refused at the door."""


@dataclass(frozen=True)
class EndCard:
    image_uri: str
    url: str | None
    supplied_by: str

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "image": self.image_uri,
            "url": self.url,
            "supplied_by": self.supplied_by,
            "generated": False,
        }


def probe_image(path: Path) -> tuple[int, int]:
    """(width, height) from ffprobe. Measure, never infer — assembly's rule.

    ffprobe rather than a new dependency: assembly already requires it, and a
    header parser we wrote ourselves would be one more thing to be wrong about.
    """
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(path)],
        capture_output=True, text=True,
    )
    try:
        width, height = (int(v) for v in proc.stdout.strip().split("x")[:2])
    except (ValueError, IndexError):
        raise EndCardError(f"{path.name} is not an image ffmpeg can read") from None
    if width > MAX_IMAGE_EDGE or height > MAX_IMAGE_EDGE:
        raise EndCardError(
            f"{path.name} is {width}x{height}; the longest edge may be "
            f"{MAX_IMAGE_EDGE}px"
        )
    return width, height


def validate_bytes(data: bytes) -> None:
    if not data:
        raise EndCardError("the uploaded file is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise EndCardError(
            f"the image is {len(data) // 1024}KB; the limit is "
            f"{MAX_IMAGE_BYTES // 1024}KB"
        )


def validate_url(raw: str) -> str:
    """Normalise to the domain a viewer should read off the card.

    The protocol is dropped because nobody types https:// from a video, and a
    trailing slash reads as a typo at 1080x1920.
    """
    text = (raw or "").strip()
    if not text:
        raise EndCardError("the website is empty")
    if len(text) > MAX_URL_CHARS:
        raise EndCardError(
            f"the website is {len(text)} characters; the limit is {MAX_URL_CHARS}"
        )
    text = _SCHEME_RE.sub("", text).rstrip("/")
    if not _DOMAINISH_RE.match(text):
        raise EndCardError(f"{raw!r} does not look like a website address")
    return text
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd api && uv run pytest tests/test_endcard.py -q`
Expected: PASS, 12 tests

- [ ] **Step 5: Commit**

```bash
git add api/newsdesk/endcard.py api/tests/test_endcard.py
git commit -m "feat(endcard): validate the publisher's mark at the door

ffprobe rather than a new dependency — assembly already requires it, and a
header parser we wrote ourselves would be one more thing to be wrong about at
a trust boundary.

DURATION_S is 2.5 to match assembly.BED_FADE_OUT_S, so the two agree by
construction rather than by someone remembering.

manifest_entry() reports generated: false and names the supplier. A receipt that
accounts for every frame except one misleads by omission, and this is the only
frame in the product that no model made."
```

---

### Task 6: Render and append the end card

**Files:**
- Modify: `api/newsdesk/endcard.py`
- Test: `api/tests/test_endcard.py`

**Interfaces:**
- Consumes: `EndCard`, `DURATION_S`, `probe_image` from Task 5; `assembly.resolve_ffmpeg`, `assembly.probe_duration`
- Produces: `render_card(image, out, *, url, ffmpeg, width=1080, height=1920, ground="#F2EDE4", font=None) -> Path` · `append_card(video, card, out, *, ffmpeg) -> Path`

- [ ] **Step 1: Write the failing test**

```python
# append to api/tests/test_endcard.py
from newsdesk.endcard import DURATION_S, append_card, render_card


def test_a_rendered_card_is_the_bed_fade_long(png: Path, tmp_path: Path):
    """2.5s, because that is what the music already fades over."""
    from newsdesk.assembly import probe_duration, resolve_ffmpeg
    out = tmp_path / "card.mp4"
    render_card(png, out, url="radiomilwaukee.org", ffmpeg=resolve_ffmpeg(needs_subtitles=False))
    assert out.exists()
    assert abs(probe_duration(out) - DURATION_S) < 0.15


def test_a_rendered_card_is_the_delivery_size(png: Path, tmp_path: Path):
    from newsdesk.assembly import resolve_ffmpeg
    out = tmp_path / "card.mp4"
    render_card(png, out, url="radiomilwaukee.org", ffmpeg=resolve_ffmpeg(needs_subtitles=False))
    assert probe_image(out) == (1080, 1920)


def test_appending_extends_the_video_by_the_card(png: Path, tmp_path: Path):
    from newsdesk.assembly import probe_duration, resolve_ffmpeg
    ff = resolve_ffmpeg(needs_subtitles=False)
    card = tmp_path / "card.mp4"
    render_card(png, card, url="radiomilwaukee.org", ffmpeg=ff)
    body = tmp_path / "body.mp4"
    render_card(png, body, url="radiomilwaukee.org", ffmpeg=ff)  # stand-in body
    out = tmp_path / "final.mp4"
    append_card(body, card, out, ffmpeg=ff)
    assert abs(probe_duration(out) - (DURATION_S * 2)) < 0.3


def test_a_missing_card_refuses_rather_than_rendering_without_it(tmp_path: Path):
    """A silently dropped end card means a publisher believes their brand shipped
    on a video where it did not, and hears about it from someone else."""
    from newsdesk.assembly import resolve_ffmpeg
    with pytest.raises(EndCardError, match="not an image"):
        render_card(tmp_path / "absent.png", tmp_path / "card.mp4",
                    url="x.org", ffmpeg=resolve_ffmpeg(needs_subtitles=False))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_endcard.py -q -k "card"`
Expected: FAIL — `ImportError: cannot import name 'render_card'`

- [ ] **Step 3: Write the implementation**

Append to `api/newsdesk/endcard.py`:

```python
DELIVERY_W = 1080
DELIVERY_H = 1920

# The logo kit's paper and ink, not invented here. 816434d retuned the whole app
# onto the supplied mark: paper #f9f6ee, ink #353334, red #f2322f. A card mixing
# its own cream with the app's would read as a mistake rather than a choice —
# which is the exact reason that commit moved the app's red four degrees of hue.
DEFAULT_GROUND = "#f9f6ee"
DEFAULT_INK = "0x353334"


def render_card(
    image: Path,
    out: Path,
    *,
    url: str | None,
    ffmpeg: str,
    width: int = DELIVERY_W,
    height: int = DELIVERY_H,
    ground: str = DEFAULT_GROUND,
    font: str | None = None,
) -> Path:
    """A DURATION_S still: the logo centred on the kit's ground, URL beneath.

    Refuses on an unreadable image rather than rendering a blank card. The
    publisher must not learn from someone else that their brand did not ship.
    """
    probe_image(image)  # raises EndCardError before anything is encoded

    logo_h = int(height * 0.22)
    chain = [
        f"[1:v]scale=-1:{logo_h}:force_original_aspect_ratio=decrease[logo]",
        f"[0:v][logo]overlay=(W-w)/2:(H-h)/2-{int(height * 0.04)}[withlogo]",
    ]
    last = "withlogo"
    if url:
        draw = (
            f"[{last}]drawtext=text='{url}'"
            f":fontcolor={DEFAULT_INK}:fontsize={int(height * 0.026)}"
            f":x=(w-text_w)/2:y=h/2+{int(height * 0.10)}"
        )
        if font:
            draw += f":fontfile='{font}'"
        chain.append(f"{draw}[out]")
        last = "out"

    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-t", str(DURATION_S),
        "-i", f"color=c={ground}:s={width}x{height}:r=30",
        "-loop", "1", "-t", str(DURATION_S), "-i", str(image),
        "-f", "lavfi", "-t", str(DURATION_S), "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex", ";".join(chain),
        "-map", f"[{last}]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-t", str(DURATION_S), str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        raise EndCardError(f"end card render failed: {proc.stderr[-400:]}")
    return out


def append_card(video: Path, card: Path, out: Path, *, ffmpeg: str) -> Path:
    """Concat the card after the mastered video.

    Deliberately NOT done inside assembly's filtergraph. That file produced the
    0.0 LUFS defect and the ffmpeg-5.1 framelog failure, and it is the wrong
    file to open for a two-and-a-half second bumper. The trade is recorded in
    the plan: the bed still fades under the last narration and the card holds in
    silence, rather than the music resolving on the logo.
    """
    if not card.exists():
        raise EndCardError("the end card segment is missing; refusing to publish "
                           "a video the publisher believes is branded")
    listing = out.with_suffix(".concat.txt")
    listing.write_text(f"file '{video.resolve()}'\nfile '{card.resolve()}'\n")
    proc = subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-ar", "48000", "-ac", "2", str(out)],
        capture_output=True, text=True,
    )
    listing.unlink(missing_ok=True)
    if proc.returncode != 0 or not out.exists():
        raise EndCardError(f"end card concat failed: {proc.stderr[-400:]}")
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd api && uv run pytest tests/test_endcard.py -q`
Expected: PASS, 16 tests

- [ ] **Step 5: Look at the actual card**

This is a `CLAUDE.md` standing rule: verify against real output, several defects here were invisible to tests and obvious in one frame.

```bash
cd api && uv run python -c "
from pathlib import Path
from newsdesk.assembly import resolve_ffmpeg
from newsdesk.endcard import render_card
render_card(Path('../brand-kit/style-key.png'), Path('/tmp/card.mp4'),
            url='radiomilwaukee.org', ffmpeg=resolve_ffmpeg(needs_subtitles=False))
"
ffmpeg -y -i /tmp/card.mp4 -vframes 1 /tmp/card.png && open /tmp/card.png
```

Confirm by eye: logo centred and not stretched, URL legible at phone size, ground colour matches the kit. Fix and re-render before moving on.

- [ ] **Step 6: Commit**

```bash
git add api/newsdesk/endcard.py api/tests/test_endcard.py
git commit -m "feat(endcard): render the card and concat it after mastering

Concat rather than a filtergraph change, deliberately. build_filtergraph is the
file that produced the 0.0 LUFS reading and the ffmpeg-5.1 framelog failure, and
a two-and-a-half second bumper is not worth opening it on a deadline.

The cut that buys, named rather than buried: the bed still fades under the last
narration and the card holds in silence, instead of the music resolving on the
logo. The follow-up is recorded in the plan.

render_card probes the image before it encodes anything, so an unreadable upload
refuses instead of producing a blank card with a logo-shaped hole in it."
```

---

### Task 7: The `endcard` stage

**There is no `stage_assembly`.** The cut lives in
`api/scripts/run_cs1_assemble.py`, imported by `cli.py`, and that call site says
why: *"a working, verified path that has produced a manifest surviving
`genblaze verify` byte for byte, and a second implementation of it would be a
second thing to keep true."* **Do not edit that file.** The end card is its own
stage, running after the cut, reading what the cut published.

**Files:**
- Modify: `api/newsdesk/pipeline.py` (`STAGES` at :57; new `stage_endcard`)
- Modify: `api/newsdesk/cli.py` (dispatch)
- Test: `api/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `EndCard`, `render_card`, `append_card`, `DURATION_S` from Tasks 5–6
- Produces: `Pipeline.stage_endcard() -> StageResult` · `STAGES == ("script","gate","blocks","narration","assembly","endcard","caption")` · `RunState.final["end_card"]`

- [ ] **Step 1: Write the failing test**

```python
# append to api/tests/test_pipeline.py
def test_endcard_runs_after_assembly_and_before_caption():
    from newsdesk.pipeline import STAGES
    assert STAGES.index("assembly") < STAGES.index("endcard") < STAGES.index("caption")


def test_a_run_with_no_end_card_requested_skips_the_stage(cs2):
    """Skipped is not a detail — it is the difference between a resumed run and
    a re-rolled one. Most runs carry no logo and must not pay for a re-encode."""
    pipe = _fresh(cs2)
    result = pipe.stage_endcard()
    assert result.ok and result.skipped
    assert "end_card" not in (pipe.state.final or {})


def test_the_end_card_is_recorded_as_supplied_not_generated(cs2, monkeypatch, tmp_path):
    """The one frame no model made is the frame the receipt is loudest about."""
    published = tmp_path / "final.mp4"
    published.write_bytes(b"stub")
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"stub")

    monkeypatch.setattr("newsdesk.pipeline.render_card",
                        lambda image, out, **kw: out.write_bytes(b"card") or out)
    monkeypatch.setattr("newsdesk.pipeline.append_card",
                        lambda video, card, out, **kw: out.write_bytes(b"joined") or out)
    monkeypatch.setattr("newsdesk.pipeline._publish_branded", lambda p, run_id: "b2://x/final.mp4")

    pipe = _fresh(cs2)
    pipe.state = replace(pipe.state, final={
        "uri": str(published),
        "end_card_request": {"local_path": str(logo), "uri": "b2://x/endcard.png",
                             "url": "radiomilwaukee.org"},
    })
    pipe.state = pipe.state.approve("Tarik Moody")

    result = pipe.stage_endcard()
    assert result.ok and not result.skipped
    entry = pipe.state.final["end_card"]
    assert entry["generated"] is False
    assert entry["supplied_by"] == "Tarik Moody"
    assert entry["url"] == "radiomilwaukee.org"


def test_the_end_card_stage_refuses_an_unapproved_run(cs2, tmp_path):
    """Wall 3. Re-publishing a video is publishing; it needs a named human."""
    from newsdesk.pipeline import PipelineError

    pipe = _fresh(cs2)
    pipe.state = replace(pipe.state, final={
        "uri": str(tmp_path / "f.mp4"),
        "end_card_request": {"local_path": "x.png", "uri": "b2://x", "url": None},
    })
    with pytest.raises(PipelineError, match="approv"):
        pipe.stage_endcard()
```

Add `from dataclasses import replace` to the test file's imports if absent.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_pipeline.py -q -k endcard`
Expected: FAIL — `AttributeError: 'Pipeline' object has no attribute 'stage_endcard'`

- [ ] **Step 3: Write the implementation**

In `api/newsdesk/pipeline.py`:

```python
# at :57
STAGES = ("script", "gate", "blocks", "narration", "assembly", "endcard", "caption")

# with the other imports
from newsdesk.endcard import EndCard, append_card, render_card


def _publish_branded(path: Path, run_id: str) -> str:
    """Upload the branded cut beside the original and return its URI.

    Separate function so the test can replace it without a B2 credential; the
    stage itself must never learn how storage works.
    """
    from newsdesk.config import BUCKETS, backend

    store = backend(BUCKETS["runs"])
    key = f"{run_id}/final-branded.mp4"
    store.put(key, path.read_bytes())
    return f"b2://{BUCKETS['runs']}/{key}"


# as a new method on Pipeline, after stage_gate
    def stage_endcard(self) -> StageResult:
        """Append the publisher's mark to a published cut.

        Its own stage rather than an edit to scripts/run_cs1_assemble.py: that
        file is the verified path whose manifest survives `genblaze verify`
        byte for byte, and its own call site says a second implementation would
        be a second thing to keep true. This reads what it produced instead.
        """
        spec = (self.state.final or {}).get("end_card_request")
        if not spec:
            return self._record(StageResult(
                name="endcard", ok=True, skipped=True,
                detail="no end card requested",
            ))
        if not self.state.is_approved:
            raise PipelineError(
                "the end card re-publishes the video, and publishing needs a "
                "named human — approve the run first"
            )

        source = Path(self.state.final["uri"])
        card_mp4 = source.with_name("endcard.mp4")
        render_card(Path(spec["local_path"]), card_mp4, url=spec.get("url"),
                    ffmpeg=resolve_ffmpeg(needs_subtitles=False))
        branded = source.with_name("final-branded.mp4")
        append_card(source, card_mp4, branded,
                    ffmpeg=resolve_ffmpeg(needs_subtitles=False))

        card = EndCard(image_uri=spec["uri"], url=spec.get("url"),
                       supplied_by=self.state.approval.approver)
        self.state = replace(self.state, final={
            **(self.state.final or {}),
            "uri": _publish_branded(branded, self.state.run_id),
            "end_card": card.manifest_entry(),
        })
        # NO self.state.save() here. RunState.save() calls backend(...).put() —
        # it reaches B2 over the network, and api/.env carries live credentials,
        # so a stage that saves makes every test touching it hit the network and
        # breaks the suite's $0 / no-network guarantee. No stage method saves;
        # persistence is Pipeline.save(), called by the CLI. Found in Task 3,
        # where the same line was written into the brief and caught before merge.
        return self._record(StageResult(
            name="endcard", ok=True,
            detail=f"card appended, supplied by {card.supplied_by}",
        ))
```

Import `resolve_ffmpeg` from `newsdesk.assembly` at the top of `pipeline.py`.

In `api/newsdesk/cli.py`, beside the `caption` branch:

```python
        if stage == "endcard":
            return pipe.stage_endcard()
```

**Two more things Task 3 proved are required and easy to miss:**

1. `cli.py` has a `_CREDENTIALS` map keyed by stage. Add
   `"endcard": ["B2_KEY_ID", "B2_APP_KEY"]` — it re-uploads, so it needs them.
   Without an entry, `--only endcard` fails deep inside the provider call
   instead of with a friendly message at the door.
2. `tests/test_pipeline.py` has a pre-existing `test_stage_order_is_fixed`
   asserting the exact `STAGES` tuple. Adding a stage breaks it. Update it —
   that is the test doing its job, not an obstacle.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd api && uv run pytest tests/test_pipeline.py -q -k endcard`
Expected: PASS, 4 tests

- [ ] **Step 5: Run the whole suite**

Run: `cd api && uv run pytest tests/ -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add api/newsdesk/pipeline.py api/newsdesk/cli.py api/tests/test_pipeline.py
git commit -m "feat(pipeline): the end card is its own stage, not an edit to the cut

scripts/run_cs1_assemble.py is the verified path whose manifest survives
genblaze verify byte for byte, and its call site says plainly that a second
implementation would be a second thing to keep true. So the card reads what the
cut published rather than reaching inside it, and a run with no logo skips the
stage instead of paying for a re-encode.

supplied_by comes from the approval, not a form field. The human who stamped the
run owns the mark on it, and reading it from the approval means the two cannot
disagree. An unapproved run is refused outright — appending a card re-publishes
the video, and publishing needs a named human."
```

### Task 7b (follow-up, not blocking)

Move the bed's fade so it resolves on the card. Requires `build_filtergraph()`. Do not attempt before the demo.

---

# PHASE 2 — the kit system

Phase 2 changes existing behaviour. Do not start it until Phase 1 is committed and the suite is green.

---

### Task 8: Keyed kit resolution

**Files:**
- Modify: `api/newsdesk/brandkit.py` (`KIT_PREFIX` at :34, `load` at :95)
- Modify: `api/newsdesk/storyfile.py` (`StoryFile` at :69, `parse_story` at :168)
- Test: `api/tests/test_kits.py`

**Interfaces:**
- Produces: `brandkit.kit_prefix(kit_id: str | None) -> str` · `brandkit.load(*, store=None, kit_id: str = "house") -> BrandKit` · `StoryFile.kit: str`

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_kits.py
"""Kit resolution. B2 keys are flat, so kit/ and kit/diorama/ coexist and the
existing kit never moves — the cheapest correct answer, and no migration.
"""
from __future__ import annotations

import pytest

from newsdesk.brandkit import kit_prefix
from newsdesk.storyfile import StoryFileError, parse_story

_STORY = {
    "id": "kit-test",
    "title": "A story",
    "through_line": "fuse",
    "facts": [{"text": "A fact with a number, 5", "sources": [{"url": "https://x.org/a"}]}],
}


@pytest.mark.parametrize("kit_id,expected", [
    (None, "kit/"),
    ("house", "kit/"),
    ("diorama", "kit/diorama/"),
])
def test_the_house_kit_keeps_its_prefix_so_nothing_migrates(kit_id, expected):
    assert kit_prefix(kit_id) == expected


def test_a_story_defaults_to_the_house_kit():
    assert parse_story(dict(_STORY)).kit == "house"


def test_a_story_may_name_a_kit():
    assert parse_story({**_STORY, "kit": "diorama"}).kit == "diorama"


def test_an_unknown_kit_is_refused_at_wall_1():
    """422 at the door, no run created, nothing spent — a fact with no source's
    standard, applied to art direction."""
    with pytest.raises(StoryFileError, match="kit"):
        parse_story({**_STORY, "kit": "not-a-kit"})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_kits.py -q`
Expected: FAIL — `ImportError: cannot import name 'kit_prefix'`

- [ ] **Step 3: Write the implementation**

In `api/newsdesk/brandkit.py`, replace the `KIT_PREFIX` constant:

```python
# The house kit keeps the bare prefix so nothing already published has to move.
# B2 keys are flat, so "kit/negative.txt" and "kit/diorama/negative.txt" are
# different keys with no collision and no migration.
KIT_PREFIX = "kit/"
HOUSE_KIT = "house"
KNOWN_KITS = (HOUSE_KIT, "diorama")


def kit_prefix(kit_id: str | None) -> str:
    if not kit_id or kit_id == HOUSE_KIT:
        return KIT_PREFIX
    return f"{KIT_PREFIX}{kit_id}/"
```

Change `load` to take `kit_id: str = HOUSE_KIT` and use `kit_prefix(kit_id)` wherever `KIT_PREFIX` was used.

In `api/newsdesk/storyfile.py`, add `kit: str = "house"` to `StoryFile` and in `parse_story`:

```python
    kit = (doc.get("kit") or HOUSE_KIT).strip()
    if kit not in KNOWN_KITS:
        raise StoryFileError(
            f"{where}: unknown kit {kit!r}. Choose from: {', '.join(KNOWN_KITS)}"
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd api && uv run pytest tests/test_kits.py tests/test_storyfile.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/newsdesk/brandkit.py api/newsdesk/storyfile.py api/tests/test_kits.py
git commit -m "feat(brandkit): kits are keyed, and nothing migrates

B2 keys are flat, so kit/negative.txt and kit/diorama/negative.txt are simply
different keys. The house kit keeps the bare prefix and never re-syncs, which
means this change cannot break anything already published.

An unknown kit id is refused at Wall 1 — 422, no run, nothing spent. Art
direction is held to a fact-with-no-source's standard because a run that names
a kit we cannot load is a run we already know the ending of."
```

---

### Task 9: Split the exclusion constant

**Files:**
- Create: `brand-kit/floor.txt`
- Modify: `brand-kit/negative.txt`
- Modify: `api/newsdesk/blockprompt.py` (`negative_line` at :93, `negative_is_intact` at :181)
- Modify: `policy/policy.yaml` (POL-2, POL-4)
- Test: `api/tests/test_kits.py`

**Interfaces:**
- Produces: `blockprompt.platform_floor() -> str` · `blockprompt.negative_line(kit_id: str = "house") -> str` · `BlockPrompt.negative_is_intact` checks against the floor

- [ ] **Step 1: Write the failing test**

```python
# append to api/tests/test_kits.py
from newsdesk.blockprompt import negative_line, platform_floor

FLOOR_TERMS = ("photorealism", "live-action footage", "3D render",
               "lip-sync", "talking characters", "watermark", "logo")
TEXT_TERMS = ("readable text", "letters", "words", "numbers", "captions", "subtitles")


@pytest.mark.parametrize("term", FLOOR_TERMS)
def test_the_floor_carries_every_harm_pol1_and_pol3_exist_for(term):
    assert term in platform_floor()


@pytest.mark.parametrize("term", TEXT_TERMS)
def test_the_text_default_is_not_in_the_floor(term):
    """The text half is narrowable. If it were in the floor, no kit could ever
    carry a letterpress label, which is the diorama style's whole signature."""
    assert term not in platform_floor()


def test_the_house_negative_still_forbids_text():
    """Narrowable is not narrowed. The house kit is unchanged in effect."""
    line = negative_line("house")
    for term in TEXT_TERMS:
        assert term in line


def test_every_kit_negative_starts_with_the_floor():
    """The whole POL-2 argument. Without it a kit is compared against itself."""
    for kit_id in ("house", "diorama"):
        assert negative_line(kit_id).startswith(platform_floor())
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_kits.py -q -k floor`
Expected: FAIL — `ImportError: cannot import name 'platform_floor'`

- [ ] **Step 3: Write the implementation**

`brand-kit/floor.txt` — one line, no trailing newline drift, and **never edited by a kit**:

```
photorealism, live-action footage, 3D render, lip-sync, talking characters, watermark, logo
```

`brand-kit/negative.txt` becomes the house kit's *additions* only:

```
readable text, letters, words, numbers, captions, subtitles, color drift, repeated text, doubled text, two lines of identical text
```

In `blockprompt.py`. **`_read(name, directory)` takes a full path string, not a
subdirectory name** — and `blockprompt.py` **must never import `brandkit.py`**,
because `gate.py` imports this module and `tests/test_structure.py` walks that
graph. `brandkit` reaches `config.backend`, which is network-capable. So the kit
names are defined *here*, and `brandkit` and `storyfile` import them from here:

```python
HOUSE_KIT = "house"
KNOWN_KITS = (HOUSE_KIT, "diorama")


def kit_dir_for(kit_id: str | None = None) -> Path:
    """The directory holding one kit's files. The house kit is the bare root."""
    base = kit_dir()
    return base if not kit_id or kit_id == HOUSE_KIT else base / kit_id


def platform_floor() -> str:
    """The harms POL-1 and POL-3 exist for. No kit may narrow this, ever.

    Read from the kit ROOT, never from a kit subdirectory — that is what makes
    it a floor. An outlet that could write its own floor is compared against
    itself and passes trivially.
    """
    return _read("floor.txt", str(kit_dir()))


def negative_line(kit_id: str = HOUSE_KIT) -> str:
    """floor + this kit's additions. Add-only above the floor."""
    additions = _read("negative.txt", str(kit_dir_for(kit_id)))
    return f"{platform_floor()}, {additions}" if additions else platform_floor()
```

`brandkit.py` and `storyfile.py` then do `from newsdesk.blockprompt import
HOUSE_KIT, KNOWN_KITS`. That edge is safe in both directions: `blockprompt`
imports nothing new, and neither file is in `gate.py`'s graph.

**Verify the constraint still holds before committing:**

```bash
cd api && uv run pytest tests/test_structure.py -q
```

Change `negative_is_intact` to assert the emitted NEGATIVE starts with `platform_floor()`.

Add changelog entries to POL-2 and POL-4 in `policy/policy.yaml`, **retaining the pre-split wording next to the new**, per the standing rule.

- [ ] **Step 4: Run the whole suite**

Run: `cd api && uv run pytest tests/ -q`
Expected: PASS. Expect `test_blockprompt.py` failures if the floor/additions split changed byte order; fix by updating the expected constant, never by narrowing the floor.

- [ ] **Step 5: Commit**

```bash
git add brand-kit/floor.txt brand-kit/negative.txt api/newsdesk/blockprompt.py policy/policy.yaml api/tests/test_kits.py
git commit -m "feat(policy): split the exclusion constant into a floor and a text default

Add-only made the diorama's letterpress label structurally impossible: a fence
reading 'no text except <LABEL>' is a narrowing, and narrowing is the one move
add-only forbids. Granting the kit an override would have turned the exclusion
line back into a suggestion, which is the sentence POL-2 exists to prevent.

So the constant splits instead. The floor — photorealism, live-action, 3D
render, lip-sync, talking characters, watermark, logo — is the set of harms
POL-1 and POL-3 exist for and no kit touches it. The text half is narrowable,
and only by inheriting POL-4's existing conditions: three elements, four words,
each mapped to an entered fact.

The house kit is unchanged in effect; its negative still forbids text. What
changed is that it is now an addition rather than a floor, which is what makes
a second kit possible without making the first one weaker.

POL-2 and POL-4 keep their pre-split wording beside the new. Corrections stay
in the record."
```

---

### Task 10: Block labels, validated like claims

**Files:**
- Modify: `api/newsdesk/claims.py` (`ScriptBlock` at :219, `validate_block` at :334)
- Modify: `api/newsdesk/script.py` (parse, prompt)
- Test: `api/tests/test_claims.py`

**Interfaces:**
- Produces: `ScriptBlock.label: str | None = None` · `validate_block` emits `Problem(kind="label_untraced")` and `kind="label_too_long"`

- [ ] **Step 1: Write the failing test**

```python
# append to api/tests/test_claims.py
from newsdesk.claims import ScriptBlock, validate_block

LABEL_MAX_WORDS = 4


def test_a_block_with_no_label_is_unaffected(cs1_story_fixture=None):
    story = cs1_story()
    block = ScriptBlock(n=1, narration="A sentence with no claims in it at all.")
    assert not [p for p in validate_block(story, block) if "label" in p.kind]


def test_a_label_longer_than_four_words_is_rejected():
    """POL-4's element budget. Past it, models duplicate or garble the words."""
    story = cs1_story()
    block = ScriptBlock(n=1, narration="Framing only.", label="one two three four five")
    assert any(p.kind == "label_too_long" for p in validate_block(story, block))


def test_a_label_that_maps_to_no_fact_is_rejected():
    """The narrowing is gated. A letterpress word is a claim in three words."""
    story = cs1_story()
    block = ScriptBlock(n=1, narration="Framing only.", label="NINE TRILLION")
    assert any(p.kind == "label_untraced" for p in validate_block(story, block))


def test_a_label_drawn_from_a_mapped_fact_passes():
    story = cs1_story()
    fact = story.facts[0]
    word = next(w for w in fact.text.split() if len(w) > 4)
    block = ScriptBlock(n=1, narration="Framing only.", label=word,
                        claims=(Claim(spoken=word, fact_id=fact.id, evidence=fact.text),))
    assert not [p for p in validate_block(story, block) if "label" in p.kind]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_claims.py -q -k label`
Expected: FAIL — `TypeError: ScriptBlock.__init__() got an unexpected keyword argument 'label'`

- [ ] **Step 3: Write the implementation**

Add `label: str | None = None` to `ScriptBlock`, and to `validate_block`:

```python
    if block.label:
        words = block.label.split()
        if len(words) > LABEL_MAX_WORDS:
            problems.append(Problem(
                block=block.n, kind="label_too_long",
                message=(f"label {block.label!r} is {len(words)} words; POL-4's "
                         f"element budget is {LABEL_MAX_WORDS}"),
            ))
        if not any(normalize(block.label) in normalize(c.evidence) for c in block.claims):
            problems.append(Problem(
                block=block.n, kind="label_untraced",
                message=(f"label {block.label!r} maps to no entered fact. A word "
                         "printed on a prop is a claim in three words."),
            ))
```

- [ ] **Step 4: Run the whole suite**

Run: `cd api && uv run pytest tests/ -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/newsdesk/claims.py api/newsdesk/script.py api/tests/test_claims.py
git commit -m "feat(claims): a letterpress label is a claim in three words

The label goes where claims are made, so it is validated the way claims are:
four words at most, per POL-4's element budget, and it must map to a fact the
journalist entered. A block whose label traces to nothing is repaired at \$0,
before a picture is bought.

This is what keeps the Task 9 split honest. The word printed on a prop is held
to the same standard as the sentence spoken over it — the only version of
'readable text is allowed here' that does not cost the product its argument.

label is None for the house kit and nothing changes there."
```

---

### Task 11: Author the diorama kit

**Files:**
- Create: `brand-kit/diorama/{negative,style-tokens,scene-guidance}.txt`, `brand-kit/diorama/{through-lines.yaml,voice.json,subtitle.ass}`
- Test: `api/tests/test_kits.py`

- [ ] **Step 1: Write the failing test**

```python
# append to api/tests/test_kits.py
from newsdesk.brandkit import REQUIRED_TEXT

KIT_ROOT = Path(__file__).resolve().parents[2] / "brand-kit"


@pytest.mark.parametrize("kit_id", ["house", "diorama"])
def test_every_kit_carries_all_six_required_files(kit_id):
    """Absent any one of these, it is not a kit."""
    base = KIT_ROOT if kit_id == "house" else KIT_ROOT / kit_id
    for name in REQUIRED_TEXT:
        assert (base / name).is_file(), f"{kit_id} is missing {name}"


def test_the_diorama_kit_records_why_it_is_9_16():
    """The reference is 16:9. The deviation is deliberate and lives in guidance,
    not in style-tokens.txt, which is sent to the provider verbatim."""
    guidance = (KIT_ROOT / "diorama" / "scene-guidance.txt").read_text()
    assert "9:16" in guidance and "16:9" in guidance


def test_the_diorama_kit_carries_the_moderation_map():
    """Named politicians die at render; mushroom cloud trips NSFW. That cost
    someone an afternoon and belongs in the kit, not in anyone's memory."""
    guidance = (KIT_ROOT / "diorama" / "scene-guidance.txt").read_text().lower()
    assert "politician" in guidance
    assert "mushroom cloud" in guidance
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_kits.py -q -k diorama`
Expected: FAIL — missing files

- [ ] **Step 3: Write the kit**

`brand-kit/diorama/style-tokens.txt` — the source's STYLE line **verbatim**, no comments (this file is sent to the provider):

```
cinematic vintage paper diorama, aged sepia newsprint world, monochrome halftone print, monochrome archival cutout figures with black censor bars over their eyes, single burnt-orange accent, distressed letterpress, warm tungsten light, macro tilt-shift shallow depth of field, film grain, handcrafted stop-motion paper feel, non-photorealistic, no live-action
```

`brand-kit/diorama/negative.txt` — additions above the floor, with the label fenced:

```
bright saturated colors, color photography, photorealistic humans, faces, gibberish letters, repeated text, doubled text, two lines of identical text
```

`brand-kit/diorama/scene-guidance.txt` — carries, in prose: the fake-oner shape (one continuous FPV move, boundaries hidden in motion blur, one impact every ~3s, ends motion-blurred); the **9:16 deviation and why** ("the reference is 16:9; Newsdesk delivers 9:16 end to end and assembly is not aspect-aware — do not 'fix' this back"); the **moderation map** (named politicians submit fine and die at render; close-up recognisable statesman faces fail; "mushroom cloud" trips NSFW; censor bars over eyes both sell the look and defuse likeness); and the label rule (one per scene, ≤4 words, must map to a fact).

`brand-kit/diorama/through-lines.yaml` — the burnt-orange object menu, same schema as the house menu.

`brand-kit/diorama/voice.json` — the war-report narrator, 9–10.5s per line.

`brand-kit/diorama/subtitle.ass` — bold condensed sans.

- [ ] **Step 4: Sync and verify**

```bash
cd api && uv run python ../scripts/sync_brand_kit.py && uv run python ../scripts/verify_brand_kit.py
```

The kit is read from B2, not the working copy. Editing the files without syncing does nothing.

- [ ] **Step 5: Render one story and look at it**

```bash
cd api && uv run python -m newsdesk ../stories/<a-story-with-kit-diorama>.yaml --only script
cd api && uv run python -m newsdesk ../stories/<same>.yaml --only gate
```

Then a full run, and the source's own VERIFY step: pull a frame from each clip; confirm every scene reads as newsprint with **exactly one** orange accent; confirm each label rendered correctly on a prop and is not misspelled; confirm the through-line object appears six times. Fix and re-render before delivering.

**Use `seedance-1-0-pro-fast-251015`** — `$0.13` a run against 2.0's `$5.40`. Only escalate if the look demonstrably fails.

- [ ] **Step 6: Commit**

```bash
git add brand-kit/diorama api/tests/test_kits.py
git commit -m "feat(brand-kit): the paper-diorama kit

Authored from diorama-doc.md rather than from a paraphrase, so the moderation
map comes with it: named politicians submit fine and die at render, close-up
recognisable statesman faces fail, and mushroom cloud trips an NSFW flag. That
knowledge cost someone an afternoon and now lives in the kit rather than in
anyone's memory.

Rendered 9:16 against the reference's 16:9, and scene-guidance.txt says so and
says why, because the next person to read the reference will otherwise 'fix' it.
The note is in guidance rather than style-tokens.txt, which is sent to the
provider verbatim — an explanation of ourselves would have shipped in the prompt."
```

---

### Task 12: Through-line authoring by interview

Deferred until after the demo. Per HANDOFF §8: interview → AI drafts → human publishes, the same shape as Wall 1. The drafted entry passes the same gate every block prompt passes before it can be used, and is baked at publish into an immutable versioned kit in B2. `through-lines.yaml` records why the draft is gated rather than trusted: `dollar-cut` once read "labelled paper strips", a POL-4 violation written into the menu by its own authors.

---

## Self-review

**Spec coverage:** captions → Tasks 1–3 · end card → Tasks 5–7 · through-line suggestion → Task 4 · kit resolution → Task 8 · constant split → Task 9 · labels → Task 10 · diorama kit → Task 11 · authoring → Task 12 (deferred, per spec). The spec's "music resolves on the card" is **cut**, named at the top and recorded as Task 7b.

**Placeholders:** none. Task 11's kit files are described by required content and pinned by tests rather than reproduced in full, because their content is a verbatim copy from `diorama-doc.md`, which the implementer must open anyway — `CLAUDE.md` requires it.

**Type consistency:** `Caption`, `EndCard`, `ScriptBlock.label`, `kit_prefix`, `platform_floor`, `negative_line(kit_id)` are used with the same signatures in every task that references them. `sources_for` returns `tuple[str, ...]` in Tasks 1 and 2. `generate_captions` returns `(RunState, Ledger, tuple[Caption, ...])` in Tasks 2 and 3.
