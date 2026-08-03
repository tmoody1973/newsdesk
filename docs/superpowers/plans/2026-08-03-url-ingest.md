# URL ingest (PLAN.md §B4) — paste a link, confirm the facts

**Approved by Tarik 2026-08-02 19:54 CDT** ("backend + wizard field"). Design
source: `docs/PLAN.md` §B4, quoting Tarik 2026-07-28: *"the journalist can even
put a link to a story they did and you pull the facts to help craft the video."*

**The invariant that makes this strengthen Wall 1 rather than pierce it:**
extraction **proposes**, the journalist **confirms each fact**, and a proposal
whose quote is not literally present in the fetched article is **dropped, not
shown**. The pasted URL is the human's citation; the model never writes one.

## Global Constraints

- **`gate.py` must never import anything network-capable.** `tests/test_structure.py`
  walks its import graph. `ingest.py` IS network-capable by nature — nothing in
  `blockprompt.py`, `gate.py`, or their import graphs may import it.
- **The whole suite stays at $0 with no network.** Ingest tests inject
  `fetch_fn` and `chat_fn` fakes; no test fetches a URL or reaches a provider.
- **Immutability.** Frozen dataclasses, `dataclasses.replace`, never mutate.
- **A model must never write a citation.** The source URL on every proposed
  fact is the journalist's pasted URL, copied — never model output.
- **Refuse, never warn.** An unfetchable page, a non-verbatim quote, an SSRF
  violation: each refuses with a reason. Nothing ships as content-with-caveat.
- **No new dependencies.** stdlib + already-installed packages only
  (`genblaze-core` is already a dependency).
- **Commit messages:** conventional commits, no Co-Authored-By trailer.
- **Run tests with:** `cd api && uv run pytest tests/ -q`

---

### Task 1: `ingest.py` and `POST /ingest`

**Files:**
- Create: `api/newsdesk/ingest.py`
- Modify: `api/newsdesk/server.py` (add `POST /ingest`)
- Modify: `policy/policy.yaml` (new POL-7, provenance)
- Test: `api/tests/test_ingest.py` (new), `api/tests/test_server.py` (endpoint additions)

**Interfaces:**
- `ingest.fetch_article(url: str, *, fetch_fn=None) -> str` — fetched, readable
  text. Default fetch reuses genblaze's SSRF-pinned redirect-revalidating
  stream: `from genblaze_core.storage.transfer import _http_get_stream` (the
  same private-import genblaze's own `verify.py` uses — reuse, don't fork; note
  the private status in a comment). Cap the download (use genblaze's own
  `_DEFAULT_MAX_DOWNLOAD_BYTES` if importable, else 5 MB), `resp.release_conn()`
  in a `finally`. Readable text via a stdlib `html.parser.HTMLParser` subclass:
  drop `script`/`style`/`nav`/`header`/`footer` contents, collapse whitespace.
  No readability library — no new dependencies.
