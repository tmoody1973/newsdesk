"""Kit resolution. B2 keys are flat, so kit/ and kit/diorama/ coexist and the
existing kit never moves — the cheapest correct answer, and no migration.
"""
from __future__ import annotations

import pytest

from newsdesk.blockprompt import negative_line, platform_floor
from newsdesk.brandkit import kit_prefix
from newsdesk.storyfile import StoryFileError, parse_story

_STORY = {
    "id": "kit-test",
    "title": "A story",
    "through_line": "fuse",
    "facts": [{"text": "A fact with a number, 5", "sources": [{"url": "https://x.org/a"}]}],
}


@pytest.mark.parametrize("kit_id,expected", [
    (None, "kit/"),
    ("house", "kit/"),
    ("diorama", "kit/diorama/"),
])
def test_the_house_kit_keeps_its_prefix_so_nothing_migrates(kit_id, expected):
    assert kit_prefix(kit_id) == expected


def test_a_story_defaults_to_the_house_kit():
    assert parse_story(dict(_STORY)).kit == "house"


def test_a_story_may_name_a_kit():
    assert parse_story({**_STORY, "kit": "diorama"}).kit == "diorama"


def test_an_unknown_kit_is_refused_at_wall_1():
    """422 at the door, no run created, nothing spent — a fact with no source's
    standard, applied to art direction."""
    with pytest.raises(StoryFileError, match="kit"):
        parse_story({**_STORY, "kit": "not-a-kit"})


FLOOR_TERMS = ("photorealism", "live-action footage", "3D render",
               "lip-sync", "talking characters", "watermark", "logo")
TEXT_TERMS = ("readable text", "letters", "words", "numbers", "captions", "subtitles")


@pytest.mark.parametrize("term", FLOOR_TERMS)
def test_the_floor_carries_every_harm_pol1_and_pol3_exist_for(term):
    assert term in platform_floor()


@pytest.mark.parametrize("term", TEXT_TERMS)
def test_the_text_default_is_not_in_the_floor(term):
    """The text half is narrowable. If it were in the floor, no kit could ever
    carry a letterpress label, which is the diorama style's whole signature."""
    assert term not in platform_floor()


def test_the_house_negative_still_forbids_text():
    """Narrowable is not narrowed. The house kit is unchanged in effect."""
    line = negative_line("house")
    for term in TEXT_TERMS:
        assert term in line


def test_every_kit_negative_starts_with_the_floor():
    """The whole POL-2 argument. Without it a kit is compared against itself."""
    for kit_id in ("house", "diorama"):
        assert negative_line(kit_id).startswith(platform_floor())


def test_a_prompt_built_in_a_kit_carries_that_kits_style_and_exclusions(tmp_path, monkeypatch):
    """Threading the kit id into `negative_line` alone leaves every diorama
    block rendering in the HOUSE look: `style-tokens.txt` is the kit's whole
    appearance and it was read from the root unconditionally, so the kit's own
    file was published, verified, and never sent to a provider."""
    from newsdesk.blockprompt import BlockPrompt

    (tmp_path / "floor.txt").write_text("photorealism", encoding="utf-8")
    (tmp_path / "negative.txt").write_text("house additions", encoding="utf-8")
    (tmp_path / "style-tokens.txt").write_text("the house look", encoding="utf-8")
    kit = tmp_path / "diorama"
    kit.mkdir()
    (kit / "negative.txt").write_text("kit additions", encoding="utf-8")
    (kit / "style-tokens.txt").write_text("the diorama look", encoding="utf-8")
    monkeypatch.setenv("NEWSDESK_BRAND_KIT_DIR", str(tmp_path))

    built = BlockPrompt.build(1, scene="s", motion="m", audio="a", kit="diorama")
    assert "the diorama look" in built.style_reference
    assert "the house look" not in built.style_reference
    assert built.negative == "photorealism, kit additions"

    house = BlockPrompt.build(1, scene="s", motion="m", audio="a")
    assert "the house look" in house.style_reference
    assert house.negative == "photorealism, house additions"


