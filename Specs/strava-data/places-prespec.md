# Places — Geography Keepsake · Pre-Spec

**Status:** PRE-SPEC (concept + design direction, brainstormed 2026-07-13). **Not build-ready.**
This is the input to a future `/strava` pipeline run — the Analyze/Design stages should verify the
data recipes and turn the module contracts below into a build-ready spec in `dashboard-spec.md`
before any `strava-developer` work.

**Interactive design mocks** (illustrative routes; aesthetic + layout reference, not exact GPS):
- Hero map — https://claude.ai/code/artifact/22a27be0-2cec-4bc0-8346-e6d24f5adcb2
- Passport filmstrip — https://claude.ai/code/artifact/9c1d2929-9028-4171-abea-c844759554e5

---

## 1. The idea in one line

Turn the Strava dashboard's thin **Map** tab (start-point dots on a San-Diego-locked view) into a
**"Places"** section: a neutral, story-first keepsake of *where a life in motion has happened* —
built on the 344 GPS **stream** files the current map ignores entirely.

**Tone: neutral keepsake.** Emphasis on the visual and the memory, not analysis or achievement.
State facts quietly; let the map speak. Not a stats page, not a highlight reel.

## 2. Why now / what's being wasted

- The current `chart_map()` (`dashboard/charts_production.py`) plots **one dot per activity at its
  start point**, on a map hard-centered on San Diego (`MAP_CENTER_LAT/LON` in `config.py`) at
  zoom 11. Consequence: the athlete's **~136 Boston-area activities are off-screen** at the default
  view, and routes are never shown.
- Meanwhile `data/streams/*.csv` holds **full GPS tracks for all 344 activities**
  (`t,lat,lng,distance_m,altitude_m,velocity_ms,heartrate,cadence,watts,temp_c,moving,grade_pct`).
  This is the richest data in the repo and the map uses none of it.

## 3. The athlete's real geography (verified 2026-07-13)

- **Two home bases:** San Diego (~145 activities, 2025–now) and Boston metro (~136, 2024–2025).
  The athlete **moved Boston → San Diego**; San Diego is home-now and growing (more events expected).
- **28 distinct regions**, ~319 activities with `start_latlng`.
- **Geography-rich sports beyond run/MTB:** alpine + nordic ski, hikes, rock climbing, snowboard,
  SUP, ice skating.
- **Trips are the emotional core.** Low-count places (1–5 activities) mark vacations and are
  disproportionately meaningful. Both anchor memories are **multi-day clusters away from home**:
  - **Whitney / Sierra** — 4-day expedition (2025-09-29 → 10-02): Cottonwood Lakes (10,130 ft) →
    **Mt. Whitney summit 14,507 ft via JMT** → Alabama Hills. Highest point by ~3,700 ft.
  - **Maine hut ski** — 3-day hut-to-hut nordic trip (2025-02-07 → 09, western Maine ~45.2°N).

## 4. Data feasibility (verified 2026-07-13)

- **Stream coverage: 344 / 344 activities have a stream file** → every route can be drawn as a real
  line, including **all 26 travel activities**. No "some trips won't render" problem.
- 25 activities lack `start_latlng` (indoor/manual: weights, Pilates) — correctly excluded from the map.
- **Trip auto-detection works.** A naive "away-from-home + consecutive days" pass found ~14 trips and
  cleanly recovered both anchor memories (Whitney 4d/3act/14,507 ft; Maine 3d/nordic×3), plus Jay Peak,
  Michigan, Vancouver, Mt. Washington, etc.

### Two data wrinkles to design around (not blockers)

- **Wrinkle A — a roaming trip splits by geography.** The Vancouver trip broke into two clusters
  (Nanaimo island vs. Stanley Park, ~30 mi apart). **Fix:** cluster primarily on *time-gap-while-
  away-from-home*, treat geography loosely. A trip is "a stretch of days I wasn't home," not "a spot."
- **Wrinkle B — a big day-trip near home hides from trip-clustering.** The **10,800 ft Mt. San Jacinto
  hike** sits *inside* the San Diego home box, so trip-detection never sees it. This is why the
  **passport and the peaks reel are two different lenses**: passport catches *trips*, peaks catches
  *superlatives wherever they happened*. Together they miss nothing.

## 5. Section structure (top → bottom)

New nav tab **"Places"** that **replaces** the existing "Map" tab (retire `chart_map()`'s start-dots
view; change the nav tuple `("map","Map")` → `("places","Places")`). One geography home, no redundancy.

