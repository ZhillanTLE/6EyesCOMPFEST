# Windfall — session handoff

**Read this, then `frontend/CLAUDE.md`, then start.** Do not re-read the design
bundle or the paper PDF; everything load-bearing from both is already in the
repo. Re-deriving them is the main way to burn tokens on this project.

Authority order: `docs/windfall-paper.md` → `frontend/CLAUDE.md` → the vendored
design system. CLAUDE.md wins over the paper where they conflict.

---

## Next session — start here (written Aug 2026)

**Verify state in five commands**

```bash
python -m unittest discover -s backend/tests -t .   # 120 tests, all green
python scripts/scope_check.py                       # must exit 0
cd frontend && npm run build                        # must pass
WINDFALL_FIXTURES=1 PORT=8000 python -m backend.app # then curl /api/recovery/health
cd frontend && npx next start -p 3067               # /windfall and /recovery
```

Run BOTH servers. The console fetches its cards from Flask through the Next
rewrite, so with Flask down `/recovery` shows a bare "Internal Server Error"
and no cards. That is the whole explanation for the missing-seed-data report
from last session — the data was never broken, the backend process had been
stopped.

### The one thing left that cannot be done from here

**Step 8 — `docker compose up` has still never run.** Docker is not installed
on this machine. Everything else on *Done means* is verified; this is not.
Run `docker compose up --build` first thing on a machine with Docker, then
open `http://localhost:3000/recovery`.

Verified by reading, this session (see *Docker audit* below): compose service
names, ports, build contexts, both Dockerfiles' COPY paths against the real
tree, the backend HEALTHCHECK that `depends_on: service_healthy` needs, the
build-arg-not-env-var handling of `WINDFALL_API_ORIGIN`, and `.env.example`
against every variable the code reads. **Still unproven and only provable by
running it:** that the base images pull, that `npm ci` resolves in-image, that
both healthchecks actually pass, and that `depends_on` sequences correctly.

### Unfinished thread from this session

The live-inference refusal was committed and unit-tested (120 green), but the
**HTTP** verification was interrupted before it ran. Confirm it by hand:

```bash
WINDFALL_FIXTURES=0 MOCK_LLM=false GEMINI_API_KEY= PORT=8001 python -m backend.app
curl  http://127.0.0.1:8001/api/recovery/health         # inferenceConfigured: false
curl -X POST http://127.0.0.1:8001/api/recovery/run      -H 'Content-Type: application/json' -d '{"travelerId":"wf-01"}'
# expect HTTP 503 and reason: live_inference_unconfigured
```

Also still worth doing: the console renders whatever `error` string the API
returns, so a dead backend reads as "Internal Server Error". Distinguishing a
connectivity failure from an API error in `frontend/src/lib/windfall/api.ts`
would turn that into something actionable. Not started.

### When the Gemini key arrives

The live path is complete and wired — `llm.py` (one `complete_json`, temp 0,
static prompts), `classifier_agent`, `searcher_agent`, `notification_curator`,
and the four MCP tools in `mcp_tools.py` (in-process by default,
`WINDFALL_MCP=stdio` to route through a real MCP session). Put the key in
`backend/.env` and run with `WINDFALL_FIXTURES=0`. Watch for `reasonedBy` /
`writtenBy` reading `gemini` rather than `deterministic (...)`, and for the
FALLBACK badge disappearing from the pipeline stages.

---

## Where things stand

Steps 1, 2, 3, 4, the sending feature and the frontend design-handoff work
are **done and committed**. Remaining: **step 6, `docker compose`** — plus the
loose ends under *Not done*.

The console is now the handoff's three-view flow — **browse → pipeline →
previews** — and there is a landing page at `/windfall`.

**Design-alignment pass (Aug 2026, see `docs/design-plan.md`):** both pages
were rebuilt/reworked to the two-page reference bundle. The landing carries
the reference's hero, decision marquee, captured-run pipeline demo,
product/market/approver bands and the shared wave footer; the console gained
the stepper header, the dark default theme, the segmented theme control, the
card signals strip and the same footer. Forbidden features (batch/fleet,
sort/filter/pagination, BrowserFrame, traveler override) stay excluded.

