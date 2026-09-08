# Landing-page tile art — brainstorm and spec sheet

**Status:** the landing page ships; the art does not. `landing/art.py` returns a placeholder for
both tiles. This document is the whole brief for the session that replaces them — it assumes no
context from the session that wrote it.

---

## 1. The problem

`running-log/index.html` is the site's front door. It presents two dashboards as equal choices,
running log on the left and Strava on the right, and each is fronted by a square artwork that is
the tile's whole visual identity.

Four constraints, in priority order:

1. **Visually pleasing over informative.** These are not charts. A viewer should not be able to
   read a number off them, and shouldn't want to.
2. **Rooted in the real data.** Not decoration — every mark comes from something that actually
   happened. That is the point of the whole site.
3. **Simple and elegant.** One idea per tile, executed cleanly.
4. **Visually distinct from each other.** A viewer should be able to tell the two tiles apart at
   a glance, without reading the captions.

---

## 2. The contract — `landing/art.py`

The seam already exists in code. `landing/page.py` calls exactly these two names and nothing
else; replace the two function *bodies* and you are done.

```python
def college_art(rows, *, size=480) -> str:   # returns an <svg …>…</svg> string
def strava_art(rows, *, size=480) -> str
```

`rows` is the already-loaded CSV as a list of dicts (see `landing/data.py`), so no implementation
re-reads a file. Both must return something renderable when handed an **empty list** — a fork PR
or a fresh clone may not have the data.

Six rules every implementation must honor:

1. **Inline SVG only.** No `<img>`, no canvas, no external asset. The art has to theme-switch,
   and a raster can't.
