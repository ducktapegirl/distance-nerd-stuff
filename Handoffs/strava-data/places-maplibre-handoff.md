# Places — Open-Source Tiled Basemap (MapLibre) — Testing Handoff

**Purpose:** resume local testing/debugging of the Places hero's new tiled basemap in a
fresh (non-cloud) session. Read this first, then `strava-data/dashboard/charts_places.py`
(`_HERO_TEMPLATE`, the `<script>` starting around line 1063) and the update banner at the
top of the "Places — Build-Ready Spec" section of `Specs/strava-data/dashboard-spec.md`.

**Branch:** `claude/places-map-open-source-lxzny0` (work here; do NOT create a new branch).
**Status:** code complete, committed (`946baf4`), pushed. **Building locally with a real
`MAPTILER_KEY` surfaced issues** (not yet detailed) that this handoff exists to unblock —
the cloud session that wrote this code could not reach the CDNs needed to see real tiles
render (see "What was NOT verified" below), so this is the first real-tile test pass.

---

## What changed and why

The Places hero ("the main map") was a **hand-rolled `<canvas>` 2D renderer**
(`chart_places_hero` in `charts_places.py`) using a **custom equirectangular projection**
frozen at `COSLAT = 0.7551` (cosine of the raw-extent midpoint latitude) — explicitly **not**
Web Mercator. This was a deliberate Pass-A architecture choice (see
`Plans/strava-data/places-basemap-plan.md`) made specifically to avoid tiles, because slippy
map tiles are Web Mercator and would misregister against the routes across the 32°–50°N
span the data spans, unless one side got reprojected at runtime.

The user wanted the ability to toggle between real street-detail and terrain basemaps.
Adopting **MapLibre GL JS** resolves the projection conflict instead of working around it:
MapLibre owns Web Mercator natively, so every route point is now projected through the
map's own `map.project()` call — perfect tile registration at every latitude, no reprojection
math needed on our side.

## Architecture

- **MapLibre is mounted** in a `<div id="places-map">`, positioned absolutely behind the
  existing `<canvas id="chart-places-hero">`.
- **The glow is unchanged in spirit** — the same additive-blend (`globalCompositeOperation
  ='lighter'` on dark grounds, `'multiply'` on light) of thin, translucent, per-sport-colored
  polylines with golden-ratio jittered alpha — but it's now drawn on a **2D canvas overlay
  layered on top of the MapLibre canvas** (`pointer-events:none` so gestures pass through to
  the map). It redraws on `map.on('move', drawGlow)` and `map.on('styledata', drawGlow)`.
