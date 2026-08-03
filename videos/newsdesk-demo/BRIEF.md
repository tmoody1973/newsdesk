---
workflow: general-video
flow: companion
storyboard: no
message: "Newsdesk makes the video and refuses to say what it cannot prove"
destination: hackathon-submission
aspect: 1920x1080
language: en
length: 180s
angle: live-workflow-demo
---

## Intent

The Newsdesk hackathon submission demo: the complete workflow live on
production, using ProPublica's Machine Bias story, with the judging criteria
woven into an ElevenLabs voiceover. Documentary pace, opens on the problem
hook (the ProPublica article itself, scrolling slow). Real screen recording,
speed-ramped in the slow spans; the governance is the product. Hard cap 3:00
at 1920×1080/30fps. Directed by Tarik in docs/HANDOFF-demo-video.md — that
file is the shot list and the authority.

## Assets

- ../../demo/vo-final.md — the FINAL seven-segment VO script; recorded audio
  lives in the session scratchpad as seg1/2/2b/3/4/5/6.mp3 (measured 165.9s).
- scratchpad repro/demo-clips/s1-problem.webm — ProPublica scroll + front page.
- scratchpad repro/demo-clips/s2-wizard.webm — the whole wizard, one take
  (recording in progress; MARK epoch lines in repro/record-1-2.log are the
  edit points, each clip's t=0 is its first MARK).
- scratchpad repro/demo-clips/s3-board.webm, s4-approve.webm,
  s5-published.webm, s5b-film.webm — scenes 3–5b (recorder staged, runs after
  the run's blocks render).
- ../../demo/architecture-animated.html — self-drawing SVG architecture
  diagram (~19s), drop in as a NATIVE scene, not screen-recorded.
- ../../demo/end-bumper.html — stacked logo + tagline on cream (~5s), native
  scene; the VO's final words land on it.
- The published run MP4 (B2 public URL) — its OWN audio plays under the S5b
  span; the demo VO is silent there.

## Customizations

- Speed-ramps 6–10× on render/assembly waits, 1× on interactions, cut by MARK
  timestamps.
- S5b carries the published film's own audio (Playwright captures no audio;
  download the MP4 and lay its trimmed audio under that span).
- Master loudnorm I=-16, TP=-1.5, AAC 192k, faststart.

## Notes

- ≤3:00 is a hard submission limit; tighten footage, never the VO read.
- Every UI moment the VO references must be visible when spoken (dropped
  count, refusal, dollar figures, approver string, Copy click, two human
  receipts, architecture).
- Verify with eyes and ears at 1× before delivery (repo standing rule).
