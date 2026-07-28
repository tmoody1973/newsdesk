"""Assembly timing — audio leads, picture follows (MOO-428, design spec §6.6).

The timing model is pure functions so §6.6's rules are testable at $0 before any
ffmpeg runs. Each rule here exists to remove a named failure, and several of them
are assertions that something does *not* happen — the fixed window, the centred
take, the evenly spaced gap — because those are the things that make an explainer
feel machine-made and none of them announce themselves in a render.
"""

from __future__ import annotations

import pytest

from newsdesk.assembly import (
    AssemblyError,
    ROLES,
    approved_or_raise,
    ass_document,
    assembly_contract,
    clip_action,
    plan_timeline,
    subtitle_cues,
)
from newsdesk.state import RunState

CONTRACT = {
    "delivery": {
        "assembly_contract": {
            "lead_in_s": 0.4,
            "tail_gap_s": [0.5, 1.5],
            "tail_by_role": {
                "cold open": 1.3,
                "stakes": 0.9,
                "evidence": 0.6,
                "turn": 1.15,
                "kicker": 1.5,
                "_second_evidence_offset": 0.15,
            },
        }
    }
}

# The six measured CS-1 takes, trimmed.
TAKES = [9.644, 10.883, 9.28, 12.56, 12.399, 9.247]


@pytest.fixture
def contract():
    return assembly_contract(CONTRACT)


@pytest.fixture
def timeline(contract):
    return plan_timeline(TAKES, contract)


# --- the contract is published, not compiled in ----------------------------


def test_the_lead_in_comes_from_the_brand_kit(contract):
    assert contract.lead_in_s == 0.4


def test_the_tail_range_comes_from_the_brand_kit(contract):
    assert contract.tail_range == (0.5, 1.5)


def test_a_kit_without_an_assembly_contract_raises():
    with pytest.raises(AssemblyError):
        assembly_contract({"delivery": {}})


def test_every_published_tail_sits_inside_the_published_range(contract):
    low, high = contract.tail_range
    assert all(low <= contract.tail_for(role) <= high for role in ROLES)


# --- block length follows the take -----------------------------------------


def test_block_length_is_lead_in_plus_take_plus_tail(timeline):
    for block in timeline:
        assert block.length_s == pytest.approx(
            block.lead_in_s + block.take_s + block.tail_s
        )


def test_narration_starts_after_the_cut_not_on_it(timeline):
    """The viewer needs a beat to read a new image before a voice starts.

    Narration landing on the cut means the shot is never actually seen.
    """
    for block in timeline:
        assert block.narration_start_s == pytest.approx(block.start_s + 0.4)


def test_the_take_is_never_centred(timeline):
    """Centring is the failure §6.6 was written to remove.

    A centred take puts dead air at BOTH ends of every block. If the lead-in ever
    equals the tail, something has started centring.
    """
    for block in timeline:
        assert block.lead_in_s != block.tail_s


def test_no_block_shares_a_length_with_another(timeline):
    """A fixed window would make all six identical. This is that alarm."""
    assert len({round(b.length_s, 3) for b in timeline}) == len(timeline)


def test_no_two_gaps_between_lines_are_identical(timeline):
    """Evenly spaced gaps are what machine-cut video sounds like.

    The gap between one line ending and the next beginning is this block's tail
    plus the next block's lead-in. With a constant lead-in that reduces to the
    tails, and the six-beat formula hands two consecutive blocks the same role —
    which is why the kit carries a second-evidence offset.
    """
    gaps = [
        round(timeline[i].tail_s + timeline[i + 1].lead_in_s, 3)
        for i in range(len(timeline) - 1)
    ]
    assert len(set(gaps)) == len(gaps), f"duplicate gaps: {gaps}"


def test_blocks_run_back_to_back_with_no_overlap(timeline):
    for a, b in zip(timeline, timeline[1:]):
        assert b.start_s == pytest.approx(a.start_s + a.length_s)


def test_the_first_block_starts_at_zero(timeline):
    assert timeline[0].start_s == 0.0


def test_the_take_length_is_the_measured_one(timeline):
    assert [b.take_s for b in timeline] == TAKES


def test_total_runtime_is_the_sum_of_the_blocks(timeline):
    total = timeline[-1].start_s + timeline[-1].length_s
    assert total == pytest.approx(sum(b.length_s for b in timeline))


def test_a_missing_take_is_refused_rather_than_guessed():
    """A block with no measured take cannot be timed, and inventing one is worse."""
    with pytest.raises(AssemblyError):
        plan_timeline([9.6, None, 9.2], assembly_contract(CONTRACT))


# --- the clip serves the voice ---------------------------------------------


def test_a_clip_longer_than_its_block_is_trimmed():
    action, seconds = clip_action(clip_s=10.0, block_s=8.5)
    assert action == "trim"
    assert seconds == pytest.approx(8.5)


