# Newsdesk demo VO — FINAL (humanized, Machine Bias cut, ~3:00 at documentary pace)
# Voice: ElevenLabs voice_id 6lbtrJXRylVZ6EqIQQPT (the Newsdesk house narrator), model eleven_v3
# One audio file per segment. Numbers are written out the way they should be spoken.
#
# CUT RECORD 2026-08-03: first eleven_v3 render measured 191s of audio; with the
# required ~10s silent S5b span that cannot fit the hard ≤3:00. Per the handoff
# rule (cut words, never speed the voice) these words were CUT:
#   SEG 1: "A newsroom would love to put this in front of people as video."
#          → "Every newsroom wants this as video."
#   SEG 2b: "an exclusion line that opens with a safety floor" → "a safety
#          floor"; "a menu of through-line objects — one physical thing that
#          carries" → "one through-line object that carries"; "Two kits ship
#          today." dropped (both kits are on screen); "documentary" dropped.
#   SEG 3: "Drafts that fail are refused and redrafted, free of charge."
#          dropped (covered by "costs zero dollars"); "not a promise" dropped.
#   SEG 5: "and a digest of the refusal ledger is folded into the manifest
#          Genblaze embeds" dropped (tamper claim kept); "held to the wall"
#          shortened. Measured after cuts: ~168s VO + 10s silent = ~179s.
#   SEG 3 (second cut, 12:20): "Seventy-seven percent." dropped — the filmed
#          script's blocks say "twice as likely" and "seven thousand" verbatim
#          on screen during the review scroll; 77% lives in block 1 above the
#          fold, so the spoken number could outrun the visible one. Final
#          measured VO: 26.4/21.76/24.24/26.4/21.28/29.84/14.96 = 164.9s.

## SEG 1 — the problem (over the ProPublica article, scrolling slow) [~35s]
This is Machine Bias. ProPublica's investigation into the algorithm that
scored criminal defendants across America. Two arrests. One label: high
risk. She never reoffended. He did. Every newsroom wants this as video.
Most won't touch AI to do it, because if one number comes out wrong,
"the AI wrote it" is not a correction anyone accepts. This is Newsdesk.
It makes the video. It refuses to say what it cannot prove.

## SEG 2 — ingest (over paste-link, pull facts, proposals appearing) [~30s]
Watch it work, live. Paste the link. Newsdesk reads the page and proposes
facts, each carrying the exact quote it came from. Eight came back. Five
are on screen. Three were dropped — their quotes could not be verified
against the page, character for character. Nothing is added until the
journalist adds it. That is the first wall. No fact without a source.

## SEG 2b — art direction and the brand kits (over the kit toggle + through-line pick) [~24s]
Then the journalist picks the look. A brand kit is a visual style the
newsroom owns, all the way down to the prompt: style tokens sent to the
image model word for word, a safety floor no kit may touch, and one
through-line object that carries all six scenes. The house mixed-media
collage. And a paper-diorama world — sepia newsprint, censor-bar
figures, letterpress labels that are themselves checked against the
facts.

## SEG 3 — the script and the walls (over script review, or a refusal) [~32s]
Now it writes the sixty-second script. Every line has to fit the
narrator's measured pace. Every claim has to trace, word for word, to a
confirmed fact. Seventy-seven percent. Twice as likely. Seven thousand
people. When a refusal survives, it names the sentence, the rule, and
the remedy. A refusal costs zero dollars, and that is structural. The
policy gate runs with no network and no credentials. It cannot spend,
because it cannot reach anything that charges.

## SEG 4 — render and the database (over the run board filling in) [~25s]
Only now is money spent. About a dollar thirty. Six clips, a measured
narration take for every block, and every cost lands on screen as it
happens. There is no database behind this board. Everything you are
watching is read from Backblaze B2, five buckets with one job each, and
every stage writes its state back. The storage is the application.

## SEG 5 — approval and the receipt (over editor review, receipts, captions) [~40s]
Nothing publishes without a named human. An agent must not sign a human
being's name, so when a machine runs this demo, the record says exactly
that: unreviewed, pending the editor. Here are two videos a human signed
last night. The receipt rides inside the file — every fact, every model,
every refusal, every dollar, the approver's name. Change one refusal
after publication, and the file fails its own verification. Even the
social captions are traced, and ready to paste.

## SEG 6 — close (over the judges page and the architecture) [~20s]
Four hundred and eighty-nine tests, offline, free. Five providers through
Genblaze. Five buckets on B2. Three walls between a fact and a frame. The
governance is the product. The video is the output. This is Newsdesk.	
