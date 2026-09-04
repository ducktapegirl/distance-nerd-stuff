# Strava on e-paper: display ideas for the reTerminal Sticky

**Status:** 61 ideas built as 63 cards (16 in the device rotation) · **Created:** 2026-09-03 ·
**Updated:** 2026-09-03 (merged the `uoiv93` plan: entries 57-62 added, 52 rewritten; then owner
review: footers dropped, 38 retired, 21 redesigned, 59's icon replaced) · **Owner:** unassigned

Companion to the code in `strava-data/feed/` and the entrypoint `strava-data/build_feed.py`.
This document is the idea catalogue; the code is the subset that already runs.

---

## Why

The repo has exactly one output path today: a 3.3 MB interactive HTML dashboard
(`running-log/strava.html`) built for a browser — Plotly, hover, tabs, light/dark themes, a WebGL
map. None of that survives on an ePaper panel. Publishing Strava numbers to a **reTerminal Sticky**
via SenseCraft HMI is therefore a genuinely new output target, not a re-skin of the dashboard.

## The device

**reTerminal Sticky** — 3.97", 800×480, 4-level grayscale ePaper, 235 PPI, capacitive touch,
ESP32-S3, magnetic mount, ~7-day standby.

Three facts drive every design decision below:

1. **It is dense, not coarse.** 800×480 across 3.97" means the whole screen is about **3.4" × 2.0"**,
   so **1 mm ≈ 9.3 px**. A 12 px label is 1.3 mm tall — invisible. This is the opposite of the usual
   "small screen = low resolution" intuition, and it is the single most important constraint.
   Working floors: **text ≥ 26 px, strokes ≥ 3 px, headline numerals 84–110 px**.
2. **It is a fridge magnet, not a monitor.** The Sticky's premise is a magnetic note board glanced
   at in passing. That argues for **one idea per screen** and against porting any multi-panel
   dashboard layout. With ~7-day standby the refresh cadence is hourly at best, so content should
   rotate on a **daily** clock, not a live one.
3. **Four tones, no colour.** White / light / dark / black, plus ordered dithering for the steps
   between. Enough for a real sequential ramp; nowhere near enough for the dashboard's teal/amber
   `SPORT_COLORS`, which must be re-tabled as **tone + pattern + shape**.

## What SenseCraft HMI can consume

Per Seeed's docs, the platform offers Gallery, Canvas, **RSS** and **Web** functions. Two are useful
here and the prototype publishes to both:

| Transport | What we publish | Notes |
|---|---|---|
| **RSS function** | `feed.xml` — RSS 2.0, one item per card | Title = the fact; description = one sentence of context. No HTML, no CDATA, no enclosures — assume the reader shows plain text only. |
| **Web function** | `epaper.html` — one 800×480 card, static | No JavaScript, no CDN, no webfonts, no scrolling. |
| *(escape hatch)* | `feed.json` | For HMI Canvas or anything else later. |

All three land in `running-log/`, which is already the GitHub Pages publish root, and are gitignored
exactly like `index.html` / `strava.html` — generated output never collides with committed data.
Deployed URLs are `https://ducktapegirl.github.io/distance-nerd-stuff/{feed.xml,epaper.html}`.

`epaper-all.html` is a fourth output: every card stacked in one scroll, for previewing the whole
rotation. The panel never loads it.

## Cadence caveat

`strava-fetch.yml` runs on `0 6 1,15 * *` — **twice a month**. A card that says "last 7 days" can be
up to 15 days stale. The build deliberately treats **the last day with data**, not the wall clock,
as "today" so nothing lies about freshness; but if these cards are meant to feel live, that cron
wants bumping to daily. Left unchanged: it changes Strava API usage, which is the owner's call.

---

## The icon and graphic system

One 1-bit vocabulary, authored as **inline SVG generated in Python** (`strava-data/feed/svg.py`) —
no icon font, no CDN, no JS. Three tiers:

- **Sport glyphs** (~56–130 px): runner, bike, shoe, mountain — solid silhouettes with chunky
  strokes. Interior detail below ~3 px vanishes on ePaper, so these are strokes, not outlines.
  Still to draw: hiker, ski, climber, paddle, skate, racket, dumbbell.
- **Data-glyphs** — icons that *are* the chart. A shoe whose sole fills with mileage; a mountain
  whose base fills with the fraction of a summit; a dial whose needle is the load ratio. These
  carry more than decorative icons do, and they are the reason `glyph_shoe` and `glyph_mountain`
  both take a `fill_frac`. **The fill is a lighter tone than the outline on purpose** — filled solid
  black, a full shoe loses its silhouette and reads as a blob.
- **Tone ramp** — the panel's four native greys (`#000` / `#555` / `#AAA` / `#FFF`) extended with
  three ordered-dither `<pattern>` fills, giving a 7-step sequential ramp (`svg.RAMP`, `svg.tone()`).
  Every fill snaps to one of those seven so nothing depends on the device dithering an arbitrary
  colour for us. **Encode categories by shape and pattern; reserve tone for quantity.**

Type: one weight of a bundled-everywhere sans (Helvetica/Arial — the panel has no webfonts), all-caps
26–30 px labels with wide tracking, and hairline rules instead of boxes. ePaper renders a 3 px rule
beautifully and a 1 px one not at all.

Two constraints the code enforces rather than documents:
`svg.text()` **raises** below 26 px, and `svg.fit_text()` shrinks-then-ellipsizes against a character
budget (there is no text measurement at build time, so widths are approximated at ~0.55 × font size).

---

## The catalogue

61 ideas, **all of them now built** as 63 real `card_*` functions — ideas 3 and 19 each build more
than one. **[ROTATION]** marks the fifteen ideas (sixteen cards) the device cycles through daily,
hand-picked 2026-09-03; **[CATALOGUE]** ones exist, render, and ship in `feed.xml`, on the proof
sheet and at their own `epaper/<id>.html`, but are held back from the panel. Every recipe was checked
against the real data; the numbers quoted are live as of the 2026-08-30 fetch.

### A · Right now — state you would glance at

1. **[CATALOGUE]** **Load gauge** — ACWR (7-day ÷ 28-day mean daily suffer score) on a four-band dial:
   `<0.8` detrained, `0.8–1.3` steady, `1.3–1.5` spiking, `>1.5` danger. Same quantity the
   dashboard's V8 chart plots, reduced to the one number you would actually glance at.
   *Today: **1.37**, spiking.* Bands get monotonically more ink as risk rises, so the ramp reads as
   a gradient of concern with no colour key. Needle stops at 60 % of the radius so it never crosses
   the readout.
2. **[CATALOGUE]** **Days since last activity** — one enormous numeral; the whole screen is the number. Trivial off
   `streaks()["days_since"]`.
3. **[ROTATION]** **Last activity** — three cards off one idea. `last` is the words (name and
   description, typographically); `last-route` is the shape alone; **`latest` is both** — the GPS
   track across the top with a 4x2 grid of its own numbers beneath, and it is the one that rotates.
   On a fridge magnet the map and the numbers want to arrive together. The dashboard's
   `_activity_detail_json` already emits these fields, pre-formatted.
4. **[CATALOGUE]** **Rolling 7-day totals** — miles + hours + feet as three big numbers. `totals(window(acts, 7))`.
5. **[CATALOGUE]** **Fresh / cooked** — a single word from ACWR + days-since, with a face-glyph. The most
   "fridge magnet" idea in the list, and **demoted out of the rotation** when the merged plan landed:
   a readiness verdict computed from data that is at most a fortnight fresh describes the fetch cron
   as much as the athlete. The companion "rest nudge" card was cut for the same reason.
6. **[CATALOGUE]** **Last activity's route** — as #36 but pinned to the most recent GPS activity rather than rotating.

### B · Streaks and consistency

7. **[CATALOGUE]** **Active-day streak** — consecutive days with an activity. *Current 1, longest ever 7.*
8. **[CATALOGUE]** **Rest-day counter** — days since the last full rest day; the inverse framing, and for this
   athlete (355 active days of 687) the more interesting one.
9. **[ROTATION]** **Last-30-days strip** — 30 cells, filled = active. *17 of 30.* Rendered as **two rows of
   15**, not one row of 30: at 800 px a single row forces 20 px cells (~2 mm) that vanish at arm's
   length.
10. **[CATALOGUE]** **Week-shape bars** — 7 bars Mon–Sun, this week's miles against the 8-week median as a ghost outline.
11. **[CATALOGUE]** **Consistency ratio** — active ÷ elapsed days, all-time (355/687 = 52 %) as a split disc.
12. **[CATALOGUE]** **Day-of-week fingerprint** — 7 bars. *Sunday 70, Wednesday 55, Saturday 43.* Counterintuitive
    (Saturday is the **least** active day) and therefore worth a card.
13. **[CATALOGUE]** **Longest streak vs current** — two bars racing. Only interesting when the gap is small.

### C · Volume and progress

14. **[CATALOGUE]** **YTD vs the same date last year** — *536 mi vs 489 mi.* Two bars plus a delta pill.
15. **[CATALOGUE]** **This month vs the 12-month median** — a thermometer that fills. *Aug 58 mi against a ~70 mi median.*
16. **[CATALOGUE]** **Rolling 12-month odometer** — *880 mi*, digits in mechanical odometer boxes,
    `MILES · LAST 365 DAYS` beneath. Footer carries activities / feet / moving hours.
17. **[ROTATION]** **Monthly sparkline** — 13 months of miles as a 3 px step line, no axis, a dot on "now".
18. **[ROTATION]** **Elevation as landmark** — *126,355 ft = 4.4 × Everest*, drawn as four solid peaks plus
    a hollow fifth filled to 0.4 of a summit, clipped to the silhouette so the partial never spills
    past the slopes. The most poster-like card in the set.
19. **[ROTATION]** **The Journey ladder** — see the expanded section below.
20. **[ROTATION]** **Sport split** — last 365 days: *Run 70, MTB 68*, everything else trailing. Worth showing
    precisely because it is a dead heat.
21. **[ROTATION]** **Hours in motion, as a tally** — *285.9 moving hours* as a 12-hour dial wound N times round.

### D · The racing self — segments

22. **[CATALOGUE]** **Latest PR** — segment name, time, date, effort number, and the effort count as
    five-bar tally gates. *"Oops, I crapped my pants on Lenkeit bridge", 0:10 on effort 21.* The
    segment names are half the appeal; `fit_text` exists largely for them.
23. **[CATALOGUE]** **PR pace** — PRs set in the last 30 / 90 / 365 days as three counters. *30 / 135 / 500.*
    Currently the footer of #22; deserves its own card.
24. **[CATALOGUE]** **Home-segment leaderboard** — top 5 by effort count with best times, as a scoreboard.
    *Canyon entrance via Salix ×36, Salix out to PV ×29, Lenkeit bridge ×21.*
25. **[CATALOGUE]** **Most-improving segment** — biggest negative `recent_trend` among segments with ≥5 efforts.
    *Lex Town Track, −40.7 %.*
26. **[CATALOGUE]** **Most-declining segment** — the honest inverse. *Tree Y/T 1 split, +48.7 %.* Ships with a
    self-deprecating caption or it is just mean.
27. **[CATALOGUE]** **Segment consistency spotlight** — reuse `rollups_cards.seg_consistency_picks`; show the
    coefficient of variation as a dot scatter of every effort.
28. **[CATALOGUE]** **Repeat-offender counter** — one segment, its count as tally marks. The tally renderer from
    #22 already handles up to 40.
29. **[CATALOGUE]** **The crossover fact** — reuse `chart_seg_grade_vs_time`: the grade at which running overtakes
    mountain biking. A one-sentence card, no chart.

57. **[ROTATION]** **Segment of the month** — whichever segment saw the most efforts in the last 30
    days (ties break on lifetime efforts), with best / latest / trend, and a sparkline of the last
    24 effort times **plotted inverted** so a rising line means getting faster. *Darkwood Lite,
    4x in 30 days, best 2:44, +10% slower lately.* Ported from the `uoiv93` prototype.

### E · Gear — the most actionable category

30. **[CATALOGUE]** **Shoe mileage bars** — one row per non-retired shoe: data-glyph, name, filled bar,
    `mi / limit`. Threshold comes from Strava's own replacement reminder, else 400 mi.
    **Units trap:** `notification_distance` arrives in the athlete's *display* units (400, 450, 0 —
    only coherent as miles against a 470-mile shoe), while `distance` is metres and
    `converted_distance` is miles.