# --- the diorama kit ---------------------------------------------------------
#
# The kit is six files and they are the deliverable. These check the things a
# reader cannot check by eye: that every required file exists, that the pieces
# the pipeline parses actually parse into what it expects, and that the two
# hard-won pieces of knowledge — the moderation map and the 9:16 deviation —
# are in the kit rather than in someone's memory.

from pathlib import Path  # noqa: E402

from newsdesk.brandkit import REQUIRED_TEXT  # noqa: E402

KIT_ROOT = Path(__file__).resolve().parents[2] / "brand-kit"
DIORAMA = KIT_ROOT / "diorama"


def _kit_base(kit_id: str) -> Path:
    return KIT_ROOT if kit_id == "house" else KIT_ROOT / kit_id


@pytest.mark.parametrize("kit_id", ["house", "diorama"])
def test_every_kit_carries_all_six_required_files(kit_id):
    """Absent any one of these, it is not a kit."""
    for name in REQUIRED_TEXT:
        assert (_kit_base(kit_id) / name).is_file(), f"{kit_id} is missing {name}"


def test_the_diorama_kit_records_why_it_is_9_16():
    """The reference is 16:9. The deviation is deliberate and lives in guidance,
    not in style-tokens.txt, which is sent to the provider verbatim."""
    guidance = (DIORAMA / "scene-guidance.txt").read_text(encoding="utf-8")
    assert "9:16" in guidance and "16:9" in guidance


def test_the_diorama_kit_carries_the_moderation_map():
    """Named politicians die at render; mushroom cloud trips NSFW. That cost
    someone an afternoon and belongs in the kit, not in anyone's memory."""
    guidance = (DIORAMA / "scene-guidance.txt").read_text(encoding="utf-8").lower()
    assert "politician" in guidance
    assert "mushroom cloud" in guidance
    assert "censor bar" in guidance


@pytest.mark.parametrize("kit_id", ["house", "diorama"])
def test_no_kit_explains_itself_inside_the_two_provider_facing_files(kit_id):
    """style-tokens.txt and negative.txt go on the wire verbatim. A comment in
    either ships inside the prompt — which is how the 9:16 note would have
    reached a provider as an instruction about aspect ratio."""
    for name in ("style-tokens.txt", "negative.txt"):
        text = (_kit_base(kit_id) / name).read_text(encoding="utf-8")
        assert "#" not in text, f"{kit_id}/{name} carries a comment"
        assert text.strip() == text.strip().splitlines()[0].strip() or "\n" not in text.strip()


def test_the_diorama_style_tokens_are_the_sources_own_line():
    """Verbatim from diorama-doc.md's STYLE block. Paraphrasing it is how a
    house style drifts — and this is the file that IS the look."""
    tokens = (DIORAMA / "style-tokens.txt").read_text(encoding="utf-8").strip()
    for phrase in (
        "cinematic vintage paper diorama",
        "aged sepia newsprint world",
        "monochrome halftone print",
        "black censor bars over their eyes",
        "single burnt-orange accent",
        "distressed letterpress",
        "warm tungsten light",
        "macro tilt-shift shallow depth of field",
        "film grain",
        "handcrafted stop-motion paper feel",
        "non-photorealistic, no live-action",
    ):
        assert phrase in tokens, f"style tokens dropped {phrase!r}"


def test_the_diorama_negative_never_forbids_the_thing_the_kit_is_for():
    """A blanket ban on letters would make the letterpress label impossible —
    the whole reason Task 9 split the constant. It still refuses the failure
    modes of on-prop text: gibberish, duplication, doubled lines."""
    additions = (DIORAMA / "negative.txt").read_text(encoding="utf-8").strip()
    # Split on commas: the terms are the whole exclusion, so "letters" is a
    # blanket ban and "gibberish letters" is a quality bar on a permitted one.
    terms = {t.strip() for t in additions.split(",")}
    for banned in ("readable text", "letters", "words", "numbers", "subtitles",
                   "captions"):
        assert banned not in terms
    for kept in ("gibberish letters", "repeated text", "doubled text"):
        assert kept in additions


