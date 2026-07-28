"""The master manifest — the claim the video makes about itself (MOO-428, P0-7).

Assembly makes the picture; this makes the record. They are separate modules
because they answer to different standards: a cut can be re-done, but a receipt
that overstates by one field is worse than no receipt at all.

**Nothing here is composed by hand that genblaze already recorded.** Each block's
per-run `manifest.json` in B2 carries the real `Step` — provider, model, params,
timestamps, and the asset's sha256 — from the run that actually produced it. The
master run concatenates those, so the lineage in the receipt is the lineage the
SDK wrote at generation time rather than a summary of it re-typed later. What is
added on top is only what genblaze could not know: who approved it, and the
timing decisions assembly made.

The final MP4 is the *carrier*, not a listed asset. Embedding rewrites the
file's bytes, so an MP4 cannot contain its own hash — the assets under
verification are the six clips and six takes it was cut from, each of which is
public and fetchable, which is why `genblaze verify --fetch` can check them
without trusting us.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from genblaze_core.media import Mp4Handler
from genblaze_core.models.manifest import Manifest
from genblaze_core.models.run import Run
from genblaze_core.models.step import Step

from newsdesk.assembly import BlockTiming
from newsdesk.state import RunState


class ReceiptError(RuntimeError):
    """Raised when a manifest cannot be built, or must not be trusted."""


@dataclass(frozen=True)
class BlockRecord:
    """One block's inputs to the receipt, gathered from three places."""

    timing: BlockTiming
    narration: str
    generation_steps: tuple[dict[str, Any], ...]
    take_uri: str | None
    take_sha256: str | None
    voice_provider: str | None
    voice_model: str | None
    claims: tuple[dict[str, Any], ...] = ()


def _step_from_raw(raw: dict[str, Any]) -> Step:
    """Rehydrate a Step genblaze already wrote, rather than describing it again."""
    try:
        return Step.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 — a malformed record is not a summary
        raise ReceiptError(
            f"a per-block manifest step would not parse ({type(exc).__name__}). "
            f"Refusing to substitute a hand-written one — a receipt that "
            f"paraphrases its own evidence is not evidence."
        ) from exc


def narration_step(record: BlockRecord) -> Step:
    """The take, as a step. Narration does not ride a Pipeline, so it is composed.

    Composed rather than rehydrated because `narration.run_take` walks its own
    chain outside a `Pipeline` — the same reason `decisions.py` exists for
    `chat()`. The fields are filled from what was actually measured, and the
    timing lands in `metadata` because it is assembly's decision, not the
    provider's.
    """
    from genblaze_core.models.asset import Asset
    from genblaze_core.models.enums import Modality, StepStatus

    assets = []
    if record.take_uri:
        assets.append(Asset(
            url=record.take_uri,
            sha256=record.take_sha256,
            media_type="audio/mpeg",
        ))
    return Step(
        provider=record.voice_provider,
        model=record.voice_model or "unknown",
        modality=Modality.AUDIO,
        prompt=record.narration,
        status=StepStatus.SUCCEEDED,
        assets=assets,
        metadata={
            "block": record.timing.n,
            "role": record.timing.role,
            # Where this line's assertions came from. Per block rather than per
            # run, because "the video cites these six facts" is a much weaker
            # claim than "this sentence cites this fact and quotes it here".
            "claims": list(record.claims),
            "fact_ids": sorted({str(c.get("fact_id")) for c in record.claims}),
            # The measured numbers, per block. §6.6: a receipt that says "10.0s"
            # six times when none of them were is a small lie in a document whose
            # entire value is that it contains none.
            "take_s": record.timing.take_s,
            "lead_in_s": record.timing.lead_in_s,
            "tail_s": record.timing.tail_s,
            "block_length_s": record.timing.length_s,
            "starts_at_s": record.timing.start_s,
            "narration_starts_at_s": record.timing.narration_start_s,
        },
    )


def build_run(
    state: RunState,
    records: Sequence[BlockRecord],
    *,
    run_name: str,
    runtime_s: float,
) -> Run:
    """The master run: every block's real lineage, plus who approved it."""
    from genblaze_core.models.enums import RunStatus

    if state.approval is None:
        raise ReceiptError(
            "refusing to build a manifest for an unapproved run — the approver is "
            "not an optional field of this document, it is the point of it"
        )

    steps: list[Step] = []
    for record in records:
        steps.extend(_step_from_raw(raw) for raw in record.generation_steps)
        steps.append(narration_step(record))

    return Run(
        name=run_name,
        status=RunStatus.COMPLETED,  # a Run COMPLETES; only a Step SUCCEEDS
        steps=steps,
        metadata={
            "story": state.story,
            "approved_by": state.approval.approver,
            "approved_at": state.approval.ts,
            "runtime_s": runtime_s,
            "blocks": len(records),
            "facts": list(state.facts),
            "narration": {r.timing.n: r.narration for r in records},
            "assembly": {
                "model": "audio leads, picture follows (design spec §6.6)",
                "never": [
                    "speed-compress the voice",
                    "stretch or squeeze video to fit audio",
                    "centre a take inside a fixed block",
                    "space the gaps evenly",
                ],
                "gaps_s": [
                    round(records[i].timing.tail_s + records[i + 1].timing.lead_in_s, 3)
                    for i in range(len(records) - 1)
                ],
            },
        },
    )


def embed(mp4: Path, manifest: Manifest, out: Path) -> Path:
    """Write the manifest into the MP4's UUID box."""
    return Mp4Handler().embed(mp4, manifest, out)


def extract(mp4: Path) -> Manifest:
    """Read it back out. Used to prove the round trip, not just the write."""
    return Mp4Handler().extract(mp4)


def publishable(manifest: Manifest) -> None:
    """Refuse to publish a file whose manifest does not check out.

    The failure message is deliberately blunt and deliberately not actionable —
    there is no "publish anyway". A file that does not match its manifest is the
    one thing this product exists to make impossible.
    """
    report = manifest.verification_report()
    if not report.ok:
        raise ReceiptError(
            "This file doesn't match its manifest. Don't publish it.\n"
            f"  hash_ok: {report.hash_ok}\n"
            f"  assets missing sha256: {manifest.output_asset_ids_missing_sha256()}\n"
            f"  invalid metadata: {report.invalid_metadata_ids}"
        )
