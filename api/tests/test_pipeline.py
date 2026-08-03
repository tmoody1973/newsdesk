"""The orchestrator (MOO-434).

The whole point of injecting providers is that this file exists: stage
ordering, the resume rule and the "$0 on a refusal" property are all testable
here rather than discoverable on a credit card.

The resume rule is the one worth stating out loud. A run is ~5 minutes and
several dollars, and the failure that actually happens is a late stage dying on
a provider timeout. Re-running from the top would re-roll the pictures — which
costs money AND silently changes the video, because a second roll of the same
prompt is a different image. So "already done" must mean "skipped", never
"redone".
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from dataclasses import replace

from newsdesk.claims import Claim, ScriptBlock
from newsdesk.pipeline import STAGES, Pipeline, PipelineError
from newsdesk.state import Block, RunState
from newsdesk.storyfile import load_story

STORIES = Path(__file__).resolve().parents[2] / "stories"


@pytest.fixture
def cs2():
    return load_story(STORIES / "cs2.yaml")


def _fresh(story_file):
    """A pipeline that never consults B2 for prior state."""
    return Pipeline.start(story_file, resume=False)


# --- the run's identity ------------------------------------------------------


def test_a_new_run_carries_the_story_and_its_facts(cs2):
    pipe = _fresh(cs2)
    assert pipe.state.run_id == "cs2"
    assert pipe.state.story == cs2.story.title
    assert len(pipe.state.facts) == len(cs2.story.facts)
    assert pipe.state.art_direction["through_line"] == "record"


def test_the_facts_reach_the_state_with_their_sources(cs2):
    """The Run Board and the receipt both read facts off the state. A fact that
    arrives there stripped of its sources is Wall 1 undone one layer down."""
    pipe = _fresh(cs2)
    assert all(f["sources"] for f in pipe.state.facts)


def test_stage_order_is_fixed():
    """Renaming or reordering these changes a user-facing flag AND an audit
    record, since stage names appear in the run's event log."""
    assert STAGES == (
        "script", "gate", "blocks", "narration", "assembly", "endcard", "caption",
    )


# --- the script stage --------------------------------------------------------


def _script_blocks(n=6):
    return tuple(
        ScriptBlock(
            n=i,
            narration=f"Line {i} about a number.",
            claims=(Claim(spoken="a number", fact_id="F1", evidence="evidence"),),
        )
        for i in range(1, n + 1)
    )


def test_the_script_stage_puts_lines_and_claims_on_the_state(cs2, monkeypatch):
    import newsdesk.pipeline as p

    blocks = _script_blocks()
    monkeypatch.setattr(
        p, "generate_script", lambda state, ledger, story, **kw: (state, ledger, blocks)
    )
    pipe = _fresh(cs2)
    result = pipe.stage_script()

    assert result.ok and not result.skipped
    assert [b.n for b in pipe.state.blocks] == [1, 2, 3, 4, 5, 6]
    assert pipe.state.blocks[0].fact_ids == ("F1",)
    assert pipe.state.blocks[0].claims[0]["evidence"] == "evidence"


def test_a_script_that_survives_nothing_fails_the_stage(cs2, monkeypatch):
    """generate_script returns no blocks unless every check passed. That is a
    refusal, and a refusal must stop the run before the blocks stage spends."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(
        p, "generate_script", lambda state, ledger, story, **kw: (state, ledger, ())
    )
    result = _fresh(cs2).stage_script()
    assert not result.ok
    assert result.cost_usd == 0.0


def test_an_already_scripted_run_is_skipped_not_regenerated(cs2, monkeypatch):
    """THE resume rule. Re-generating produces DIFFERENT lines, which would
    invalidate takes already cut from the old ones and any human approval
    attached to that cut."""
    import newsdesk.pipeline as p

    called = []
    monkeypatch.setattr(
        p, "generate_script",
        lambda *a, **k: called.append(1) or (a[0], a[1], _script_blocks()),
    )

    pipe = _fresh(cs2)
    pipe.state = pipe.state.__class__(
        **{**pipe.state.__dict__,
           "blocks": tuple(Block(n=i, narration=f"Line {i}") for i in range(1, 7))}
    )
    result = pipe.stage_script()

    assert result.skipped and result.ok
    assert called == [], "a resumed run must not call the model again"
    assert len(pipe.blocks) == 6, "the existing lines are rehydrated for later stages"


# --- the gate stage ----------------------------------------------------------


def test_the_gate_stage_needs_no_provider_and_spends_nothing(cs2, monkeypatch):
    """CS-4's acceptance criterion: the refusal path runs with no credentials.
    Not "we don't call the API" — no provider object is constructed at all."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(p, "load_kit", _kit)
    result = _fresh(cs2).stage_gate()

    assert result.ok, result.detail
    assert result.cost_usd == 0.0
    assert "$0" in result.detail