def test_a_clip_shorter_than_its_block_holds_its_last_frame():
    action, seconds = clip_action(clip_s=10.0, block_s=11.75)
    assert action == "hold"
    assert seconds == pytest.approx(1.75)


def test_a_clip_that_already_fits_is_left_alone():
    action, _ = clip_action(clip_s=10.0, block_s=10.0)
    assert action == "fit"


def test_the_clip_is_never_stretched():
    """There is no third verb. Stretching video to fit audio is a named never."""
    verbs = {clip_action(10.0, b)[0] for b in (5.0, 10.0, 20.0)}
    assert verbs <= {"trim", "hold", "fit"}


# --- Wall 3 ----------------------------------------------------------------


def test_assembly_refuses_a_run_with_no_approval():
    """Structural, not a UI check. There is no other way to satisfy Wall 3."""
    with pytest.raises(AssemblyError, match="approv"):
        approved_or_raise(RunState(run_id="r", story="s"))


def test_assembly_accepts_an_approved_run():
    state = RunState(run_id="r", story="s").approve("Tarik Moody")
    assert approved_or_raise(state).approver == "Tarik Moody"


def test_the_approval_carries_a_timestamp():
    state = RunState(run_id="r", story="s").approve("Tarik Moody")
    assert approved_or_raise(state).ts


# --- subtitles -------------------------------------------------------------

LINE = (
    "Three hundred thousand households lost their water subsidy in a single "
    "budget cycle. Nobody announced it. The line item simply stopped appearing."
)


def test_cues_start_when_the_narration_does():
    cues = subtitle_cues(LINE, start_s=4.0, take_s=9.6)
    assert cues[0].start_s == pytest.approx(4.0)


def test_cues_end_when_the_take_does():
    cues = subtitle_cues(LINE, start_s=4.0, take_s=9.6)
    assert cues[-1].end_s == pytest.approx(13.6)


def test_no_cue_carries_more_than_two_lines():
    for cue in subtitle_cues(LINE, start_s=0.0, take_s=9.6):
        assert len(cue.text.split("\\N")) <= 2


def test_cues_do_not_overlap():
    cues = subtitle_cues(LINE, start_s=0.0, take_s=9.6)
    for a, b in zip(cues, cues[1:]):
        assert b.start_s >= a.end_s


def test_every_word_survives_the_split():
    """A caption that silently drops a word is a caption that misquotes."""
    cues = subtitle_cues(LINE, start_s=0.0, take_s=9.6)
    spoken = " ".join(c.text.replace("\\N", " ") for c in cues)
    assert spoken.split() == LINE.upper().split()


def test_cues_are_offset_by_the_lead_in_not_by_the_block_start():
    """Timed to the trimmed audio, which begins 0.4s into its block."""
    early = subtitle_cues(LINE, start_s=0.0, take_s=9.6)
    late = subtitle_cues(LINE, start_s=0.4, take_s=9.6)
    assert late[0].start_s - early[0].start_s == pytest.approx(0.4)


# --- the ASS document ffmpeg will actually accept ---------------------------

KIT_ASS = """; Newsdesk burned-in subtitle style (MOO-425)
;
; Anton, uppercase, ink on a pasteboard halo.

[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname
Style: Default,Anton

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,ANTON RESOLVED — STYLE KEY OK
"""


def test_the_document_starts_at_the_script_info_header():
    """ffmpeg's ASS demuxer rejects a file with anything before [Script Info].

    Measured 2026-07-28: the kit's leading comment block made the whole burn
    fail — and the error it produced was `Unable to open <path>`, which points
    at the filename and not at the content. The comments are documentation for
    whoever edits the kit; they are not part of what ships to libass.
    """
    doc = ass_document(KIT_ASS, ())
    assert doc.startswith("[Script Info]")


def test_the_probe_line_does_not_survive_into_a_render():
    """The kit ships one Dialogue line reading ANTON RESOLVED, to be burned once
    and looked at. A probe that reaches a finished video is a caption nobody
    wrote."""
    assert "ANTON RESOLVED" not in ass_document(KIT_ASS, ())


def test_the_styles_survive():
    doc = ass_document(KIT_ASS, ())
    assert "Style: Default,Anton" in doc
    assert "PlayResX: 1080" in doc


def test_cues_are_written_as_dialogue_lines():
    cues = subtitle_cues("Nobody announced it.", start_s=1.5, take_s=2.0)
    doc = ass_document(KIT_ASS, cues)
    assert "Dialogue: 0,0:00:01.50,0:00:03.50,Default,,0,0,0,,NOBODY ANNOUNCED IT." in doc


def test_captions_are_uppercased_because_the_kit_says_so():
    """ASS has no text-transform, so "Anton, uppercase" has to happen here.

    The kit's continuity rule is that the tool and the media it produces look
    like the same product, and the app's stamps are uppercase Anton. A
    lowercase caption in the same face reads as a different component.
    """
    assert subtitle_cues("Nobody announced it.", start_s=0.0, take_s=2.0)[0].text == (
        "NOBODY ANNOUNCED IT."
    )


