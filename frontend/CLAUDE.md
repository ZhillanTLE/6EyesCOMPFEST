# Windfall

B2B abandoned-cart recovery for online travel agencies. A three-agent Gemini
pipeline (Classifier → Searcher → Notification Curator) reads a traveler's
booking history, decides what action recovers the cart, drafts the
notification, and sends it on analyst approval.

**Thesis:** rebuild the cart to fit the traveler instead of discounting it —
and deliberately send no discount to travelers whom price isn't blocking.
Restraint is the differentiator, not a fallback.

Competition entry (COMPFEST 18 AIC, penyisihan). Stack: **Flask + Next.js
(App Router) + plain CSS**, served via `docker compose`.

> An earlier revision of this file said "React/Vite". That was a recommendation
> made before the repo was inspected, not a constraint derived from the rules or
> the design bundle — and the repo already ships Next.js 16 with a
> Next-specific `AGENTS.md`. The FE rule prohibits dashboards, complex auth and
> history pages, not a framework, so Next.js violates nothing.
>
> **Boundary that must hold:** the console is a *client that calls Flask*. Do
> not let Next's affordances pull the backend across — no Route Handlers under
> `app/api/**` serving business logic, no Server Actions, no data fetching in
> Server Components. The single Flask endpoint stays the only backend. The one
> permitted use of Next server config is the `rewrites()` proxy in
> `next.config.ts`, which forwards `/api/recovery/*` to Flask so the browser
> stays same-origin.
>
> `docker compose up` from clean is the hard requirement, not the framework.

---

## Authority order

1. `docs/windfall-paper.md` — the specification. Wins over everything.
   Transcribed from the submitted PDF, with an Errata table at the end listing
   the eleven defects corrected in the markdown but still present in the PDF.
   The PDF has not been regenerated; the markdown is the working spec.
2. This file — resolved decisions that post-date the paper. Wins over the paper
   where they conflict (see Paper errata).
3. `frontend/design-system/` — the **vendored** design system (tokens,
   `styles.css`, brand and agent assets), copied verbatim from the handoff
   bundle and tracked in git. Visual reference only; its logic is stale (see
   Known stale spec).

   Vendored rather than referenced because a judge cloning this repo must be
   able to `docker compose up` without a directory that exists on one machine,
   and because a hand-transcribed copy of the tokens is an undocumented fork
   with no way to detect drift. The raw bundle stays gitignored — the vendored
   copy supersedes it.

---

## Competition scope — verbatim rules (penyisihan)

**FE / Antarmuka:** "UI wajib hanya berfokus pada alur interaksi inti, yaitu
menerima input tunggal dari pengguna dan menampilkan output dari AI. Peserta
tidak perlu membangun fitur pelengkap seperti dashboard analitik tingkat
lanjut, sistem otentikasi yang kompleks, atau halaman riwayat penggunaan."

**BE & Integrasi:** "Arsitektur backend wajib hanya sampai pada pemrosesan
interaksi sinkron. Peserta tidak perlu mengimplementasikan background jobs,
pipeline pencatatan data otomatis (automated data logging), atau infrastruktur
database terdistribusi. Fokuskan agar API/sistem lokal dapat dijalankan sesuai
panduan di README.md menggunakan docker compose."

**Model AI & Algoritma:** "Implementasi AI wajib hanya berfokus pada
fungsionalitas inferensi utama (core inference) dengan parameter yang bersifat
statis pada saat demonstrasi berjalan. Peserta tidak diminta untuk menyertakan
sistem pembaruan otomatis (auto-tuning), skrip pengujian massal (bulk testing
scripts), atau mekanisme loop umpan balik otomatis pada repository tahap
penyisihan ini."

These are hard limits, not preferences. If a task seems to require crossing
one, **stop and ask** — do not implement a "small" version of it.

### Pre-commit scope check

Before every commit, verify against the verbatim rules above:

- Does this add a scheduler, worker, queue, or anything running outside the
  request cycle? → **violates BE**
- Does it write logs or persist run history automatically? → **violates BE**
- Does it add a second DB, cache layer, or external store? → **violates BE**
- Does it add auth, a dashboard, a history page, or a second user input before
  the AI runs? → **violates FE**
- Does anything tune, learn, or change parameters at runtime? → **violates AI**
- Did I add a script that runs many carts in bulk? → **violates AI**

If any answer is yes, stop and report before committing.

### Known near-misses

