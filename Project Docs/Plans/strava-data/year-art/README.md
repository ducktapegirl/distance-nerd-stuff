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

```bash
uv run python strava-data/tools/proof_year_art.py
```

Standalone like `poster_40for40.py`: reads `strava-data/data/` directly, imports
nothing from `feed/` or `dashboard/`, and is **not** wired into any build or
workflow. It copies the poster's six-family colour scheme so the two pieces read
as siblings.

## Output

| File | What it is |
|---|---|
| `year.html` | **the piece** — every year, interactive, self-contained, no framework or build step |
| `year.svg` | the 2025 composition, static (what a print export would start from) |
| `grid.svg`, `spiral.svg`, `bloom.svg`, `clock.svg` | the four exploration proofs |
| `proofs.html` | contact sheet of all five — gitignored, rebuild to view |

## The composition

The piece stacks two of the four proofs. **The bloom (C)** is the ground: every
GPS track from a shared origin, each rotated by its day of year, held back in
tone so it reads as texture. **The year clock (B)** is the figure: 365 days
around a ring, bar length = distance, thickness = duration, colour = family.

Two things had to be true for the stack to work, and neither was obvious from
the separate proofs:

- **The scrim between the layers must stay small.** Every bloom track shares an
  origin, so the bloom is densest at dead centre — a wide scrim erases it
  exactly where it lives. It now stops just past the inner ring and protects
  only the centre type.
- **The bloom scales to the 85th-percentile track extent, not the largest.**
  Scaling to the widest track shrinks every local route to lint. The handful of
  travel days deliberately run off-canvas instead; those over-runs are the best
  thing in the piece.

Every label sits on top of the bloom, so month labels and centre type carry a
background-coloured halo (`paint-order="stroke"`) rather than keeping the ground
clear for them.

## Multiple years

All years live in **one SVG**, one `<g class="year">` each, and the picker
toggles which is shown — so switching costs no fetch and the armature never
moves underneath you. Two things this forced:

- **One scale shared by every year.** Spoke length is normalised against the
  longest activity across *all* years (Mt. Whitney, 22.3 mi, which happens to
  be in 2025 — so 2025 looks unchanged and the thinner years are drawn against
  it). Per-year normalisation would make a 5-mile run in a light year draw as
  long as a 13-mile hike in a heavy one, which is exactly the comparison the
  picker invites. The bloom's 85th-percentile extent is shared for the same
  reason.
- **The angle denominator follows the year.** 2024 is a leap year, so it maps
  onto 366 days; hardcoding 365 would put its Dec 31 somewhere 2025's isn't.

Partial years say so — 2024 starts in October and 2026 stops in September, and
an unqualified "51 activities" beside 2025's 194 reads as a collapse in fitness
rather than a short window of data. The picker marks them with a dot, and the
centre subtitle carries the covered span.

## Interactivity

Four interactions, one of which mobile forces:

- **Figure–ground link.** Each spoke and its own bloom trace share a `data-id`;
  pointing at one lights both. This is the whole reason the two views are
  stacked rather than shown side by side — it is the only pairing here that can
  say "this bar" and "the shape of that day" in one gesture.
- **Centre readout.** The well swaps to date, name, distance/time/elevation and
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
  but keeps the family filter.

Spokes are ~2 px wide, so the drawn geometry is not a usable pointer target —
`concept_year(interactive=True)` emits fat transparent hit lines, full-length so
a short spoke is no harder to reach than a long one.

## Known gaps

- **No keyboard access to individual activities.** ← → change year, but there
  is no way to reach a spoke without a pointer: 194 spokes would mean 194 tab
  stops, so arrow-keys stepping through days is the right answer and it is not
  built.
- **`year.html` is ~1.5 MB** with all three years embedded, almost all bloom
  path data (already decimated 6:1). Fine as a page, but it wants a
  Douglas–Peucker pass before shipping to the Pages site, and the cost grows
  with every year added.
- **The bloom's rotation-by-day currently reads as texture, not information** —
  colour is spent on sport, so a January limb looks like a July one. Open choice:
  keep sport-colour and accept the ground as pure texture, or colour the bloom by
  month and let the clock carry sport alone.
- **Metric morph is not built** — remapping spoke length to duration, elevation
  or suffer score. Likely the highest-value next addition, since the shape of
  *hardest* is probably not the shape of *longest*.
