# Places — 3D Terrain Feature — Session Handoff

**Purpose:** resume debugging a recurrence of the "requires two clicks" bug in a fresh
session. Read this first, then `strava-data/dashboard/charts_places.py` — everything
relevant lives inside `_HERO_TEMPLATE`'s inline `<script>` (roughly lines 1063–1660).

**Branch:** `main` (all work this session was committed and pushed directly to `main`,
no feature branch). **Status:** feature complete and deployed. The reported "two
clicks to zoom in" bug was reproduced, root-caused and fixed on 8 Aug 2026 — see
"RESOLVED" below. It was **not** a recurrence of `4126db2`.

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

## RESOLVED (8 Aug 2026): "two clicks to zoom in" was a *different* bug

**Status: root-caused, fixed, and verified.** It was not a recurrence of `4126db2`.
That one was *terrain/pitch missing with the camera correct*; this one was the
mirror image — *terrain and pitch correct, camera never moved*.

### Root cause

**`map.setStyle()` called while a camera animation is in flight permanently
destroys that animation.** MapLibre stops feeding the ease render frames: it never
completes, never fires `moveend`/`idle`, and the map sits at `isMoving() === true`
forever, stranded at a partial zoom. Everything hanging off `'idle'` — including
the terrain retry — is dead behind it.

The first click on a passport/peak card ran this sequence (measured, not inferred):

```
t=0    fitBounds -> flyTo{zoom:10.468, duration:620}   camera at z=3.546, p=0  [movestart]
t=8    setStyle                        via applyMapStyle <- enterActivity
t=9    setTerrain                      via applyTerrainState <- enterActivity
t=13   easeTo{pitch:60, duration:700}  via applyTerrainState <- enterActivity
t=13   zoomend + moveend at z=3.546    <- the 620ms fly is killed 13ms in
t=877  pitchend  p=60, z=3.546         <- pitched 3D terrain over the whole US
```

Two agents, in sequence:

1. `applyTerrainState()`'s `easeTo({pitch:60})` calls `stop()` internally, killing
   the fly **13 ms into a 620 ms animation**.
2. Underneath that, `setStyle()` at t=8 had *already* doomed the fly. Removing only
   the `easeTo` made things **worse**, not better — the fly then froze permanently
   (`isMoving()` still true at t=9000, no events at all after t=883, terrain wiped).
   The `easeTo`'s `stop()` was accidentally *rescuing* the wedged camera into a
   consistent — if wrongly framed — state.

**Why only the first click, and why "whichever I click first":** `enterActivity()`
calls `applyMapStyle()` only when `mode` isn't already `street`/`terrain`. Since
`24a49be` removed the force-reset to `glow` on exit, `mode` sticks at `terrain`
after the first card click, and the basemap **button** handler sets `mode` itself —
so a manual Overview→Terrain round-trip doesn't re-arm it either. Exactly one click
per page load takes the style-swap path. Nothing to do with *which* activity.

### The fix (in `charts_places.py`, all inside `_HERO_TEMPLATE`)

- `applyMapStyle()` calls `map.stop()` before `setStyle()`, so no ease is ever left
  wedged, and sets a `styleSwapping` flag.
- New `onStyleSettled(fn)` arms `'style.load'` **and** `'idle'` (first wins) plus a
  re-checking timeout, because neither event is dependable alone here.
- New `frameBounds(bounds, padding, animate)` — the single funnel for every framing
  move (`goFrame`, `placesFlyTo`, `enterActivity`). It defers the move while a style
  swap is in flight and replays it afterwards, and **bakes `TERRAIN_PITCH` into the
  `fitBounds` itself** so terrain never needs a second camera animation.
- `applyTerrainState()` only eases pitch when no framing move owns the camera.

Two traps worth remembering, both of which produced a wrong intermediate fix:

- **`isStyleLoaded()` still returns `true` for a moment after `setStyle()`** (visible
  at t=8→t=9 above), so it cannot detect "swap in flight." That's what `styleSwapping`
  is for. A first attempt gated `frameBounds` on `isStyleLoaded()` and failed 3/3.
- **Conversely, don't gate on `isStyleLoaded()` in the steady state:** terrain DEM
  tiles keep it `false` most of the time, so gating there deferred every routine fly
  by seconds, and a stale held move later replayed with the wrong pitch.

### Verification

`tools/mobile_preview.py` (transport T2), fresh page load per trial:

- First-click framing: **3/3 PASS** on the live site (simulated fix) and **3/3** on
  the local build — settles at `z=11.459`, the exact `cameraForBounds()` target,
  `pitch=60`, terrain + route present, not stuck.
