# Art sections — spec sheet for five unused proofs

> **Status: BUILT (2026-09-09). This document has moved on — it is kept as the record of what was
> known going in, not as the build spec.**
>
> All five pieces shipped. The real build specs, including the numbers that only came out of
> rendering them at dashboard size, are appended where this file always said they should go:
>
> - **Strava** (Contour Field, Signature Route, Tangle) —
>   [`strava-data/dashboard-spec.md`](strava-data/dashboard-spec.md) § "Art tab — three pieces
>   promoted from the landing-art proofs".
> - **Running Log** (the new Art view, Woven Weeks, Constellation) —
>   [`running-log/dashboard-spec.md`](running-log/dashboard-spec.md) § "Art view".
>
> **Where this document was wrong or incomplete**, corrected in the specs above:
>
> - §B2 says "the proof uses `sqrt` — change it". It does not: `b2_contour` already used
>   `** 0.4`. The docstring says sqrt; the code disagrees with it.
> - §B2 assumed 373 profiles would fit the square frame. They do not — the pitch falls to 1.9
>   user units and the strokes alone fill the band at any amplitude. Contour Field ships at
>   **900×1720**, the one non-square piece in the set.
> - §A4's thread gate does not transfer. `|dy| < 34` was ~10 minutes on a 120-minute axis; on the
>   miles axis it is ~0.7 mi and **no thread draws at all**.
> - The three open decisions in §"Running Log" were settled: stacked cards on the Strava side,
>   `y = miles` for A4, and the Year Clock **moved** into the new Art view.
>
> The three open decisions and the per-piece notes below are left as written, for the record.

**Status when written: seed, not a build spec.** Nothing here was implemented. This document
existed so the session that built these views did not have to rediscover what the landing-art
session already learned the hard way.

## What this is

The landing-art work prototyped **twelve** directions and shipped two — A1 Ring of Seasons on the
College tile, B3 Route Grid on the Strava tile. The other ten are rendered, measured and committed
under [`../Plans/landing-art/proofs/`](../Plans/landing-art/proofs/), and nothing consumes them.

Five are worth promoting into dashboard **Art** views:

| Proof | Goes to | File |
|---|---|---|
| **A2** Woven Weeks | Running Log | `a2.svg` (23.2 KB) |
| **A4** Constellation | Running Log | `a4.svg` (38.5 KB) |
| **B2** Contour Field | Strava | `b2.svg` (36.3 KB) |
| **B4b** Signature Route + repeats | Strava | `b4b.svg` (22.2 KB) |
| **B5** Tangle | Strava | `b5.svg` (26.1 KB) |

The split is forced by the data, not by taste: **the College log has no GPS at all** (paper log,
2003–2007), so the A-pieces are built from dates and quantities; the B-pieces are all geometry.

Regenerate every proof with:

```bash
uv run python tools/proof_landing_art.py
```

**Strava already has an Art view** — `("art", "Art")`, a seventh nav entry holding one piece,
"Years in Motion" (`strava-data/dashboard/art_year.py`). Its build spec is under
"Art tab — Years in Motion" in
[`strava-data/dashboard-spec.md`](strava-data/dashboard-spec.md).

**The Running Log has no Art view and needs one built.** It has six views
(`running-log/dashboard/page.py:19`) and no `art` among them.

### Where the real spec goes

This file is a seed. Both `dashboard-spec.md` files call themselves "the append point for every
new view", so when a piece actually lands, **its build spec is appended there** — not here. This
document should end up describing work that has moved on.

---

## Cross-cutting — what changes between a tile and a dashboard

The five proofs were authored under landing-tile constraints. Most of those constraints do not
apply on a dashboard, and **that is the whole reason to promote them**. Do not lift the proof code
verbatim; re-derive it.

### 1. The ~40 KB budget is gone

That was a tile rule (two artworks inlined into one small front-door page). `art_year.py` ships a
bloom of **40,361 points** after Douglas-Peucker — three orders of magnitude past the tile budget.

This is the single biggest unlock. Every one of these proofs was cut down purely to fit 40 KB:

