# Places — 3D Terrain Feature — Session Handoff

**Purpose:** resume debugging a recurrence of the "requires two clicks" bug in a fresh
session. Read this first, then `strava-data/dashboard/charts_places.py` — everything
relevant lives inside `_HERO_TEMPLATE`'s inline `<script>` (roughly lines 1063–1660).

**Branch:** `main` (all work this session was committed and pushed directly to `main`,
no feature branch). **Status:** feature complete and deployed; one bug reported as
recurring (see "The bug to debug" below) — not yet reproduced or root-caused in this
handoff.

**Live site:** `https://ducktapegirl.github.io/distance-nerd-stuff/strava.html` — the
Places tab, `#places?a=<id>&b=terrain` deep-links, or just click "3D Terrain" in the
Map button row.

---

## What was built this session

Added a real 3D terrain view to the Places hero (previously "Terrain" was just a flat
MapTiler style, no actual elevation/pitch). Landed across 8 commits on `main`:

| Commit | What |
|---|---|
| `a7da9b8` | Initial feature: raster-dem terrain source, pitched camera, native MapLibre GL route line, scoped to single-activity deep links only |
| `ecfa599` | Unrelated: matched the dashboard title font size to the Running Log page |
| `4126db2` | **Fixed "requires two clicks to appear"** — see full diagnosis below, this is the bug now recurring |
| `d2b2fba` | Fixed a duplicate route line (old 2D canvas overlay + new GL layer both drawing the same track) and made the route color match the activity's sport (not a fixed accent color) |
| `644cd12` | Swapped MapTiler's stock `outdoor-v4` style for the user's own custom MapTiler Cloud styles (light + dark variants) |
| `97addbf` | Fixed multi-day curated trips (e.g. "Maine Hut Trail — Days 1–3") only showing one day's route |
| `24a49be` | **Latest change**: made 3D Terrain a full peer of Overview/Street, selectable on all Places views (not just single-activity) — previously the button was hidden and force-reset outside a deep link |
| `8f54147` | Session log entry in `Claude's Log.md` |

### Architecture as it stands today

- One shared MapLibre GL JS map (`map`, `initMap()` around line 1178) powers the whole
  Places hero — the aggregate multi-activity overview *and* single-activity deep links.