def test_an_unknown_through_line_names_what_is_on_offer(cs2, monkeypatch):
    """A typo here used to surface at generation time, after the gate had
    passed and the first image was about to be paid for."""
    import newsdesk.pipeline as p
    from dataclasses import replace

    monkeypatch.setattr(p, "load_kit", _kit)
    pipe = _fresh(replace(cs2, through_line="no-such-object"))
    with pytest.raises(PipelineError, match="record"):
        pipe.stage_gate()


# --- the blocks stage --------------------------------------------------------


class _FakeResult:
    def __init__(self, ok=True, cost=0.156, n=1):
        self.ok = ok
        self.cost_usd = cost
        self.video_model = "seedance-1-0-pro-fast-251015"
        self.still_uri = f"https://b2/still-{n}.png" if ok else None
        self.clip_uri = f"https://b2/clip-{n}.mp4" if ok else None


def test_every_block_cost_lands_in_the_run_log(cs2, monkeypatch):
    """`RunState.total_cost` sums the event log, because GMI does not report
    cost — so a block whose spend never reaches an event is a block that
    silently cost nothing on the receipt."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(p, "load_kit", _kit)
    monkeypatch.setattr(p, "sink", lambda prefix: None)

    async def fake_run_block(prompt, **kw):
        return _FakeResult(n=prompt.block)

    monkeypatch.setattr(p, "run_block", fake_run_block)

    pipe = _fresh(cs2)
    result = asyncio.run(
        pipe.stage_blocks(image_provider=object(), video_provider=object())
    )

    assert result.ok
    assert result.cost_usd == pytest.approx(0.156 * 6)
    assert pipe.state.total_cost == pytest.approx(0.156 * 6)


def test_the_pictures_land_on_the_block_not_only_in_the_log(cs2, monkeypatch):
    """Editor Review and the Run Board render `still_uri`.

    The stage recorded cost and status and threw the URIs away, so a run that
    completed perfectly showed grey rectangles on every screen that displays a
    frame. Caught by looking at Editor Review against a real run, not by a test
    — hence this one.
    """
    import newsdesk.pipeline as p
    from newsdesk.state import Block

    monkeypatch.setattr(p, "load_kit", _kit)
    monkeypatch.setattr(p, "sink", lambda prefix: None)

    async def fake_run_block(prompt, **kw):
        return _FakeResult(n=prompt.block)

    monkeypatch.setattr(p, "run_block", fake_run_block)

    pipe = _fresh(cs2)
    # with_block only patches blocks that already exist — the script stage is
    # what creates them, so a realistic state has them before blocks runs.
    pipe.state = replace(
        pipe.state, blocks=tuple(Block(n=i, narration=f"L{i}") for i in range(1, 7))
    )
    asyncio.run(pipe.stage_blocks(image_provider=object(), video_provider=object()))

    for block in sorted(pipe.state.blocks, key=lambda b: b.n):
        assert block.still_uri == f"https://b2/still-{block.n}.png"
        assert block.clip_uri == f"https://b2/clip-{block.n}.mp4"
        assert block.status == "ready"


def test_one_dead_block_fails_the_stage_and_names_it(cs2, monkeypatch):
    """Five of six is not a video. The stage has to stop the run rather than
    hand assembly a gap it would fill with a frozen frame."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(p, "load_kit", _kit)
    monkeypatch.setattr(p, "sink", lambda prefix: None)

    async def fake_run_block(prompt, **kw):
        return _FakeResult(ok=prompt.block != 4, cost=0.156, n=prompt.block)

    monkeypatch.setattr(p, "run_block", fake_run_block)

    result = asyncio.run(
        _fresh(cs2).stage_blocks(image_provider=object(), video_provider=object())
    )
    assert not result.ok
    assert "4" in result.detail
    assert result.cost_usd > 0, "a failed run still spent what it spent"


