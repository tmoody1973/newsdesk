"""ingest.py: propose facts from a pasted URL, and the wall that guards it
(PLAN.md §B4, task-1-brief).

Every test injects `fetch_fn`/`chat_fn`. Nothing here reaches a provider or
opens a socket — the same $0/no-network property `test_script.py` has.
"""

from __future__ import annotations

import json

import pytest

from newsdesk.ingest import (
    _MAX_ARTICLE_CHARS,
    IngestError,
    Proposal,
    fetch_article,
    propose_facts,
)

ARTICLE_HTML = """
<html>
<head><style>body { color: red; }</style></head>
<body>
<nav>Home | About</nav>
<header>Masthead</header>
<script>var leak = "should-not-appear-in-text";</script>
<article>
  <p>The   Federal Communications Commission voted 3-2 on Tuesday to approve
  the merger.</p>
  <p>Executives said the deal would close within ninety days.</p>
</article>
<footer>Copyright 2026 Wire Service</footer>
</body>
</html>
"""

REAL_QUOTE = (
    "The Federal Communications Commission voted 3-2 on Tuesday to approve "
    "the merger."
)
INVENTED_QUOTE = "The agency approved the merger unanimously."
URL = "https://example.org/story"


def _fetch_fn(url: str) -> str:
    assert url == URL
    return ARTICLE_HTML


def _fake_chat(proposals: list[dict]):
    """Stands in for chat(); returns a JSON array the way the real prompt asks
    for. Mirrors test_script.py's `_fake_chat` factory."""
    payload = json.dumps(proposals)

    class _Response:
        def __init__(self, t: str):
            self.text = t

    def _call(*args, **kwargs):
        return _Response(payload)

    return _call


# --- fetch_article ------------------------------------------------------


def test_fetch_article_strips_boilerplate_and_collapses_whitespace():
    text = fetch_article(URL, fetch_fn=_fetch_fn)
    assert "should-not-appear-in-text" not in text
    assert "color: red" not in text
    assert "Home | About" not in text
    assert "Masthead" not in text
    assert "Copyright" not in text
    assert "  " not in text  # runs of whitespace collapsed to one space
    assert REAL_QUOTE in text


def test_fetch_article_does_not_fuse_adjacent_elements_in_minified_html():
    """Pretty-printed HTML (ARTICLE_HTML above) has newlines between tags
    that mask this bug — a real article's markup doesn't. No whitespace
    between `<h1>...</h1><p>...</p>` or `<td>3</td><td>2</td>` must not
    read as the headline running into the lede, or two numerals reading as
    one number."""
    minified = (
        "<html><body><article>"
        "<h1>Regulators fine the bank</h1><p>The fine totaled 12 million.</p>"
        "<table><tr><td>3</td><td>2</td></tr></table>"
        "</article></body></html>"
    )
    text = fetch_article(URL, fetch_fn=lambda url: minified)
    assert "bankThe" not in text
    assert "32" not in text
    assert "3 2" in text


# --- propose_facts: the verbatim wall ------------------------------------


def test_propose_facts_drops_an_invented_quote_and_keeps_a_verbatim_one():
    chat_fn = _fake_chat([
        {"text": "The FCC approved the merger 3-2.", "quote": REAL_QUOTE},
        {"text": "The agency approved it unanimously.", "quote": INVENTED_QUOTE},
    ])
    result = propose_facts(URL, chat_fn=chat_fn, fetch_fn=_fetch_fn)

    assert len(result.proposals) == 1
    assert result.dropped == 1
    survivor = result.proposals[0]
    assert isinstance(survivor, Proposal)
    assert survivor.quote == REAL_QUOTE
    assert survivor.text == "The FCC approved the merger 3-2."


def test_propose_facts_url_on_every_survivor_is_the_input_url_verbatim():
    weird_url = "https://Example.org/Story?utm=1"

    def fetch(url: str) -> str:
        assert url == weird_url
        return ARTICLE_HTML

    chat_fn = _fake_chat([
        {"text": "fact one", "quote": REAL_QUOTE},
    ])
    result = propose_facts(weird_url, chat_fn=chat_fn, fetch_fn=fetch)
    assert len(result.proposals) == 1
    assert all(p.url == weird_url for p in result.proposals)


def test_propose_facts_all_invented_quotes_yields_no_proposals_and_a_count():
    chat_fn = _fake_chat([
        {"text": "a", "quote": INVENTED_QUOTE},
        {"text": "b", "quote": "Something else nobody wrote."},
    ])
    result = propose_facts(URL, chat_fn=chat_fn, fetch_fn=_fetch_fn)
    assert result.proposals == ()
    assert result.dropped == 2


def test_propose_facts_article_chars_reflects_the_fetched_text():
    chat_fn = _fake_chat([])
    result = propose_facts(URL, chat_fn=chat_fn, fetch_fn=_fetch_fn)
    assert result.article_chars == len(fetch_article(URL, fetch_fn=_fetch_fn))
    assert result.proposals == ()
    assert result.dropped == 0


def test_propose_facts_on_an_empty_or_unreadable_page_raises_ingest_error():
    def only_boilerplate(url: str) -> str:
        return "<html><body><script>var x = 1;</script></body></html>"

    with pytest.raises(IngestError):
        propose_facts(URL, chat_fn=_fake_chat([]), fetch_fn=only_boilerplate)


# --- the article is bounded before it's ever used -------------------------


def test_propose_facts_truncates_a_very_long_article_to_the_named_cap():
    """A page well inside the 5 MB download cap can still be far too much
    text for one chat() call — measured: 1.68M characters (~420k tokens)
    hard-fails claude-haiku's 200k context. `article_chars` reflects the
    capped length actually used, not the raw fetch."""
    huge_tail = "x" * 100_000
    huge_html = f"<html><body><article><p>{huge_tail}</p></article></body></html>"

    result = propose_facts(URL, chat_fn=_fake_chat([]), fetch_fn=lambda url: huge_html)
    assert result.article_chars == _MAX_ARTICLE_CHARS


def test_propose_facts_checks_quotes_against_the_truncated_text_not_the_full_page():
    """The prompt and the verbatim check must agree on what "the article"
    is. A quote that only exists past the truncation cutoff was never shown
    to the model either — it has to be dropped for the same reason an
    invented quote is, not pass because the checker read further than the
    prompt did."""
    tail_only_quote = "a fact stated only past the truncation cutoff point"
    padding = "filler word " * 20_000  # well past _MAX_ARTICLE_CHARS
    long_html = (
        f"<html><body><article><p>{REAL_QUOTE}</p>"
        f"<p>{padding}{tail_only_quote}</p></article></body></html>"
    )

    chat_fn = _fake_chat([{"text": "a late fact", "quote": tail_only_quote}])
    result = propose_facts(URL, chat_fn=chat_fn, fetch_fn=lambda url: long_html)

    assert result.proposals == ()
    assert result.dropped == 1
