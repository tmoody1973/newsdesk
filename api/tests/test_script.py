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