**The pixels have now been looked at.** Both routes were driven in a headless
browser against Flask fixtures: browse → pipeline (rebuild wf-01 and reminder
wf-03, equal weight) → previews, with screenshots reviewed and zero console
errors. That pass caught a real bug: the `--wf-font-*` tokens rebind at
`:root`, but next/font's variables lived on a layout wrapper div, so every
font token computed to guaranteed-invalid and BOTH routes had always rendered
in Arial. Fixed by hoisting `fontVars` onto `<html>` in the root layout.

```
b5d686c  feat: send the approved notification on explicit approval
cf8f549  feat: pipeline screen with real per-stage timing
26c25ea  fix: vendor design system, add paper, enforce scope check
7f79a44  Step 3: complete the design-system port
e450d03  Step 3 (in progress): port Windfall design-system components
77b790a  Step 2: synchronous recovery endpoint returning the full reasoning trace
f383cd9  Step 1: recovery data contracts, deterministic core, and golden fixture
40baf36  Initial commit
```

Remote is `https://github.com/ZhillanTLE/6EyesCOMPFEST`. The older
`6Eyes-AIC-COMPFEST` repo is abandoned but still public and still shows Claude
as co-author on two commits — the user was advised to delete it.

### Verify state in four commands

```bash
python -m unittest discover -s backend/tests -t .   # 111 tests, all green
python scripts/scope_check.py                       # must exit 0
cd frontend && npm run build                        # must pass
python -m backend.tools.duffel_hold_probe           # needs a key; see Blockers
```

---

## Architecture in one screen

**Backend** — `backend/recovery/`, an isolated Flask blueprint. Shares nothing
with the pre-existing `/api/plan-trip`: no background thread, no SocketIO, no
Firestore, no auth decorator. That isolation is deliberate and is what makes
the penyisihan scope claims true of the recovery path.

```
config.py        every frozen constant. Nothing steers a decision from elsewhere.
schemas.py       dataclass contracts for every seam. to_dict() camelCases.
serialize.py     snake_case inside, camelCase on the wire.
tiers.py         percentile tier + cold-start cart proxy.
gate.py          the two-axis rule. THE product.
ladder.py        rungs, deltas, first-clear. All arithmetic lives here.
outcomes.py      the ONLY place an outcome is chosen.
pipeline.py      orchestrates + measures per-stage wall clock.
providers.py     FixtureProvider / LiveProvider, hold status.
notifications.py Indonesian traveler copy (templates; Gemini swaps in later).
sender.py        SMTP, on approval only.
repository.py    seed reader + browse queue.
formatting.py    Indonesian numbers (IDR 24.640.000, -11,2%).
routes/recovery.py   GET /queue, POST /run, POST /send, GET /health
```

**Frontend** — Next.js 16 App Router at `/recovery`. A **client that calls
Flask**, nothing more. `next.config.ts` rewrites `/api/recovery/*` to Flask so
the browser stays same-origin.

```
app/recovery/{layout,page,windfall.css}   the console, three views
app/windfall/{layout,page,reveal}         the landing page
components/windfall/  primitives, AgentStage, AgentAvatar, FareLedger,
                      OutcomeCard, previews, TravelerCard, BrowseView,
                      PipelineView, PreviewsView, ApprovalBar, HoldPanel,
                      index (barrel)
lib/windfall/         types, format, api, replay, fonts
design-system/        VENDORED tokens + assets, tracked in git
```

`windfall.css` is shared by both routes and stays the only file allowed a hex
literal. `lib/windfall/fonts.ts` holds the three next/font calls so the console
and the landing page cannot drift onto different weights.

**Route-name overlap, verified harmless.** The landing page is `/windfall` and
the static assets live under `public/windfall/`. Next serves the public file
for an exact asset path and the page for `/windfall` itself; both were probed
and return 200. Do not add a nested route under `app/windfall/` that collides
with an asset directory name.

