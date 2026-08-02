"""Script generation and its governance record (MOO-419 + MOO-433).

Every test injects a fake `chat_fn`. Nothing here reaches a provider, so the
suite stays at $0 and runs with no network — the same property Wall 2 has.
"""

from __future__ import annotations

import json

import pytest
from fixtures import cs1_blocks, cs1_story

from newsdesk.claims import normalize, validate_script
from newsdesk.decisions import Ledger
from newsdesk.policy.gate import check_narration
from newsdesk.script import (
    ScriptError,
    accepts_temperature,
    chat,
    generate_script,
    parse_blocks,
    wants_thinking_disabled,
)
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


def test_a_citation_to_a_nonexistent_fact_is_not_retried():
    """Citing a fact that does not exist gets no second chance.

    This is the boundary that survived contact with the live run. Abridged
    evidence and forgotten mappings have benign readings and earn one ask;
    inventing a fact ID does not — no rewrite makes F9 exist.
    """
    bad = json.loads(_payload(cs1_blocks()))
    bad["blocks"][0]["claims"] = [
        {
            "spoken": "One point one billion dollars",
            "fact_id": "F9",
            "evidence": "$1.1B",
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


# --- unused facts: repaired once, then surfaced, never gated -----------------


def _payload_missing_f3() -> str:
    """CS-1 with block 3 re-pointed at F2, so F3 goes unused.

    Rewritten 2026-07-28. The old version made block 3 carry NO claims at all,
    which is now itself a violation (`untraced_block`) — so the test would have
    been measuring the wrong refusal. An unused fact has to be isolated from
    every other rule to prove it does not block on its own, so this block still
    traces cleanly; it just traces somewhere else.
    """
    payload = json.loads(_payload(cs1_blocks()))
    payload["blocks"][2]["narration"] = (
        "The corporation had routed federal money to more than fifteen hundred "
        "local stations since nineteen sixty-seven. Then the pipeline closed. "
        "Nothing replaced it."
    )
    payload["blocks"][2]["claims"] = [
        {
            "spoken": "The corporation had routed federal money to more than "
                      "fifteen hundred local stations",
            "fact_id": "F2",
            "evidence": "the conduit distributing federal funds to 1,500+ local "
                        "public radio and",
        },
        {"spoken": "since nineteen sixty-seven", "fact_id": "F2", "evidence": "since 1967"},
    ]
    return json.dumps(payload)


def test_an_unused_fact_earns_one_repair_pass():
    calls = []

    def _twice(*args, **kwargs):
        calls.append(kwargs.get("prompt", ""))

        class _R:
            text = _payload_missing_f3() if len(calls) == 1 else _payload(cs1_blocks())

        return _R()

    _, ledger, blocks = generate_script(_run(), Ledger(), cs1_story(), chat_fn=_twice)
    assert len(calls) == 2, "an unused fact should be asked about once"
    assert "F3" in calls[1], "the repair prompt must name the fact that went unused"
    assert ledger.decisions[0].verdict == "pass"
    assert len(blocks) == 6


def test_an_unused_fact_never_blocks_the_script():
    """It is not a policy rule. Nothing false reaches the screen because of it."""
    _, ledger, blocks = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(_payload_missing_f3())
    )
    assert ledger.decisions[0].verdict == "pass"
    assert len(blocks) == 6


def test_a_fact_still_unused_after_the_ask_is_surfaced():
    """Before the ask an orphan is noise; after it, it means something."""
    _, ledger, _ = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(_payload_missing_f3())
    )
    assert "F3" in ledger.decisions[0].reason
    assert "unused" in ledger.decisions[0].reason


# --- throttling is waited out, not recorded as a refusal ---------------------