def test_caption_is_the_last_stage():
    """After the video is done, per the request. --only caption re-runs for cents."""
    from newsdesk.pipeline import STAGES
    assert STAGES[-1] == "caption"
    assert STAGES.index("caption") > STAGES.index("assembly")


def test_caption_stage_stores_captions_on_the_run(cs2, monkeypatch):
    from newsdesk.caption import Caption
    from newsdesk.claims import Claim

    def _fake(state, ledger, story, blocks, *, through_line, chat_fn=None, model=None):
        return state, ledger, (Caption(
            platform="linkedin", variant=1, hook="h", body="b", cta="c",
            hashtags=("#A", "#B", "#C"),
            claims=(Claim(spoken="h", fact_id="F1", evidence="e"),),
        ),)

    monkeypatch.setattr("newsdesk.pipeline.generate_captions", _fake)
    pipe = _fresh(cs2)
    result = pipe.stage_caption()
    assert result.ok
    assert pipe.state.final["captions"][0]["platform"] == "linkedin"
    # I4: the claim trail has to reach the receipt, not just the prose it
    # produced — the whole feature's headline claim is that every caption
    # traces to an entered fact.
    assert pipe.state.final["captions"][0]["claims"] == [
        {"spoken": "h", "fact_id": "F1", "evidence": "e"}
    ]


def test_caption_stage_is_ok_but_empty_when_nothing_traced(cs2, monkeypatch):
    """A refusal is a normal outcome, not a stage failure — the ledger carries why."""
    def _none(state, ledger, story, blocks, *, through_line, chat_fn=None, model=None):
        return state, ledger, ()

    monkeypatch.setattr("newsdesk.pipeline.generate_captions", _none)
    pipe = _fresh(cs2)
    result = pipe.stage_caption()
    assert result.ok and result.detail == "no caption traced"
    # I1: no prior captions existed, so there is nothing to preserve — but a
    # refusal must not manufacture a `captions: []` entry either.
    assert "captions" not in (pipe.state.final or {})


def test_a_failed_caption_retry_leaves_existing_captions_intact(cs2, monkeypatch):
    """I1: `caps` is empty on a provider outage or exhausted repair attempts.
    Overwriting `final['captions']` with that empty result would erase a
    batch a previous run already traced successfully — and captions are
    deliberately safe to re-run (unlike the script stage), so this refusal
    has to be a no-op, not data loss."""
    def _none(state, ledger, story, blocks, *, through_line, chat_fn=None, model=None):
        return state, ledger, ()

    monkeypatch.setattr("newsdesk.pipeline.generate_captions", _none)
    pipe = _fresh(cs2)
    existing = [{"platform": "linkedin", "variant": 1, "hook": "h", "body": "b",
                 "cta": "c", "hashtags": ["#A", "#B", "#C"], "sources": [],
                 "text": "h\n\nb\n\nc", "claims": []}]
    pipe.state = replace(pipe.state, final={"captions": existing})

    result = pipe.stage_caption()

    assert result.ok and result.detail == "no caption traced"
    assert pipe.state.final["captions"] == existing


def _kit(**_kw):
    """The published brand kit, as the pipeline reads it — from the file that
    IS the kit under version control, so these tests never touch B2.

    Takes `**_kw` because the real `brandkit.load` is keyword-only and is called
    with `kit_id=`. A fake with a narrower signature than the thing it replaces
    is a test that passes for the wrong reason right up until it doesn't."""
    import yaml

    doc = yaml.safe_load(
        (STORIES.parent / "brand-kit" / "through-lines.yaml").read_text(encoding="utf-8")
    )
    return type("Kit", (), {"through_lines": doc})()


# --- the end card stage -------------------------------------------------------


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


def test_the_endcard_stage_skips_when_a_card_is_already_applied(cs2, monkeypatch):
    """A second pass over `--from endcard` (or any resume reaching this stage
    again) must not re-encode: `final["uri"]` is already the branded b2://
    URI, and treating it as a local path a second time is the exact bug this
    guards against. render_card/append_card must not even be called."""
    def _boom(*a, **kw):
        raise AssertionError("stage re-rendered a card that was already applied")

    monkeypatch.setattr("newsdesk.pipeline.render_card", _boom)
    monkeypatch.setattr("newsdesk.pipeline.append_card", _boom)

    pipe = _fresh(cs2)
    pipe.state = replace(pipe.state, final={
        "uri": "b2://newsdesk-runs/cs2/final-branded.mp4",
        "end_card_request": {"local_path": "x.png", "uri": "b2://x", "url": None},
        "end_card": {"image": "b2://x", "url": None, "supplied_by": "Tarik Moody",
                     "generated": False},
    })
    pipe.state = pipe.state.approve("Tarik Moody")

    result = pipe.stage_endcard()
    assert result.ok and result.skipped