---

## Decisions already made — do not re-litigate

Each cost a round trip with the user. They are settled.

1. **Next.js, not Vite.** CLAUDE.md's original "React/Vite" was a
   recommendation written before the repo was seen. Amended. The hard
   constraint is `docker compose up`, not the framework. **Boundary that must
   hold:** no Route Handlers serving business logic, no Server Actions, no
   Server Component data fetching. Flask stays the only backend.

2. **Browse cards SHOW tier and campaign share** — as a *provisional estimate*,
   labelled "Likely:". This reverses an earlier decision. The reasoning, worth
   keeping: campaign share is raw history and the tier estimate is a
   deterministic percentile lookup, both cheap and available before inference.
   The Classifier produces a *reasoned verdict* that can differ. Showing the
   estimate gives a reviewer a hypothesis to test the model against; without it
   there is nothing to compare the output to, and the fair question becomes why
   Gemini is in the loop at all.

3. **Sending is real.** Email sends on approval; WhatsApp is preview-only and
   labelled so on screen. Fixtures do **not** disable delivery.

4. **Design bundle is vendored** at `frontend/design-system/`, tracked. A judge
   cloning the repo must build without a directory that exists on one machine.
   `windfall.css` imports the real tokens and defines only what the bundle
   lacks (dark theme, tier tints, CTA colours) — it is **the only file allowed
   a hex literal**.

5. **`tokens/fonts.css` is deliberately not imported.** It pulls Google Fonts
   over the network; the console must render inside docker with no egress.
   `next/font` self-hosts and `windfall.css` rebinds `--wf-font-*`.

6. **Cold start:** `campaignShare` is `null`, never fabricated. The ladder still
   runs on the cart-proxy tier because a rebuild concedes no margin. Tier stays
   one of Value/Comfort/Premium with `tierSource: "cart_proxy"`; the UI labels
   it "Cold-start". CLAUDE.md's contract lists `ColdStart` as a tier value —
   this reconciliation keeps τ well-defined and satisfies the display rule.

7. **Per-cart tests only.** A loop over the seed is a bulk-testing script and
   violates the AI scope rule. It shipped once and was caught by review, which
   is why `scripts/scope_check.py` exists and must run before every commit.

8. **Git history is append-only.** No amend, rebase, or force-push. Earlier
   rewrites predate the rule and were user-instructed.

9. **Previews are their own screen, reached BEFORE approving.** The prototype
   reached `previews` only after approving and headed it "Disetujui". That
   inverts the product — CLAUDE.md is explicit that the analyst approves before
   anything is sent, and the handoff README states the purpose as reading the
   message before it sends. So `ApprovalBar` lives on the previews screen and
   the sent state renders there. The pipeline screen ends on a forward control.

10. **The landing page ships at `/windfall`, with its headline figures
    replaced.** The design's "32% recovered with zero discount" and "68% offered
    / 32% purposely declined" were never measured, and with six carts a
    percentage is noise. The rail states counts taken from the captured run.
    "IDR 0 margin conceded" survives verbatim — true across every outcome, and
    asserted by a test. `/` is still the pre-existing plan-trip app and was left
    alone.

11. **Commits:** conventional style, message body only, **no attribution or
    co-author trailer**. `.claude/settings.local.json` lives in the *parent*
   directory `compfest/`, not the repo. Author as
   `Zhillan <zhillanbaniaksa@gmail.com>` so GitHub shows one contributor.

---

## The decision logic — everything depends on it

```
c_i = campaignShare            share of past spend on discounted product
g_i = (p_0 - s_i) / s_i        budget gap: cart vs. usual spend

D_i = rebuild ladder           iff c_i >= 0.25 AND g_i > 0
      reminder, no discount    otherwise
```

**Both axes, always.** Campaign share alone must never trigger an intervention.
This is the whole thesis and the easiest thing to accidentally simplify away.

Ladder: `01 reprice → 02 lateral → 03 tier_down`, stop at first `δ_k ≥ τ`.
τ = Value 0.05 · Comfort 0.10 · Premium 0.15. Percentile cuts 0.30 / 0.80.
c\* = 0.25. All are calibration constants, frozen, not derived.

