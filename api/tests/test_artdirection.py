"""The through-line suggestion. It picks from the menu; it never writes one.

through-lines.yaml states the property this protects: "The menu IS the policy
boundary. A journalist picks a label and a meaning — they never write framing
language." A model returning free text would step straight over that line, so
the only thing it is allowed to return is an id that already exists.
"""
from __future__ import annotations

import json

from fixtures import cs1_story

from newsdesk.artdirection import suggest_through_line
from newsdesk.decisions import Ledger
from newsdesk.state import RunState

MENU = {
    "tower-signal": {"use_when": "Reach, coverage, or a service going dark."},
    "fuse": {"use_when": "A deadline, a countdown, an inevitability."},
}


def _run() -> RunState:
    return RunState(run_id="ad-test", story="Who pays when public radio goes dark?")


def _chat(payload: str):
    def _c(model, **kwargs):
        return type("R", (), {"text": payload})()
    return _c


def test_a_valid_id_is_returned_with_its_reason():
    _, _, got = suggest_through_line(
        _run(), Ledger(), cs1_story(), MENU,
        chat_fn=_chat(json.dumps({"through_line": "fuse", "why": "a deadline story"})),
    )
    assert got == ("fuse", "a deadline story")


def test_an_id_outside_the_menu_is_refused_not_coerced():
    _, ledger, got = suggest_through_line(
        _run(), Ledger(), cs1_story(), MENU,
        chat_fn=_chat(json.dumps({"through_line": "a burning pipe", "why": "x"})),
    )
    assert got is None
    assert ledger.decisions[-1].verdict == "reject"


def test_an_empty_id_falls_through_to_no_suggestion():
    """A dict default does not fire on an empty value — HANDOFF dead assumption 5.
    An empty string must become None, never menu item zero."""
    _, _, got = suggest_through_line(
        _run(), Ledger(), cs1_story(), MENU,
        chat_fn=_chat(json.dumps({"through_line": "", "why": ""})),
    )
    assert got is None


def test_an_unreachable_model_suggests_nothing_rather_than_guessing():
    def _boom(model, **kwargs):
        raise RuntimeError("provider down")

    _, ledger, got = suggest_through_line(
        _run(), Ledger(), cs1_story(), MENU, chat_fn=_boom
    )
    assert got is None
    assert ledger.decisions[-1].verdict == "reject"


def test_the_prompt_offers_every_menu_id_and_its_use_when():
    seen = {}

    def _spy(model, **kwargs):
        seen.update(kwargs)
        return type("R", (), {"text": json.dumps({"through_line": "fuse", "why": "d"})})()

    suggest_through_line(_run(), Ledger(), cs1_story(), MENU, chat_fn=_spy)
    for tid, entry in MENU.items():
        assert tid in seen["prompt"]
        assert entry["use_when"] in seen["prompt"]