- Three basemap modes: `glow` (default, tile-free "BackgroundGhost" look), `street`,
  `terrain`. `styleForMode(m)` (line 1154) resolves each to a MapTiler style URL.
  `terrain`'s light/dark styles are the user's own custom MapTiler Cloud styles:
  - Light: `019fe2f9-32eb-7c1c-856d-ed5499e401cd` ("Outdoor-NoMarkings")
  - Dark: `019fe30f-cd64-7835-afd2-56ffea88cc0f` ("Outdoor-NoMarkings-Dask" — user's
    own typo in the title, left as-is since it's just a label)
- `applyTerrainState()` (line 1216) is the terrain state machine: adds a `raster-dem`
  source + `setTerrain()` + pitches the camera to 60° whenever `mode==='terrain'`
  (as of `24a49be`, no longer requires an activity to be selected). If an activity
  *is* selected (`curActivity` truthy), it also builds a GeoJSON `LineString` (single
  day) or `MultiLineString` (multi-day trip, from `window.placesRouteDays`) route line
  in the activity's sport color, on top of the terrain.
- The old 2D canvas "glow" overlay (`drawGlow()`) still draws the aggregate cloud of
  every activity's route — but skips its own route-drawing pass entirely whenever
  `curActivity` is set, since the GL layer now owns that (see `d2b2fba`).
- `enterActivity(id)` / `exitActivityMode()` (lines 1546 / 1559) manage `curActivity`.
  Selecting an activity defaults the mode to `terrain` if it wasn't already
  `street`/`terrain`. Leaving an activity (a View button click) no longer forces the
  mode back to `glow` (that reset was removed in `24a49be`) — mode now persists like
  Street/Overview always did, and `applyTerrainState()` just drops the stale route
  layer if terrain stays active with no activity selected.

---

## The bug to debug: "specific activities require two clicks to zoom in" (recurring)

**User's report, verbatim:** *"a similar 'specific activities require two clicks to
zoom in' bug that we fixed in commit 4126db2... It's happening again."*

### What `4126db2` diagnosed and fixed (full detail, since the same class of bug may be back)

Three sequential root causes were found and fixed in that commit, all inside
`applyTerrainState()`'s interaction with `map.setStyle()`:

1. **`setStyle()` while a raster-dem terrain source was active crashed MapLibre's
   internal style-diff** (`AbortError`, `"_checkLoaded"` warning). Fixed by manually
   stripping the terrain source/route layer before every `setStyle()` call
   (`applyMapStyle()`, line 1161).
2. **The retry mechanism was wired to MapLibre's `'style.load'` event**, which —
   confirmed via direct raw-event tracing (registering a listener on every MapLibre
   event and logging with timestamps) — **does not reliably fire for `setStyle()`
   calls after the map's initial load**, despite MapTiler's own official docs using
   exactly that pattern for adding terrain. Switched the retry listener to `'idle'`
   (fires once the map has fully settled, including all sources) — confirmed reliable
   across every test at the time.
3. **Even with `'idle'` as the retry, a genuinely fresh click could still fail**: the
   *synchronous* call to add terrain right after triggering a style change ran before
   the new style had finished loading — `addSource()`/`setTerrain()` throw in that
   state, silently aborting before pitch/route setup ran, with no console error. Fixed
   by restoring an `isStyleLoaded()` guard on the terrain-adding path (`applyTerrainState()`,
   line ~1225 today) — safe *only* because `'idle'` (not `'style.load'`) provides the
   actual reliable retry.

That third fix is what shipped as "the fix" for the two-clicks symptom. **This exact
guard is still in place today** (verified before writing this handoff) — the
`24a49be` change (terrain-on-all-views) did not touch `applyTerrainState()`'s
`isStyleLoaded()` guard or the `'idle'` listener at all, only the `want` condition
(dropped the `curActivity` requirement) and what happens when there's no route to draw.

### Why it might be back — untested hypotheses for the new session

**The user's wording is "zoom in," not "3D doesn't appear."** The original bug was
about the *terrain/pitch* failing to appear (camera was already correctly positioned,
just flat). "Two clicks to zoom in" could describe the same underlying symptom
described loosely, or a **genuinely different bug in the camera positioning itself**.
Worth distinguishing early via a debug hook (see Methodology below): on a slow first
click, does `map.getCenter()`/`getZoom()` already match the target activity's bounds
(camera is fine, only terrain/pitch is stalled — the known/original bug), or is the
camera *also* not at the target (a new bug)?

One concrete hypothesis for a **new** camera-specific bug, not yet tested: the
passport/peaks card click handlers (`charts_places.py:2483-2484` and `:2623-2624`)
call `window.placesFlyTo(d.fly)` (triggers an animated `map.fitBounds()`, 620ms
duration) *immediately followed by* `window.placesLinkActivity(d.id)` →
`enterActivity(id)`, which — if the mode wasn't already `street`/`terrain` — calls
`applyMapStyle()` → `map.setStyle()` a few milliseconds later, in the same tick.
**Untested: does calling `setStyle()` shortly after `fitBounds()` was triggered
interrupt/cancel the in-flight camera animation**, leaving the camera short of its
target on the first click? A second click, with mode now already `terrain` (so
`enterActivity()` skips `applyMapStyle()` entirely), wouldn't have anything to
interrupt the second `fitBounds()` call, and would land correctly — consistent with
"needs a second click."

If true, this would explain "specific activities": before `24a49be`, *every* fresh
activity click reset mode to `glow` on the way out (via the old `exitActivityMode()`
force-reset), so *every* activity click was a fresh `glow`→`terrain` transition,
always triggering `setStyle()`. Now that terrain mode persists across View-button
switches, only the *first* activity clicked after boot (or after manually switching
away and back) actually triggers a style change — most subsequent activity clicks
skip `applyMapStyle()` entirely and go straight to `applyTerrainState()`. So the
failure mode may not be about *which* activities, but about *whichever activity
happens to be clicked while a style transition is also in flight* — worth checking
with the user whether "specific activities" really means the same ones fail
every time, or just whichever one they happened to click first in a session.

**Do not assume either hypothesis is correct without reproducing it.** Use the
methodology below — it's what actually found all three root causes last time,
whereas guessing from first principles produced two wrong fixes in a row before the
raw event tracing found the real answer.

---

## Debugging methodology that worked (reuse this)

1. **Temporary debug hook pattern.** Add `window.__DEBUG_placesMap = map;` right after
   `map = new maplibregl.Map({...})` in `initMap()` (line ~1188), rebuild, and drive
   the page via `mcp__Claude_Browser__javascript_tool` calling
   `window.__DEBUG_placesMap.getPitch()/getTerrain()/getSource()/getLayer()/getCenter()/
   getZoom()/isStyleLoaded()` etc. **Always remove the hook before the final commit**
   (`grep -c "__DEBUG" strava-data/dashboard/charts_places.py` should be 0).
2. **Raw event tracing is what actually found the `'style.load'` unreliability.**
   Don't trust a library's documented "recommended pattern" under your app's specific
   call sequence — register listeners on every candidate MapLibre event
   (`'style.load'`, `'styledata'`, `'sourcedata'`, `'idle'`, `'error'`) with
   `Date.now()` timestamps pushed into a `window.__DEBUG_terrainLog` array, then
   trigger the interaction once and read the log. This found the real firing order in
   one pass after two wrong fixes based on reasoning alone.
3. **A single successful test looks identical to a flaky one.** Test repeat
   interactions (multiple fresh clicks, activity switches, theme toggles) in
   **multiple genuinely fresh browser tabs** — a fix that works once in a warm/cached
   tab can fail non-deterministically on a cold one. `tabs_create` for a new tab (or a
   hard cache-busting query string + `force: true` on `navigate` if the tab cap is
   hit) each time you want a clean test.
4. **The Browser pane tool's console-message buffer persists across many
   `navigate()` calls in a reused tab.** An `AbortError`/`"_checkLoaded"` warning
   observed mid-session may be leftover from an *earlier* test, not a live symptom of
   the current page state. Confirmed by testing in a brand-new tab (zero console
   messages on load) after wrongly attributing it to "every page load." Don't
   diagnose from a reused tab's console history — open a fresh tab, or at minimum
   note the exact click→check sequence and treat old entries with suspicion.
5. **Direct `curl`/sandbox fetches to `api.maptiler.com` with the key return "Key
   usage restricted"** — the `MAPTILER_KEY` in `strava-data/.env` is domain-restricted
   to `ducktapegirl.github.io`. It worked fine all session from the local dev server
   (`127.0.0.1:8765`) through the Browser pane, so local testing is not blocked — only
   raw out-of-browser fetches (e.g. `curl`, or `WebFetch`) are. If you need to fetch a
   MapTiler URL directly (not through the rendered page), do it via
   `javascript_tool`'s `fetch()` from a tab that's navigated to the *live* deployed
   site, where the referrer genuinely matches.

---

## Decisions made this session (context for anything that looks like a deliberate choice)

- **Explicit source/layer teardown before every `setStyle()`**, not relying on
  MapLibre's own style-diff to clean up — logs a benign "rebuild style from scratch"
  console warning but was empirically the *reliable* option; a "cleaner" version that
  let the diff handle removal passed once then failed non-deterministically on
  identical retests. Don't "clean this up" without re-running the same repeat-click
  stress test that caught the regression.
- **Multi-day trips render as one route color** (the trip's single signature
  activity's sport color), not per-day sport-matched segments — user's explicit
  choice, made when told that one curated trip (Stanley Park) genuinely mixes a bike
  ride and a run. Per-day coloring would need a `FeatureCollection` of per-day
  features + a MapLibre `match` paint expression instead of today's flat
  `line-color`; scoped out as a possible future follow-up, not started.
- **Multi-day route geometry is filtered by the trip's own curated name substring**
  (`spec["sig"]`), not the whole activity cluster — `_away_clusters()`'s 5-day-gap
  rule merges unrelated legs into one cluster (confirmed: the "Stanley Park" cluster
  also contains an unrelated Bellevue/Seattle/Nanaimo leg from the same trip). This
  was caught by a Plan-mode validation subagent before any code was written, not
  during testing — worth continuing to route non-trivial fixes through that
  validation step even when a fix looks obvious.
- **3D Terrain is now unrestricted (this session's final change, `24a49be`)** — user
  explicitly reversed the original single-activity-only design. If the recurring bug
  turns out to be caused by this change, that's a real regression to fix, not a
  reason to revert the feature (user wants it available everywhere).

---

## Outstanding questions for the user (ask before/while investigating)

1. When you say "two clicks to zoom in" — on the first click, does the camera pan to
   roughly the right area but stay flat/2D, or does it not move much at all?
2. Is this the *same specific activities* failing every time, or does it seem to be
   "whichever one I click first" in a session? (Bears directly on the fitBounds/
   setStyle-interruption hypothesis above.)
3. Reproducing on the live deployed site, or locally? Slow connection, or does it
   happen on a fast one too?
4. Does switching to Overview/Street and back to Terrain make it happen again on the
   next activity click, or only right after a fresh page load?

---

## Relevant project context

- Build: `uv run python strava-data/build_dashboard.py` (writes `running-log/strava.html`,
  gitignored, never commit it).
- Local preview: `uv run python -m http.server 8765 --directory running-log`, then
  browse `http://127.0.0.1:8765/strava.html` (use `127.0.0.1`, not `localhost`, for
  MapTiler key restrictions to resolve correctly relative to the deployed domain's
  behavior — though note the key itself is restricted to the *production* domain, not
  localhost; local testing still works because MapTiler's restriction is
  referrer-based and permissive enough in practice, but don't be surprised if you
  need to double check `TILES_OK` locally per point 5 in the Methodology section).
- The whole feature lives in one file: `strava-data/dashboard/charts_places.py`. Two
  Python data-prep functions (`_passport_data()`, `_peaks_data()`, ~lines 1990-2090)
  feed three JS templates (`_HERO_TEMPLATE`, `_PASSPORT_TEMPLATE`, `_PEAKS_TEMPLATE`)
  via `window.placesFlyTargets` / `placesRouteCoords` / `placesRouteColorIdx` /
  `placesRouteDays` globals published from the passport/peaks scripts and consumed by
  the hero's `applyTerrainState()`.
- MapLibre GL JS version pinned: `4.7.1` (via unpkg CDN, `strava-data/dashboard/config.py`).
  Not the MapTiler SDK JS — plain MapLibre + MapTiler-hosted style JSON URLs.
- The user has pasted their live (but domain-restricted) MapTiler key into chat twice
  this session. Flagged both times; user confirmed they understand it's already
  public in the deployed page's source (client-side keys are inherently visible) and
  chose not to rotate it. No action needed unless they ask.

---

## Suggested prompt to start the next session

> Read `Project Docs/Handoffs/strava-data/places-3d-terrain-handoff.md` for full
> context, then help me debug a recurrence of the "requires two clicks" bug in the
> Places 3D Terrain view (originally fixed in commit `4126db2`, now happening again
> for specific activities). Use the debug-hook + raw-event-tracing methodology
> described in the handoff rather than guessing from first principles — that's what
> found the real root causes last time.
