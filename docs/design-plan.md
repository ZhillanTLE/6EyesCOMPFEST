# Reference design → implementation plan

Source: `Windfall (landing + console).html`, a two-page bundle. Both embedded
documents were decoded to `design/landing.html` and `design/console.html`
(gitignored — derived from the raw bundle, which is itself gitignored; this
plan is the tracked record of what they contain).

The outer file routes between the two pages with `#landing` / `#console`
fragments and a `postMessage({wfGo})` iframe harness. That harness is a
prototype artifact; the app uses real Next.js routes (`/windfall`,
`/recovery`) and plain links between them.

Authority: CLAUDE.md wins on logic and scope; the design wins on layout,
visuals and copy; `docs/windfall-paper.md` is the specification.

## Landing page (`design/landing.html` → `app/windfall/page.tsx`)

| Design section | Component / disposition |
|---|---|
| Sticky nav: mark + serif "Windfall", links Product · Market · Who runs it, ink "Open the console" button | `LandingNav` (in page) — links to `#product` `#market` `#user` and `/recovery` |
| Hero: "New — the three-agent pipeline is live" pill with 3 stacked agent avatars; mono-700 60px headline "We rebuild abandoned carts, not give discounts."; sub-para; stat rail; CTA pair | Hero block. **Claims discipline:** the design's "32% recovered" / "IDR 0 spent discounting travelers who'd book anyway" are unmeasured — the rail states counts from the captured run instead ("2 of 10 sent a reminder, no offer", "IDR 0 margin conceded"). Layout, type and animation match the design. |
| "Decisions approved today" marquee: ten decision cards, duplicated for a seamless loop, edge fade, pause on hover | `DecisionMarquee` (in page). Cards carry the captured run's travelers, outcomes and savings. Design's traveler "Mika Kurosawa" (SCL → MAD) is Salsabilla Hasan in the seed; the caption's "68% / 32%" becomes counts ("7 of 10 got an offer; 2 were left alone on purpose"). Outcome tags: REBUILT / LATERAL / REMINDER / ALTERNATIVE. |
| Animated pipeline demo in a fake browser frame (`localhost:5000/queue/...` bar) | Kept as a static-data demo card, **without the fake browser chrome** — `BrowserFrame` is on CLAUDE.md's do-not-build list. Stage cards, ledger rows, reconciliation footer and the email mock come from Ria Lavenia's captured run; timings shown are the run's real per-stage durations. Scroll-triggered reveal + RUN AGAIN control. |
| `#product`: "One console. Three agents. Nothing else." + 3 agent cards + "Not built on purpose." dashed callout | Product band, verbatim layout. Searcher card footnote states the tiered thresholds (Value 5% · Comfort 10% · Premium 15%), not the design's flat "≥ 3%", per the frozen constants. |
| `#market`: "Carts too valuable to discount blindly." + 3 segment rows on the warm band + exclusion line | Market band, copy verbatim (statements of mechanism / market description, no measured claims). |
| `#user`: "One decision, one approver…" + analyst persona card (Mika Kurosawa, day timeline, NAMED APPROVER) + 4 watcher rows | Persona band. Mika Kurosawa is staff-only (no collision with the traveler seed). Watcher 4's "sends the cart back through the pipeline, which re-reasons" describes a flow that is not built — reworded to what is true (the traveler can reply; the message states what changed and why). |
| Dark CTA band "Rebuild carts now and read the reasoning." | CTA band, verbatim ("Seeded data, no integration" is true). |
| Footer: warm rounded band, tide gradient, three animated wave SVGs, giant "windfall" wordmark, link columns, pulse-arrow links, bottom bar (© · Privacy · Jakarta · 09.41 · N carts in queue) | `WaveFooter` — shared component, used by both pages. "34 carts in queue" → "10 carts in queue" (the real queue). |

## Console (`design/console.html` → `app/recovery/*`)

| Design element | Disposition |
|---|---|
| Fixed header: mark SVG + serif lockup (→ landing), 3-step stepper Carts · Pipeline · Previews, Dark/Light segmented control | Rework console nav to match. Stepper is presentational (reflects the current view). Fixture badge stays. |
| Dark theme default (`wf-theme` in localStorage) | Adopt: design defaults dark; saved preference still wins. |
| Browse: centred mono 44px "Abandoned Carts", 2-col card grid | Adopt title/grid. |
| Card anatomy: name, "Likelihood:" tier pill (tinted), campaign-share line, cart value, signals row (bookings ×N · trip average · avg hotel), route ⇄ + airline, hotel + ★, abandoned label, CTA | Enrich `TravelerCard` with the signals row and ⇄ route per the design. CTA label stays **Analisis** (design's "Recover" pre-empts the Classifier — CLAUDE.md UI rule). |
| Select-all checkboxes, "Recover selected (N)", fleet board, "Approve all", batch results table, "Send all" | **Not built.** Batch/fleet violates *input tunggal* + no-bulk-testing (CLAUDE.md do-not-build). |
| Sort menu, tier filter, pagination, state line | **Not built.** Plain list only (CLAUDE.md do-not-build). |
| Pipeline view: avatar wells overlapping AgentStage cards, skeletons, FareLedger, "No discount needed" panel at equal weight, error panel, DecisionCard with reconciliation grid + OTA strip | Already ported (`PipelineView` + friends). Keep. |
| Previews: mail chrome + EmailPreview, WhatsAppPreview labelled preview-only, PREVIEW tags | Already ported. Approval stays **on the previews screen, before send** (decision #9) — the design's post-approval "Disetujui" ordering is a known inversion and is not restored. |
| Traveler override ("I'd prefer to spend less" → re-run ladder) | **Not built.** A second AI-triggering input (FE rule), and the design implements it as hard-coded theater. §5.3 story. |
| `window.claude.complete` call in the prototype's `recover()` | Prototype artifact. Inference lives in Flask (Gemini), fixtures replay it. |
| Wave footer + bottom bar on the console page | Added via shared `WaveFooter`. |

## Stages already done (verified this session, not rebuilt)

- Step 2 — contracts + per-cart golden fixtures: `backend/recovery/{schemas,serialize}.py`, `seed/{travelers,golden}.json` (ten travelers, outcomes 4 rebuild · 1 lateral · 2 reminder · 2 alternative · 1 error). 117 tests green.
- Step 3 — synchronous `POST /api/recovery/run` returning the full trace.
- Step 6 — approval → real SMTP send behind `SEND_ENABLED` / `DEMO_RECIPIENT`; WhatsApp preview-only.
- Step 7 — `WINDFALL_FIXTURES=1` replay, labelled "Replaying capture" in the header.

Remaining build: step 4 (landing rebuild), step 5 (console chrome + browse
polish), step 8 (`docker compose up` — blocked locally: Docker is not
installed on this machine; the compose files exist and the runtime layout was
verified by hand per `docs/HANDOFF.md`).
