# Mt. Whitney, 1 October 2025 — five design proofs

A decision record for a single-colour **11″×14″** line-art print of one hike. Five layouts are
rendered from the real track and put side by side; **nothing is chosen yet** — the right-hand
column below is deliberately blank.

This mirrors [`../poster/alternates/`](../poster/alternates/), which did the same job for the
40-for-40 print. Once a layout wins, it graduates to a maintained tool at
`strava-data/tools/poster_whitney.py`, the way design A there became `poster_40for40.py`.

```bash
uv run python "Project Docs/Plans/strava-data/whitney/proofs.py"
uv run python "Project Docs/Plans/strava-data/whitney/proofs.py" --png --dpi 300
uv run python "Project Docs/Plans/strava-data/whitney/proofs.py" --profile-x time
```

Open `proofs.html` for the contact sheet, or the `proof_*.svg` files directly in a browser.
`proofs.html` and the PNGs are gitignored; the five SVGs are committed.

| | Layout | Shape | Dominant element | Chosen? |
|-|--------|-------|------------------|---------|
| **A** | **Ascent** | vertical stack, portrait | the drawn mountain | |
| **B** | **Triptych** | three panels, portrait | equal billing | |
| **C** | **Medallion** | circular, portrait | the GPS route | |
| **D** | **Horizon** | landscape | the elevation profile | |
| **E** | **Summit** | triangular, portrait | the elevation profile | |

---

## What the data turned out to be

Two measurements shaped every layout here, and both were surprises worth knowing before you pick.

**1 · It is a near-perfect out-and-back.** The outbound and return 100 m grid signatures have a
Jaccard overlap of **0.955**, and start and finish are **10 m** apart. The return line lands on
top of the outbound one, so the GPS trace draws as a *single* line no matter what you do. There is
no loop to exploit and no two-strand reading available — which is why the route is used as a
graphic mark (C, and the small insets) rather than as a shape with internal structure.

**2 · The elevation profile is itself a mountain.** 8,361 ft to the summit at the **exact
midpoint** of the distance (11.37 of 22.29 mi, 50.9%) and back down to 8,533 ft — near-symmetric.
The profile and the drawing of Whitney are the same shape twice, once observed and once measured.

