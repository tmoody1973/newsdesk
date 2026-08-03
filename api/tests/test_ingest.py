"""ingest.py: propose facts from a pasted URL, and the wall that guards it
(PLAN.md §B4, task-1-brief).

Every test injects `fetch_fn`/`chat_fn`. Nothing here reaches a provider or
opens a socket — the same $0/no-network property `test_script.py` has.
"""

from __future__ import annotations

import json

import pytest

from newsdesk.ingest import IngestError, Proposal, fetch_article, propose_facts

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
