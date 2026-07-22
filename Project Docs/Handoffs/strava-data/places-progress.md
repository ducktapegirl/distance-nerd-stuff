# Places — Build Progress & Handoff

**Purpose:** resume the Places build (`Plans/strava-data/places-plan.md`) cleanly in a fresh session. Read this first,
then `Plans/strava-data/places-plan.md` (the approved plan) and the `## Places` sections of `Specs/strava-data/dashboard-spec.md`
(the build contracts). Source of intent: `Specs/strava-data/places-prespec.md`.

**Branch:** `claude/strava-places-plan-v9oxb3` (work here; do NOT create a new branch).
**Execution model (from the plan):** run through the `/strava` orchestrator skill in the MAIN
session (Opus). Model split per dispatch: Analyze=Opus, Design=Fable (spent — see below),
Build=Sonnet, QA=Sonnet, Review gate (`/code-review` high + `/security-review`)=Opus.
Fable budget is ONE dispatch total and it was spent on Pass A Design — Pass B/C Design are
**Opus spec-extensions** written by the orchestrator.

---

## Status (updated 2026-07-14)

| Pass | Module | State | Commits |
|---|---|---|---|
| **A** | Hero (full GPS route-density map) | ✅ shipped | `9956269`, tweak `62331e6`, labels `f096d57` |
| **B** | Two Homes cards | ✅ shipped | spec `c07b7b0`, code `674cbfc` |
| **C** | Passport + Peaks | ✅ shipped | spec+code this pass (see below) |

All commits pushed. Generated HTML (`running-log/strava.html`) is **gitignored** —
rebuilt from source by the deploy workflow; never commit it.

### What's live (Pass C)
- **Passport** (`chart_places_passport`): horizontal filmstrip of **7 featured trip stamps**
  (curated order Whitney → Maine → Vancouver → Snow Snake → Muggy → Jay Peak → Whaleback) + a
  **4-chip brief-stops row** (NYC, Baldface, Mt Washington, San Jacinto). Each stamp = a dark-inset
  `<canvas>` thumbnail: real signature-activity GPS colored by **terrain grade** (green descent /
  slate flat / red climb from `grade_pct`) + a violet `altitude_m` elevation profile; server-side
  region overline / caption (athlete title) / live date-span + sport-tags; badges **Highest point ·
  14,507 ft** (Whitney), **Easternmost · 70.2°W** (Maine), **Northernmost · 49.3°N** (Vancouver —
  NOT Maine). Header meta live: **7 trips · 7 states & 1 province**. Hover reveals ↗; click →
  `placesFlyTo(fly-box)` + smooth-scroll to hero.
- **Peaks** (`chart_places_peaks`): 6-row record book — Highest 14,507 ft (Whitney) · Northernmost
  49.3°N (Vancouver) · **Home-adjacent giant 10,800 ft (San Jacinto — Wrinkle B, missed by
  clustering)** · Easternmost 70.2°W (Maine) · First in San Diego (live earliest SD act, *Time zone
  shakeout*) · Longest climb 6,752 ft (Whitney). Each row: big mono value, slate overline, title,
  violet altitude sparkline, lat/lng, click → `placesFlyTo`.
- **Trip clustering** = time-gap-away-from-home (`_away_clusters`, gap > 5 days; Wrinkle A keeps the
  roaming Seattle→Vancouver trip as one). Curated editorial copy matched to live clusters by unique
  title substring `sig`; unmatched multi-day clusters degrade to auto-featured (graceful).
- **Geometry loader** `_load_trip_geo` reads only the ~11 signature/peak streams (not all 344),
  RDP+cap-120, emits numeric `path`/`grade`/`elev` + a `fly` box. **XSS:** the `PC` payload is
  numeric-only keyed by opaque slot; every display string is rendered server-side and `_html_escape`d
  (now also escapes `"`/`'` because titles land in `aria-label` attributes).
