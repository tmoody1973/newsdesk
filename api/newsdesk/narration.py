"""One narrator, six takes (MOO-426, P0-5).

ElevenLabs is the primary and LMNT the fallback, so the resilience story CS-5
tells spans two modalities rather than one — the same run can lose its video
model and its voice and still finish, with the manifest naming who actually
spoke each block.

Three things here are consequences of measurement rather than design taste.

**The chain is walked here, not by `fallback_models`.** MOO-424 established that
genblaze's chain fires only on `ProviderErrorCode.MODEL_ERROR`, a branch its
classifier reaches only for "not found"/"not available" and only after auth and
server checks have claimed anything containing 401, 403, 400 or 5xx. So the
outer loop is ours. `_is_transient` is imported from `blocks` rather than copied:
it is the CS-5 finding itself, and two copies would drift apart the first time
one of them learned a new failure string.

**The take is measured after its silence is stripped, with `ffprobe`.**
`asset.duration` comes back `None` — genblaze probes it with `mutagen`, which is
not installed — and even if it were, it would report the padded length. Design
spec §6.6 makes every timing decision downstream depend on the real start of the
words, so the trim happens before the measurement, not after.

**The correction ladder is built from levers that exist on this stack.**
`voice.json` lists "lower speech rate one notch" as correction 2; it is
unreachable, because the genblaze ElevenLabs adapter builds `voice_settings`
from `stability`, `similarity_boost` and `style` only and never forwards
`speed`. And ElevenLabs documents SSML `<break>` on every model *except* v3 —
v3 takes audio tags (`[short pause]`, `[pause]`, `[long pause]`) instead. So a
short take is lengthened by pause tags at internal sentence boundaries, which is
`voice.json` correction 1 ("split into another sentence") done without touching
a word the journalist wrote. A long take has no word-preserving lever at all, so
it is re-rendered: v3 is non-deterministic and the same text measured 2.22-2.93
words per second across four takes, which is spread enough to be worth one roll.

Under §6.6 none of this is a sync constraint any more. Block length is derived
from the take, so a miss costs runtime, not desync — which is why the loop is
capped at two corrections and then hands the block to an editor.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import re
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Awaitable, Callable, Sequence
from urllib.parse import urlparse
from urllib.request import url2pathname

from genblaze_core import Modality, Pipeline

# Imported, not copied. The classifier IS the CS-5 finding — it is the reason a
# flaky 401 costs a retry instead of a provider switch — and a second copy would
# drift the first time either one learned a new failure string.
from newsdesk.blocks import RETRY_DELAYS_S, _is_transient
from newsdesk.config import BUCKETS, backend

# Two corrections, then an editor looks at it. Design spec §6.4: repeated
# identical failures mean the line is wrong, not the seed.
MAX_REVOICES = 2

# How many takes may be in flight at once. Measured, not chosen: six concurrent
# calls to ElevenLabs came back `code=rate_limit` and pushed four of six blocks
# onto LMNT. Two is under every published plan's concurrency limit, and six
# ten-second takes at two abreast still finish inside a minute.
TTS_CONCURRENCY = 2

# v3's audio tags, shortest first. Not SSML: ElevenLabs documents `<break>` on
# every model EXCEPT v3, and a break tag sent to v3 is a tag the narrator may
# simply read out loud.
#
# `[short pause]` is deliberately absent. It was in the first version by
# symmetry and never by measurement: scripts/spike_pause_tag.py quantified
# `[pause]` at +0.36s per boundary and `[long pause]` at +1.25s, and on the live
# CS-1 run block 6 spent both of its corrections on the short notch against a
# 0.26s deficit and moved about a tenth of a second. v3's audio tags are
# probabilistic, so the smallest one is the one most likely to be ignored — and
# a notch that costs a take and buys nothing spends an attempt an editor is
# waiting on.
PAUSE_TAGS = ("[pause]", "[long pause]")

# Where each notch stops being the right size, in seconds of deficit PER
# internal sentence boundary. The midpoint between the two measured
# per-boundary gains, 0.36s and 1.25s.
_NOTCH_CEILINGS = (0.80,)

# Peak rather than RMS, and -45dB rather than -60dB: TTS "silence" is room tone,
# not digital zero. A calibration knob, deliberately — the right threshold is a
# property of the voice and the codec, not something a model can reason out.
SILENCE_THRESHOLD_DB = -45
SILENCE_DETECTION = "peak"

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


class NarrationError(RuntimeError):
    """Raised when a take cannot be measured or the voice config is unusable."""


@dataclass(frozen=True)
class VoiceSpec:
    """One narrator on one provider, as published in the brand kit."""

    provider: str
    model: str
    voice_id: str
    voice_name: str | None = None

    @property
    def pause_tags(self) -> bool:
        """Whether this model takes `[pause]`-style audio tags.

        v3 only. Every other ElevenLabs model wants SSML `<break>` and LMNT
        wants neither, so a provider handed the wrong vocabulary reads the tag
        aloud in the middle of the story.
        """
        return self.model.startswith("eleven_v3")


@dataclass(frozen=True)
class Take:
    """One block's narration, and who actually spoke it.

    `duration_s` is the trimmed length — the number §6.6 derives block length
    from. `raw_duration_s` is kept beside it so "we stripped the silence" is a
    claim the manifest can support rather than assert.
    """

    n: int
    uri: str | None = None
    sha256: str | None = None
    local_path: Path | None = None
    provider: str | None = None
    model: str | None = None
    voice_id: str | None = None
    text: str | None = None
    duration_s: float | None = None
    raw_duration_s: float | None = None
    cost_usd: float = 0.0
    status: str = "failed"
    used_fallback: bool = False
    revoices: int = 0
    note: str | None = None
    attempts: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.status == "ready"

    @property
    def trimmed_s(self) -> float | None:
        """Silence removed from the two ends, in seconds."""
        if self.raw_duration_s is None or self.duration_s is None:
            return None
        return round(self.raw_duration_s - self.duration_s, 3)


# --- the published voice ---------------------------------------------------


def _spec(kit_voice: dict[str, Any], slot: str) -> VoiceSpec:
    entry = kit_voice.get(slot)
    if not isinstance(entry, dict):
        raise NarrationError(
            f"brand kit voice.json has no {slot!r} voice. Refusing to pick one — "
            f"a narrator chosen by a default is undisclosed casting."
        )
    missing = [k for k in ("provider", "model", "voice_id") if not entry.get(k)]
    if missing:
        raise NarrationError(
            f"voice.json {slot!r} is missing {', '.join(missing)}. A voice_id that "
            f"falls back to the provider default is a different narrator with the "
            f"manifest still naming this one."
        )
    return VoiceSpec(
        provider=str(entry["provider"]),
        model=str(entry["model"]),
        voice_id=str(entry["voice_id"]),
        voice_name=entry.get("voice_name"),
    )


def voice_specs(kit_voice: dict[str, Any]) -> tuple[VoiceSpec, VoiceSpec]:
    """The chain, in order, read from the published kit."""
    return _spec(kit_voice, "primary"), _spec(kit_voice, "fallback")


def take_window(kit_voice: dict[str, Any]) -> tuple[float, float]:
    """POL-5's runtime budget, from the kit rather than a code constant.

    §6.6 demoted this from a sync constraint to a runtime one, which is exactly
    why it must stay editable by an editor without a deploy.
    """
    window = (kit_voice.get("delivery") or {}).get("target_take_seconds")
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise NarrationError(
            "brand kit voice.json has no delivery.target_take_seconds — "
            "the take window is published, not hardcoded."
        )
    return float(window[0]), float(window[1])


# --- measurement -----------------------------------------------------------


def probe_duration(path: Path) -> float:
    """Length of an audio file in seconds, from ffprobe.

    Not `asset.duration`: the ElevenLabs adapter probes with `mutagen`, which is
    not installed, so it is always `None` — and it would report the padded
    length anyway.
    """
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    raw = proc.stdout.strip()
    try:
        return round(float(raw), 3)
    except ValueError:
        raise NarrationError(
            f"ffprobe could not measure {path.name}: {raw or proc.stderr.strip()[:200]!r}"
        ) from None


def strip_silence(src: Path, dst: Path) -> Path:
    """Remove leading and trailing silence, and nothing in between.

    `silenceremove` only trims the head, so the tail is done by reversing the
    stream, trimming its head, and reversing back. The obvious one-pass form —
    `stop_periods=-1` — removes EVERY silence in the file, which would strip the
    sentence-end pauses that voice.json measured as the only thing that got a
    take into the window.
    """
    trim = (
        f"silenceremove=start_periods=1:start_threshold={SILENCE_THRESHOLD_DB}dB"
        f":detection={SILENCE_DETECTION}"
    )
    proc = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-af", f"{trim},areverse,{trim},areverse", str(dst)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not dst.exists():
        raise NarrationError(f"ffmpeg could not trim {src.name}: {proc.stderr.strip()[:200]}")
    return dst


def classify(seconds: float, window: tuple[float, float]) -> str:
    """`short`, `in`, or `long` against the published window."""
    low, high = window
    if seconds < low:
        return "short"
    if seconds > high:
        return "long"
    return "in"


def _distance(seconds: float | None, window: tuple[float, float]) -> float:
    if seconds is None:
        return float("inf")
    low, high = window
    if seconds < low:
        return low - seconds
    if seconds > high:
        return seconds - high
    return 0.0


def best_take(takes: Sequence[Take], window: tuple[float, float]) -> Take | None:
    """The take closest to the window, which is not always the last one.

    Three attempts that all missed still produce a best available take. Keeping
    whichever happened to come last would throw away a 10.7s render in favour of
    a 6.0s one for no reason a viewer could hear.
    """
    return min(takes, key=lambda t: _distance(t.duration_s, window), default=None)


# --- the correction ladder -------------------------------------------------


def boundaries_in(narration: str) -> int:
    """How many internal sentence boundaries a line has — where a pause can go."""
    return max(len([s for s in _SENTENCE_BREAK.split(narration.strip()) if s]) - 1, 0)


def pause_tag(deficit_s: float, *, boundaries: int = 1, bump: int = 0) -> str:
    """Which pause notch to ask for, sized by the deficit **per boundary**.

    Per boundary because that is where the time is actually bought: a tag lands
    at each sentence break, so a line with three of them gets three times the
    lengthening from the same notch. Sizing against the whole deficit under-fires
    on a two-sentence block, which is how block 6 of the live CS-1 run of
    2026-07-28 spent two corrections and stayed short.
    """
    need = deficit_s / max(boundaries, 1)
    notch = sum(1 for ceiling in _NOTCH_CEILINGS if need > ceiling)
    return PAUSE_TAGS[min(notch + bump, len(PAUSE_TAGS) - 1)]


def paced(narration: str, tag: str) -> str:
    """Insert `tag` at every internal sentence boundary. Never after the last.

    A pause after the final sentence is trailing silence, and `strip_silence`
    removes it again — so it would cost a take and change nothing measurable.
    The words are untouched; only the spaces between sentences change.
    """
    sentences = [s for s in _SENTENCE_BREAK.split(narration.strip()) if s]
    return f" {tag} ".join(sentences)


# --- one take, walking the chain -------------------------------------------


async def _speak(speak: Callable[..., Any], spec: VoiceSpec, text: str) -> tuple[Path, float]:
    """Call the renderer, whether it is sync or async.

    The live renderer awaits `Pipeline.arun`; the test renderer returns a file
    it just wrote. Accepting both is what keeps the chain logic testable at $0
    without a mock standing in for the thing under test.
    """
    result = speak(spec, text)
    if inspect.isawaitable(result):
        result = await result
    return result


async def run_take(
    n: int,
    narration: str,
    *,
    specs: Sequence[VoiceSpec],
    window: tuple[float, float],
    speak: Callable[..., Any],
    max_revoices: int = MAX_REVOICES,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> Take:
    """Voice one block: walk the chain, measure, correct, keep the best.

    A provider that renders anything at all keeps the block — the correction
    loop stays on it rather than falling through to the fallback, because a
    substituted narrator is a visible downgrade and an out-of-window take is,
    since §6.6, only a runtime cost.
    """
    attempts: list[dict[str, Any]] = []
    spent = 0.0

    for spec in specs:
        candidates: list[Take] = []
        text = narration

        for revoice in range(max_revoices + 1):
            rendered: Path | None = None

            # Same model first, then down the chain. A transient 401 clears on
            # retry about half the time; answering it by switching providers
            # abandons a working voice and changes the narrator mid-story.
            for attempt_n in range(len(RETRY_DELAYS_S) + 1):
                if attempt_n:
                    await sleep(RETRY_DELAYS_S[attempt_n - 1])
                try:
                    rendered, cost = await _speak(speak, spec, text)
                except Exception as exc:  # noqa: BLE001 — a dead voice is data
                    transient = _is_transient(exc)
                    attempts.append({
                        "provider": spec.provider,
                        "model": spec.model,
                        "status": f"error: {type(exc).__name__}",
                        "detail": str(exc)[:160],
                        "retryable": transient,
                    })
                    if transient and attempt_n < len(RETRY_DELAYS_S):
                        continue
                    break
                spent += cost
                break

            if rendered is None:
                break  # this voice is exhausted; try the next one

            raw = probe_duration(rendered)
            trimmed = strip_silence(rendered, rendered.with_name(f"{rendered.stem}-trimmed{rendered.suffix}"))
            measured = probe_duration(trimmed)
            verdict = classify(measured, window)

            attempts.append({
                "provider": spec.provider,
                "model": spec.model,
                "status": verdict,
                "raw_duration_s": raw,
                "duration_s": measured,
                "cost_usd": round(cost, 4),
            })
            candidates.append(Take(
                n=n,
                local_path=trimmed,
                provider=spec.provider,
                model=spec.model,
                voice_id=spec.voice_id,
                text=text,
                duration_s=measured,
                raw_duration_s=raw,
                revoices=revoice,
                status="ready" if verdict == "in" else "review",
            ))

            # The one correction worth paying for: a short take gets pause tags
            # where the sentences already break. Measured on eleven_v3 —
            # `[pause]` adds ~0.5s per boundary, `[long pause]` ~1.2s — and it
            # leaves every word the journalist wrote exactly where it was.
            #
            # An overrun gets nothing, and that is a correction to this module's
            # first version. Both prescribed levers are unavailable:
            # `voice_settings.speed` is not forwarded by the genblaze adapter,
            # and shortening the line would edit words `claims.py` has already
            # traced to a fact. What is left is a fresh render, and the live
            # CS-1 run of 2026-07-28 priced that: four long blocks, eight extra
            # renders, one landed. About $0.25 to move the runtime of one block
            # by a second — and since §6.6 derives block length from the take,
            # a second of runtime is the entire cost of an overrun.
            if verdict == "in" or revoice == max_revoices or not (
                verdict == "short" and spec.pause_tags
            ):
                break
            text = paced(narration, pause_tag(
                window[0] - measured, boundaries=boundaries_in(narration), bump=revoice
            ))

        chosen = best_take(candidates, window)
        if chosen is not None:
            return replace(
                chosen,
                cost_usd=round(spent, 4),
                used_fallback=spec is not specs[0],
                attempts=tuple(attempts),
                note=None if chosen.status == "ready" else (
                    f"{chosen.duration_s}s is outside {window[0]}-{window[1]}s after "
                    f"{len(candidates) - 1} correction(s) — flagged for review"
                ),
            )

    tried = ", ".join(f"{a['provider']} ({a['status']})" for a in attempts)
    return Take(
        n=n,
        cost_usd=round(spent, 4),
        status="failed",
        note=f"no voice provider completed this block — tried {tried}",
        attempts=tuple(attempts),
    )


async def narrate(
    lines: Sequence[tuple[int, str]],
    *,
    specs: Sequence[VoiceSpec],
    window: tuple[float, float],
    speak: Callable[..., Any],
    concurrency: int = TTS_CONCURRENCY,
    **kwargs: Any,
) -> list[Take]:
    """Voice every block, a few at a time, in block order.

    The cap is the whole point. Six concurrent ElevenLabs calls came back
    `code=rate_limit` on 2026-07-28 and four of six blocks completed on LMNT —
    a narrator change caused by us, recorded in the manifest as though the
    provider had failed. A fallback that fires because we flooded the primary
    is not resilience; it is noise in the one record that is supposed to make
    substitutions visible.
    """
    gate = asyncio.Semaphore(concurrency)

    async def one(n: int, text: str) -> Take:
        async with gate:
            return await run_take(n, text, specs=specs, window=window,
                                  speak=speak, **kwargs)

    return list(await asyncio.gather(*(one(n, text) for n, text in lines)))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --- the live renderer, and landing the take in B2 -------------------------


def local_path_of(url: str) -> Path:
    """The file behind a `file://` asset URL.

    Both TTS adapters write the audio to disk and hand back `local_file_url()`,
    so the take is already local — which is what lets it be trimmed and measured
    before anything is uploaded. Percent-decoded rather than string-sliced,
    because a temp directory with a space in it is not a hypothetical on macOS.
    """
    parsed = urlparse(url)
    if parsed.scheme != "file":
        raise NarrationError(f"expected a local audio file, got {url!r}")
    return Path(url2pathname(parsed.path))


def speaker(providers: dict[str, Any], *, timeout: int = 180) -> Callable[..., Any]:
    """The live renderer: one Genblaze step per take, keyed by provider name.

    `raise_on_failure=True` on purpose — `run_take`'s chain is driven by
    exceptions, and a step that came back failed without raising would look to
    it like a successful render of a file that is not there.
    """

    async def speak(spec: VoiceSpec, text: str) -> tuple[Path, float]:
        provider = providers.get(spec.provider)
        if provider is None:
            raise NarrationError(f"no provider wired for {spec.provider!r}")
        result = await (
            Pipeline(f"take-{spec.provider}")
            .step(
                provider,
                model=spec.model,
                prompt=text,
                modality=Modality.AUDIO,
                voice_id=spec.voice_id,
            )
            .arun(raise_on_failure=True, timeout=timeout)
        )
        step = result.run.steps[0]
        if not step.assets:
            raise NarrationError(f"{spec.provider} returned no audio for block text")
        return local_path_of(step.assets[0].url), float(getattr(step, "cost_usd", None) or 0.0)

    return speak


_CONTENT_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".opus": "audio/opus"}


def store_take(take: Take, *, prefix: str, store: Any | None = None) -> Take:
    """Upload the trimmed take to b2://newsdesk-assets and record its digest.

    The trimmed file is the one that ships, so it is the one that gets a URL —
    the raw take's only lasting trace is `raw_duration_s`, which is what makes
    "we stripped the silence" checkable rather than merely stated. A failed take
    uploads nothing; a zero-byte object in the assets bucket is a fact-checker's
    dead link.
    """
    if take.local_path is None or not take.local_path.exists():
        return take
    store = store if store is not None else backend(BUCKETS["assets"])
    key = f"{prefix}/take-{take.n:02d}{take.local_path.suffix}"
    data = take.local_path.read_bytes()
    store.put(key, data, content_type=_CONTENT_TYPES.get(take.local_path.suffix, "audio/mpeg"))
    return replace(take, uri=store.get_durable_url(key), sha256=sha256_of(take.local_path))
