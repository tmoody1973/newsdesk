"""CS-1 as executable fixture (newsdesk-case-studies.md).

The case studies were written as acceptance tests, so they are transcribed here
rather than paraphrased. Fact text is verbatim from the table; narration is the
golden six-block script the generator is expected to reproduce in shape.
"""

from __future__ import annotations

from newsdesk.claims import Claim, ScriptBlock
from newsdesk.facts import Source, Story

CS1_ENTRIES = [
    (
        "July 2025 rescissions package eliminated $1.1B in previously approved CPB "
        "funding covering FY2026-27",
        [Source.url("https://www.npr.org/2025/08/01/cpb-rescission")],
    ),
    (
        "CPB - the conduit distributing federal funds to 1,500+ local public radio and "
        "TV stations since 1967 - announced it would wind down; board voted to "
        "dissolve, Jan 2026",
        [Source.url("https://www.npr.org/2026/01/06/cpb-dissolve")],
    ),
    (
        "CPB cut staff ~70% and began closing out grants after Oct 1 with no new funding",
        [Source.url("https://www.cpb.org/impact")],
    ),
    (
        "Station impacts: WPBS Watertown NY lost ~$1M (a third of its budget), 30% "
        "workforce reduction; KUAC Fairbanks lost $1.2M, cut overnight broadcasts; "
        "Basin PBS West Texas lost 48% of revenue",
        [Source.url("https://www.cpb.org/impact")],
    ),
    (
        "Rural and tribal stations hit hardest; Native Public Media's network of 57 "
        "radio + 4 TV stations at risk",
        [Source.url("https://theconversation.com/public-radio-rural")],
    ),
    (
        "Some metros saw donation surges post-cut (Nashville, Louisville, KUOW Seattle)",
        [Source.url("https://www.npr.org/2025/08/01/cpb-rescission")],
    ),
]


def cs1_story() -> Story:
    return Story.build("Who pays when public radio goes dark?", CS1_ENTRIES)


# The golden script. Every line is 23-27 words across 2-3 sentences (POL-5, as
# recalibrated against Marcus Louis on 2026-07-28), numbers spelled out, and
# every number phrase carried by a claim whose evidence is verbatim in its fact.
def cs1_blocks() -> tuple[ScriptBlock, ...]:
    return (
        ScriptBlock(
            n=1,
            role="cold open",
            narration=(
                "One point one billion dollars in public broadcasting money vanished "
                "in a single July vote. It had already been approved. Congress took "
                "it back."
            ),
            claims=(
                Claim(
                    spoken="One point one billion dollars",
                    fact_id="F1",
                    evidence="$1.1B",
                ),
            ),
        ),
        ScriptBlock(
            n=2,
            role="stakes",
            narration=(
                "The corporation that had routed federal money to more than fifteen "
                "hundred local stations since nineteen sixty-seven voted to dissolve "
                "itself. That pipeline is closed."
            ),
            claims=(
                Claim(spoken="fifteen hundred", fact_id="F2", evidence="1,500+"),
                Claim(spoken="nineteen sixty-seven", fact_id="F2", evidence="1967"),
            ),
        ),
        ScriptBlock(
            n=3,
            role="evidence",
            narration=(
                "Seventy percent of the corporation's staff was gone within months. "
                "Grants were closed out. Nothing new was ever funded behind them, and "
                "no replacement arrived."
            ),
            claims=(Claim(spoken="Seventy percent", fact_id="F3", evidence="~70%"),),
        ),
        ScriptBlock(
            n=4,
            role="evidence",
            narration=(
                "Watertown lost a third of its budget. Fairbanks lost one point two "
                "million dollars and cut its overnight broadcasts. West Texas lost "
                "forty-eight percent of revenue."
            ),
            claims=(
                Claim(spoken="a third", fact_id="F4", evidence="a third of its budget"),
                Claim(
                    spoken="one point two million dollars", fact_id="F4", evidence="$1.2M"
                ),
                Claim(spoken="forty-eight percent", fact_id="F4", evidence="48% of revenue"),
            ),
        ),
        ScriptBlock(
            n=5,
            role="turn",
            narration=(
                "Rural and tribal stations were hit hardest, with fifty-seven tribal "
                "radio stations at risk. Then Nashville, Louisville and Seattle saw "
                "donations surge instead."
            ),
            claims=(
                Claim(spoken="fifty-seven", fact_id="F5", evidence="57 radio"),
                Claim(spoken="donations surge", fact_id="F6", evidence="donation surges"),
            ),
        ),
        ScriptBlock(
            n=6,
            role="kicker",
            narration=(
                "One point one billion dollars left the system. What came back arrived "
                "in pieces, from listeners, unevenly, and only in the places that could "
                "afford it."
            ),
            claims=(
                Claim(
                    spoken="One point one billion dollars",
                    fact_id="F1",
                    evidence="$1.1B",
                ),
            ),
        ),
    )
