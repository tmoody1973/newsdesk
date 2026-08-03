"""URL ingest (PLAN.md §B4): paste a link, get proposed facts back.

*"the journalist can even put a link to a story they did and you pull the
facts to help craft the video."* — Tarik, 2026-07-28. This is the on-ramp:
paste a link instead of typing six facts and sources by hand.

**This strengthens Wall 1; it does not bypass it.** `propose_facts` never
returns a `Fact` — it returns a `Proposal`, which is inert until a journalist
confirms it in the wizard and it becomes a `Fact` with `Source.url(...)`
(that wiring is the wizard's job, not this module's). And a proposal only
survives if its `quote` is a verbatim, character-for-character span of the
fetched article — checked with `claims.normalize`, the exact discipline
`claims.py` already applies to narration. A quote the model invented is
dropped, not shown, not flagged: dropped.

**Why this is not a `judged()` role, even though PLAN.md §B4 numbers it
chat() role #4.** `judged()` (`decisions.py`) records a verdict against a
`RunState` — every call site has a run in flight to attach the ledger entry
to. Ingest runs *before* a run exists; there is no `RunState` to bind the
record to, and inventing one to satisfy `judged()`'s signature would fabricate
a run just to log a decision that happened outside of one. Resolution: don't
invent a fake run. The refusal is instead made visible in the one place that
does exist for it — the `/ingest` response carries `proposals`, `dropped`
(the count silently discarded, so the refusal isn't invisible) and
`article_chars` (so a caller can tell "nothing came back" from "there was
nothing to read"). If a later task gives runs a pre-run ledger, that is the
seam where this call becomes `judged()` too.

**SSRF.** Fetching an arbitrary journalist-pasted URL is a public SSRF
surface. `server.py` validates the scheme and calls
`genblaze_core._utils.check_ssrf` before this module is ever reached; the
default fetch below is *also* protected, for free, because
`genblaze_core.storage.transfer._http_get_stream` re-resolves and re-pins the
IP on every hop internally (redirects included). Both are private imports —
not a public genblaze contract — reused deliberately rather than forked,
the same way genblaze's own `providers/_ffmpeg_utils.py` reuses `check_ssrf`
for its own HTTP input path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Callable

from newsdesk.claims import normalize
from newsdesk.script import MODEL, chat

# ponytail: genblaze's own _DEFAULT_MAX_DOWNLOAD_BYTES is 5 GB — sized for
# video/image asset transfers, not a news article's HTML. Reusing it here
# would make the "cap the download" requirement a no-op for anything an
# article page could plausibly be, so this module keeps its own, much
# smaller cap instead. (Brief said "use genblaze's constant if importable,
# else 5 MB" — the importable constant turned out to be the wrong size for
# this job; discrepancy recorded in the task report.)
_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
_FETCH_TIMEOUT_S = 20.0
_CHAT_TIMEOUT_S = 60.0

# ponytail: past 40k characters it's not a news story anymore — it's a
# liveblog, a comment thread, or a scraped nav dump the extractor let
# through. The tail adds tokens to the chat() call, not facts. Untruncated,
# a fetched page well inside the 5 MB download cap can still blow a model's
# context window in one prompt (measured: 1.68M chars → ~420k tokens, a hard
# failure on claude-haiku's 200k window, surfaced only as an opaque 502).
# Truncated ONCE, here, before the text is used for BOTH the prompt and the
# verbatim check below — checking a quote against the untruncated article
# would pass quotes the model never actually saw.
_MAX_ARTICLE_CHARS = 40_000

_WS_RE = re.compile(r"\s+")
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class IngestError(ValueError):
    """The page could not be read — unfetchable, or nothing left after strip."""


@dataclass(frozen=True)
class Proposal:
    """A candidate fact, not yet confirmed. Inert until a journalist accepts it."""

    text: str
    quote: str
    url: str


@dataclass(frozen=True)
class ProposeResult:
    """What `propose_facts` returns: survivors, plus the refusal made visible.

    `dropped` and `article_chars` exist so the caller (`/ingest`) can answer
    "why did I get zero proposals?" without re-deriving it — an empty
    `proposals` tuple alone can't distinguish "the page was unreadable" from
    "the model proposed six things and all six were invented quotes".
    """

    proposals: tuple[Proposal, ...]
    dropped: int
    article_chars: int


class _TextExtractor(HTMLParser):
    """Strips markup to readable text. No readability heuristics, no new
    dependency — good enough for the single-page news-story shape this feeds,
    and script/style/nav/header/footer are exactly the boilerplate that would
    otherwise leak into what the model reads and what the verbatim check
    compares against.
    """

    _SKIP_TAGS = frozenset({"script", "style", "nav", "header", "footer"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        # A tag boundary is a word boundary. Without this, minified HTML
        # (real articles; the pretty-printed fixture hid this) collapses
        # adjacent elements into one token — `<td>3</td><td>2</td>` reads as
        # "32", and a headline butts straight into its lede. `_WS_RE`
        # collapses the extra spaces this adds everywhere else, so it's free.
        self._parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: Any) -> None:
        self._parts.append(" ")  # same fusion risk as a start/end pair

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        return _WS_RE.sub(" ", "".join(self._parts)).strip()


def _default_fetch(url: str) -> str:
    """Default `fetch_fn`: genblaze's SSRF-pinned, redirect-revalidating
    stream, capped and decoded. Private import — see module docstring.
    """
    from genblaze_core.storage.transfer import _http_get_stream

    resp = _http_get_stream(url, timeout=_FETCH_TIMEOUT_S)
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_DOWNLOAD_BYTES:
                raise IngestError("that page is too large to read")
            chunks.append(chunk)
    finally:
        resp.release_conn()
    return b"".join(chunks).decode("utf-8", errors="replace")


def fetch_article(url: str, *, fetch_fn: Callable[[str], str] | None = None) -> str:
    """Fetch `url` and return its readable text — script/style/nav/header/footer
    dropped, whitespace collapsed. `fetch_fn(url) -> raw html str` is
    injectable so this (and everything built on it) is testable at $0 with no
    network.
    """
    fetch = fetch_fn or _default_fetch
    raw_html = fetch(url)
    parser = _TextExtractor()
    parser.feed(raw_html)
    parser.close()
    return parser.text()


_PROPOSE_PROMPT = """You are helping a journalist pull candidate facts out of \
an article they reported, for a short video story.