- Review gate: `/code-review high` → fixed 2 findings (aria-label quote-escaping; dropped a
  new `#86efac` hex → `#4ade80`). QA: Playwright geometry pass (desktop+mobile × light+dark) — 7
  stamps / 4 chips / 6 peaks, all canvases inked, 0 body h-overflow, click-to-fly fires.

### What's live (Pass A + B)
- Nav tab **Places** replaced the old **Map** (`chart_map()` retired). Section id `view-places`.
- **Hero** (`chart_places_hero`): bespoke `<canvas>` route-density map, all 324 GPS tracks, additive
  glow; View control (All / San Diego / Boston / Trips-as-lens) + Glow/Terrain basemap; cooperative
  pan/zoom; light-theme `multiply` composite; **column-aligned** to the 1100px content width with a
  **fullscreen ⛶ button**; on-canvas labels (homes show name+activity/era only — NO lat/lng; trip
  "destinations" keep their detail line). Exposes **`window.placesFlyTo(target)`** (see contract below).
- **Two Homes** (`chart_places_homes`): two equal glass cards below the hero; dark-committed heatmap
  thumbnails (dense-core p1..p99 box, cover-fit, centered on density median); live 3-line mono stats.

### Established conventions (KEEP for Pass C)
- **All code lives in `strava-data/dashboard/charts_places.py`.** Builders return **raw
  HTML/`<canvas>`/JS strings** (the `chart_calendar()` precedent), NOT `go.Figure`. stdlib + numpy
  only, NO pandas. ASCII-only in every Python `print()` (use `_ascii()` for user text).
- **Live stats, not frozen:** counts/miles/segment winners are computed at build time from the data
  (so the fetch cron can't leave them stale), with a soft `[places] NOTE:` on drift — never a hard
  assert that could break the deploy build.
- **Injected-JSON XSS rule (IMPORTANT):** anything spliced into a `<script>` via `json.dumps` must
  carry ONLY the fields the JS reads — never third-party strings (segment names, activity titles).
  `json.dumps` does not escape `<`/`/`. Display strings are rendered server-side into HTML and
  `_html_escape`d there. Pass C's passport uses the athlete's activity TITLES — apply the same rule.
- **No new palette hex.** Reuse config tokens: teal `#2dd4bf` (Run/TrailRun), amber `#f59e0b` (MTB),
  violet `#a78bfa` (`ELEVATION_COLOR`/trail-ski), green `#4ade80` (`HIKE_COLOR`), slate `#8b949e`.
  Terrain gradient (Pass C) = green `#4ade80` / slate `#8b949e` / red `#f87171` (`SLOWER`).
- **Streams parse once:** use the memoized `_places_tracks(rows)` (caches `_load_tracks`). Home boxes
  `_SD_BOX`/`_BOS_BOX`; projection = equirectangular + `COSLAT=0.7551`; helpers `_uv`, `_metro_frame`,
  `_in_box`, `_bucket`.

### `window.placesFlyTo(target)` contract (built in Pass A — Pass C calls it)
`target` is `'all' | 'sd' | 'bos'` OR a box `{lat0, lat1, lng0, lng1}` (south, north, west, east).
Tweens the hero camera there, clears the Trips lens, and syncs the View buttons. **Pass C's passport
stamps and peaks rows call this** for click-to-fly-into-hero (e.g. a stamp click →
`placesFlyTo({lat0,lat1,lng0,lng1})` of that trip). Register any new clickable chart ids as needed.

---

## Pass C — Passport (Module 3) + Peaks (Module 4)  ← ✅ DONE (recipe preserved for reference)

Modules 3–4 share the trip/superlative precompute, so they land together. Full contracts in
`Specs/strava-data/places-prespec.md` §6 Modules 3–4 and `Plans/strava-data/places-plan.md` Pass C. Second build-ready mock exists:
**`Specs/strava-data/mocks/places-passport-mock.html`** (near-production; port its HTML/CSS/JS, swap seeded
data for real). No mock for peaks (reuse the passport's canvas elevation-profile code).

### Analyze (Opus) — the analytical heart. Pin:
- **Trip-clustering** by *time-gap-while-away-from-home* (pre-spec Wrinkle A: a roaming trip like
  Vancouver splits by geography, so cluster on time not place). Recover the anchors: **Whitney/Sierra
  4-day (2025-09-29→10-02, summit 14,507 ft)** and **Maine hut ski 3-day nordic×3 (2025-02-07→09)**,
  plus the ~14 auto-detected trips (Jay Peak, Michigan, Vancouver, Mt Washington, etc.).
- **Per-trip terrain-gradient path** from `grade_pct` (descent→green / flat→slate / climb→red) and
  **elevation profile** from `altitude_m`, for the passport thumbnails.
- **Superlative badges (D1)** on featured stamps; **peaks record book** ~5–6 rows.
- Emit a precomputed **trips + superlatives** structure the builders render from.

### PINNED CORRECTIONS from Pass A Analyze (do NOT re-derive wrong):
- **Highest point = Whitney 14,507 ft.**
- **San Jacinto = 10,800 ft** — a home-adjacent giant that trip-clustering MISSES (it's a same-day
  out-and-back near the SD box, so no multi-day trip forms). The **peaks reel** catches it; the
  passport does not (pre-spec Wrinkle B). Two different lenses by design.
- 🔴 **Northernmost = Vancouver / Stanley Park 49.29°N — NOT Maine 45.2°N.** The plan/pre-spec's
  "Northernmost · Maine" badge is FACTUALLY WRONG. The hero already ships the corrected
  `49.3°N · northernmost` on the Vancouver label. Pass C peaks must use Vancouver, not Maine.

### Build (Sonnet): port the passport mock (filmstrip: scroll-snap, drag-to-scroll, edge-fade,
hover-lift, badges, brief-stops chips), swap seeded squiggles for real path + `grade_pct` coloring +
`altitude_m` profile; captions = the athlete's own activity **titles** (city/state/country CSV cols
are EMPTY — use titles). Then the peaks record book (reuse the passport's canvas elevation sparkline;
click → `placesFlyTo`). Then QA (Sonnet) + Review gate (Opus) + commit.