| Proof | Cut to fit the tile | Available |
|---|---|---|
| B2 | 40 ridges × 48 points, integer coords | **373** elevation profiles |
| B5 | 150 routes, ~24 points each | **351** routes |
| A4 | forced onto `<use>` symbols (1,138 `<circle>` = ~57 KB) | same data, no cap |

### 2. The frame changes, so the composition must

Tiles are **640×480** (4:3, `preserveAspectRatio="xMidYMid slice"`). Both existing art pieces use
**`S = 900` square** — `art_year.py:67` and `year_clock.py:32`, the latter commented "same
proportions as the Strava art clock" — capped at `max-width: 720px`. A2 in particular was
*designed around* a constraint that no longer exists (see below).

### 3. Interactivity becomes expected

`art_year.py` carries four interactions worth reading before designing a fifth: hover figure–ground
linking (a spoke lights its own GPS trace), a **drag-scrub** for touch, a sport-family filter, and
a year picker with arrow-key support. Each proof below names its natural interaction.

### 4. Theme is pure cascade, never `applyChartTheme()`

These are not Plotly figures, so `tidy_dark()` / `fig_html()` do not apply and `applyChartTheme()`
must not touch them. Colors are `--art-*` custom properties resolved by the cascade, each carrying
a **literal hex fallback** because rasterizers do not implement `var()`:

- `art_year.py:50` — `paint(key, interactive)` / `ink(token, literal, interactive)`, the original gate.
- `landing/art.py` — `ART_COLORS` plus `art_css()`, a newer variant where **one dict is the single
  source** of both the SVG fallbacks and the CSS `template.py` emits, so the two cannot drift.
  Prefer this shape.

Whatever is added needs a value in **both** the dark and light blocks. A color defined only in dark
is how the light theme ships broken.

### 5. Mobile is a tap-target problem, not a layout one

`art_year` added drag-scrub specifically because "a day is ~7 px of arc at the rim" — pointing at
individual marks is not viable at 375 px. A2 and A4 both put ~1,138 marks on one canvas and will
hit exactly this.

### 6. Determinism

Same CSV in, same SVG out. No `random()`, no clock; seed anything variable from the data, and sort
before slicing. Otherwise every deploy produces a spurious diff and the page can never be visually
regression-tested.

### 7. Namespace the ids

`art_year.py` prefixes everything `art-` / `ART_`; `year_clock.py` uses `yc-`. SVG `<defs>` ids
share one document namespace, so a new piece needs its own prefix or it silently cross-wires with
whatever else is on the page.

### 8. Helpers that already exist — do not rewrite these

`landing/geometry.py` (stdlib only):

| Function | What it does |
|---|---|
| `track(aid, step=6)` | stream → lat/lng projected to local meters, recentered on its own start, already y-down |
| `altitude(aid, n=48)` | `altitude_m` resampled to n points, **never parses lat/lng** |
| `simplify(pts, eps)` | Douglas-Peucker, iterative so a long track cannot blow the stack |
| `thin(pts, cap)` | evenly drop to a hard point cap, keeping the ends |
| `fit(pts, x0, y0, w, h, pad)` | scale into a box, aspect preserved |
| `bbox` / `rotate` / `path` | bounds, rotation, `"M x y L …"` at n decimals |
| `FAMILY` / `COLOR` | the five sport families and their hexes |

`tools/proof_landing_art.py` holds a working implementation of all five pieces.

**Where the shared code should live — verified, and not what you would guess.**

- `landing/geometry.py` **is importable from either dashboard** under `uv run` (checked with
  `sys.path[0]` set to `running-log/`, as the real build has it). Its chain is stdlib-only, so
  nothing comes with it.
- But that inverts the layering — `landing/` is the front door and is documented as depending on
  nothing. With a third consumer arriving, the honest move is to **promote these helpers into
  `nerd_common/`**, which is the designated shared package and which both dashboards *already*
  import (`nerd_common.tokens`, `nerd_common.format`, `nerd_common.theme`). Do that rather than
  importing across or copying a third time.