def test_the_diorama_through_line_menu_matches_the_house_schema():
    """Same fields, because `ThroughLine.from_kit` reads one shape. A menu that
    invents its own keys loads clean and renders the object wrong."""
    import yaml

    house = yaml.safe_load((KIT_ROOT / "through-lines.yaml").read_text(encoding="utf-8"))
    kit = yaml.safe_load((DIORAMA / "through-lines.yaml").read_text(encoding="utf-8"))

    house_keys = {k for e in house["through_lines"] for k in e}
    entries = kit["through_lines"]
    assert len(entries) >= 6, "six blocks need at least six options to choose between"
    for entry in entries:
        assert set(entry) <= house_keys, f"{entry['id']} invents keys the loader ignores"
        for required in ("id", "label", "use_when", "framing", "escalation",
                         "lettering_risk"):
            assert entry.get(required), f"{entry['id']} has no {required}"
        assert "burnt-orange" in entry["framing"], (
            f"{entry['id']} is not the burnt-orange object — the single accent in a "
            f"sepia world IS the through-line"
        )
    assert any(e.get("countable") for e in entries), (
        "a countable escalation is the one that renders monotonically; the menu "
        "needs at least one"
    )


def test_every_diorama_through_line_loads_into_the_scene_builder():
    """The menu is only art direction if `build_scene` can read it. Loaded the
    way `pipeline.through_line()` loads it, doc and all."""
    import yaml

    from newsdesk.scene import GROUND, ThroughLine, build_scene

    doc = yaml.safe_load((DIORAMA / "through-lines.yaml").read_text(encoding="utf-8"))
    for entry in doc["through_lines"]:
        tl = ThroughLine.from_kit(entry, doc=doc)
        scene = build_scene(tl, 1)
        assert GROUND not in scene, "the diorama ground is sepia newsprint, not cream"
        assert "sepia" in scene.lower()
        assert '"' not in scene and "'" not in scene, (
            f"{entry['id']} puts a quoted string in SCENE — POL-4 reads that as a "
            f"request for on-screen text and blocks the block"
        )


def test_the_diorama_voice_parses_into_what_narration_and_assembly_read():
    """voice.json is not documentation: `voice_specs`, `take_window` and
    `assembly_contract` all parse it, and each raises rather than defaulting."""
    import json

    from newsdesk.assembly import ROLES, assembly_contract
    from newsdesk.narration import take_window, voice_specs

    voice = json.loads((DIORAMA / "voice.json").read_text(encoding="utf-8"))
    primary, fallback = voice_specs(voice)
    assert primary.provider and primary.voice_id and fallback.voice_id

    low, high = take_window(voice)
    assert 5.0 < low < high < 20.0

    contract = assembly_contract(voice)
    assert set(ROLES) <= set(contract.tail_by_role), "a role with no tail gap"
    assert all(
        contract.tail_range[0] <= v <= contract.tail_range[1]
        for v in contract.tail_by_role.values()
    )


def test_the_diorama_subtitles_burn():
    """`ass_document` slices the kit file at [Script Info] and drops the probe
    line. A header it cannot find produces a file ffmpeg rejects with 'Unable to
    open', which names the filename and nothing about the content."""
    from newsdesk.assembly import Cue, ass_document

    raw = (DIORAMA / "subtitle.ass").read_text(encoding="utf-8")
    doc = ass_document(raw, (Cue(start_s=0.0, end_s=1.0, text="ONE"),))

    assert doc.startswith("[Script Info]")
    assert "PlayResX: 1080" in doc and "PlayResY: 1920" in doc
    assert "Style: Default," in doc
    assert "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,ONE" in doc
    assert "RESOLVED" not in doc, "the rendering probe must not survive into a cut"


