"""The worker's HTTP surface.

A run is ~5 minutes of wall clock, which is why this exists at all: it cannot be
a Vercel function, and the web app cannot hold a connection open for it. So the
shape is deliberately dull —

    POST /runs      accept a story, start a run, answer immediately with its id
    GET  /runs/{id} the run's state, proxied from B2
    GET  /health    can this container actually cut a video

— and the progress UI is the Run Board polling `GET /runs/{id}`. No queue, no
websocket, no database. `RunState` was already the resume record and already
saved to B2 after every stage; this only exposes it.

**Why `GET /runs/{id}` proxies rather than pointing the browser at B2.** The runs
bucket is private and must stay that way: it holds the fact ledger, the claim
map and the approver's name before anything is published. Handing the browser a
B2 key to read it would trade a private bucket for a public one.

Stdlib `http.server`, not a framework. The ceiling is real and named here rather
than discovered: `ThreadingHTTPServer` is fine for a handful of concurrent runs
and would not survive being someone's actual product. `MAX_CONCURRENT_RUNS`
keeps it honest — a container that accepts a seventh run it has no CPU for is
lying to six people.
"""

from __future__ import annotations

import json
import os
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from newsdesk.config import BUCKETS, backend
from newsdesk.storyfile import StoryFileError, parse_story

# A run is CPU-and-network bound for ~5 minutes. Beyond a few at once the
# provider rate limits bite first (TTS_CONCURRENCY is 2 per run for a reason)
# and every run gets slower rather than any of them failing honestly.
MAX_CONCURRENT_RUNS = int(os.getenv("NEWSDESK_MAX_CONCURRENT_RUNS", "3"))

# Set on the container. Unset means open, which is correct for local development
# and wrong everywhere else — `/health` reports which mode it is in so a deploy
# that forgot the code is visible rather than quietly public.
ACCESS_CODE = os.getenv("NEWSDESK_ACCESS_CODE", "")

_running: set[str] = set()
_lock = threading.Lock()


class RunRejected(Exception):
    """A run that will not be started, with the status code to say so."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class IngestRejected(Exception):
    """A `/ingest` request that will not be served, with the status to say so."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def _parse_body(raw: bytes) -> Any:
    """Parse a request body's raw bytes as JSON. Shared by `/runs` and
    `/ingest` so both fail the same way on the same malformed input; pulled
    out as a pure function so the failure is testable without a socket.
    """
    return json.loads(raw or b"{}")


