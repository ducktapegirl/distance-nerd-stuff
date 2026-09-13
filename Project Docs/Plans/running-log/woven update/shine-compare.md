# shine-compare.html — the real Low Relief build, three ways

Unlike the other sheets, this one is not a mock. It renders the actual `art_relief.py` module —
all four years, all 1,138 runs — three times with only the fill gradient swapped, each on the
dark and the light ground with that theme's own type colors. The generator is
[gen_shine_compare.py](gen_shine_compare.py).

## What the module does (the recipe to recover)

Recover the module with `git show cb52a18:running-log/dashboard/art_relief.py`. Its shape:

- **Packaging** as `art_year.py` / `art_weave.py`: one string of `<style>` + `<svg>` + legend +
  readout + JSON marks + `<script>`, every id and class `lr-`. Tokens `lr-ground`
  (`#243044` / `#dfe4ec`) and `lr-ink` (`#64748b` both) via an `LR_COLORS` dict that `_css()`
  writes into both `:root` and `:root.light`.
- **Rows** from `_rows()` with a stable sort key `(date, type, miles)` so the build is
  byte-identical from the same CSV.
- **One `<ellipse>` per run**: `cx` at its column center, `cy = T + (row + .5)·rh`,
  `rx = ln/2` on Woven Weeks' length curve, `ry = rh·0.62`, `fill="url(#lr-g-<type>)"`,
  `data-t="<type>"`. Placed then sorted `(−ln, date, type)` — widest first.
- **Five radial gradients**, objectBoundingBox, center `(.42, .36)`, `r .62`:

  ```
  0     #fff              stop-opacity .96    crown
  .30   var(--type,#hex)  stop-opacity .93    true color
  .78   var(--type,#hex)  stop-opacity .78    rim begins
  1     #000              stop-opacity 0      shaded, fades out
  ```

  The type stops are written as `style="stop-color:var(--easy, #2dd4bf)"` — the style attribute
  is the form every current browser honors for `var()` on SVG paint properties. Interpolating
  toward theme-neutral white and black, instead of toward precomputed lighter/darker hexes, is
  what lets one gradient per type serve both themes.
- **One shadow filter** on the group of all ellipses: `feGaussianBlur (SourceAlpha, .9)` →
  `feOffset (.6, 1)` → `feColorMatrix` to black at `.28` → `feMerge` under `SourceGraphic`. The
  classic chain rather than `feDropShadow`, for support.
- **Legend filter without groups**: global draw order rules out a `<g>` per type, so the
  button toggles `lr-off-<type>` on the `<svg>` and five CSS rules fade
  `#lr-svg.lr-off-easy ellipse[data-t="easy"] { opacity:.08 }`.
- **Hover**: Woven Weeks' nearest-mark search and drag-scrub verbatim, marks extended to
  `[cx, cy, rx, iso, miles, type]`, and `#lr-hi` is an ellipse moved *and resized* to the mark.
- **Labels**: day headers at `T − 30`; year labels at a gap derived from the maximum Monday
  overrun plus the shadow's throw (`L − (max(0, (ln_max − colw)/2) + 2) − 10`).

## The three variants

`gen_shine_compare.py` monkeypatches `AR._gradient` (and, for 03, blanks `AR._SHADOW` and strips
the `filter=` attribute), calls `art_relief_html(rows)`, and keeps only the `<svg>…</svg>`:

1. **Current build** — as committed.
2. **No shine** — the white `0` stop removed; the first stop is the type color at `.93`. Rim
   darkening, shadow, translucency, tapered ends untouched.
3. **Flat, tapered** — every stop the type color at `.86`, no rim, no shadow. Uniform translucent
   fill; the taper is the ellipse silhouette.

**The id-namespacing trick.** Each variant appears twice on the page (dark and light ground).
SVG paint-server references (`fill="url(#id)"`) resolve *document-wide*, so a second copy with
the same ids would silently take the first copy's gradient — and the first copy's theme colors.
The generator renames every `lr-` to `v1-`/`v2-`/`v3-` per variant, and again to `v1l-` etc. for
the light copy, then sets the type-color custom properties per ground container
(`.ground.dark { --easy:#2dd4bf; … } .ground.light { --easy:#0d9488; … }`, the values from
`template.py`'s two `:root` blocks) so each copy's `var()` resolves in its own theme.

The screenshot [shine-compare.png](shine-compare.png) shows 02 and the top of 03.

## Verdict at the pin

None of the three yet. 01's crown read as a distracting shine, worst in the light theme; 02 kept
the lift without the streak but still did not land; 03 lost the lift and read as a bar chart.