The section has deliberate **rhythm**: an immersive full-bleed hero at the top, then intimate glass
cards below. Cinematic → tender → reflective.

1. **The whole map (hero)** — real GPS routes, both coasts equal, glowing where repeated.
2. **Two homes** — Boston & San Diego as equal twin heatmaps.
3. **The passport** — trips as a filmstrip of stamps, captioned in the athlete's own titles.
4. **The peaks** — a restrained ~5–6-item captioned record book.
5. **(Future)** exploration / tile-completion game — parked; builds on the hero's heatmap plumbing.

---

## 6. Module contracts

### Module 1 — The whole map (hero)

- **Full-bleed**, breaks out of the `.card` grid for impact. Immersive height (~100svh feel).
- **Routes, not dots:** each activity a thin polyline (~1px, low opacity) from its stream, colored by
  sport. Overlapping repeats brighten via additive blending → a personal heatmap falls out for free.
- **Basemap = dark glow by default** (`carto-darkmatter`-style dark tiles + neon routes) with a
  **Glow ↔ Terrain toggle**; Terrain swaps to a shaded-relief basemap so mountains show through
  (pairs with the peaks module). In light page theme, dark-glow may swap to a light basemap — the map
  is theme-aware even though the mock committed to dark.
- **Both coasts by default:** open fit-to-all-bounds so San Diego + Boston are both visible as two
  glowing clusters, trips as faint sparks between.
- **Two control rows** (reuse the existing `.seg-filter`/`.seg-btn` component):
  - **View:** `All · San Diego · Boston · Trips`. San Diego / Boston zoom to that metro.
    **`Trips` is a HIGHLIGHT LENS, not a zoom** — it dims the two home glows and brightens every trip
    spark, staying wide (a single zoom can't frame coast-to-coast trips, and per-trip buttons don't
    scale). Drill-down to a *specific* trip happens from the passport, not here.
  - **Map:** `Glow · Terrain` (basemap style).
- **Free pan & zoom always available** (native to the tile map); the buttons only shortcut to nice
  framings, they never replace manual navigation.
- **Neutral framing, no tagline.** Earlier iterations had a "Home was Boston. Home is San Diego now."
  caption; **removed** — the labeled home glows carry the story without a sentence. Keep only a quiet
  "PLACES" eyebrow. (Tagline is one line to reinstate if ever wanted.)
- **Labels** on-map: the two homes always (name + coord + count, Geist Mono); key trips (Sierra, Maine,
  Vancouver) faintly always, others on zoom.
- **Base stat line** (mono): activities · regions · states & provinces. **Legend:** Running / MTB /
  Trail·ski / Hike.

**Division of labor (settled):** the **map is the overview**, the **passport is the drill-down**.
Map "Trips" = "light up all my adventures"; clicking a passport stamp = "fly me to *that* one."
Scales to any number of trips.

### Module 2 — Two homes

- Two **equal** glass cards side by side (stack on mobile). **Identical scale, zoom, and treatment** —
  neutrality enforced visually; not before/after, not vs. Each: a small dark heatmap thumbnail + a
  3-line mono stat block (miles · most-repeated loop/street · date range). Labels: **Boston**
  `2024–2025` / **San Diego** `2025–now`. No arrow.

### Module 3 — The passport (filmstrip)

- **Horizontal-scroll filmstrip** of stamps (scroll-snap; drag-to-scroll; edge-fade mask), weighted by
  meaning not volume.
- **Featured trips** = larger stamps. Each stamp:
  - **Route thumbnail** (dark inset mini-map) with the line **colored by terrain gradient**
    (`grade_pct`): **descent → green `#4ade80`, flat → slate `#8b949e`, climb → red `#f87171`** — all
    existing palette hues, no new constants. A faint **violet (`#a78bfa`) elevation profile** runs along
    the thumbnail bottom. Each trip's terrain *shape* differs (Whitney climbs hard to its peak; Michigan
    stays flat), which is the visual differentiator.
  - **Caption = the athlete's own activity title** ("Muggy in Michigan", "Maine Hut Trail — Days 1–3",
    "Jay Peak Spring Riding"). The `city/state/country` CSV columns are mostly empty, so use the titles —
    they're more charming than any reverse-geocoder.
  - **Region overline** (small-caps mono), **date span** (mono), **sport tags** (e.g. `nordic ski ×3`).
  - **Superlative badge** where earned (see decision D1): e.g. `Highest point · 14,507 ft` on Whitney,
    `Northernmost · 45.2°N` on Maine — ties the passport to the peaks reel.
  - **Hover** lifts the card and reveals "↗ view on map" — the click that flies the hero map to that trip.