- **Fixture capture** must be a deliberate manual step. Persisting fixture
  outputs back to disk as a side effect of a live run is automated logging.
- **Retry with backoff** around Duffel/Gemini is fine (still synchronous).
  "Queue it and try later" is a background job.
- **SQLite is allowed** (local file, not distributed) for *reading* seed data
  and threshold config only. The moment it records what happened, it is
  logging.
- **No `test_all_travelers.py`** or any loop over the seed set. Test one cart
  at a time.
- `.env` must be gitignored. A public judged repo with a live Duffel key is a
  worse problem than any scope violation.

---

## Decision logic

Two independent signals. A price intervention requires **both**:

```
c_i  = campaignShare       — share of past spend on discounted products
                              (price-sensitivity proxy)
g_i  = (p_0 - s_i) / s_i    — budget gap: cart price vs. usual spend

D_i = rebuild ladder        if c_i >= c* AND g_i > 0
      reminder, no discount  otherwise
```

Campaign share alone must **not** trigger a discount. High share with a cart
that already fits → still reminder. This is the whole thesis; do not simplify
it back to a single axis.

### Rebuild ladder

Ordered attempts, stop at the first that clears the tier threshold
(`k* = min{k : δ_k >= τ(T_i)}`), so the result stays closest to the original:

| # | Attempt | Changes | Status |
|---|---------|---------|--------|
| 01 | Re-price same cart | Nothing; re-query price | Implemented |
| 02 | Lateral | Same star, same dates, comparable property | Implemented |
| 03 | Tier-down | Hotel star −1; destination and dates fixed | Implemented |
| 04 | Date shift | — | Roadmap (§5.3) |
| 05 | Combination | — | Roadmap (§5.3) |
| — | None qualify | Alternative destination, or reminder | Implemented |

**Lateral is hotel-only.** Flight stays fixed — swapping it invalidates the
Duffel Hold Order, and hotel substitution is what keeps the swap margin-neutral.
Same-cabin flight swap is §5.3.

Lateral surfaces **only if** the saving clears τ. "Found something, not worth
showing" must remain a reachable outcome or restraint stops being real.

### Four outcomes

`rebuild` · `lateral` · `reminder` · `alternative`

**Never name the no-discount outcome `hold`.** It collides with Hold Order, the
airline price-freeze. Use `reminder`.

### Cold start

`campaignShare` is **null** (never fabricated) when there's no history. The
ladder still runs on the cart-derived proxy tier (flight class + hotel star),
because rebuild costs no margin. No margin-costing action is permitted.
Outcome may be lateral, tier-down, alternative, or reminder.

---

## Frozen constants

```
Tier percentile cutpoints:  <=30 Value · 31-80 Comfort · >80 Premium
Thresholds τ:               Value 0.05 · Comfort 0.10 · Premium 0.15
Campaign share cutpoint c*: 0.25
```

All are **calibration constants, not derived**. Frozen in code per the static-
parameter rule. The paper's §1.1 tiered thresholds win over the landing page's
flat "≥3%".

---

## Data contract

```
name             string
tier             "Value" | "Comfort" | "Premium" | "ColdStart"
campaignShare    number | null      // null for cold start, never faked
usualSpend       number             // baseline for gap computation
cartValue        number
bookings         number
avgStars         number
abandonedAt      timestamp
freezeExpiresAt  timestamp | null   // from Duffel; null = no guarantee
outcome          "rebuild" | "lateral" | "reminder" | "alternative"
```

**Seed: 5–6 travelers**, one per decision path. Must include two Premium
travelers with opposite campaign shares (one low → reminder, one high → rebuild
clearing τ=15%) — that contrast is the demo's strongest moment. Construct the
seed so the ladder genuinely reaches 15%; do not back-fit.

No author names as travelers. No name reused across traveler and staff personas.

---

## MCP tools

`read_traveler_history` · `search_flights` · `search_hotels` ·
`check_hold_eligibility`

**`create_hold` is out of scope.** It's a real write against airline inventory;
it must not fire during the demo. Eligibility check is read-only and fine.

Freeze covers the **flight only** — Duffel `payment_required_by`. The hotel has
no equivalent primitive and re-prices at conversion. Three states must render:
eligible (real expiry), not eligible (**no deadline shown at all**), pre-auth
fallback (simulated, explicitly labelled).

---

## Sending

The pipeline **drafts** the notification; the analyst **approves**; the system
**sends**. Sending is real, not a preview.

