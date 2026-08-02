"""The orchestrator — one story in, one run through every stage.

Before this module there was no single entry point. Five scripts, each with
`RUN_ID` and `CLIP_PREFIX` frozen at the top and `story = cs1_story()` imported
from the test fixtures. Making a second video meant hand-editing constants in
four files and running five commands in the right order. That one gap is what
blocked CS-2, blocked PRD P0-9's "a judge can execute CS-2 end-to-end without
help", and blocked live generation from the web app.

Nothing here is new capability. Every stage below already existed and already
took the story as a parameter — `generate_script`, `check`, `run_block`,
`narrate`. The engine was general the whole time; there was simply nothing to
drive it. This is the driver.

**Stages are resumable and individually addressable**, because a run is ~5
minutes of wall clock and several dollars, and the failure mode that actually
happens is stage 4 of 5 dying on a provider timeout. Re-running the whole thing
to recover would re-roll the pictures — which costs money AND silently changes
the video, since a second roll of the same prompt is a different image. So each
stage checks whether its output already exists before it spends anything.

`RunState` is the resume record and it already knew how to be one: it is saved
to B2 after every stage, which is also exactly what the web app's Run Board
polls. No queue, no websocket, no database.

Design notes:

* The **gate runs before any provider is constructed**, not merely before the
  paid call. `$0 on a refusal` is a structural property here, the same way
  `gate.py` keeps its import graph free of anything network-capable.
* Providers are injected. The whole orchestration path is therefore testable
  at $0, which is what lets the stage ordering and the resume logic be tested
  in CI rather than discovered on a credit card.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Sequence

from newsdesk.assembly import resolve_ffmpeg
from newsdesk.blocks import run_block, run_still, sink
from newsdesk.brandkit import load as load_kit
from newsdesk.caption import generate_captions
from newsdesk.decisions import Ledger
from newsdesk.endcard import EndCard, EndCardError, append_card, render_card
from newsdesk.narration import narrate, store_take, take_window, voice_specs
from newsdesk.policy.gate import check
from newsdesk.scene import ThroughLine, build_block_prompt
from newsdesk.script import generate_script
from newsdesk.state import Attempt, Block, RunState
from newsdesk.storyfile import StoryFile

BLOCKS = 6

# Stage names, in the only order they can run. Each is the name a caller passes
# to `--only` / `--from`, and the name that appears in the run's event log, so
# renaming one changes a user-visible interface and an audit record at once.
STAGES = ("script", "gate", "blocks", "narration", "assembly", "endcard", "caption")


class PipelineError(RuntimeError):
    """A stage could not complete and the run must not continue past it."""


@dataclass(frozen=True)
class StageResult:
    """What one stage did, and what it cost.

    `skipped` is not a detail: it is the difference between a resumed run and a
    re-rolled one. A resumed run reuses the pictures the human already looked
    at; a re-rolled run quietly replaces them.
    """

    name: str
    ok: bool
    cost_usd: float = 0.0
    skipped: bool = False
    detail: str = ""


@dataclass
class Pipeline:
    """One story, driven through the stages.

    Mutable by design and the only mutable thing here — it holds `state`, which
    is replaced (never mutated) after every transition, so the object is a
    cursor over a chain of immutable states rather than a bag of fields.
    """

    story_file: StoryFile
    state: RunState
    ledger: Ledger = field(default_factory=Ledger)
    blocks: tuple[Any, ...] = ()
    results: list[StageResult] = field(default_factory=list)

    @classmethod
    def start(cls, story_file: StoryFile, *, resume: bool = True) -> Pipeline:
        """Load the existing run for this story, or begin a new one.

        Resume is the default because the expensive thing is already-generated
        assets, and the safe direction to be wrong in is "did not spend money".
        """
        state: RunState | None = None
        if resume:
            try:
                state = RunState.load(story_file.run_id)
            except Exception:  # noqa: BLE001 — no prior run is the normal case
                state = None

        if state is None:
            story = story_file.story
            state = RunState(
                run_id=story_file.run_id,
                story=story.title,
                facts=tuple(
                    {
                        "id": f.id,
                        "text": f.text,
                        "sources": [
                            {"kind": s.kind, "value": s.value, "dataset": s.dataset,
                             "row_id": s.row_id, "page": s.page}
                            for s in f.sources
                        ],
                    }
                    for f in story.facts
                ),
                art_direction={"through_line": story_file.through_line},
            )
        return cls(story_file=story_file, state=state)

    # --- stages -------------------------------------------------------------

    def stage_script(self, *, chat_fn: Callable[..., Any] | None = None) -> StageResult:
        """Wall 1 then the script. Text only — cents, not dollars."""
        if self.state.blocks and all(b.narration for b in self.state.blocks):
            self.blocks = self.blocks or _blocks_from_state(self.state)
            return self._record(StageResult(
                "script", True, skipped=True,
                detail=f"{len(self.state.blocks)} blocks already scripted",
            ))

        kwargs = {"chat_fn": chat_fn} if chat_fn else {}
        state, ledger, blocks = generate_script(
            self.state, self.ledger, self.story_file.story, **kwargs
        )
        self.state, self.ledger = state, ledger

        if not blocks:
            rejections = "; ".join(d.reason for d in ledger.rejections()[-3:])
            return self._record(StageResult(
                "script", False,
                detail=f"no block survived checking — {rejections or 'see ledger'}",
            ))

        self.blocks = blocks
        self.state = self.state.log("script", f"{len(blocks)} blocks written")
        self.state = _attach_blocks(self.state, blocks)
        return self._record(StageResult("script", True, detail=f"{len(blocks)} blocks"))

    def stage_gate(self) -> StageResult:
        """Wall 2, on every block, before a provider object even exists.

        Deliberately its own stage rather than a check inside `stage_blocks`.
        The demo's rejection beat IS this stage, and CS-4's whole acceptance
        criterion is that it can run with no credentials configured at all.
        """
        through_line = self.through_line()
        blocked: list[str] = []
        for n in range(1, BLOCKS + 1):
            prompt = build_block_prompt(through_line, n, BLOCKS)
            verdict = check(prompt)
            if not verdict.passed:
                blocked.append(f"block {n}: {verdict.explain()}")

        if blocked:
            self.state = self.state.log("gate", "refused before any spend")
            return self._record(StageResult(
                "gate", False, detail="\n".join(blocked),
            ))

        rules = len(check(build_block_prompt(through_line, 1, BLOCKS)).findings)
        self.state = self.state.log("gate", f"{BLOCKS} blocks x {rules} rules passed")
        return self._record(StageResult(
            "gate", True, detail=f"{BLOCKS} blocks x {rules} rules, $0 spent",
        ))

    def stage_endcard(self) -> StageResult:
        """Append the publisher's mark to a published cut.

        Its own stage rather than an edit to scripts/run_cs1_assemble.py: that
        file is the verified path whose manifest survives `genblaze verify`
        byte for byte, and its own call site says a second implementation would
        be a second thing to keep true. This reads what it produced instead.
        """
        final = self.state.final or {}
        # A card already on `final` means an earlier run of this stage already
        # applied it and `final["uri"]` now points at the *branded* b2:// URI —
        # not a local path. Re-running would hand that URI to `Path(...)` and
        # die inside `append_card`'s ffmpeg concat instead of skipping cleanly,
        # which is exactly the resumability this module promises (module
        # docstring, :15). Checked first, before the "was one requested" branch
        # below, since a leftover `end_card_request` is expected to still be
        # sitting on `final` once applied.
        if final.get("end_card"):
            return self._record(StageResult(
                name="endcard", ok=True, skipped=True,
                detail="end card already applied",
            ))
        spec = final.get("end_card_request")
        if not spec:
            return self._record(StageResult(
                name="endcard", ok=True, skipped=True,
                detail="no end card requested",
            ))
        if not self.state.is_approved:
            raise PipelineError(
                "the end card re-publishes the video, and publishing needs a "
                "named human — approve the run first"
            )

        source = Path(self.state.final["uri"])
        card_mp4 = source.with_name("endcard.mp4")
        branded = source.with_name("final-branded.mp4")
        try:
            render_card(Path(spec["local_path"]), card_mp4, url=spec.get("url"),
                        ffmpeg=resolve_ffmpeg(needs_subtitles=False))
            append_card(source, card_mp4, branded,
                        ffmpeg=resolve_ffmpeg(needs_subtitles=False))
        except EndCardError as exc:
            # EndCardError is a plain ValueError, not a PipelineError — cli.py
            # only catches PipelineError around the stage loop, so left alone
            # this crashes with a raw traceback. A corrupt logo is the path a
            # journalist hits by uploading a bad image, not an operator error,
            # so it goes through the same ok=False channel stage_blocks uses
            # for a failed encode: cli.py prints "FAIL"/"stopped at endcard"
            # cleanly AND still calls pipe.save(), so the approval already on
            # this run survives a retry with a fixed image.
            return self._record(StageResult(
                name="endcard", ok=False, detail=str(exc),
            ))

        card = EndCard(image_uri=spec["uri"], url=spec.get("url"),
                       supplied_by=self.state.approval.approver)
        self.state = replace(self.state, final={
            **(self.state.final or {}),
            "uri": _publish_branded(branded, self.state.run_id),
            "end_card": card.manifest_entry(),
        })
        # NO self.state.save() here. RunState.save() calls backend(...).put() —
        # it reaches B2 over the network, and api/.env carries live credentials,
        # so a stage that saves makes every test touching it hit the network and
        # breaks the suite's $0 / no-network guarantee. No stage method saves;
        # persistence is Pipeline.save(), called by the CLI. Found in Task 3,
        # where the same line was written into the brief and caught before merge.
        return self._record(StageResult(
            name="endcard", ok=True,
            detail=f"card appended, supplied by {card.supplied_by}",
        ))

    def stage_caption(self, *, chat_fn: Callable[..., Any] | None = None) -> StageResult:
        """Social captions for a finished run. Text only — about a cent.

        Runs after assembly because the request was for captions once the video
        exists. It reads the script, not the video, so it is safe to re-run with
        `--only caption` without touching a single rendered frame.
        """
        self.state, self.ledger, caps = generate_captions(
            self.state,
            self.ledger,
            self.story_file.story,
            tuple(self.state.blocks),
            through_line=self.state.art_direction.get("through_line", ""),
            chat_fn=chat_fn,
        )
        payload = [
            {"platform": c.platform, "variant": c.variant, "hook": c.hook,
             "body": c.body, "cta": c.cta, "hashtags": list(c.hashtags),
             "sources": list(c.sources), "text": c.text}
            for c in caps
        ]
        self.state = replace(
            self.state, final={**(self.state.final or {}), "captions": payload}
        )
        return self._record(StageResult(
            "caption", True,
            detail=f"{len(caps)} captions" if caps else "no caption traced",
        ))

    async def stage_blocks(
        self,
        *,
        image_provider: Any,
        video_provider: Any,
        stills_only: bool = False,
    ) -> StageResult:
        """Six blocks, concurrently. The only stage that spends real money.

        The gate is NOT re-run here — `stage_gate` owns it and the runner
        refuses to reach this stage without it. One wall, one owner.
        """
        through_line = self.through_line()
        prompts = [build_block_prompt(through_line, n, BLOCKS) for n in range(1, BLOCKS + 1)]
        prefix = self.story_file.clip_prefix.rstrip("/")

        async def one(prompt: Any) -> tuple[int, bool, float, str, str | None, str | None]:
            if stills_only:
                url, cost, model = await run_still(
                    prompt, image_provider=image_provider, sink_=sink(prefix)
                )
                return prompt.block, bool(url), cost, model, url, None
            result = await run_block(
                prompt,
                image_provider=image_provider,
                video_provider=video_provider,
                sink_=sink(prefix),
            )
            return (
                prompt.block, result.ok, result.cost_usd, result.video_model,
                result.still_uri, result.clip_uri,
            )

        outcomes = await asyncio.gather(*(one(p) for p in prompts))

        spent = sum(o[2] for o in outcomes)
        failed = [str(o[0]) for o in sorted(outcomes) if not o[1]]
        for n, ok, cost, model, still, clip in sorted(outcomes):
            # The URIs go ON the block, not only into the log. Without this the
            # state carries no pictures at all, and every screen that shows a
            # frame — the Run Board, Editor Review — renders grey rectangles for
            # a run that completed perfectly. Found by looking at Editor Review
            # against a real run, 2026-07-28.
            self.state = self.state.with_block(
                n,
                status="ready" if ok else "failed",
                still_uri=still,
                clip_uri=clip,
            ).log(
                "blocks", f"block {n} {'ready' if ok else 'FAILED'} on {model}",
                cost_usd=cost, block=n, model=model,
            )

        if failed:
            return self._record(StageResult(
                "blocks", False, cost_usd=spent,
                detail=f"blocks {', '.join(failed)} produced nothing",
            ))
        return self._record(StageResult(
            "blocks", True, cost_usd=spent,
            detail=f"{BLOCKS}/{BLOCKS} ready" + (" (stills only)" if stills_only else ""),
        ))

    async def stage_narration(self, *, speak: Any, kit_voice: dict[str, Any]) -> StageResult:
        """Six takes on the published narrator, stored under this story's prefix.

        Resumable on the same principle as the script: a block that already has
        a `voice_uri` is left alone. Re-voicing is not merely a repeat charge —
        a new take has a DIFFERENT duration, and §6.6 derives every block's
        length on the timeline from that number. Re-voicing one block silently
        re-cuts the whole video.
        """
        done = [b for b in self.state.blocks if b.voice_uri]
        if len(done) == len(self.state.blocks) and self.state.blocks:
            return self._record(StageResult(
                "narration", True, skipped=True,
                detail=f"{len(done)} takes already voiced",
            ))

        lines = [(b.n, b.narration) for b in sorted(self.state.blocks, key=lambda b: b.n)]
        if not lines:
            return self._record(StageResult(
                "narration", False, detail="no script to voice — run the script stage",
            ))

        primary, fallback = voice_specs(kit_voice)
        window = take_window(kit_voice)
        takes = [
            store_take(t, prefix=self.story_file.narration_prefix)
            for t in await narrate(
                lines, specs=[primary, fallback], window=window, speak=speak
            )
        ]

        spent = sum(t.cost_usd for t in takes)
        failed = [str(t.n) for t in sorted(takes, key=lambda t: t.n) if not t.ok]
        review = sum(1 for t in takes if t.status == "review")

        for take in sorted(takes, key=lambda t: t.n):
            self.state = self.state.with_block(
                take.n,
                status="ready" if take.ok else (
                    "failed" if take.status == "failed" else "voicing"
                ),
                voice_uri=take.uri,
                voice_duration_s=take.duration_s,
                attempts=tuple(
                    Attempt(
                        n=i + 1,
                        provider=a.get("provider", "?"),
                        model=a.get("model", "?"),
                        status=str(a.get("status")),
                        cost_usd=a.get("cost_usd"),
                        note=a.get("detail"),
                    )
                    for i, a in enumerate(take.attempts)
                ),
            ).log(
                "narrate",
                f"block {take.n} voiced by {take.provider} at {take.duration_s}s",
                block=take.n, provider=take.provider, model=take.model,
                cost_usd=take.cost_usd,
            )

        if failed:
            return self._record(StageResult(
                "narration", False, cost_usd=spent,
                detail=f"blocks {', '.join(failed)} were not voiced",
            ))

        runtime = sum(t.duration_s or 0.0 for t in takes)
        note = f", {review} outside the take window" if review else ""
        return self._record(StageResult(
            "narration", True, cost_usd=spent,
            detail=f"{len(takes)} takes, {runtime:.1f}s of narration{note}",
        ))

    # --- helpers ------------------------------------------------------------

    def through_line(self) -> ThroughLine:
        """The art-direction menu item this story picked, from the PUBLISHED kit.

        Resolved here rather than at load time so the failure — "the kit does
        not offer that through-line" — happens once, in one place, with the
        list of what it does offer. `brandkit.load()` reads B2 and never falls
        back to the working copy beside the code.
        """
        kit = load_kit()
        wanted = self.story_file.through_line
        entry = next(
            (e for e in kit.through_lines["through_lines"] if e["id"] == wanted), None
        )
        if entry is None:
            offered = ", ".join(e["id"] for e in kit.through_lines["through_lines"])
            raise PipelineError(
                f"the published brand kit offers no through-line '{wanted}'. "
                f"Available: {offered}"
            )
        return ThroughLine.from_kit(entry)

    def _record(self, result: StageResult) -> StageResult:
        self.results.append(result)
        return result

    @property
    def spent(self) -> float:
        return round(sum(r.cost_usd for r in self.results), 4)

    def save(self) -> str:
        return self.state.save()


def _publish_branded(path: Path, run_id: str) -> str:
    """Upload the branded cut beside the original and return its URI.

    Separate function so the test can replace it without a B2 credential; the
    stage itself must never learn how storage works.
    """
    from newsdesk.config import BUCKETS, backend

    store = backend(BUCKETS["runs"])
    key = f"{run_id}/final-branded.mp4"
    store.put(key, path.read_bytes())
    return f"b2://{BUCKETS['runs']}/{key}"


def _attach_blocks(state: RunState, blocks: Sequence[Any]) -> RunState:
    """Put the written lines on the state so a resume can skip the script stage."""
    return replace(
        state,
        blocks=tuple(
            Block(
                n=b.n,
                narration=b.narration,
                # `fact_ids` is a property on ScriptBlock: deduplicated, in
                # first-mention order. Recomputing it here would be a second
                # implementation of the thing the block card renders.
                fact_ids=b.fact_ids,
                claims=tuple(
                    {"spoken": c.spoken, "fact_id": c.fact_id, "evidence": c.evidence}
                    for c in b.claims
                ),
            )
            for b in blocks
        ),
    )


def _blocks_from_state(state: RunState) -> tuple[Any, ...]:
    """Rehydrate just enough of the script for the later stages.

    Narration and block number are all the downstream stages read. Notably this
    does NOT re-run the model: re-generating a script produces DIFFERENT lines,
    which would invalidate takes already cut from the old ones and any human
    approval attached to that cut.
    """
    from newsdesk.claims import Claim, ScriptBlock

    return tuple(
        ScriptBlock(
            n=b.n,
            narration=b.narration,
            claims=tuple(
                Claim(spoken=c["spoken"], fact_id=c["fact_id"], evidence=c["evidence"])
                for c in b.claims
            ),
        )
        for b in sorted(state.blocks, key=lambda b: b.n)
    )
