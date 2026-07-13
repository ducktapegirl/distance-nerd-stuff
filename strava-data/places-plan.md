# Places — Build Plan (model-split execution)

**Status:** APPROVED PLAN (2026-07-13). Input to a `/strava` pipeline run.
**Source of intent:** [`places-prespec.md`](places-prespec.md) (concept + module contracts).
**Design mocks (in-repo):** [`mocks/places-hero-mock.html`](mocks/places-hero-mock.html),
[`mocks/places-passport-mock.html`](mocks/places-passport-mock.html).

## Context

`places-prespec.md` defines a **Places** section that replaces the thin **Map** tab (start-point
dots hard-centered on San Diego, ignoring the 344 GPS stream files). Places is a story-first
keepsake built from those streams: a full-bleed route/heatmap hero, twin home heatmaps, a
passport filmstrip of trips, and a restrained peaks record book.

This plan's distinguishing purpose: **split the `/strava` pipeline stages across Fable, Opus, and
Sonnet** to maximize each model's impact while respecting that **Fable access is limited**.

---

## Model split (the core of this plan)

Principle: **Fable is scarce and creative; Opus is the correctness workhorse; Sonnet is the
high-volume implementer.** Assign each stage the cheapest model that does the job well, and
reserve Fable for the one stage where its aesthetic/narrative judgment isn't cheaply reproduced.

All `strava-*` agents pin `model: opus` in their frontmatter **except** `strava-qa` and
`strava-maintenance` (`sonnet`). Realize the split via the **`model` override** on each `Agent`
dispatch (e.g. `Agent(subagent_type="strava-viz-design", model="fable", …)`). The `/strava`
orchestrator runs in the **main session** (a subagent can't spawn subagents) — keep it on
**Opus** for gate judgment.

| Stage | Agent / skill | Model | Why |
|---|---|---|---|
| Orchestration + gates | `/strava` (main session) | **Opus** | Drives the pipeline, writes the spec file, runs the review gate — strongest judgment. |
| **Analyze** | `strava-data-analyst` | **Opus** | Correctness-critical: trip-clustering (time-gap-away-from-home, Wrinkle A), stream-draw perf across 344 tracks, projection/fit-to-bounds, superlatives incl. home-adjacent giants (Wrinkle B). Everything downstream trusts these numbers. |
| Ideate (optional) | `strava-creativity` | **Opus** | Modules already specified; heavy ideation not required. Promote to Fable only on a larger budget. |
| **Design** → spec | `strava-viz-design` | **★ Fable** | The one Fable dispatch. Scope is now *harden the mocks for real data* (label behavior vs. dense tracks, Trips lens over real coast-to-coast geometry, projection edge cases) + control/hover/label contracts. Fable's strength + precedent (it authored the dashboard's creative sections). Read-only; **orchestrator (Opus) writes the returned spec into `dashboard-spec.md`.** |
| **Build** | `strava-developer` | **Sonnet** (escalate to Opus) | High-volume, well-specified port of the mocks + real-data wiring. Escalate a specific piece to Opus only if it stalls (projection/perf, map fly-to). |
| **QA** | `strava-qa` | **Sonnet** (default) | Both themes, mobile, label overlap, edge clipping, units policy. No override. |
| **Review gate** | `/code-review` + `/security-review` | **Opus** (main session) | Correctness/safety on the diff, run at high effort. |

**Net Fable spend at the recommended budget: one dispatch (Design).** Widening to Ideate and/or a
Fable design-QA pass is optional; nothing else changes. Note the mocks are so complete that Opus
viz-design could cover Design if Fable is too scarce.

---

## Design mocks — near-production front-end

The two mocks are **not just reference — they are near-production front-end.** The build largely
**ports them and injects real data.**

**Hero mock** (`mocks/places-hero-mock.html`) — a bespoke `<canvas>` renderer, **NOT Plotly, NOT
tile-based.** It projects anchors to a dark radial-gradient canvas, draws routes as additive-blend
glow (`ctx.globalCompositeOperation='lighter'`), and hand-rolls pan/zoom/wheel, tweened fly-to,
on-canvas labels, and the `View` (All·SD·Boston·**Trips = highlight lens**, dims homes/brightens
trips/stays wide) + `Map` (Glow·Terrain) control rows. Palette = exact `config.py` tokens;
**dark-committed** (consistent with pre-spec §7); `prefers-reduced-motion` handled. Uses **seeded
fake routes at abstract positions** → the real build feeds it **real lat/lng projected +
fit-to-bounds**.