**`p_0` is the ABANDONMENT price**, carried in the seed as `valueIdr` on the
flight and the hotel. It is history and must not move underneath the search:
if `p_0` were a fresh re-quote, rung 01 would compare today's price to itself
and could only ever return 0%, silently disabling the cheapest rung. `p_k`
comes from re-query; `p_0` does not.

**Lateral is hotel-only and the flight is pinned across every rung** — a Duffel
Hold Order is held against one flight offer, so swapping the flight voids the
guarantee the freeze exists to provide.

Four outcomes: `rebuild` · `lateral` · `reminder` · `alternative`, plus `error`
for upstream failure. **Never name the no-discount outcome `hold`** — it
collides with Hold Order.

### The seed — 6 travelers, one per path

| id | name | tier | share | outcome | why it exists |
|---|---|---|---|---|---|
| wf-01 | Prasetyo Wibowo | Premium | 0.09 | reminder | gate closes on campaign share though the cart IS over budget |
| wf-02 | Ayu Kartika | Premium | 0.46 | rebuild | **the contrast**: same tier as wf-01, opposite outcome, purely from share. Genuinely clears τ=15% |
| wf-03 | Bagus Hartono | Comfort | 0.44 | lateral | same-star swap clears; ladder stops before any downgrade |
| wf-04 | Intan Maharani | Value | 0.45 | alternative | gate opens, nothing clears, different trip proposed |
| wf-05 | Rizky Firmansyah | proxy | null | reminder | cold start; ladder runs, nothing worth showing |
| wf-06 | Dewi Anggraini | Comfort | 0.31 | error | carrier inventory unavailable; classifier and gate still complete because p_0 is known |

wf-01 beside wf-02 is the demo's strongest moment. Do not weaken it.

---

## Not done

**Step 6 — `docker compose` is WRITTEN but NEVER RUN.**

`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, both
`.dockerignore`s and `README.md` all exist. **Docker is not installed on the
development machine**, so `docker compose up` has never executed. This is the
one remaining item in *Done means* that cannot be ticked from here.

What WAS verified, by assembling the runtime layout by hand and running it:

- the build arg bakes correctly — `routes-manifest.json` contains
  `http://backend:8000/api/recovery/:path*`
- `.next/standalone/server.js` is emitted
- `public/` and `.next/static` are genuinely **absent** from standalone, so the
  Dockerfile's manual copy is load-bearing, not defensive
- the assembled layout serves `/recovery` (HTTP 200), proxies
  `/api/recovery/queue` through to Flask, and serves
  `/windfall/agents/classifier-awake.svg` (HTTP 200)
- all six carts run through the Next proxy with correct outcomes, real
  per-stage timings and `marginConcededIdr: 0`

**ANSWERED — the rewrite destination IS baked at build time.** It is written
into `.next/routes-manifest.json` during `next build`. Setting
`WINDFALL_API_ORIGIN` under compose `environment:` would silently do nothing;
it is passed as a **build arg**. Changing the backend host requires a rebuild.

What is still unproven: whether the images actually build, whether
`node:22-alpine` and `python:3.12-slim` pull cleanly, whether the healthchecks
pass, and whether `depends_on: service_healthy` sequences correctly. **Run
`docker compose up --build` first thing.**

**Seen in a browser only through curl.** Both routes were served from a real
`npm run start` with Flask behind the proxy and probed: `/windfall` 200 with
every section present in the server-rendered HTML, `/recovery` 200, the queue
proxy 200, `POST /api/recovery/run` for wf-02 returning `rebuild` with
`marginConcededIdr: 0` and real per-stage timings, and both the agent and brand
SVGs 200. What that does NOT prove is layout: nobody has looked at the pixels.

Historic note, still partly true: The page returns HTTP 200 and every UI
string is present in the client bundle, but the browse cards are fetched
client-side (a direct consequence of CLAUDE.md forbidding Server Component data
fetching), so server-rendered HTML contains the shell and no cards. Nobody has
*looked* at the console. Do this immediately after compose works — it is the
cheapest way to find layout breakage.

