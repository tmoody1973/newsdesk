"""SCENE construction, and the gate's verdict on what it produces (MOO-424).

The real test of a prompt builder is not that it renders a string — it is that
every string it renders survives the policy gate. If the builder can produce a
block the gate rejects, the journalist meets a refusal they cannot act on,
because they never wrote the words being refused.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from newsdesk.policy.gate import check
from newsdesk.scene import ThroughLine, build_block_prompt, build_scene

KIT = Path(__file__).resolve().parents[2] / "brand-kit" / "through-lines.yaml"


def all_through_lines() -> list[ThroughLine]:
    doc = yaml.safe_load(KIT.read_text(encoding="utf-8"))
    return [ThroughLine.from_kit(e) for e in doc["through_lines"]]


def test_the_kit_has_the_six_documented_options():
    assert len(all_through_lines()) == 6


@pytest.mark.parametrize("tl", all_through_lines(), ids=lambda t: t.id)
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_every_menu_option_passes_the_gate_at_every_block(tl, n):
    """36 combinations, all of them reachable from the UI by clicking."""
    result = check(build_block_prompt(tl, n))
    assert result.passed, f"{tl.id} block {n}: {result.explain()}"


@pytest.mark.parametrize("tl", all_through_lines(), ids=lambda t: t.id)
def test_the_ground_is_named_in_every_scene(tl):
    """The one element that drifted when left implicit — two scenes off one
    style key produced a blue ground and a tan one (MOO-424)."""
    scene = build_scene(tl, 3)
    assert "warm cream" in scene
    assert "halftone" in scene


@pytest.mark.parametrize("tl", [t for t in all_through_lines() if t.surface], ids=lambda t: t.id)
def test_a_lettering_prone_object_describes_its_surface_in_the_same_sentence(tl):
    """scene-guidance.txt: naming blankness in a separate sentence produced
    legible numerals three times out of four. It has to arrive with the object."""
    scene = build_scene(tl, 1).lower()
    sentences = [x.strip() for x in scene.split(".") if x.strip()]
    # The sentence that introduces the object, found by a word unique to it.
    anchor = tl.framing.split()[1].lower()
    object_sentence = next(s for s in sentences if anchor in s)
    surface_anchor = tl.surface.lower().split()[:4]
    assert " ".join(surface_anchor) in object_sentence, (
        "the surface must be described in the same sentence as the object; "
        "a separate exclusion afterwards produced legible numerals 3 of 4 times"
    )


def test_the_escalation_advances_across_blocks():
    """Whichever phrasing a through-line uses, the six blocks must differ."""
    tl = all_through_lines()[0]
    stages = [build_scene(tl, n) for n in (1, 3, 6)]
    assert len(set(stages)) == 3, "every block should describe a different state"


@pytest.mark.parametrize(
    "tl", [t for t in all_through_lines() if t.countable], ids=lambda t: t.id
)
def test_a_countable_escalation_falls_by_a_whole_unit(tl):
    """Stated as an exact count, decreasing, never repeating.

    The percentage phrasing it replaced came back non-monotonic twice on live
    rolls — block 6 with MORE rings than block 1. A model cannot render a
    proportion of an abstract change; it can render eight things and three.
    """
    import re

    counts = []
    for n in range(1, 7):
        m = re.search(r"Draw EXACTLY (\d+) ", build_scene(tl, n))
        assert m, f"block {n} states no count"
        counts.append(int(m.group(1)))

    assert counts[0] == tl.countable["start"]
    assert counts[-1] == tl.countable["end"]
    assert counts == sorted(counts, reverse=True), f"not monotonic: {counts}"
    assert len(set(counts)) == len(counts), f"two blocks share a count: {counts}"


@pytest.mark.parametrize(
    "tl", [t for t in all_through_lines() if t.silhouette], ids=lambda t: t.id
)
def test_a_silhouette_describes_rather_than_forbids(tl):
    """scene-guidance.txt: framing, not negation, drives what a model renders.

    v1 of the tower silhouette ended in "NO observation deck, NO disc, NO bulge,
    NO pod" and two of six blocks grew a pod anyway. A shape stated positively
    leaves nothing to resolve.
    """
    shape = tl.silhouette.upper()
    assert " NO " not in shape, "the silhouette forbids instead of describing"
    assert "NOT A " not in shape


@pytest.mark.parametrize("tl", all_through_lines(), ids=lambda t: t.id)
def test_no_scene_requests_readable_text(tl):
    """POL-4 is checked by the gate above; this asserts the builder never even
    reaches for the vocabulary."""
    scene = build_scene(tl, 4).lower()
    for phrase in ("the words", "text reading", "labelled", "spelling", "written on"):
        assert phrase not in scene


@pytest.mark.parametrize("tl", all_through_lines(), ids=lambda t: t.id)
def test_the_negative_line_survives_construction(tl):
    """POL-2 is a byte comparison; the builder must not touch the constant."""
    assert build_block_prompt(tl, 1).negative_is_intact


def test_the_prompt_does_not_claim_an_attached_style_key():
    """MOO-424 removed the style-key image input. A prompt still saying "match
    the attached key" points the model at nothing and invites it to invent the
    referent — which is how the blue-ground/tan-ground drift started."""
    rendered = build_block_prompt(all_through_lines()[0], 1).render()
    assert "attached" not in rendered.lower()


@pytest.mark.parametrize("tl", all_through_lines(), ids=lambda t: t.id)
@pytest.mark.parametrize("n", [1, 3, 6])
def test_sentences_start_with_a_capital(tl, n):
    """A prompt that reads as broken prose gets treated as broken prose."""
    for sentence in [s.strip() for s in build_scene(tl, n).split(".") if s.strip()]:
        assert sentence[0].isupper(), f"{tl.id} block {n}: {sentence[:60]!r}"


# --- block results are read against the SDK's enum, not a guessed vocabulary --


def test_a_succeeded_image_step_is_not_treated_as_a_failure():
    """The first version compared status against ("completed", "success", "ok")
    and hard-stopped a healthy run whose status was StepStatus.SUCCEEDED."""
    from genblaze_core.models.enums import StepStatus

    from newsdesk.blocks import read_result

    class _Asset:
        url, sha256 = "b2://assets/still.png", "abc"

    class _Clip:
        url, sha256 = "b2://assets/clip.mp4", "def"

    class _Step:
        def __init__(self, status, assets, model, cost):
            self.status, self.assets, self.model, self.cost_usd = status, assets, model, cost

    class _Run:
        steps = [
            _Step(StepStatus.SUCCEEDED, [_Asset()], "gemini-2.5-flash-image", 0.039),
            _Step(StepStatus.SUCCEEDED, [_Clip()], "seedance-1-0-pro-fast-251015", 0.022),
        ]

    result = read_result(1, _Run(), requested_video_model="seedance-1-0-pro-fast-251015")
    assert result.ok
    assert result.still_uri and result.clip_uri
    assert result.cost_usd == 0.061
    assert not result.used_fallback


def test_a_fallback_video_model_is_recorded_as_the_one_that_ran():
    """The chain is only honest if the manifest names the provider that ran."""
    from genblaze_core.models.enums import StepStatus

    from newsdesk.blocks import read_result

    class _A:
        url, sha256 = "u", "s"

    class _Step:
        def __init__(self, model):
            self.status, self.assets, self.model, self.cost_usd = (
                StepStatus.SUCCEEDED, [_A()], model, 0.0,
            )

    class _Run:
        steps = [_Step("gemini-2.5-flash-image"), _Step("kling-image2video-v2.1-master")]

    result = read_result(1, _Run(), requested_video_model="seedance-1-0-pro-fast-251015")
    assert result.used_fallback
    assert result.video_model == "kling-image2video-v2.1-master"


# --- POL-4 element budget (policy v2) ---------------------------------------


def _scene_with(text: str) -> object:
    from newsdesk.blockprompt import BlockPrompt

    return BlockPrompt.build(1, scene=text, motion="Slow push in.", audio="Room tone.")


def test_sourced_on_prop_text_within_budget_passes():
    """The permitted case: a short question mapped to an entered fact."""
    prompt = _scene_with(
        'A cream card taped at one corner, carrying the hand-lettered words "F1".'
    )
    assert check(prompt, fact_ids=("F1",)).passed


def test_too_many_text_elements_is_rejected():
    prompt = _scene_with('Cards reading "F1", "F2", "F3" and "F4" laid in a row.')
    result = check(prompt, fact_ids=("F1", "F2", "F3", "F4"))
    assert not result.passed
    assert "4 text elements" in result.explain()


def test_an_over_long_text_element_is_rejected():
    prompt = _scene_with('A card hand-lettered "who pays when the lights go out".')
    result = check(prompt, fact_ids=("WHO PAYS WHEN THE LIGHTS GO OUT",))
    assert not result.passed
    assert "words on screen" in result.explain()


def test_an_unsourced_word_outranks_a_budget_complaint():
    """A policy violation must not be buried under a quibble about counting."""
    prompt = _scene_with('Cards reading "RIGGED", "F1", "F2" and "F3".')
    result = check(prompt, fact_ids=("F1", "F2", "F3"))
    assert not result.passed
    assert "RIGGED" in result.explain()


def test_the_published_negative_line_carries_the_duplication_terms():
    """Policy v2 extended the constant; POL-2 byte-compares against it."""
    from newsdesk.blockprompt import negative_line

    line = negative_line()
    for term in ("repeated text", "doubled text", "two lines of identical text"):
        assert term in line
    assert build_block_prompt(all_through_lines()[0], 1).negative_is_intact


def test_a_kit_brings_its_own_ground_and_accent():
    """The ground and the corner accents are house constants — warm cream card,
    navy and coral. Left unconditional they contradict the diorama's own STYLE
    line inside the same prompt: sepia newsprint above, cream collage below.
    They come from the kit's art-direction file, defaulting to the house."""
    from newsdesk.scene import ANCHOR, GROUND, ThroughLine, build_scene

    entry = {"id": "keg-fuse", "label": "A powder keg", "framing": "a squat paper keg",
             "escalation": "the fuse shortens"}
    doc = {"scene": {"ground": "An aged sepia newsprint diorama interior",
                     "anchor": "One burnt-orange paper element is the only colour in frame"}}

    scene = build_scene(ThroughLine.from_kit(entry, doc=doc), 1)
    assert "aged sepia newsprint diorama interior" in scene
    assert "One burnt-orange paper element is the only colour in frame" in scene
    assert GROUND not in scene and ANCHOR not in scene

    house = build_scene(ThroughLine.from_kit(entry), 1)
    assert GROUND in house and ANCHOR in house


