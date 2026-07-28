"""Script generation and its governance record (MOO-419 + MOO-433).

Every test injects a fake `chat_fn`. Nothing here reaches a provider, so the
suite stays at $0 and runs with no network — the same property Wall 2 has.
"""

from __future__ import annotations

import json

import pytest
from fixtures import cs1_blocks, cs1_story

from newsdesk.decisions import Ledger
from newsdesk.script import ScriptError, generate_script, parse_blocks
from newsdesk.state import RunState


def _payload(blocks) -> str:
    return json.dumps({
        "blocks": [
            {
                "n": b.n,
                "role": b.role,
                "narration": b.narration,
                "claims": [
                    {"spoken": c.spoken, "fact_id": c.fact_id, "evidence": c.evidence}
                    for c in b.claims
                ],
            }
            for b in blocks
        ]
    })


def _fake_chat(text: str):
    """Stands in for genblaze chat(); returns whatever the test scripted."""

    class _Response:
        def __init__(self, t: str):
            self.text = t
            self.model = "fake-model"
            self.tokens_in = 100
            self.tokens_out = 200

    def _call(*args, **kwargs):
        return _Response(text)

    return _call


def _run() -> RunState:
    return RunState(run_id="test-run", story="Who pays when public radio goes dark?")


# --- parsing ----------------------------------------------------------------


def test_parses_plain_json():
    blocks = parse_blocks(_payload(cs1_blocks()))
    assert len(blocks) == 6
    assert blocks[0].claims[0].fact_id == "F1"


def test_parses_json_inside_a_fenced_code_block():
    """Models fence JSON even when told not to. Refusing to cope is a self-own."""
    fenced = f"Here is the script:\n\n```json\n{_payload(cs1_blocks())}\n```\n"
    assert len(parse_blocks(fenced)) == 6


def test_prose_with_no_json_raises():
    with pytest.raises(ScriptError):
        parse_blocks("I'm sorry, I can't help with that.")


def test_wrong_block_count_raises():
    partial = json.loads(_payload(cs1_blocks()))
    partial["blocks"] = partial["blocks"][:4]
    with pytest.raises(ScriptError):
        parse_blocks(json.dumps(partial))


# --- generation + the ledger ------------------------------------------------


def test_generation_returns_six_blocks():
    state, ledger, blocks = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(_payload(cs1_blocks()))
    )
    assert len(blocks) == 6


def test_a_clean_script_records_a_pass_decision():
    _, ledger, _ = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(_payload(cs1_blocks()))
    )
    assert len(ledger.decisions) == 1
    assert ledger.decisions[0].verdict == "pass"
    assert ledger.decisions[0].role == "script"


def test_an_unmapped_number_records_a_reject_naming_the_claim():
    bad = json.loads(_payload(cs1_blocks()))
    bad["blocks"][0]["narration"] = (
        "Two point six billion dollars in public broadcasting money vanished in a "
        "single July vote. It had already been approved. Congress took it back."
    )
    bad["blocks"][0]["claims"] = []

    _, ledger, blocks = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(json.dumps(bad))
    )
    decision = ledger.decisions[0]
    assert decision.verdict == "reject"
    assert "two point six" in decision.reason.lower()
    assert blocks == ()


def test_a_rejection_changes_the_ledger_digest():
    """The rejection has to reach the manifest, or the receipt is a highlight reel."""
    clean = Ledger()
    _, after, _ = generate_script(
        _run(), clean, cs1_story(), chat_fn=_fake_chat(_payload(cs1_blocks()))
    )
    assert after.digest() != clean.digest()


def test_an_unreachable_model_records_a_reject_rather_than_passing():
    def _boom(*args, **kwargs):
        raise RuntimeError("connection refused")

    _, ledger, blocks = generate_script(_run(), Ledger(), cs1_story(), chat_fn=_boom)
    assert ledger.decisions[0].verdict == "reject"
    assert blocks == ()


def test_the_run_log_records_the_decision():
    state, _, _ = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(_payload(cs1_blocks()))
    )
    assert any(e.kind == "decision.script" for e in state.events)


# --- POL-5 is enforced on generated lines, not assumed ----------------------