def test_a_rate_limit_is_retried_not_recorded_as_a_reject(monkeypatch):
    """A busy queue is not an editorial judgment. Recording it as one would put
    'blocked' in the ledger for a script nobody ever objected to."""
    monkeypatch.setattr("newsdesk.script.RETRY_DELAYS", (0, 0, 0))
    calls = []

    def _throttled_once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError('GMICloud chat failed (429): rate_limit_exceeded')

        class _R:
            text = _payload(cs1_blocks())

        return _R()

    _, ledger, blocks = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_throttled_once
    )
    assert len(calls) == 2
    assert ledger.decisions[0].verdict == "pass"
    assert len(blocks) == 6


def test_a_non_throttle_error_is_not_retried(monkeypatch):
    """Only throttles get patience. A bad slug should fail on the first try."""
    monkeypatch.setattr("newsdesk.script.RETRY_DELAYS", (0, 0, 0))
    calls = []

    def _boom(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("model not found")

    _, ledger, _ = generate_script(_run(), Ledger(), cs1_story(), chat_fn=_boom)
    assert len(calls) == 1
    assert ledger.decisions[0].verdict == "reject"
    assert "model not found" in ledger.decisions[0].reason


def test_abridged_evidence_earns_one_repair_pass():
    """Quoting around an appositive is abridgement, not invention.

    The live CS-1 run produced exactly this: "CPB announced it would wind down"
    quoted from a fact carrying a clause between "CPB" and "announced". No string
    check can tell that from a fabrication, so it gets one ask.
    """
    bad = json.loads(_payload(cs1_blocks()))
    bad["blocks"][1]["claims"] = [
        {"spoken": "fifteen hundred", "fact_id": "F2", "evidence": "CPB announced it would wind down"},
        {"spoken": "nineteen sixty-seven", "fact_id": "F2", "evidence": "1967"},
    ]

    calls = []

    def _twice(*args, **kwargs):
        calls.append(kwargs.get("prompt", ""))

        class _R:
            text = json.dumps(bad) if len(calls) == 1 else _payload(cs1_blocks())

        return _R()

    _, ledger, blocks = generate_script(_run(), Ledger(), cs1_story(), chat_fn=_twice)
    assert len(calls) == 2
    assert ledger.decisions[0].verdict == "pass"
    assert len(blocks) == 6


def test_evidence_must_still_be_verbatim_in_an_accepted_script():
    """The guarantee, not the number of chances. Retrying must never launder it."""
    bad = json.loads(_payload(cs1_blocks()))
    bad["blocks"][0]["claims"] = [
        {"spoken": "One point one billion dollars", "fact_id": "F1", "evidence": "$2.4B"}
    ]

    _, ledger, blocks = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(json.dumps(bad))
    )
    assert ledger.decisions[0].verdict == "reject"
    assert blocks == ()
    assert "$2.4B" in ledger.decisions[0].reason


def test_a_claim_bolted_on_without_editing_the_line_earns_one_repair_pass():
    """What the model actually did when asked to place an unused fact: it added
    a claim to block 6 whose quoted phrase was nowhere in block 6's narration."""
    bad = json.loads(_payload(cs1_blocks()))
    bad["blocks"][5]["claims"].append(
        {"spoken": "CPB cut staff roughly seventy percent", "fact_id": "F3", "evidence": "~70%"}
    )

    calls = []

    def _twice(*args, **kwargs):
        calls.append(kwargs.get("prompt", ""))

        class _R:
            text = json.dumps(bad) if len(calls) == 1 else _payload(cs1_blocks())

        return _R()

    _, ledger, blocks = generate_script(_run(), Ledger(), cs1_story(), chat_fn=_twice)
    assert ledger.decisions[0].verdict == "pass"
    assert len(blocks) == 6


def test_every_check_still_holds_on_an_accepted_script():
    """The invariant that never moved, asserted directly rather than trusted."""
    _, _, blocks = generate_script(
        _run(), Ledger(), cs1_story(), chat_fn=_fake_chat(_payload(cs1_blocks()))
    )
    story = cs1_story()
    known = {f.id for f in story.facts}
    for b in blocks:
        assert check_narration(b.narration).passed
        for c in b.claims:
            assert c.fact_id in known
            assert normalize(c.spoken) in normalize(b.narration)
            assert normalize(c.evidence) in normalize(story.by_id(c.fact_id).text)
    assert validate_script(story, blocks).passed