# --- captions must not break a spoken number --------------------------------
#
# Every figure in this product is spelled out, because POL rules require numbers
# to be written as they are said. That makes a mid-number line break a recurring
# defect rather than an unlucky one — the live CS-1 cut produced
# "KUAC IN FAIRBANKS LOST ONE / POINT TWO MILLION DOLLARS AND CUT".


def _lines(cues):
    return [line for c in cues for line in c.text.split("\\N")]


def test_a_spelled_out_number_never_breaks_across_lines():
    line = ("KUAC in Fairbanks lost one point two million dollars and cut "
            "overnight broadcasts entirely.")
    for text in _lines(subtitle_cues(line, start_s=0.0, take_s=9.6)):
        assert not text.endswith("ONE"), text
        assert not text.startswith("POINT"), text


def test_a_long_number_run_stays_whole():
    line = "One point one billion dollars vanished from the budget in a single year."
    joined = " ".join(_lines(subtitle_cues(line, start_s=0.0, take_s=9.6)))
    assert "ONE POINT ONE BILLION" in joined


def test_a_number_run_is_not_split_across_two_cues():
    line = ("The rescissions package eliminated one point one billion dollars in "
            "previously approved funding covering two fiscal years of public media.")
    for cue in subtitle_cues(line, start_s=0.0, take_s=9.6):
        text = cue.text.replace("\\N", " ")
        assert not text.endswith("ONE POINT"), text


def test_a_bare_and_still_breaks_normally():
    """`and` joins a number run only when numbers sit on both sides of it.

    Otherwise the commonest word in English becomes unbreakable and every cue
    grows a tail.
    """
    line = "The stations went dark and the listeners noticed and nobody explained why."
    cues = subtitle_cues(line, start_s=0.0, take_s=9.6)
    assert len(_lines(cues)) > 1


def test_no_line_ends_on_a_stranded_short_word():
    """A line ending in "a" or "of" reads as a typo, not as a line break."""
    line = ("A third of its operating budget vanished in a single quarter of the "
            "financial year without any public announcement at all.")
    for text in _lines(subtitle_cues(line, start_s=0.0, take_s=9.6)):
        assert text.split()[-1] not in {"A", "OF", "IN", "TO", "AT", "AN", "THE"}, text


# --- the bed is ducked, never faded by hand ---------------------------------


def test_the_bed_is_keyed_off_the_voice(timeline):
    from newsdesk.assembly import build_filtergraph

    graph = build_filtergraph(timeline, [10.0] * 6, 6, music_index=12)
    assert "sidechaincompress" in graph
    assert "[bed][key]" in graph


def test_there_is_no_music_leg_without_music(timeline):
    from newsdesk.assembly import build_filtergraph

    graph = build_filtergraph(timeline, [10.0] * 6, 6)
    assert "sidechaincompress" not in graph
    assert graph.endswith("[aout]")


def test_the_bed_never_outlives_the_picture(timeline):
    from newsdesk.assembly import build_filtergraph

    graph = build_filtergraph(timeline, [10.0] * 6, 6, music_index=12)
    assert f"atrim=0:{timeline[-1].end_s:.3f}" in graph


def test_nothing_in_the_graph_re_times_audio_or_video(timeline):
    """The four nevers, asserted against the actual command rather than the docs."""
    from newsdesk.assembly import build_filtergraph

    graph = build_filtergraph(timeline, [10.0] * 6, 6, music_index=12)
    assert "atempo" not in graph
    assert "rubberband" not in graph
    assert "setpts=" not in graph.replace("setpts=PTS-STARTPTS", "").replace(
        "asetpts=N/SR/TB", ""
    )


# --- delivery master --------------------------------------------------------


def test_the_master_gain_reaches_the_platform_target():
    """Platforms normalise DOWN, not up. A quiet file just plays quiet."""
    from newsdesk.assembly import DELIVERY_LUFS, master_gain_db

    assert master_gain_db(-17.4, -3.6) == pytest.approx(DELIVERY_LUFS + 17.4, abs=0.05)


def test_the_master_never_pushes_past_the_true_peak_ceiling():
    """A file that clips on a lossy encode is worse than one that plays quiet.

    Headroom is the binding constraint, not the loudness target.
    """
    from newsdesk.assembly import TRUE_PEAK_CEILING_DB, master_gain_db

    gain = master_gain_db(-30.0, -0.5)  # very quiet, almost no headroom
    assert -0.5 + gain <= TRUE_PEAK_CEILING_DB + 0.01


def test_an_already_loud_mix_is_turned_down_not_left_alone():
    from newsdesk.assembly import master_gain_db

    assert master_gain_db(-11.0, -6.0) < 0


def test_a_mix_already_at_target_is_left_alone():
    from newsdesk.assembly import DELIVERY_LUFS, master_gain_db

    assert master_gain_db(DELIVERY_LUFS, -6.0) == pytest.approx(0.0, abs=0.01)
