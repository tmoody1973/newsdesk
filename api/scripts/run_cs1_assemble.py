#!/usr/bin/env python3
"""Assemble CS-1 into one MP4 (MOO-428, P0-6 + P0-7).

    uv run python scripts/run_cs1_assemble.py --approve "Tarik Moody"
    uv run python scripts/run_cs1_assemble.py            # must refuse — no approval

$0. Every asset it needs already exists in B2 and every duration was already
measured; this only cuts.

Wall 3 is the first thing that happens, not the last. Without an approval record
the run stops before a single file is downloaded — which is the point: "publish
is unreachable without a named human" has to be a property of the code path, not
a button that is merely hard to find.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from newsdesk.assembly import (
    ROLES,
    AssemblyError,
    anton_is_resolvable,
    ass_document,
    assembly_contract,
    approved_or_raise,
    clip_action,
    plan_timeline,
    probe_duration,
    render,
    subtitle_cues,
)
from genblaze_core.models.manifest import Manifest  # noqa: E402

from newsdesk.brandkit import load
from newsdesk.config import BUCKETS, ConfigError, backend, require
from newsdesk.music import MODEL as MUSIC_MODEL
from newsdesk.music import (BED_TARGET_LUFS, compose, gain_for, measure_lufs,
                            movement_spans)
from newsdesk.narration import sha256_of
from newsdesk.receipt import (BlockRecord, ReceiptError, build_run, embed, extract,
                              music_step, publishable)
from newsdesk.state import RunState

RUN_ID = "cs1-narration"
CLIP_PREFIX = "cs1-tower-signal/"
WORK = Path("out/assemble")


def arg(flag: str, default: str | None = None) -> str | None:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def _keys(store, prefix: str) -> list[str]:
    keys, token = [], None
    while True:
        page = store.list(prefix, next_token=token) if token else store.list(prefix)
        keys += [getattr(e, "key", str(e)) for e in page.entries]
        token = page.next_token
        if not token:
            return keys


def clip_keys(store) -> dict[int, str]:
    """Map block number to clip key, read from each run's own manifest.

    The HIERARCHICAL sink names folders by run UUID, so the block number is not
    in the path — it is in `run.name` ("block-3"). Guessing the mapping from sort
    order would pair the wrong picture with the wrong line, and that failure
    looks like a style problem rather than a bug.
    """
    found: dict[int, str] = {}
    for key in _keys(store, CLIP_PREFIX):
        if not key.endswith("manifest.json"):
            continue
        run = json.loads(store.get(key)).get("run", {})
        name = str(run.get("name", ""))
        if not name.startswith("block-"):
            continue
        videos = [
            a["url"]
            for step in run.get("steps", [])
            for a in step.get("assets", [])
            if str(a.get("media_type", "")).startswith("video")
        ]
        if videos:
            found[int(name.removeprefix("block-"))] = (
                key.rsplit("/", 1)[0] + "/assets/" + videos[0].rsplit("/", 1)[-1]
            )
    return found


def block_steps(store) -> dict[int, tuple[dict, ...]]:
    """Each block's real Step records, as genblaze wrote them at generation time.

    Rehydrated rather than summarised: these carry the provider, params,
    timestamps and asset sha256 from the run that actually made the clip, so the
    receipt's lineage is the SDK's own record and not a retelling of it.
    """
    found: dict[int, tuple[dict, ...]] = {}
    for key in _keys(store, CLIP_PREFIX):
        if not key.endswith("manifest.json"):
            continue
        run = json.loads(store.get(key)).get("run", {})
        name = str(run.get("name", ""))
        if name.startswith("block-"):
            found[int(name.removeprefix("block-"))] = tuple(run.get("steps", []))
    return found


def fetch(store, key: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(store.get(key))
    return dest


def main() -> int:
    try:
        require("B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    state = RunState.load(RUN_ID)
    approver = arg("--approve")
    if approver:
        state = state.approve(approver)
        state.save()

    # Wall 3, before anything is fetched or spent.
    try:
        approval = approved_or_raise(state)
    except AssemblyError as exc:
        print(f"REFUSED  {exc}")
        return 1
    print(f"approved  {approval.approver} at {approval.ts}")

    if not anton_is_resolvable():
        print("FAIL  Anton is not resolvable by libass. ffmpeg does not embed it "
              "and a missing face falls back SILENTLY.\n"
              "      brew install --cask font-anton")
        return 1
    print("font      Anton resolved")

    kit = load()
    contract = assembly_contract(kit.voice)
    takes_s = [b.voice_duration_s for b in sorted(state.blocks, key=lambda b: b.n)]
    blocks = plan_timeline(takes_s, contract)

    store = backend(BUCKETS["assets"])
    mapping = clip_keys(store)
    missing = [b.n for b in blocks if b.n not in mapping]
    if missing:
        print(f"FAIL  no clip found for block(s) {missing}")
        return 1

    WORK.mkdir(parents=True, exist_ok=True)
    clips = [fetch(store, mapping[b.n], WORK / f"clip-{b.n:02d}.mp4") for b in blocks]
    takes = [
        fetch(store, f"{RUN_ID}/take-{b.n:02d}.mp3", WORK / f"take-{b.n:02d}.mp3")
        for b in blocks
    ]

    cues = []
    narration = {b.n: b.narration for b in state.blocks}
    for block in blocks:
        cues += list(subtitle_cues(
            narration[block.n],
            start_s=block.narration_start_s,
            take_s=block.take_s,
        ))
    ass_path = WORK / "subtitles.ass"
    ass_path.write_text(ass_document(kit.subtitle_ass, cues), encoding="utf-8")

    print(f"\n{'blk':<4}{'role':<11}{'start':>8}{'take':>8}{'tail':>7}{'len':>8}  clip")
    for block, clip in zip(blocks, clips):
        action, amount = clip_action(probe_duration(clip), block.length_s)
        print(f"{block.n:<4}{block.role:<11}{block.start_s:>8.2f}{block.take_s:>8.2f}"
              f"{block.tail_s:>7.2f}{block.length_s:>8.2f}  {action} {amount:.2f}s")

    gaps = [round(blocks[i].tail_s + blocks[i + 1].lead_in_s, 3)
            for i in range(len(blocks) - 1)]
    runtime = blocks[-1].end_s
    print(f"\ngaps      {gaps}  ({'all distinct' if len(set(gaps)) == len(gaps) else 'DUPLICATES'})")
    print(f"runtime   {runtime:.2f}s   cues {len(cues)}")

    # The bed. Generated once and cached: it is keyed to this timeline, so it is
    # only stale if the timeline moves — and re-composing on every assembly would
    # give the same story a different score each time it was cut.
    bed = WORK / "bed.mp3"
    if "--no-music" in sys.argv:
        bed = None
        print("\nmusic     skipped (--no-music)")
    elif bed.exists():
        print(f"\nmusic     cached {bed} ({probe_duration(bed):.2f}s)")
    else:
        spans = movement_spans(blocks)
        print("\nmusic     composing " + " → ".join(
            f"{s.name} {s.duration_ms / 1000:.1f}s" for s in spans))
        compose(blocks, bed)
        print(f"          {bed} ({probe_duration(bed):.2f}s), ducked under the voice")

    bed_gain, lufs = 0.0, None
    if bed is not None:
        lufs = measure_lufs(bed)
        bed_gain = gain_for(lufs)
        print(f"          {lufs} LUFS → gain {bed_gain} → {BED_TARGET_LUFS} LUFS "
              f"in the clear, ducked further under the voice")

    out = WORK / "cs1.mp4"
    render(blocks, clips, takes, ass_path=ass_path, out=out,
           music=bed, music_gain=bed_gain)
    measured = probe_duration(out)
    print(f"\nrendered  {out}  {measured:.2f}s  {out.stat().st_size / 1e6:.1f} MB")
    if abs(measured - runtime) > 0.5:
        print(f"WARN      rendered length differs from the plan by "
              f"{abs(measured - runtime):.2f}s")

    # --- the receipt -------------------------------------------------------
    raw_steps = block_steps(store)
    by_n = {b.n: b for b in state.blocks}
    records = [
        BlockRecord(
            timing=block,
            narration=by_n[block.n].narration,
            generation_steps=raw_steps.get(block.n, ()),
            take_uri=by_n[block.n].voice_uri,
            # Hashed from the file that was actually cut from, not carried over
            # from the narration run. `publishable()` blocked the first attempt
            # over exactly this: six audio assets with no digest, which would
            # have shipped a receipt naming files nobody could check.
            take_sha256=sha256_of(takes[block.n - 1]),
            claims=tuple(by_n[block.n].claims),
            voice_provider=next(
                (a.provider for a in by_n[block.n].attempts if a.status in ("in", "short", "long")),
                None,
            ),
            voice_model=next(
                (a.model for a in by_n[block.n].attempts if a.status in ("in", "short", "long")),
                None,
            ),
        )
        for block in blocks
    ]

    bed_step = None
    if bed is not None:
        bed_key = f"{RUN_ID}/bed.mp3"
        store.put(bed_key, bed.read_bytes(), content_type="audio/mpeg")
        bed_step = music_step(
            store.get_durable_url(bed_key), sha256_of(bed),
            model=MUSIC_MODEL,
            plan=[{"section": sp.name, "first_block": sp.first_block,
                   "duration_ms": sp.duration_ms} for sp in movement_spans(blocks)],
            measured_lufs=lufs, gain=bed_gain,
        )

    run = build_run(state, records, run_name=f"{RUN_ID}-assembled",
                    runtime_s=measured, music=bed_step)
    manifest = Manifest.from_run(run)
    manifest.canonical_hash = manifest.compute_hash()

    try:
        publishable(manifest)
    except ReceiptError as exc:
        print(f"\nBLOCKED  {exc}")
        return 1

    embedded = WORK / "cs1-embedded.mp4"
    embed(out, manifest, embedded)
    back = extract(embedded)

    print(f"\nmanifest  {len(run.steps)} steps · {len(manifest.to_canonical_json())} bytes canonical")
    print(f"          approved_by {run.metadata['approved_by']} at {run.metadata['approved_at']}")
    print(f"          hash {manifest.canonical_hash[:16]}…")
    print(f"embedded  {embedded}  {embedded.stat().st_size / 1e6:.1f} MB")
    print(f"round trip  extracted hash {back.canonical_hash[:16]}… "
          f"{'MATCH' if back.canonical_hash == manifest.canonical_hash else 'MISMATCH'}")

    key = f"{RUN_ID}/cs1.mp4"
    store.put(key, embedded.read_bytes(), content_type="video/mp4")
    print(f"published  {store.get_durable_url(key)}")
    print(f"\nverify with:  uv run genblaze verify --fetch {embedded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