- **Three basemap modes**, implemented as MapLibre **style swaps** (one code path, `styleForMode(mode)`):
  - **Glow** — `{version:8, sources:{}, layers:[{type:'background', paint:{'background-color':'rgba(0,0,0,0)'}}]}`
    (fully transparent — the hero's CSS radial-gradient ground shows through). This is also
    the automatic fallback whenever MapLibre or the key is unavailable.
  - **Street** — MapTiler `streets-v2` (light theme) / `streets-v2-dark` (dark theme).
  - **Terrain** — MapTiler `outdoor-v2` (real relief/hillshade tiles; this is a *light*
    basemap regardless of page theme — see "Known non-issues" below).
- **Key/CDN wiring:** `config.MAPLIBRE_CDN` (JS+CSS from unpkg) is spliced into `<head>` in
  `page.py` next to `PLOTLY_CDN`. `config.MAPTILER_KEY = os.environ.get("MAPTILER_KEY", "")`
  is read at build time and spliced into the hero template replacing the `__MAPTILER_KEY__`
  token. Empty key → `TILES_OK = false` → Street/Terrain buttons render `disabled`, hero
  stays Glow-only.

## Key JS functions (all inside `_HERO_TEMPLATE`'s `<script>` in `charts_places.py`)

| Function | Role |
|---|---|
| `initMap()` | Lazily constructs the `maplibregl.Map` (deferred until the hero has non-zero size, since the section can mount hidden behind an inactive tab — WebGL init on a 0×0 container is unreliable). Sets `cooperativeGestures: true` (ctrl+scroll / two-finger to zoom, so the page still scrolls on one-finger/plain wheel), disables rotation. |
| `styleForMode(m)` / `applyMapStyle()` | Picks/apply the MapLibre style JSON for the current mode + theme. |
| `drawGlow()` | The glow overlay draw loop — sizes the canvas to DPR, clears, sets composite mode, strokes every track via `projectPt()`, then calls `drawLabels()` and `updateZoomButtons()`. |
| `projectPt(lng, lat)` / `fallbackProject(lng, lat)` | Projects a point through `map.project()` when the map exists; falls back to a **static** equirectangular fit of the full extent (no pan/zoom) if MapLibre never initialized — this is what rendered in the cloud session's testing. |
| `goFrame(v, animate)` / `window.placesFlyTo(target)` | Camera framing — `map.fitBounds()` to preset boxes (`allBounds`, `viewBounds('sd'|'bos')`) or an arbitrary `{lat0,lat1,lng0,lng1}` box. **`placesFlyTo` keeps its exact old signature/contract**, so the Homes cards / Passport stamps / Peaks rows that already call it needed zero changes. |
| `applyHashState()` | Restores View/Map selection from `#places?v=&b=` on load; sets `pendingFrame` so the View applies once `map.on('load')` fires (no visible fly on first paint). |
| `window.__placesHeroRedraw` | Called by the page's global theme toggle (`applyChartTheme()` in `template.py`) — retints the glow colors and, if not in Glow mode, calls `applyMapStyle()` to swap the light/dark Street variant. |

**Deleted** as part of this conversion: the `COSLAT` frame math for screen projection, the
custom camera (`cur{s,fx,fy}`, `tweenTo`, `fitBox`, `frameTarget`), all bespoke pointer/pinch/
wheel/dblclick gesture handlers, the shift-drag marquee selection box, the adaptive graticule,
the inlined vector-coastline basemap (`_load_basemap`, `assets/basemap.json`) and the inlined
hillshade PNG (`_load_hillshade`, `assets/hillshade.png`). MapLibre's native camera + gestures
+ `BoxZoom` replace all of it. Net diff was **-145 lines** despite adding a whole new map layer.

## Files touched (commit `946baf4`)

- `strava-data/dashboard/config.py` (+16) — `MAPLIBRE_CDN` constant, `MAPTILER_KEY` env read.
- `strava-data/dashboard/page.py` (+/-3) — splice `MAPLIBRE_CDN` into `<head>`.
- `strava-data/dashboard/charts_places.py` (675 lines touched, net -145) — the bulk: markup
  (`#places-map` div, retitled Map buttons), CSS (stacking `z-index`s — map `0`, glow canvas
  default/no explicit z-index anymore after a fix, `.places-chrome` `2`), and the full script
  rewrite described above. `_load_basemap`/`_load_hillshade` functions deleted; `ASSETS_DIR`
  import dropped (no longer used by the hero).
- `.github/workflows/deploy.yml` (+5) — passes `MAPTILER_KEY` secret as a build env var.
- `Specs/strava-data/dashboard-spec.md` (+52/-x) — an update banner under "Places —
  Build-Ready Spec" explaining the new model, plus "SUPERSEDED"/"UPDATED" callouts on the
  now-stale Basemap/Terrain/zoom-control/selection-zoom sections (kept for history, not deleted).

## What was verified in the cloud session, and how

Only the **code-level / fallback path** — this environment's outbound proxy hard-blocks
`unpkg.com` and `api.maptiler.com` with an explicit 403 policy denial (confirmed via
`curl "$HTTPS_PROXY/__agentproxy/status"`, which lists both hosts under `recentRelayFailures`
with `"detail": "gateway answered 403 to CONNECT (policy denial or upstream failure)"`).
That block applies even to Playwright's browser traffic (same proxy), so **real MapLibre
init and real tile rendering were never exercised in the cloud session** — this is the
biggest gap and the most likely place your local issues live.

What *did* pass, via `window.maplibregl` being undefined → `HAS_ML=false` → `TILES_OK=false`
→ Glow-only fallback:
- `uv run python strava-data/build_dashboard.py` — clean, no exceptions, `[places]` console
  lines print (`hero: tracks=330 pts=22555`, `basemap: maplibre tiles, maptiler_key=MISSING
  (glow-only)`, etc.).
- A Playwright pass against the built HTML: **zero page/JS errors** in both themes; the
  Street/Terrain buttons correctly render `disabled` with no key; the glow canvas overlay
  paints non-transparent pixels (confirmed via `getImageData` pixel counts) in both light and
  dark theme; `window.placesFlyTo()` (tested directly, and via the "Trips" View button) moves
  the fallback-projected camera and doesn't throw; a stacking bug (glow canvas painting above
  `.places-chrome`, occluding buttons) was caught and fixed via explicit `z-index`s.

