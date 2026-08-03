# Newsdesk - AI Video Explainer Tool for Journalists

## Inspiration

I work in radio. Newsrooms around me want short video badly, and most of them will not let AI anywhere near it. The reason is simple: if one number comes out wrong, "the AI wrote it" is not a correction anyone accepts. A newsroom's whole product is being believed.

So I stopped thinking about the generation problem and started thinking about the publishing problem. What would an AI video tool have to prove before an editor could sign it? That question became Newsdesk: it makes the video, and it refuses to say anything it cannot prove.

## What it does

A journalist pastes a link to a story they reported. Newsdesk reads the page and proposes facts, each one carrying the exact quote it came from. Anything it cannot verify against the page, character for character, gets dropped rather than shown. Nothing enters the story until the journalist adds it.

The journalist picks a brand kit, which is a visual style the newsroom owns all the way down to the prompt. The style tokens go to the image model word for word, every kit sits on a safety floor it cannot remove (no real-person likenesses, no fabricated news scenes, no readable text inside generated frames), and each kit carries a through-line object, one physical thing that appears in every scene so six clips read as one film. The demo story is ProPublica's Machine Bias investigation, about risk scores and criminal records. The through-line is a record.

Then the AI writes a sixty-second script, and a policy gate checks every line word for word against the confirmed facts. Drafts that fail are refused and redrafted. A refusal costs $0, and that is structural rather than a promise: the gate runs with no network access and no credentials, so it cannot reach anything that charges. Only after a script survives does money get spent, about $1.22 for six rendered clips and a measured narration take per block.

Nothing publishes without a named human. When my agent ran the demo, the record honestly says "Claude (agent) — UNREVIEWED, pending Tarik Moody", because an agent must not sign a human being's name. The published file carries a receipt inside it: every fact, every model, every refusal, every dollar, the approver's name. Change one entry afterward and the file fails its own verification. Even the social captions are checked the same way, every claim traced to an entered fact.

## How we built it

The web app is Next.js on Vercel. The render worker is Python on Fly.io with its own ffmpeg. There is no database: Backblaze B2 is the only data store, five buckets with one job each (assets, brand kits, runs, manifests, audit). Every page load reads B2 and every stage completion writes B2. The storage is the application.

Generation goes through Genblaze, which handles the provider pipeline, embeds the manifest in the output file, and verifies it later. GMI Cloud does stills, video, and the script model. ElevenLabs does narration, with LMNT as fallback, and each take is measured against a calibrated duration window. The editorial policy is a YAML file with numbered rules and a changelog; when testing killed one of our assumptions, the wrong value stayed in the file next to the right one, because a standards document that quietly edits itself is not one anybody should trust.

There are 489 tests and they all run offline, which is what makes "$0 spent on a refusal" checkable rather than a marketing line.

## Challenges we ran into

Machine Bias almost beat the script writer. The facts are number-dense, and the pacing rule (23 to 27 words per ten-second block) refused draft after draft, dozens of them across four filmed takes. The fix came from the product itself: the refusal banner names the failing block, the rule, and the remedy, and its remedy said to trim the two longest facts to one spoken sentence each. I did what my own error message told me to do, and the next take passed on the first round.

Mid-demo, the GMI account ran out of credits during the caption stage. The checker could not verify claims, so it blocked rather than assumed safe, and the run published with zero captions instead of unchecked ones. Annoying in the moment, and exactly the behavior the whole project argues for. After a top-up, the caption stage re-ran and landed six captions with every claim traced.

Rendering had its own surprise: the local renderer silently dropped video frames after any 60-second boundary a clip crossed. Finding that meant scanning the finished file frame by frame instead of trusting a green checkmark.

## Accomplishments that we're proud of

The refusal economics work. This project refused more drafts than it accepted, and the total bill for all of those refusals was zero dollars, because the gate physically cannot spend money. The one video that survived checking cost $1.22, and its receipt can prove where every cent and every sentence came from.

The approval record tells the truth even when it is awkward. A human-signed run says so. An agent-run demo says "UNREVIEWED, pending" instead of pretending.

And the demo itself is one real run on production, refusals on camera, not a sizzle reel.

## What we learned

The governance is the product and the video is the output. Once I accepted that, every hard decision got easier: refusals became features worth filming, the policy file grew a changelog instead of silent edits, and tests started asserting why a number sits in a band instead of just what the number is.

I also learned that an error message is product surface. The refusal banner that names the sentence, the rule, and the remedy ended up being the thing that saved the demo.

## What's next for Newsdesk - AI Video Explainer Tool for Journalists

Deeper brand kit customization. Two kits ship today (the house mixed-media collage and a paper-diorama documentary world). Next is a kit editor so a newsroom can build its own: palette, materials, typography, narrator voice, and a custom menu of through-line objects, all still sitting on the safety floor no kit is allowed to remove.

More customizable stories. Today every run is six ten-second blocks in one format. Next is choosing length, aspect ratio, and block structure per story, plus letting a journalist reorder blocks and pin a specific fact to a specific scene before the script is written, with the same word-for-word checking on whatever shape comes out.

Branded end cards. Every published video should close on the newsroom's own mark: logo, tagline, and a scannable pointer to the receipt, generated from the same brand kit as the rest of the film so the last frame is also the provenance frame.

Smaller items with real bugs behind them: the wizard fails to display a refusal on a brand-new run (found during the demo, documented, fix is small), and caption generation should retry on its own after a provider failure instead of waiting for an operator.

## Built with

Next.js, Vercel, Python, Fly.io, Backblaze B2, Genblaze, GMI Cloud, ElevenLabs, LMNT, ffmpeg
