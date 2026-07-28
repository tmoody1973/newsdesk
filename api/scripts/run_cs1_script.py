#!/usr/bin/env python3
"""Generate the CS-1 script against the real GMI endpoint (MOO-419).

    uv run python scripts/run_cs1_script.py
    uv run python scripts/run_cs1_script.py --model Qwen/Qwen3.5-397B-A17B

Text only, so cents rather than dollars. Prints the six blocks, the claim->fact
map, per-block word/sentence counts against POL-5, and the ledger digest that
enters the master manifest.

The point is not that a model can write six lines. It is that a model which
writes a *wrong* line gets refused here, with the refusal recorded — so run it
more than once and watch what happens on the takes that miss.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from fixtures import cs1_story  # noqa: E402

from newsdesk.config import ConfigError, require  # noqa: E402
from newsdesk.decisions import Ledger  # noqa: E402
from newsdesk.policy.gate import check_narration, estimate_take_seconds  # noqa: E402
from newsdesk.script import MODEL, generate_script  # noqa: E402
from newsdesk.state import RunState  # noqa: E402


def main() -> int:
    model = MODEL
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]

    try:
        require("GMI_API_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    story = cs1_story()
    print(f"story  {story.title}")
    print(f"facts  {len(story.facts)} — {', '.join(f.id for f in story.facts)}")
    print(f"model  {model}\n")

    state, ledger, blocks = generate_script(
        RunState(run_id="cs1-live", story=story.title), Ledger(), story, model=model
    )

    decision = ledger.decisions[0]
    print(f"verdict  {decision.verdict.upper()}")
    print(f"reason   {decision.reason}\n")

    if not blocks:
        print("No script returned — the refusal is the output. Raw reply:\n")
        print(decision.response[:1500])
        print(f"\nledger digest  {ledger.digest()}")
        return 1

    for b in blocks:
        words = len(b.narration.split())
        finding = check_narration(b.narration)
        print(f"--- Block {b.n} · {b.role}")
        print(f"    {b.narration}")
        print(f"    {words} words · ~{estimate_take_seconds(b.narration):.1f}s · "
              f"POL-5 {'pass' if finding.passed else 'FAIL'}")
        for c in b.claims:
            print(f"    {c.fact_id} ← \"{c.spoken}\"  ⇢  {c.evidence!r}")
        print()

    used = {c.fact_id for b in blocks for c in b.claims}
    orphans = {f.id for f in story.facts} - used
    print(f"facts used     {', '.join(sorted(used))}")
    print(f"orphan facts   {', '.join(sorted(orphans)) if orphans else 'none'}")
    print(f"ledger digest  {ledger.digest()}")
    print(f"run events     {len(state.events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
