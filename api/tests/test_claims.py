"""The claim->fact validator (MOO-419, P0-2).

CS-1 is the happy path; CS-3's strictness probe is the one that matters. Both
run offline against pure functions — no chat(), no provider, $0.
"""

from __future__ import annotations

import dataclasses

import pytest
from fixtures import cs1_blocks, cs1_story

from newsdesk.claims import Claim, ScriptBlock, validate_script


# --- CS-1: the happy path ---------------------------------------------------


def test_cs1_script_passes():
    result = validate_script(cs1_story(), cs1_blocks())
    assert result.passed, result.explain()


def test_cs1_every_fact_is_used_by_some_block():
    """No orphan facts — the acceptance criterion is F1-F6 with no orphans."""
    used = {c.fact_id for b in cs1_blocks() for c in b.claims}
    assert used == {f.id for f in cs1_story().facts}


# --- CS-3: strictness -------------------------------------------------------


def test_number_with_no_claim_is_rejected():
    """The CS-3 probe: a narration number that traces to nothing."""
    story = cs1_story()
    bad = ScriptBlock(
        n=1,
        role="cold open",
        narration=(
            "Thirty-one percent of your dollar goes to policing. That share has "
            "grown quietly for years, and nobody voted on it."
        ),
        claims=(),
    )
    result = validate_script(story, (bad,))
    assert not result.passed
    assert "thirty-one" in result.explain().lower()


def test_rejection_names_the_offending_claim():
    story = cs1_story()
    bad = ScriptBlock(
        n=2,
        role="stakes",
        narration="Ninety percent of stations went dark. Nobody counted them.",
        claims=(),
    )
    assert "ninety" in validate_script(story, (bad,)).explain().lower()


def test_unknown_fact_id_is_rejected():
    story = cs1_story()
    block = ScriptBlock(
        n=1,
        role="cold open",
        narration="One point one billion dollars vanished. It had been approved.",
        claims=(Claim(spoken="One point one billion dollars", fact_id="F9", evidence="$1.1B"),),
    )
    result = validate_script(story, (block,))
    assert not result.passed
    assert "F9" in result.explain()


def test_evidence_absent_from_the_cited_fact_is_rejected():
    """Citing a real fact that does not actually say it is the subtler failure."""
    story = cs1_story()
    block = ScriptBlock(
        n=1,
        role="cold open",
        narration="Two point four billion dollars vanished. It had been approved.",
        claims=(Claim(spoken="Two point four billion dollars", fact_id="F1", evidence="$2.4B"),),
    )
    result = validate_script(story, (block,))
    assert not result.passed
    assert "$2.4B" in result.explain()


def test_spoken_phrase_absent_from_the_narration_is_rejected():
    """A mapping that describes a line the script does not contain is not a mapping."""
    story = cs1_story()
    block = ScriptBlock(
        n=1,
        role="cold open",
        narration="Money vanished from public broadcasting. It had been approved.",
        claims=(Claim(spoken="One point one billion dollars", fact_id="F1", evidence="$1.1B"),),
    )
    assert not validate_script(story, (block,)).passed


# --- calibration: the gate must not block legitimate copy -------------------


def test_prose_without_numbers_needs_no_claim():
    """CS-2's lesson: a validator that fires on everything gets switched off."""
    story = cs1_story()
    block = ScriptBlock(
        n=6,
        role="kicker",
        narration=(
            "The tower still stands. What lights it now is smaller, local, and "
            "paid for by the people who happen to live near it."
        ),
        claims=(),
    )
    assert validate_script(story, (block,)).passed


def test_evidence_match_ignores_case_and_spacing():
    story = cs1_story()
    block = dataclasses.replace(
        cs1_blocks()[3],
        claims=(
            Claim(spoken="a third", fact_id="F4", evidence="A  THIRD   of its budget"),
            Claim(spoken="one point two million dollars", fact_id="F4", evidence="$1.2M"),
            Claim(spoken="forty-eight percent", fact_id="F4", evidence="48% of revenue"),
        ),
    )
    assert validate_script(story, (block,)).passed


@pytest.mark.parametrize(
    "phrase",
    ["fifteen hundred", "seventy percent", "1,500", "48%", "a third", "nineteen sixty-seven"],
)
def test_number_bearing_phrases_are_detected(phrase):
    """If the detector misses these, the CS-3 probe passes vacuously."""
    from newsdesk.claims import number_tokens

    assert number_tokens(phrase), f"{phrase!r} should read as number-bearing"


@pytest.mark.parametrize("phrase", ["the tower still stands", "grants were closed out"])
def test_plain_prose_is_not_number_bearing(phrase):
    from newsdesk.claims import number_tokens

    assert not number_tokens(phrase)