31. **[CATALOGUE]** **Retire-me alert** — reversed out of the full black bar in white, so
    the alert needs no extra row height and cannot collide with the shoe below.
    *ASICS DS Trainer at 470 mi against a 450 mi threshold — over.* The one genuinely **useful**
    card here.
32. **[CATALOGUE]** **Bike odometer** — *Wile E. Coyote, 250.2 mi*, a bike glyph with a filling frame.
33. **[CATALOGUE]** **Gear graveyard** — the retired ASICS and its description: *"last of its kind. I've purchased
    the same shoe for 15 years."* Pure personality, zero computation.

### F · Places

34. **[CATALOGUE]** **Passport counter** — *28 regions, 9 states and provinces*, via the dashboard's
    `_count_regions` (10 km greedy clustering) and `_count_states` (39-box lat/lng table).
35. **[CATALOGUE]** **Two homes** — *San Diego 782 mi vs Boston 530 mi*, two route thumbnails side by side.
    Reuse `_home_stats` and `_home_thumb_tracks`.
36. **[CATALOGUE]** **Route of the day** — one activity's GPS path, chosen deterministically by date so it
    changes daily with no device-side state. Reads **one** streams file, not the 42 MB directory.
    Latitude degrees are ~1/cos(lat) wider on the ground than longitude degrees, so the path is
    cosine-corrected or it comes out squashed; it is then fitted to the card's **rectangle**,
    preserving aspect — letterboxing a wide, flat route into a square wastes most of the card.