**Agent avatars now render.** `AgentAvatar.tsx` stacks all three states and
crossfades by opacity, as the handoff requires; `avatarState()` ports the
prototype's `stFor()`, including the halted case where the Classifier finishes
and everything downstream stays asleep.

**Accessibility done.** Live region announcing each phase, table semantics on
the fare ledger, spoken status on agent stages, `:focus-visible` rings,
keyboard-activated cards, one breakpoint at 720px.

**Gemini agents exist but have never made a real call.** All three are wired
(`classifier_agent.py`, `searcher_agent.py`, `notification_curator.py`) behind
`llm.py`, with deterministic fallbacks. Inference is skipped for three reasons,
each survivable and each reported in the trace: `MOCK_LLM=true`,
`WINDFALL_FIXTURES=1`, or no `GEMINI_API_KEY`. **No key has ever been
configured, so the live prompts are unexercised** — the JSON contracts, the
one-step tier cap and the emoji stripper have only been tested against their
fallbacks. Set `GEMINI_API_KEY`, run with `WINDFALL_FIXTURES=0`, and check that
`reasonedBy`/`writtenBy` report `gemini` rather than `deterministic`.

**MCP tools complete, and the contract is proven across the process
boundary.** All four from paper section 5.1 are registered with FastMCP and
dispatchable in-process. `WINDFALL_MCP=stdio` now genuinely routes through a
real MCP client session, and a test asserts both paths return identical
results — including that a null `campaignShare` survives serialisation rather
than quietly becoming zero. `create_hold` is absent and a test keeps it absent.

**Hold states render.** `hold_manager.py` exists (paper section 5.2.2 names it)
and all three states appear on screen: eligible with a real expiry, not
eligible with no deadline at all, simulated explicitly labelled. Scope is
declared as flight-only everywhere, because Duffel holds a flight offer and
the hotel re-prices at conversion.

**`LiveProvider` wired but never run against a real API.** `WINDFALL_FIXTURES=0`
now genuinely takes the live path (an earlier revision always used fixtures and
only changed the label). Without keys it fails honestly with an `error`
outcome. With keys, nothing is known: the ladder may not clear, and the seed
was calibrated against fixtures, so **wf-02 clearing tau=15% on live prices is
unverified**.

Smaller: `docs/windfall-paper.md` errata are applied in the markdown but **the
submitted PDF still carries all eleven defects**. (`MOCK_LLM` and the README run
instructions were listed here as missing; both have since landed.)

**`frontend/windfallpaper.md` is a stale untracked duplicate** of the spec — 435
lines against the 642 in `docs/windfall-paper.md`, with none of the errata
applied. Delete it; a second copy of the spec that disagrees with the first is a
trap.

**`npm run build` passes but `npx eslint` reports one pre-existing error** in
`app/recovery/page.tsx`: the theme-hydration effect calls `setState` directly
(`react-hooks/set-state-in-effect`). Predates this work and does not fail the
build, because Next 16 no longer lints during `build`.

---

## Blockers needing the user

1. **`backend/.env` does not exist.** No `DUFFEL_API_KEY`, so
   `duffel_hold_probe.py` cannot run and hold eligibility is guesswork. If no
   seeded carrier supports hold, the honest move is to drop the freeze from the
   demo narrative and make the ladder the whole story. The probe is written,
   read-only, and has no path to `POST /air/orders`.

2. **Q14 unanswered — Hotels.com or Tripadvisor?** The paper said Hotels.com;
   the code calls `tripadvisor16.p.rapidapi.com`. `.env.example` documents a
   `RAPIDAPI_HOST` nothing reads. `_rapidapi_search_hotels` is **defined twice**
   in `skyscanner_gds.py` (~lines 343 and 351); the first is dead code shadowed
   by the second. Star rating is what the entire ladder pivots on — confirm the
   field exists and is populated before switching providers.

