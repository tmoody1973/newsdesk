"""A story as a file, not a Python fixture.

Until now the only way to describe a story to this system was to edit
`tests/fixtures` and hand-edit `RUN_ID` and `CLIP_PREFIX` constants in four
scripts. That is why there has only ever been one video: CS-1 was not the first
story, it was the only one the code could express.

This module is the boundary between "a journalist described a story" and
`Story.build()`. It is deliberately the strictest module in the package —
everything downstream trusts that a loaded story is well-formed, and Wall 1
("no fact without a source") is only as strong as the parser underneath it.

Pure: yaml and the dataclasses, no network, no providers. `gate.py`'s import
graph is checked by tests/test_structure.py and this module must stay safe to
sit anywhere in it.

The file format, by example:

    id: cs1
    title: Who pays when public radio goes dark?
    through_line: tower-signal
    facts:
      - text: July 2025 rescissions eliminated $1.1B in CPB funding
        sources:
          - url: https://www.npr.org/2025/08/01/cpb-rescission
          - citation: time.com, Aug 1 2025
      - text: Police take 43 cents of every property-tax dollar
        sources:
          - dataset: mke-budget-commons
            row: R14
            page: 137

`id` and `through_line` are here rather than passed on the command line because
they decide where a run's assets land in B2, and a story whose art direction
lives in a shell history is a story nobody can re-run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from newsdesk.facts import Source, Story

# A run's B2 prefix is built from these, so they end up in object keys.
# Restricted rather than escaped: a story id is chosen by a person once, and
# "rejected because ids are lowercase and hyphenated" is a better failure than a
# key with a slash in it that nothing can list.
_ID_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-")

# Exactly one of these per source entry. Named so a YAML author never writes the
# word "kind" — the key they choose IS the kind.
_URL, _CITATION, _DATASET = "url", "citation", "dataset"


class StoryFileError(ValueError):
    """Raised when a story file cannot be read as a story.

    Messages name the file, the fact index and what to do about it. A
    journalist hits this, not a developer, and "invalid input" is not a thing
    anyone can act on.
    """


@dataclass(frozen=True)
class StoryFile:
    """A loaded story plus the art direction that decides how it is rendered.

    `story` is the same `Story` the rest of the pipeline already takes, so
    nothing downstream needs to know a file was involved.
    """

    id: str
    story: Story
    through_line: str

    @property
    def run_id(self) -> str:
        """The key `RunState` is stored under."""
        return self.id

    @property
    def clip_prefix(self) -> str:
        """Where this story's blocks land in the assets bucket.

        Includes the through-line because re-rolling a story with different art
        direction should not overwrite the previous roll's clips — the old
        `cs1-tower-signal/` prefix already had this shape and it was right.
        """
        return f"{self.id}-{self.through_line}/"


def _require(node: Any, field: str, where: str) -> Any:
    if not isinstance(node, dict):
        raise StoryFileError(f"{where}: expected a block of keys, got {type(node).__name__}")
    value = node.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise StoryFileError(f"{where}: missing required field '{field}'")
    return value


def _source(entry: Any, where: str) -> Source:
    """One source entry. The key chosen IS the kind; exactly one is allowed.

    A bare string is accepted as a URL only when it looks like one. Accepting
    any bare string as a URL is how "npr.org (Aug 1, 2025)" — which is a
    citation, not a link — would end up in the receipt as a dead hyperlink that
    reads like a verified source.
    """
    if isinstance(entry, str):
        text = entry.strip()
        if text.startswith(("http://", "https://")):
            return Source.url(text)
        raise StoryFileError(
            f"{where}: bare source '{text[:40]}' is not a URL. Write it as "
            f"`citation: {text[:40]}` if it is a reference rather than a link."
        )

    if not isinstance(entry, dict):
        raise StoryFileError(f"{where}: a source must be a URL or a block of keys")

    present = [k for k in (_URL, _CITATION, _DATASET) if entry.get(k)]
    if len(present) != 1:
        raise StoryFileError(
            f"{where}: a source needs exactly one of url / citation / dataset, "
            f"found {present or 'none'}"
        )

    kind = present[0]
    if kind == _URL:
        value = str(entry[_URL]).strip()
        if not value.startswith(("http://", "https://")):
            raise StoryFileError(f"{where}: url '{value[:40]}' is not http(s)")
        return Source.url(value)

    if kind == _CITATION:
        return Source.citation(str(entry[_CITATION]))

    row = entry.get("row") or entry.get("row_id")
    if not row:
        raise StoryFileError(
            f"{where}: a dataset source needs a `row` — a dataset name alone "
            f"points at a file, not at the number in the script."
        )
    page = entry.get("page")
    return Source.dataset_row(
        str(entry[_DATASET]).strip(),
        str(row).strip(),
        page=int(page) if page is not None else None,
    )


def parse_story(doc: Any, *, where: str = "story") -> StoryFile:
    """Parse an already-loaded YAML/JSON document. Separated from file reading
    so the web app can hand this the body of a POST without touching disk."""
    if not isinstance(doc, dict):
        raise StoryFileError(f"{where}: expected a mapping at the top level")

    story_id = str(_require(doc, "id", where)).strip()
    bad = sorted(set(story_id) - _ID_CHARS)
    if bad or not story_id:
        raise StoryFileError(
            f"{where}: id '{story_id}' may only use lowercase letters, digits "
            f"and hyphens (offending: {''.join(bad)}). It becomes a storage prefix."
        )

    title = str(_require(doc, "title", where)).strip()
    through_line = str(_require(doc, "through_line", where)).strip()

    raw_facts = doc.get("facts")
    if not isinstance(raw_facts, list) or not raw_facts:
        raise StoryFileError(f"{where}: needs a `facts:` list with at least one fact")

    entries: list[tuple[str, list[Source]]] = []
    for i, fact in enumerate(raw_facts, start=1):
        at = f"{where} fact {i}"
        if isinstance(fact, str):
            raise StoryFileError(
                f"{at}: '{fact[:40]}' has no sources. Every fact needs at least "
                f"one — that is the rule this tool exists to enforce."
            )
        text = str(_require(fact, "text", at)).strip()
        raw_sources = fact.get("sources") or []
        if not isinstance(raw_sources, list) or not raw_sources:
            raise StoryFileError(
                f"{at}: '{text[:40]}' has no sources. Every fact needs at least one."
            )
        entries.append((text, [_source(s, f"{at} source {j}")
                               for j, s in enumerate(raw_sources, start=1)]))

    story = Story.build(title, entries)
    # Belt and braces: the parser above should make this unreachable, but Wall 1
    # is the product and it gets checked by the module that owns it, not only by
    # the one that reads files.
    story.validate()
    return StoryFile(id=story_id, story=story, through_line=through_line)


def load_story(path: str | Path) -> StoryFile:
    """Read one story file. Raises StoryFileError with the path in the message."""
    p = Path(path)
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StoryFileError(f"no story file at {p}") from exc
    except yaml.YAMLError as exc:
        raise StoryFileError(f"{p} is not valid YAML: {exc}") from exc
    return parse_story(doc, where=str(p))
