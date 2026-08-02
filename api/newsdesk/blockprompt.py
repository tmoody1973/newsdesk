"""The five-field block prompt — the structure the policy gate parses.

No free-form text ever reaches a provider. Every block prompt is a labeled
document with exactly five fields, so the gate inspects a structure instead of
scanning prose. That is what makes the deterministic checks cheap, and what
makes "the NEGATIVE line is unmodified" a byte comparison rather than a
judgement call.

Schema imported verbatim from ~/.claude/skills/vox-motion-graphics.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

def _find_brand_kit(start: Path | None = None) -> Path:
    """Walk up until a `brand-kit/` directory turns up.

    This was `parents[2]`, which is right in the repo — `api/newsdesk/` is two
    levels under the root — and wrong in the container, where `newsdesk/` sits
    directly under `/app`, so it resolved to `/brand-kit` and the deployed gate
    died on `FileNotFoundError: '/brand-kit/style-tokens.txt'`.

    Same fault as `gate._find_policy_file`, one directory over, found the same
    way: by running a real story against the deployed worker. Both files live at
    the repo root because there is exactly one of each — POL-2 requires the
    NEGATIVE line to be byte-identical to `brand-kit/negative.txt`, which a
    second copy would quietly break.

    `NEWSDESK_BRAND_KIT_DIR` still wins over this; see `kit_dir`. The search is
    what the gate falls back to, and the gate has to work with no credentials
    at all, so it cannot wait on a B2 sync.
    """
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        candidate = parent / "brand-kit"
        if candidate.is_dir():
            return candidate
    return here.parents[2] / "brand-kit"


DEFAULT_BRAND_KIT = _find_brand_kit()
REPO_ROOT = DEFAULT_BRAND_KIT.parent

FIELDS = ("STYLE REFERENCE", "SCENE", "MOTION", "AUDIO", "NEGATIVE")

# Which kits exist, named here rather than in brandkit.py so that a module
# with no network access (this one) can be the shared source of truth.
# brandkit.py and storyfile.py import these FROM here — never the reverse,
# because brandkit.py reaches newsdesk.config.backend and gate.py imports
# this module; test_structure.py fails the build if that path ever connects.
HOUSE_KIT = "house"
KNOWN_KITS = (HOUSE_KIT, "diorama")

# Field labels are anchored at line start. A field's value runs until the next
# label or end of text, so multi-line SCENE descriptions survive a round trip.
_FIELD_RE = re.compile(
    r"^(?P<label>" + "|".join(re.escape(f) for f in FIELDS) + r"):[ \t]*"
    r"(?P<value>.*?)(?=^(?:" + "|".join(re.escape(f) for f in FIELDS) + r"):|\Z)",
    re.MULTILINE | re.DOTALL,
)
_HEADER_RE = re.compile(r"^Block\s+(\d+)\s*$", re.MULTILINE)


class BlockPromptError(ValueError):
    """Raised when a prompt does not conform to the five-field schema."""


def kit_dir() -> Path:
    """Where the brand kit lives on this filesystem.

    Overridable via NEWSDESK_BRAND_KIT_DIR so a deployed run reads the kit
    fetched from B2 (`newsdesk.brandkit.sync_down`) rather than whatever
    happens to be checked out beside the code.

    The indirection is what keeps the two requirements compatible. MOO-425
    wants the published kit at runtime; `tests/test_structure.py` walks this
    module's import graph — gate.py imports it — and fails the build if
    anything network-capable appears. So the fetch lives in `brandkit.py`,
    which this module must never import, and the two meet at a directory path.
    """
    override = os.getenv("NEWSDESK_BRAND_KIT_DIR")
    return Path(override) if override else DEFAULT_BRAND_KIT


def kit_dir_for(kit_id: str | None = None) -> Path:
    """The directory holding one kit's files. The house kit is the bare root."""
    base = kit_dir()
    return base if not kit_id or kit_id == HOUSE_KIT else base / kit_id


@lru_cache(maxsize=8)
def _read(name: str, directory: str) -> str:
    """Cached kit read, keyed on the directory as well as the file.

    Keying on the directory matters: an lru_cache over a no-argument reader
    would outlive a NEWSDESK_BRAND_KIT_DIR change and hand back the previous
    kit's bytes — which POL-2 would then byte-compare against, silently.
    """
    return (Path(directory) / name).read_text(encoding="utf-8").strip()


def platform_floor() -> str:
    """The harms POL-1 and POL-3 exist for. No kit may narrow this, ever.

    Read from the kit ROOT, never from a kit subdirectory — that is what makes
    it a floor. An outlet that could write its own floor is compared against
    itself and passes trivially.
    """
    return _read("floor.txt", str(kit_dir()))


def negative_line(kit_id: str = HOUSE_KIT) -> str:
    """floor + this kit's additions. Add-only above the floor."""
    additions = _read("negative.txt", str(kit_dir_for(kit_id)))
    return f"{platform_floor()}, {additions}" if additions else platform_floor()


