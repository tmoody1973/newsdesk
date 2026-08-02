"""The story file is Wall 1's front door (MOO-434).

Every other module trusts that a loaded `Story` is well-formed. These tests are
mostly about what the loader REFUSES, because a parser that quietly accepts a
malformed fact turns "no fact without a source" from a guarantee into a hope.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from newsdesk.facts import FactError
from newsdesk.storyfile import StoryFileError, load_story, parse_story

STORIES = Path(__file__).resolve().parents[2] / "stories"

GOOD = {
    "id": "cs9",
    "title": "A title",
    "through_line": "tower-signal",
    "facts": [
        {"text": "A sourced fact", "sources": ["https://example.org/a"]},
        {"text": "Another", "sources": [{"citation": "Some Report, 2026"}]},
    ],
}


def test_a_well_formed_story_becomes_a_Story():
    sf = parse_story(GOOD)
    assert sf.id == "cs9"
    assert sf.story.title == "A title"
    assert [f.id for f in sf.story.facts] == ["F1", "F2"]
    assert sf.story.facts[0].sources[0].value == "https://example.org/a"


def test_ids_are_assigned_in_file_order():
    """Claim mapping cites F-numbers, so file order is load-bearing, not cosmetic."""
    sf = parse_story(GOOD)
    assert sf.story.by_id("F2").text == "Another"


def test_the_prefix_carries_the_through_line():
    """Re-rolling with different art direction must not overwrite the old clips."""
    sf = parse_story(GOOD)
    assert sf.clip_prefix == "cs9-tower-signal/"
    assert sf.run_id == "cs9"


# --- what it refuses ---------------------------------------------------------


def _without(**changes):
    doc = {**GOOD, **changes}
    return {k: v for k, v in doc.items() if v is not None}


@pytest.mark.parametrize("field", ["id", "title", "through_line"])
def test_a_missing_required_field_names_itself(field):
    with pytest.raises(StoryFileError, match=field):
        parse_story(_without(**{field: None}))


def test_a_fact_with_no_sources_is_refused_by_name():
    """Wall 1. The message has to quote the fact — a journalist reads this, and
    "fact 2 is invalid" does not tell them which sentence to go source."""
    doc = _without(facts=[{"text": "Turnout hit a record high", "sources": []}])
    with pytest.raises(StoryFileError, match="Turnout hit a record high"):
        parse_story(doc)


def test_a_bare_string_fact_is_refused():
    """The most natural thing to type is a plain list of sentences. That is
    exactly a story with no sources, so it has to fail loudly."""
    with pytest.raises(StoryFileError, match="no sources"):
        parse_story(_without(facts=["turnout hit a record high"]))


def test_a_citation_shaped_string_is_not_silently_a_url():
    """"npr.org (Aug 1, 2025)" is a citation. Accepting any bare string as a URL
    puts it in the receipt as a dead hyperlink that reads like a live source —
    the receipt is the product, and a fake link in it is worse than a refusal."""
    doc = _without(facts=[{"text": "x", "sources": ["npr.org (Aug 1, 2025)"]}])
    with pytest.raises(StoryFileError, match="citation"):
        parse_story(doc)


def test_a_source_cannot_be_two_kinds_at_once():
    doc = _without(
        facts=[{"text": "x", "sources": [{"url": "https://a.b", "citation": "c"}]}]
    )
    with pytest.raises(StoryFileError, match="exactly one"):
        parse_story(doc)


def test_a_dataset_source_without_a_row_is_refused():
    """CS-3's whole point is that a claim traces to a ROW. A dataset name alone
    points at a file, not at the number that appears on screen."""
    doc = _without(facts=[{"text": "x", "sources": [{"dataset": "budget-commons"}]}])
    with pytest.raises(StoryFileError, match="row"):
        parse_story(doc)


def test_a_dataset_source_keeps_its_row_and_page():
    doc = _without(
        facts=[{
            "text": "Police take 43 cents",
            "sources": [{"dataset": "mke-budget-commons", "row": "R14", "page": 137}],
        }]
    )
    src = parse_story(doc).story.facts[0].sources[0]
    assert src.kind == "dataset_row"
    assert (src.dataset, src.row_id, src.page) == ("mke-budget-commons", "R14", 137)
    assert src.describe() == "mke-budget-commons row R14, p.137"


def test_an_id_that_would_break_a_storage_key_is_refused():
    """The id becomes a B2 prefix. A slash in it produces keys nothing can list."""
    with pytest.raises(StoryFileError, match="prefix"):
        parse_story(_without(id="cs1/tower"))


def test_a_story_with_no_facts_is_refused():
    with pytest.raises(StoryFileError, match="facts"):
        parse_story(_without(facts=[]))


def test_a_missing_file_names_the_path():
    with pytest.raises(StoryFileError, match="nope.yaml"):
        load_story("/tmp/definitely/nope.yaml")


# --- the shipped stories are fixtures AND the test suite ---------------------


def test_every_shipped_story_loads_and_validates():
    """CLAUDE.md: "these fixtures ARE the test suite". A story file that stopped
    parsing would otherwise only be discovered by spending money on a run."""
    files = sorted(STORIES.glob("*.yaml"))
    assert files, f"no story files found in {STORIES}"
    for path in files:
        sf = load_story(path)
        sf.story.validate()  # raises FactError, not StoryFileError, if Wall 1 fails
        assert sf.story.facts, f"{path.name} has no facts"


def test_shipped_story_ids_are_unique_and_match_their_filenames():
    """Two stories sharing an id share a B2 prefix and a RunState key, so the
    second run would overwrite the first one's state mid-flight."""
    seen: dict[str, Path] = {}
    for path in sorted(STORIES.glob("*.yaml")):
        sf = load_story(path)
        assert sf.id == path.stem, f"{path.name} declares id '{sf.id}'"
        assert sf.id not in seen, f"{path.name} reuses the id of {seen[sf.id].name}"
        seen[sf.id] = path


def test_every_shipped_through_line_exists_in_its_own_kits_menu():
    """A typo here is only discovered at generation time, after the gate has
    passed and the first image is about to be paid for.

    Resolved against the story's OWN kit. This used to read the house menu for
    every story, which was right while there was one kit and would have passed a
    diorama story naming a house object — the one mistake it exists to catch.
    """
    from newsdesk.blockprompt import HOUSE_KIT

    kit_root = STORIES.parent / "brand-kit"
    for path in sorted(STORIES.glob("*.yaml")):
        sf = load_story(path)
        base = kit_root if sf.kit == HOUSE_KIT else kit_root / sf.kit
        menu = yaml.safe_load((base / "through-lines.yaml").read_text(encoding="utf-8"))
        known = {e["id"] for e in menu["through_lines"]}
        assert sf.through_line in known, (
            f"{path.name} names through-line '{sf.through_line}', which the "
            f"'{sf.kit}' kit does not offer ({sorted(known)})"
        )