## What was NOT verified — check these first

1. **MapLibre actually initializing** — confirm `window.maplibregl` is truthy and a
   `canvas.maplibregl-canvas` element appears inside `#places-map`. If it silently doesn't
   (CDN blocked, script error, CSP, ad-blocker, whatever your local issue is), the hero
   degrades to the *same static fallback projection* the cloud session saw — so if what
   you're seeing looks suspiciously like "the old map but frozen, no pan/zoom," that's
   probably it, and the JS console is the first place to look for a MapLibre load error.
2. **Real tile fetch/render** for Street + Terrain. Slugs used: `streets-v2`,
   `streets-v2-dark`, `outdoor-v2` — these are current MapTiler v2 style names but **verify
   they're available on your account tier** (`mtStyle()` in the script builds
   `https://api.maptiler.com/maps/<slug>/style.json?key=<key>` — paste that URL directly in a
   browser tab with your key to sanity-check it returns a style JSON, not a 40x error).
3. **Route/glow registration accuracy against real tiles**, at multiple zooms — this is the
   actual point of the whole conversion. Check San Diego, Boston, and at least one distant
   trip (Vancouver / Sierra / Maine) and confirm the glow lines actually sit on the real roads/
   trails/coastline rather than drifting, especially after zooming and panning.
4. **Chrome/control stacking** with real tiles underneath — the z-index fix was validated
   against the transparent Glow fallback only; worth a second look once tiles are visibly
   painting (top-right View/Map toggle, zoom +/− cluster, fullscreen button).
5. **MapLibre's attribution control** — placement/legibility over both the dark and light
   theme footer scrim (`.maplibregl-ctrl-attrib` CSS overrides are in the `<style>` block but
   untested against a real attribution string).
6. **Zoom button disabled state**, fullscreen resize (`map.resize()` on fullscreen toggle),
   `#places?v=sd&b=terrain`-style hash restore on page load, and the theme-toggle repaint
   (light/dark ↔ `applyMapStyle()` swapping `streets-v2`/`streets-v2-dark`) — logic ports were
   straightforward but never run against a live `maplibregl.Map` instance.
7. **Mobile touch gestures** via MapLibre's `cooperativeGestures` (two-finger pan/pinch,
   one-finger scroll-through) — only desktop viewport was exercised in the cloud session.

## Known non-issues / already-considered tradeoffs (don't re-litigate these as bugs)

- **Terrain mode's glow uses `multiply`, not `lighter`.** `outdoor-v2` is a light basemap
  regardless of page theme, so `drawGlow()` computes `additive = !TH.light && mode!=='terrain'`
  — Terrain always gets the ink-on-paper composite. If Terrain's glow looks "duller" than
  Glow/Street, that's intentional, not a regression.
- **Line width formula was tuned once already** (`ctx.lineWidth = Math.max(1.0, Math.min(2.6,
  0.5 + z*0.17))`, keyed to `map.getZoom()`) to approximately match the old canvas hero's
  visual weight at continental vs. city zoom. If it still looks off once real tiles are up,
  it's a one-line tweak in `drawGlow()`.

## Local testing commands (Windows)

**cmd.exe:**
```cmd
set MAPTILER_KEY=your_key
uv run python strava-data\build_dashboard.py
uv run python -m http.server 8766 --directory "Running Log"
```

**PowerShell:**
```powershell
$env:MAPTILER_KEY="your_key"
uv run python strava-data/build_dashboard.py
uv run python -m http.server 8766 --directory "Running Log"
```

Then open `http://localhost:8766/strava.html#places` in a normal (non-sandboxed) browser and
toggle Street/Terrain — this is the first environment in this whole effort with real network
access to `unpkg.com` and `api.maptiler.com`, so it's the first real test of the tile path.

## Git / ops

- Commit trailers: `Co-Authored-By: Claude <noreply@anthropic.com>` +
  `Claude-Session: <url>` (do not put the model id in commits/PRs/code — chat only).
- Push: `git push -u origin claude/places-map-open-source-lxzny0` (retry w/ backoff on
  network error).
- Do NOT open a PR unless asked.
- Relevant prior commit: `946baf4` — "Places hero: real tiled basemap via MapLibre GL JS
  (Glow/Street/Terrain)".