- `landing/geometry.py` itself *copies* `track()`/`simplify()`/`path()` from `art_year.py` because
  importing `dashboard.art_year` drags in `dashboard.config`, which calls `load_dotenv()` and reads
  `MAPTILER_KEY`. Same trade `poster_40for40.py` makes. Promoting to `nerd_common/` retires that
  duplication instead of extending it.

⚠ **Cross-dashboard imports are a trap.** `running-log/dashboard/` and `strava-data/dashboard/` are
*both* packages literally named `dashboard`, and each build puts its own parent on `sys.path[0]`.
So `import dashboard.art_year` from the Running Log side does not fail cleanly — it resolves to the
**wrong** `dashboard` package and reports a missing submodule. A Strava-side art module can import
`art_year` freely; a Running-Log-side one must never try.

### 9. Packaging — pick the self-contained pattern

The two dashboards package hand-built SVG art **differently**, and the new Running Log Art view has
to choose:

| | `art_year.py` (Strava) | `year_clock.py` (Running Log) |
|---|---|---|
| CSS | its own `<style>` in the fragment | `running-log/dashboard/template.py:619` |
| JS | its own `<script>` in the fragment | `running-log/dashboard/template.py:1291` |
| Returns | style + svg + controls + script, one string | markup + a JSON data blob only |

**Use the `art_year.py` self-contained pattern.** The Year Clock's behavior is spread across three
files, which is exactly the split worth not inheriting. `art_fragment(rows)` at `art_year.py:553`
is the shape to copy; `strava-data/dashboard/page.py:657` shows how a single `art_html` string gets
injected.

---

## Running Log — creating the Art view

Structural work, not invention: both dashboards already share the same nav/router machinery
(`.tab[data-view]` buttons, `#view-<name>` sections, an `html[data-view]` attribute set before
first paint).

1. Append `("art", "Art")` to `NAV_VIEWS` in `running-log/dashboard/page.py:19`.
2. Add a `section_art(rows)` to `running-log/dashboard/sections.py` and include it in the
   concatenation in `page.py` (the existing sections are chained there in view order).
3. Put the drawing in a **new module** beside `year_clock.py` — not in `sections.py`, and not in
   `visualize_log.py`. Follow §9: return one self-contained fragment.
4. Give it an id prefix that collides with neither `yc-` nor anything in `template.py`.

### Open decisions — record these, do not assume

- **Does the Year Clock move?** It currently renders inside `section_overview`
  (`sections.py:40`). It is the Running Log's only existing art piece and arguably belongs in an
  Art view — but moving it changes the Overview and the deep-link `#overview` anchor.
- **One piece or both?** If A2 and A4 both land, they need a picker like `art_year`'s year buttons,
  or two stacked cards.
- **Strava side:** do B2/B4b/B5 become separate entries in the existing Art view, a picker
  alongside "Years in Motion", or their own views?

---

# The five pieces

Each entry: what it draws, the technical cruxes that actually bit, the data reality, and a
suggested interaction. The cruxes are findings from rendering these, not speculation — most were
discovered because the first attempt looked wrong.

---

## A2 — Woven Weeks · Running Log

**Concept.** A warp of seven day-of-week columns against a weft of ~192 week rows; each run is a
slub whose length is its mileage. Four years of training as a bolt of cloth. Nothing is readable as
a number, which is the point.

**Cruxes**

- **The weft must be a real, continuous thread.** First cut drew it at 0.4 units against 1.6-unit
  slubs; the seven day columns read as seven separate barcodes with visible gutters between them —
  the exact opposite of cloth. Fixed by drawing the weft in a dimmed ink at `min(rowheight*0.34, 1.2)`.
- **Slubs must overrun their column.** A big week has to bleed into the days either side of it
  (`ln = 12 + (colw + 12) * (mi/mx) ** 0.75`). Without the overrun, the columns stay separate and
  the piece is a bar chart lying on its side.
- **The row-density constraint is the reason to promote this.** 192 rows over 440 units is 2.29
  units a row — about 1.2 px at the 240 px tile size, which is a moiré rather than a textile. That
  forced a 96-row variant (`a2b.svg`, two weeks to a row). **On a 900-unit canvas the constraint
  disappears** and the fine version becomes the right one.
