"""Wall 1 — nothing enters the pipeline without a source.

A pure function with no provider access. That is what makes the guarantee
structural: there is no code path from an unsourced fact to a paid API call,
because this module cannot reach one.

Enforces that a source is *present*, not that it is *correct*. Verifying the
claim is the journalist's job; refusing to proceed without one is ours.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SourceKind = Literal["url", "citation", "dataset_row"]


class FactError(ValueError):
    """Raised when facts do not satisfy Wall 1."""


@dataclass(frozen=True)
class Source:
    """Where a fact came from.

    `dataset_row` exists for the deterministic path (CS-3): facts exported from
    a parsed budget carry dataset + row + page instead of a URL. Provenance in,
    provenance out.
    """

    kind: SourceKind
    value: str
    dataset: str | None = None
    row_id: str | None = None
    page: int | None = None

    @classmethod
    def url(cls, value: str) -> Source:
        return cls(kind="url", value=value.strip())

    @classmethod
    def citation(cls, value: str) -> Source:
        return cls(kind="citation", value=value.strip())

    @classmethod
    def dataset_row(cls, dataset: str, row_id: str, *, page: int | None = None) -> Source:
        return cls(
            kind="dataset_row",
            value=f"{dataset}#{row_id}",
            dataset=dataset,
            row_id=row_id,
            page=page,
        )

    def describe(self) -> str:
        """One line for the sources ledger and the receipt."""
        if self.kind == "dataset_row":
            page = f", p.{self.page}" if self.page is not None else ""
            return f"{self.dataset} row {self.row_id}{page}"
        return self.value


@dataclass(frozen=True)
class Fact:
    """One verified statement, with at least one source once validated."""

    id: str
    text: str
    sources: tuple[Source, ...] = ()

    @property
    def is_sourced(self) -> bool:
        return len(self.sources) > 0


@dataclass(frozen=True)
class Story:
    """A story's facts. IDs are assigned here so claim mapping can rely on them."""

    title: str
    facts: tuple[Fact, ...] = field(default_factory=tuple)

    @classmethod
    def build(cls, title: str, entries: list[tuple[str, list[Source]]]) -> Story:
        """Assign stable F1, F2… IDs in entry order."""
        return cls(
            title=title.strip(),
            facts=tuple(
                Fact(id=f"F{i}", text=text.strip(), sources=tuple(sources))
                for i, (text, sources) in enumerate(entries, start=1)
            ),
        )

    def unsourced(self) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if not f.is_sourced)

    def validate(self) -> None:
        """Raise unless every fact carries a source.

        The message names the offending facts rather than saying "invalid
        input" — a journalist has to be able to act on it without opening the
        code.
        """
        if not self.facts:
            raise FactError("A story needs at least one fact before it can be scripted.")

        bad = self.unsourced()
        if bad:
            listed = "; ".join(f"{f.id} — {f.text[:60]}" for f in bad)
            raise FactError(
                f"Every fact needs a source before it can appear on screen. "
                f"Unsourced: {listed}"
            )

    def by_id(self, fact_id: str) -> Fact:
        for f in self.facts:
            if f.id == fact_id:
                return f
        raise FactError(f"No such fact: {fact_id}")

    def ledger(self) -> str:
        """The sources ledger the wizard renders in mono."""
        rows = []
        for f in self.facts:
            if f.is_sourced:
                rows.append(f"{f.id} → {', '.join(s.describe() for s in f.sources)}")
            else:
                rows.append(f"{f.id} — UNSOURCED")
        return "\n".join(rows)
