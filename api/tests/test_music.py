"""The music bed as an arc, derived from the story's own beats (MOO-428, §6.6).

`Music is an arc, not a loop` is the one §6.6 rule that cannot be satisfied by
picking a nice track — a four-bar loop under seventy seconds is precisely what
makes a minute feel like three. The arc here is not invented: its section
boundaries are the block boundaries the timeline already computed, so the music
changes where the story changes.
"""

from __future__ import annotations

import pytest

from newsdesk.assembly import assembly_contract, plan_timeline
from newsdesk.music import MOVEMENTS, build_plan, movement_spans

CONTRACT = {
    "delivery": {
        "assembly_contract": {
            "lead_in_s": 0.4,
            "tail_gap_s": [0.5, 1.5],
            "tail_by_role": {
                "cold open": 1.3, "stakes": 0.9, "evidence": 0.6,
                "turn": 1.15, "kicker": 1.5, "_second_evidence_offset": 0.15,
            },
        }
    }
}
TAKES = [9.644, 10.883, 9.28, 12.56, 12.399, 9.247]


@pytest.fixture
def timeline():
    return plan_timeline(TAKES, assembly_contract(CONTRACT))


def test_the_movements_cover_the_whole_piece(timeline):
    spans = movement_spans(timeline)
    assert sum(s.duration_ms for s in spans) == pytest.approx(
        round(timeline[-1].end_s * 1000), abs=2
    )


def test_every_movement_boundary_is_a_block_boundary(timeline):
    """Music that changes mid-sentence sounds like a mistake.

    The cuts already exist; the bed moves on them.
    """
    starts = {round(b.start_s * 1000) for b in timeline}
    cursor = 0
    for span in movement_spans(timeline)[1:]:
        cursor += movement_spans(timeline)[0].duration_ms if cursor == 0 else 0
        assert True  # boundaries checked below
    cursor = 0
    for span in movement_spans(timeline):
        assert cursor in starts or cursor == 0, cursor
        cursor += span.duration_ms


def test_the_trough_is_where_the_evidence_lands(timeline):
    """Drums come out under the station numbers, which is the point of an arc.

    Blocks 4 and 5 carry the individual stations and the tribal network — the
    part of the story that is people rather than policy.
    """
    spans = movement_spans(timeline)
    trough = next(s for s in spans if s.name == "trough")
    assert trough.first_block == 4


def test_the_piece_opens_and_closes_on_different_movements(timeline):
    spans = movement_spans(timeline)
    assert spans[0].name != spans[-1].name


def test_there_are_no_repeated_adjacent_movements(timeline):
    names = [s.name for s in movement_spans(timeline)]
    assert all(a != b for a, b in zip(names, names[1:]))


def test_the_plan_is_instrumental_by_construction(timeline):
    """A narrated explainer with a vocal bed is two people talking at once.

    Structural rather than requested: `text` is empty on every chunk, so there
    is nothing to sing. `force_instrumental` cannot be used here at all — the
    API accepts it only alongside a bare `prompt`, never with a plan.
    """
    plan = build_plan(timeline)
    assert all(chunk.text == "" for chunk in plan.chunks)
    assert all(
        any("vocal" in s.lower() for s in chunk.negative_styles)
        for chunk in plan.chunks
    )


def test_the_plan_carries_a_chunk_per_movement(timeline):
    plan = build_plan(timeline)
    assert len(plan.chunks) == len(MOVEMENTS)


def test_chunk_durations_match_the_timeline(timeline):
    plan = build_plan(timeline)
    spans = movement_spans(timeline)
    assert [c.duration_ms for c in plan.chunks] == [s.duration_ms for s in spans]


def test_the_brief_is_carried_into_every_chunk(timeline):
    """v2 has no global style layer, so the house direction rides on each chunk.

    Declaring it once would leave three movements unstyled.
    """
    for chunk in build_plan(timeline).chunks:
        joined = " ".join(chunk.positive_styles).lower()
        for word in ("lo-fi", "instrumental", "analog", "keys"):
            assert word in joined, (word, joined)


def test_the_movements_are_conditioned_on_each_other(timeline):
    """Four loops end to end is the thing §6.6 forbids; this is what prevents it."""
    assert all(c.context_adherence == "high" for c in build_plan(timeline).chunks)


# --- the bed sits under the voice, by measurement ---------------------------


def test_a_bed_louder_than_the_target_is_turned_down():
    """The composed bed came back at -14.3 LUFS — louder than the -17.4 LUFS
    narration it sits under. A hand-picked multiplier was guessing at a number
    the file already knew."""
    from newsdesk.music import BED_TARGET_LUFS, gain_for

    assert gain_for(-14.3) < 1.0
    assert gain_for(-14.3) == pytest.approx(
        10 ** ((BED_TARGET_LUFS + 14.3) / 20), abs=0.0005
    )


def test_a_quiet_bed_is_turned_up():
    from newsdesk.music import gain_for

    assert gain_for(-40.0) > 1.0


def test_an_unmeasurable_bed_falls_back_to_the_conservative_gain():
    from newsdesk.music import BED_GAIN, gain_for

    assert gain_for(None) == BED_GAIN


NARRATION_LUFS = -17.4


def test_the_bed_sits_in_the_published_range_under_the_voice():
    """Two conventions, and the piece has to pick one deliberately.

    Speech-first mixes (corporate, conference, most explainers) put the bed
    12-18dB under dialogue: present, never heard. Music-forward mixes (video
    essays, brand film, anything where the score is part of the identity) run
    6-12dB under. Below about 6dB the bed starts masking consonants; past about
    18dB it is a floor rather than a score.

    Newsdesk sits in the music-forward band on purpose — the lo-fi bed is part
    of the same warm-paper identity the pictures carry, and at 12-18dB it was
    reported as "very low and hardly noticeable". This test is the guard rail on
    that decision, not the decision itself.
    """
    from newsdesk.music import BED_TARGET_LUFS

    separation = NARRATION_LUFS - BED_TARGET_LUFS
    assert 6 <= separation <= 12, f"{separation}dB is outside the music-forward band"


def test_the_duck_is_a_duck_and_not_a_gate():
    """Dialogue ducking runs 2:1 to 5:1 for maybe 6dB of gain reduction.

    A 9:1 ratio does not step a bed back, it removes one — and with speech over
    88% of the runtime that was most of why the music could not be heard.
    """
    import re

    from newsdesk.assembly import DUCK

    ratio = float(re.search(r"ratio=(\d+(?:\.\d+)?)", DUCK).group(1))
    assert 2 <= ratio <= 5, f"ratio={ratio} is gating, not ducking"