def _validate_ingest_url(raw: Any) -> str:
    """Validate a posted `url`, returning it stripped. Everything here is a
    422 (a refusal), never a 500 — a bad or dangerous URL is an expected
    input, not a bug.

    `http://` gets its own branch rather than falling through to
    `check_ssrf`: `check_ssrf` (`resolve_ssrf`) is HTTPS-only and would
    refuse it anyway, but with genblaze's internal wording ("Only HTTPS URLs
    are allowed, got: http://") — accurate, and useless to a journalist who
    just pasted a small paper's plain http:// link. This is our gate, so the
    message here can actually name the fix. `check_ssrf` still runs, and is
    still the authority, for every URL that reaches it — which after this
    branch is only ever `https://`.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise IngestRejected(422, "a url is required")
    url = raw.strip()

    scheme = urlparse(url).scheme
    if scheme == "http":
        raise IngestRejected(
            422,
            "that link is http:// — try the https:// version, "
            "or paste the text of the story instead.",
        )
    if scheme != "https":
        raise IngestRejected(
            422, f"unsupported URL scheme '{scheme}' — paste a link to the story"
        )

    # Private import — same as genblaze's own providers/_ffmpeg_utils.py,
    # which reuses this exact function for its own HTTP-input SSRF check
    # rather than forking one. Not a public genblaze contract.
    #
    # This resolves the host a second time — `_http_get_stream` in
    # `ingest.py` re-resolves and re-pins on every hop internally, which is
    # what actually closes the DNS-rebinding TOCTOU window. This earlier
    # call buys nothing against that; what it buys is a $0 refusal before
    # any fetch happens at all, for the common case (an obviously private
    # host) that doesn't need a hop-by-hop guarantee to catch.
    from genblaze_core._utils import check_ssrf

    try:
        check_ssrf(url)
    except ValueError as exc:
        raise IngestRejected(422, str(exc)) from exc

    return url


def _claim_slot(run_id: str) -> None:
    with _lock:
        if run_id in _running:
            raise RunRejected(409, f"run '{run_id}' is already in flight")
        if len(_running) >= MAX_CONCURRENT_RUNS:
            raise RunRejected(
                503,
                f"this worker is already running {len(_running)} stories. "
                f"Try again in a few minutes.",
            )
        _running.add(run_id)


def _release(run_id: str) -> None:
    with _lock:
        _running.discard(run_id)


def _execute(story_file: Any, stages: list[str], approver: str) -> None:
    """One run, start to finish, on its own thread.

    Every failure is written into the run's own state before the thread dies.
    A run that vanishes without a trace is worse than one that failed: the Run
    Board would poll a state that never changes and the page would spin forever.
    """
    from newsdesk.cli import _run_stage
    from newsdesk.pipeline import Pipeline

    pipe = Pipeline.start(story_file)
    try:
        if approver:
            # Saved immediately, not merely held: the assembly stage re-loads
            # RunState from B2 rather than reading this object, so an approval
            # that only exists in memory is an approval Wall 3 cannot see — and
            # a run of `--only assembly` would be refused by its own approver.
            pipe.state = pipe.state.approve(approver)
            pipe.save()
        for stage in stages:
            result = _run_stage(pipe, stage, stills_only=False)
            if result is not None and not result.ok:
                pipe.state = pipe.state.log(
                    "error", f"stage {stage} failed: {result.detail}"
                )
                break
            pipe.save()
    except Exception as exc:  # noqa: BLE001 — the thread is the last line here
        pipe.state = pipe.state.log(
            "error", f"{type(exc).__name__}: {str(exc)[:300]}"
        )
        traceback.print_exc()
    finally:
        try:
            pipe.save()
        finally:
            _release(story_file.run_id)


class Handler(BaseHTTPRequestHandler):
    server_version = "newsdesk"

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        self.send_response(status)
        # The web app is on another origin. Read-only surface, and the access
        # code is what actually gates starting a run.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Access-Code")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        if status == 204:
            # A 204 carries no body and MUST NOT carry Content-Length
            # (RFC 9110 §15.3.5). Fly's HTTP/2 edge rejects the violation as a
            # malformed frame, which killed every browser CORS preflight —
            # the wizard's POSTs died as "network connection was lost".
            self.end_headers()
            return
        body = json.dumps(payload).encode()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        return not ACCESS_CODE or self.headers.get("X-Access-Code") == ACCESS_CODE

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, {})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            return self._send(200, _health())

        if self.path.startswith("/runs/"):
            run_id = self.path.removeprefix("/runs/").strip("/")
            if not run_id or "/" in run_id:
                return self._send(400, {"error": "bad run id"})
            try:
                raw = backend(BUCKETS["runs"]).get(f"{run_id}/state.json")
            except Exception:  # noqa: BLE001 — an unknown run is a 404, not a 500
                return self._send(404, {"error": f"no run '{run_id}'"})
            return self._send(200, json.loads(raw.decode()))

        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")
        if path == "/ingest":
            return self._handle_ingest()
        if path != "/runs":
            return self._send(404, {"error": "not found"})
        if not self._authorized():
            return self._send(401, {"error": "an access code is required"})

        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = _parse_body(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "body must be JSON"})

        # Wall 1 at the edge. The same parser the CLI uses, so a story posted
        # from the browser is held to the identical standard as one on disk —
        # no fact without a source, and the refusal names the fact.
        try:
            story_file = parse_story(body.get("story"), where="posted story")
        except StoryFileError as exc:
            return self._send(422, {"error": str(exc)})

        stages = body.get("stages") or ["script", "gate", "blocks", "narration", "assembly"]
        approver = str(body.get("approver") or "").strip()
        if "assembly" in stages and not approver:
            # Wall 3, refused at the door rather than five minutes and several
            # dollars later. Assembly cannot publish without a named human, so a
            # run that ends in assembly and carries no name is one we already
            # know the ending of.
            return self._send(422, {
                "error": "a run that ends in assembly needs an approver — "
                         "publishing is unreachable without a named human"
            })

        try:
            _claim_slot(story_file.run_id)
        except RunRejected as exc:
            return self._send(exc.status, {"error": str(exc)})

        threading.Thread(
            target=_execute, args=(story_file, list(stages), approver), daemon=True
        ).start()

        self._send(202, {
            "run_id": story_file.run_id,
            "stages": stages,
            "poll": f"/runs/{story_file.run_id}",
        })

    def _handle_ingest(self) -> None:
        """`POST /ingest` — paste a URL, get proposed facts back.

        Synchronous and cheap (one `chat()` call): no thread, no slot, unlike
        `/runs`. See `newsdesk/ingest.py` for why this isn't a `judged()` role
        and what `dropped`/`article_chars` are for.
        """
        if not self._authorized():
            return self._send(401, {"error": "an access code is required"})

        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = _parse_body(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "body must be JSON"})

        try:
            url = _validate_ingest_url(body.get("url") if isinstance(body, dict) else None)
        except IngestRejected as exc:
            return self._send(exc.status, {"error": str(exc)})

        from newsdesk.ingest import IngestError, propose_facts

        try:
            result = propose_facts(url)
        except IngestError as exc:
            # ingest.py's own messages already name the fallback ("...paste
            # the text of the story instead.") — passed through as-is.
            return self._send(422, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 — a provider failure, not ours
            return self._send(502, {"error": f"{type(exc).__name__}: {exc}"})

        self._send(200, {
            "proposals": [
                {"text": p.text, "quote": p.quote, "url": p.url} for p in result.proposals
            ],
            "dropped": result.dropped,
            "article_chars": result.article_chars,
        })


def _health() -> dict[str, Any]:
    """Can this container actually finish a run?

    Checks the two things that fail SILENTLY rather than loudly, both of which
    have burned this project: ffmpeg without libass renders a video with no
    captions and exits 0, and a missing Anton falls back to another face without
    a word. Reported here so a bad image is caught by a health check rather than
    by watching the output.
    """
    from newsdesk.assembly import AssemblyError, anton_is_resolvable, resolve_ffmpeg

    try:
        ffmpeg = resolve_ffmpeg(needs_subtitles=True)
        subtitles = True
    except AssemblyError as exc:
        ffmpeg, subtitles = str(exc)[:120], False

    anton = anton_is_resolvable()
    return {
        "ok": subtitles and anton,
        "ffmpeg_with_libass": ffmpeg if subtitles else None,
        "subtitles_filter": subtitles,
        "anton_installed": anton,
        "access_code_required": bool(ACCESS_CODE),
        "running": sorted(_running),
        "capacity": MAX_CONCURRENT_RUNS,
    }


def serve(port: int | None = None) -> None:
    bind = int(port or os.getenv("PORT", "8080"))
    health = _health()
    print(f"newsdesk worker on :{bind}  health={json.dumps(health)}", flush=True)
    if not health["ok"]:
        # Loud, but not fatal: script and gate stages still work without ffmpeg,
        # and a worker that refuses to boot cannot tell anyone why.
        print("WARNING  this container cannot burn captions — see /health", flush=True)
    ThreadingHTTPServer(("0.0.0.0", bind), Handler).serve_forever()


if __name__ == "__main__":
    serve()
