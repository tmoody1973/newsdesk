# What the Vox Explainer Prompt Pack changes here

Source: `docs/design/vox-explainer-prompt-pack.pdf` (Zubair Trabzada, AI
Workshop). Read the PDF, not just this file — this is the delta against what
Newsdesk currently does, not a replacement for it.

## Already landed

Prompt 08 ("Fix the pacing nobody else fixes") is the source of design spec
§6.6, and all six of its steps are implemented: silence stripped first,
narration 0.4s after the cut, clip length follows audio, uneven gaps, music as
an arc, subtitles ≤2 lines timed to the trimmed audio. That one is done.

So is "write for the ear", "never invent a number" (strengthened — every claim
carries a verbatim span), and "trim the silence off every take".

## NOT landed — and this is where the blandness comes from

### 1. The camera. This is the big one.

Prompt 03: *"every clip is a fake one-take. One continuous first-person flight
through the diorama, starting and ending in motion blur so the six clips cut
together as if it never stopped moving. Fly through doorways, under bridges,
between buildings. **Never a static shot.**"*

`scene.MOTION` currently says the exact opposite, on all six blocks:

> *"Elements settle into place with small paper shifts; a slow push in. No camera
> shake, no whip pans, no parallax."*

That constant was written to stop the collage swooping like a template. It
over-corrected into six static wides. The pack's answer is not "swoop" — it is
**continuous motion that cuts together**, with motion blur at both ends of every
clip so block 3 flows into block 4.

### 2. Three text elements, four words per title — a hard limit, not a ban

Prompt 01 STEP 5 and the rules page: *"a MAXIMUM of three text elements per scene
and a maximum of four words in any title, or the model will duplicate or garble
the words. This is the single most common failure and it is entirely avoidable."*

Newsdesk's POL-4 is stricter — no readable text at all — which is why the
"WHO PAYS?" prop in CS-1's art direction was never built. The pack says bounded
on-prop text works. POL-4 already admits a bounded on-prop question; the gate
should enforce **≤3 elements, ≤4 words** rather than zero.

### 3. Six labels, one per scene, the last one is the whole video's question

Prompt 03 STEP 3: *"Write six short labels, one per scene, maximum three words
each, that will be letterpress-printed on a prop inside the shot. The last one
should be the question or phrase the whole video is built around."*

Not one prop with text — **six**, escalating to the kicker. That is a per-block
field the script writer should produce alongside the narration.

### 4. The negative prompt the pack ships

> *"repeated text, doubled text, two lines of identical text, dark background,
> photorealistic, live action, human faces"*

Compare against `brand-kit/negative.txt`. The **repeated/doubled text** clauses
are the ones that stop the garbling failure and are worth having verbatim.

### 5. Verify frames before you assemble

*"Pull one frame out of each clip and actually look at it. Finding a garbled
title after the final render costs you the whole assembly step twice."*

This is MOO-429 (post-render vision check) and it is unbuilt. The pack treats it
as table stakes, not as a nice-to-have.

### 6. The calibration step

Prompt 05 STEP 2: generate one ~20-word test line, measure it, and derive the
speech rate and target word count that lands 9–10.5s **before** writing six
blocks. Newsdesk did this by hand across two sessions. It should be a step the
product runs once per voice.

## The four tests — use these on the STORY, not just the prompt

Prompt 04 STEP 1 names what makes a story explainable in sixty seconds:

1. one hard **NUMBER** that is genuinely surprising
2. there is a **TWIST** — the obvious interpretation is wrong
3. it can be shown with **OBJECTS** rather than talking heads
4. it **matters** to the audience's money, safety or work

*"Reject anything that fails one of the four, no matter how big the headline is."*

**This pairs directly with URL ingest (plan B4).** When a journalist pastes a
link, score the story against these four before anyone spends a cent, and say
which one it fails. "This story has no twist" is the most useful thing this
product could tell a reporter, and it costs nothing.

## Where the pack is wrong for this stack — keep the correction

*"The style key is the whole game. One reference image, attached to every clip."*

Measured false on GMI (MOO-415, MOO-424): no GMI video family exposes a
style-reference slot, and passing a style key as an image input made consistency
**worse** — two scenes off one key gave a blue ground and a tan one, while naming
the palette in text locked it. The pack was written for Higgsfield, where
`medias:[{role:"image"}]` exists. Naming the palette in text is the equivalent
here, and it works.
