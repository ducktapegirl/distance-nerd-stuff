# The Sticky rotation on a 2.9″ four-color XIAO panel

**Status:** built, 15 of 16 rotation cards adapted, four decisions left to the owner on the
sheet · **Created:** 2026-09-12 · **Owner:** unassigned

Companion to `strava-data/feed/xiao/` and the review sheet it builds, `epaper_xiao-all.html`.
The Sticky catalog and its rationale are in [`epaper-feed-brainstorm.md`](epaper-feed-brainstorm.md);
this document covers only what changes when the same rotation goes on the smaller panel.

---

## The device

Seeed's **2.9″ Quadruple Color ePaper** — 296 × 128, black / white / red / yellow — on the XIAO
ePaper Display Board (EE04 / EE05), which SenseCraft HMI lists as "2.9″ Monochrome / Color, 296×128".
Same delivery path as the Sticky: the Web function fetches a static page. What differs:

| | Sticky | XIAO 2.9″ | Consequence |
|---|---|---|---|
| Pixels | 800 × 480 | 296 × 128, landscape | a tenth of the pixel budget; a 2.3 : 1 strip |
| Density | 235 PPI | 112 PPI (66.9 × 29.1 mm active) | the Sticky's 26 px floor is 12.4 px here, physically |
| Tones | 4 grays + 3 dithers | **4 solid colors, no gray, no anti-aliasing** | no `#555` / `#AAA`; every fill is one of the four |
| Refresh | seconds | ~25 s full refresh | hourly rotation is fine; nothing faster |

Floors are derived, not guessed: 26 px at 235 PPI is 2.8 mm of em, which is 12.4 px at 112 PPI,
rounded **up** to **14 px** because there is no anti-aliasing to soften a 12 px stem; the 3 px
stroke is 0.32 mm, which is 1.4 px here, rounded up to **2 px** because a 1 px line on e-ink is a
coin toss. `feed/xiao/svg.py` enforces both and, unlike the Sticky's, **raises on any color outside
the palette** — a stray gray would be quantized by the device into whichever of black, red or white
its algorithm liked, and the card would look different on the panel than on the sheet.

Orientation is landscape (the product page says 128 × 296; SenseCraft says 296 × 128).

## 1 · Audit of the rotation

Criterion: does the card's *idea* survive at ≥ 14 px, ≥ 2 px strokes, four colors, in a strip?
"Adapt" keeps the fact and the graphic with less of it; "drop" means the card's whole point is
density this panel does not have.

| Card | Verdict | What changes |
|---|---|---|
| `strip` (9) | adapt | 2 rows of 15 cells at 13 px (3 mm). Headline above; rest days take the wash, today the accent. |
| `sparkline` (17) | adapt | Headline number, 13-month line, end dot as the accent, range label under. |
| `everest` (18) | adapt | Up to six summits across the bottom; the partial one fills with the wash. |
| `journey-run` / `-bike` (19) | adapt · **mockup** | Numbers over the milepost strip (the precise half). The CONUS map is the mockup. |
| `split` (20) | adapt | Five bar rows → four; the track is a wash band, no outline. |
| `hours` (21) | adapt | Numeral left, one tally mark per 24 h along the bottom; the partial day is the accent. |
| `mosaic` (37) | **drop** · mockup | 32 routes would be 25 px squiggles. A 2 × 6 at 42 px is on the sheet to reinstate or not. |
| `latest` (3) | adapt | Route left, six of eight stats in a 3 × 2 grid; the activity name moves into the masthead. |
| `segment-month` (57) | adapt | Name, best / last / trend (accent when slower), spark of the last 24 efforts. Grade caption goes. |
| `hall-of-fame` (58) | adapt · **mockup** | Three of the weekly five, two 14 px lines each, distance not date. A one-name version is the mockup. |
| `uv-week` (59) | adapt | Numeral, a yellow sun that turns red past half a 20-UV-hour week, the week's cells on the ramp. |
| `wildlife` (52) | adapt | Ten bar rows → a four-up scoreboard of silhouettes; the latest sighting is the accent. |
| `week-2004` (60) | adapt | The then / now band keeps both headline numbers and the average paces; the day lists go. |
| `anniversary` (61) | adapt | When-line (accent on the day), distance · time, race name, date. Comments go. |
| `haiku` (62) | adapt | Three lines at 18 px shrinking to 14, full width, no glyph. Never ellipsized — checked. |

Rotation: the Sticky's list minus `mosaic`, in the Sticky's order, keyed on the same UTC hour
(`xiao/cards.py:ROTATION`, `card_of_the_hour`). Cards with no data this fetch (no GPS stream on the
newest activity, no UV this ISO week) drop out exactly as they do on the Sticky.

## 2 · The 296 × 128 layout system

