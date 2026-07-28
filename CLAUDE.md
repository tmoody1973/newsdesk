# Newsdesk — instructions for agents

## Read these before you build. They are not optional.

This project has been burned once by an agent building from summaries while the
real material sat unread. **Inventory the repo and open the primary sources
before writing code in any area.**

| Building… | Read first, in full |
|---|---|
| **Any UI** | **`docs/design/stamp-system-design-handoff.pdf` — LOOK AT THIS FIRST.** It is the whole design on one sheet: four stamp treatments, The Desk, all three wizard steps, the Run Board, Editor Review, the Receipt chit, Brand Kit & Policy, and the 380px Run Board. Read it as an image before writing a line of UI. Then `stamp-system-design-handoff/project/Newsdesk Screens.dc.html` — a complete 426-line mockup of all six screens plus four stamp treatments. Its README opens *"CODING AGENTS: READ THIS FIRST"* and asks for pixel-perfect recreation. Follow its imports: `project/_ds/modernist-*/styles.css` is the design system with the real component classes and custom properties. **Do not re-derive a palette or layout from `newsdesk-ui-ux-spec.md`** — that is the summary; this is the source. |
| **Block prompts / visual craft** | `~/.claude/skills/vox-motion-graphics/references/vox-prompts.md` — the block-prompt template, the eight-device visual vocabulary, the motion vocabulary, and two worked examples. Its central instruction is that every block combines two or three devices **chosen to literally illustrate that block's narration line**. Also `references/diorama-doc.md`. |
| **Anything at all** | `docs/HANDOFF.md` (state, mandate, 30 dead assumptions), `docs/PLAN.md` (the full build plan), then the issue in Linear. |
| **Policy / the gate** | `policy/policy.yaml` is the live source. The mockup contains an older POL-1…POL-5 set; the YAML wins. |
| **Facts, stories, fixtures** | `newsdesk-case-studies.md` — CS-1…CS-5 with their art direction and motifs written out. These fixtures **are** the test suite. |

## Standing rules for this repo

- **No scope cuts without saying the word "cut" out loud** and naming the
  criterion being dropped. Never present a cut as prudence. See the mandate at
  the top of `docs/HANDOFF.md`.
- **Verify against real output.** View images at full size, listen to audio,
  screenshot the page. Several bugs here were invisible to tests and obvious in
  a screenshot.
- **`gate.py` must never import anything network-capable.** `test_structure.py`
  enforces it, and it is what makes "$0 spent on a refusal" structural.
- **Encode the convention, not the value.** Where a number was tuned by ear or
  by eye, the test asserts the named band it must sit in and says why.
- **Corrections stay in the record.** When testing kills an assumption, the wrong
  version stays next to the right one — see `policy.yaml` POL-2 `changelog` and
  `voice.json` `why_the_window_moved`.