37. **[ROTATION]** **Route mosaic** — 32 thumbnails in an 8×4 grid, rotating daily out of all 348 GPS tracks.
    Abstract, and dense pixels are exactly what this panel is good at.
38. **[RETIRED]** **Home density** — San Diego route density, dithered rather than glowed. Bins every 15th
    point of every track (21,666 points) over the extent the data occupies; binning *start* points
    over the whole home box put every ride in one cell. **Retired on owner review** and removed
    from the build: a 12x12 grid of 21 px cells has to stay square, so it can never use more than
    the body's height on a 5:3 panel, and at that size the three dither patterns stop being
    distinguishable from each other. `places.raw_points_in`, which existed only for this card,
    went with it.
39. **[CATALOGUE]** **Compass extremes** — *northernmost 49.3°N, easternmost 70.2°W, highest 14,507 ft*, from the
    pinned `_PEAKS_DEF` record book.

### G · Weather and environment

40. **[CATALOGUE]** **Temperature range** — trained from *−14.5 °C to 32.7 °C* (**6 °F to 91 °F**). A thermometer
    with two marks.
41. **[CATALOGUE]** **The heat verdict** — reuse V4: pace degrades with heat, heart rate does not. One sentence.
42. **[CATALOGUE]** **UV exposure** — *max 8.7*; a sun glyph whose ray count is the index. Note `uv_index` is
    time-of-day resolved, not a daily max (a 07:34 run reads 0.1).