- **Email sends for real.** WhatsApp stays preview-only — the Business API
  needs verified business status and pre-approved templates, out of reach for
  penyisihan. Label the WhatsApp panel explicitly as a preview so the asymmetry
  reads as a decision, not a bug.
- **Send fires only on explicit approval.** Never as part of the pipeline run.
  Clicking through six travelers must not send six emails.
- **`SEND_ENABLED` flag** so the flow can be demonstrated with sending off if
  the judging environment has no outbound SMTP.
- **`DEMO_RECIPIENT` env var.** Seed travelers are synthetic and have no real
  addresses; sending to fabricated ones bounces and damages sender reputation.
  All demo sends route to one inbox you control.
- SMTP credentials live in `.env`, never committed. `docker compose` reads them.
- **Under `WINDFALL_FIXTURES=1`, sending still works.** Fixtures replace
  *inference*, not *delivery* — you need to prove sending works on judging day.

Scope note: sending synchronously inside the approval request stays within the
BE rule (no queue, no worker, no scheduler). The approval click is a
confirmation on a side-effecting action, not a second AI-triggering input. The
paper's §2.4 should state this explicitly.

---

## Do not build

- Batch / fleet / multi-cart views — violates *input tunggal* and *no bulk
  testing* simultaneously. §5.3 story.
- Sort / filter / pagination toolbar — plain list only. Six cards need no
  navigation.
- `BrowserFrame` (fake browser chrome with `localhost:5000` bar).
- "Zona 1/2/3" vocabulary or visible zone numbering.
- Any dashboard, login, or history surface.
- Orchestrator, scheduler, conversion logging, holdout measurement — all §5.3.

---

## UI rules

**The `reminder` outcome renders at equal visual weight to `rebuild`.** It
currently appears as a greyed-out "skipped" row. It is the product's key
differentiator — a decision, not an absence. This is the single most likely
thing to get quietly dropped.

- Whole traveler card is the click target. If a button is kept, label it for the
  action (`Analisis`) — never an outcome word (`Rebuild`, `Recover`), which
  pre-empts the Classifier.
- Selecting a card **transitions** to the pipeline view; it does not append
  below a still-visible list.
- Every agent stage needs a visible pending state. Stage timing must be **real**,
  driven by the actual response — never `setTimeout` theater.
