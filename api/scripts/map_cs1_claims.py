#!/usr/bin/env python3
"""Trace an already-voiced run's narration back to its facts (MOO-428).

    uv run python scripts/map_cs1_claims.py

Cents — one text call.

`generate_script` emits claims alongside the lines, and every new run carries
them from the start. This exists for the run that was voiced before the claim
map was persisted to state: regenerating the script would produce *different
lines*, which would invalidate six rendered takes and the human approval
attached to the cut made from them.

The mapping is untrusted in the same way the generator is. `validate_script`
still requires every claim to name a real fact and quote it verbatim, so a map
produced after the fact cannot launder anything.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from dataclasses import asdict  # noqa: E402

from fixtures import cs1_story  # noqa: E402

from newsdesk.claims import ScriptBlock  # noqa: E402
from newsdesk.config import ConfigError, require  # noqa: E402
from newsdesk.decisions import Ledger  # noqa: E402
from newsdesk.script import ROLES, map_claims  # noqa: E402
from newsdesk.state import RunState  # noqa: E402

RUN_ID = "cs1-narration"


def main() -> int:
    try:
        require("GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    state = RunState.load(RUN_ID)
    story = cs1_story()
    blocks = tuple(
        ScriptBlock(n=b.n, narration=b.narration, role=ROLES[b.n - 1])
        for b in sorted(state.blocks, key=lambda b: b.n)
    )
    print(f"story   {story.title}")
    print(f"facts   {', '.join(f.id for f in story.facts)}")
    print(f"blocks  {len(blocks)} already voiced — narration is fixed input\n")

    state, ledger, mapped = map_claims(state, Ledger(), story, blocks)
    decision = ledger.decisions[-1]
    print(f"verdict  {decision.verdict.upper()}")
    print(f"reason   {decision.reason}\n")

    if not mapped:
        print("No claim map. The refusal is the output — nothing was written to state.")
        return 1

    # The facts themselves go in too. Without them the receipt names a story and
    # carries no evidence, which is a document that asks to be trusted rather
    # than one that can be checked.
    state = replace(state, facts=tuple(asdict(f) for f in story.facts))
    for block in mapped:
        state = state.with_block(
            block.n,
            claims=tuple(asdict(c) for c in block.claims),
            fact_ids=block.fact_ids,
        )

    for block in mapped:
        print(f"--- Block {block.n} · {block.role}")
        for claim in block.claims:
            print(f"    {claim.fact_id} ← \"{claim.spoken}\"  ⇢  {claim.evidence!r}")

    used = {c.fact_id for b in mapped for c in b.claims}
    orphans = {f.id for f in story.facts} - used
    print(f"\nfacts used    {', '.join(sorted(used))}")
    print(f"orphan facts  {', '.join(sorted(orphans)) if orphans else 'none'}")
    print(f"ledger        {ledger.digest()}")
    print(f"state         b2://newsdesk-runs/{state.save()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
