# E-paper feed — merged build plan

**Status:** **built** 2026-09-03 · **Created:** 2026-09-03 · **Owner:** unassigned
**Branch executed on:** `claude/strava-rss-display-brainstorm-z26d8r` (this branch)

**Two places the build diverged from this plan, both deliberate:**

1. **64 cards, not 63.** The plan's arithmetic treated the existing build as 56 cards; it was
   already 57, because catalogue idea 19 builds both `journey-run` and `journey-bike`. Seven net
   new cards (eight added, `animals` removed in favour of `wildlife`) makes 64. The rotation is 17
   as planned.
2. **Step 5's verification script grew an overlap check.** The planned checks (text >= 26 px,
   stroke >= 3 px, 800x480, one `<svg>`, no console errors) all pass on a card whose labels are
   printed on top of each other, which is the failure mode these hand-placed absolute layouts
   actually have. `tools/epaper_check.py` therefore also compares every pair of text boxes and
   flags anything drawn off-panel. It found four real collisions in the new cards and one
   pre-existing one in `record-book`, whose kicker was printing through a 110 px headline.

Supersedes `Project Docs/Plans/strava-data/eink-feed-plan.md` on branch
`claude/strava-rss-feed-display-uoiv93` (commit `7984afd`). That branch stays unmerged as a
reference for its Pillow prototypes (`strava-data/tools/eink_cards.py`, the contact sheets under
`Project Docs/Plans/strava-data/eink-cards/`).

Companion docs: idea catalogue [`epaper-feed-brainstorm.md`](epaper-feed-brainstorm.md); device
runbook [`../../Handoffs/strava-data/epaper-deployment.md`](../../Handoffs/strava-data/epaper-deployment.md).

---

## Why a merge, and which base

Two branches planned the same thing — Strava cards for a Seeed ePaper panel driven by SenseCraft HMI:

| | `z26d8r` (this branch) | `uoiv93` (other) |
|---|---|---|
| State | **Built**: `strava-data/feed/` package, 57 cards, `build_feed.py`, wired into `deploy.yml` | **Plan + prototypes**: Pillow tool with 17 PNG mock cards, strip-map mocks |
| Device | reTerminal Sticky, **800×480**, 4 tones — a real product (Seeed p-6861) | "reTerminal E1005, 800×650" — **does not exist**; Seeed's E-series is E1001–E1004 and the 3.97" panel is the Sticky |
| Rendering | Whole-card SVG, stdlib+numpy, no JS, no fonts | PNG via Pillow (Pillow would move to runtime deps) |
| Delivery | `epaper.html` (one card, chosen at build time) + `feed.xml` (text) + `epaper-all.html` proof sheet + `feed.json`; **daily `deploy.yml` cron** advances the card | `screen.html` with client-side JS time-slot rotation + RSS with PNG enclosures |
| Routing | `gen_journey.py` → `assets/journey_routes.json` (checked in) | `gen_routes.py` (never written) |

**This branch is the base.** It is built, verified, dependency-free, on the right device, and its
build-time rotation + daily cron is the robust choice — the panel runs no JavaScript, so `uoiv93`'s
client-side slot rotation would never fire on the device.

**Pulled in from `uoiv93`:** six cards (below), a `pr-checks.yml` build step, the whole-word
wildlife regex, a checked-in verification script, and "pin one card by URL" (as static per-card
pages rather than a `?card=` query, since there is no JS).

**Two local-run defects found while planning** — the feed cannot currently be built or verified on
Windows:
- `strftime("%-d")` / `"%-H"` is glibc-only and raises `ValueError` on Windows. 21 uses:
  `feed/cards.py` (19), `feed/layouts.py:33`, `feed/page.py:176`.
- `build_feed.py` prints card titles containing `—`; a cp1252 console raises `UnicodeEncodeError`.

## Card decisions (owner, 2026-09-03)

