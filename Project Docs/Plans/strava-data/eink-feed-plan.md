# E-paper feed for the reTerminal E1005 — build plan

Status: **planned, not built.** Everything below is ready to execute in a fresh session.
Prototype artefacts this plan builds on live next to it in `eink-cards/`
(contact sheets, per-card PNGs, `route-maps/` strip-map mocks) and in
`strava-data/tools/eink_cards.py` + `strava-data/tools/eink_route_maps.py`.

## 1. Context

Goal: publish a rotating set of Strava "screens" that Seeed's **SenseCraft HMI** can pull
onto a **reTerminal E1005** (3.97" e-paper, **800×650**, **4 grey levels**: 0/85/170/255).
SenseCraft fetches content on a user-set interval (minutes) and displays what it gets; the
device never renders anything itself, so every screen is a **pre-rendered PNG** at the
panel's exact size and palette. GitHub Pages is static, so "a different screen each pull"
is done with a **time-slot rotation page** (client-side, no server) and, in parallel, an
**RSS feed** with one item per screen. Both are built by one new deploy step from the same
data the dashboards already use, and refresh automatically whenever
`strava-fetch.yml` pushes new data (that push already triggers `deploy.yml`).

Decisions already made by the owner:
- Cards to build (idea numbers from `eink-cards/idea-sheet.png`):
  **#1+#2, #24, #26, #32, #38 (×2, strip-map treatment), #44, #51, #53, #56, #57** → 11 screens.
- Activity names are shown **verbatim** (no profanity masking).
- Units per repo policy: **min/mi**, **mph**, **°F**; data files stay metric.
- Route ladders start at **92129** (Rancho Peñasquitos); running and biking get separate cards.

Unverified (Seeed docs are egress-blocked from the cloud container; check from a normal
browser at the start of the build — 10 minutes): whether SenseCraft's **RSS** widget renders
per-item images (`<enclosure>`/`media:content`) or text only, and whether **Web Content**
takes a JS-rendered screenshot (it does per reviews, via a headless browser in Seeed's cloud).
The plan emits both so either path works; polish whichever the E1005 actually uses.

## 2. The 11 screens

Every screen is a function `card_<id>(ctx) -> (PIL.Image "L" 800×650, meta)` where `meta`
carries `guid`, `title` (≤60 chars, one line), `lines` (3–6 short text lines for the RSS
description / text fallback), and `pub_date`. Guids are stable per *content*, so a device
that de-duplicates by guid still sees a change only when the content changes.

| id | idea | template | guid | data recipe (all from `strava-data/data/` unless noted) |
|---|---|---|---|---|
| `latest` | #1+#2 | Map + stats | `latest-<activity_id>` | Newest activity that has `streams/<id>.csv`. Route: lng/lat → equirectangular (× cos lat), `charts_places._rdp(pts, 0.00004)`, fit into 744×300 box, 4 px black line over 9 px light halo, start ring / finish square, 1 km scale bar, N arrow. Stats 4×2: distance mi, moving h:mm:ss, pace `M:SS /mi` (run) or mph (bike), climb ft, avg HR, temp °F, suffer, kudos. Footer = description (fit to one line). Prototype: `eink_cards.card_latest`. |
| `rest` | #24 | Hero | `rest-<date>-<state>` | From daily suffer sums (`load_series`): count consecutive days with suffer ≥ the athlete's 70th percentile ending at the last data date. ≥3 → "3 hard days in a row" + sleeping-cat icon (new icon: curled cat outline, 96 px) + "rest tomorrow?". Else show days since last rest day and a "streak of easy days" variant. Always emits (never an empty card). |
| `segment` | #26 | Hero + sparkline | `segment-<segment_id>-<n_efforts>` | `segment_efforts.csv`: most efforts in the last 30 days before the newest activity; ties → most efforts overall. Best/latest/trend (`segments_summary.recent_trend`, sign → arrow + "slower/faster lately"), effort-time sparkline (last 24, inverted so up = faster). Prototype: `card_segment_week`. |
| `names` | #32 | List | `names-<iso_week>` | Activities whose name isn't Strava's default (`DEFAULT_NAME` regex in the prototype, plus "Warm Up"). Score = punctuation ×3 + min(len,40)/8 + kudos/2 + non-ASCII bonus. Pick 5 by ISO week seed so it rotates weekly. Sport icon, name wrapped to 2 lines at 26 px, date, one stat, kudos. Prototype: `card_hall_of_fame`. |
| `route-run` | #38 | Strip map | `route-run-<dest>-<miles_floor_10>` | Lifetime run + trail-run miles → first ladder rung with road miles > total (rung distances come from the routed asset, §4, not the hand-typed table). Strip-map treatment exactly as `eink_route_maps.mock_strip`: real highway polyline rotated so the destination is up, left ribbon 330 px wide, 100-mile ticks, city labels at true along-road mileposts (stacked when <22 px apart), marker box to the left; right column: big number, TO GO, LAST PASSED, NEXT UP, progress %, locator inset (whole route on state outlines). Mock: `eink-cards/route-maps/running-strip.png`. |
| `route-bike` | #38 | Strip map | `route-bike-<dest>-<miles_floor_10>` | Same with MountainBikeRide + Ride + EBikeRide miles. Mock: `biking-strip.png`. Known crowding when the last 3 cities are within ~130 mi (Sacramento/Truckee/Reno): the label stacker already pushes up; add "hide milepost text when stacked" so only names stack. |
| `uv` | #44 | Hero | `uv-<iso_week>` | Σ over the ISO week of `uv_index × moving_time_min/60` for outdoor activities with a UV value (≈339 of 374 have one). Big number + "UV-hours this week", 7 day-cells shaded by daily UV-hours, sunscreen icon (new: tube outline) that fills at ≥ 20 UV-hours, footer: peak UV activity name + value. Week = ISO week of the newest activity. |
| `week2004` | #51 | Then & now | `then-<iso_week>` | `running-log/running_log.csv` rows with same `week_of_year` in 2004 (fallback 2003): miles, avg `pace_min_per_mile`, up to 4 workouts (`day_of_week`, `workout_type`, miles, race flag) in DejaVu Mono on a light-grey band; below: this week's run miles/pace/activities, or "no runs this week — last run: …". Prototype: `card_2004`. |
| `anniv` | #53 | Hero | `anniv-<race_date>` | From `running_log.csv` where `is_race == 1` (247 races): pick the race whose month-day is closest to today (±7 days window; else the next upcoming). "22 years ago today" (or "in 3 days"), `race_name`, `race_distance`, `race_time` as hero, the `comments` line wrapped to 3 lines. Today = the deploy date (`datetime.now()`), not the data date — this card is calendar-driven. |
| `wildlife` | #56 | List | `wildlife-<total_sightings>` | Whole-word regex over `name + description` (the prototype's `ANIMALS` list — substring matching over-counted "owl"/"hawk" via "slowly"/"nighthawk"; keep `\b…s?\b`). Tally per animal, 2-column bars, animal icons, footer = latest sighting + activity name. Prototype: `card_wildlife`. |
| `haiku` | #57 | Hero | `haiku-<activity_id>` | Template-generated 5-7-5-ish three lines from the newest activity: sport word, distance, a weather/temperature clause, a suffer-score adjective, and one wildlife/description noun if present. Deterministic (seed = activity id) so it's stable until the next activity. ~12 line templates per slot, syllable counts checked with a tiny CMU-free heuristic (vowel groups); no LLM. Big serif-ish type (DejaVu Serif Bold 36 px), activity name in the footer. |

Shared chrome (already in the prototype and to be lifted into the package): `header()`
black band with kicker, `footer()` grey rule + line, `hero()`, `progress_bar()`, `gauge()`,
`sparkline()`, `stamp()`, `wrap()/fit()`, icon set (`ic_run`, `ic_bike`, animals, …),
`quantize()` to the 4 levels, `verify()` (mode L, 800×650, palette-only).

## 3. Outputs

All under `running-log/feed/` (gitignored, published by Pages like the HTML):

```
running-log/feed/
  cards/<id>.png          11 screens, mode L, 800x650, pixels ∈ {0,85,170,255}
  screen.html             rotation page for SenseCraft Web Content (see §5)
  strava.xml              RSS 2.0, one <item> per screen, newest-content first
  manifest.json           [{id, guid, title, lines, png, pub_date}] – used by screen.html
```

Live URLs (project page): `https://ducktapegirl.github.io/distance-nerd-stuff/feed/screen.html`,
`…/feed/strava.xml`, `…/feed/cards/latest.png`.

## 4. Code layout

New files only; nothing on the issue-guardrails denylist except the two workflow edits in §6,
which are a direct owner request.

```
strava-data/build_feed.py            thin entrypoint (mirrors build_dashboard.py)
strava-data/feed/__init__.py
strava-data/feed/palette.py          BLACK/DARK/LIGHT/WHITE, W/H, quantize(), verify()
strava-data/feed/draw.py             fonts, text/wrap/fit, header/footer/hero/bars/gauge/sparkline
strava-data/feed/icons.py            sport + metric + animal icons (from eink_cards.py) + new cat, sunscreen
strava-data/feed/data.py             ctx loader: activities, segments, efforts, gear, athlete, runlog,
                                     load_series() (daily suffer, 7d/28d, ACWR), run_week_streak(), animal_hits()
strava-data/feed/cards/<id>.py       one module per screen (functions listed in §2)
strava-data/feed/routes.py           ladder + loader for the routed asset; strip-map drawing (Frame,
                                     draw_basemap, draw_route, draw_cities, marker, mock_strip → draw_strip)
strava-data/feed/rss.py              xml.etree RSS 2.0 writer with <enclosure type="image/png">
strava-data/feed/page.py             screen.html + manifest.json writer
strava-data/tools/gen_routes.py      ONE-OFF: downloads the two Natural Earth files into
                                     strava-data/assets/cache/ (gitignored), builds the road graph
                                     (Graph class from eink_route_maps.py: 3-decimal vertex keys,
                                     endpoint→segment snap ≤0.06°, crossing noding, 0.004° merge),
                                     routes 92129 → every waypoint → every ladder destination, and
                                     writes strava-data/assets/routes.json (committed, ~100 KB):
                                     {dest: {miles, pts:[[lng,lat]…] (RDP-simplified), marks:[[name, mi, lng, lat]…]}}
strava-data/assets/routes.json       committed output of gen_routes.py
```

Reuse from the existing dashboard package: `dashboard.data.load_activities/load_segments/
load_segment_efforts`, `dashboard.config.DATA_DIR/KM_TO_MI`, `dashboard.charts_places._rdp`,
`strava-data/assets/basemap.json` (coast/admin/lakes polylines — the strip map's locator inset).

Routing notes (learned the hard way, all implemented in `eink_route_maps.Graph`):
- Natural Earth 10m roads are **not topologically noded**: lines meet mid-segment and stop a
  few hundred metres short. Without snapping, 92129→Portland routed to 1,423 mi; with
  endpoint-to-segment snapping **and** true crossing detection it routes to **1,074 mi**
  (real ≈1,080) and 92129→Reno to **623 mi** (real ≈620). Keep all three snap passes.
- Bbox in the prototype is lng −125.5..−106, lat 30.5..47.5. Rungs east of that (Denver,
  Austin, Dallas, … Lexington MA) need the bbox widened to the whole CONUS when generating;
  graph build is ~3.5 s for the west, expect ~15 s for CONUS. Mexico City/Panama/Ushuaia
  rungs may not route (sparse roads south of the border): fall back to straight legs and mark
  `"routed": false` so the card says "as the crow flies".
- Places file lacks some small towns (Truckee, Yosemite, Primm, …); `FALLBACK` dict in the
  prototype has their coordinates. Prefer the western duplicate when a name is ambiguous
  (Portland OR, Las Vegas NV).
- `gear.json.notification_distance` holds **miles** typed into Strava's alert box (400, 450),
  despite the API docs saying metres — irrelevant to the chosen cards but noted for #48 later.

Dependency: **Pillow moves from the `dev` group to runtime deps** in `pyproject.toml`
(`uv add pillow`) because `deploy.yml` runs `uv sync --no-dev`. The stdlib+plotly+numpy rule
in `CLAUDE.md` is scoped to `build_dashboard.py`; document the feed builder as the exception.

## 5. SenseCraft delivery

**Rotation page `feed/screen.html`** (Web Content path):
- 800×650, no scrolling, black on white, the current card as a full-bleed `<img>`.
- Tiny inline JS: `slot = floor(Date.now()/1000 / SLOT_SECONDS)`; `idx = slot % cards.length`
  (cards from the inlined manifest, ordered as in §2). `SLOT_SECONDS` defaults to **1800**
  (30 min) — set it to the device's pull interval so every pull is a new screen; both are
  owner-configurable (`?slot=900` overrides; `?card=latest` pins one for testing).
- `<noscript>` fallback: the first card's PNG, so a non-JS fetch still shows something.
- Cache headers aren't controllable on Pages; add `?v=<build_hash>` to the PNG URLs from the
  manifest so a republish is never served stale by SenseCraft's fetcher.

**RSS `feed/strava.xml`** (RSS path): `<title>` = card title, `<description>` = the 3–6 text
lines joined with ` · ` (also a plain `<br>`-free version for text-only renderers),
`<enclosure url=…/cards/<id>.png type="image/png" length=…>`, `<guid isPermaLink="false">`,
`<pubDate>` = the data date (or deploy date for `anniv`). 11 items, newest-content first.

**Device setup (owner does this once in the SenseCraft app/site):**
1. Web Content → URL `…/feed/screen.html`, refresh interval = the slot length (30 min).
   If the screenshot looks soft, this is SenseCraft rescaling — confirm the page is exactly
   800×650 with no margins.
2. Or RSS Feed → `…/feed/strava.xml`, same interval; if items render text-only, use the
   RSS widget inside Canvas next to an Image widget pointed at `…/feed/cards/latest.png`.

## 6. Deploy / CI changes (show the owner before pushing — G3-style approval)

- `.github/workflows/deploy.yml`: after "Build Running Log dashboard", add
  `- name: Build e-paper feed` → `run: uv run python strava-data/build_feed.py`. Add
  `strava-data/feed/**`, `strava-data/build_feed.py`, `strava-data/assets/routes.json` to
  the `paths:` filter.
- `.github/workflows/pr-checks.yml`: same build step after the two dashboard builds, before
  `qa.py`; a card that throws fails the PR.
- `.gitignore`: `running-log/feed/` (generated) — `strava-data/assets/cache/` is already there.
- `pyproject.toml` / `uv.lock`: Pillow to runtime.

## 7. Docs updates

- `CLAUDE.md`: layout tree (`strava-data/feed/`, `build_feed.py`, `tools/gen_routes.py`,
  `assets/routes.json`), a "Build the e-paper feed" command block, the Pillow exception to the
  no-pandas/stdlib rule, and the feed URLs.
- New `Project Docs/Specs/strava-data/eink-feed-spec.md`: the §2 table as the source of truth
  for what screens exist (mirrors how `dashboard-spec.md` works for the dashboard), the guid
  scheme, the palette/size contract, and the SenseCraft setup steps.
- This plan: flip Status to "built" and link the spec.

## 8. Execution order

1. Verify the two SenseCraft unknowns (§1) from a browser; note the answers in the spec.
2. `uv add pillow`; move it out of the dev group.
3. Lift `eink_cards.py` kit into `strava-data/feed/{palette,draw,icons,data}.py` (no behaviour change; the prototype tool keeps working by importing from the package).
4. `tools/gen_routes.py` from `eink_route_maps.Graph`/`build_route`; widen bbox to CONUS; commit `assets/routes.json`. Sanity-check rung miles against the hand ladder (±10%).
5. `feed/routes.py` + `feed/cards/route_*.py` from `mock_strip`; replace the hand-typed ladder distances with the routed ones.
6. Remaining cards in this order (cheapest first, each with its prototype as the starting point): `latest`, `names`, `wildlife`, `segment`, `week2004`, then the four new ones `uv`, `rest`, `anniv`, `haiku`.
7. `rss.py`, `page.py`, `build_feed.py`; run locally; open `running-log/feed/screen.html` via `uv run python -m http.server 8765 --directory running-log`.
8. Workflow + gitignore + pyproject edits (§6), CLAUDE.md + spec (§7).
9. Branch + PR; CI green; merge; deploy; point the E1005 at the URL.

## 9. Verification

- `uv run python strava-data/build_feed.py` writes 11 PNGs, `strava.xml`, `screen.html`,
  `manifest.json` with no exceptions; each PNG passes `verify()` (mode L, 800×650, palette-only).
- `xmllint --noout running-log/feed/strava.xml`; the W3C feed validator once deployed.
- Playwright screenshot of `screen.html` at 800×650 (`tools/mobile_preview.py --desktop --url …`
  or a 10-line script) for `?card=<id>` on every id: no clipping, no margins, image fills the
  viewport; then without `?card` to confirm the slot rotation picks different cards at
  different `?now=` overrides (add a `?now=<epoch>` test hook).
- Spot-check numbers against the dashboard: total miles per sport vs the stat cards; the
  segment card's best time vs `segments_summary.best_time_s`; routed rung miles vs the ladder.
- On the device: first pull shows a card; two pulls one slot apart show different cards; a
  data push (or manual `deploy.yml` dispatch) changes `latest` within one interval.
- `pr-checks.yml` green with the feed step included.

## 10. Later (not in this build)

Cards prototyped but not selected stay available in `eink_cards.py`: week in review, streak +
load gauge, PR board, passport, cardiac hearts, shoe odometer, funny segment, achievements,
joggernaut index, latest sighting. Overview/corridor/fan map treatments are in
`eink_route_maps.py` and `eink-cards/route-maps/`. A "arrived in <city>" one-time badge when a
rung rolls over is a natural add once #60 is built.