- **Brief stops** = a quiet chip row beneath the strip for one-off travel days (Mt. Washington, Whaleback,
  Snow Snake, "Vacation Legs", Baldface). Nothing dropped, nothing overweighted.
- **Theme-aware** (normal in-page section): light + dark both designed; the **map thumbnails stay dark
  insets in both themes** (map panels are dark objects → they read as little windows).

### Module 4 — The peaks (record book)

- A **restrained ~5–6 rows** of genuinely singular moments (deliberate restraint — not a "fun facts"
  list). Each row: big mono superlative number (`14,507 ft`), a slate overline label (`HIGHEST POINT`),
  the athlete's activity title, a tiny **elevation-profile sparkline** from that activity's altitude
  stream (a little mountain silhouette), and lat/lng in mono. Click → hero map flies there.
- **Candidate beats:** Highest point (Whitney, 14,507 ft) · Northernmost (Maine huts ~45.2°N) · the two
  anchor trips · **first activity in San Diego** (the move, stated neutrally) · longest single climb.
- Catches home-adjacent giants that trip-clustering misses (e.g. San Jacinto 10,800 ft).

---

## 7. Design system (honor the existing dashboard)

Everything lives inside the current identity so it reads as *part* of the dashboard, not a microsite.

- **Palette (existing tokens only, from `dashboard/config.py`):** grounds `#0d1117`/`#161b22`; sport
  colors teal `#2dd4bf` (Running), amber `#f59e0b` (MTB), violet `#a78bfa` (Trail/elevation), green
  `#4ade80` (Hike); slate `#8b949e` / primary `#e6edf3` text; accent blue `#58a6ff`. Terrain gradient
  reuses green/slate/red (`#f87171` = existing `SLOWER`). **No new palette hex.**
- **Type:** Geist for display/labels, **Geist Mono for all numbers, coordinates, dates** (field-notebook
  voice). Falls back to a clean system stack (deliberately *not* Inter).
- **Theme:** the mid-page modules (2–4) are theme-aware light/dark via CSS custom properties, matching
  the dashboard's `applyChartTheme()` convention; the hero is dark-committed for the glow aesthetic but
  the production basemap remains theme-swappable.
- **Motion:** gentle — map fly-to on click, soft fade-in on scroll, hover lift on stamps. **No animated
  line-drawing** (tips into gimmick; wrong for a keepsake). Respect `prefers-reduced-motion`.
- **Display units policy still applies** (min/mi, mph, °F; metric data converted at display time).

## 8. Decisions locked (my judgment, per athlete's "trust your judgement")

- **D1 — Superlative badges live ON the featured stamps** (not only in the peaks reel). They tie the two
  modules together and give each stamp a reason-for-being; kept to trips that genuinely earn one.
- **D2 — Stamps stay tall & rich** (route thumbnail + full caption), not a dense contact-sheet. Suits the
  keepsake tone; the filmstrip's horizontal scroll absorbs the height cost.
- **D3 — Terrain-gradient thumbnails, kept.** Green→slate→red reads as terrain and adds real per-trip
  texture; preferred over a flat single-sport line. (If it ever reads noisy at build time, fall back to
  a single sport-colored line + the violet elevation profile alone.)

## 9. Out of scope / future

- **Exploration / tile-completion game** (VeloViewer-style street or tile completion for the home
  cities) — parked as future work; the hero's route/heatmap plumbing is the foundation it would build on.
- No new data files required — the streams already exist. Trip-clustering + superlatives are precomputed
  in Python at build time (stdlib + numpy only, per the dashboard's no-pandas rule).

## 10. Suggested pipeline hand-off

1. **Analyze** (`strava-data-analyst`): verify trip-clustering (time-gap-away-from-home recipe, Wrinkle A),
   stream-drawing feasibility/perf across 344 tracks, and the peaks/superlatives list (Wrinkle B); pin the
   numbers (Whitney 14,507 ft, San Jacinto 10,800 ft, home counts, region count).
2. **Design** (`strava-viz-design`): promote the module contracts above into `dashboard-spec.md`
   view specs (div ids, control contracts, hover/label rules, terrain-gradient color mapping).
3. **Build** (`strava-developer`): new builders in `dashboard/charts_production.py` (or a new
   `charts_places.py`), retire `chart_map()`, wire the `("places","Places")` nav + section HTML/JS.
4. **QA** (`strava-qa`): both themes, mobile, label overlap, edge clipping, units policy.