2. **Theme-aware via CSS variables with literal fallbacks**, e.g.
   `fill="var(--art-run, #2dd4bf)"`. `strava-data/dashboard/art_year.py`'s `paint()` / `ink()`
   gate is the working precedent: the variable path for the interactive page, a literal hex for
   anything that rasterizes (rasterizers don't implement `var()`).
3. **`viewBox` + `preserveAspectRatio`, never fixed px.** The tile is fluid.
4. **Deterministic.** Same CSV in, same SVG out. Seed any randomness from the data (an activity
   id, a date) — never `random()`, never the clock. Otherwise every deploy produces a spurious
   diff and the page can never be visually regression-tested.
5. **Under ~40 KB of SVG per tile.** `art_year.py` down-samples GPS with `track(aid, step=6)`;
   this wants to be far coarser still.
6. **Legible at 240 px.** The tile renders at roughly half size on mobile. Anything that depends
   on reading individual strokes fails there.

One more, learned from `art_year.py`: **both tiles are inlined into the same document**, so SVG
`<defs>` ids (gradients, filters, clip paths) share one namespace. Namespace them per tile or the
artwork silently cross-wires. The placeholder already does this (`artph-college`, `artph-strava`).

---

## 3. The organizing idea — pattern vs. path

The axis of distinction is a gift from the data itself:

- **The college log has no GPS.** 2003–2007, transcribed from paper: dates, minutes, miles,
  workout type, a comment. Its art must be **abstract, rhythmic, typographic** — built from time
  and quantity, not geography.
- **Strava is nothing but geography.** ~378 GPS stream files, elevation, a dozen-plus sport
  types. Its art can be **literal, linear, cartographic** — built from paths.

*Pattern vs. path. Woven vs. drawn.* Lean into that contrast rather than trying to make the two
tiles rhyme.

---

## 4. Twelve directions

### College Running Log — abstract / rhythmic

**A1 — Ring of Seasons.** Four concentric arcs, one per academic year, each a continuous band
whose *thickness* is weekly mileage. Reads as a tree-ring cross-section: four years of training,
thicker in season, thin over breaks, with visible gaps where the log stops. Elegant, obviously
about time, reveals almost nothing specific. In-repo relative: `running-log/dashboard/year_clock.py`
— go deliberately coarser and drop all labels, or the tile becomes a small copy of a chart the
dashboard already has.

**A2 — Woven Weeks.** Each week is a horizontal thread; each run a slub of varying weight along
it. Stacked ~200 weeks tall, it reads as a textile — a woven fabric of four years. Warm, tactile,
low-information, and impossible to confuse with anything the Strava tile could produce.

**A3 — Pace Ribbon.** One continuous line traversing the tile, vertical position = pace, stroke
width = duration, four years compressed into a single sweep. The simplest possible mark that is
still honestly the data. Risk: it may read as a chart.

**A4 — Constellation.** Every run a dot placed by (day-of-year, minutes), sized by miles, faint
links between consecutive runs. Season blocks emerge as dense clusters separated by voids — and
the voids (summers, injuries) are the visual interest.

**A5 — Ink Strata.** Horizontal bands, one per month, each filled with hatching whose density is
that month's volume. Reads as sedimentary rock or a letterpress gradient. Purely textural; the
most "not a chart" option here.

**A6 — Typographic mass.** The ~1,400 `comments` strings set very small in Geist Mono and flowed
into a shape, so the log's actual words become the texture. Distinctive and personal, but needs a
readability decision — it is illegible at tile size, which is arguably the point.

**Leading candidates: A1 or A2.** A1 is safest and most obviously elegant; A2 is the most
distinctive and the least chart-like.

### Strava — literal / linear

**B1 — Route Bloom.** Every GPS track centered on its own start point, drawn at a common scale,
overlaid at low opacity in its sport's color: a radial flower of accumulated movement. **Caution:**
`art_year.py` already draws a bloom under the Year Clock, so this must not read as a re-crop of
it — go colorless-except-one-hue, or single-sport, or far denser.

**B2 — Contour Field.** Elevation streams only, drawn as stacked ridgelines (Joy Division style),
one line per activity, sorted by total gain. Pure geography, zero map. Very elegant, very distinct
from anything on the college side, and cheap: `altitude_m` alone, no lat/lng.

**B3 — Route Grid.** A quiet 6×6 grid of thumbnail route shapes, each activity's track normalized
to its own cell, one color per sport family. Reads as a specimen sheet. `tools/poster_40for40.py`
already does exactly this at poster scale — the tile would be its miniature, a nice family
resemblance across the project.

**B4 — Single Signature Route.** One route — the most-repeated loop, or the longest ride — drawn
as a single confident line, large, everything else omitted. Maximum simplicity. Instantly legible
at 240 px and unmistakably "a map" without being one.

**B5 — Tangle.** All routes drawn from a common origin as one continuous unbroken polyline, in
one stroke, knotting into a dense scribble. Rooted in every activity but reads as pure gesture.

**B6 — Sport Palette Bands.** Vertical bands whose widths are the sport families' shares, each
filled with a fragment of an actual route from that sport. Literal material, abstract arrangement.

**Leading candidates: B2 or B4.** B2 is the most beautiful-per-line-of-code and shares nothing
visually with existing repo art; B4 is the boldest simplicity play and the safest at small sizes.

---

## 5. Suggested pairings

| Pairing | Why it works |
|---|---|
| **A1 Ring of Seasons + B2 Contour Field** | Circle vs. horizon. Concentric vs. stacked. Reads as a matched pair without repeating a mark. **Recommended starting point.** |
| A2 Woven Weeks + B4 Signature Route | Texture vs. line — the strongest possible contrast. Riskiest, and potentially the best. |
| A4 Constellation + B3 Route Grid | Both are "many small things". Likely too similar; listed as the one to avoid. |

---

## 6. Inputs

| Direction | Reads |
|---|---|
| A1, A2, A4, A5 | `running-log/running_log.csv` — `date`, `miles`, `minutes`, `workout_type`. Read `utf-8-sig` (the file has a BOM). |
| A3 | + `pace_min_per_mile` |
| A6 | + `comments` |
| B1, B3, B4, B5 | `strava-data/data/activities.csv` (`sport_type`) + `strava-data/data/streams/<id>.csv` (`lat`, `lng`) |
| B2 | `streams/<id>.csv` `altitude_m` only |
| B6 | `activities.csv` `sport_type` + one stream per family |

`activities.csv` is committed. `streams/` is **~378 files and gitignored.**

### The streams constraint — read this before choosing

**`strava-data/data/streams/` is not in git.** Any direction needing per-activity GPS therefore
cannot generate its geometry in CI: fork PRs and fresh clones have `activities.csv` but no
streams. Three ways out:

**(a)** Pick a direction that needs only `activities.csv` (B6, or a route-free variant).

**(b) Precompute the geometry into a small committed asset** under `strava-data/assets/`, and have
`strava_art()` read that. **This is the repo's established pattern and the recommended answer** —
`assets/journey_routes.json` (25 KB, written by `tools/gen_journey.py` from a 50 MB Natural Earth
download that is never committed) and `assets/poster_glyphs.json` (written by
`tools/gen_poster_glyphs.py`) both work exactly this way: a `tools/gen_*.py` script run by hand
when the inputs change, a small JSON committed, and the build doing no heavy lifting and no
network I/O. Follow it: `tools/gen_landing_art.py` → `assets/landing_art.json`.

**(c)** Accept the placeholder on fork PRs. Cheapest, and the page already degrades this way — but
it means the front door looks unfinished in exactly the situation where a stranger is looking at it.

---

## 7. Decisions this session must make

Per tile:

- [ ] Which direction.
- [ ] Build-time generation, or precomputed committed asset (see §6 — (b) is recommended for
      anything touching streams).
- [ ] The `--art-*` CSS variable names, and where they are defined. `art_year.py`'s `ART_CSS`
      block is the precedent for scoping them.
- [ ] Actual SVG size, measured, against the ~40 KB budget.
- [ ] How it is verified. `strava-data/tools/proof_year_art.py` and the `epaper-all.html` proof
      sheet are the two existing patterns.

Cross-cutting:

- [ ] Confirm the two tiles are distinguishable at 240 px, side by side, in **both** themes.
      This is constraint #4 and the easiest one to lose while polishing each tile alone.

---

## 8. How to run that session

`/dashboard` is the wrong pipeline — the landing page is neither target and has no profile.
Drive it directly:

1. Read this document.
2. Pick a pairing from §5.
3. Prototype **both** tiles as standalone SVG files under `Project Docs/Plans/landing-art/proofs/`
   and look at them side by side, at 480 px and at 240 px, in both themes, before wiring
   anything into `landing/art.py`. Judging a tile alone is how the pair ends up looking alike.
4. Only then replace the two function bodies in `landing/art.py`, rebuild with
   `uv run python build_landing.py`, and check the real page.

Related reading: `strava-data/dashboard/art_year.py` (theme-aware SVG at scale),
`running-log/dashboard/year_clock.py` (the college data drawn as a clock),
`strava-data/feed/svg.py` (hand-written SVG primitives under hard constraints),
`strava-data/tools/poster_40for40.py` (route selection, projection, region clustering).