That rhyme is the strongest idea available in this data, so three proofs turn on it (A stacks the
two and aligns their summits; D makes the profile into ground and demotes the drawing to a
backdrop; E nests the drawing *inside* the profile's silhouette) and two deliberately do not
(B separates them into different panels; C ignores it entirely). **Choosing between those two
camps is the real decision** — the shape of the sheet follows from it.

| | |
|---|---|
| Activity | `16005045227` · "Mt. Whitney from Whitney Portal and JMT" |
| Distance / gain | 22.29 mi · 6,752 ft |
| Low / summit | 8,361 ft → 14,507 ft measured (**14,505 ft printed** — see crux 6) |
| Moving / elapsed | 12 h 00 m / 14 h 58 m, started 03:17, two athletes |
| Track bounding box | 5,235 × 3,481 m — aspect 1.50, landscape |
| Profile natural aspect | 19:1 (so every proof exaggerates; see crux 4) |

---

## The five

### A · Ascent — vertical stack

The drawn peak sits directly above the measured one and **their summits are aligned on one
vertical**, joined by a dotted leader, so the eye reads the same mountain twice. The drawing leads,
the profile answers, the figures climb its left flank and the route is a small mark by the type.

Profile at **6.2×** exaggeration. The drawing is narrowed to 852 units — not to a margin — because
that is the width at which `Whitney_Peak.svg`'s own summit (55.1% across its ink) lands on the
day's summit (50.9% of distance). Get that wrong by the 39 units it would otherwise miss by and
the whole concept reads as a misprint.

### B · Triptych — three panels, one frame

Three panels of 282 × 980 with a shared caption baseline. **THE MOUNTAIN** (drawing plus the two
figures beneath it), **THE CLIMB** (the profile turned 90° so distance runs bottom-to-top), **THE
LINE** (the track rotated to portrait). Nothing crosses the gaps, so a re-hang cannot break it.

Rotating the profile is what makes a narrow column work — it stops being a chart and becomes an
ascent. Panel 1 pairs the drawing with the figures for a structural reason: a 1.97-aspect drawing
in a 282-wide panel can never exceed ~143 units tall, so the column has to be filled by a second
element rather than by scaling a landscape drawing into a portrait hole.

### C · Medallion — circular

The route is the hero inside a disc, and the elevation is wrapped around it as a **polar ring**:
angle from distance, radius from altitude, 12 o'clock at the trailhead. Because the day is an
out-and-back the ring swells symmetrically to its widest directly opposite the start. The dashed
inner circle is the trailhead elevation — the ring's floor.

Radius runs 290 → 410, a ratio of **1.41**. An earlier pass used 352 → 410 and it read as a
slightly wobbly circle rather than as terrain; the swing has to be large or the device is wasted.
This is the only proof that does not rhyme profile against drawing, and the only one where the
drawing is reduced to a supporting band.

### D · Horizon — landscape

The sheet turned. The profile stops being a chart and becomes **ground**: the two figures stand on
the terrain line at the point four miles in where they actually were, and the drawing falls back
to the lightest weight as a backdrop ridge.

Profile at **6.8×**. That exaggeration puts the average ascent at roughly 41°, and the figures were
drawn on a 33° slope, so they sit on the line without needing to be rotated — a piece of luck that
makes this the most natural of the five. The backdrop is pushed left and sized so its base clears
the profile's apex entirely: two mountains that *nearly* register read as a printing fault, two
that plainly do not read as a range.

### E · Summit — triangular

The profile exaggerated to **12.4×** until the composition simply *is* its silhouette, with the
drawing nested inside that envelope and the summits on one vertical — the observed mountain inside
the measured one. Type sits in the two corners the triangle opens up.

The nested drawing is 46% of the measure and set 44% of the way down, because that is where the
profile's envelope is wide enough (~560 units) to contain it. Push it higher or wider and its
flanks poke through the data line.

---

## Technical cruxes

Carried forward for whichever design wins.

**1 · `hikers_simple2.png` does not exist.** The file committed in `50b3a50` is
`hikers_simple2.svg` — already clean vector, 16 paths, 8.7 KB, the simplest asset in the set. No
raster tracing, and no Pillow dependency (Pillow is not installed).

**2 · The drawings are open cubic strokes, not filled outlines.** All seven are Illustrator
exports: a viewBox with no width/height, one `.st0` class, and only `<path class="st0">` whose `d`
is an `M` then relative cubics, never closed. **`gen_poster_glyphs.py`'s pipeline cannot read
them** — its `rings()` splits on the letter `M` and pairs every number as a point, which against
relative cubics interleaves control points with anchors; and its `<path d="` regex matches *zero*
paths, because the real attribute order is `class`, then `d`.

`proofs.py` emits them verbatim inside a transform group instead — no flattening, no JSON
intermediate, curves stay curves. Two things it must get right, both now covered:

- Strip `<defs><style>` and `class="st0"`, setting stroke on the wrapping `<g>`. Two drawings in
  one sheet would each define `.st0`, silently defeating per-element weights. *(`grep -c st0
  proof_*.svg` returns 0 for all five.)*
- `vector-effect="non-scaling-stroke"`, so weight is constant in sheet units. Without it, scaling
  the 1345-wide peak to 850 turns its 2 px stroke into 0.32 mm.

**3 · Ink bounds are measured, not assumed.** `art()` flattens each path once at load to get the
true ink box and the highest point. Every viewBox happens to sit exactly 1.0 unit outside the ink
on all four sides, but measuring means a redrawn asset cannot silently break a summit alignment.

**4 · Exaggeration is a design parameter, and so is the x-axis.** At 1:1 in a 930-wide band this
profile is 47 units tall. The proofs use 4.7× (B), 6.2× (A), 6.8× (D) and 12.4× (E), reported on
every run. The x-axis has **two honest answers**: by distance the summit falls at 50.9% and the
profile is symmetric (this is what makes A and E work); by elapsed time it falls at 56%, the
ascent is long and the descent steep — truer to the day. `--profile-x time` renders the whole set
the other way; compare before committing.

**5 · The route draws once.** See "near-perfect out-and-back" above. Tolerances used: 4 m where
the route is the hero (C, B panel 3), 6 m mid, 9 m for insets. `poster_40for40.py`'s `cap=600`
is deliberately *not* carried over — it exists because that poster draws forty thumbnails, and
here the switchbacks are the signature.

**6 · Print 14,505 ft, not 14,507 ft.** The watch recorded 4,421.6 m; Whitney's surveyed summit is
14,505 ft. The 2 ft delta is barometric drift, and printing it hangs your altimeter's error on a
wall. Distance and gain are used as measured.

**7 · Which drawing is a decision about ink density.**

| File | Aspect | Paths | |
|---|---|---|---|
| `Whitney_Peak.svg` | 2.51 | 36 | cleanest; used in A, C, E |
| `Whitney_Peak_Vignette.svg` | 1.97 | 80 | best in a narrow column or as a backdrop; B, D |
| `Whitney_Wide.svg` | 1.98 | 166 | carries foreground boulders — as a *backdrop* they read as floating debris, which is why D switched away from it |
| `Whitney_Vignette_Trees.svg` | 1.51 | 105 | matches the track's aspect exactly; unused so far |
| `Whitney_Alabama_Hills.svg` | 2.19 | **460** | 13× the ink of Peak; will go muddy anywhere below full-sheet width |

If you want to see Alabama Hills, it needs a proof of its own at full-sheet scale, not a slot
sized for a 36-path drawing.

**8 · The figures carry their own slope, and it can be removed.** `hikers_simple2.svg` is drawn
standing on a hand-drawn hillside — paths 4, 5 and 9, verified by rendering them isolated.
`HIKER_GROUND` drops them so the figures can stand on a line we draw instead; `HIKER_FOOT` is
where the lower figure's boot met that slope. Concepts that want the vignette whole simply do not
pass the drop set. Figures are always scaled to a **height**, never fitted to a box.

**9 · Repo habits already encoded.** Every text write uses `newline="\n"` (this repo has a commit
fixing exactly that); `csv.DictReader` with `utf-8-sig`; no `strftime("%-d")`, which raises on
Windows.

**10 · Not yet built: the dawn device.** D could draw the pre-dawn stretch of the profile dashed
rather than solid — single ink preserved, and it says the day started at 03:17 without a word of
text. It is left out because it needs a *verified* sunrise time for Lone Pine on 2025-10-01, and
an estimated one would be a fact invented for a print.

---

## Verified

Run against all five on every build (`/tmp` scripts, not committed):

- No element crosses a sheet edge; tightest margin to the trim is **0.42 in** (proof C).
- No two text elements overlap.
- `grep -c 'st0\|<style\|<defs' proof_*.svg` → **0** for all five.
- Only the four intended stroke weights appear: 1.8 / 2.4 / 3.0 / 3.8 units (0.46–0.97 mm).
- Figures' feet land on the drawn profile in A, D and E, checked at 3× zoom.

Canvas and palette: **1100×1400 user units for 11×14 in at 100 units per inch** (D is 1400×1100,
the same sheet turned), ground `#F5F0E6`, ink `#2B2A28` — the same 100-units-per-inch convention
and the same two colours as the 40-for-40 print, so the two hang as a pair.
