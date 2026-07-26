# Newsdesk — Project Brief & PRD
**v1.0 · Jul 22, 2026 · Owner: Tarik Moody · Target: Backblaze Generative Media Hackathon (submit Aug 2)**

---

## Part 1 — Project Brief (one page)

**Logline:** Newsdesk turns verified facts into broadcast-style motion-graphics explainer videos — with an editorial policy gate that rejects unethical generations before they're made, a human approval gate before anything publishes, and a cryptographically verifiable provenance receipt embedded in every finished video.

**One-sentence narrative hook:** *Every newsroom is about to use generative media; this is what it looks like when it's held to journalism's standards.*

**Why now:** Generative video quality crossed the broadcast threshold in 2025–26 while newsroom trust in AI cratered. Newsrooms face a false choice: ban the tools or use them ungoverned. Nobody has shipped the third option — governed generation with receipts.

**Audience:**
- *Primary (product):* small/nonprofit/local newsrooms with no motion-graphics team and no AI policy infrastructure — the same under-resourced tier as the Callsign play.
- *Primary (hackathon):* Backblaze judges scoring real-world utility, production readiness, meaningful B2 use, meaningful Genblaze use.
- *Secondary (career):* newsroom AI-innovation hiring teams (CNN archetype: operationalize AI in editorial workflows while upholding accuracy, fairness, transparency).

**What it is:** A web app where a journalist enters verified facts + sources, art-directs the visual approach from a policy-approved menu (through-line object, style, per-block motifs, optional uploaded real assets), and receives a 60-second Vox-style collage explainer. Generation runs on Genblaze (Seedance 2.0 primary, Kling i2v fallback, ElevenLabs narration w/ LMNT fallback) inside an evaluate→reject→retry AgentLoop governed by a policy file. All assets, manifests, style kit, and audit tables persist to Backblaze B2; the master provenance manifest — including which human approved publication — is embedded in the MP4 itself and independently verifiable via `genblaze verify`.

**What it is not:** an autonomous news generator; a deepfake tool; a photorealism engine; a replacement for editorial judgment. Its most important feature is what it refuses to make.

**Positioning:** "AI on a leash," productized — deterministic walls between fact entry, policy enforcement, generation, and human approval. Open-source (MIT) after the hackathon, per the Public Radio Agents / Callsign phased playbook.

**Constraints:** solo builder; 12 days; Genblaze SDK is v0; hero demo must be cached; ~$25 generation budget (less if GMI credits land).

---

## Part 2 — PRD

### Problem Statement
Small and mid-size newsrooms cannot produce motion-graphics explainer video — the highest-engagement news format — because it requires a skill set they can't afford. Generative video makes production cheap but introduces unacceptable editorial risk: fabricated scenes, real-person likenesses, unverifiable claims, and no audit trail. Without a governance layer, every generated asset is a standards incident waiting to happen; the cost of not solving it is that these newsrooms either forfeit the format entirely or adopt ungoverned tools that damage reader trust.

### Goals
1. **A journalist with zero video skills produces a publishable 60s explainer from facts + sources in under 30 minutes** of active work (excluding render time).
2. **Zero policy-violating assets can reach the publish state** — violations are caught pre-generation (prompt gate) or post-generation (render evaluation) and auto-retried or surfaced.
3. **Every published video carries an embedded, independently verifiable provenance record** with per-block lineage and named human approver; `genblaze verify` passes on the shipped file.
4. **Every narration claim traces to an entered source** — the script validator refuses claims without a source mapping.
5. *(Hackathon goal)* Demonstrably deepest rubric coverage: agentic pipeline (AgentLoop), multi-provider fallback chains, ≥4 distinct meaningful B2 uses, provenance as core UX.

### Non-Goals
- **Photorealistic output of any kind** — collage/illustration styles only; photorealism is where news-media harm lives. Permanent, not just v1.
- **Fully automated publishing** — human approval is a load-bearing wall, not a v1 limitation.
- **Breaking-news speed** — this is an explainer desk (hours), not a live desk (seconds); live workflows have different verification economics.
- **Multi-tenant auth/roles** — single demo user for v1; Clerk stub at most. Team workflows are post-hackathon.
- **Custom style training / brand onboarding UI** — one house style (Mixed Media collage) shipped as a B2 brand kit; the kit format is designed for future styles but no UI to author them.
- **C2PA signing** — Genblaze manifests are tamper-evident in trusted storage; adversarial-grade signing is a documented Future Consideration, not v1.

### User Stories (priority order)
**Journalist (primary persona)**
- As a reporter at a text-only newsroom, I want to paste my verified facts and sources and get a broadcast-style explainer, so I can compete in a format my newsroom can't otherwise afford.
- As a reporter, I want to choose the through-line visual metaphor and per-block motifs from an approved menu, so the video reflects my editorial framing rather than a machine's guess.
- As a reporter, I want the tool to refuse my request when it violates policy — and tell me why in plain language — so I learn the boundary instead of discovering it in a correction.
- As a reporter, I want to upload a real photo from my reporting to appear as a collage element, so authentic material anchors the generated visuals — and is labeled as authentic in the receipt.
- As a reporter, I want to see per-block progress and retry status, so a provider failure reads as "retrying on backup model," not a dead app.

**Editor (approval persona)**
- As an editor, I want a review screen showing every block, its policy-check results, and its full generation lineage, so I can approve with the same confidence as a normal standards review.
- As an editor, I want my approval recorded in the provenance manifest by name and timestamp, so accountability is explicit.
- As an editor, I want to reject a single block with a note and trigger regeneration of only that block, so one bad clip doesn't restart a 6-block run.

