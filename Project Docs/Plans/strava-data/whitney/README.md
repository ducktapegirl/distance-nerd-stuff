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
| **D** | **Horizon** | landscape | the elevation profile | **taken forward → D1/D2/D3** |
| **E** | **Summit** | triangular, portrait | the elevation profile | |

**D was taken forward.** [`proofs_d.py`](proofs_d.py) develops it three ways with landmarks from
the real Strava segments and the descent drawn as a map below the profile — see
[Concept D developed](#concept-d-developed) at the foot of this file.

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

---

# Concept D developed

`proofs_d.py` takes concept D and adds the three things it was asked to carry: landmarks along
the profile drawn from this activity's own **Strava segment efforts**, the GPS route as the
**descent only** set below the profile and tied to it, and **profile and route at equal weight**
with the figures demoted to an accent.

```bash
uv run python "Project Docs/Plans/strava-data/whitney/proofs_d.py"
```

| | Layout | Sheet | Annotation | Chosen? |
|-|--------|-------|------------|---------|
| **D4** | **Portal** | 11×14 portrait | keyed on the map, legend + profile below | **current direction** |
| **D1** | **Section** | 11×14 portrait | numerals + legend at the foot | superseded by D4 |
| **D2** | **Descent** | 11×14 portrait | named in place under the profile | |
| **D3** | **Field note** | 14×11 landscape | numerals + a column at the right | |

**D4 is the current direction**, worked up from D1 against an explicit brief — see
[D4 · Portal](#d4--portal) below.

## The landmarks come from the segments

18 segment efforts are on file for this activity. `segment_efforts.csv` carries no start or end
index, but it carries `start_date_local` and `elapsed_time_s`, and the stream carries `t` — which
is enough to place every effort on the track exactly. Four efforts name landmarks directly:

| Landmark | Source |
|---|---|
| Trail Camp | end of **"summit down to trail camp"** |
| The 97 Switchbacks | **"99 Switchbacks down"** — the descent's own effort, 13.60–15.83 mi |
| Trail Crest / JMT Jct | start of **"Trail Crest to Whitney Summit"** |
| Lone Pine Lake Jct | start of **"Lone Pine Lake to Trail head"** |
| The Final Ridge & Needles | summit → Trail Crest, from the same effort |
| Outpost Camp | no segment; found by published elevation on the descent |

A useful corroboration fell out of this: **"Trail Crest to Whitney Summit" ends at 14,505 ft** on
the track — the surveyed figure, independently confirming crux 6.

**Printed elevations are the published ones**, not the watch's. They are facts about the places
rather than about the barometer, and every one lands within 132 ft of the track's own reading —
under 2% of a profile spanning 6,146 ft, so the label and its position never visibly disagree.
Distance is carried by 5-mile ticks on the baseline rather than hung off each landmark, because
published mileages and this track disagree by about 6% (the guidebook's 10.7 mi to the summit
against the watch's 11.37) and printing both side by side would look like an error.

## Why there is no true cross-section

The request was to align the two views vertically. **For this route that is impossible**, and the
track says so twice:

- The descent **backtracks 29% of its easting** — the switchbacks fold back on themselves — so
  elevation plotted against easting is multivalued and draws a tangle, not a section.
- Summit to Trail Crest is **1.89 mi and 898 ft of descent inside 57 m of easting**: 17.3% of the
  descent's distance in 1.2% of its width. A true section would crush a fifth of the day, the
  Needles and Trail Crest included, into a vertical wall.

**Leader lines between the views were the next option and are also out.** Trail Crest lies 59 m
*west* of the summit, because the final ridge runs north — so its tie-line crosses the summit's.
Exactly one crossing, but it falls between the two most important marks on the sheet.

What is left, and what all three use: **a numbered mark in both views, plus the two named spans
drawn at double weight in both.** The switchbacks are a dense zigzag on the map and a steep step
on the profile; drawing both heavier ties them by the line itself rather than by a rule.

### How close does D2 actually get?

D2 gives profile and map one shared measure, which is as near as this route allows. Measured:

| | profile | map | apart |
|---|---|---|---|
| Whitney Portal | 100.0% | 97.3% | 2.7 pts |
| Lone Pine Lake Jct | 73.7% | 79.3% | 5.6 pts |
| Outpost Camp | 68.8% | 75.0% | 6.3 pts |
| **Trail Camp** | **41.0%** | **28.5%** | **12.5 pts** |
| Trail Crest / JMT Jct | 17.3% | 7.6% | 9.7 pts |
| Mount Whitney Summit | 0.0% | 8.7% | 8.7 pts |

Worst case **1.16 in on an 11 in sheet**, at Trail Camp, where the switchbacks pack trail distance
into very little easting. Close enough that the eye scans between the two views, but it is *not*
registration — so the numerals still carry the tie, and the tool prints this divergence on every
run rather than letting the claim go unchecked.

## Further cruxes

**11 · The alignment turns the sheet portrait.** Stacking a full-measure map under the profile
fixes the map's height: the descent's box is 5,234 × 3,476 m, so the map is 0.664 of its own
width. At 14×11 landscape the measure is 1,210 units, making the map 805 tall and leaving nothing
for a profile. Turned portrait the measure is 930, the map is 617, and profile + map + type all
fit. D3 keeps the landscape sheet and pays for it — the map drops to 700 units and off the
profile's measure entirely.

**12 · D2's map is width-fitted, not contain-fitted.** A contain-fit map sits inset from the
profile above it and quietly breaks the shared measure the design is built on, so `route_mapper`
takes a `fit="width"` mode. D1 and D3 stay contain-fit; neither claims a shared measure.

**13 · "Equal importance" is optical, not arithmetic.** The profile is a short taut line; the map
is a long meander over twice the area. At identical stroke the map reads lighter, so it gets a 20%
bump (3.6 against the profile's 3.0, spans 6.8 against 6.0) to sit level — the same kind of hand
correction `poster_40for40.py` makes with `GLYPH_OPTICAL`.

**14 · Six landmarks on one measure need fanned leaders, not staggered labels.** Outpost Camp and
Lone Pine Lake are half a mile apart — 46 units on the descent's measure — so labels set under
their own x collide however they are staggered. D2 puts them on six even slots with a two-segment
leader back to the point. D1 cannot do this at all: its landmarks are squeezed into the right half
of the triangle, which is why it needs the legend.

**15 · One mapper per view.** `profile_mapper` and `route_mapper` return an index→point function,
and both the drawn polyline and every mark on it come from that same function — so a landmark and
the line it sits on cannot drift apart when a box is resized.

## Verified

- No element off any sheet; tightest margin **0.34 in** (D3).
- No text overlaps in any of the three.
- The D2 divergence table above is regenerated and printed on every run.
- `--png --dpi 300` → 3300×4200 (D1, D2) and 4200×3300 (D3).

---

## D4 · Portal

Worked up from D1 against a five-point brief: the route takes centre stage; landmarks move to
the **ascent**; the drawing and the figures become art attached to no data; the profile drops to
the same rank as the legend; and the two spans are reduced to their **start points**, with the
heavier-stroke device removed entirely.

### The composition

Three registers, top to bottom, each doing one job:

- **Header.** Type at the left; the vignette and the figures on the right, sharing one baseline
  and set shoulder to shoulder so they read as a *single* piece of art rather than two loose
  objects. Grouping them is what keeps them visibly separate from everything below — which is the
  point, since they illustrate the day rather than record it.
- **The route**, alone, holding the middle third at the heaviest weight on the sheet (3.6 against
  the profile's 2.2). Nothing else is allowed into that band.
- **The apparatus**: legend at the left, profile at the right, as peers, sharing a baseline at
  the foot of the sheet. A hairline rule originally separated this band from the map and was
  later removed — the gap alone carries the separation, and the shared bottom baseline is what
  makes the two read as one register rather than two leftovers.

The ascent is drawn rather than the descent, to match where the landmarks now sit. Because the
day is a 0.955-Jaccard out-and-back the two are visually identical — only the keyed indices differ.

### Two landmarks genuinely coincide, and the marks say so

- **The switchbacks begin at Trail Camp** — 4 and A are 0.8% of the ascent apart.
- **The final ridge begins at Trail Crest** — 5 and B are the same place, so they are pinned to
  the same index (the start of the *Trail Crest to Whitney Summit* effort). Positioning 5 by its
  published 13,700 ft instead put it **3.9% *after* the ridge it starts**, which reads as an
  error rather than as a coincidence.

Both pairs fan apart from one point on a shared origin, so they read as one place with two names.

### Further cruxes

**16 · A key's circle has to lead its type size.** The first pass drew 15 px digits inside
r = 5.4 circles; the digits spilled and every marker rendered as a blob. Circled keys are r = 12
at 14 px on the map. On the profile they are bare digits on a short tick — no circle at all,
both because the profile is apparatus rather than subject, and because eight circled keys will
not fit on a 277-unit ascent limb without touching.

**17 · Key placement has to clear three things, and each was found by getting it wrong.**
`place()` pushes a key outward along the route's local normal until it clears:

1. the **segments** of the route, not its vertices — after simplification a straight stretch of
   trail carries vertices only at its ends, so a vertex test left "5" sitting squarely on the
   line it was meant to be off;
2. every key already placed;
3. every key already placed *with its leader* — B and Trail Crest share an index, so sending B
   further out along the same ray drove its leader straight through 5's circle. Letters get a fan
   of candidate directions (±0.75, ±1.15 rad) for exactly this reason.

**18 · Numbers above the profile line, letters below.** The coincident pairs then stack across
the line, which is legible at a size where nudging them apart horizontally is not.

**19 · Distance is on the axis, not on the landmarks.** Published mileages and this track
disagree by about 6% (10.7 mi to the summit against the watch's 11.37), so the legend carries
names and elevations only and the profile's baseline carries 5-mile ticks. Printing both figures
side by side would look like an error.

## Tuning D4 by hand — `tune.py`

`tune.py` writes **`layout.html`**: the real proof with every piece movable and resizable over
an inch ruler and grid. Nothing about the design is duplicated in it — the pieces come from
`proofs_d.d4_parts()`, so what you drag is exactly what prints.

```bash
uv run python "Project Docs/Plans/strava-data/whitney/tune.py"
uv run python "Project Docs/Plans/strava-data/whitney/proofs_d.py" --layout layout.json --png
```

Ten pieces, each `aspect` (corner handles, ratio preserved), `free` (independent w/h) or `wide`
(a rule — width only): mountain drawing, hikers, title, date, GPS route, horizontal rule, legend,
distance/gain, elevation profile, axis caption. Drag to move, corners to resize, arrow keys to
nudge 0.01″ (Shift 0.1″), or type exact inches. Snap defaults to 1/8″. Dashed ghosts show where
a moved piece started.

**The round trip.** Move things → **Copy** → save as `layout.json` beside the script →
`proofs_d.py --layout layout.json` renders it for real. `place_parts()` maps each saved box back
to one transform per piece, so the editor never needs to know how a piece is drawn.

**A layout file is a staging post, not the destination.** It renders correctly but leaves the
source saying one thing and the picture showing another, so once a layout is settled the numbers
get wired into the constants in `design_d4` by hand and the JSON is thrown away. `layout.json` is
gitignored to stop a stale one outliving the source it contradicts.

### Cruxes

**20 · Never put SVG in a `<template>`.** Template contents are parsed as **HTML**, where
`<path/>` does not self-close — so all 80 paths of the mountain drawing nested inside the first
one and only that one rendered, while `getBBox()` reported a box a quarter of the right size.
The pieces are written straight into the live `<svg>`, where the parser is in SVG mode.

**21 · Measure before adding the hit target.** Each piece gets a transparent rect over its
bounding box so the whole box is draggable rather than only the hairlines under the cursor — but
measure first, or the target defines the box it is supposed to describe.

**22 · A rule is a line, so its box has no height.** `h/h0` is then a divide-by-zero and the
piece is ungrabbable. Degenerate axes are padded to 8 units, and the scale factors guard against
a zero denominator on both the JS and the Python side.

**23 · Handles are sized `4.5/Z`** so they stay constant on screen at any zoom, and pointer
positions come from `getScreenCTM().inverse()` rather than from arithmetic on the zoom factor.

Verified end to end: an element moved in the editor to (5.43, 1.355) at 3.00 in wide renders from
`--layout` at exactly (5.43, 1.355) × 3.00 in.

**24 · A layout file is only valid against the source that produced it.** Every box carries the
`x0/y0/w0/h0` it was measured from, so once the tuned numbers are folded into the constants the
same file would apply the move a *second* time. `layout.json` is deleted at the moment it is
wired in, not kept around.

### Round one, wired in

Six pieces moved; title, date, legend and stats stayed. The tuned values now live in one block
of module constants (`V_AT`, `HK_AT`, `ROUTE_AT`, `RULE_AT`, `PROFILE_AT`, …) rather than being
derived from each other — a derived layout silently re-flows the next time one of its inputs
moves, which is the thing hand-tuning is trying to stop.

| piece | move | scale |
|---|---|---|
| Mountain drawing | 1.06&Prime; left, 0.36&Prime; up | **1.20&times;** |
| Hikers | 3.52&Prime; left, 0.62&Prime; down — now under the type | **0.66&times;** |
| GPS route | 0.10&Prime; left, 0.19&Prime; up | — |
| Horizontal rule | 0.32&Prime; up | — |
| Elevation profile | 0.47&Prime; up | — |
| Axis caption | 0.39&Prime; up | — |

The header no longer pairs the drawing with the figures on one baseline: the figures group with
the title block by proximity and the drawing stands alone. Everything renders within **0.03 in**
of what was dragged.

### Round two — one numbering system

The Final Ridge marker was dropped and the switchbacks joined the numbered sequence, so the
letter keys are gone entirely and the sheet carries **one labelling system, 1-7**, ordered by
distance along the ascent.

Two consequences worth recording:

**25 · Staggering is now by crowding, not by kind.** The switchbacks begin *at* Trail Camp, so
4 and 5 sit 0.10 mi apart — 2.5 units apart on the profile. Previously 4 was a number (above the
line) and A a letter (below), and the split did the separating for free. With both numbered, the
profile places a key above the line unless it would land within 15 units of one already there,
in which case it drops below. On the map every key now shares one placement routine with the
full fan of directions available to any of them, rather than the fan being reserved for letters.

**26 · The legend hangs from the caption's baseline.** Its top is no longer a constant: it is
derived as `PROFILE_AT[1] + CAPTION_GAP - (len(pts) - 1) * LEGEND_LEAD`, so the foot of the
apparatus band stays one line however many landmarks there are. Adding or removing a landmark
now re-flows the legend upward from the bottom instead of running it past the sheet edge. This
is the one place a derived value is right — the alignment is the requirement.

**Open:** the legend reads `4 Trail Camp 12,039 FT` then `5 The 97 Switchbacks begin 12,000 FT`
— an ascending list that goes down 39 ft. The published figures disagree because the switchbacks
begin at Trail Camp and the two are quoted from different sources; the track has them at 12,058
and 12,078 ft, in the right order. Printing 12,039 for both would state the coincidence
correctly.

### Round three — the rule comes out

The hairline between the map and the apparatus band was removed; the band is now held together
by the shared baseline at its foot and separated from the map by whitespace alone. That drops
the movable pieces from ten to nine and settles one of the open questions above, since the
rule's right end was the odd one out. Two right edges remain: the route and profile at 1023.4,
the distance/gain block at 1015.

### Round four — the switchbacks come out

`The 97 Switchbacks begin` was dropped, leaving six landmarks, 1-6. The legend re-flowed on its
own: its top is derived from the axis caption's baseline, so losing a row moved it 25 units down
rather than leaving a gap at the foot — which is what crux 26 was for.

Two things resolved themselves with it. The legend no longer reads `12,039 FT` then `12,000 FT`
on consecutive ascending rows, since that was the switchbacks quoted from a different source than
Trail Camp. And the profile's crowding rule no longer fires: with the switchbacks gone, no two
landmarks fall within 15 units of each other, so every key sits above the line. The rule stays in
the code because it is what makes the legend safe to edit.

---

# Print files

```bash
uv run python "Project Docs/Plans/strava-data/whitney/print_ready.py"
```

Writes `whitney_11x14.{pdf,svg,png}`. The PDF is the deliverable: **11.00 × 14.00 in exactly**
(MediaBox 792 × 1008 pt), three embedded font subsets, no background. Set up for **one ink on
cream stock**, so no bleed is needed — no ink comes within half an inch of the trim.

## 27 · `vector-effect="non-scaling-stroke"` is a trap, and it had been lying for weeks

The drawings sit inside a `scale()`, so they need their stroke weight held independent of that
scale. `non-scaling-stroke` looks like exactly the right tool. **Chromium pins it to DEVICE
pixels**, which means:

- the same file rendered darker in a screen preview than at 300 dpi — the drawing got *lighter
  the higher the output resolution*;
- rasterised as an `<img>` rather than opened as a document, the hikers produced **zero ink**
  and vanished entirely.

Measured, rendering as a document at 3×, against strokes with the scale folded in:

| region | as shipped | correct | |
|---|---|---|---|
| Mountain drawing | 28,642 px | 78,231 px | **+173%** |
| Hikers | 1,235 px | 14,791 px | **+1098%** |
| GPS route (no `scale()`) | 97,814 px | 97,814 px | 0% |

So **every proof PNG in this folder's history had under-weighted artwork**, and the design was
art-directed against it. `proofs.art_at` now divides the width by the scale and emits no
`vector-effect` at all, so a weight means the same thing at every resolution and in every
renderer. The art weights were then re-chosen against the honest render: `ART_VIGNETTE = 1.0`
and `ART_HIKERS = 1.2` units (0.25 / 0.30 mm), which matches what had been approved on screen
while clearing the practical minimum for ink on uncoated stock. `print_ready.bake_strokes` still
exists and now finds nothing to do — it is a guard, not a step.

## 28 · A PNG with no `pHYs` chunk has no size at all

`page.screenshot` writes none, so 3300 × 4200 opened as **45.8 × 58.3 in at 72 dpi**. A shop
would print it at the wrong size or bounce it. `tag_png_dpi` inserts the chunk after IHDR.

## 29 · The sans was never Helvetica Neue

The stack is `"Helvetica Neue", Helvetica, Arial` and Helvetica Neue is not installed on this
machine, so all 38 sans elements have been set in **Arial** throughout — as the PDF's embedded
`ArialMT` and `Arial-BoldMT` confirm. A Mac at the print shop *would* have Helvetica Neue, take
the first branch, and reflow every right-anchored elevation in the legend. Embedding the fonts
that were actually used is what makes the page deterministic; the SVG is for editing, not output.

## 30 · One right margin

The lower band had drifted onto three right edges — route 1023.6, profile 1023.3, distance/gain
1015 — because the 1/8 in snap grid in the layout editor does not contain 1015, so anything
sitting on the old margin jumped when it was dragged. `RIGHT = 1023.4` is now a single constant;
the profile's left edge is derived from it (`RIGHT - 545`) and the distance/gain block is
anchored to it. Both land on 1023.40 exactly.

The route's ink edge is 1023.60, 0.2 units out, and stays there: that edge is wherever landmark
1's callout circle happens to fall, so pinning it would mean shifting the whole map to suit a
bubble. 0.2 units is 0.002 in — 0.05 mm.
