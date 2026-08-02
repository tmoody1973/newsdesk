"""Suggesting a through-line, without letting anyone author one.

through-lines.yaml is explicit about what it is: "The menu IS the policy
boundary. A journalist picks a label and a meaning — they never write framing
language, and they never learn why a tower renders as a paper cutout rather
than a photograph." That knowledge lives here.

So this returns an ID or nothing. Free text never reaches a prompt. The menu's
`use_when` fields were written as human guidance and turn out to be exactly the
input this needs — whoever wrote them wrote this feature's prompt.

Routed through judged() so the receipt can record WHY a through-line was chosen.
An art-direction decision that appears in the provenance record beats an
unexplained menu click.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from newsdesk.decisions import Ledger, judged
from newsdesk.facts import Story
from newsdesk.script import MODEL, PROVIDER, TIMEOUT_S, chat
from newsdesk.state import RunState

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def build_prompt(story: Story, menu: dict[str, Any]) -> str:
    options = "\n".join(
        f"- {tid}: {(entry or {}).get('use_when', '')}" for tid, entry in menu.items()
    )
    facts = "\n".join(f"{f.id}: {f.text}" for f in story.facts)
    return f"""Choose the through-line object for this story.

STORY: {story.title}

FACTS:
{facts}

MENU — you must choose one of these ids exactly. Do not invent one:
{options}

Return JSON only: {{"through_line": "<id from the menu>", "why": "one short sentence"}}"""


def suggest_through_line(
    state: RunState,
    ledger: Ledger,
    story: Story,
    menu: dict[str, Any],
    *,
    chat_fn: Callable[..., Any] | None = None,
    model: str | None = None,
) -> tuple[RunState, Ledger, tuple[str, str] | None]:
    """(id, why) from the menu, or None. Never an id the menu does not carry."""
    chat_fn = chat_fn or chat
    model = model or MODEL
    chosen: tuple[str, str] | None = None

    def _call() -> tuple[str, str, str]:
        nonlocal chosen
        response = chat_fn(model, prompt=build_prompt(story, menu),
                          temperature=0.2, max_tokens=200, timeout=TIMEOUT_S)
        raw = getattr(response, "text", "") or ""
        fenced = _FENCE_RE.search(raw)
        doc = json.loads(fenced.group(1) if fenced else raw)
        # `or ""` rather than a dict default: a model sending "through_line": ""
        # would otherwise sail past .get()'s default. HANDOFF dead assumption 5.
        tid = (doc.get("through_line") or "").strip()
        why = (doc.get("why") or "").strip()
        if not tid:
            return "reject", "the model suggested no through-line", raw
        if tid not in menu:
            return "reject", (
                f"{tid!r} is not in the menu. The menu is the policy boundary; "
                "a suggestion outside it is refused rather than coerced."
            ), raw
        chosen = (tid, why)
        return "pass", f"{tid}: {why}", raw

    state, ledger, _decision = judged(
        state, ledger, role="art-direction", model=model, provider=PROVIDER, call=_call
    )
    return state, ledger, chosen