**Reader / verifier (trust persona)**
- As a reader, I want to open a receipt from the published video showing how it was made and who approved it, so I can trust — or interrogate — what I'm watching.
- As a fact-checker, I want to run one command against the MP4 file itself and get a cryptographic pass/fail, so verification doesn't depend on trusting the publisher's website.

**Edge/error stories**
- As a journalist, when I enter a claim with no matching source, I want the validator to block scripting with that claim highlighted, so unverifiable statements never reach narration.
- As a journalist, when a provider is down mid-run, I want the fallback chain to complete my run on the backup model — and the manifest to show which blocks used which provider.

### Requirements

**P0 — cannot ship without (maps to build-plan Days 3–8)**
| # | Requirement | Acceptance criteria (abridged) |
|---|---|---|
| P0-1 | Facts-in schema: story facts, each with ≥1 source (URL/citation) | Given a fact without a source, when the journalist submits, then submission is blocked with that fact flagged |
| P0-2 | Script validator: 6-block script, every claim mapped to a fact ID | Given a generated script line containing an unmapped claim, then the line is rejected and rewritten or surfaced |
| P0-3 | Policy gate v1 (pre-generation, deterministic + LLM check): no real-person likeness, no fabricated news scenes, no photoreal styles, no unsourced on-prop text | Given a block prompt requesting a named public figure's face, then the prompt is rejected with a human-readable policy citation and **zero paid API calls occur** |
| P0-4 | Genblaze generation per block: Seedance 2.0 primary, `fallback_models=[kling-i2v]`, style key from B2 brand kit, explicit aspect ratio | Given the primary model returns MODEL_ERROR, then the block completes via fallback and the manifest records the actual provider |
| P0-5 | Narration: ElevenLabs (fixed voice_id) w/ LMNT fallback; take-duration verification 9.0–10.5s | Given a take of 12.8s, then the block is re-voiced (shortened or rate-adjusted) before assembly |
| P0-6 | Human approval gate | Given no editor approval, then assembly/publish is not reachable by any path |
| P0-7 | Assembly: ffmpeg stitch + subtitle burn; master manifest with per-block lineage + approver; `Mp4Handler.embed()`; `genblaze verify` passes | Checklist: final MP4 plays; embedded manifest extracts; verify returns true; receipt page renders from B2 |
| P0-8 | B2 persistence: assets bucket (HIERARCHICAL), brand-kit bucket, manifests, Parquet run tables | All four object classes present in B2 after one run |
| P0-9 | Judge-accessible URL running the full flow | A judge can execute Case Study CS-2 end-to-end without help |

| P1 — nice-to-have | |
|---|---|
| P1-1 | Post-render policy evaluation inside AgentLoop (vision-model check of the rendered clip; auto-retry with tightened prompt; parent-linked lineage) — **the criterion-crusher; cut first if behind** |
| P1-2 | Tier-2 asset upload: journalist's real photo composited as collage cutout, flagged `authentic: true` in manifest |
| P1-3 | EmbedPolicy dual receipts: redacted public receipt vs. full internal manifest |
| P1-4 | Per-block editor rejection → regenerate single block with note in lineage |

| P2 — future considerations (design for, don't build) | |
|---|---|
| P2-1 | Multi-style brand kits per newsroom; C2PA signing; multi-tenant roles; RSS/social publishing targets; `genblaze-higgsfield` adapter so the original skill runs natively; policy file marketplace for newsroom standards desks |

### Success Metrics
*Hackathon-frame (evaluate Aug 3–15):*
- Submission complete with all five Devpost artifacts; demo video ≤3 min with the rejection beat and live `verify`.
- **Leading:** a cold-start judge completes CS-2 end-to-end unaided; policy gate catches 100% of CS-4 red-team prompts with $0 spent on blocked prompts; full 6-block run completes ≤15 min wall-clock with ≤1 manual intervention.
- **Lagging:** prize outcome (target: Grand; floor: Feedback Prize); ≥1 Genblaze issue/PR acknowledged by maintainers; the demo video functions as a portfolio artifact in ≥1 job conversation.

*Product-frame (post-hackathon, 90 days):* 3 real newsrooms run a story through it; zero policy incidents in published output.

### Open Questions
- **[Engineering, blocking — Day 2]** Does GMI's Seedance endpoint accept an image/style reference through Genblaze's Step params? (Fallback confirmed: Kling i2v.)
- **[Engineering, blocking — Day 2]** `abatch_run()` concurrency ceiling on GMI — 6 parallel jobs or sequential?
- **[Engineering, non-blocking]** Vision-model choice for P1-1 render evaluation — Genblaze `chat()` with image input vs. a GMI multimodal model.
- **[Editorial/legal, non-blocking]** Policy file v1 line on depicting deceased public figures in archival-collage contexts (news-legitimate but likeness-adjacent). Default: prohibit in v1, document as open.
- **[Product, non-blocking]** Public receipt: how much prompt text to redact by default (EmbedPolicy setting).

### Timeline
Hard deadline **Aug 3, 5:00 PM EDT** (submit Aug 2 per build plan). Phasing = the day-by-day plan in `newsdesk-phase25-scouting-and-build-plan.md`; scope-cut ladder pre-named there. Dependency: GMI credits form (submitted Day 1); no other external dependencies.