43. **[CATALOGUE]** **Dark o'clock** — *22 starts before 8 a.m., earliest 03:17.* A moon/sun split glyph.

59. **[ROTATION]** **UV this week** — sum of `uv_index x moving hours` over the ISO week, as a
    seven-cell day strip under one big number, beside a sun whose disc darkens toward 20 UV-hours.
    Only 339 of 374 activities carry a UV value; the rest are excluded rather than counted as zero,
    which would quietly understate every week that had an indoor session in it. Pairs with #42,
    which is a lifetime max rather than a dose.

### H · Records and superlatives

44. **[CATALOGUE]** **Record book** — the six pinned `_PEAKS_DEF` rows, one per rotation day, each a full-screen fact.
45. **[CATALOGUE]** **Longest ever** — longest run, longest ride, biggest climb day.
46. **[CATALOGUE]** **Kudos leaderboard** — *"Snow Snake 🐍", 12 kudos.* Small and human.

### I · Memory

47. **[CATALOGUE]** **On this day** — same month/day in prior years. **Sparse**: the dataset only spans 2024–2026,
    so most days have exactly one hit. Must degrade to "nothing on this day — here is the nearest".
48. **[CATALOGUE]** **A year ago this week** — a wider, far more reliable window than #47. Prefer this one.
49. **[CATALOGUE]** **First ever** — the first activity in the dataset, framed as an origin story.