- Marks are emitted grouped by stroke-width into a few `<path>`s rather than ~1,138 elements.

**Data.** 1,138 rows with `miles > 0` across 189 weeks carrying mileage. Peak week 65.5 mi (ISO
weeks — note that A1 buckets by academic-year week instead and gets a slightly different peak, so
state the bucketing wherever the number is shown). Per-run median 7.0 mi, max 15.1.

⚠ `workout_type` is **free text with 52 distinct values** (`run` 672, blank 125, `long run` 102,
then a long tail including `pizza relays` and `run (shh! don't tell)`). Anything encoding workout
type must normalize first, or use `dashboard.data.map_type()`, which already folds them into
easy/long/tempo/workout/race.

**Interaction.** Hover a slub → date, distance, workout type. Filter by mapped type. The four
academic years are natural bands; a year picker would work as it does on the clock.

---

## A4 — Constellation · Running Log

**Concept.** A dot per run placed at (day-of-year, minutes), sized by miles, with faint threads
between runs a few days apart. All four years overlaid on **one** calendar, so the piece is really
about the **voids** — summers, taper weeks, injuries — rather than the marks.

**Cruxes**

- **Element count.** 1,138 `<circle>` elements is ~57 KB on its own. Solved with five `<symbol>`
  definitions and `<use href>` (~25 KB). Still the right call on a dashboard: it keeps the DOM small
  enough to attach handlers to.
- **Threads must be gated on both axes**, not on date proximity alone. Linking any two runs within
  three days hangs a near-vertical stem off every dot whose neighbor ran a very different duration,
  and the field reads as a barcode with drips instead of a constellation. The working gate was
  `|dx| < 14 and |dy| < 34` in user units, *in addition to* the date test.
- **Only 798 of the 1,138 runs recorded a duration.** A `y = minutes` encoding silently drops 30% of
  the data. Either say so on the page, or encode `y = miles`, which all 1,138 have. This is the
  most important decision in the piece and the easiest to miss.

**Data.** 1,138 runs with mileage; 798 of them with minutes. 100 races (`is_race == "1"`) are
available as a natural highlight layer.

**Interaction.** Hover → that run's `comments` field. This is the log's best and least-exploited
asset: 1,075 non-empty entries, median 218 characters, real writing from the day it happened. A
constellation whose dots reveal the actual sentence is a much better piece than one that reveals a
mileage. The voids also invite an annotation layer ("stress fracture", "summer at home").

---

## B2 — Contour Field · Strava

**Concept.** Elevation only — no map, no lat/lng. Every activity's altitude profile as a ridgeline,
stacked and sorted by total gain, each filled opaque so the row in front occludes the one behind
(the Joy Division construction). Cheapest beautiful thing in the set.

**Cruxes**

- **Fill and stroke must be two separate elements.** This is the highest-value finding here.
  Stroking the closed occluder polygon draws its baseline *and both vertical sides*, so every ridge
  renders boxed and the stack reads as forty rectangles rather than a horizon. Emit a filled path
  (no stroke) and an open profile path (no fill), same geometry.
- **That doubles the path data**, which is what forced 40 ridges × 48 points at integer coordinates
  to fit 40 KB. **Lifting the cap makes all 373 profiles feasible** — that is the version worth
  building, and it is a genuinely different picture.
- **Amplitude must be `(relief / max) ** 0.4`.** Linear scaling flattens the median 84 m day to 4%
  of the frame against the 2,058 m maximum, and the field becomes forty straight lines. Even `sqrt`
  (0.5) leaves it dull.
- **The first row needs headroom.** Baselines march down the canvas, so the top baseline must sit
  lower than the tallest amplitude or the biggest day runs straight off the top.
- Ski days produce genuine sawtooth profiles (repeated descents). They look like glitches and are
  not.

**Data.** 373 of 378 streams yield a usable 48-point profile; 336 activities have `gain > 0`
(median 84 m, p90 204 m, max 2,058 m). `geometry.altitude()` reads only the `altitude_m` column, so
this piece never pays for the projection.

