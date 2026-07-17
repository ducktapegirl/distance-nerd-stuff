# Future work: Places hero — route/glow contrast against the real basemaps

**Status:** proposal / not started · **Created:** 2026-07-17 · **Owner:** unassigned

## Why

The Places hero moved from a tile-free canvas to real MapLibre/MapTiler basemaps
(`946baf4`, plus the 2026-07 Backdrop + full-dark-mode follow-up — see
`Handoffs/strava-data/places-maplibre-handoff.md` and the update banners at the top of
"Places — Build-Ready Spec" in `Specs/strava-data/dashboard-spec.md`). That session already
fixed one contrast problem: the on-canvas **label text** (coord/sub lines) was failing WCAG AA
against the near-white light-theme basemaps (measured as low as 3.56:1; fixed by removing the
alpha fade on those lines in light theme — see the "light-theme label contrast" follow-up
banner in the spec).

While reviewing that fix live, the athlete flagged a **second, separate** contrast concern that
wasn't in scope for that pass: the **route/glow polylines themselves** — not just the labels —
are hard to read against the real basemaps, including the *default* Glow (Backdrop) view.
Revisit this as its own pass.

## The problem (as reported, not yet independently measured)

- The glow route lines read as **subtle even on Glow/Backdrop**, the mode built specifically as
  a neutral ground for the routes to pop against.
- Not yet checked systematically against **Street** and **Terrain**, where real map detail
  (roads, contour lines, place labels) competes with the route lines for attention — this is
  likely worse than on Backdrop's plain ground.
- Likely needs: **heavier line weight** and some kind of **standoff / halo** (a contrasting
  outline or backing stroke around each route line, distinct from the per-sport color) so
  routes stay legible over both light and dark, both busy and plain basemap content.

## Relevant code (starting points, not a prescription)

- `drawGlow()`, `strava-data/dashboard/charts_places.py:1184-1219` — the route-line draw loop.
  Current line weight: `ctx.lineWidth = Math.max(1.0, Math.min(2.6, 0.5 + z*0.17))` (zoom-scaled,
  `charts_places.py:1202`), composite mode `additive = !TH.light` (`lighter` dark / `multiply`
  light, `charts_places.py:1197`), stroke color `strokeStyle = 'rgba(col..., a)'`
  (`charts_places.py:1210`) with no additional outline/halo pass.
- For comparison, the **Homes thumbnails** (a separate, smaller route renderer) already do
  something closer to a halo/standoff — worth checking whether that technique
  (`strava-data/dashboard/charts_places.py:783-800`, `~line 2177` grade-colored segment
  detail strokes with `shadowBlur`) is reusable or was already tried and found insufficient
  here.
- The retinted `TH.route` colors come from `--running`/`--mtb`/`--elevation`/`--other` CSS
  custom properties (`retint()`, `charts_places.py:1112-1120`) — any contrast fix should stay
  theme-aware the same way the label fix did (compute against the real basemap ground colors,
  not assume).

## Suggested approach for the next pass

1. **Measure first, don't eyeball.** The label fix in this session found the actual failure by
   pulling real background colors from MapTiler's live `style.json` (not guessing) and running
   the WCAG contrast formula against them at the actual alpha/color values used. Do the same
   for route-line legibility — likely via a perceptual contrast check (line color vs. sampled
   basemap pixel colors under the route, at a few representative zooms) rather than eyeballing
   screenshots, since "does the line read clearly" is more subjective than static-text contrast
   but can still be checked objectively (e.g. minimum luminance delta against the busiest patch
   of basemap the route crosses).
2. **Research prior art before designing from scratch** — the athlete specifically wants to look
   at how established route-visualization products solve exactly this problem before we design
   in a vacuum:
   - **Strava** (global heatmap / route overlays — likely the closest reference, similar
     colored-route-over-basemap problem at global scale)
   - **Trailforks** (trail-specific styling, often uses a white/dark outline standoff around
     colored trail lines)
   - **AllTrails** (route overlay against both Street and Terrain-style basemaps)

   Look specifically at: line weight relative to zoom, whether they use a contrasting outline/
   halo stroke (and its width/color/opacity relative to the main line), and whether the
   standoff differs between basemap styles (plain vs. busy) or theme (light vs. dark).
3. **Prototype a standoff stroke.** A common technique: draw a wider, high-contrast-with-the-
   ground outline stroke first (e.g. a light halo in dark theme, dark halo in light theme —
   mirroring the existing but currently-inert `shadowBlur` halo idea already in the label code,
   `charts_places.py:1278`), then the per-sport colored line on top at its current/adjusted
   width. Verify the halo is visible in `additive`/`lighter` (dark) and `multiply` (light)
   composite modes — it may need its own composite handling separate from the route lines'.
4. **Re-check against all three real basemaps in both themes** (6 combinations, same matrix as
   the Backdrop/dark-mode verification pass) plus a few real routes at multiple zooms — a fix
   tuned only against Backdrop's plain grey may not generalize to Street's saturated colors or
   Terrain's relief shading.

## Not in scope for this note

- The label-text contrast fix (coord/sub line alpha) is **already shipped** — this file is
  specifically about the route/glow polylines, a different visual layer.
- No code changes proposed here; this is a scoping note for the next working session.