- `ingest.propose_facts(url: str, *, chat_fn=None, fetch_fn=None, max_proposals: int = 8) -> tuple[Proposal, ...]`
  - `Proposal` frozen dataclass: `text: str`, `quote: str`, `url: str`.
  - One `chat()` call (same `chat_fn` injection pattern as
    `script.generate_script`, `script.py:591`): prompt carries the article
    text and asks for JSON `[{text, quote}]` — `text` a candidate fact in
    plain declarative words, `quote` the **verbatim span** of the article it
    came from. The prompt must state the discipline: a quote that is not
    character-for-character from the article will be discarded.
  - **The verbatim check is the wall:** normalize both sides with
    `claims.normalize` (reuse it — do not write a second normalizer) and drop
    any proposal whose normalized quote is not a substring of the normalized
    article text. Dropped means dropped: not returned, count of drops
    available to the caller for the response.
  - `url` on every returned Proposal is the input `url`, verbatim.
  - On the recording question: `docs/PLAN.md` §B4 asks for `judged()`
    (role #4), but `judged()` binds to a RunState and ingest is pre-run —
    there is no run yet. Resolution: do NOT invent a fake run. Record the
    decision where it can live: the endpoint response carries
    `{proposals, dropped: <count>, article_chars: <len>}` so the refusal is
    visible, and `ingest.py`'s module docstring records why `judged()` does
    not apply pre-run. If a later task gives runs a pre-run ledger, this is
    the seam.
- `server.py` `do_POST` gains an `/ingest` branch, same shape as `/runs`:
  `_authorized()` → parse body `{url}` (400 bad JSON) → validate scheme is
  http/https and pass `genblaze_core._utils.check_ssrf(url)` (422 with the
  reason on failure — the SSRF refusal is a refusal, not a 500) → fetch +
  propose → `_send(200, {"proposals": [...], "dropped": n})`. An unfetchable
  or empty page → 422 with a message that names the fallback: *"could not
  read that page — paste the text of the story instead."* A `chat` failure →
  502 with the provider error. No thread, no slot — this is synchronous and
  cheap (one chat call).
- `policy/policy.yaml`: append POL-7 following the existing entry shape
  (`id`, `name`, `why`, `layers: [deterministic]`, `check`). Substance: facts
  may be proposed only from a URL the journalist pasted as **a story they
  reported**; the UI copy says so; every proposal carries a verbatim quote
  from that page or it is not shown. `updated:` header bumps to 2026-08-03.

**Tests (write first, watch each fail):**
- Fixture article HTML (inline constant or `fixtures.py` addition) + a
  `_fake_chat` (mirror `test_script.py:45-58`) returning a JSON payload of
  proposals. Assert: proposals whose quotes appear verbatim survive; a
  proposal with an invented quote is dropped; `dropped` counts it; every
  surviving proposal's `url` equals the input URL byte-for-byte.
- `fetch_article` strips script/style and collapses whitespace (fixture with
  a `<script>` that must not leak into the text).
- Endpoint: reuse `test_server.py`'s direct-handler-logic pattern — bad JSON
  400; missing/invalid url 422; scheme `file://` 422; (SSRF check itself is
  genblaze's, tested there — test that OUR path calls it and refuses, by
  injection or a private-IP literal `http://169.254.169.254/` which
  `check_ssrf` refuses without network).
- `tests/test_structure.py` must stay 12/12 — run it before committing.

---

### Task 2: the wizard URL field

**Files:**
- Modify: `web/components/FactsAndSources.tsx` (URL field + proposals UI)
- Modify: `web/lib/worker.ts` (add `ingestUrl()` on the existing `post()` helper)
- Modify: `web/lib/draft.ts` (only if a helper is genuinely needed — the
  `DraftFact` shape does NOT change; a proposal becomes
  `{id, text, sources: [{kind: "url", value: url}]}` via the existing
  immutable-update pattern)

**Before writing a line of UI, read** `docs/design/stamp-system-design-handoff.pdf`
and `stamp-system-design-handoff/project/Newsdesk Screens.dc.html` (the wizard
step 1 screen) per `CLAUDE.md` — the design bundle is the source of truth. The
new field must be indistinguishable in style from the existing story-title
field (`FactsAndSources.tssx:56-65` — `.field` > `label` + `.input`).

**Behavior:**
- A `.field` block **above the fact rows**: label + input, placeholder/copy
  **"Paste a link to a story you reported."** — that exact copy; the
  provenance wording is policy (POL-7), not flavor.
- A `.btn btn-secondary` "Pull facts" beside/below it: disabled unless the
  value passes `looksLikeUrl` (reuse from `draft.ts:44-46`). On click: call
  `POST /ingest` via a new `ingestUrl(url)` in `worker.ts` built on `post()`.
  Pending state on the button while in flight.
- Response proposals render as a list of confirmable rows (reuse `.card` /
  `.mono` / `.tag` idioms): each shows the proposed **text**, the verbatim
  **quote** underneath in `.mono`, and an "Add fact" button. Adding appends a
  `DraftFact` with the proposal text and one url source (the pasted URL) via
  the existing `onChange({...draft, facts: [...draft.facts, newFact]})`
  pattern. Nothing is ever auto-added.
- Show `dropped` when nonzero: one `.card-meta` line — "N proposals were
  dropped because their quotes could not be verified against the page." That
  sentence is the product argument; do not soften it.
- Errors surface the server's own message verbatim (the `WorkerError`
  pattern already does this) — including the 422 "paste the text of the
  story instead" fallback copy.
- Keep the proposal's `quote` in component state only — the `Draft`/payload
  shape is unchanged and `toPayload` (draft.ts:130-142) needs no edit.

**Verification (no web test harness exists):** run the dev server against a
stubbed worker (or the real local worker), exercise the flow, and
**screenshot the wizard** showing (a) the field matching the design system,
(b) proposals rendered, (c) a fact added to the rows. Attach the screenshot
path in the report. Visual fidelity to the mockup is a review criterion.

---

## Deliberate cuts, named

- **CUT: paste-the-text fallback input.** The 422 copy names the fallback;
  the actual textarea flow is not built in this pass. The journalist can
  still type facts by hand exactly as today — the field is additive.
- **CUT: "edited fact reverts to unsourced".** §B4's edit-tracking bullet.
  The confirmed fact keeps its URL source when edited (Wall 1 still requires
  a source; the verbatim discipline lives at proposal time, server-side).
  Full revert-tracking needs Draft-model surgery this pass does not touch.
