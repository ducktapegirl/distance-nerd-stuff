# raised-marks.html — a lifted center, shaded sides, color kept

Between the stone wall and the relief map: every run keeps its own workout color and its own
mark, but each mark is *raised* — brighter along its crown, falling into shadow at its edges —
and *translucent*, so overlaps deepen rather than cover. All four are lit from the upper-left so
the page reads as one surface under one light. Data, geometry, views, and `wob()` as in
[thread-samples.md](thread-samples.md); original type colors. A faint ground of week-row guides
(`#243044`, `.5` wide, `.55`) sits under everything.

`shade(hex, dl)` below is an HSL lightness shift used to make a lighter or darker version of a
type color for the sample. (The real build replaced this with theme-neutral white/black
interpolation inside the gradient — see [shine-compare.md](shine-compare.md).)

## 01 Gel pills

Each run a `<rect rx = h/2>` (`h = rh·.84`) filled by a per-type vertical `linearGradient`
(`shade(c, +.22)` → `c` at 45% → `shade(c, −.24)`), at `.84` opacity; a second, shorter
rounded rect over the top 42% filled white→transparent (`.55 → 0`) is the gloss; a black `.35`
copy translated `+0.9` under a `feGaussianBlur .7` group is the shadow.

## 02 Beveled tiles

A flat rect of the type color (`h = rh·.88`) at `.86` group opacity with four chamfer facets of
depth `.75`: top and left as white at `.42` / `.18`, bottom and right as black at `.45` / `.22`.
Hard-edged; the wall's cousin.

## 03 Soft mounds — chosen

One `<ellipse>` per run, `rx = ln/2`, `ry = rh·.62`, filled by a per-type `<radialGradient
cx=".42" cy=".36" r=".62">`: `0 → shade(c, +.26) @ .98`, `.38 → c @ .92`, `.78 →
shade(c, −.22) @ .78`, `1 → shade(c, −.32) @ 0`. No outline at all — only a lit form fading to
nothing at its rim. A black `.28` ellipse offset `(+.6, +1.0)` under a `feGaussianBlur .9` group
is the shadow. Marks are drawn **widest first** so a short run is never buried under a long one
in the same week.

This became the real `art_relief.py` build. Two things changed on the way to the module:
the gradient's crown and rim were rebuilt from theme-neutral white and black stops (so one def
serves both themes with the page's `var(--easy)` colors), and the per-run shadow ellipses were
replaced by a single blur/offset/merge filter on the whole group.

## 04 Frosted glass slabs

A half-opacity rect of the type color, a blurred lighter inset (`shade(c, +.3)` at `.75`,
`feGaussianBlur .8`) so light pools inside, a `.5` white rim along the top edge and a `.45` black
one along the bottom, and a `.4` shadow under a `1.1` blur. Stacks like acrylic where runs
overlap.