def test_a_line_outside_the_pol5_window_is_rejected():
    bad = json.loads(_payload(cs1_blocks()))
    bad["blocks"][2]["narration"] = "Funding stopped."
    bad["blocks"][2]["claims"] = []

    _, ledger, blocks = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(json.dumps(bad))
    )
    assert ledger.decisions[0].verdict == "reject"
    assert "POL-5" in ledger.decisions[0].reason
    assert blocks == ()


def test_the_golden_script_satisfies_pol5():
    """If the fixture itself violates POL-5, every other test here is theatre."""
    from newsdesk.policy.gate import check_narration

    for block in cs1_blocks():
        finding = check_narration(block.narration)
        assert finding.passed, f"block {block.n}: {finding.message}"


# --- the prompt carries the craft, not the caller ---------------------------


def test_the_prompt_names_every_fact_id():
    from newsdesk.script import build_prompt

    prompt = build_prompt(cs1_story())
    for fact in cs1_story().facts:
        assert fact.id in prompt


def test_the_prompt_states_the_calibrated_pol5_window():
    from newsdesk.script import build_prompt

    prompt = build_prompt(cs1_story())
    assert "23" in prompt and "27" in prompt


def test_the_prompt_example_satisfies_pol5():
    """The worked example must obey the rule it demonstrates.

    The first version of it was 22 words against a 23-27 window — a prompt
    demonstrating the failure it is trying to prevent.
    """
    from newsdesk.policy.gate import check_narration
    from newsdesk.script import _EXAMPLE

    finding = check_narration(_EXAMPLE)
    assert finding.passed, finding.message


def test_a_short_line_gets_one_repair_pass_before_rejection():
    """§6.4: one retry, then surface. Not zero, and not an unbounded loop."""
    short = json.loads(_payload(cs1_blocks()))
    short["blocks"][0]["narration"] = "Money vanished."
    short["blocks"][0]["claims"] = []

    calls = []

    def _twice(*args, **kwargs):
        calls.append(kwargs.get("prompt", ""))

        class _R:
            text = json.dumps(short) if len(calls) == 1 else _payload(cs1_blocks())

        return _R()

    _, ledger, blocks = generate_script(_run(), Ledger(), cs1_story(), chat_fn=_twice)
    assert len(calls) == 2, "a short line should trigger exactly one repair pass"
    assert "Block 1" in calls[1], "the repair prompt must name the block that missed"
    assert ledger.decisions[0].verdict == "pass"
    assert "repair" in ledger.decisions[0].reason
    assert len(blocks) == 6


def test_a_fabricated_citation_is_not_retried():
    """Citing a fact that does not say it gets no second chance.

    This is the boundary that matters. An unmapped number is usually a real
    figure the model forgot to declare, so it earns one ask (see the test
    below). Evidence that is not in the cited fact is the model inventing a
    source, and asking politely for a nicer version of that is how a validator
    becomes a formality.
    """
    bad = json.loads(_payload(cs1_blocks()))
    bad["blocks"][0]["claims"] = [
        {
            "spoken": "One point one billion dollars",
            "fact_id": "F1",
            "evidence": "$2.4B",
        }
    ]

    calls = []

    def _count(*args, **kwargs):
        calls.append(1)

        class _R:
            text = json.dumps(bad)

        return _R()

    _, ledger, _ = generate_script(_run(), Ledger(), cs1_story(), chat_fn=_count)
    assert len(calls) == 1
    assert ledger.decisions[0].verdict == "reject"


def test_an_unmapped_number_earns_one_repair_pass():
    """The counterpart to the test above: a forgotten mapping is asked about once."""
    bad = json.loads(_payload(cs1_blocks()))
    bad["blocks"][1]["narration"] = (
        "The corporation that had routed federal money to more than fifteen "
        "hundred local stations since nineteen sixty-seven voted to dissolve in "
        "twenty twenty-six."
    )

    calls = []

    def _twice(*args, **kwargs):
        calls.append(kwargs.get("prompt", ""))

        class _R:
            text = json.dumps(bad) if len(calls) == 1 else _payload(cs1_blocks())

        return _R()

    _, ledger, blocks = generate_script(_run(), Ledger(), cs1_story(), chat_fn=_twice)
    assert len(calls) == 2
    assert "quantity with no claim" in calls[1]
    assert ledger.decisions[0].verdict == "pass"
    assert len(blocks) == 6