def test_a_render_failure_surfaces_through_the_pipelines_own_failure_channel(
    cs2, monkeypatch, tmp_path,
):
    """A corrupt logo must fail as `StageResult(ok=False)`, the channel every
    other stage failure uses — not leak `EndCardError` (a plain ValueError)
    past cli.py's `except PipelineError` as a raw traceback in front of a
    judge."""
    from newsdesk.endcard import EndCardError

    published = tmp_path / "final.mp4"
    published.write_bytes(b"stub")

    monkeypatch.setattr(
        "newsdesk.pipeline.render_card",
        lambda image, out, **kw: (_ for _ in ()).throw(
            EndCardError("logo.png is not an image ffmpeg can read")
        ),
    )

    pipe = _fresh(cs2)
    pipe.state = replace(pipe.state, final={
        "uri": str(published),
        "end_card_request": {"local_path": "logo.png", "uri": "b2://x/logo.png",
                             "url": None},
    })
    pipe.state = pipe.state.approve("Tarik Moody")

    result = pipe.stage_endcard()
    assert not result.ok
    assert "not an image" in result.detail


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


# --- the kit, threaded from the story file -----------------------------------
#
# Task 8 keyed the kits and Task 10 made the script stage emit a prop label;
# neither reached the run path. `brandkit.load()` was called with no kit_id and
# every prompt was built from the house files, so a story saying `kit: diorama`
# rendered as the house kit and its own style-tokens.txt was never read.


def _reply(label: str | None = None, n: int = 6) -> str:
    """A model reply in the shape `script.parse_blocks` actually parses.

    Built through the PRODUCING module rather than by constructing ScriptBlock
    directly: `label` arrives from a JSON key the generator emits, and a fixture
    that skips that step proves only that the two halves agree with each other.
    """
    import json

    return json.dumps({"blocks": [
        {
            "n": i,
            "role": "evidence",
            "narration": f"Line {i} states a third of its budget in plain words.",
            "claims": [{"spoken": "a third", "fact_id": "F1", "evidence": "a third"}],
            **({"label": label} if label else {}),
        }
        for i in range(1, n + 1)
    ]})


def test_a_prop_label_survives_attach_persist_restore(cs2):
    """The first resume after scripting used to lose it silently.

    `state.Block` had no `label` field, so `_attach_blocks` dropped what the
    script stage had just validated and `_blocks_from_state` rebuilt every block
    with `label=None`. The word on the prop was gone by the time the blocks
    stage read the state back — with no error, because a missing label is a
    legal state.
    """
    from newsdesk.pipeline import _attach_blocks, _blocks_from_state
    from newsdesk.script import parse_blocks

    blocks = parse_blocks(_reply(label="WATERTOWN"))
    assert blocks[0].label == "WATERTOWN", "the fixture must carry what the parser emits"

    state = _attach_blocks(_fresh(cs2).state, blocks)
    assert state.blocks[0].label == "WATERTOWN"

    # Through JSON, because that is the actual round trip: the state is written
    # to B2 between stages, not held in memory.
    restored = RunState.from_json(state.to_json())
    assert [b.label for b in _blocks_from_state(restored)] == ["WATERTOWN"] * 6


def test_a_house_block_still_round_trips_with_no_label(cs2):
    """House stories emit no label at all and must stay byte-identical."""
    from newsdesk.pipeline import _attach_blocks, _blocks_from_state
    from newsdesk.script import parse_blocks

    state = _attach_blocks(_fresh(cs2).state, parse_blocks(_reply()))
    restored = RunState.from_json(state.to_json())
    assert all(b.label is None for b in _blocks_from_state(restored))


def test_the_script_stage_asks_for_the_storys_own_kit(cs2, monkeypatch):
    """`build_prompt` only asks for a prop label when the kit carries props. A
    diorama story whose script stage says "house" never gets a label at all."""
    import newsdesk.pipeline as p

    seen = {}

    def _capture(state, ledger, story, **kw):
        seen.update(kw)
        return state, ledger, ()

    monkeypatch.setattr(p, "generate_script", _capture)
    _fresh(replace(cs2, kit="diorama")).stage_script()
    assert seen.get("kit") == "diorama"


