# 2025 in motion — calendar-year art

A companion to the [40 for 40 poster](../poster/README.md): where that piece
*selects* forty routes, this one takes a whole calendar year and leaves nothing
out. 2025 is the only complete year in the data — **194 activities, 181 with
usable GPS, 183 distinct days, 833 mi, 14 sport types**.

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
| `year.html` | **the piece** — interactive, self-contained, no framework or build step |
| `year.svg` | the same composition, static (what a print export would start from) |
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

## Interactivity (first cut)

Three interactions, plus one that mobile forces:

- **Figure–ground link.** Each spoke and its own bloom trace share a `data-id`;
  pointing at one lights both. This is the whole reason the two views are
  stacked rather than shown side by side — it is the only pairing here that can
  say "this bar" and "the shape of that day" in one gesture.
- **Centre readout.** The well swaps to date, name, distance/time/elevation and
  sport. Names step 21 → 17 → 14 px by length before ellipsing; the well is
  ~300 user units wide.
- **Family filter.** The legend toggles spokes, traces *and* hit targets
  together, and clears the selection if you filter away what is lit.
- **Drag to scrub.** A day is ~7 px of arc at the rim, so tapping a spoke is not
  viable on a phone. Dragging anywhere moves a hand around the year and selects
  the nearest activity in an enabled family. Hover is the desktop enhancement,
  not the only way in.

Spokes are ~2 px wide, so the drawn geometry is not a usable pointer target —
`concept_year(interactive=True)` emits fat transparent hit lines, full-length so
a short spoke is no harder to reach than a long one.

## Known gaps

- **No keyboard access.** 194 spokes would mean 194 tab stops. Arrow-keys
  stepping through days is the right answer; it is not built.
- **`year.html` is ~870 KB**, almost all bloom path data (already decimated 6:1).
  Fine as a page, but it wants a Douglas–Peucker pass before shipping to the
  Pages site.
- **The bloom's rotation-by-day currently reads as texture, not information** —
  colour is spent on sport, so a January limb looks like a July one. Open choice:
  keep sport-colour and accept the ground as pure texture, or colour the bloom by
  month and let the clock carry sport alone.
- **Metric morph is not built** — remapping spoke length to duration, elevation
  or suffer score. Likely the highest-value next addition, since the shape of
  *hardest* is probably not the shape of *longest*.
