"""One command, one story.

    uv run python -m newsdesk stories/cs2.yaml
    uv run python -m newsdesk stories/cs2.yaml --stills-only     # ~$0.23
    uv run python -m newsdesk stories/cs2.yaml --only gate       # $0, no creds
    uv run python -m newsdesk stories/cs1.yaml --from blocks

This replaces `run_cs1_script.py`, `run_cs1_blocks.py` and `run_cs1_narration.py`,
each of which had its story frozen at the top of the file.

`--only gate` is the demo's refusal beat and CS-4's whole acceptance criterion:
it runs the deterministic wall with no provider constructed and no credential
required, which is what makes "$0 spent on a refusal" something you can watch
rather than something we assert.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from newsdesk.config import ConfigError, require
from newsdesk.pipeline import STAGES, Pipeline, PipelineError, StageResult
from newsdesk.state import RunState
from newsdesk.storyfile import StoryFileError, load_story

USAGE = __doc__

# What each stage actually needs, so a run asks for exactly the keys it will
# use. `gate` appears here deliberately with an empty list: it is the stage that
# must run on a machine holding no credentials at all.
_CREDENTIALS = {
    "script": ["GMI_API_KEY"],
    "gate": [],
    "blocks": ["GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY"],
    "narration": ["ELEVENLABS_API_KEY", "LMNT_API_KEY", "B2_KEY_ID", "B2_APP_KEY"],
    "assembly": ["B2_KEY_ID", "B2_APP_KEY"],
    "endcard": ["B2_KEY_ID", "B2_APP_KEY"],
    "caption": ["GMI_API_KEY"],
}


def _flag(name: str) -> bool:
    return name in sys.argv


def _opt(name: str, default: str = "") -> str:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def _planned() -> list[str]:
    """Which stages this invocation will run, in order."""
    only = _opt("--only")
    if only:
        if only not in STAGES:
            raise SystemExit(f"unknown stage '{only}'. Choose from: {', '.join(STAGES)}")
        return [only]
    start = _opt("--from", STAGES[0])
    if start not in STAGES:
        raise SystemExit(f"unknown stage '{start}'. Choose from: {', '.join(STAGES)}")
    return list(STAGES[STAGES.index(start):])


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    positional = [a for a in args if not a.startswith("-")]
    # The value of --only / --from is positional-looking; drop it.
    for opt in ("--only", "--from"):
        if opt in sys.argv:
            taken = _opt(opt)
            if taken in positional:
                positional.remove(taken)

    if not positional or _flag("--help") or _flag("-h"):
        print(USAGE)
        return 0 if _flag("--help") or _flag("-h") else 1

    try:
        story_file = load_story(Path(positional[0]))
    except StoryFileError as exc:
        print(f"FAIL  {exc}")
        return 1

    stages = _planned()
    stills_only = _flag("--stills-only")

    # Credentials are demanded per stage, not up front. `--only gate` must run
    # on a machine with no keys at all — that is the property CS-4 rests on, and
    # asking for a TTS key before a refusal would quietly destroy it.
    needed: list[str] = []
    for stage in stages:
        needed += _CREDENTIALS.get(stage, [])
    if needed:
        try:
            require(*dict.fromkeys(needed))
        except ConfigError as exc:
            print(f"FAIL  {exc}")
            return 1

    print(f"story     {story_file.id}  {story_file.story.title}")
    print(f"facts     {len(story_file.story.facts)}  all sourced (Wall 1 passed)")
    print(f"art       {story_file.through_line} -> {story_file.clip_prefix}")
    print(f"stages    {' -> '.join(stages)}\n")

    pipe = Pipeline.start(story_file, resume=not _flag("--fresh"))

    try:
        for stage in stages:
            result = _run_stage(pipe, stage, stills_only=stills_only)
            if result is None:
                continue
            mark = "skip" if result.skipped else ("ok" if result.ok else "FAIL")
            cost = f"  ${result.cost_usd:.3f}" if result.cost_usd else ""
            print(f"{mark:4}  {result.name:10}{cost}  {result.detail}")
            if not result.ok:
                print(f"\nstopped at {result.name}. Spend so far ${pipe.spent:.3f}.")
                pipe.save()
                return 1
    except PipelineError as exc:
        print(f"FAIL  {exc}")
        return 1

    print(f"\nspend     ${pipe.spent:.3f}")
    # Persist unless the run was purely a refusal check.
    #
    # This used to be gated on the stage list containing B2 credentials, which
    # was wrong in a way that printed success: `script` needs only GMI_API_KEY,
    # so `--only script` reported "6 blocks" and then wrote nothing at all. The
    # blocks existed in memory and were discarded on exit. Gate-only genuinely
    # must not write — it is the one path that runs with no credentials — so the
    # save is attempted and its failure is reported rather than assumed.
    if stages != ["gate"]:
        try:
            print(f"state     b2://newsdesk-runs/{pipe.save()}")
        except Exception as exc:  # noqa: BLE001 — a run that cannot save must say so
            print(f"WARNING   the run finished but state was not saved: {exc}")
            return 1
    return 0


def _run_stage(pipe: Pipeline, stage: str, *, stills_only: bool):
    """Dispatch one stage. Providers are built only for the stage that needs them."""
    if stage == "script":
        return pipe.stage_script()
    if stage == "gate":
        return pipe.stage_gate()
    if stage == "blocks":
        from genblaze_gmicloud import GMICloudImageProvider, GMICloudVideoProvider

        from newsdesk.blocks import register_seedance_ratio
        from newsdesk.pricing import register_all

        image, video = GMICloudImageProvider(), GMICloudVideoProvider()
        register_all(image=image, video=video)
        register_seedance_ratio(video)
        return asyncio.run(
            pipe.stage_blocks(
                image_provider=image, video_provider=video, stills_only=stills_only
            )
        )
    if stage == "narration":
        from genblaze_elevenlabs import ElevenLabsTTSProvider
        from genblaze_lmnt import LMNTProvider

        from newsdesk.brandkit import load as load_kit
        from newsdesk.narration import speaker
        from newsdesk.pricing import register_all

        elevenlabs, lmnt = ElevenLabsTTSProvider(), LMNTProvider()
        register_all(elevenlabs=elevenlabs, lmnt=lmnt)
        return asyncio.run(
            pipe.stage_narration(
                speak=speaker({"elevenlabs": elevenlabs, "lmnt": lmnt}),
                # The narrator is part of the kit: the diorama's is a war
                # reporter, the house's a measured documentary voice. Loading
                # the house kit here voiced every story in the house narrator
                # however its style-tokens.txt read.
                kit_voice=load_kit(kit_id=pipe.story_file.kit).voice,
            )
        )
    if stage == "assembly":
        # The cut lives in scripts/run_cs1_assemble.py, which is imported rather
        # than reimplemented: it is a working, verified path that has produced a
        # manifest surviving `genblaze verify` byte for byte, and a second
        # implementation of it would be a second thing to keep true.
        import sys as _sys
        from pathlib import Path as _Path

        scripts = str(_Path(__file__).resolve().parents[1] / "scripts")
        if scripts not in _sys.path:
            _sys.path.insert(0, scripts)
        import run_cs1_assemble as cut

        cut.configure(pipe.story_file)
        code = cut.main()

        # Re-read what assembly wrote. It owns the state from here — it records
        # the approval, flips status to `published` and attaches the final URI,
        # all by saving to B2 directly. Without this the pipeline's own save()
        # writes its stale in-memory copy back over the top, and the run reads
        # as `drafting` with `approval: null` forever while the verified MP4 sits
        # published beside it. Measured on CS-2, 2026-07-28: the manifest held
        # the approver and `genblaze verify` passed, and state.json had lost it.
        try:
            pipe.state = RunState.load(pipe.story_file.run_id)
        except Exception:  # noqa: BLE001 — a failed cut may not have written
            pass

        return pipe._record(StageResult(
            "assembly", code == 0,
            detail="MP4 cut, manifest embedded, verify it with `genblaze verify --fetch`"
            if code == 0 else "assembly refused or failed — see above",
        ))
    if stage == "endcard":
        return pipe.stage_endcard()
    if stage == "caption":
        return pipe.stage_caption()
    raise PipelineError(f"unknown stage {stage}")


if __name__ == "__main__":
    raise SystemExit(main())