- Classifier reasoning shows both axes, with line count matching evidence
  needed: two lines for a price intervention ("Campaign share 47% —
  price-sensitive" + "Cart 18% above usual spend"), one line for reminder
  ("Campaign share 9% — historically pays full price"). Keep the asymmetry.
- Surface `campaignShare` on browse cards near the tier badge, visually
  secondary.
- Cold-start tier labelled as proxy-derived.
- Approval control is explicit and distinct from the analysis trigger. Sent
  state must be visible after sending.
- Include a replay control.
- No fake countdowns. A deadline shows only when a carrier genuinely guarantees
  the fare.
- Accessibility: `:focus-visible` rings, keyboard nav, `aria-*` on cards and
  stages, at least one breakpoint (prototype is fixed 1160px).

### Claims discipline

No unmeasured performance numbers anywhere in the UI or copy. Every figure must
be true by construction from the seed run, or a statement of mechanism.

- Report **counts, not percentages** ("3 of 6 carts needed no change"). With six
  travelers any percentage is noise.
- Rebuilds are also zero-discount, so "recovered with zero discount" is vacuous.
  The margin claim is **"IDR 0 margin conceded"** — true across every outcome.
- Never say "discount" on a rebuild. The price is lower because the *trip*
  changed.
- On a reminder, never imply a missed deal.

---

## Language

Indonesian for traveler-facing copy (email / WhatsApp previews) — formal but
warm, address as *Anda*. English for analyst-facing console chrome.

Indonesian number formatting **everywhere**: `USD 1.480`, `−10,3%`, `3,81s`.
Route codes uppercase: `CGK → NRT`.

---

## Design system

Vendored at `frontend/design-system/`. Import tokens from its `tokens/*.css`.
**No hardcoded hex literals** outside `src/app/recovery/windfall.css`, which is
the only file permitted to define a colour — and it defines only what the
bundle does not ship (dark theme, tier tints, CTA colours). Everything the
bundle owns is imported, never restated. Import components from
`@/components/windfall` (the barrel), not individual files.

Note the bundle ships **no** `components/` sources — only a compiled
`_ds_bundle.js`. The React components in `src/components/windfall/` are the
port, and they are the component layer.

`tokens/fonts.css` is deliberately **not** imported: it pulls the three
families from the Google Fonts CDN, and the console must render identically
inside `docker compose` with no outbound network. `next/font` self-hosts them
at build time and `windfall.css` rebinds `--wf-font-*` onto those, so
components still reference only design-system token names.

Fonts: Instrument Serif (product name, section headings, sparing) · Archivo
(body, labels, names) · IBM Plex Mono (all numbers, codes, reasoning, status).

Semantic color is rationed to two places only: ledger pass/fail rows, and amber
markers on previews and price deadlines. No gradients, no glassmorphism, no big
stat cards.

**Preserve the signature tension:** agent reasoning reads as monospace system
output; notification previews read as real messages a human received.

---

## Fixtures

`WINDFALL_FIXTURES=1` replays a captured run from local files — protects
judging day from rate limits and network failure, and conserves Gemini quota
during development.

Two conditions: the live path stays fully functional so real inference can be
demonstrated on request, and the UI labels replay mode **visibly**. "Cached for
reliability" must never quietly become "faked".

Use Gemini Flash for development. Mock LLM responses (`MOCK_LLM=true`) for
plumbing work — most iterations don't need inference at all.

---

## Known stale spec in the design bundle

The bundle predates these decisions and will mislead if followed literally:

- Says **three** outcomes; there are four.
- Names the no-discount outcome `hold`.
- Ships `BrowserFrame` and "Zona 1→3" as foundations.
- Traveler cards lack `campaignShare` and `usualSpend`.
- Has no approval or sent state.
- `_ds_manifest.json` subtitle still reads "the three pipeline verdicts:
  rebuild, hold, alternative".

---

## Paper errata (outstanding — fix in the doc, follow this file meanwhile)

Resolved in the current paper: the two-axis rule now appears in §4.1, the
percentile notation and `k*` stopping rule landed, and `s_i` is introduced in
§3.2.1. Still outstanding:

- **Tabel 1.5 says "rendering preview tanpa pengiriman aktual"** — wrong.
  Sending on approval is in scope. The Abstrak and Tabel 1.7 ("serta mengirim
  pesan tersebut") are correct; Tabel 1.5 and §2.3.2 need updating to describe
  preview → approval → send.
- Tabel 1.6 has no lateral rung; §4.1 prose and this file define one.
- Gambar 5.1 says "Organizer Agent"; Tabel 1.7 says Classifier. Classifier is
  correct.
- Agent naming drifts three ways: "Notification Agent" (Abstrak, Gambar 5.1),
  "Notification Curator" (Tabel 1.1), "Notification Curator Agent" (elsewhere).
  Canonical: **Notification Curator Agent**.
- `c*` is used in §4.1 but never given a value, while every other constant is
  frozen. It is 0,25.
- §3.2.3 cites `[10]` for an extended-RFM claim; should be `[11]` (Ozcan).
- §5.3 reads *"tidak sengaja diberi tindakan"* — inverts the holdout
  definition. Should be *"sengaja tidak diberi tindakan"*.
- §3.2.5 is silent on cold-start `campaignShare`; this file resolves it as null.
- "traveler" and "wisatawan" used interchangeably. Standardise on **traveler**.

---

## Done means

- `docker compose up` works from clean per README
- All four outcomes render, `reminder` at equal weight to `rebuild`
- Reasoning trace visible: tier + rationale, each ladder attempt + result,
  final decision, notification preview
- Approval sends a real email to `DEMO_RECIPIENT`; sent state visible
- Whole flow in one synchronous request cycle
- No hardcoded hex; `npm run build` passes
- No unmeasured claims in any copy
- Pre-commit scope check passes on every commit

---

## Working style

Commit at the end of every stage. Never carry uncommitted work across stages.

- Conventional commits: `feat:` `fix:` `docs:` `chore:` `refactor:`. Subject
  under 72 chars, imperative mood.
- **Commit messages contain the message body only.** No attribution, no
  co-author trailer, no generation footer. `.claude/settings.local.json` sets
  attribution to empty — do not override it, and do not write attribution text
  into the message body manually.
- Never `git commit --amend`, `git rebase`, `git reset --hard`, or force-push.
  History is append-only.
- Never alter commit dates or author dates.
- If a stage fails midway, commit the working part with a `wip:` prefix and
  report, rather than leaving it uncommitted.
- Ask before deviating from anything in this file.