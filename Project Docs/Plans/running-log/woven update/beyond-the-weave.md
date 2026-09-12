# beyond-the-weave.html — six non-textile concepts

Same bones as Woven Weeks — a row per week, a column per weekday, one mark per run whose size is
its mileage and whose color is its workout type — but the mark stops being a thread. Data,
geometry, the two views, and the `wob()` hash are exactly as in
[thread-samples.md](thread-samples.md); the page's original (unmuted) type colors are used
throughout, at the user's request. Samples are rendered by JavaScript functions that return an
SVG string, except the relief map, which returns two `<canvas>` elements.

## 01 Worms

Dark soil ground (`#1a1410` plus a 7-unit dot pattern of two soil flecks). Each run is a polyline
sampled along `y + amp·sin(2π·s/wl + phase)` with `amp = 0.9 + 0.5·u`, `wl = 11 + 5·u`, phase
`wob(k+3, π)`, damped toward the ends by `(1 − 0.35·|2t − 1|)`. Five strokes per run: a dark
offset shadow (sw + .9, `.55`), the body (sw 3.2), segment rings as the same path with
`stroke-dasharray=".45 2.1"` in the dark tone, a pale saddle as a dash that only paints a
~13%-long band a third of the way along (`dasharray="0 <ln·.28> <ln·.13> <ln>"`), and a `.16`
white highlight translated `−0.8`.

## 02 Cross-stitch sampler

Cream aida (`#e9e2d3`) with a `<pattern>` of cell outlines and corner holes, cell = `rh`,
anchored at `(L, T)`. Each run is `n = max(2, round(ln / cell))` X stitches starting at
`col0 = round((x − L) / cell)`; the two diagonals of every X are accumulated into two path strings
per type (`a` = `\`, `b` = `/`) so the whole sampler is ~4 paths per type. A dark offset copy
under both gives thread depth; a `.28` white line over the `/` stroke gives the sheen. The only
concept where mileage is *countable*.

## 03 Footprints in sand

Sand ground with a sparse dot pattern. Each run is a trail of `round(ln / 5.2)` prints,
alternating `side = ±1` for left/right (`py = y + side·.95`, plus a slow drift `wob(k, .5)·i/n`),
each foot an ellipse `rx 1.5 ry .9` with a toe dot, rotated `side·10 + wob(k+31+i, 6)` degrees,
over a `.35` shadow ellipse. ~3,900 prints for the window — a real build would use a `<symbol>`
+ `<use>`.

## 04 Dry-stone wall

Black mortar ground. Each run is an eight-vertex polygon: width `ln`, height `rh·0.9`, every
vertex jittered by `wob(k+i, 0.25–1.5)` so no two stones match. Fill is the type color with a
darker `.7` outline; a light stroke along the top three vertices and a `.28` black stroke along
the bottom three give the lit-from-above bevel. Each week is a course laid on the last.

## 05 Rain on still water

First version (rejected as "jarring"): three concentric *stroked* ellipses per drop. Second
version, the one in the file: each drop is **one** ellipse (`rx = ln/2`, `ry = min(rh·1.25,
rx·.13)·(1 + wob(k, .18))`, so it overlaps the neighboring rows slightly) filled by a per-type
`<radialGradient>` whose `stop-opacity` rises and falls three times (`.95 → .55 → .14 → .44 →
.10 → .28 → .05 → .12 → 0`) so the crests are soft bands of light, not lines. The whole layer is
`style="mix-blend-mode:screen"` with a `feGaussianBlur stdDeviation=".55"` filter, so where drops
meet they add into one shimmering surface. Drops are sorted widest-first so small ones stay on
top. Ground: a vertical navy gradient plus a faint tiled swell (`q15 −1.1 30 0 t30 0`, `.16`).

## 06 Relief map

The one raster. A `Float32Array` heightmap at 3 samples/unit over the full window
(2,328 × 546): every run adds a Gaussian bump `A·exp(−dx²/2σx²)·exp(−dy²/2σy²)` with
`A = (mi/mx)^0.8`, `σx = ln·0.26`, `σy = rh·0.95`, evaluated only inside ±3σ. The field is
soft-saturated with `tanh(h / (0.62·p95))` so the densest weeks read as peaks without flattening
the rest into sea, then colored by a nine-stop hypsometric ramp (deep water `12,40,74` → shore →
lowland green → upland → tan → rock → snow `252,252,252`), hillshaded from the upper-left
(`light = (−.55, −.6, .58)`, vertical exaggeration 26, `m = 0.62 + 0.5·shade`), and overlaid with
marching-squares contours every 0.1 (index lines every 0.5, heavier). Type is not encoded;
elevation maps are single-variable. Because it is a raster, a real build would need either an
embedded data-URI image or a pure-SVG-filter reproduction (`feComponentTransfer` tables for the
ramp, `feConvolveMatrix` for edges) — a different kind of build than the other Art pieces, which
is part of why the next round went back to per-run SVG marks.

At the end of this round the user asked for a variant "like the terrain map but not strictly
terrain — a raised center with beveled sides, keeping the color per workout type" — see
[raised-marks.md](raised-marks.md).
