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

# api/newsdesk/blockprompt.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BRAND_KIT = REPO_ROOT / "brand-kit"

FIELDS = ("STYLE REFERENCE", "SCENE", "MOTION", "AUDIO", "NEGATIVE")

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


@lru_cache(maxsize=8)
def _read(name: str, directory: str) -> str:
    """Cached kit read, keyed on the directory as well as the file.

    Keying on the directory matters: an lru_cache over a no-argument reader
    would outlive a NEWSDESK_BRAND_KIT_DIR change and hand back the previous
    kit's bytes — which POL-2 would then byte-compare against, silently.
    """
    return (Path(directory) / name).read_text(encoding="utf-8").strip()


def negative_line() -> str:
    """The fixed exclusion line. A policy constant, not a suggestion (POL-2)."""
    return _read("negative.txt", str(kit_dir()))


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
            style_reference=style_reference
            or f"Match the attached style key EXACTLY — {style_tokens()}",
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
        """POL-2: byte-identical to the brand kit constant.

        Startswith rather than equality so an AgentLoop-tightened prompt still
        passes — tightening may only *add* exclusions, never remove them.
        """
        return self.negative == negative_line() or self.negative.startswith(
            negative_line() + ","
        )


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