A sibling package, `strava-data/feed/xiao/`, not a parameterization of the Sticky's: the Sticky
modules import `W`, `H`, `MIN_TEXT` as module constants in ~70 places, and the drawing is the only
thing the smaller panel changes. The data layer — `metrics`, `places`, `journey`, `geo`, `stats`,
`fmt` — is reused unchanged, as are the glyph builders in `feed/svg.py` (drawn in a 100-unit box,
so they carry no panel size).

```
feed/xiao/
  config.py    296×128 · MIN_TEXT 14 · MIN_STROKE 2 · PAD 6 · the four colors · Palette roles
  svg.py       primitives at those floors, palette-validated; its own solid-disc sun
  layouts.py   base · hero · stat_row · bars · spark · cells · route · then_now · tally · glyph_row · lines
  cards.py     one @card per rotation id, plus mosaic (rotation=False) for the sheet; build_mockups
  page.py      render_page (the device page) · render_sheet (audit + rotation + mockup pairs)
```

Vertical budget: masthead to y = 21 (kicker 14 px caps, date as "9 SEP" — the year cost 53 px
that a twenty-character kicker needs more), body 27 → 122. That is 95 px for the whole idea, which
is why no card has a footer, a divider, or a second line of anything. Headline numerals 26–48 px.

Outputs, gitignored beside the Sticky's: `epaper_xiao.html` (device page), `epaper_xiao-all.html`
(the sheet), `epaper_xiao/<id>.html` (one card, for pinning), and a `xiao` block in `feed.json`.
`build_feed.py` builds both panels in one run, so neither workflow changed.

## 3 · Color

Two physical facts shape every choice. On these panels **yellow reads light** — near white in
luminance, an area wash, never text or a thin stroke — and **red reads mid-dark**, fine for shapes
and large numerals, risky under ~20 px. Black is the only ink. The hexes are pure primaries
(`#FF0000`, `#FFFF00`) so whatever nearest-color quantizer SenseCraft runs maps them exactly.

Cards never name a hex. They ask a `Palette` for a **role** — `ink`, `accent`, `wash`, `run`,
`bike`, `ramp` — so a color model is a table, not a rewrite:

| Model | accent | wash | run / bike | Idea |
|---|---|---|---|---|
| **A · Semantic** (ships) | red | yellow | ink / ink | Red = *the one thing to look at*: now, here, today, an alert. Yellow = the light tone: reference, past, rest. Categories by shape, quantity by tone — the Sticky's rule, translated. |
| B · Heat | *none* (ink) | yellow | ink / ink | No reserved accent; color only ever means *more*. Strip cells by that day's miles. |
| C · Sport | red | yellow | ink / **red** | Bike = red, run = black, the dashboard's teal / amber re-tabled. Costs the accent its meaning on bike cards. |

All three share the four-step ramp white → yellow → red → black for quantity (uv-week's cells).

A ships because it is the direct translation of the existing intent — `svg.tone()` said quantity
by tone, and red-as-accent is what a single spot color is for. B and C are the two that cannot be
decided from principle, so the sheet shows the same cards under each.

## What the sheet asks you to decide

Open `epaper_xiao-all.html` (1× is close to physical size on an ordinary monitor; 2× shows the
pixels; "as the panel sees it" thresholds every channel at one half, which is the same collapse
the device's quantizer makes, dithering aside).

1. **Journey:** milepost strip (ships) or the CONUS map. The map is legible at 144 px wide with the
   coast clipped and the state lines dropped, but it is a busy 2 px line.
2. **Mosaic:** stay dropped, or reinstate the 2 × 6 at 42 px.
3. **Hall of fame:** three names on two lines each (ships), or one name as a quote card.
4. **Color model:** A (ships), B, or C — globally or per card. Switching is one `Palette` argument.

To act on any of them: `DROPPED` and the `variant=` defaults in `xiao/cards.py`, and `DEFAULT` in
`xiao/config.py`.

## Verification

```bash
uv run python strava-data/build_feed.py          # both panels
uv run python tools/epaper_check.py --panel xiao # 296×128 exact, floors, overlap, palette
uv run python tools/epaper_check.py              # the Sticky, unchanged
```

The XIAO run adds one check the Sticky never needed: every rendered `fill` / `stroke` must be one
of the four palette colors. Determinism was verified by building twice and diffing all three
outputs.

## Unknowns

- **How SenseCraft quantizes a web page for a four-color panel** — nearest color or dithered — is
  undocumented. The cards use pure primaries and no gray so that either gives the same result;
  what dithering would do to anti-aliased text edges is the one thing only the device can show.
- **Refresh:** 25 s per full refresh means the panel will visibly flash on every card change. The
  hourly rebuild is the right cadence; do not point the device's own poll below that.
- The panel's font. Same assumption as the Sticky (a bundled Helvetica / Arial); emoji in an
  activity name may render as boxes in the masthead of `latest`.