| Pair | Pick |
|---|---|
| Latest activity | **One combined map + stats card** (new `latest`); replaces `last` + `last-route` in rotation |
| Rest / readiness | **Remove both**: drop `fresh` from rotation, do not build the rest-nudge |
| Segment spotlight | **Port "segment of the month"** (new) |
| Activity names | **Port "hall of fame"** (new) |
| UV | **Build "UV this week"** (new) |
| Wildlife | **Port `uoiv93`'s scoreboard** (icons, 2 columns, whole-word match), replacing `animals` |
| Journey | **This branch's** `journey-run` / `journey-bike` (decided earlier) |
| No counterpart → merge in | **This week in 2004**, **Race anniversary**, **Daily haiku** (all new) |
| Rotation | **All merged cards rotate** |

**Final `ROTATION` (17):**
`strip, sparkline, everest, journey-run, journey-bike, split, hours, mosaic, heat, latest,
segment-month, hall-of-fame, uv-week, wildlife, week-2004, anniversary, haiku`.

---

## Step 0 — this document

Written. Remaining in this step: copy
`Project Docs/Plans/strava-data/eink-cards/{contact-sheet.png,idea-sheet.png,README.md}` from
`uoiv93` into `Project Docs/Plans/strava-data/epaper-prototypes/` (~275 KB;
`git show claude/strava-rss-feed-display-uoiv93:"<path>" > …`) so the references above survive
branch deletion. Commit before any code.

## Step 1 — make the build run on Windows

