"""CS-4 — the red-team battery. Runs entirely offline and asserts $0 spent.

Production readiness is proven by what the system refuses. This is the sharpest
test in the repo and the demo's best twenty seconds: six adversarial requests,
every rejection citing a rule, and a spend counter that reads exactly zero
because the gate has no provider to call.

The counter is not decoration. If someone later wires a network call into the
gate, `test_structure.py` fails on the import and this fails on the spend.
"""

from __future__ import annotations

import pytest

from newsdesk.blockprompt import BlockPrompt, negative_line
from newsdesk.facts import FactError, Source, Story
from newsdesk.policy.gate import check


class SpendCounter:
    """Stands in for every provider. Any call at all is a test failure."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.usd = 0.0

    def __call__(self, *args, **kwargs):
        self.calls.append(f"{args}{kwargs}")
        self.usd += 999.0  # so a leak is unmistakable rather than a rounding error
        raise AssertionError("a provider was called during a gate-only test")


@pytest.fixture
def spend() -> SpendCounter:
    return SpendCounter()


def block(scene: str, *, motion: str = "Slow push-in.", audio: str = "Ambient hum.") -> BlockPrompt:
    return BlockPrompt.build(1, scene=scene, motion=motion, audio=audio)


# --- R1-R4: must be refused -------------------------------------------------


def test_r1_named_likeness_rejected(spend):
    result = check(block(
        "The president stands at a podium reacting to results, cut out on torn paper."
    ))
    assert not result.passed
    assert any(f.rule_id == "POL-1" for f in result.failures())
    assert "silhouette" in result.explain()  # teaches the boundary, not just refuses
    assert spend.usd == 0.0


def test_r2_photoreal_news_scene_rejected(spend):
    result = check(block(
        "Make it look like real news footage of the crowd outside city hall at night."
    ))
    assert not result.passed
    assert any(f.rule_id == "POL-3" for f in result.failures())
    assert spend.usd == 0.0


def test_r3_unsourced_fact_blocked_at_intake(spend):
    story = Story.build("Election night", [("turnout hit a record high", [])])
    with pytest.raises(FactError) as exc:
        story.validate()
    assert "F1" in str(exc.value)  # names the offending fact, not "invalid input"
    assert spend.usd == 0.0


def test_r4_unsourced_on_prop_text_rejected(spend):
    result = check(block(
        'A torn paper placard in the foreground with the word "RIGGED?" on it.'
    ))
    assert not result.passed
    assert any(f.rule_id == "POL-4" for f in result.failures())
    assert spend.usd == 0.0


def test_pol2_modified_negative_line_rejected(spend):
    tampered = block("A paper ballot box, flat navy field.")
    tampered = type(tampered)(**{**tampered.__dict__, "negative": "photorealism only"})
    result = check(tampered)
    assert any(f.rule_id == "POL-2" for f in result.failures())
    assert spend.usd == 0.0


# --- R5: the compliant retry must PASS --------------------------------------


def test_r5_compliant_retry_passes(spend):
    """The gate teaches the boundary rather than dead-ending the journalist."""
    result = check(block(
        "An abstract dark silhouette stands at an empty podium, rendered as a torn "
        "paper cutout against a flat navy field. Hand-drawn marker rings radiate outward."
    ))
    assert result.passed, result.explain()
    assert spend.usd == 0.0


# --- CS-2: the false-positive control ---------------------------------------


def test_cs2_control_story_trips_nothing(spend):
    """If the upbeat vinyl story trips a gate, the gate is miscalibrated."""
    result = check(
        block(
            "A record spins at the centre of a warm yellow field, growing from a coaster "
            "to a monument. Paper-disc bars rise beside it; a crate-digging hand cutout "
            "reaches in from the left."
        ),
        narration="Vinyl revenue passed one billion dollars in the United States last year, the first time that has happened since nineteen eighty-three.",
    )
    assert result.passed, result.explain()
    assert spend.usd == 0.0


# --- POL-5 --------------------------------------------------------------------


@pytest.mark.parametrize(
    "narration,should_pass",
    [
        ("Vinyl revenue passed one billion dollars in the United States last year, the first time that has happened since nineteen eighty-three.", True),
        ("Vinyl is up.", False),
        (" ".join(["word"] * 40), False),
    ],
)
def test_pol5_narration_window(narration, should_pass, spend):
    result = check(block("A record spins on warm yellow paper."), narration=narration)
    pol5 = [f for f in result.findings if f.rule_id == "POL-5"]
    assert pol5, "POL-5 did not run"
    assert pol5[0].passed is should_pass, pol5[0].message
    assert spend.usd == 0.0


# --- the whole point ----------------------------------------------------------


def test_entire_battery_costs_nothing(spend):
    for scene in [
        "The president signing a bill at a desk.",
        "Photorealistic live-action footage of a newsroom.",
        'A sign that reads "STOLEN" in the foreground.',
        "An abstract silhouette at an empty podium, torn paper cutout.",
    ]:
        check(block(scene))
    assert spend.calls == []
    assert spend.usd == 0.0
    assert negative_line()  # brand kit loaded from disk, not the network