**Interaction.** Hover a ridge → activity name, date, gain. A sort toggle (gain / date / distance)
is the obvious control and re-orders the whole field — with 373 rows, sorting by date turns it into
a two-year seismograph.

---

## B4b — Signature Route + every repeat · Strava

**Concept.** The single most-repeated loop in the record, drawn solid, with all ~20 of its
near-identical siblings ghosted behind it on a shared scale. The subject is not the route — it is
the **GPS wander between repeats**, the fuzz of twenty runs of the same four miles.

**Cruxes**

- **Cluster detection is a grid-cell Jaccard on the *recentered* track** — 100 m cells, overlap
  > 0.5. This is `poster_40for40.py`'s duplicate test inverted: there it keeps two laps of one loop
  off the wall, here it finds them on purpose. **Recentering on the start point is what makes it
  work** — two runs of the same loop compare equal even when the watch caught a different driveway.
- **It is O(n²)** over candidates (restrict to ~1–13 km, leaving ~300 routes). Fine at build time,
  but worth a note as the record grows; a cheap prefilter on distance and start point would cut it.
- **One scale shared across the whole cluster.** Fitting each repeat to its own bounds aligns them
  on the *frame* instead of on *each other*, and the wander — the entire subject — vanishes.
  Compute the bounds over the union, then place every track through the same transform.
- One ghost currently shows a straight line across the middle: a real GPS dropout. Honest, but a
  dropout filter (reject segments over some jump threshold) is a defensible option.

**Data.** The top loop is a 4.4 mi run with ~20 matches, and it sits inside a cluster of five
~4.5 mi loops each repeated 19–21 times. There is more than one signature route here, which
suggests a picker rather than a single hardcoded pick.

**Interaction.** Scrub the repeats chronologically and watch the line settle. Color each ghost by
pace and the piece becomes "did I get faster on this loop over two years?" — a real question the
dashboard cannot currently answer.

---

## B5 — Tangle · Strava

**Concept.** Every route laid head to tail as **one unbroken polyline**. Because each is recentered
on its own start and most are loops, the line keeps returning to where it began — so the activities
knot around a common center instead of wandering off the canvas. Rooted in every activity, reads as
pure gesture.

**Cruxes**

- **A single `<path>` is what buys the point budget.** No per-element overhead, integer coordinates,
  ~24 points an activity got 150 routes into 40 KB. Without the cap, all 351 fit comfortably.
- **Simplify per route, in meters, before concatenating** (`simplify(pts, eps≈22)`), then `fit()`
  the finished polyline once at the end. Simplifying after concatenation would cut corners across
  the joins between activities.
- **Point-to-point activities translate the entire remainder of the line.** Loops return to their
  origin and cost nothing; a long one-way ride shifts everything drawn after it. A handful of travel
  days visibly drag the composition. Either accept it, order the routes so they cancel, or exclude
  non-loops.

**Data.** 351 of 378 activities have usable GPS.

**Interaction.** **A draw-on animation is nearly free** — one path, so `stroke-dasharray` +
`stroke-dashoffset` animates the whole two-year record being drawn in one stroke. This is already
on `art_year.py`'s future-work list
([`../Plans/strava-data/2026-09-07-year-art-future-work.md`](../Plans/strava-data/2026-09-07-year-art-future-work.md))
and this piece is the cheapest place to try it. Respect `prefers-reduced-motion`.

---

## Related reading

- [`../Plans/landing-art/README.md`](../Plans/landing-art/README.md) — the full exploration record,
  including the six directions not promoted here and why A3 and B6 lost.
- [`../Plans/landing-art.md`](../Plans/landing-art.md) — the original brief, with its §6 correction.
- `strava-data/dashboard/art_year.py` — the reference implementation for everything in §1–§9.
- `strava-data/tools/proof_year_art.py` — how an exploration proof sheet is structured.
- [`strava-data/dashboard-spec.md`](strava-data/dashboard-spec.md) §"Art tab" — the existing Art
  view's build spec, and the append point for new Strava entries.
- [`running-log/dashboard-spec.md`](running-log/dashboard-spec.md) — the append point for the new
  Running Log Art view.
