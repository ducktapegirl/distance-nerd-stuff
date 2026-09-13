# thread-samples.html — thread treatments for Woven Weeks

Two rounds lived in this file; the second overwrote the first in place, so only round 2 survives
as HTML. Both are described here.

## Shared scaffolding (every sheet in this folder)

**Data.** Real runs from `running-log/running_log.csv`, weeks 56–100 of the log — sophomore
year, 207 runs — extracted with the module's own reader so the mapping matches the page:

```python
import sys, json, datetime, csv
sys.path.insert(0, "running-log"); sys.path.insert(0, "running-log/dashboard")
from dashboard.config import EASY_COLOR, LONG_COLOR, RACE_COLOR, TEMPO_COLOR, WORKOUT_COLOR
import art_weave as AW
rows  = list(csv.DictReader(open("running-log/running_log.csv", encoding="utf-8-sig")))
runs  = AW._rows(rows)                                   # (date, miles, mapped type), sorted
d0    = runs[0][0]; start = d0 - datetime.timedelta(days=d0.weekday())
mx    = max(r[1] for r in runs)                          # global max miles, so ln is faithful
W0, WN = 56, 100
sel = [{"row": (d - start).days // 7 - W0, "dow": d.weekday(), "mi": round(mi, 2),
        "t": t, "date": d.isoformat()}
       for d, mi, t in runs if W0 <= (d - start).days // 7 < WN]
json.dump({"runs": sel, "nrow": WN - W0, "mx": mx, "types": AW.TYPES,
           "colors": {...five hexes...}}, open("_weave_sample.json", "w"))
```

The JSON is then substituted for a `__DATA_JSON__` placeholder inside a
`<script type="application/json">` block (with `</script` escaped) so the sheet is one file.

**Geometry**, copied from `art_weave.py` and computed in the page's JS:
`S = 900; L, R, T, B = 118, 858, 74, 858; rh = (B - T) / 194` (the *whole* log's row count, so
the pitch is the page's, not the window's); `colw = (R - L) / 7`;
`ln = 0.34*colw + 0.95*colw*(mi/mx)**0.6`; `x = L + dow*colw + (colw - ln)/2`;
`y = T + (row + 0.5)*rh`; today's stroke `sw = min(rh*0.8, 3.6) = 3.23`.

**Two views per sample**, both from the same SVG string with different `viewBox`es: a 2.6×
detail (Mon and Tue, 18 rows from row 8: `viewBox = [L-18, y(8)-rh/2-1, 2*colw+36, 18*rh+2]`,
displayed 640 px wide) and page scale (the whole window, `[L-18, T-2, (R-L)+36, nrow*rh+4]`,
displayed 621 px wide — the width the real page gives the piece). The page-scale view is the
honest test: a thread is ~3 px there.

**Determinism.** Every jitter, phase, or lean comes from a pure hash of the run's own data,
never `Math.random()`:

```js
function wob(n, amp){ var h = Math.imul(n | 0, 2654435761) >>> 0;
                      return ((h >>> 11) % 2000 / 1000 - 1) * amp; }
function keyOf(r){ return Math.round(Date.parse(r.date) / 86400000) * 7 + Math.round(r.mi * 10); }
```

## Round 1 (overwritten): per-strand shading

Four treatments that all tried to make each strand read as a cylinder. Rejected because, at
~3 px per thread, cross-strand shading is not what makes cloth look like cloth (the blanket photo
in round 2 made that clear).

1. **Lit cord** — the flat `h` stroke drawn three times: color core (sw 3.6), a black band at
   `.30` opacity (sw 1.6) translated `+0.9`, a white line at `.34` (sw 1.1) translated `−0.85`;
   both bands *inside* the core's width so nothing halos onto the ground. Straight.
2. **Wool** — a wide halo of the thread's own color at `.16` (sw 5.4) under a 3.2 core, a soft
   black shade at `.18`, no highlight; every run and weft row bowed with `wob(k, .35)` as the
   control-point offsets of a relative cubic `c ln/3 a, 2ln/3 b, ln 0`.
3. **Hand-spun** — the bow at `.55`, plus a second, thicker stroke (sw 4.2) over the middle
   ~48% of each run so it swells like a slub.
4. **Plied** — two 1.7-wide strands per run sampled along a sine (`wave(x, y, ln, amp .95,
   wavelength 9.5, phase wob(k, π))`, the second strand at `phase + π`) so they cross; a black
   shadow strand beneath. Heaviest by far (~430 KB of sampled polyline for 207 runs).

The idea that carried forward: layering the same path data via `<use>` so three visual layers
cost 1× the bytes.

## Round 2 (the surviving HTML): muted yarn + stitch grain

Reacting to a photo of a knit rainbow blanket. What makes it read as yarn is (a) a muted, matte
palette where the hues sit at one tonal level, and (b) one fine stitch grain tiled uniformly
across every color, with rows fully covering the surface. So the sheet varies exactly those two.

**Muting** in HSL: saturation `× sMul`, lightness nudged toward a target
(`l += (lTo − l) × lAmt`) so the five type colors read as a dye lot rather than five brand
colors. Sample 01/02/04: `sMul .55, lTo .58, lAmt .45`; sample 03: `.40, .60, .6`. Each sample
prints its five resulting swatches so the teal/blue convergence can be judged.

**Grain** as an SVG `<pattern patternUnits="userSpaceOnUse">` — one tile = one weft row tall
(`height = rh`, width 2.4), two stitch rows inside with a brick offset — **stroked along each
thread** (`stroke="url(#pattern)"` on a second copy of the same path), so it lands only on yarn,
never in the gaps, and the tiling is one continuous cloth across all colors. Three tiles:

- *stockinette* — a knit V (`M.15 .45 L1.2 1.55 L2.25 .45`) in white `.22` over a black `.30`
  copy shifted `+.42`;
- *garter* — purl bumps: a black ellipse (`ry .5`) under a white one (`ry .42`) offset up;
- *rib* — 1.6-wide tile of vertical black/white bars with a thin horizontal dark rule at mid-row.

**Cover.** Samples 01–03 draw an undyed weft (`#6b6f78`) at the run stroke width and full
opacity first, so no card shows between rows (the blanket has no background); sample 04 keeps
today's thin weft and open ground. All keep a faint per-thread shade/sheen at `.13`/`.10`.

Verdict at the time: 01 (stockinette, 55%) was the recommendation. The user instead branched away
from weaving entirely — see [beyond-the-weave.md](beyond-the-weave.md).
