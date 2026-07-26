# Newsdesk — UI/UX Spec (HeroUI Pro build)
**v1 · Screens, flows, tokens, and component mapping. Companion to the PRD; requirement IDs refer to it.**

---

## 1. Design direction — "The Paste-Up Room"

The app is the table where the explainer gets assembled, checked, and stamped — a production surface, not a dashboard. The metaphor is yours already: **bumwad**. Architectural trace paper, plan-check stamps, registration marks, the paste-up board. It connects your methodology, the collage output style, and the tool's governance story in one visual language — and it steers deliberately away from both generic SaaS-dashboard and the hairline-rule broadsheet cliché that "newsroom tool" invites.

**The one aesthetic risk (the signature): the stamp system.** Every consequential state change renders as a rubber stamp — slightly rotated, ink-textured, uppercase Anton: `APPROVED` (blue), `BLOCKED` (red), `RETRY 2` (gray), `VERIFIED` (blue, with hash suffix). Policy rejections don't appear as error toasts; they appear as a red stamp slammed onto the block card with the rule citation beneath in mono. This is the plan-check ritual from your architecture life applied to editorial review — and it makes the tool's most important feature (refusal) its most memorable visual moment. Everything else stays quiet so the stamps can be loud.

**Continuity with output:** Anton is already the burned-subtitle font in the videos. Using it for stamps and display means the tool and the media it produces are visibly the same product.

### Tokens
| Token | Value | Use |
|---|---|---|
| `pasteboard` | `#E8E6DF` | App surface — cool putty board, not warm cream |
| `ink` | `#1A1917` | Text, rules, chrome |
| `canary` | `#F2C744` | Bumwad trace — selection, active step, highlights, through-line accents |
| `stamp-red` | `#C8372D` | BLOCKED, destructive, policy citations |
| `approval-blue` | `#2B5DA8` | APPROVED, VERIFIED, links, provenance affordances |
| `graphite` | `#6B675F` | Secondary text, metadata, disabled |

Type: **Anton** (display: stamps, screen titles, big numbers — used with restraint), **Public Sans** (body/UI — a civic-information workhorse, on-theme for a public-interest tool), **IBM Plex Mono** (all provenance data: hashes, model IDs, timestamps, source IDs — machine truth always renders in mono). Radius: HeroUI `sm` globally (near-square, print-shop); full-round only on status chips. Motion: one orchestrated moment only — the stamp lands with a single 120ms scale-settle; respect `prefers-reduced-motion` by rendering it static. No skeleton shimmer; loading states are honest text ("Generating block 3 of 6 · Seedance 2.0").

HeroUI theme: extend `light` in `tailwind.config` — `background: pasteboard`, `primary: approval-blue`, `danger: stamp-red`, `warning: canary`, `foreground: ink`; `fontFamily` display/sans/mono per above. One theme; no dark mode in v1.

---

## 2. Information architecture & flow

```
The Desk (stories list)
 └─ New Story wizard ── 1 Facts & Sources → 2 Art Direction → 3 Script Review ──▶ Run Board (live)
                                                                                    └─▶ Editor Review (gate) ─▶ Published + Receipt
```
Left rail (HeroUI Pro sidebar shell, collapsed-icon style): Desk · Brand Kit · Policy · Audit. The wizard and Run Board are full-bleed working surfaces — no rail clutter while producing.

---

## 3. Screens

### 3.1 The Desk — story list
HeroUI Pro **application shell + Table**. Columns: Story · Status (Chip: Drafting / Generating / Awaiting approval / Published / Blocked) · Blocks done (Progress, 0–6) · Approver · Updated. Row click → contextual: drafts open the wizard, runs open the Run Board, published opens the Receipt.
**Empty state (first-run):** "Nothing on the board. Start with facts — the video comes later." → primary Button `Start a story`, secondary link `Load a case study` (seeds CS-1/CS-2 fixtures — this is how a judge cold-starts; PRD P0-9).

### 3.2 New Story wizard — 3 steps (HeroUI Pro multi-step form template)
Progress header: three steps with canary underline on the active step. Copy rule throughout: buttons say what happens — `Add fact`, `Check sources`, `Write script`, never "Submit."

**Step 1 · Facts & Sources (P0-1).** Repeating fact rows: Textarea (the fact) + source sub-rows (Input for URL/citation; CS-3 mode: dataset+row picker). A fact without a source shows an inline `UNSOURCED` chip in stamp-red and blocks Continue — the row error text: "Every fact needs a source before it can appear on screen." Right side: a live **Sources ledger** card (mono) assigning F1, F2… IDs.
```
┌ Facts ──────────────────────────┐ ┌ Sources ledger ┐
│ F1 [fact text……………………] │ │ F1 → npr.org    │
│    src: npr.org  [+ source]     │ │ F2 → cpb.org    │
│ F2 [fact text……………………] │ │ F3 — UNSOURCED  │
│    src: ⚠ UNSOURCED             │ └────────────────┘
└─ [Add fact]         [Continue] ─┘
```

