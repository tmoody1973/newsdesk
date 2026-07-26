"""The decision ledger — provenance for editorial judgments (MOO-433).

Genblaze records everything that runs through `Pipeline.step()`: model, prompt,
params, timestamps, hash, embedded in the finished MP4. But `chat()` is a plain
function, not a `BaseProvider`, so it cannot ride a Pipeline and nothing about
it reaches a manifest.

For most apps that is a footnote. For this one it is the product: all three of
our `chat()` calls are governance — script validation, the policy gate's
semantic half, and post-render vision evaluation. Left alone, the receipt would
document every image we made and stay silent on everything we refused.

So we keep the record ourselves, in the same places Genblaze keeps its own, and
fold its digest into the master manifest at assembly. That last step is what
separates provenance from logging: without it the ledger is a text file anyone
could quietly edit afterwards; with it, altering a single rejection breaks
`genblaze verify`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from newsdesk.state import RunState, now

Verdict = Literal["pass", "reject", "revise"]


@dataclass(frozen=True)
class Decision:
    """One editorial judgment made by a model, recorded like any other step."""

    ts: str
    role: str                 # script | policy | vision
    model: str
    provider: str
    verdict: Verdict
    reason: str               # human-readable, cites a rule where one applies
    block: int | None = None
    rule_id: str | None = None
    prompt: str = ""          # redacted in the public receipt via EmbedPolicy
    response: str = ""
    cost_usd: float | None = None

    def digest(self) -> str:
        """Stable hash of the decision, excluding nothing.

        Sorted keys so the digest does not depend on field order — the same
        canonicalization discipline genblaze applies to its own manifests.
        """
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode()
        ).hexdigest()

    def summary(self) -> str:
        """What the public receipt shows — verdict and rule, never the prompt."""
        rule = f"{self.rule_id} · " if self.rule_id else ""
        where = f"block {self.block}: " if self.block is not None else ""
        return f"{where}{rule}{self.verdict} — {self.reason}"


@dataclass(frozen=True)
class Ledger:
    """Every decision in a run, hashable as a unit."""

    decisions: tuple[Decision, ...] = ()

    def add(self, decision: Decision) -> Ledger:
        return Ledger(decisions=self.decisions + (decision,))

    def rejections(self) -> tuple[Decision, ...]:
        return tuple(d for d in self.decisions if d.verdict == "reject")

    def digest(self) -> str:
        """One hash covering the whole ledger — this is what enters the manifest.

        Built from the per-decision digests rather than the raw objects, so a
        reordering is detectable and a single altered decision changes the root.
        """
        joined = "\n".join(d.digest() for d in self.decisions)
        return hashlib.sha256(joined.encode()).hexdigest()

    def manifest_entry(self) -> dict[str, Any]:
        """The block folded into the master manifest at assembly."""
        return {
            "decision_ledger": {
                "count": len(self.decisions),
                "rejections": len(self.rejections()),
                "sha256": self.digest(),
                "summaries": [d.summary() for d in self.decisions],
            }
        }


def record_decision(
    state: RunState,
    ledger: Ledger,
    *,
    role: str,
    model: str,
    provider: str,
    verdict: Verdict,
    reason: str,
    block: int | None = None,
    rule_id: str | None = None,
    prompt: str = "",
    response: str = "",
    cost_usd: float | None = None,
) -> tuple[RunState, Ledger, Decision]:
    """Record one judgment into both the ledger and the run log.

    Returns new state — nothing mutates, so the run's history is append-only
    and a decision cannot be quietly revised after the fact.
    """
    decision = Decision(
        ts=now(), role=role, model=model, provider=provider, verdict=verdict,
        reason=reason, block=block, rule_id=rule_id, prompt=prompt,
        response=response, cost_usd=cost_usd,
    )
    state = state.log(
        f"decision.{role}",
        decision.summary(),
        block=block,
        rule_id=rule_id,
        provider=provider,
        model=model,
        cost_usd=cost_usd,
    )
    return state, ledger.add(decision), decision


def judged(
    state: RunState,
    ledger: Ledger,
    *,
    role: str,
    model: str,
    provider: str,
    call: Callable[[], tuple[Verdict, str, str]],
    block: int | None = None,
    rule_id: str | None = None,
    prompt: str = "",
    cost_usd: float | None = None,
) -> tuple[RunState, Ledger, Decision]:
    """Run a chat()-backed judgment and record it, whatever happens.

    `call` returns (verdict, reason, raw_response). If it raises, the failure is
    recorded as a **reject** rather than propagating unrecorded — a checker that
    cannot answer must not become an implicit pass. Fail closed, and say so in
    the ledger.
    """
    try:
        verdict, reason, response = call()
    except Exception as exc:  # noqa: BLE001 — deliberate fail-closed boundary
        verdict, reason, response = (
            "reject",
            f"checker unavailable ({type(exc).__name__}) — blocked rather than assumed safe",
            "",
        )
    return record_decision(
        state, ledger, role=role, model=model, provider=provider, verdict=verdict,
        reason=reason, block=block, rule_id=rule_id, prompt=prompt,
        response=response, cost_usd=cost_usd,
    )