ARTICLE TEXT:
{article}

Propose up to {max_proposals} candidate facts a video could cite from this \
article. Return ONLY a JSON array, no prose, no markdown fence:

[{{"text": "<the fact stated in plain declarative words>", "quote": "<the \
exact span of the article text above it came from>"}}, ...]

Discipline: "quote" MUST be copied character-for-character from the article \
text above — same punctuation, same capitalization, same spacing. A quote \
that is not found verbatim in the article will be discarded before a \
journalist ever sees it, and the fact it belongs to is discarded with it.
"""


def _parse_candidates(text: str) -> list[dict[str, Any]]:
    """Tolerant JSON extraction — same fence/brace tolerance as
    `script.parse_blocks`, sized down to a list instead of a `{"blocks": []}`
    dict. A reply that yields nothing parseable proposes nothing; that is not
    an error, it's zero candidates for the verbatim check to drop.
    """
    fenced = _FENCE_RE.search(text)
    candidate = fenced.group(1) if fenced else text
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("["), candidate.rfind("]")
        if start == -1 or end <= start:
            return []
        try:
            payload = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return []
    if isinstance(payload, dict):
        payload = payload.get("facts") or payload.get("proposals") or []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def propose_facts(
    url: str,
    *,
    chat_fn: Callable[..., Any] = chat,
    fetch_fn: Callable[[str], str] | None = None,
    max_proposals: int = 8,
) -> ProposeResult:
    """Fetch `url`, ask `chat_fn` to propose facts, and drop anything whose
    quote isn't verbatim in the fetched article.

    `url` on every surviving `Proposal` is `url`, byte-for-byte — a model
    never writes a citation, this function does, and it copies rather than
    invents.
    """
    # Truncated once, up front — the prompt below and the verbatim check
    # further down both read `article`, so both see the same (possibly
    # shortened) text. See `_MAX_ARTICLE_CHARS`.
    article = fetch_article(url, fetch_fn=fetch_fn)[:_MAX_ARTICLE_CHARS]
    if not article.strip():
        raise IngestError(
            "could not read that page — paste the text of the story instead."
        )

    prompt = _PROPOSE_PROMPT.format(article=article, max_proposals=max_proposals)
    response = chat_fn(
        MODEL, prompt=prompt, temperature=0.2, max_tokens=2000, timeout=_CHAT_TIMEOUT_S
    )
    raw = getattr(response, "text", "") or ""
    candidates = _parse_candidates(raw)[:max_proposals]

    normalized_article = normalize(article)
    proposals: list[Proposal] = []
    dropped = 0
    for item in candidates:
        text = str(item.get("text", "")).strip()
        quote = str(item.get("quote", "")).strip()
        if not text or not quote or normalize(quote) not in normalized_article:
            dropped += 1
            continue
        proposals.append(Proposal(text=text, quote=quote, url=url))

    return ProposeResult(
        proposals=tuple(proposals), dropped=dropped, article_chars=len(article)
    )