**Passport mock** (`mocks/places-passport-mock.html`) — essentially build-ready. HTML/CSS filmstrip
(scroll-snap, edge-fade, drag-to-scroll, hover-lift, badges, region/title/date/tags, brief-stops
chips, gradient key) + a per-thumbnail `<canvas>` drawing a terrain-graded route squiggle
(green→slate→red via `gradeColor()`) + a violet elevation profile. **Already fully theme-aware**
(`prefers-color-scheme` + `:root[data-theme]` overrides, matching `applyChartTheme()`). Build swaps
the seeded squiggle for the real per-trip `lat/lng` path, real per-segment `grade_pct` coloring,
and real `altitude_m` profile; generates stamps from the precomputed trips.

**Architecture decision (recommended: Option A).** Adopt the canvas approach — port the mock's
renderer and feed it real projected coordinates — rather than reconcile the look onto a Plotly tile
map (Option B), which can't faithfully reproduce the additive glow, fly-to, or Trips lens. Both
`charts_places` builders therefore emit **raw HTML/`<canvas>`/JS strings with data injected as
JSON**, not `go.Figure` — following the **`chart_calendar()` precedent** (`dashboard/charts_production.py`),
which already returns a raw HTML/SVG string.

**Guardrails:** port the mocks' structure/CSS/JS; replace only fake data with real streams +
precomputed trips/superlatives. Colors already match the palette (**no new hex**, pre-spec §7).
Hero stays dark-committed; passport is already theme-aware. Preserve `prefers-reduced-motion`.

---

## Execution phases (hero-first MVP)

Run through `/strava`, pausing at each gate. Each pass ends with build + QA + review + a rebuilt
`Running Log/strava.html`.

### Pass A — Foundation + Hero (Module 1)
1. **Analyze (Opus):** stream loader for `data/streams/*.csv` (stdlib + numpy, **no pandas**) with
   per-track decimation/point budget; projection `lat/lng → normalized canvas coords` +
   fit-to-all-bounds so both coasts frame by default; per-view framings for SD/Boston zoom;
   confirm Trips stays wide; home-box counts (145/136); region/state/province counts. Pin numbers.
2. **Design (Fable):** adapt the hero mock into `dashboard-spec.md` — harden for real data (labels
   vs. dense tracks, Trips lens over real geometry, projection edges), div ids, control contracts,
   label rules, theme-swappable basemap treatment.
3. **Build (Sonnet):** `charts_places.py` with `chart_places_hero()` returning a raw
   HTML/`<canvas>`/JS string — port the mock renderer, inject real routes as JSON; retire
   `chart_map()`; nav tuple `("map","Map")` → `("places","Places")` + section id
   `view-map` → `view-places` in `page.py`; add Places section HTML.
4. **QA (Sonnet)** → **Review gate (Opus)** → rebuild.

### Pass B — Two homes (Module 2)
- **Analyze (Opus):** per-home miles, most-repeated loop/street, date ranges.
- **Build (Sonnet):** two equal glass cards, identical scale/zoom, dark heatmap thumbnails, 3-line
  mono stat blocks, no arrow. (Spec extension by Opus if Fable budget is tight — aesthetic already
  established in Pass A.)
- **QA / Review.**

### Pass C — Passport (Module 3) + Peaks (Module 4)
- **Analyze (Opus):** the analytical heart — trip-clustering (recover Whitney 4d/14,507 ft, Maine
  3d nordic×3, plus the ~14 auto-detected trips), per-trip terrain-gradient path from `grade_pct`,
  elevation profiles from `altitude_m`, superlative badges (D1), and the ~5–6 peaks rows incl. San
  Jacinto 10,800 ft (Wrinkle B). Emit a precomputed trips/superlatives structure.