60. **[ROTATION]** **This week in 2004** — the same ISO week in the paper-era log against this one:
    miles, average pace, and up to four workouts with a race flag, the old log in a shaded band
    behind the present. The CSV's `week_of_year` is already the ISO week, so it joins straight onto
    `date.isocalendar()`. Ported from the `uoiv93` prototype.
61. **[ROTATION]** **Race anniversary** — a race from the 2003-07 log whose calendar date falls within
    +/-7 days of today (else the next one coming up): "21 years ago today", the distance, the finish
    time as the headline, and what she wrote about it afterwards. **The one card keyed to the wall
    clock** rather than to the last day with data — an anniversary that arrived while the fetch cron
    was asleep is still an anniversary.

### J · Voice and whimsy

50. **[CATALOGUE]** **The joggernaut byline** — the Strava bio (*"I'm the joggernaut, bitch"*) as a masthead.
    Already the RSS channel description.
51. **[CATALOGUE]** **From the logbook** — an activity title and its description, typographically, rotating
    daily. Picks only from activities that *have* a description (291 of 374). Zero charts, maximum
    charm — the titles are genuinely funny ("Oooh, clockwise!", "🦌", "Saw a massive coyote, hazed
    it, then almost fell into a small ravine while looking at it sideways and running forwards").
52. **[ROTATION]** **Wildlife scoreboard** (`wildlife`, was `animals`) — titles and descriptions matched
    against an animal word list, as a two-column board of icon + bar + count. *24 activities, 27
    mentions across 10 species, led by coyote ×7.* Matching is now **whole-word with an optional
    plural**, ported from the `uoiv93` prototype along with its animal silhouettes: the original
    substring test counted "slowly" as an owl and "sealed" as a seal, which is where the old
    "29 activities" came from. Silly, cheap, and yours.
53. **[CATALOGUE]** **Emoji-title census** — how many activity names are pure emoji.

58. **[ROTATION]** **Activity-name hall of fame** — five of the 242 activities that got a real name
    rather than "Morning Run", scored on punctuation, length, kudos and emoji, in a window that
    moves by ISO week. Names wrap to two lines rather than truncating: the names *are* the card.
    Ported from the `uoiv93` prototype.
62. **[ROTATION]** **Daily haiku** — a 5-7-5 assembled from the newest activity's own numbers, with no
    model and no network: a fixed vocabulary, ~18 templates per line, and a vowel-group syllable
    counter that decides which of them scan today. Seeded by the activity id, so the same ride
    always writes the same poem. Templates naming an animal drop out unless that activity actually
    recorded a sighting, and templates counting miles drop out for a zero-distance session — the
    card should not invent a hawk it did not see.

### K · Meta and data-nerd

54. **[CATALOGUE]** **Dataset stats** — *374 activities, 687,776 GPS points, 42 MB of streams.* A card about the data.
55. **[CATALOGUE]** **Device timeline** — *Forerunner 255S ×364, 255 ×9, Strava App ×1.*
56. **[CATALOGUE]** **Lap splits** — the first use of the **unconsumed `laps/` data** (374 files, 1,356 rows): the
    last activity's mile splits as a bar ladder. Note 79 files hold a single whole-activity lap, so
    only ~295 activities have anything to show, and `1.609 km` laps mean auto-lap is set to miles.

---

## The Journey (idea 19), expanded

Cumulative mileage as a road trip out of **92129**, following **real interstate geometry**.
Running heads east on I-8 → I-10 → I-40 to **Boston** (3,009 mi); riding heads southeast on
I-8 → I-10 to **Austin** (1,345 mi). The two corridors share **1.1 %** of their geometry, so the
cards read as genuinely different journeys rather than the same picture twice.

**Where the data sits today** (all-time totals — a journey must never run backwards, so this uses
the monotonic all-time figure, not a rolling window):

| | total | past | next | to go | of the route |
|---|---:|---|---|---:|---:|
| **Running** (`Run` + `TrailRun`) | 880 mi | Albuquerque (854) | **Amarillo** (1,138) | 258 mi | 29 % |
| **Biking** (`MountainBikeRide` + `Ride` + `EBikeRide`) | 549 mi | Phoenix (343) | **Las Cruces** (695) | 146 mi | 41 % |

**How the route is built.** `strava-data/tools/gen_journey.py` pulls Natural Earth's
`ne_10m_roads` (~50 MB, never committed — the same treatment `gen_basemap.py` gives its sources),
keeps the 2,015 US major-highway segments, welds their endpoints into a routable graph, and
shortest-paths from 92129 to each destination. It writes
`strava-data/assets/journey_routes.json` (25.7 KB): the routed polyline, its cumulative mileage,
and the cities the road passes. **The dashboard build does no routing and no network I/O** — it
reads that asset.

Two things the graph build gets wrong if you are not careful, both of which cost a debugging pass:

- **Plain grid-rounding does not weld the network.** Natural Earth is a cartographic layer, not a
  routing one: segment endpoints are near-coincident rather than identical. Rounding coordinates to
  a grid leaves two endpoints 1 km apart in different cells, which shattered the network into 229
  components and made obviously reachable cities unroutable. The fix is a spatial hash that
  searches the 3×3 cell neighbourhood (`Welder`, 0.02° tolerance).
- **Snap only to the largest component.** Even welded, a few hundred orphan clusters remain. Salt
  Lake City and Austin both snapped into one and returned a silent "no route".

**The measured distances validate the old guesses.** The previous version of this card used a
hand-maintained ladder of estimated road distances. Routed against real highways: Boston 3,009 vs
the guessed 3,000, Chicago 2,059 vs 2,080, New York 2,804 vs 2,780, Salt Lake City 757 vs 750 —
thirteen of fifteen within ±7 %. The outliers were Los Angeles (−15 %) and Phoenix (+17 %), where
Natural Earth's coarse geometry cuts corners. The ladder is gone; mileposts are now whatever cities
the road actually passes, at measured distance, so nothing is hand-maintained. To send a journey
somewhere else, edit `CORRIDORS` in `gen_journey.py` and re-run it.

**Layout — the map + milepost hybrid.** Headline mileage and "N MI TO ⟨city⟩" in the left column;
a small orientation map top-right with the travelled portion solid and the road ahead dashed, and a
dot at the current position; a full-width milepost strip beneath with filled (passed) and hollow
(ahead) stations and the sport glyph riding the line. Two registers: the map answers *where*, the
strip answers *how far*.

Three details that are load-bearing rather than cosmetic:

- **Both maps frame on a fixed continental extent** (`geo.CONUS`), not on their own route's
  bounding box. The bike corridor is a thin east-west band, so a tight frame renders an
  unrecognisable sliver. The map is for orientation only, so a consistent, recognisable silhouette
  beats filling the box.
- **Basemap strokes are solid greys, never `svg.tone()`.** A dither pattern used as a *stroke*
  renders as a dotted chain and turns a coastline into noise.
- **`svg.polyline` gained a `dash` argument** for the road ahead.

**Anchorage was dropped.** It sat outside the basemap's clip box (61°N against a clip at 55°N), and
the bike corridor now ends at Austin regardless.

## The proof sheet

`epaper-all.html` is the browsing surface: every card rendered at real size, grouped into rolls by
family, each proof carrying its catalogue number, RSS title and data recipe, and a mark for whether
the device actually cycles it. It is generated by the same build as the cards, so it cannot drift
from what ships.

## What the build ships

`strava-data/feed/` — `config.py` (panel constants, tone ramp), `metrics.py` (pure computation),
`journey.py` (the destination ladders), `places.py` (region clustering, home boxes, the record
book), `stats.py` (OLS and coefficient of variation), `svg.py` (primitives, dither, glyphs, the
`Card` container), `layouts.py` (eleven composable card layouts), `fmt.py` (portable date
formatting — `%-d` is a glibc extension and raises on Windows), `cards.py` (64 builders — 62 ideas,
with idea 3 building three cards and the Journey ladder two), `rss.py`, `page.py`. Entrypoint
`strava-data/build_feed.py`, wired into `deploy.yml` and `pr-checks.yml` after the two existing
builds. Inputs are `strava-data/data/` **and** `running-log/running_log.csv`, the paper-era log,
which entries 60 and 61 read.

Every card also ships as its own page at `running-log/epaper/<id>.html`, so one card can be pinned
on the device by URL. There is no `?card=` query and there cannot be one: the panel runs no
JavaScript, so the choice is made at build time or in the URL.

**Layouts came first, on purpose.** Sixty-four hand-laid-out cards would have drifted apart within a
week; eleven layouts (`hero_number`, `stat_trio`, `bar_rows`, `bar_grid`, `two_up`, `text_card`,
`spark`, `cell_grid`, `dial`, `route_card`, `route_stats`, `then_now`) carry the shared structure so
`cards.py` is mostly data binding.

**Cards carry no footer.** Every card used to end with a line of context above a hairline rule -
"no axis on purpose", "11.9 full days · 23 times round". Dropped on owner review: a fridge magnet
glanced at in passing gets one fact, and the sentence of context already exists in the RSS
`<description>` with the provenance in the card's `recipe`, both of which the proof sheet shows
under each proof. `BOT_RULE` survives as the bottom bound of the body and nothing is drawn on it;
the layouts took back the 32 px.

**Verification is `tools/epaper_check.py`**, not a squint at the proof sheet. It measures every card
at 800x480 for text under 26 px, effective strokes under 3 px, overlapping text and off-panel
drawing. The overlap check earns its keep: hand-placed absolute layouts with no reflow mean a longer
activity name prints one label straight through another while every other check still passes — which
is exactly how it found a pre-existing bug in the record-book card.

**`feed/` deliberately does not import from `dashboard/`.** `geometry_stats.py` and
`charts_places.py` hold equivalent maths, but both pull in plotly and `dashboard/config.py` (which
loads dotenv and reads `MAPTILER_KEY`). The cost is duplicated reference data — the state boxes,
home boxes and the peaks record book are copied into `places.py` and **can drift** from the
dashboard's copies. Hoisting them into `nerd_common/` is the right fix and is out of scope here.

Deliberate non-choices: **no Plotly** (needs JS and a CDN, emits anti-aliased colour, assumes hover),
**no JavaScript at all** in the page, and **whole-card SVG at exact user units** rather than CSS
layout, so nothing depends on the cascade or on font metrics.

### Verified

Build is stdlib + numpy, no network, 1.7 s. RSS parses with 57 unique GUIDs, RFC-822 dates and no
HTML in descriptions. Rendered at exactly 800×480 in Chromium, **all 57 cards**: minimum text 26 px,
minimum effective stroke 3.00 px (accounting for `scale()` on glyph groups), scroll extent exactly
800×480, and no text clipped past a card edge. Quantized to the panel's four tones every card stays
legible, with 2–28 % ink coverage. No metric display units (`km`, `km/h`, `°C`) in any output.
Numbers spot-checked by hand against the CSVs for the weekday fingerprint (Sunday 70 / Saturday 43),
the segment leaderboard (36 / 29 / 21) and the heat verdict (43 s/mi, +1 bpm). Both existing
dashboards still build and `running-log/qa.py` passes 13/13.

Four bugs the sweep caught and fixed, worth knowing because they are the kind that recur:
`fit_text` ignored letter-spacing, so any fitted string drawn with tracking could overrun its box;
`cell_grid` used a hardcoded 10 px vertical gap while honouring `gap` horizontally, overflowing the
card; `by_weekday` built names as `"Tue" + "day"`; and the home-density card binned *start* points
over a one-degree box, so every ride landed in a single cell — it now bins every 15th point of every
track over the extent the data actually occupies.

## Next steps, in rough order of value

1. **#48 A year ago this week**, **#24 home-segment leaderboard**, **#14 YTD vs last year** — high
   interest, all pure `activities.csv`, no new plumbing.
2. **#56 lap splits** — retires the "fetched but unconsumed" note on `laps/`.
3. ~~Bump the fetch cron~~ — done 2026-09-03: every 3 days, with a daily
   site rebuild so the card of the day actually advances.
4. **Portrait mode.** The Sticky has an accelerometer. If SenseCraft exposes orientation, a 480×800
   variant is worth having — but the renderer is currently hardcoded to 800×480 in `config.W/H`, so
   this means making the card layouts size-parametric rather than flipping a constant.
5. **Touch.** Capacitive touch exists and is currently unused; the page is deliberately readable with
   zero interaction. If HMI's Web function passes touch through, "tap for the next card" is cheap.