def style_tokens() -> str:
    """The house style descriptor, verbatim from the craft layer."""
    return _read("style-tokens.txt", str(kit_dir()))


@dataclass(frozen=True)
class BlockPrompt:
    """One block's generation request. Immutable — `tighten()` returns a copy."""

    block: int
    style_reference: str
    scene: str
    motion: str
    audio: str
    negative: str

    @classmethod
    def build(
        cls,
        block: int,
        *,
        scene: str,
        motion: str,
        audio: str,
        style_reference: str | None = None,
        negative: str | None = None,
    ) -> BlockPrompt:
        """Construct with the brand kit supplying the two fixed fields.

        Callers describe the block; they do not get to author the style
        reference or the exclusion line.
        """
        return cls(
            block=block,
            # No attachment is named, because there is no longer one to name.
            # MOO-424 removed the style-key image input — it made consistency
            # worse — and a prompt that still says "match the attached key"
            # points a model at nothing and invites it to invent the referent.
            style_reference=style_reference
            or f"Render in this house style EXACTLY — {style_tokens()}",
            scene=scene.strip(),
            motion=motion.strip(),
            audio=audio.strip(),
            negative=negative or negative_line(),
        )

    def render(self) -> str:
        """The labeled document that goes on the wire."""
        return (
            f"Block {self.block}\n"
            f"STYLE REFERENCE: {self.style_reference}\n"
            f"SCENE: {self.scene}\n"
            f"MOTION: {self.motion}\n"
            f"AUDIO: {self.audio}\n"
            f"NEGATIVE: {self.negative}"
        )

    def render_for_image(self) -> str:
        """Image-step variant — MOTION and AUDIO describe time, which a still has none of.

        The NEGATIVE line is carried anyway so POL-2 holds across both steps and
        the manifest records the same exclusion for each. It is advisory here:
        Gemini image generation has no negative-prompt mechanism, so absence must
        also be stated positively inside SCENE (POL-4's prompting rule).
        """
        return (
            f"STYLE REFERENCE: {self.style_reference}\n"
            f"SCENE: {self.scene}\n"
            f"NEGATIVE: {self.negative}"
        )

    def tighten(self, *, scene: str | None = None, negative_suffix: str = "") -> BlockPrompt:
        """Return a stricter copy — the AgentLoop retry move (§6.4).

        Never mutates: the original stays queryable as the v1 in the lineage.
        """
        return replace(
            self,
            scene=(scene or self.scene).strip(),
            negative=f"{self.negative}, {negative_suffix}" if negative_suffix else self.negative,
        )

    @property
    def negative_is_intact(self) -> bool:
        """POL-2: the emitted NEGATIVE must carry the platform floor intact.

        Startswith rather than equality so an AgentLoop-tightened prompt still
        passes — tightening may only *add* exclusions, never remove them. The
        floor, not a kit's full negative_line(), is the source of truth: a kit
        is compared against the one thing it cannot narrow, not against itself.
        """
        floor = platform_floor()
        return self.negative == floor or self.negative.startswith(floor + ",")


def parse(text: str) -> BlockPrompt:
    """Parse a rendered block prompt back into its fields.

    Strict by design: a missing field, a duplicate, prose before the first
    label, or fields out of order is a rejection, not something to recover
    from. If the prompt that reached a provider cannot be reconstructed
    exactly, the manifest cannot honestly claim to record what was asked.

    One case this deliberately does *not* catch: text appended after the last
    field is absorbed into NEGATIVE, which then re-renders identically. No
    structural check can see that. It is caught one layer up — the appended
    text makes `negative_is_intact` False, so POL-2 rejects the block. The
    parser proves shape; the gate proves policy.
    """
    header = _HEADER_RE.search(text)
    block = int(header.group(1)) if header else 0

    found: dict[str, str] = {}
    for match in _FIELD_RE.finditer(text):
        label = match.group("label")
        if label in found:
            raise BlockPromptError(f"duplicate field: {label}")
        found[label] = match.group("value").strip()

    missing = [f for f in FIELDS if f not in found]
    if missing:
        raise BlockPromptError(f"missing field(s): {', '.join(missing)}")

    parsed = BlockPrompt(
        block=block,
        style_reference=found["STYLE REFERENCE"],
        scene=found["SCENE"],
        motion=found["MOTION"],
        audio=found["AUDIO"],
        negative=found["NEGATIVE"],
    )

    # Round-trip identity is the completeness check. A label-based scan happily
    # absorbs trailing prose into whichever field came last, so counting what
    # the regex consumed proves nothing. Re-rendering does: if the input does
    # not reproduce, something was in it that the schema has no field for.
    if _normalize(parsed.render()) != _normalize(text):
        raise BlockPromptError("text outside the labeled fields, or fields out of order")

    return parsed


def _normalize(text: str) -> str:
    """Collapse whitespace so formatting differences do not read as content."""
    return re.sub(r"\s+", " ", text).strip()