# --- attaching claims to narration that already exists -----------------------


def _stripped(blocks):
    """The same six lines with their claims removed — a run voiced before its
    claim map was captured."""
    from dataclasses import replace
    return tuple(replace(b, claims=()) for b in blocks)


def _claim_reply(blocks):
    return json.dumps({"blocks": [
        {"n": b.n, "claims": [
            {"spoken": c.spoken, "fact_id": c.fact_id, "evidence": c.evidence}
            for c in b.claims
        ]}
        for b in blocks
    ]})


def test_claims_are_mapped_onto_narration_without_changing_it():
    """A run voiced before its claims were captured can still be traced.

    The narration is fixed input here, not something the model may improve: the
    takes were rendered from these exact words and a human approved the cut. A
    mapper that rewrote a line would silently invalidate both.
    """
    from newsdesk.script import map_claims

    blocks = cs1_blocks()
    _, _, mapped = map_claims(
        _run(), Ledger(), cs1_story(), _stripped(blocks),
        chat_fn=_fake_chat(_claim_reply(blocks)),
    )
    assert [b.narration for b in mapped] == [b.narration for b in blocks]
    assert all(b.claims for b in mapped)


def test_a_mapping_that_cites_a_missing_fact_is_refused():
    """The mapper is untrusted for the same reason the generator is."""
    from newsdesk.script import map_claims

    bad = json.dumps({"blocks": [{"n": 1, "claims": [
        {"spoken": "One point one billion dollars", "fact_id": "F9",
         "evidence": "$1.1B"}
    ]}]})
    _, ledger, mapped = map_claims(
        _run(), Ledger(), cs1_story(), _stripped(cs1_blocks())[:1],
        chat_fn=_fake_chat(bad),
    )
    assert mapped == ()
    assert ledger.decisions[-1].verdict == "reject"


def test_the_mapping_is_recorded_in_the_ledger():
    """chat() produces no manifest entry of its own, so the decision has to be
    written down or the receipt is silent about how the tracing was produced."""
    from newsdesk.script import map_claims

    blocks = cs1_blocks()
    _, ledger, _ = map_claims(
        _run(), Ledger(), cs1_story(), _stripped(blocks),
        chat_fn=_fake_chat(_claim_reply(blocks)),
    )
    assert ledger.decisions[-1].role == "claim_map"


# --- temperature, and the family that refuses it ----------------------------
#
# Measured 2026-08-02 on GMI: `anthropic/claude-sonnet-5` and `-opus-5` return
# 400 "`temperature` is deprecated for this model" at 0.2, and 200 with it
# omitted. The 4.x family accepts it. `judged()` records a 400 as a *reject*, so
# without the guard a wrong parameter impersonates a governance decision — the
# whole point of these tests is that only the checker gets to refuse.


@pytest.mark.parametrize("model", [
    "anthropic/claude-sonnet-5",
    "anthropic/claude-opus-5",
    "anthropic/claude-fable-5",
    "anthropic/claude-sonnet-5-20260514",   # dated builds are the same family
    "claude-sonnet-5",                      # Anthropic-direct ids carry no prefix
])
def test_the_claude_5_family_is_asked_without_a_temperature(model):
    assert not accepts_temperature(model)


@pytest.mark.parametrize("model", [
    "anthropic/claude-haiku-4.5",           # the production script model
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-4.8",
    "claude-haiku-4-5-20251001",            # the escape hatch's default id
    "deepseek-ai/DeepSeek-V3-0324",
])
def test_every_other_model_keeps_its_temperature(model):
    """A guard that fires on everything is a guard that gets deleted."""
    assert accepts_temperature(model)


