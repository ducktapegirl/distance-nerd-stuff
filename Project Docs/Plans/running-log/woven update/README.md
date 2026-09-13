# Woven Weeks update — a pinned exploration

**Status: pinned, not adopted.** Nothing in this folder is on the page. It records a September
2026 attempt to replace the Running Log Art view's second piece, *Woven Weeks*
(`running-log/dashboard/art_weave.py`), that ended with "none of these yet." Everything needed
to pick it back up is here: the sample sheets themselves (self-contained HTML with the real data
embedded), a markdown per sheet explaining how it was built, the generator for the last sheet,
and the verification screenshots of the one variant that was fully built and briefly committed.

The exploration also surfaced a real bug in Woven Weeks — a long Monday run painting over the
"2005–06" year label — which was fixed on its own, independent of any redesign. That fix is on
the page; see the last section.

## What was tried, in order

Each round was a reaction to the one before. The prompt that drove each is in quotes.

| round | sheet | what it tried |
|---|---|---|
| 1 | *(overwritten — described in [thread-samples.md](thread-samples.md))* | "make the strands look like actual threads": four per-strand treatments — lit cord, wool, hand-spun, plied. Verdict: the shading cue was the wrong one. |
| 2 | [thread-samples.html](thread-samples.html) | Reacting to a photo of a knit blanket: "the colors need to be less saturated, and the texture isn't right." Muted-yarn palette + a stitch grain tiled across every color. Four variants on two dials (saturation, stitch). |
| 3 | [beyond-the-weave.html](beyond-the-weave.html) | "totally branch out, not as a woven concept": worms, cross-stitch sampler, footprints in sand, dry-stone wall; then "inspired by water" (rain on still water — first as stroked rings, then softened to radial glows); then "a terrain map instead" (a canvas heightmap with hillshade and contours). |
| 4 | [raised-marks.html](raised-marks.html) | "like the terrain map but not strictly terrain — a raised center with beveled sides, keep the color per workout type, translucent like the brick concept": gel pills, beveled tiles, soft mounds, frosted glass. **Soft mounds was chosen** and built for real as *Low Relief*. |
| 5 | [shine-compare.html](shine-compare.html) | On the real build: "the shine is too visually distracting" — the committed build, the same with the white crown removed, and a flat tapered version. Verdict: none yet; pin it. |

Every sheet uses the same real data — `running-log/running_log.csv`, weeks 56–100 of the log
(sophomore year, 207 runs) — placed with the *exact* geometry `art_weave.py` uses, so each sample
is a faithful preview rather than an illustration. The per-sheet markdown gives the recipe.

## The one that was built: Low Relief

Sample 03 of round 4 became a real module, `running-log/dashboard/art_relief.py` (prefix `lr-`),
and replaced Woven Weeks in commit **`cb52a18`** ("Replace Woven Weeks with Low Relief on the
Running Log Art view"). It was reverted by the commit that follows this folder's pin commit, so
the tree is back to Woven Weeks. To recover it:

```
git show cb52a18:running-log/dashboard/art_relief.py > running-log/dashboard/art_relief.py
```

`cb52a18` touched six files, and all six matter if it is restored wholesale
(`git revert` of the revert is the clean way): `art_relief.py` (new), `art_weave.py` (deleted),
`sections.py` (card, caption, import), `art_constellation.py` (a docstring pointer), `CLAUDE.md`
(the Art-views table and module list), and the Woven Weeks section of
`Project Docs/Specs/running-log/dashboard-spec.md`.

What it was, in one paragraph: one `<ellipse>` per run (~1,138), `rx = ln/2` on Woven Weeks'
length curve, `ry = rowheight * 0.62`, filled by one radial gradient per workout type whose crown
interpolates from white and whose rim toward black — theme-neutral, so the same five defs serve
both themes with the page's own `var(--easy)` colors — under a single shadow filter, drawn
widest-first so short runs stay on top, with the legend filter keyed on `data-t` plus a class on
the `<svg>` (global draw order rules out a `<g>` per type). The screenshots
[relief-desktop-dark.png](relief-desktop-dark.png), [relief-desktop-light.png](relief-desktop-light.png)
and [relief-mobile.png](relief-mobile.png) are of that build on the actual page; it passed the
determinism check (byte-identical rebuild), `qa.py`, both themes, and a synthetic touch-scrub at
375 px. The full recipe is in [shine-compare.md](shine-compare.md), which was generated from the
module itself.

Why it was pinned rather than kept: the white crown read as a distracting shine, especially in
the light theme; removing it (shine-compare 02) kept the lift but still didn't land; the flat
version (03) lost the lift and read as a bar chart.

## The bug this found, and its fix

Independent of any redesign, Woven Weeks had a real geometry collision. `colw = (R - L)/7 =
105.71` and a max-length slub is `ln = 0.34*colw + 0.95*colw = 136.37`. A Monday slub is
centered in its column, so it *starts* at `L + (colw - ln)/2 = 102.67`, and with a 3.25 stroke
and `stroke-linecap="round"` its visible edge reaches ≈ 101. The year labels were
`text-anchor="end"` at the literal `x = L - 12 = 106`. So a long Monday run crossed "2005–06"
(and would cross any year whose first week has a long Monday run). Drawing the labels after the
threads only decided who painted on top; it did not remove the overlap.

**The fix** (in `art_weave.py`, on the page now) derives the gap from the worst-case reach
instead of hardcoding it:

```python
max_ln  = 0.34 * colw + 0.95 * colw           # the mi == mx case
bleed   = max(0.0, (max_ln - colw) / 2) + sw / 2
label_x = L - bleed - 10                      # 10 units of clear air
```

That puts the label's right edge at ≈ 91 against a thread edge of ≈ 101, and — the point of
deriving it — a later re-tune of the length curve or stroke width can never push a thread back
over the labels. "2005–06" at font-size 14 is ~52 units wide, so it now starts near x ≈ 39: inside
the frame, with no `viewBox` or `L` change and no other design element touched. The day-of-week
headers were left at `T - 22`; they overlap nothing (the first thread is at `T + 2`).

## Rebuilding any sheet

All four HTML sheets are self-contained: the run data for the window is embedded as JSON and
every render is JavaScript in the page, so they open from disk with no build. The
per-sheet markdown gives the extraction script for the window and the geometry, so a sheet can be
regenerated on fresh data or extended with a new variant. `shine-compare.html` is the exception —
it is rendered from the real `art_relief` module by [gen_shine_compare.py](gen_shine_compare.py),
which needs that module restored first (see above; the script's docstring repeats the command).
