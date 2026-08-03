# What is Newsdesk?

*Plain English, for anyone. No background needed.*

Three lengths below — a sentence, a paragraph, and the full explanation. Take
whichever fits the box you're filling in.

---

## One sentence

> Newsdesk turns sourced facts into short news videos, and seals a tamper-proof
> record inside every file showing how it was made — and what it refused to make.

---

## One paragraph

> Newsrooms want short vertical video, and AI can now produce it in minutes for
> about a dollar. Most newsrooms still won't touch it, because they can't publish
> something they can't account for. Newsdesk fixes the accountability, not the
> video: every fact must arrive with a source or the story won't load, a plain-
> language rulebook checks the plan before any money is spent, and a named human
> has to approve it before it can be assembled. The finished MP4 carries a record
> inside it listing every model that ran, what it cost, who approved it — and
> every request the system refused. Change one refusal afterwards and the record
> stops verifying.

---

## The full explanation

### Start with the problem

Picture a local news station. A reporter has just finished a story about the
city's water pipes — 65,000 old lead lines still in the ground, the city
replacing about 5,000 a year.

The station wants a 60-second vertical video for Instagram and TikTok, because
that's where a lot of people get their news now.

That video used to take an editor most of a day. Today, AI can make one in about
ten minutes for roughly a dollar.

So why isn't every newsroom doing it?

Because a newsroom's whole business is being believed. If one number in that
video is wrong, or if the AI invents footage that looks like a real news scene
but never happened, the station has published something false under its own name.
"The AI made it" is not a defence anyone accepts — not the audience, not a
regulator, not the person it got wrong about.

So most newsrooms leave the tools alone. The risk is worth more than the video.

**Newsdesk exists to make that trade-off go away.**

### What it actually does

You give it your facts — and every single one has to come with a source. Where
did you get this? A link, a document, a report. You can type them in, or paste a
link to a story you reported and let the system propose the facts from it, which
you then confirm one by one. Nothing it proposes counts until a person accepts it.

Then you pick a visual style, and the system writes a script, generates the
animation, records the narration, and cuts it together.

Four things make it different from a normal AI video tool.

#### 1. It won't accept rumours

If you type a fact without a source attached, the story doesn't load. Not a
warning you can click past — the system simply won't take it. Sources aren't a
nice-to-have you fill in later; they're the price of entry.

#### 2. It says no before it spends money

There's a rulebook — seven rules, written in ordinary English. No real people's
faces. No invented scenes dressed up to look like real news footage. No words on
screen, because AI still misspells things. And, since the app can now take a
pasted link and pull facts out of it: a link you paste is a story you're
reporting, not one you're quietly borrowing.

Before anything gets generated, the plan is checked against those rules. If
something breaks one, it stops there.

Here's the clever part: the piece of the system that says no is deliberately
built so it *can't* connect to any of the paid services. Not "we told it not to"
— it physically has no route. So refusing always costs exactly nothing.

That got tested for real. One afternoon the AI provider had an outage and the
fact-checker couldn't run. The system tried nine times, and nine times it refused
— because it couldn't confirm the facts checked out, and it treats *"I can't
verify this"* as *"then I won't publish it."* Total cost of those nine attempts:
zero.

#### 3. A person has to sign it, and the software won't sign for them

Nothing publishes itself. A human reads the script, watches the clips, and puts
their name on it. There is no other route to a finished video — not a setting, not
an admin override. The code has no path that skips the person.

Until someone signs, the record literally says *unreviewed*. The software will
not put a human's name on a document on their behalf.

And that review earns its keep. On the water-pipes story, the first script said
the city "replaced roughly 3,300 in 2025" and, seconds later, "passed 10,000
replacements that year." Both numbers were true. Both were properly sourced. One
was the count for that year, the other the running total since the programme
started — but read together they sounded like a contradiction.

No automatic checker could catch that, because nothing was actually wrong. It
needed an editor to notice it *sounded* wrong. That's exactly what the review
screen is for, and it worked — before a cent was spent on animation.

#### 4. The finished video carries its own paperwork

This is the heart of it.

Think of the sticker inside a car door, or the label on a food package. Every
video Newsdesk makes has a record baked into the file itself: which AI made each
piece, what it was told to make, what it cost, who approved it, and when.

And — this is the unusual bit — **it also records everything the system refused to
make, and why.**

Most tools log what they did. This one keeps a record of what it *wouldn't* do,
and then locks the two together. If someone later tried to quietly delete an
inconvenient refusal, the whole record stops checking out. It's a tamper-evident
seal. You can't quietly edit the history.

### Why anyone should care

The video is the thing you watch. The receipt is the thing that lets a newsroom
put its name on it.

Plenty of tools will make you a video. Newsdesk is built for the moment
afterwards, when somebody asks *"how did you make this, and how do I know you
didn't make it up?"* — and there's an answer that holds up when they check.

---

## If you want to see it rather than read about it

| | |
|---|---|
| The live app | [newsdesk-rosy.vercel.app](https://newsdesk-rosy.vercel.app) — open, no sign-in |
| A receipt | [one of the published videos](https://newsdesk-rosy.vercel.app/runs/who-pays-when-the-signal-goes-quiet/receipt) — every claim traced to the fact behind it |
| The rulebook | [the seven rules](https://newsdesk-rosy.vercel.app/policy), rendered from the same file the system enforces |
| What it refused | [the red team page](https://newsdesk-rosy.vercel.app/redteam) — attempts to break it, and what each refusal said |

Deeper reading, in increasing order of detail:
[`docs/JUDGING-CRITERIA.md`](JUDGING-CRITERIA.md) · [`README.md`](../README.md) ·
[`docs/HANDOFF.md`](HANDOFF.md)