---

## Tooling notes
- **Build:** `uv run python strava-data/build_dashboard.py` (use `uv run` — bare `python` is Py2 here).
  Regenerates `running-log/strava.html`; watch for `[places]` console lines.
- **Screenshot verify (works despite the Preview-MCP/CDN caveat):** the QA agent's Preview MCP and
  `cdn.plot.ly` are blocked in this environment, but the Places canvases are bespoke (no Plotly), so
  Playwright with the **pre-installed Chromium** works. Pattern (see scratchpad `verify_*.py` if this
  session's scratch survives, else rebuild it): in-process `127.0.0.1` http.server over `running-log/`
  + `uv run --with playwright python`, launch
  `chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")`, goto
  `strava.html#places`. **Measure element geometry (getBoundingClientRect), don't just eyeball** — the
  Pass B mobile card-collapse bug was invisible in a screenshot but obvious in a height measurement.
- **Analyst EDA scratch:** Pass A/B reproducible scripts were in the session scratchpad
  (`eda*.py`, `passA-recipe.md`, `passB-spec-section.md`); regenerate via the analyst if gone.
- **Pinned numbers reference:** hero counts 155 SD / 137 Boston / 319 mapped / 28 regions / 9 states &
  provinces; homes 782 mi SD / 529 mi Boston; segments "Canyon entrance via Salix" ×34 /
  "Cataldo East" ×20.

## Git / ops
- Commit trailers required: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` +
  `Claude-Session: <url>`. Do NOT put the model id in commits/PRs/code — chat only.
- Push: `git push -u origin claude/strava-places-plan-v9oxb3` (retry w/ backoff on network error).
- Do NOT open a PR unless asked.
