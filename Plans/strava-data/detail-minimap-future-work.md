# Future work: per-activity mini-map + elevation profile in the Activity Details panel

**Status:** proposed / design decisions resolved · **Created:** 2026-07-18 · **Owner:** unassigned

## Why

The Activity Details panel — the right-side panel on desktop, the bottom sheet on
mobile, rendered by `renderActivity(a)` (`strava-data/dashboard/template.py:701`)
— shows an activity's name, date, and stat tiles only. This adds a small **map
with the GPS track** and an **elevation profile** to that panel, like the Places
"Passport" stamps but with a **lightweight static basemap** behind the track.
Static (no pan/zoom), read-only, and consistent with the site's styling in both
light and dark and on both mobile and desktop.

## What we're building (decisions locked 2026-07-18)

- **Static Glow basemap** — MapTiler `backdrop-v4`, `-dark` variant in dark mode
  — behind the track. Graceful **tile-free fallback** (subtle gradient/graticule,
  like the Passport stamps) when `MAPTILER_KEY` is empty, mirroring the hero.
- **Solid sport-colored route** — run = `--running` teal, MTB = `--mtb` amber —
  with a **contrast casing** (route stroked twice: a wide light/dark casing under
  the colored route) for legibility on tiles. Reuses the hero's casing idea from
  `places-basemap-contrast-future-work.md`.
- **Violet elevation profile** (`--elevation`) below the map — a small filled
  altitude-vs-distance area mirroring the Peaks sparkline (`drawSpark`).
- **Inline SVG**, not Plotly/canvas — survives `innerHTML` injection, themes for
  free via CSS custom properties, and repeats cleanly when `showDay` stacks
  several activities.
- **Responsive**: fluid `width:100%` with a fixed aspect box — ~380px usable on
  the desktop 420px panel, ~300–380px in the mobile bottom sheet.

## Architecture & reuse

- **Geometry (build time):** reuse `_load_trip_geo(aid)`
  (`charts_places.py:1708`). Add a variant (or extend it) that also
  **web-mercator-projects the track into the basemap's exact pixel frame** so the
  route lands on the roads: at build time, pad the track bbox, pick the slippy-map
  **zoom** that fits it in the target W×H, compute the **center** lon/lat, project
  each point to a pixel and normalize to 0..1 within that frame. Emit per activity:
  the normalized track pts, `elev[]`, `distance[]` (elevation x-axis), `sport`,
  and the basemap `{center, zoom, w, h}`. Doing the projection in Python means
  **no mercator JS ships** and alignment is exact. Keep existing Passport behavior
  untouched.
- **Embed** this compact payload into `ACT_DATA` via `_activity_detail_json`
  (`page.py:52`), capped ~50–60 pts (~0.4–0.6 MB inline for 330 geo activities;
  the hero already embeds all tracks, so this is in-band). Gate on a `hasGeo` flag
  — the ~20 indoor activities get no map block (stats still render).
- **Basemap raster (client, lazy):** on panel open, build the MapTiler **static**
  URL from the embedded `{center, zoom, w, h}` + style slug + `-dark` suffix +
  `MAPTILER_KEY`
  (`https://api.maptiler.com/maps/backdrop-v4{-dark}/static/{lon},{lat},{zoom}/{w}x{h}@2x.png?key=…`)
  and set it as the SVG `<image>` href. Loading lazily (one request per opened
  activity) keeps page weight flat; the key is already baked + domain-restricted
  (`config.py:31-36`). MapTiler's static-map calls count against the free tier
  (ample for a personal site).
- **Track + elevation (client):** the SVG draws a wide casing `<polyline>`, then
  the sport-colored route `<polyline>` at `path*W, path*H`, then the violet
  elevation `<path>`/`<polygon>` using `var(--elevation)` + `fill-opacity`. These
  theme automatically.
