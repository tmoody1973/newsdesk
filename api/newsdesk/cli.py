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
from newsdesk.pipeline import STAGES, Pipeline, PipelineError
from newsdesk.storyfile import StoryFileError, load_story

USAGE = __doc__


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
    # on a machine with no keys at all — that is the property CS-4 rests on.
    needs_money = {"script", "blocks", "narration"} & set(stages)
    if needs_money:
        try:
            require("GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
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
    if needs_money:
        print(f"state     b2://newsdesk-runs/{pipe.save()}")
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
    if stage in ("narration", "assembly"):
        # Not yet driven from here. Both still work; they are still reached by
        # scripts/run_cs1_narration.py and scripts/run_cs1_assemble.py, which
        # remain hardcoded to CS-1. Printing this rather than silently
        # succeeding, because a run that reports "ok" for a stage it did not
        # perform is the failure this whole handoff is a reaction to.
        print(f"todo  {stage:10}  not yet wired into the orchestrator — "
              f"use scripts/run_cs1_{stage}.py (CS-1 only)")
        return None
    raise PipelineError(f"unknown stage {stage}")


if __name__ == "__main__":
    raise SystemExit(main())
