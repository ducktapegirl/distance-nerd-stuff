# Places — Basemap Plan (real terrain + a map behind the glow)

**Status:** ✅ SHIPPED (2026-07-14). Decisions D1–D3 confirmed (allow small assets /
pre-rendered PNG + regen script / faint). All three feedback items delivered:
- **#3 scroll arrows** — `3f712ac`.
- **#2 Glow vector basemap** — `91ea5fd` (`assets/basemap.json` + `tools/gen_basemap.py`).
- **#1 Terrain shaded relief** — this commit (`assets/hillshade.png` + `tools/gen_hillshade.py`).

Build contract lives in `Specs/strava-data/dashboard-spec.md` (“Places — Basemap” / “Places — Terrain”).
Original plan retained below for reference.

---

Follow-on to the shipped Places build (`places-plan.md`, Passes A–C). Source of
feedback: three review notes after looking at the live section.

## The feedback, triaged

| # | Feedback | Verdict |
|---|---|---|
| 1 | Terrain toggle is non-functional — the mock's concentric rings were transcribed as a **placeholder** and never replaced. Want an **actual terrain (shaded-relief) map**. | Plan (basemap) |
| 2 | Glow map should have a **lightweight/translucent map behind it** for geographic grounding. Cards are fine as-is. | Plan (basemap) |
| 3 | Passport stamps want **explicit scroll arrows** instead of relying on the scrollbar. | **No plan — small standalone change** |

**1 and 2 are the same feature wearing two hats:** a *basemap layer under the
canvas* — a light translucent geographic layer in **Glow** mode, real shaded
relief in **Terrain** mode. They share ~90% of the plumbing (a layer drawn
under the route glow, synced to the hero camera, theme-aware). One plan.

**#3 is out of scope here** — a self-contained UI addition (chevron buttons that
scroll the strip, fade at the ends, coexist with the drag-scroll + edge-fade).
Do it as a one-commit follow-up, no pipeline.

---

## Why this needs a plan (it reopens locked decisions)

The Pass-A architecture was **Option A: bespoke `<canvas>`, NO tiles** — chosen
because Plotly/tile maps couldn't do the additive glow, fly-to, and Trips lens.
A real basemap pulls back toward tiles, and two locked constraints are in the way:

1. **Projection mismatch (the sneaky one).** The hero projects
   **equirectangular + a fixed `COSLAT=0.7551`**, *not* Web Mercator. Slippy
   tiles and hillshade services are Mercator. Overlaying them under the route
   layer **misregisters across the 32°–50°N span** unless one side is reprojected
   at runtime — expensive and fiddly.
2. **Self-contained / no-new-data / offline.** The whole dashboard is one HTML
   file on GitHub Pages; `CLAUDE.md` bans new data files and the CSP/CDN notes
   warn against runtime network deps. Live tiles add a network dependency +
   attribution obligations.

So the plan's real job is a short **Analyze/Design** pass to pick the basemap
source **against those constraints** — that choice drives everything else.

---

## The design space (Analyze must choose)