- 9-step regression sweep (activity→activity, Overview/Street/Terrain switching,
  View button, multi-day trip, theme toggle): **9/9 PASS on the fixed build; the
  pre-fix build fails only step A** (`z=3.546`, centre outside the activity box) with
  every other step identical — a clean controlled comparison.
- Both deep-link forms (`?a=<id>&b=terrain` and `?a=<id>`): PASS.
- Mobile 375×812 first click: PASS.
- `running-log/qa.py`: 13/13.

### Original report (for context)

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

0. **Check the transport can actually run animations before trusting it.** In the
   Aug 2026 session the Browser pane tool was structurally unusable for this bug:
   its tab reports `document.visibilityState === "hidden"` and delivers **zero**
   `requestAnimationFrame` callbacks and **zero** `ResizeObserver` callbacks. The
   Places map is created lazily *by* a ResizeObserver and its camera eases are
   rAF-driven, so the map never even constructed there (`#places-map` had no
   children, `maplibregl.Map` was never called) — which reads exactly like a page
   bug if you don't probe. **Use `tools/mobile_preview.py` (transport T2) for any
   map/camera/animation work**; it reports `visible` with rAF and RO both firing,
   takes `--url` for the live site, and `--eval @file` returns a `Promise`, so a
   whole install-tracer → click → wait → dump experiment fits in one call. Two
   gotchas: `--hash` prepends its own `#` (pass `places`, not `#places`), and Git
   Bash rewrites `--page /strava.html` into a Windows path unless you set
   `MSYS_NO_PATHCONV=1`.

1. **Temporary debug hook pattern.** Add `window.__DEBUG_placesMap = map;` right after
   `map = new maplibregl.Map({...})` in `initMap()` (line ~1188), rebuild, and drive
   the page via `mcp__Claude_Browser__javascript_tool` calling
   `window.__DEBUG_placesMap.getPitch()/getTerrain()/getSource()/getLayer()/getCenter()/
   getZoom()/isStyleLoaded()` etc. **Always remove the hook before the final commit**
   (`grep -c "__DEBUG" strava-data/dashboard/charts_places.py` should be 0).
2. **Raw event tracing is what actually found the `'style.load'` unreliability.**
   (Caveat added Aug 2026: in the T2 traces `'style.load'` *did* fire after every
   `setStyle()`, once, at ~820–1550 ms. So treat "style.load never fires" as
   environment- or sequence-dependent rather than absolute — `onStyleSettled()`
   now arms `'style.load'`, `'idle'` and a timeout together instead of betting on
   any one of them.)
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
- **3D Terrain is now unrestricted (`24a49be`)** — user explicitly reversed the
  original single-activity-only design; it stays that way. For the record, the
  "two clicks" bug was **not** caused by `24a49be`: the underlying
  setStyle-kills-the-camera race lives in `enterActivity()`/`applyMapStyle()` and
  predates it. What `24a49be` changed is *how often* it fires — by letting `mode`
  persist as `terrain`, it reduced the style-swap path from potentially every
  activity click to just the first one per page load, which is why the symptom
  presented as "whichever I click first."

---

## Questions that were asked, and the answers (8 Aug 2026)

These four answers are what collapsed the search space to a single code path before
any instrumentation ran — worth asking first in any similar investigation.

1. *First-click behaviour?* — "Navigates me back to the map and changes to the 3D
   Terrain view, but **doesn't zoom in enough**." (Ruled out a `4126db2` recurrence
   immediately: terrain was fine, the camera was not.)
2. *Same activities each time?* — "**Whichever I click first.**"
3. *Where?* — the **live deployed site**.
4. *Does Overview/Street → Terrain re-arm it?* — "**Only after a fresh page load.**"

2 + 4 together pin it to `enterActivity()`'s `applyMapStyle()` branch, which runs on
exactly one click per page load. See RESOLVED above.

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

## Where this stands

The "two clicks to zoom in" bug is fixed and verified (see RESOLVED above); no
open bug is outstanding on this feature. Possible follow-ups, none started:

- **Perceived delay on the first activity click.** The framing move is now held
  until the new style reports in, ~1.8 s after the click on the live site, so the
  camera sits still and then flies. Correct, but a loading affordance or a shorter
  hold (e.g. framing on `style.load` for the *base* style before DEM tiles) would
  feel better.
- **The `AbortError: signal is aborted without reason`** from
  `Style._remove` ← `Map._updateStyle` still appears once per style swap. It is
  benign here (it predates this fix and did not cause the camera bug) but it has
  never been chased down.
- **Per-day route colouring for multi-day trips** — scoped out by the user, see
  Decisions above.
