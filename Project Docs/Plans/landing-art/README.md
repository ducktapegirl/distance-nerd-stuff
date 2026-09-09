# Landing tile art — the twelve directions

The exploration record behind the two artworks on
[`running-log/index.html`](../../../landing/art.py). The brief is
[`../landing-art.md`](../landing-art.md); this directory is what answered it.

```bash
uv run python tools/proof_landing_art.py   # the 14 SVGs + proofs.html
uv run python build_landing.py             # the page that ships
```

`proof_landing_art.py` is **not** wired into any build or workflow — same
treatment `proof_year_art.py` gets. It reads `running-log/running_log.csv` and
`strava-data/data/` directly.

## What shipped

| Tile | Direction | Size |
|---|---|---|
| College Running Log | **A1 Ring of Seasons** | 5.9 KB |
| Strava Dashboard | **B3 Route Grid** | 23.5 KB |

Circle against grid: one large organic form beside a regular field of small
ones. Constraint #4 in the brief is that the two tiles are tellable apart at a
glance at 240 px, and that is a property of the *pair*, not of either tile — so
`proofs.html` ends in a 6×6 pairing matrix, which is the part that actually
decided it.

## The proofs

Every direction from §4 of the brief, plus a variant of A2 and of B4. Each is
rendered from the real data at the tile's true 640×480 frame.

| File | Direction | Notes |
|---|---|---|
| `a1.svg` | **Ring of Seasons** — shipped | Four concentric academic years, thickness = weekly miles |
| `a2.svg` / `a2b.svg` | Woven Weeks | 192 week-rows against 7 day-columns; `a2b` is two weeks to a row |
| `a3.svg` | Pace Ribbon | The weakest of the six — see below |
| `a4.svg` | Constellation | Dot per run at (day of year, minutes); the summer voids are the subject |
| `a5.svg` | Ink Strata | A ruled band per month, density = volume |
| `a6.svg` | Typographic mass | The log's own comments as texture; the most personal option |
| `b1.svg` | Route Bloom | 110 routes rotated to their day of year |
| `b2.svg` | Contour Field | 40 elevation profiles as an occluding horizon |
| `b3.svg` | **Route Grid** — shipped | 48 routes, 8×6 square cells, colored by sport family |
| `b4.svg` / `b4b.svg` | Signature Route | The 4.4 mi loop run ~20 times; `b4b` ghosts every repeat behind it |
| `b5.svg` | Tangle | 150 routes head to tail as one unbroken line |
| `b6.svg` | Sport Palette Bands | The weakest of the six — see below |

`proofs.html` is the contact sheet — each tile at 640 and 240 px, a light/dark
toggle, a measured byte count against the 40 KB budget, and the pairing matrix.
It is **gitignored**; rebuild it to view.

## Three things the brief got wrong or did not say

**`strava-data/data/streams/` is not gitignored.** §6 of the brief claimed it
was and built a three-way decision on it; `git ls-files` returns **379 tracked
files**. CI, fork PRs and fresh clones all have the geometry, so there is no
`tools/gen_landing_art.py` and no committed asset — `data.load_strava()` reads
the streams directly. The `gen_journey.py` / `gen_poster_glyphs.py` precedent
does not apply, because *their* sources genuinely are not in the repo.

**The tile is 4:3, not square.** `.tile-art-wrap` is `aspect-ratio: 4 / 3` and
`slice`s, so a square 480×480 artwork loses 12.5% off the top and the same off
the bottom — fatal for anything centered and circular, which A1 is. Everything
here is authored 640×480.

**The ~40 KB budget forces subset selection.** Measured: all 351 routes at
`step=12` is ~595 KB; all 374 elevation profiles is ~192 KB; 1,138 `<circle>`
elements for A4 is ~57 KB. A4, B1, B2, B3 and B5 all ship subsets because of it.

## Two directions that rendered broken, and why

Both are traps any future tile can fall into, so they are worth keeping:

- **B2 Contour Field** stroked its closed occluder polygon, so every ridge drew
  its baseline and both vertical sides as well and the stack came out as 44
  boxes rather than a horizon. Fill and stroke have to be **separate elements**
  — which doubles the path data, so the resolution has to come down to pay for
  it (48 points, 40 ridges, integer coordinates).
- **A5 Ink Strata** hatched near-vertically across bands only `480/46 = 10.4`
  units tall, so each rule drew a 10-unit stub and stopped; since every band
  carries its own pattern, the stubs did not line up across the boundary and the
  tile rendered as a field of falling dashes. Hatching must run *along* a thin
  band. Tilting it a few degrees per academic year — to make the four years read
  as separate beds — then put a large moiré fan over every tilted band, so the
  tilt was dropped too.

## The two that lost on their own merits

**A3 Pace Ribbon** is the weakest college option and the brief predicted it
("may read as a chart"). It does not even manage that: weekly pace swings
further than the whole plotted range, so the ribbon shreds into vertical spikes
and reads as noise. A three-week centered smooth helps and is still not enough.

**B6 Sport Palette Bands** reads as pastel stripes. The narrow families only
ever show a sliver of a route, and `other` — climbing, pickleball, the gym — has
no route worth showing, only GPS jitter.

## A known limitation of the shipped grid

About 11 of the 48 cells draw as near-straight. The per-family quota is **not**
the cause: all 48 clear the `0.38` squarishness bar with room to spare (185 of
216 running routes qualify for 30 slots), so raising the threshold changes
nothing. Bounding-box squarishness simply cannot see a straight line — an
out-and-back that drifts sideways has a square box and one stroke.

The metric that does catch it is **tortuosity** (path length ÷ box diagonal,
where ~1.4 means out-and-back), but ranking by it selects for lapping a small
area: the sheet fills with the same neighborhood loop three times and the same
track oval three times, and only 8 of 48 picks stay the same. A proper fix is
tortuosity **plus** a duplicate test — `poster_40for40.py`'s 100 m grid-cell
Jaccard comparison, applied in reverse. Weighed against a handful of honest
point-to-point cells, that was judged not worth the build time.