def test_a_claude_5_call_reaches_the_provider_with_no_temperature(monkeypatch):
    """The regex is only half of it — chat() has to actually drop the kwarg."""
    seen: dict = {}

    def _spy(model, **kwargs):
        seen.update(kwargs, model=model)
        return type("R", (), {"text": "ok"})()

    monkeypatch.setattr("newsdesk.script._gmi_chat", _spy)
    chat("anthropic/claude-sonnet-5", prompt="hi", temperature=0.2, max_tokens=16)
    assert "temperature" not in seen
    assert seen["prompt"] == "hi" and seen["max_tokens"] == 16


def test_a_claude_4_call_keeps_the_temperature_it_was_given(monkeypatch):
    seen: dict = {}

    def _spy(model, **kwargs):
        seen.update(kwargs)
        return type("R", (), {"text": "ok"})()

    monkeypatch.setattr("newsdesk.script._gmi_chat", _spy)
    chat("anthropic/claude-haiku-4.5", prompt="hi", temperature=0.4, max_tokens=16)
    assert seen["temperature"] == 0.4


# --- thinking, and the 200 OK that carries nothing ---------------------------
#
# The Claude 5 family reasons past its whole output budget on a prompt this
# size — GMI reported thinking_tokens == output_tokens == 4000 and a content
# block of length zero. An empty 200 is worse than a 400: it reaches
# parse_blocks as "the model did not return JSON" and judged() files it as a
# reject, so a broken request wears the costume of the claim checker working.


def test_a_claude_5_call_asks_for_thinking_to_be_disabled(monkeypatch):
    seen: dict = {}

    def _spy(model, **kwargs):
        seen.update(kwargs)
        return type("R", (), {"text": "ok"})()

    monkeypatch.setattr("newsdesk.script._gmi_chat", _spy)
    chat("anthropic/claude-sonnet-5", prompt="hi", temperature=0.2, max_tokens=2000)
    assert seen["thinking"] == {"type": "disabled"}
    assert "temperature" not in seen        # both quirks, one call


def test_no_thinking_flag_is_sent_to_a_model_that_never_asked_for_one(monkeypatch):
    """A parameter another model does not understand is a 400 waiting to happen."""
    seen: dict = {}

    def _spy(model, **kwargs):
        seen.update(kwargs)
        return type("R", (), {"text": "ok"})()

    monkeypatch.setattr("newsdesk.script._gmi_chat", _spy)
    chat("anthropic/claude-haiku-4.5", prompt="hi", temperature=0.4, max_tokens=2000)
    assert "thinking" not in seen
    assert seen["temperature"] == 0.4


def test_the_anthropic_escape_hatch_sends_no_thinking_flag(monkeypatch):
    """Direct Messages API leaves thinking off unless asked. Do not ask."""
    seen: dict = {}

    def _spy(model, **kwargs):
        seen.update(kwargs, model=model)
        return type("R", (), {"text": "ok"})()

    monkeypatch.setattr("newsdesk.script._anthropic_chat", _spy)
    monkeypatch.setattr("newsdesk.script.PROVIDER", "anthropic")
    monkeypatch.setattr("newsdesk.script.ANTHROPIC_MODEL", "claude-sonnet-5-20260514")
    chat("anthropic/claude-sonnet-5", prompt="hi", temperature=0.2, max_tokens=2000)
    assert "thinking" not in seen
    assert "temperature" not in seen        # still dropped: it is a Claude 5


def test_the_two_quirks_travel_together(monkeypatch):
    """Every model that loses temperature gains the thinking flag, and vice versa.

    They were found in the same hour on the same family. Pinning them as one
    set is what stops a future model getting half the treatment.
    """
    for model in ["anthropic/claude-sonnet-5", "anthropic/claude-opus-5",
                  "anthropic/claude-fable-5"]:
        assert not accepts_temperature(model) and wants_thinking_disabled(model)
    for model in ["anthropic/claude-haiku-4.5", "anthropic/claude-sonnet-4.6",
                  "deepseek-ai/DeepSeek-V3-0324"]:
        assert accepts_temperature(model) and not wants_thinking_disabled(model)
