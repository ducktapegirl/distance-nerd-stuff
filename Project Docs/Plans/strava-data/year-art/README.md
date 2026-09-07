# Years in motion — calendar-year art

A companion to the [40 for 40 poster](../poster/README.md): where that piece
*selects* forty routes, this one takes a whole calendar year and leaves nothing
out. Every year present in the data gets a layer, reachable from a picker:

| Year | Activities | With GPS | Days | Distance | Coverage |
|---|---|---|---|---|---|
| 2024 | 51 | 48 | 50 | 206 mi | 13 Oct – 31 Dec (partial) |
| 2025 | 194 | 181 | 183 | 833 mi | full year |
| 2026 | 133 | 122 | 126 | 549 mi | 1 Jan – 6 Sep (partial) |

The year range is **discovered from the data**, not hardcoded — a new year in
`activities.csv` becomes a new layer and a new picker button on the next build.

**The piece now ships in the Strava dashboard**, as the only entry on its `Art`
tab. The canonical generator is
[`strava-data/dashboard/art_year.py`](../../../../strava-data/dashboard/art_year.py);
the build spec is the
[dashboard spec](../../../Specs/strava-data/dashboard-spec.md) under
"Art tab". This directory keeps the exploration record and a standalone copy of
the piece:

```bash
uv run python strava-data/build_dashboard.py      # the Art tab
uv run python strava-data/tools/proof_year_art.py # the proofs + standalone page
```

`proof_year_art.py` **imports** the piece from `dashboard/art_year.py` rather
than keeping a second copy — it owns only the four exploration proofs. It reads
`strava-data/data/` directly and is **not** wired into any build or
workflow. It borrows the poster's idea of coloring by sport family so the two
pieces read as siblings, but groups into **five** families rather than the
poster's six:

| Family | Legend | Sport types |
|---|---|---|
| `run` | run | Run, TrailRun |
| `mtb` | bike | MountainBikeRide, Ride, EBikeRide |
| `foot` | hike / walk | Hike, Walk |
| `snow` | snow | AlpineSki, Snowboard, NordicSki |
| `other` | other | IceSkate, RockClimbing, WeightTraining, Workout, Pickleball, StandUpPaddling, Pilates |

The poster splits snow by direction of travel — downhill against nordic —
because it must fill a wall from forty routes and a merged family could empty
it of a terrain. Nothing here is selected, so all snow is one family, and
skating (which the poster groups with nordic) sits in `other`. A color is worth
spending on a family you see often, not on eleven activities across three
years.

## Output

| File | What it is |
|---|---|
| `year.html` | the piece standalone — same fragment the Art tab renders, in a bare page |
| `year.svg` | the 2025 composition, static (what a print export would start from) |
| `grid.svg`, `spiral.svg`, `bloom.svg`, `clock.svg` | the four exploration proofs |
| `proofs.html` | contact sheet of all five — gitignored, rebuild to view |

## The composition

The piece stacks two of the four proofs. **The bloom (C)** is the ground: every
GPS track from a shared origin, each rotated by its day of year, held back in
tone so it reads as texture. **The year clock (B)** is the figure: 365 days
around a ring, bar length = distance, thickness = duration, color = family.

Two things had to be true for the stack to work, and neither was obvious from
the separate proofs:

- **The scrim between the layers must stay small.** Every bloom track shares an
  origin, so the bloom is densest at dead center — a wide scrim erases it
  exactly where it lives. It now stops just past the inner ring and protects
  only the center type.
- **The bloom scales to the 85th-percentile track extent, not the largest.**
  Scaling to the widest track shrinks every local route to lint. The handful of
  travel days deliberately run off-canvas instead; those over-runs are the best
  thing in the piece.

Every label sits on top of the bloom, so month labels and center type carry a
background-colored halo (`paint-order="stroke"`) rather than keeping the ground
clear for them.

## Multiple years

All years live in **one SVG**, one `<g class="art-year">` each, and the picker
toggles which is shown — so switching costs no fetch and the armature never
moves underneath you. Two things this forced:

- **One scale shared by every year.** Spoke length is normalized against the
  longest activity across *all* years (Mt. Whitney, 22.3 mi, which happens to
  be in 2025 — so 2025 looks unchanged and the thinner years are drawn against
  it). Per-year normalization would make a 5-mile run in a light year draw as
  long as a 13-mile hike in a heavy one, which is exactly the comparison the
  picker invites. The bloom's 85th-percentile extent is shared for the same
  reason.
- **The angle denominator follows the year.** 2024 is a leap year, so it maps
  onto 366 days; hardcoding 365 would put its Dec 31 somewhere 2025's isn't.

Partial years say so — 2024 starts in October and 2026 stops in September, and
an unqualified "51 activities" beside 2025's 194 reads as a collapse in fitness
rather than a short window of data. The picker marks them with a dot, and the
center subtitle carries the covered span.

## Interactivity

Four interactions, one of which mobile forces:

- **Figure–ground link.** Each spoke and its own bloom trace share a `data-id`;
  pointing at one lights both. This is the whole reason the two views are
  stacked rather than shown side by side — it is the only pairing here that can
  say "this bar" and "the shape of that day" in one gesture.
- **Center readout.** The well swaps to date, name, distance/time/elevation and
  sport. Names step 21 → 17 → 14 px by length before ellipsing; the well is
  ~300 user units wide.
- **Family filter.** The legend toggles spokes, traces *and* hit targets
  together, and clears the selection if you filter away what is lit. A family
  switched off stays off when you change year.
- **Drag to scrub.** A day is ~7 px of arc at the rim, so tapping a spoke is not
  viable on a phone. Dragging anywhere moves a hand around the year and selects
  the nearest activity in an enabled family. Hover is the desktop enhancement,
  not the only way in.
- **Year picker** at the bottom, or ← → keys. Switching clears the selection
  but keeps the family filter. In the dashboard the arrow keys only act while
  the Art tab is the active view — a document-level handler would otherwise eat
  left/right on every other tab.

Spokes are ~2 px wide, so the drawn geometry is not a usable pointer target —
`year_layer(interactive=True)` emits fat transparent hit lines, full-length so
a short spoke is no harder to reach than a long one.

## Edge cases

Audited against the real data rather than assumed:

- **Leap years.** 2024 maps onto 366 days, so its Dec 31 lands at 359.0° next to
  2025's 359.01° — no drift under the picker. No Feb 29 activity exists yet.
- **No distance recorded** (25 activities: climbing, weights, Pilates, one
  skate). A spoke would be exactly zero units long and simply not appear, while
  still being counted in the subtitle. These draw as a **tick inside the ring**
  instead — present and countable, without inventing a distance. Width still
  carries duration, and the readout omits the mileage rather than printing
  "0.0 mi".
- **Tiny but real distances** get a 4-unit floor, ~1.7% of the radial range, so
  a 0.05-mile activity is still visible as itself.
- **Two activities on one day** share an angle exactly and overlap — 19 across
  the three years. They are **not** fanned or stacked: the angle stays honest and
  paint order decides. `PRIORITY` puts runs and rides on top of the gym session
  they share a day with, and the hit lines are emitted in the same order so the
  pointer reaches whatever is visually on top rather than whichever happened to
  be last in the file.
- **Unmapped sport types** fall back to "other", which is survivable but silent,
  so the build now prints a note naming them. `Pilates` was the one found this
  way and is now mapped explicitly.
- **Activity names are inlined as JSON in a `<script>`**, so `<` and `>` are
  escaped — no current name would break out, but nothing stops a future one.

## Known gaps

Tracked in
[`../2026-09-07-year-art-future-work.md`](../2026-09-07-year-art-future-work.md):
metric morph, keyboard access to individual activities, a draw-on animation,
ambient mode, a deep link to a single activity, and scrub damping.
Douglas–Peucker simplification is **done** — `simplify()` runs at 0.5 user
units, which is sub-pixel at the rendered size and cut the bloom from 110,718
points to 40,361.