def test_every_diorama_block_prompt_passes_the_gate():
    """Wall 2 against the kit as authored, at $0. Kit text is prompt text: a
    framing clause that says `the governor` trips POL-1, a quoted word trips
    POL-4, and either one blocks all six blocks of every story that picks it —
    at run time, in front of whoever asked for the video."""
    import yaml

    from newsdesk.policy.gate import check
    from newsdesk.scene import ThroughLine, build_block_prompt

    doc = yaml.safe_load((DIORAMA / "through-lines.yaml").read_text(encoding="utf-8"))
    for entry in doc["through_lines"]:
        tl = ThroughLine.from_kit(entry, doc=doc)
        for n in range(1, 7):
            verdict = check(build_block_prompt(tl, n, 6, kit="diorama"))
            assert verdict.passed, f"{entry['id']} block {n}: {verdict.explain()}"


# --- publishing a kit --------------------------------------------------------


class _FakeStore:
    """A B2 bucket that lives in a dict. The kit path is $0 and offline here."""

    def __init__(self, objects: dict[str, bytes] | None = None):
        self.objects = dict(objects or {})

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def exists(self, key: str) -> bool:
        return key in self.objects

    def get_durable_url(self, key: str) -> str:
        return f"https://example.invalid/{key}"


def _published(kit_id: str) -> dict[str, bytes]:
    """What a synced bucket holds for one kit, keyed the way B2 keys it."""
    from newsdesk.brandkit import FLOOR, kit_prefix

    objects = {f"kit/{FLOOR}": b"photorealism"}
    for name in REQUIRED_TEXT:
        objects[f"{kit_prefix(kit_id)}{name}"] = (
            b"version: 1\nthrough_lines: []\n" if name.endswith(".yaml")
            else b"{}" if name.endswith(".json") else b"x"
        )
    return objects


def test_sync_down_materializes_a_kit_the_gate_can_actually_read(tmp_path):
    """The floor is at the kit ROOT and is not one of the six required files, so
    it was never fetched. A deployed run points NEWSDESK_BRAND_KIT_DIR at this
    directory and `platform_floor()` reads floor.txt out of it — without it the
    gate dies on FileNotFoundError, having refused nothing."""
    from newsdesk import brandkit

    dest = brandkit.sync_down(tmp_path / "kit", store=_FakeStore(_published("house")))
    assert (dest / "floor.txt").is_file()
    for name in REQUIRED_TEXT:
        assert (dest / name).is_file()


def test_sync_down_lays_a_keyed_kit_out_the_way_kit_dir_for_looks_for_it(tmp_path):
    """`kit_dir_for('diorama')` is `<root>/diorama`, and the floor stays at the
    root because a kit that could write its own floor is compared against
    itself."""
    from newsdesk import brandkit
    from newsdesk.blockprompt import kit_dir_for

    dest = brandkit.sync_down(
        tmp_path / "kit", store=_FakeStore(_published("diorama")), kit_id="diorama"
    )
    assert (dest / "floor.txt").is_file(), "the floor is never inside a kit"
    for name in REQUIRED_TEXT:
        assert (dest / "diorama" / name).is_file()

    import os
    os.environ["NEWSDESK_BRAND_KIT_DIR"] = str(dest)
    try:
        assert kit_dir_for("diorama") == dest / "diorama"
    finally:
        del os.environ["NEWSDESK_BRAND_KIT_DIR"]


def test_loading_a_keyed_kit_reads_that_kits_prefix(tmp_path):
    from newsdesk import brandkit

    kit = brandkit.load(store=_FakeStore(_published("diorama")), kit_id="diorama")
    assert kit.through_lines == {"version": 1, "through_lines": []}

    # And the same bucket cannot satisfy a house load: the two prefixes are
    # different keys, which is what makes "nothing migrates" true.
    with pytest.raises(brandkit.BrandKitError):
        brandkit.load(store=_FakeStore(_published("diorama")))
