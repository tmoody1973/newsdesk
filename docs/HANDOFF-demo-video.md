# Handoff — the submission demo video

**Written** 2026-08-03 ~06:20 CDT · **Hard deadline: TODAY, Aug 3, 5:00 PM EDT**
**Mission:** one MP4, ≤3:00, 1920×1080 — the complete Newsdesk workflow live on
production, using ProPublica's **Machine Bias** story, with the judging criteria
woven into an ElevenLabs voiceover. Tarik directed: real screen recording,
speed-ramp the slow parts, **open on the problem hook** (the ProPublica article
itself, scrolling slow).

## ▶ START HERE — what is already done

- **The VO script is FINAL and humanized:** `demo/vo-final.md`. Six segments,
  ~2:45 total, numbers written out for speech. Do not rewrite it; record it.
- **The animated architecture diagram is BUILT and verified:**
  `demo/architecture-animated.html` — self-drawing SVG in the site's ink,
  ~15s build + pulse. **The end bumper is BUILT and verified:**
  `demo/end-bumper.html` — stacked logo + tagline on cream.
- **Scenes 1–2 recorder is ready:** `demo/record-scenes-1-2.mjs` (Playwright,
  records 1920×1080 webm). Scene 1 = ProPublica article scrolling + front page.
  Scene 2 = the whole wizard: title → paste link → pull facts → add 5 →
  Check sources → kit toggle shown (diorama hovered/clicked, then **house**
  chosen; through-line **Record** — the pun is intended, it's a story about
  records) → Write script (auto-retries up to 4 rounds, films any refusal for
  6s — a refusal on camera is a WANTED beat, the VO narrates it) → Script
  Review scroll → Send to generation.
- **Ingest pre-verified on prod** (do NOT re-verify, it spends): the Machine
  Bias URL returns **5 proposals, 3 dropped** in ~11s. The VO's "eight came
  back, five are on screen, three were dropped" matches this. If a fresh pull
  returns different counts on camera, FIX THE VO NUMBERS to match the footage
  — the numbers must be true of the take used.
- **Voice:** ElevenLabs `voice_id 6lbtrJXRylVZ6EqIQQPT` (the house narrator,
  Marcus Louis), `model_id "eleven_v3"`. `ELEVENLABS_API_KEY` is in `api/.env`.

## The run this demo creates

Title typed by the recorder: **"The algorithm that labeled her high risk"** →
run id `the-algorithm-that-labeled-her-high-risk`. House kit. ~$1.30.
GMI balance is roughly **$8** — one demo run plus one spare. Do not burn a
second run unless a first-take defect forces it.

**Do not `fly deploy` or `vercel --prod` anything while the run is in flight.**
Measured last night: assembly normally publishes in ~2m12s, but a run started
seconds after a deploy took 14 minutes on a cold machine.

## Step-by-step for this session