# --- Task 11b: the letterpress label splice ---------------------------------
#
# `ScriptBlock.label` was emitted, validated by claims.py, and survived the
# state round-trip — and then nothing put it in a prompt. These pin the two
# directions of that gap at once: the label must actually reach SCENE, and
# the gate must refuse the exact same quoted word the moment nobody attests
# it. Deleting either the splice or the refusal breaks one of the two.


def test_a_claims_validated_label_reaches_the_scene_and_the_gate_sources_it():
    from newsdesk.blockprompt import platform_floor

    tl = all_through_lines()[0]
    prompt = build_block_prompt(tl, 1, kit="diorama", label="EXPIRED")

    assert '"EXPIRED"' in prompt.scene
    assert prompt.negative.startswith(platform_floor())
    assert prompt.negative.endswith(
        'No text anywhere except "EXPIRED". No gibberish letters, no repeated text.'
    )
    assert check(prompt, labels=("EXPIRED",)).passed


def test_the_same_prompt_with_no_attested_label_is_refused():
    """The sibling of the test above. Deleting the new sourced-path breaks
    that one; deleting this refusal breaks this one — together they prove the
    gate did not just start accepting quoted SCENE text unconditionally."""
    tl = all_through_lines()[0]
    prompt = build_block_prompt(tl, 1, kit="diorama", label="EXPIRED")

    result = check(prompt, labels=())
    assert not result.passed
    assert "EXPIRED" in result.explain()


def test_a_five_word_label_is_refused_by_the_word_budget_even_when_attested():
    tl = all_through_lines()[0]
    label = "one two three four five"
    prompt = build_block_prompt(tl, 1, kit="diorama", label=label)

    result = check(prompt, labels=(label,))
    assert not result.passed
    assert "words on screen" in result.explain()


def test_label_none_renders_byte_identical_to_before_this_task():
    """House kit and label-less diorama blocks change nothing — the splice
    only fires when a kit ever hands `build` a label."""
    tl = all_through_lines()[0]

    house = build_block_prompt(tl, 1)
    assert house.render() == build_block_prompt(tl, 1, label=None).render()
    assert '"' not in house.scene
    assert "No text anywhere except" not in house.negative

    diorama = build_block_prompt(tl, 1, kit="diorama")
    assert diorama.render() == build_block_prompt(tl, 1, kit="diorama", label=None).render()
    assert '"' not in diorama.scene
    assert "No text anywhere except" not in diorama.negative