- Add `feed/fmt.py` with `day(d, fmt="%d %b %Y")` (format, then strip the day's leading zero) and
  `hm(t)` (`H:MM` without `%-H`). Replace every `%-d` / `%-H` use in `cards.py`, `layouts.py:33`,
  `page.py:176`.
- In `build_feed.py:main`, call `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
  before printing.
- Confirm `uv run python strava-data/build_feed.py` completes on Windows.

## Step 2 — new inputs (`feed/config.py`, `feed/metrics.py`)

- `config.RUNLOG_CSV = <repo>/running-log/running_log.csv`; `metrics.load()` reads it with
  **`utf-8-sig`** (the file has a BOM). Columns used: `date, year, week_of_year, day_of_week,
  workout_type, miles, pace_min_per_mile, comments, is_race, race_name, race_distance, race_time`
  (1,274 rows, 2003–2007, 100 rows with `is_race == "1"`). Store as `bundle["runlog"]`.
- Segment efforts are already loaded (`segment_pace_by_grade` uses them) — reuse.
- New pure helpers beside the existing ones: `segment_of_month(efforts, segs, asof)`,
  `named_activities(acts)` + `name_score(r)`, `uv_week(acts, asof)`, `runlog_week(runlog, iso_week)`,
  `race_anniversary(runlog, today)`, `haiku(act)`.
- Rewrite `animal_sightings` with `re.search(rf"\b{rx}s?\b", blob)` over the `uoiv93` list
  `[(r"coyote","Coyote"), (r"snake|rattler","Snake"), (r"owl","Owl"), (r"deer","Deer"),
  (r"quail","Quail"), (r"lizard","Lizard"), (r"hawk","Hawk"), (r"bobcat","Bobcat"),
  (r"roadrunner","Roadrunner"), (r"turkey","Turkey"), (r"rabbit|bunny","Rabbit")]` plus this
  branch's extras (tarantula, skunk, heron, seal, dolphin, whale, fox). The current substring test
  over-counts: "owl" matches "slowly", "seal" matches "sealed".

## Step 3 — cards

Every new card is a `@card(idea, family, recipe)` function in `feed/cards.py` composed from
`feed/layouts.py`, glyphs in `feed/svg.py` — the existing rule. New catalogue frames 57–62 get
matching entries in the brainstorm doc. Prototype line refs are into
`uoiv93:strava-data/tools/eink_cards.py`.

| id | idea | layout | recipe |
|---|---|---|---|
| `latest` | 3 (`last` / `last-route` stay in the catalogue) | new `route_stats(c, path, stats)`: route on top (~220 px; reuse `metrics.route_for` + `layouts.route_card` geometry), 4×2 stat grid below, description as footer via `fit_text` | distance mi, moving h:mm, pace `M:SS/mi` (run) or mph (bike), climb ft, avg HR, temp °F, suffer, kudos. Proto `card_latest` L650. |
| `segment-month` | 57 · D | `spark` + a stat trio | most efforts in the 30 days before `asof` (ties → most overall); best / latest / `recent_trend` with an arrow word; effort-time sparkline, last 24, inverted (up = faster); footer: avg HR, worst, first effort. Proto `card_segment_week` L883. |
| `hall-of-fame` | 58 · J | 5-row list on `bar_rows` geometry (sport glyph, name wrapped to 2 lines at 26 px, date + one stat) | exclude `DEFAULT_NAME` regex (L1234) and "Warm Up"; score = punctuation×3 + min(len,40)/8 + kudos/2 + 2 if non-ASCII; window of 5 by ISO-week seed. Proto L1237. |
| `uv-week` | 59 · G | `cell_grid` (7 cells) + `hero_number` + new `glyph_sunscreen(fill_frac)` | Σ `uv_index × moving_time_min/60` over the ISO week of `asof` for rows with a UV value (339/374); cells shaded by daily UV-hours via `svg.tone`; tube fills at ≥ 20 UV-hours; footer: peak-UV activity. |
| `wildlife` | 52 (replaces `animals`) | new `bar_grid(c, rows, cols=2)` (two-column `bar_rows`) | top 10 species: icon + label + bar + count; footer: latest sighting + activity name. Port the 11 animal glyphs from Pillow polygons (L506–604) to `svg._g` groups; strokes ≥ 3 px. Proto `card_wildlife` L1145. |
| `week-2004` | 60 · I | new `then_now(c, top, bottom)`: `LIGHT` band with stacked lines, this year below | same ISO week in 2004 (fallback 2003): miles, avg pace, up to 4 workouts with race flag; below: this week's run miles/pace or "no runs this week — last run …". Proto `card_2004` L1097. |
| `anniversary` | 61 · I | `text_card` | race whose month-day is within ±7 days of **the build date** (else the next upcoming): "N years ago today" / "in 3 days", `race_name`, `race_distance`, `race_time` as headline, `comments` wrapped to 3 lines. **Calendar-driven exception** to the "asof = last data day" rule — say so in the recipe string. |
| `haiku` | 62 · J | `text_card` (headline ~48 px, three lines) | deterministic templates seeded by the newest activity id: sport word, distance, weather/temp clause, suffer adjective, one wildlife/description noun if present; vowel-group syllable check, ~12 templates per slot, no LLM. Activity name in the footer. |

`fresh` stays in the catalogue, out of rotation. Set `ROTATION` to the 17 ids above;
`card_of_the_day` needs no change. Also emit **per-card static pages**
`running-log/epaper/<id>.html` (same `render_page`) so one card can be pinned in SenseCraft or
checked locally; add `running-log/epaper/` to `.gitignore`.

## Step 4 — CI / deploy

- `.github/workflows/pr-checks.yml`: add `Build e-paper feed`
  (`uv run python strava-data/build_feed.py`) after the two dashboard builds and before `qa.py`;
  add `strava-data/build_feed.py`, `strava-data/feed/**`, `strava-data/assets/**` to `paths:`.
- `.github/workflows/deploy.yml`: add `strava-data/assets/**` to `paths:` (a re-routed
  `journey_routes.json` must redeploy). The daily cron and the feed step already exist.
- No dependency changes (no Pillow). Show workflow diffs to the owner before pushing.

## Step 5 — verification script (checked in, dev-only)

`tools/epaper_check.py`, beside `tools/mobile_preview.py`, same `--probe` convention, Playwright,
run un-sandboxed:

1. Parse `running-log/feed.xml` with `xml.etree`: well-formed, ≥ 17 items, unique GUIDs, no
   `km` / `km/h` / `°C` in any title or description.
2. Open `epaper.html` and every `epaper/<id>.html` at an 800×480 viewport:
   `scrollWidth/scrollHeight == 800/480`, exactly one `<svg>`, computed `font-size ≥ 26` on every
   `<text>`, effective `stroke-width ≥ 3` (account for `transform: scale`), no console errors.
3. Screenshot each to `tools/preview-output/epaper/` (already gitignored) and print a pass/fail
   table. Exit 1 on any failure.

## Step 6 — docs

- **`README.md`**: new "Previewing locally" section — build commands for both dashboards and the
  feed, `uv run python -m http.server 8765 --directory running-log`, then
  `http://127.0.0.1:8765/epaper-all.html` (proof sheet), `/epaper.html` (what the panel gets),
  `/epaper/<id>.html` (one card), and `uv run python tools/epaper_check.py` for the automated
  pass. Note `127.0.0.1` not `localhost`, and `uv run` on Windows.
- **`CLAUDE.md`**: e-paper section → 63 cards / 17 in rotation, `running_log.csv` is a feed
  input, per-card pages, `epaper_check.py`, the `fmt.py` rule ("no `%-d`; use `fmt.day`"), the
  anniversary card's calendar exception. Preview section → the e-paper URLs.
- **`Project Docs/Handoffs/strava-data/epaper-deployment.md`**: card count, per-card URL for
  pinning, a "verify locally before merging" subsection pointing at Step 5. The SenseCraft docs
  host (`sensecraft-hmi-docs.seeed.cc/en/guides/sensecraft-hmi-{web,rss}/`) still 404s from the
  planning environment — the device poll interval remains a "read it in the UI and write it here"
  item.
- **`epaper-feed-brainstorm.md`**: catalogue entries 57–62, rotation marks updated, note
  `animals` → `wildlife` and `fresh` demoted.
- Flip this document's status to *built*.

## Step 7 — build, verify, ship

1. `uv run python strava-data/build_feed.py` → 63 cards, card of the day printed, no exceptions.
2. `uv run python tools/epaper_check.py` → all green; eyeball `epaper-all.html` and each new
   card's screenshot (no clipped text, wildlife icons legible at four tones, haiku lines fit).
3. Spot-check numbers: segment-month best time vs `segments_summary.best_time_s`; UV-hours by
   hand for one week; 2004 week miles vs the CSV rows; anniversary picks the right race for
   today's date.
4. `build_dashboard.py`, `visualize_log.py`, `running-log/qa.py` still pass (the feed touches
   nothing they use, but `pr-checks.yml` runs all four).
5. Commit in slices (plan doc → Windows fix → metrics → cards → CI → docs), push this branch, open
   a PR to `main` with the workflow diffs called out. **Do not merge** — the owner merges, Pages
   deploys `epaper.html` + `feed.xml`, and SenseCraft takes over per the runbook.

## Files touched

- New: this file, `Project Docs/Plans/strava-data/epaper-prototypes/*`, `strava-data/feed/fmt.py`,
  `tools/epaper_check.py`.
- Edited: `strava-data/feed/{cards,layouts,svg,metrics,config,page}.py`,
  `strava-data/build_feed.py`, `.github/workflows/{pr-checks,deploy}.yml`, `.gitignore`,
  `README.md`, `CLAUDE.md`, `Project Docs/Handoffs/strava-data/epaper-deployment.md`,
  `Project Docs/Plans/strava-data/epaper-feed-brainstorm.md`.
- Untouched: both `dashboard/` packages, the data layer, `assets/basemap.json`, `pyproject.toml`.