| Option | #2 light map | #1 relief | Fits locked arch? | Cost |
|---|---|---|---|---|
| **A. Raster slippy tiles** (dark-matter + hillshade layer) | ✅ | ✅ real | ✗ reopens "no tiles"; **Mercator reproject**; runtime network + attribution | high |
| **B. Static pre-rendered relief image** (embed/commit a hillshade rendered in the hero's OWN equirectangular frame) | ~ | ✅ real | ✅ keeps bespoke camera, no reproject, no network | one committed asset (bends "no new data files"); edge/resolution limits at deep zoom |
| **C. Vector coastline/borders** (embed a simplified Natural-Earth 1:110m coastline + admin-1 GeoJSON, drawn on-canvas in the hero projection) | ✅ | ✗ (lines, not relief) | ✅ perfect registration, scales with zoom, theme-able, cheap | small committed JSON |

### Recommended path (my read): **C for Glow, B for Terrain**
Thread the needle so the locked architecture is **preserved, not reopened**:

- **Glow mode → Option C.** A heavily-simplified coastline + state/province
  borders GeoJSON (tens of KB), drawn as faint polylines **in the hero's exact
  projection/camera** → registers perfectly with the routes, scales at every
  zoom, retints per theme (faint slate dark / light gray light), matches the
  "drawn" aesthetic. This is the "light translucent map behind the glow."
- **Terrain mode → Option B.** A single static **hillshade PNG pre-rendered in
  the same equirectangular frame** (fixed All extent), drawn under the glow with
  the camera transform, low opacity. Because it's rendered in the hero's own
  projection, registration is exact — **no Mercator reproject, no runtime tiles**.
  Accept softening at deep zoom (heatmap aesthetic, not survey map).

Net: **no tiles, no runtime network, camera untouched.** The only concession is
two small committed assets (a coastline JSON + a hillshade PNG) — a deliberate,
scoped exception to "no new data files," worth confirming with you (Decision D1).

Fallback if you want zero new assets: **C only** — coastline/borders in both
modes, Terrain adds denser contour-ish styling rather than true relief. Loses
"actual" shaded relief but keeps the repo perfectly self-contained.

---

## Open decisions (need your call before Build)

- **D1 — new assets?** Allow the two committed assets (coastline JSON + hillshade
  PNG), or hold the "no new data files" line and go **C-only** (no true relief)?
  *Recommend: allow them; they're small, static, and build-time-embeddable.*
- **D2 — relief data source** (if D1=allow): render the hillshade from public DEM
  (SRTM/GMTED downsampled) at build time, vs. a one-off hand-produced asset.
  *Recommend: a committed pre-rendered PNG + a documented regen script, so the
  deploy build stays fast and offline.*
- **D3 — how strong?** Glow-mode basemap should stay a *quiet* grounding (low
  opacity, thin lines) so the routes remain the subject. Confirm the intended
  prominence (faint hint vs. clearly-readable map).

---

## Execution (once D1–D3 are set)

Mirrors the `/strava` model-split from `places-plan.md` (orchestrator on Opus in
the main session; Analyze=Opus for the projection/source work; Build=Sonnet;
QA=Sonnet; Review gate=Opus). One pass, since it's a single subsystem:

1. **Analyze (Opus):** lock the basemap source per D1–D3; produce the simplified
   coastline/border GeoJSON (and hillshade render recipe) **in the hero's
   equirectangular frame**; verify byte budget + registration against 3–4 known
   points (coastlines at SD, Boston, Vancouver; a Sierra ridge).
2. **Design → `Specs/strava-data/dashboard-spec.md`:** a "Places — Basemap" spec extension:
   layer draw order (basemap → graticule → glow → labels), per-mode + per-theme
   styling, opacity, the `Glow · Terrain` toggle wiring (already exists), and how
   the layer reads the existing `cur {s,fx,fy}` camera. Retire the concentric-ring
   placeholder in `drawContours()`.
3. **Build (Sonnet):** add the basemap layer to `charts_places.py`'s hero
   (`_HERO_TEMPLATE` JS): a `drawBasemap()` called at the top of `draw()`, fed by
   injected coastline coords (Option C) and/or an embedded image (Option B);
   delete the ring placeholder. No new palette hex (reuse text/border tokens).
4. **QA (Sonnet) + Review gate (Opus):** registration across zoom levels, both
   themes, both modes, mobile; page-weight delta; `prefers-reduced-motion`; the
   Playwright geometry harness from Pass C.

**Critical files:** `dashboard/charts_places.py` (hero template + a small
basemap loader), `Specs/strava-data/dashboard-spec.md` (spec extension), plus the new asset(s)
under `strava-data/data/` or inlined. `page.py` unchanged (hero already wired).

## Out of scope
- Passport scroll arrows (#3) — separate one-commit change.
- The parked exploration/tile-completion game (still future).
