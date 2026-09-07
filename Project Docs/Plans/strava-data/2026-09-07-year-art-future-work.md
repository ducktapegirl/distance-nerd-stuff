# Years in Motion — future work

**Dated 2026-09-07.** Open items for the calendar-year art piece after it shipped
as the Strava dashboard's [Art tab](../../Specs/strava-data/dashboard-spec.md).
The piece itself and its build rules are documented in
[`year-art/README.md`](year-art/README.md) and the dashboard spec; this file is
only the backlog.

Canonical generator: **`strava-data/dashboard/art_year.py`**.
Nothing here is urgent. Nothing here is broken.

---

## 1. Douglas–Peucker simplification — the clearest win

**The problem.** `art_fragment()` adds ~1.54 MB to `strava.html` (3.34 → 4.88 MB),
almost entirely bloom path data: **351 GPS tracks, 110,718 points**, already
decimated 6:1 at read time in `track(step=6)`. The cost grows with every year
added, and this is by far the largest thing on the page.

**Measured.** Running Douglas–Peucker over the projected tracks, at tolerances
expressed in SVG user units (the viewBox is 900 units wide and renders at 720 CSS
px, so **1 user unit ≈ 0.8 px**):

| ε (user units) | ≈ px at display size | Points kept | Est. bloom size |
|---:|---:|---:|---:|
| 0.25 | 0.20 px | 56,362 (50.9%) | ~0.68 MB |
| **0.50** | **0.40 px** | **40,361 (36.5%)** | **~0.48 MB** |
| 0.75 | 0.60 px | 32,174 (29.1%) | ~0.39 MB |
| **1.00** | **0.80 px** | **27,134 (24.5%)** | **~0.33 MB** |
| 1.50 | 1.20 px | 21,104 (19.1%) | ~0.25 MB |

**The finding worth acting on:** even ε = 1.0 user unit is **under one displayed
pixel**, and it removes three quarters of the points. There is no visual argument
for keeping them — the bloom renders at 0.9px stroke and 0.38 opacity. That would
take `strava.html` from 4.88 MB to roughly **4.0 MB**.

**How.** Add the simplifier to `art_year.py` and apply it in `year_layer()` after
projecting to user units, not in `track()` — tolerance is only meaningful once the
points are in the coordinate space they will be drawn in. Keep `step=6` as-is;
the two are doing different jobs (`step` bounds the read, ε bounds the shape).

**Verify by measuring, not by eye:** total path point count before/after, page
size before/after, and a rendered diff of one dense year at 720px. A bloom that
is visually identical at 0.8px tolerance is the whole claim.

## 2. Metric morph — the highest-value addition

Let spoke length remap between **distance / duration / elevation gain / suffer
score**, animated, with the ring and bloom unchanged.

The reason to build it: the shape of *hardest* is probably not the shape of
*longest*. Right now the long green hikes dominate the ring because distance is
the only metric on offer, and an 8-mile run with 2,000 ft of climb reads as
shorter than a flat 10-miler. Elevation and suffer score would redraw the year
around effort instead of mileage — the same 194 activities, a different year.

Notes for whoever builds it:
- **`suffer_score` is on 355 of 378 rows (94%)** — missing on 23, mostly runs
  (16 Run, 2 TrailRun, 2 EBikeRide, and one each of Pilates, Hike and
  MountainBikeRide). Decide what a missing value draws rather than letting it
  become a zero-length spoke that silently vanishes; the inner-ring tick in
  `year_layer()` is the precedent. `total_elevation_gain_m` and
  `moving_time_min` are both 378/378, so those two metrics need no such
  handling.
- The shared cross-year scale (`scale_of`) is per-metric. Each metric needs its
  own max across all years, or the picker stops being comparable.
- Zero-distance activities already draw as inner-ring ticks; under a *duration*
  metric they have a real value and should become ordinary spokes. That switch
  is the fiddly part.

## 3. Keyboard access to individual activities

← → already change year (guarded to the Art view). There is still no way to reach
a **spoke** without a pointer. 194 spokes means 194 tab stops, so the answer is
arrow-key stepping through days within the ring once it has focus — one tab stop
for the figure, then arrows to walk it, Escape to release.

This is the only accessibility gap in the piece and the one thing that would stop
it being usable by keyboard alone.

## 4. Year draw-on animation

A radial hand sweeps once from January on load, spokes and traces appearing as
they happened. Good landing moment; adds nothing after the first three seconds,
and it delays the piece being legible, so it needs a skip and should respect
`prefers-reduced-motion`.

## 5. Ambient mode

No input: the piece slowly highlights "this day, last year", cycling on its own.
This is the version that belongs on a wall display, and the closest cousin to the
e-paper cards. Would pair naturally with a URL flag (`#art-ambient`) rather than a
visible control.

## 6. Deep link to a single activity

A permalink that opens the Art tab with one activity already lit, so a specific
day is shareable. The data is already there — every spoke carries `data-id`, and
`ART_DATA.act` is keyed by it. Mostly a matter of reading the hash on load and
choosing how it composes with the existing `#art` view routing.

## 7. Scrub damping

Dragging across days can flip the readout rapidly between neighboring
activities. It is not wrong, and the transitions smooth each step, but it may feel
busy on a phone where drag is the primary verb. Deliberately left alone: it is a
feel judgment that wants a real device, not a guess. Worth revisiting after using
it on mobile for a while.

---

## Not doing

- **Fanning or stacking same-day activities.** Decided: the angle stays honest and
  paint order decides, with runs and rides on top. See the README's Edge cases.
