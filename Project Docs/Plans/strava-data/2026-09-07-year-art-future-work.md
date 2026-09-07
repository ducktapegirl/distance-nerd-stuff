# Years in Motion — future work

**Dated 2026-09-07.** Open items for the calendar-year art piece after it shipped
as the Strava dashboard's [Art tab](../../Specs/strava-data/dashboard-spec.md).
The piece itself and its build rules are documented in
[`year-art/README.md`](year-art/README.md) and the dashboard spec; this file is
only the backlog.

Canonical generator: **`strava-data/dashboard/art_year.py`**.
Nothing here is urgent. Nothing here is broken.

---

## 1. Metric morph — the highest-value addition

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

## 2. Keyboard access to individual activities

← → already change year (guarded to the Art view). There is still no way to reach
a **spoke** without a pointer. 194 spokes means 194 tab stops, so the answer is
arrow-key stepping through days within the ring once it has focus — one tab stop
for the figure, then arrows to walk it, Escape to release.

This is the only accessibility gap in the piece and the one thing that would stop
it being usable by keyboard alone.

## 3. Year draw-on animation

A radial hand sweeps once from January on load, spokes and traces appearing as
they happened. Good landing moment; adds nothing after the first three seconds,
and it delays the piece being legible, so it needs a skip and should respect
`prefers-reduced-motion`.

## 4. Ambient mode

No input: the piece slowly highlights "this day, last year", cycling on its own.
This is the version that belongs on a wall display, and the closest cousin to the
e-paper cards. Would pair naturally with a URL flag (`#art-ambient`) rather than a
visible control.

## 5. Deep link to a single activity

A permalink that opens the Art tab with one activity already lit, so a specific
day is shareable. The data is already there — every spoke carries `data-id`, and
`ART_DATA.act` is keyed by it. Mostly a matter of reading the hash on load and
choosing how it composes with the existing `#art` view routing.

## 6. Scrub damping

Dragging across days can flip the readout rapidly between neighboring
activities. It is not wrong, and the transitions smooth each step, but it may feel
busy on a phone where drag is the primary verb. Deliberately left alone: it is a
feel judgment that wants a real device, not a guess. Worth revisiting after using
it on mobile for a while.

---

## Not doing

- **Fanning or stacking same-day activities.** Decided: the angle stays honest and
  paint order decides, with runs and rides on top. See the README's Edge cases.

## Done

- **Douglas–Peucker simplification** (2026-09-07). `simplify()` in
  `art_year.py`, applied in `year_layer()` after projection at
  `SIMPLIFY_EPS = 0.5` user units (~0.4 CSS px at the rendered 720px width).
  Bloom points 110,718 → 40,361; `strava.html` 4.88 MB → 4.04 MB. 0.5 rather
  than 1.0 because it captures 0.85 MB of the 1.0 MB available at half the
  deviation, staying sub-pixel even at 2x zoom.