- **Light/dark:** the SVG is injected fresh on each open, so read the current
  theme (`document.documentElement.classList.contains('light')`) to choose the
  basemap style suffix. Add a small hook so an already-open panel swaps only the
  `<image>` href on theme toggle (extend `applyTheme`/`applyChartTheme`,
  `template.py:1013`/`:934`, or a panel-scoped `MutationObserver` like the
  thumbnails at `charts_places.py:2283`). The track/elevation need no hook — CSS
  vars handle them.
- **Single source of truth for styles:** consider lifting the hero's `SLUGS` /
  `styleForMode` (`-dark` logic) into a shared spot so hero and mini-map agree.

## Files to touch

- `strava-data/dashboard/charts_places.py` — factor out the reusable
  projection/frame helper (a `_load_trip_geo` variant emitting basemap-aligned
  0..1 coords + `{center, zoom, w, h}` + `elev`/`distance`); leave Passport as-is.
- `strava-data/dashboard/page.py` — extend `_activity_detail_json` to attach the
  geometry payload per activity, gated on `hasGeo`.
- `strava-data/dashboard/template.py` — extend `renderActivity` to emit the
  mini-map SVG block (map `<image>` + casing polyline + route polyline +
  elevation area) + its CSS (aspect box that fits the 420px desktop panel and the
  mobile sheet); add the theme-toggle image-swap hook and the tile-free fallback
  background.
- `strava-data/dashboard/config.py` — reuse `MAPTILER_KEY`; optionally host the
  shared style-slug map.
- `Specs/strava-data/dashboard-spec.md` — record the new mini-map view (the spec
  is the source of truth for views, per `CLAUDE.md`).

## Edge cases

- **No-GPS / indoor** (~20 activities): omit the map+elevation block; keep stats.
- **`MAPTILER_KEY` empty:** tile-free gradient/graticule background, track +
  elevation still drawn — identical degradation to the hero.
- **Multiple activities on one day (`showDay`):** the panel already stacks each
  activity through `renderActivity`, joined by the `.d-sep` divider
  (`template.py:726-731`), inside a scrollable body. So a 2-activity day shows
  **two full blocks stacked vertically — each with its own mini-map + elevation
  profile** — and the user scrolls between them. Each mini-map is a self-contained
  SVG that lazy-loads its own basemap image independently, so N activities just
  means N independent maps with no shared state. (If stacked map height ever feels
  heavy, a later refinement could collapse all-but-the-first map behind a tap — but
  v1 keeps it simple: one map per activity, always shown.)
- **Degenerate bbox** (very short/flat track): clamp min zoom / min span, mirror
  `_load_trip_geo`'s `1e-6` guards; flat tracks get a low-relief elevation area.
- **Usage/security:** keep the MapTiler key domain-restricted; static-map
  requests count against the free tier.

## Verification

1. Rebuild `uv run python strava-data/build_dashboard.py` **twice**: once with
   `MAPTILER_KEY` set (in `strava-data/.env`) for a real basemap, once without to
   confirm the tile-free fallback.
2. `tools/mobile_preview.py` (un-sandboxed — CDN) or the `strava-qa` flow: open
   the panel from a calendar day and from HR/Pace chart-point clicks, on
   **desktop** (420px panel) and **mobile** (bottom sheet), in **light + dark**.
   Confirm: the track aligns with roads on the raster; the casing stays legible in
   both themes; the elevation area renders in `--elevation` violet; the basemap
   swaps light/dark on theme toggle; a no-GPS activity shows no map; `showDay`
   with 2+ activities stacks correctly.
3. Spot-check one activity's rendered track against Strava's own map for that id.
4. Confirm the inline-geometry page-weight delta is acceptable (~0.4–0.6 MB
   pre-gzip).

## Related

- Places hero (MapLibre + MapTiler, Glow/Terrain styles, contrast casing):
  `Handoffs/strava-data/places-maplibre-handoff.md`,
  `Plans/strava-data/places-basemap-plan.md`,
  `Plans/strava-data/places-basemap-contrast-future-work.md`.
- Sibling Activity Details improvement:
  `Plans/strava-data/activity-links-future-work.md` (Strava click-through on the
  activity name).