1. **Record scenes 1–2** (spends: ingest pennies + script $0 + blocks $0.94 when
   Send fires at the end):
   ```bash
   SP=<your scratchpad>/repro && mkdir -p "$SP" && cd "$SP" && npm init -y && npm i playwright
   npx playwright install chromium   # only if launch complains
   cp /Users/tarikmoody/Documents/Projects/newsdesk/demo/record-scenes-1-2.mjs .
   CODE=$(grep "^NEWSDESK_ACCESS_CODE" /Users/tarikmoody/Documents/Projects/newsdesk/api/.env | cut -d= -f2- | tr -d '"') node record-scenes-1-2.mjs
   ```
   Clips land in `demo-clips/s1-problem.webm`, `s2-wizard.webm`. The script
   prints `MARK <epoch-ms> <label>` lines — SAVE THEM; they are your edit
   points (each clip's t=0 is its first MARK).
   A previous half-run may already exist under run id
   `who-checks-the-school-bus-safety-records` — ignore it, wrong story.
2. **While blocks render (~5 min), generate the VO** — one MP3 per segment:
   ```bash
   KEY=$(grep "^ELEVENLABS_API_KEY" api/.env | cut -d= -f2- | tr -d '"')
   curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-speech/6lbtrJXRylVZ6EqIQQPT" \
     -H "xi-api-key: $KEY" -H "Content-Type: application/json" \
     -d '{"text": "<SEGMENT TEXT>", "model_id": "eleven_v3"}' -o seg1.mp3
   ```
   Strip the `## SEG` headers and bracketed stage directions — send prose only.
   **Listen to (or at minimum ffprobe-duration) every segment.** Target
   durations are in `vo-final.md`; eleven_v3 runs ≈150 wpm. If a segment runs
   long, cut VO words — never speed up the voice.
3. **Record scenes 3–6** (write a second small Playwright script; same
   viewport/recordVideo pattern as scenes 1–2):
   - **S3 run board live:** goto `/runs/the-algorithm-that-labeled-her-high-risk`
     while blocks render. Film ~60–90s of the board polling: the breathing
     live dot, "rendering pictures..." chip, cards filling. This footage gets
     an 6–10× speed-ramp in the cut.
   - **S4 approve:** when 6/6 ready, the board shows **Send to editor** →
     Editor Review. Approve each block, then type the approver EXACTLY:
     `Claude (agent) — UNREVIEWED, pending Tarik Moody`
     plus the access code. This string is the documented convention (see
     README "Status" + JUDGING-CRITERIA §1) — an agent must not sign a
     human's name; the VO narrates this as a feature. Film the click and the
     AWAITING→assembly moment. Assembly ≈2 min — film the working chip, ramp it.
   - **S5 published, log, captions, receipt — Tarik's explicit beats, all
     required:** (a) the published board with its stamp; (b) **scroll the RUN
     LOG deliberately** (~8s — the audit trail on screen while the VO talks
     refusals); (c) scroll to **Social captions** and click one **Copy**
     (films "Copied ✓"); (d) **the receipt page**
     (`/runs/<id>/receipt`) — a slow 12s scroll, its own beat; (e) 8s each
     on the two HUMAN-approved runs from last night —
     `/runs/why-one-in-four-babies-in-this-karachi` and
     `/runs/why-did-openai-s-and-anthropic-s-ai`.
   - **S5b — THE FINAL VIDEO PLAYS INSIDE THE DEMO (required):** open the
     published MP4's public B2 URL directly in the recorder browser
     (`https://s3.us-east-005.backblazeb2.com/newsdesk-assets/<run-id>/<run-id>.mp4`)
     and let it play 10–12 seconds. **Playwright screen recording captures NO
     AUDIO** — so in the edit, download that same MP4, trim the same span,
     and lay ITS OWN audio under this segment. The demo VO goes silent here:
     the made thing speaks for itself. This is the money shot; do not cut it.
   - **S6 the animated architecture:** open
     `file://.../demo/architecture-animated.html` in the recorder at
     1920×1080 and film ~19s from load — the diagram draws itself in
     story order and the red tamper line pulses at the end. Verified working;
     the timing map is the .t1–.t10 delays in the file. SEG 6 of the VO reads
     over this.
   - **S7 end bumper (required):** film
     `file://.../demo/end-bumper.html` for ~5s — the stacked Newsdesk mark
     lands, then the tagline. The VO's final words ("This is Newsdesk.")
     land ON the bumper. Cut to black.
4. **Assemble** (use `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg` — PATH ffmpeg
   has no drawtext and may lack filters):
   - Normalize every clip: `-vf "scale=1920:1080:flags=lanczos,fps=30" -r 30`.
   - Speed-ramps: pick the boring spans by MARK timestamps and
     `-vf "setpts=PTS/8"` them (render wait, retry waits); keep interactions
     at 1×. A simple pattern: cut each source clip into segments with
     `-ss/-t`, ramp the slow segments, then concat (concat demuxer, all
     re-encoded to the same codec first: `-c:v libx264 -crf 18 -preset slow
     -pix_fmt yuv420p`).
   - Lay VO segments at the scene boundaries (audio concat with `adelay` or a
     silence-padded concat list); duck nothing (clips are silent screen
     recordings).
   - Master: `loudnorm=I=-16:TP=-1.5`, AAC 192k, faststart.
   - **Length ≤3:00.** If over, tighten scene footage, not the VO read.
5. **VERIFY WITH EYES AND EARS** (the repo's standing rule): watch the full
   cut at 1×, listen to the whole VO, check every UI moment the VO references
   is actually visible when spoken (dropped-count, refusal text, $ figures,
   approver string, Copy click, the two human receipts, the architecture).
6. **Deliver:** `SendUserFile` the MP4 to Tarik (display: attach). Optionally
   also upload to the public assets bucket for a shareable URL:
   `cd api && uv run python - <<'EOF'` … `backend(BUCKETS["assets"]).put("demo/newsdesk-demo.mp4", open(path,"rb").read())` … match `config.py`'s API.

## Hazards learned the hard way (do not relearn)

- **The Playwright MCP tools attach to Tarik's real Chrome.** NEVER use
  `mcp__playwright__*` for this work — scratchpad-installed Playwright via
  `node` only, which launches its own isolated chromium.
- The wizard's draft is page-memory: a refresh or Back loses proposals; the
  recorder never reloads mid-wizard for this reason. Don't "fix" that.
- Script convergence: budget is 8 attempts/round; the recorder retries 4
  rounds. Machine Bias facts are number-dense; a filmed refusal is a feature,
  but if all 4 rounds fail, trim the two longest facts to one spoken sentence
  each (the refusal itself names which) and re-run scene 2 from the wizard —
  the run resumes by title.
- `running: []` flicker on `/health` = two Fly machines, per-machine memory.
  Not an outage.
- Access code lives in `api/.env` as `NEWSDESK_ACCESS_CODE`; needed for pull,
  Write script, and approval.
- **Total spend authority for this mission: ≤$3.** Anything more, stop and ask.

## Context that explains "why" (read if a decision comes up)

- `docs/JUDGING-CRITERIA.md` — the claims the VO makes; every one must stay
  true of what's on screen.
- `demo/vo-final.md` — the words. Humanized already; edit only to match
  filmed reality (counts, refusal wording).
- The VO's SEG-5 promise "two videos a human signed last night" refers to the
  Karachi and AI-hacking runs — both `approval.approver` = Tarik. True as of
  06:00; don't re-verify by spending.