3. **No SMTP credentials.** `DEMO_RECIPIENT`, `SMTP_HOST` etc. are documented in
   `.env.example` but unset, so sending has only been exercised in `suppressed`
   and `failed` states. An email has never actually been delivered.

---

## Pre-existing scope violations — in code, not introduced here

These live in `/api/plan-trip` and predate this work. Isolated rather than
fixed, per the user's decision:

- `app.py:161` spawns `threading.Thread` and streams over SocketIO → background job
- `firebase_state.py` is Firestore → distributed database
- `auth.py` guards both mutation endpoints → complex authentication
- Redis for GDS caching and as the SocketIO broker

The recovery blueprint touches none of it and `scope_check.py` enforces that. A
judge reading `app.py` will still see `threading.Thread`; a comment there names
the boundary.

---

## Practical gotchas

- **Bash heredocs over roughly 110 lines fail** here with `unexpected EOF`.
  Write long files in two or three appended chunks. This cost several retries,
  including while writing this file.
- **`git filter-branch` / amend / force-push are forbidden** by CLAUDE.md.
- Windows line endings: git warns `LF will be replaced by CRLF` constantly.
  Harmless noise.
- `frontend/AGENTS.md` requires reading `node_modules/next/dist/docs/` before
  writing Next code. Not decorative — the `output: "standalone"` static-file
  caveat above came from there.
- Run `python scripts/scope_check.py` before **every** commit. It is a real
  gate, not documentation.
- Regenerate golden one cart at a time:
  `WINDFALL_FIXTURES=1 python -m backend.tools.build_golden --cart wf-02`
- `npm install` in `frontend/` takes about a minute and is required before any
  build or typecheck.

---

## Definition of done (from CLAUDE.md)

- [~] `docker compose up` — written, never run (no Docker on the dev machine)
- [x] All four outcomes render, `reminder` at equal weight to `rebuild`
- [x] Reasoning trace visible: tier + rationale, each ladder attempt + result,
      final decision, notification preview
- [ ] Approval sends a real email to `DEMO_RECIPIENT`; sent state visible
      — flow and UI are built, but nothing has ever been delivered
- [x] Whole flow in one synchronous request cycle
- [x] No hardcoded hex; `npm run build` passes
- [x] No unmeasured claims in any copy
- [x] Pre-commit scope check passes on every commit

**Suggested next move:** install Docker, run `docker compose up --build` and fix
whatever it reveals, then load `/recovery` and `/windfall` in a real browser and
look at them. After that, set `GEMINI_API_KEY` and confirm the agents report
`gemini` rather than `deterministic`.

---

## Docker audit — read line by line, Aug 2026

Done because compose cannot be run here. Findings, both fixed:

1. **`.dockerignore` never applied.** Both services build with `context: .`,
   and Docker resolves `.dockerignore` from the context root only, so
   `backend/.dockerignore` and `frontend/.dockerignore` were dead files. Every
   build would have shipped `.git`, `frontend/node_modules`, `frontend/.next`,
   `__pycache__` and any `backend/.env` into the context — the first of those
   bakes secrets into an image layer, and the second drops host (Windows)
   binaries on top of the clean `npm ci` tree via `COPY frontend ./` and breaks
   the in-image build. Consolidated into one file at the context root; the dead
   copies were deleted rather than left looking protective.

2. **`.env.example` was missing `WINDFALL_MCP`.** Every other variable the
   recovery path reads was already documented; that one was not.

Confirmed correct and needing no change: `backend/Dockerfile` carries the
HEALTHCHECK that the frontend's `depends_on: condition: service_healthy`
requires (it is in the Dockerfile, not compose — valid, and easy to misread as
missing); `WINDFALL_API_ORIGIN` is a build arg because `next.config.ts`
resolves `rewrites()` at build time; ports 8000/3000 match the README;
`backend/` is a PEP 420 namespace package so `python -m backend.app` needs no
`__init__.py`; the seed JSON and `frontend/design-system/` both ship; and
nothing the build needs is caught by the new ignore patterns.