- **Build (Sonnet):** the passport mock is build-ready — port its HTML/CSS/JS wholesale and swap
  seeded thumbnails for real path + `grade_pct` + `altitude_m`; generate stamps from precomputed
  trips (captions = athlete's own titles, region overline / date / tags, badges, hover "↗ view on
  map" → hero fly-to, brief-stops chips). Then build the **peaks record book** (no mock; reuse the
  passport's canvas elevation-profile code for altitude sparklines; click-to-fly into hero).
  Fable only for an optional polish pass.
- **QA / Review.**

Modules 3–4 share the trip/superlative precompute, so they land together.

---

## Module build order & dependency notes

- **Analyze is the foundation** — the stream loader/projection (Pass A) and the trip/superlative
  precompute (Pass C) are what everything renders from. Get the point budget + projection right
  early; hero, homes, and passport thumbnails all reuse them.
- **Map = overview, passport = drill-down** (pre-spec §6). Build the hero fly-to hook in Pass A so
  Pass C's stamps/peaks can call it.
- **No new palette hex, no new data files** (pre-spec §7, §9). Terrain gradient reuses green
  `#4ade80` / slate `#8b949e` / red `#f87171` (`SLOWER`); elevation violet `#a78bfa`
  (`ELEVATION_COLOR`).

---

## Critical files

- **New:** `strava-data/dashboard/charts_places.py` — builders returning **raw HTML/`<canvas>`/JS
  strings**, not `go.Figure` (chart_calendar precedent); keeps large Places code out of
  `charts_production.py` (`charts_exploratory.py` precedent).
- **Edit:** `dashboard-spec.md` (Design writes view specs); `dashboard/page.py` (retire `chart_map`
  import/call, swap nav tuple + section id, add Places section HTML/JS, register any new click
  chart ids); `dashboard/config.py` (home-box constants only — reuse existing color/font tokens,
  **no new hex**); `dashboard/template.py` (any shared CSS/JS if not self-contained in the raw
  builder strings).
- **Retire:** `chart_map()` in `dashboard/charts_production.py` and its `page.py` wiring.
- **Design source (read-only):** `mocks/places-hero-mock.html`, `mocks/places-passport-mock.html`.
- **Reuse:** `fig_html`/`tidy_dark` (`theme.py`) where any real Plotly is used; `applyChartTheme()`
  (`template.py` JS); `mf`/`sport_category`/`fmt_pace` (`data.py`); the `.seg-filter`/`.seg-btn`
  control component; `KM_TO_MI`/`M_TO_FT`/`SPORT_COLORS`/`TRAIL_RUN_COLOR`/`HIKE_COLOR` (`config.py`).

---

## Verification (per pass)

1. **Build:** `uv run python strava-data/build_dashboard.py` regenerates `Running Log/strava.html`;
   check console for the new Places build lines.
2. **QA agent (Sonnet):** static checks + Preview-MCP visual pass (desktop + mobile, light + dark):
   render, label-overlap, edge-clipping, contrast, units policy (min/mi, mph, °F). Preview-MCP CDN
   caveat in `CLAUDE.md`; `tools/mobile_preview.py` is the local fallback (run un-sandboxed).
3. **Manual spot-checks:** both home glows visible on default fit-to-bounds; `Trips` dims homes and
   brightens sparks **without zooming**; a passport-stamp click flies the hero to that trip; old
   "Map" tab gone, nav reads "Places".
4. **Data accuracy:** Whitney 14,507 ft, San Jacinto 10,800 ft, home counts 145/136, region count
   match the analyst's pinned numbers.
5. **Review gate:** `/code-review` (high) + `/security-review`; loop back to Build on material
   findings.

---

## Open decisions to confirm before Pass A

- **Rendering architecture** — adopt the mock's **canvas renderer** (Option A, recommended) or
  reconcile the look onto a **Plotly tile map** (Option B, real basemap but loses the mock's glow /
  fly-to / Trips lens)?
- **Fable budget** — one dispatch (Design, recommended), or widen to Ideate / a design-QA pass?
  (Given how complete the mocks are, Opus viz-design could even cover Design.)
- **Build cadence** — hero-first MVP (recommended) or all four modules in one pipeline pass?
- **Escalation** — OK to escalate a Build sub-task to Opus if projection/perf or the map fly-to
  stalls under Sonnet?
