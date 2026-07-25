# Running Log Dashboard — Build Spec

The single hand-off artifact for the Running Log dashboard's agentic pipeline (the
`/dashboard running-log` workflow — see the repo-root `AGENTS.md`). Read-only pipeline
agents produce spec *text*; the **orchestrator writes it here**. The `dash-developer`
agent reads this file verbatim in the Build stage; the `running-log-qa` agent checks the
built page against it in the QA stage.

This is the Running Log counterpart to `Project Docs/Specs/strava-data/dashboard-spec.md`.
It consolidates what previously lived in the design handoff
(`design_handoff_running_log/readme.md`) and the architecture notes
(`Project Docs/Handoffs/running-log/session-handoff.md`), and it is the append point for
every new view.

---

## Pipeline profile

Machine-readable facts every shared `dash-*` agent loads first when the orchestrator names
`running-log` as the target.

- **Target**: `running-log`
- **Data source**: `running-log/running_log.csv` — a **frozen** historical dataset
  (2003-08-31 → 2007-05-12, ~1,274 rows). Loaded by `dashboard.data.load_rows()`
  (UTF-8-sig). There is **no live API** and no ongoing ingest; the CSV changes only if
  `running-log/parse_log.py` is re-run against the static HTML in `running-log/source/`.
- **CSV fields (19)**: `date, year, month, day, day_of_week, week_of_year, season,
  workout_type, minutes, minutes_raw, miles, pace_min_per_mile, comments, extras,
  is_race, race_name, race_distance, race_time, source_file`.
  - `is_race` is the string `"1"` / `"0"` (not a bool).
  - There is **no `place` column** — placement, when present, lives inside free-text
    `comments` (e.g. "37/224 runners"). The design handoff's idealized `Race.place` field
    does **not** exist in the data.
  - No GPS, heart rate, elevation, cadence, power, or per-split arrays exist. This is the
    data-poverty contrast with Strava — plan views accordingly.
- **Build command**: `uv run python running-log/visualize_log.py` (run from repo root).
- **Output HTML**: `running-log/index.html` (gitignored — rebuilt by `deploy.yml`).
- **Static QA**: `uv run python running-log/qa.py` (exit 0 = pass, 1 = fail).
- **QA agent**: `running-log-qa` (visual/rendered pass; the counterpart to `qa.py`).
- **Module map** — `visualize_log.py` is a thin entrypoint. Add `chart_*` functions to
  `running-log/dashboard/charts.py` and `section_*` functions to
  `running-log/dashboard/sections.py`; wire new sections into `page._build_sections` and
  the `NAV_VIEWS` tuple in `page.py`. Never restructure the entrypoint. Package layout:
  - `config.py` — paths + design-token colors (imports shared dark tokens from
    `nerd_common.tokens`; running-log-specific palettes `WORKOUT_TYPE_MAP`, `TYPE_COLORS`,
    `EVENT_GROUPS`, `WORKOUT_MIX_COLORS`, `YEAR_PALETTE`, DOW/month/season orderings).
  - `data.py` — `load_rows`, `parse_time_seconds`, `fmt_time`, `map_type`,
    `classify_race`, `normalize_distance`, `season_label`; re-exports `maybe_float` /
    `fmt_pace` from `nerd_common.format`.
  - `stats.py` — `compute_stats`, `build_race_records`, `compute_pr_cards`,
    `PR_CARD_SPECS`.
  - `theme.py` — thin wrapper over `nerd_common.theme` supplying grid color + title font
    so chart builders call bare `tidy_dark(fig)` / `fig_html(fig, height, div_id=...)`.
  - `charts.py` — all Plotly `chart_*` builders (the largest logic module).
  - `components.py` — hand-rolled HTML/SVG: `stat_card_html`, `pr_card_html`,
    `race_card_html`, `heatmap_html` (SVG calendar), `build_day_index`, `notes_search_html`.
  - `sections.py` — the six `section_*` assemblers.
  - `template.py` — static `CSS` / `JS` / `THEME_INIT_JS` / `hash_init_js` /
    `view_paint_css` string constants (theme toggle, tab routing, detail panel, notes
    search, cross-chart date sync all live here).
  - `page.py` — `build_html`, `NAV_VIEWS`, the assembler.
