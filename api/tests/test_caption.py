"""Caption generation and the checks that run before any model output is trusted.

Every test injects a fake chat_fn or builds a Caption by hand. Nothing here
reaches a provider, so the suite stays at $0 with no network.
"""
from __future__ import annotations

import json

import pytest
from fixtures import cs1_story

from newsdesk.caption import (
    HOOK_LIMIT,
    Caption,
    caption_problems,
    generate_captions,
    sources_for,
)
from newsdesk.claims import ScriptBlock
from newsdesk.decisions import Ledger
from newsdesk.state import RunState


def _caption(**over) -> Caption:
    base = dict(
        platform="youtube",
        variant=1,
        hook="Milwaukee has sixty-five thousand lead pipes and a 2037 deadline.",
        body="The city replaced roughly three thousand three hundred lines in 2025.",
        cta="Subscribe for more data-driven explainers.",
        hashtags=("#Infrastructure", "#PublicHealth", "#Shorts"),
        sources=("https://dailyreporter.com/2026/05/06/",),
    )
    base.update(over)
    return Caption(**base)


def test_a_clean_youtube_caption_has_no_problems():
    assert caption_problems(_caption()) == ()


def test_a_hook_past_the_platform_limit_is_a_problem():
    """The hook is the search snippet. Past the limit it truncates mid-sentence."""
    long_hook = "x" * (HOOK_LIMIT["youtube"] + 1)
    problems = caption_problems(_caption(hook=long_hook))
    assert any("hook" in p for p in problems)


def test_youtube_without_the_shorts_tag_is_a_problem():
    """The guide is explicit: #Shorts signals categorisation to the algorithm."""
    problems = caption_problems(_caption(hashtags=("#A", "#B", "#C")))
    assert any("#Shorts" in p for p in problems)


def test_linkedin_does_not_require_the_shorts_tag():
    c = _caption(platform="linkedin", hashtags=("#A", "#B", "#C"))
    assert caption_problems(c) == ()


@pytest.mark.parametrize("tags", [("#A", "#B"), ("#A", "#B", "#C", "#D", "#E", "#F")])
def test_hashtag_count_outside_three_to_five_is_a_problem(tags):
    """The guide treats hashtags as category labels, not reach boosters."""
    problems = caption_problems(_caption(platform="linkedin", hashtags=tags))
    assert any("hashtag" in p for p in problems)


def test_shouting_is_a_problem():
    """All-caps and exclamation runs break the sepia aesthetic the guide protects."""
    assert any("caps" in p for p in caption_problems(_caption(body="THIS IS URGENT")))
    assert any("exclamation" in p for p in caption_problems(_caption(body="Wow!!")))


def test_a_real_call_letter_acronym_is_not_shouting():
    """I2. WPBS, KUAC and KUOW are real station call letters from cs1's own
    facts (fixtures.py CS1_ENTRIES) — the stories this product exists to tell
    are ABOUT stations like these. A single acronym is a proper noun, not a
    shout; only a RUN of two or more all-caps words is shouting. Real data,
    not an invented acronym, because a made-up one proves less."""
    for acronym in ("WPBS", "KUAC", "KUOW", "RIAA"):
        problems = caption_problems(_caption(body=f"{acronym} felt the cut hardest."))
        assert not any("caps" in p for p in problems), (acronym, problems)


def test_a_run_of_all_caps_words_is_still_shouting():
    """A single acronym passes; a phrase in all caps does not. This is the
    line I2's fix has to hold — not just relaxing the check, but keeping it
    for the thing the guide actually forbids."""
    problems = caption_problems(_caption(body="STOP READING THE FINE PRINT"))
    assert any("caps" in p for p in problems)


def test_two_separate_exclamations_are_not_a_run():
    """M2. One "!" in the hook and one in the CTA is normal punctuation, not
    a run — the old `!.*!` with re.DOTALL spanned the whole caption and
    refused this. A real run ("!!", "!!!") must still be caught."""
    c = _caption(hook="Sixty-five thousand lead pipes!", body="Milwaukee is racing a 2037 deadline.",
                 cta="Subscribe for more!")
    assert not any("exclamation" in p for p in caption_problems(c))
    assert any("exclamation" in p for p in caption_problems(_caption(body="Wow!!!")))


def test_emoji_are_a_problem():
    assert any("emoji" in p for p in caption_problems(_caption(body="Big news 🚨")))


def test_sources_come_from_the_story_verbatim():
    """A model must never write a citation. These are copied, not composed.

    Asserted against the fixture's own values rather than a shape test — a
    check that only asks "does it look like a URL" would pass on an invented
    one, which is the single thing this function exists to prevent.
    """
    story = cs1_story()
    expected = tuple(
        dict.fromkeys(s.value for f in story.facts for s in f.sources)
    )
    assert sources_for(story) == expected
    assert len(expected) == len(set(expected)), "deduped, order preserved"


def test_text_property_builds_from_prose():
    """Caption.text must start with prose to ensure they stay in sync."""
    c = _caption()
    assert c.text.startswith(c.prose)


def _run() -> RunState:
    return RunState(run_id="cap-test", story="Who pays when public radio goes dark?")