def test_the_published_kit_is_fetched_under_the_storys_kit_id(cs2, monkeypatch):
    """`brandkit.load()` with no kit_id reads kit/ — the house prefix — so a
    diorama run resolved its through-line against the house menu."""
    import newsdesk.pipeline as p

    seen = {}

    def _capture(**kw):
        seen.update(kw)
        return _kit()

    monkeypatch.setattr(p, "load_kit", _capture)
    with pytest.raises(PipelineError):
        # cs2's through-line is not in the fake menu's kit; the load is what
        # this test is about, and it happens first.
        _fresh(replace(cs2, kit="diorama", through_line="no-such-object")).through_line()
    assert seen.get("kit_id") == "diorama"


def test_every_block_prompt_is_built_in_the_storys_kit(cs2, monkeypatch):
    """The gate and the blocks stage must both build in the story's kit, or the
    gate passes on one prompt and a different one is paid for."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(p, "load_kit", lambda **kw: _kit())
    seen: list[str] = []
    real = p.build_block_prompt

    def _capture(through_line, n, blocks, **kw):
        seen.append(kw.get("kit"))
        return real(through_line, n, blocks)

    monkeypatch.setattr(p, "build_block_prompt", _capture)
    _fresh(replace(cs2, kit="diorama")).stage_gate()
    assert seen and set(seen) == {"diorama"}


def test_the_gate_sources_a_scripted_label_and_blocks_pays_for_the_same_prompt(
    cs2, monkeypatch
):
    """Task 11b. `stage_gate` must give POL-4 the block's own claims-validated
    label — not check a generic prompt that never carries it — and `stage_blocks`
    must render the identical bytes, not a second prompt that happens to agree."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(p, "load_kit", _kit)
    monkeypatch.setattr(p, "sink", lambda prefix: None)

    pipe = _fresh(replace(cs2, kit="diorama"))
    pipe.state = replace(
        pipe.state,
        blocks=tuple(
            Block(n=i, narration=f"Line {i}", label="EXPIRED" if i == 1 else None)
            for i in range(1, 7)
        ),
    )

    gate_result = pipe.stage_gate()
    assert gate_result.ok, gate_result.detail

    captured: dict[int, object] = {}

    async def fake_run_block(prompt, **kw):
        captured[prompt.block] = prompt
        return _FakeResult(n=prompt.block)

    monkeypatch.setattr(p, "run_block", fake_run_block)
    asyncio.run(pipe.stage_blocks(image_provider=object(), video_provider=object()))

    assert '"EXPIRED"' in captured[1].scene
    assert '"' not in captured[2].scene


def test_an_unattested_label_left_on_the_state_makes_the_gate_refuse(cs2, monkeypatch):
    """The other direction: a label the gate is not told about is unsourced
    text, and Wall 2 must still stop it before any spend."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(p, "load_kit", _kit)

    pipe = _fresh(replace(cs2, kit="diorama"))
    pipe.state = replace(
        pipe.state,
        blocks=tuple(Block(n=i, narration=f"Line {i}") for i in range(1, 7)),
    )
    # Force a label into block 1's prompt without it being on the state — the
    # bug this task closes: a label spliced into SCENE but never sourced to
    # the gate.
    real_bbp = p.build_block_prompt

    def _bbp_with_forced_label(through_line, n, blocks=6, **kw):
        if n == 1:
            kw["label"] = "EXPIRED"
        return real_bbp(through_line, n, blocks, **kw)

    monkeypatch.setattr(p, "build_block_prompt", _bbp_with_forced_label)

    result = pipe.stage_gate()
    assert not result.ok
    assert "EXPIRED" in result.detail


def test_a_run_records_its_kit_where_editor_review_can_find_it():
    """Editor Review rebuilds the story from the run to approve it. A run that
    forgets its kit assembles a diorama with house subtitles — silently."""
    from newsdesk.pipeline import Pipeline
    from newsdesk.storyfile import parse_story

    doc = {
        "id": "kit-carrier", "title": "A title", "through_line": "note-stack",
        "kit": "diorama",
        "facts": [{"text": "A sourced fact", "sources": ["https://example.org/a"]}],
    }
    pipe = Pipeline.start(parse_story(doc, where="test"))
    assert pipe.state.art_direction["kit"] == "diorama"
    assert pipe.state.art_direction["through_line"] == "note-stack"