- **Units policy**: **No conversion.** Pace is already native **min/mile**
  (`pace_min_per_mile`) and times are `M:SS` / `H:MM:SS`. There is no metric→imperial
  conversion step (unlike Strava). Use `fmt_pace` / `fmt_time` for display; never invent a
  km or km/h surface.
- **Special data seams** (secondary — primary emphasis is quantitative): *analytic* mining
  of the free-text `comments` / `extras` (themes, mood, injuries, weather, placements like
  "37/224"). Note this text is **already displayed** via the race detail panel
  (`template.py` `renderEntry()`) and the Patterns Notes search (`components.notes_search_html`),
  so any new work is aggregate analysis, not first exposure. Surface it only when the
  numbers alone don't tell the story. The `source/_archive/` folder is an unstructured old
  website dump (meet pages, photo albums, articles, loose media) — **out of scope**.
- **Data access tools**: none beyond `Read`/`Grep`/`Glob`/`Bash` over the CSV — there is
  no MCP data source for this dashboard.

---

## Global policies (apply to every view)

- **Imports**: stdlib + `plotly` + `numpy` only in the `dashboard/` package — no pandas.
  All stats are precomputed in Python. `beautifulsoup4` / `lxml` are used **only** in
  `parse_log.py` (the ingest), never in the build.
- **ASCII-only chart text**: axis titles, tick labels, hovertemplates, and annotations use
  ASCII (the CSS handles typographic niceties).
- **Theming**: charts must read in **both** light and dark. The page restyles charts at
  runtime via `applyChartTheme()` from CSS custom properties; any color you introduce must
  be covered there (the dark-token trace colors teal/amber/violet/coral/blue are
  theme-stable; text/grid/pill colors are not). Detail-panel and heatmap text use CSS
  variables (`var(--text-*)`), never baked hex — `qa.py` enforces this.
- **Chart div ids**: every `fig_html(...)` call takes an explicit `div_id`. The static
  `qa.py` `CHART_IDS` list must include any new chart id, or its structural check fails.
- **Detail-panel / cross-chart sync**: date-axis charts that should participate in the
  shared zoom register their id in `DATE_CHART_IDS`; click-to-detail charts fire
  `plotly_click` handled by `openDetail(date)`. Follow the existing wiring in
  `template.py` rather than inventing a parallel mechanism.

### Section contract (how to add a new view)

1. Add the `chart_*` builder(s) to `charts.py`, each returning a Plotly figure themed via
   `tidy_dark(fig)` then per-chart overrides.
2. Add a `section_<name>(rows, ...)` function to `sections.py` returning an HTML string of
   the exact shape:
   ```html
   <section id="view-<name>" class="view">
     <div class="page-header">
       <div class="eyebrow">EYEBROW</div>
       <h1>Section Title</h1>
     </div>
     <!-- cards; charts wrapped as: -->
     <div class="card">
       <div class="card-title">Chart Title</div>
       {fig_html(chart_x(rows), height=H, div_id="chart-x")}
     </div>
   </section>
   ```
3. Append `("<name>", "Tab Label")` to `NAV_VIEWS` in `page.py` and call the new
   `section_<name>` in `_build_sections`.
4. Add every new chart id to `CHART_IDS` in `running-log/qa.py`.

---

## Current-state views

The dashboard ships six sections. `NAV_VIEWS` (order = tab order; first is default):
`overview, volume, mix, performance, races, patterns`.

### 1. Overview — `section_overview` (eyebrow DASHBOARD)
- **Stat cards** (`stat_card_html`, from `compute_stats`): Total Miles, Avg Mi/Week, Peak
  Week, Races, Longest Streak (days), Active Days (%).
- **Training Notes search** (`notes_search_html`) — client-side filter over
  `comments`/`extras` with per-type pills + live highlighting.
- **Training calendar heatmap** (`heatmap_html`) — hand-rolled SVG, one row per year
  (2003–2007), 7×N cells, two color modes (Workout Type / Miles Intensity) toggled in JS.
