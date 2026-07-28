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
    assert STAGES == ("script", "gate", "blocks", "narration", "assembly")


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
    def __init__(self, ok=True, cost=0.156):
        self.ok = ok
        self.cost_usd = cost
        self.video_model = "seedance-1-0-pro-fast-251015"


def test_every_block_cost_lands_in_the_run_log(cs2, monkeypatch):
    """`RunState.total_cost` sums the event log, because GMI does not report
    cost — so a block whose spend never reaches an event is a block that
    silently cost nothing on the receipt."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(p, "load_kit", _kit)
    monkeypatch.setattr(p, "sink", lambda prefix: None)

    async def fake_run_block(prompt, **kw):
        return _FakeResult()

    monkeypatch.setattr(p, "run_block", fake_run_block)

    pipe = _fresh(cs2)
    result = asyncio.run(
        pipe.stage_blocks(image_provider=object(), video_provider=object())
    )

    assert result.ok
    assert result.cost_usd == pytest.approx(0.156 * 6)
    assert pipe.state.total_cost == pytest.approx(0.156 * 6)


def test_one_dead_block_fails_the_stage_and_names_it(cs2, monkeypatch):
    """Five of six is not a video. The stage has to stop the run rather than
    hand assembly a gap it would fill with a frozen frame."""
    import newsdesk.pipeline as p

    monkeypatch.setattr(p, "load_kit", _kit)
    monkeypatch.setattr(p, "sink", lambda prefix: None)

    async def fake_run_block(prompt, **kw):
        return _FakeResult(ok=prompt.block != 4, cost=0.156)

    monkeypatch.setattr(p, "run_block", fake_run_block)

    result = asyncio.run(
        _fresh(cs2).stage_blocks(image_provider=object(), video_provider=object())
    )
    assert not result.ok
    assert "4" in result.detail
    assert result.cost_usd > 0, "a failed run still spent what it spent"


def _kit():
    """The published brand kit, as the pipeline reads it — from the file that
    IS the kit under version control, so these tests never touch B2."""
    import yaml

    doc = yaml.safe_load(
        (STORIES.parent / "brand-kit" / "through-lines.yaml").read_text(encoding="utf-8")
    )
    return type("Kit", (), {"through_lines": doc})()