def _payload(story, *, hook=None, source=None) -> str:
    """Six captions the model would return: two per platform.

    The hook is the claim's own `spoken` phrase plus a period, not an
    independent slice of the fact: `cs1_story`'s fact 0 is exactly 100
    characters, so `fact.text[:100]` (a wider slice than the 40-char claim)
    is the whole fact and leaves the tail ("$1.1B ... FY2026-27") on screen
    with nothing tracing it — `_problems` correctly rejects that as an
    unmapped number, which is real coverage working, not a flaky test. And
    without terminal punctuation, `validate_block` reads hook+body as one
    unbroken sentence and demands a claim for the body too. A period is what
    keeps this fixture the "clean caption" it is meant to be.
    """
    fact = story.facts[0]
    real_source = source or fact.sources[0].value
    spoken = fact.text[:40]
    out = []
    for platform in ("instagram", "linkedin", "youtube"):
        for variant in (1, 2):
            tags = ["#PublicMedia", "#Budget", "#Policy"]
            if platform == "youtube":
                tags.append("#Shorts")
            out.append({
                "platform": platform,
                "variant": variant,
                "hook": hook or f"{spoken}.",
                "body": "The cut lands on stations that carry the least advertising.",
                "cta": "What surprised you most? Let's discuss below.",
                "hashtags": tags,
                "sources": [real_source],
                "claims": [{"spoken": spoken, "fact_id": fact.id,
                            "evidence": fact.text}],
            })
    return json.dumps({"captions": out})


def _fake_chat(payload: str):
    def _chat(model, **kwargs):
        return type("R", (), {"text": payload})()
    return _chat


def test_six_captions_are_returned_two_per_platform():
    story = cs1_story()
    _, _, caps = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal",
        chat_fn=_fake_chat(_payload(story)),
    )
    assert len(caps) == 2 * len(__import__("newsdesk.caption", fromlist=["PLATFORMS"]).PLATFORMS)
    assert {c.platform for c in caps} == {"instagram", "linkedin", "youtube"}
    assert sorted(c.variant for c in caps if c.platform == "youtube") == [1, 2]


def test_a_clean_caption_records_a_pass_decision():
    story = cs1_story()
    _, ledger, _ = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal",
        chat_fn=_fake_chat(_payload(story)),
    )
    assert [d.verdict for d in ledger.decisions] == ["pass"]
    assert ledger.decisions[0].role == "caption"


def test_a_source_not_in_the_story_is_refused():
    """A model must never write a citation. This is that rule, enforced."""
    story = cs1_story()
    payload = _payload(story, source="https://invented.example/article")
    _, ledger, caps = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal",
        chat_fn=_fake_chat(payload),
    )
    assert caps == ()
    assert ledger.decisions[-1].verdict == "reject"
    assert "source" in ledger.decisions[-1].reason.lower()


def test_an_untraceable_claim_is_refused_not_warned():
    """Same rule as script.py: no caption beats a caption with a warning on it."""
    story = cs1_story()
    payload = json.loads(_payload(story))
    for c in payload["captions"]:
        c["claims"] = [{"spoken": "nine hundred trillion dollars",
                        "fact_id": story.facts[0].id, "evidence": "nothing"}]
    _, ledger, caps = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal",
        chat_fn=_fake_chat(json.dumps(payload)),
    )
    assert caps == ()
    assert ledger.decisions[-1].verdict == "reject"


def test_an_unreachable_model_records_a_reject_rather_than_passing():
    def _boom(model, **kwargs):
        raise RuntimeError("provider down")

    story = cs1_story()
    _, ledger, caps = generate_captions(
        _run(), Ledger(), story, (), through_line="tower-signal", chat_fn=_boom,
    )
    assert caps == ()
    assert ledger.decisions[-1].verdict == "reject"


def test_the_prompt_names_the_through_line_object():
    """The guide asks the caption to reference the object that rides through
    all six scenes. The kit knows what it is, so it is handed over, not guessed."""
    seen = {}

    def _spy(model, **kwargs):
        seen.update(kwargs)
        return type("R", (), {"text": _payload(cs1_story())})()

    generate_captions(_run(), Ledger(), cs1_story(), (),
                      through_line="tower-signal", chat_fn=_spy)
    assert "tower-signal" in seen["prompt"]


def test_an_unclosed_json_fence_still_parses():
    """A truncation-adjacent reply that OPENS a ```json fence and never closes
    it defeated the fence regex and refused good captions. The brace-slice
    rescue parses it; honestly truncated JSON still refuses."""
    import json as _json

    from newsdesk.caption import parse_captions

    payload = _json.dumps({"captions": [
        {"platform": p, "variant": v, "hook": "A hook.", "body": "A body.",
         "cta": "A cta.", "hashtags": ["#a"], "sources": ["https://x.org"],
         "text": "A hook. A body. A cta. #a",
         "claims": []}
        for p, v in (("instagram", 1), ("instagram", 2), ("linkedin", 1),
                     ("linkedin", 2), ("youtube", 1), ("youtube", 2))
    ]})
    caps = parse_captions("```json\n" + payload)
    assert len(caps) == 6