- **Cumulative Mileage** — `chart_cumulative`, `div_id="chart-cumulative"`, h=280.

### 2. Volume — `section_volume` (eyebrow TRAINING)
- **Weekly Mileage** — `chart_weekly`, `div_id="chart-weekly"`, h=320.
- **Average Weekly Mileage by Season** — 4 sparkline cards (`chart_seasonal_sparklines`),
  div ids `spark-fall` / `spark-winter` / `spark-spring` / `spark-summer`.
- **Monthly Mileage by Year** — `chart_monthly_mileage_by_year`,
  `div_id="chart-monthly-by-year"`, h=340.

### 3. Workout Mix — `section_workout_mix` (eyebrow TRAINING)
- **Workout donut** — `chart_workout_donut(rows, races_by_cat)`, `div_id="chart-donut"`
  (easy/long/tempo/workout/race split, `TYPE_COLORS`).
- **Easy Run Pace Over Time** — `chart_easy_pace`, `div_id="chart-easy-pace"` (area line;
  **no `fill:tozeroy`** — `qa.py` asserts this).
- **Miles by Workout Type per Season** — `chart_workout_mix_by_season`, fine-grained
  stacked types (`WORKOUT_MIX_COLORS`).

### 4. Performance — `section_performance` (eyebrow RACING)
- **Combined pace-over-time / season-best** — `chart_pace_timeline`,
  `div_id="chart-pace-timeline"`, colored by `EVENT_GROUPS`.
- **PR progression small-multiples** — `chart_pr_progression` per `PR_PROGRESSION_SPECS`;
  div ids `chart-pr-800m`, `chart-pr-mile`, `chart-pr-5k-xc`, `chart-pr-5k-track`,
  `chart-pr-3k-steeple`.
- **PR timeline strip** — `chart_pr_timeline`, `div_id="chart-pr-timeline"`.
- **PR cards** — `pr_card_html` from `compute_pr_cards` / `PR_CARD_SPECS` (7 cards: 800m,
  Mile, 1500m, 3k Steeple, 5k Track, 5k XC, 6k XC).

### 5. Races — `section_races` (eyebrow RACING)
- **Category tabs** — Cross Country / Indoor Track / Outdoor Track (pill switcher).
- **Race cards** (`race_card_html`) with PR badges; counts 31 XC / 29 Indoor / 39 Outdoor
  (Mud Run omitted). Classification rules live in `data.classify_race`:
  - **Cross country**: `month in {9,10}` or (`month==11 and day<25`).
  - **Indoor track**: `month==12` or `month<=2` or (`month==3 and day<28`).
  - **Outdoor track**: (`month==3 and day>=28`) or `month in {4,5}`.
  - **Omitted**: `2004-06-06` (Camp Pendleton Mud Run).

### 6. Patterns — `section_patterns` (eyebrow ANALYSIS)
- **Avg Miles by Day of Week** — `chart_dow`, `div_id="chart-dow"` (7 bars, opacity scales
  with value).
- **Avg Weekly Miles by Month** — `chart_monthly_avg`, `div_id="chart-month"` (12 bars).
- **Streak analysis** — stat grid from `compute_stats`.

### Design tokens (shared)
Dark tokens (`ACCENT #58a6ff`, `BG_*`, `BORDER_*`, `TEXT_*`, Geist / Geist Mono fonts)
come from `nerd_common.tokens` — **shared verbatim with the Strava dashboard**. Running-log
workout-type colors (local to `config.py`): easy `#2dd4bf`, tempo `#f59e0b`, long
`#a78bfa`, race `#f87171`, workout `#60a5fa`. Light-mode palette and the runtime toggle are
in `template.py`.

---

## New views

<!-- The orchestrator appends verified view specs here, one block per view, in the
     Section-contract shape above. Each block: Type / Data (file + columns + transform
     recipe from dash-analyst) / X axis / Y axis / Color by / Interactivity / Edge cases /
     Verify vs recipe (pinned spot-check values dash-developer confirms and running-log-qa
     asserts). Leave nothing "TBD." -->

_None yet — this section grows as the pipeline builds new views._
