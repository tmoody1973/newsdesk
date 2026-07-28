"""Run state — the application's only datastore (design spec §8).

One JSON document per run in b2://newsdesk-runs. The CLI writes it, the API
appends to it, the web app renders it. No database.

That is not only a simplification: it makes the state layer a fifth distinct
B2 use, and it means a crashed run is still fully inspectable rather than lost
in process memory.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal

from newsdesk.config import BUCKETS, backend

BlockStatus = Literal[
    "queued", "policy_check", "blocked", "styling", "generating",
    "vision_check", "retrying", "voicing", "ready", "failed",
]

RunStatus = Literal["drafting", "generating", "awaiting_approval", "published", "blocked"]


def now() -> str:
    """UTC ISO-8601. One helper so every timestamp in the manifest matches."""
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Event:
    """One line in the run log — and one row in the Parquet audit.

    Generation events and policy decisions share this shape deliberately, so a
    single query returns "block 3 generated on Seedance" and "block 3 rejected
    under POL-1" together rather than from two systems.
    """

    ts: str
    kind: str
    message: str
    block: int | None = None
    rule_id: str | None = None
    provider: str | None = None
    model: str | None = None
    cost_usd: float | None = None


@dataclass(frozen=True)
class Attempt:
    """One generation try. Retries append rather than overwrite, so v1 stays queryable."""

    n: int
    provider: str
    model: str
    status: str
    asset_uri: str | None = None
    sha256: str | None = None
    cost_usd: float | None = None
    parent_run_id: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Block:
    n: int
    status: BlockStatus = "queued"
    narration: str = ""
    fact_ids: tuple[str, ...] = ()
    prompt: str | None = None
    still_uri: str | None = None
    clip_uri: str | None = None
    voice_uri: str | None = None
    voice_duration_s: float | None = None
    attempts: tuple[Attempt, ...] = ()
    policy_results: tuple[dict[str, Any], ...] = ()
    # Every quantity this block asserts, with the fact it came from and the
    # verbatim span of that fact supporting it. Carried on the block rather than
    # derived at receipt time: a claim map rebuilt later is a reconstruction, and
    # the receipt's whole value is that it is not one.
    claims: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Approval:
    approver: str
    ts: str


@dataclass(frozen=True)
class RunState:
    run_id: str
    story: str
    status: RunStatus = "drafting"
    parent_run_id: str | None = None
    created_at: str = field(default_factory=now)
    facts: tuple[dict[str, Any], ...] = ()
    art_direction: dict[str, Any] = field(default_factory=dict)
    blocks: tuple[Block, ...] = ()
    events: tuple[Event, ...] = ()
    approval: Approval | None = None
    final: dict[str, Any] | None = None

    # --- transitions (all return new state; nothing mutates) -----------------

    def log(self, kind: str, message: str, **fields: Any) -> RunState:
        return replace(self, events=self.events + (Event(ts=now(), kind=kind, message=message, **fields),))

    def with_block(self, n: int, **changes: Any) -> RunState:
        blocks = tuple(replace(b, **changes) if b.n == n else b for b in self.blocks)
        return replace(self, blocks=blocks)

    def approve(self, approver: str) -> RunState:
        """Wall 3. Assembly reads this; there is no other way to satisfy it."""
        return replace(
            self, approval=Approval(approver=approver, ts=now()), status="awaiting_approval"
        ).log("approve", f"Approved by {approver}")

    @property
    def is_approved(self) -> bool:
        return self.approval is not None

    @property
    def total_cost(self) -> float:
        """Spend so far. GMI does not report cost, so this comes from our own
        registered rates (see newsdesk/pricing.py)."""
        return round(sum(e.cost_usd or 0.0 for e in self.events), 4)

    # --- persistence ---------------------------------------------------------

    def key(self) -> str:
        return f"{self.run_id}/state.json"

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> RunState:
        d = json.loads(raw)
        return cls(
            **{
                **d,
                "facts": tuple(d.get("facts", ())),
                "blocks": tuple(
                    Block(**{**b, "attempts": tuple(Attempt(**a) for a in b.get("attempts", ())),
                             "fact_ids": tuple(b.get("fact_ids", ())),
                             "policy_results": tuple(b.get("policy_results", ())),
                             "claims": tuple(b.get("claims", ()))})
                    for b in d.get("blocks", ())
                ),
                "events": tuple(Event(**e) for e in d.get("events", ())),
                "approval": Approval(**d["approval"]) if d.get("approval") else None,
            }
        )

    def save(self) -> str:
        """Persist to B2 and return the key. Called at every transition, so a
        killed process leaves the last completed step inspectable."""
        backend(BUCKETS["runs"]).put(
            self.key(), self.to_json().encode(), content_type="application/json"
        )
        return self.key()

    @classmethod
    def load(cls, run_id: str) -> RunState:
        raw = backend(BUCKETS["runs"]).get(f"{run_id}/state.json")
        return cls.from_json(raw.decode())