**Step 2 · Art Direction (Tier-1 inputs).** Three curated pickers, all HeroUI **RadioGroup as visual cards** (no free text — the menu *is* the policy boundary):
- **Through-line object** — 6 illustrated cards (fuse, balloon, tower signal, dollar being cut, record, scale). One required; card border goes canary on select.
- **Motif per block** — compact 6-slot strip, each a Select (map / chart / ledger / cutout crowd / prop with text / archival frame). Defaults pre-filled from the through-line; journalists adjust, not compose.
- **Real asset upload (P1-2)** — HeroUI file-upload dropzone: "Add a photo from your reporting. It appears as a cutout and is labeled authentic in the receipt." Uploaded thumb gets a small `AUTHENTIC` chip in approval-blue.
- A quiet mono footnote, always visible: *"Requests outside this menu are checked against policy. Real people's likenesses and photoreal news scenes will be blocked."* (Sets expectation for Tier-3 refusals without a lecture.)

**Step 3 · Script Review (P0-2).** The 6 blocks as stacked cards: narration line (editable Textarea) + claim→fact chips beneath (`F1` `F4` in mono, approval-blue). An unmapped claim renders its chip as `?` in stamp-red and blocks Continue: "This line makes a claim that doesn't trace to a fact. Map it or cut it." Word-count and est. take-length (from the 9.0–10.5s rule) shown per block in graphite. Primary action: `Send to generation`.

### 3.3 Run Board — the paste-up table (the app's hero screen)
Full-bleed board: **six block cards in a filmstrip row** (9:16 aspect), each a HeroUI Card cycling states:
`QUEUED` (graphite chip) → `GENERATING · seedance-2.0` (Progress, honest label) → `POLICY CHECK` → thumbnail, or a **stamp**:
- `RETRY 2 → kling-i2v` (gray stamp; P0-4 fallback made visible — production readiness on screen)
- `BLOCKED` (red stamp + rule citation in mono: *"POL-1: real-person likeness"*; card offers `Revise prompt` — the CS-4/R5 teach-the-boundary path)

Below the strip: **Run log** (HeroUI Pro activity-feed pattern, mono, newest first) — every submission, rejection, retry, and voice-take duration check as one-line entries. This log is the demo's supporting actor; it's also literally the Parquet audit trail rendered.
Voice row under each block: take duration badge — `9.8s ✓` in blue, `12.4s → re-voicing` in graphite.
When all six are ready: single primary action `Send to editor` (assembly stays behind the approval gate; P0-6).

### 3.4 Editor Review — the gate (P0-6, P1-4)
Split view: left, the six blocks stacked with narration + policy results; right, a sticky **Approval panel**.
- Per block: `Approve` / `Reject with note` (rejection = Textarea in a Popover; triggers single-block regeneration, note preserved in lineage).
- Any block card → **Lineage drawer** (HeroUI Drawer): the v1→v2 chain — prompt, model, provider, params, timestamps, parent_run_id — all mono. This drawer *is* the Genblaze manifest, humanized.
- Approval panel: approver name (from session), checklist of the six blocks, then the commitment control — a Button styled as the blue stamp: **`STAMP: APPROVED`**, with confirm Modal: "Your name and this timestamp become part of the video's permanent record." Then assembly runs; a quiet Progress ("Stitching · burning subtitles · embedding manifest") ends in a `VERIFIED` stamp when `genblaze verify` passes (P0-7).

### 3.5 Receipt — the public nutrition label
Standalone shareable page (also linked from the player). Designed as a **chit**: narrow column, perforated top edge, mono-dominant.
Sections: What you're watching (title, duration, published date) · **Made by** (per-block table: model, provider, style key ref; `AUTHENTIC` rows for uploaded assets called out in blue) · **Checked against policy** (rules passed, count of rejections during production — refusals are disclosed, not hidden) · **Approved by** (name, timestamp) · **Verify it yourself** (the SHA-256, and the copyable command `genblaze verify story.mp4` in a code block).
EmbedPolicy split (P1-3): public chit shows redacted prompt summaries; an internal toggle (session-gated) reveals full prompts.

### 3.6 Brand Kit & Policy (read-mostly in v1)
Brand Kit: card grid of the B2 kit — style key image, motif references, voice (play sample), subtitle font. Policy: the YAML rendered as numbered rules with plain-language names (`POL-1 · No real-person likenesses`), each with a one-line "why" — the page doubles as the newsroom-standards artifact for the repo/demo.

---

## 4. States, voice, and floor
- **Errors direct, never apologize:** "Seedance didn't respond. Block 3 is retrying on Kling." / "Verification failed — this file doesn't match its manifest. Don't publish it."
- **Empty states invite:** Audit page pre-first-run: "No runs yet. Every generation, rejection, and approval will be recorded here."
- **Vocabulary is consistent end-to-end:** Facts, Sources, Blocks, Stamp, Receipt. The button `STAMP: APPROVED` yields toast `Approved — assembling`.
- **Quality floor (unannounced):** keyboard-focus visible on every control (HeroUI defaults kept), all stamp states carry text labels (never color-only — stamp-red/blue also differ by icon), mobile-responsive down to 380px (filmstrip becomes vertical), reduced-motion honored.

## 5. Build notes (Claude Code)
Next.js + HeroUI Pro shell template; pages in §3 order = build order (Desk and wizard Day 8 per plan; Run Board consumes the same run-state JSON the CLI already emits, so the frontend is a renderer, not logic). Stamps: one `<Stamp kind>` component — CSS transform rotate(-3±1°), SVG grain mask, Anton; used in exactly four kinds. Resist adding a fifth accent or any decoration to the pasteboard: the board stays quiet, the stamps do the talking.
