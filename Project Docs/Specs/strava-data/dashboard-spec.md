# Strava Dashboard — View Specs

Generated 2026-06-10 by the `/strava` multi-agent pipeline running fully autonomously
(orchestrator: Claude Fable 5). Status: **SPEC — Exploratory tab V1–V8, ready to build.**

> **2026-06-11 refinements** — six targeted updates to the CORE dashboard (calendar,
> overview, volume, elevation, pace) plus a theme-sync fix. Spec in the
> "Core Dashboard Refinements (2026-06-11)" section near the end of this file.

Pipeline provenance: the `/dashboard strava-data` multi-agent pipeline —
`dash-analyst` (discovery + verified transform recipes) → `dash-creativity` (ranked menu) →
`dash-viz-design` (this spec) → `dash-developer` (build) → `strava-qa` (validation). (Earlier
runs used the now-retired `strava-*` reasoning agents; the roles are unchanged.)

---

## Pipeline profile

Machine-readable facts every shared `dash-*` agent loads first when the orchestrator names
`strava-data` as the target (see the repo-root `AGENTS.md`).

- **Target**: `strava-data`
- **Data source**: `strava-data/data/` — live and growing, refreshed by
  `.github/workflows/strava-fetch.yml`. Primary files: `activities.csv` (41 cols incl.
  `distance_km`, `moving_time_min`, `total_elevation_gain_m`, `average_heartrate`,
  `average_speed_kmh`, `suffer_score`, `sport_type`, `start_date_local`, `gear_id`),
  `segment_efforts.csv`, `segments_summary.csv`, `streams/{id}.csv` (per-activity time
  series), `laps/{id}.csv` (fetched, not yet consumed — retained intentionally),
  `gear.json`, `athlete.json`.
- **Build command**: `uv run python strava-data/build_dashboard.py` (run from repo root).
- **Output HTML**: `running-log/strava.html` — a gitignored build artifact written into the
  `running-log/` directory (the GitHub Pages publish root shared by both dashboards). It is
  never committed; `deploy.yml` rebuilds and publishes it. The deployed Pages site, not this
  file, is the pipeline's end.
- **Static QA**: none dedicated — the units grep (below) plus the `strava-qa` agent.
- **QA agent**: `strava-qa` (build integrity, spec compliance, units policy, data
  accuracy, edge cases, HTML sanity, responsive light/dark visual audit).
- **Module map** — `build_dashboard.py` is a thin entrypoint calling `build_page()`. Add
  `chart_*` functions to the right `strava-data/dashboard/` module and wire into
  `page.build_page()`: `theme.py` (`tidy_dark`, `fig_html`), `charts_production.py`,
  `charts_exploratory.py` (`chart_x_*`), `rollups_cards.py`, `config.py`, `data.py`,
  `geometry_stats.py`, `template.py`, `page.py`.
- **Units policy**: **imperial display, metric data** — running pace min/mi (`M:SS`, axes
  reversed), MTB/cycling speed mph, temperature °F. Never emit `min/km`, `km/h`, `kph`, or
  `°C` in displayed text; `dash-developer` greps the output for those (0 hits) before
  handoff. Full rules under "Display units" below.
- **Special data seams**: live Strava MCP tools (`mcp__strava__*`) for stats/zones/streams
  the CSVs lack; per-activity GPS streams power the Places views. This is the rich, growing
  data contrast with the frozen Running Log dataset.

---

## Exploratory Tab — Build-Ready Spec (V1–V8)

Source of truth for all conventions: the `strava-data/dashboard/` package (chart builders live
in `charts_production.py`/`charts_exploratory.py`, styling in `theme.py`). Reuse `tidy_dark(fig)`
then per-chart overrides AFTER it; wrap every figure in `fig_html(fig, H, div_id=...)`.
Charts are built with dark-theme defaults and restyled at runtime by `applyChartTheme()`
(page JS, CSS-variable driven) — **every chart must be legible in BOTH light and dark mode**,
so any text/grid/pill color a chart introduces must be covered by `applyChartTheme()`.
Hover-only; no cross-chart sync. Data: `strava-data/data/activities.csv` only. Runs =
`Run`+`TrailRun` (teal), MTB = `MountainBikeRide` (amber).

### Display units (global policy — applies to every view)
Data files stay metric; convert at display time only. All displayed text (axis titles, ticks,
hovertemplates, annotations, bins, vrect/line labels):
- **Running pace: min/mi**, formatted `M:SS`; pace axes REVERSED (faster = up/right). Running
  effort is always pace, never speed.
- **MTB / cycling speed: mph.**
- **Temperature: °F.**
Never display `min/km`, `km/h`, `kph`, or `°C`. Stats quoted on-chart (means, percentiles,
deltas) are recomputed in the display unit. Appendix A pinned values remain METRIC for
internal verification — convert before comparing (mi = km × 0.621371; min/mi = min/km ÷
0.621371; °F = °C × 9/5 + 32).

### Global rules (apply to every view below)
- **Imports:** stdlib + `plotly` + `numpy` ONLY. No pandas/scipy/sklearn. All statistics
  (z-scores, OLS, PCA via `numpy.linalg.svd`, k-means by hand, Welch t, percentiles, rolling
  sums, ACWR) precomputed in Python at build time. Transforms are verified — implement per
  Appendix A recipes; do not re-derive. Pin the named values called out under each view.
- **Color constants by NAME** (do not hardcode new palette hex): the running teal, MTB amber,
  other slate, elevation violet, and accent constants already defined in `dashboard/config.py`.
  For shades, derive teal-dark / teal-light as `rgba` of the running hex (state the rgba in
  code comments), never a new palette.
- **ASCII only** in all Python `print()` and all on-chart text. Use `->` not arrows, `delta`
  not Greek, `<=`/`>=`. No emoji in chart text.
- **Do NOT modify** `SYNC_IDS` or `CLICK_IDS`. New charts are absent from both.
- **Div id prefix** `chart-x-` for all 8. Heights via `fig_html(fig, H, div_id)`.
- **Legends:** use `tidy_dark`'s default; turn off (`showlegend=False`) where the spec says
  "no legend."
- **Annotation style:** `xref/yref="paper"` unless a data anchor is specified; plot font,
  size 10, secondary text color (or trace color where noted), translucent pill `bgcolor`,
  no arrow unless stated. Pill + text colors must adapt with the page theme (covered by
  `applyChartTheme()`), and annotations must not cover plotted data — placing them outside
  the plot area is allowed.

### Section contract
- **Nav tuple:** append `("exploratory", "Exploratory")` to the nav list in `build_page()`,
  AFTER `("map", "Map")`. No JS/tab-handler change needed (`.tab[data-view]` is generic).
- **Section HTML:** insert a new `<section id="view-exploratory" class="view">` AFTER
  `view-map`'s closing `</section>` and BEFORE `</main>`. Skeleton:
  ```html
  <section id="view-exploratory" class="view">
    <div class="section-anchor">Exploratory</div>
    <div class="card">
      <div class="card-title">About This Section</div>
      <p class="attribution">...exact copy below...</p>
    </div>
    <div class="card"><div class="card-title">The Temperature Mirage</div>{fig_html(v1,460,"chart-x-mirage")}</div>
    <div class="card"><div class="card-title">Athlete Archetypes</div>{fig_html(v2,520,"chart-x-archetypes")}</div>
    <div class="card"><div class="card-title">Two Cardiac Worlds</div>{fig_html(v3,420,"chart-x-cardiac")}</div>
    <div class="card"><div class="card-title">She Pays Pace, Not Heart, for Heat</div>{fig_html(v4,460,"chart-x-heat")}</div>
    <div class="card"><div class="card-title">The Seasonal Handoff</div>{fig_html(v5,440,"chart-x-seasonal")}</div>
    <div class="card"><div class="card-title">Cadence Is the Gearbox</div>{fig_html(v6,460,"chart-x-cadence")}</div>
    <div class="card"><div class="card-title">The Metronome and Its Tail</div>{fig_html(v7,420,"chart-x-metronome")}</div>
    <div class="card"><div class="card-title">Load, Monotony & the Spike Zone</div>{fig_html(v8,480,"chart-x-load")}</div>
  </section>
  ```
- **Attribution CSS** (add one rule near `.card-title`):
  `.attribution { font-size:13.5px; color:var(--text-secondary); line-height:1.65; margin:0; }`
- **Attribution copy** (EXACT, inside `<p class="attribution">`):
  > This section was created entirely by Claude — Anthropic's `<strong>`Claude Fable 5`</strong>`
  > model (`<code>`claude-fable-5`</code>`) acting as orchestrator, dispatching the
  > strava-data-analyst, strava-creativity, strava-viz-design, strava-developer, and strava-qa
  > subagents. Every analysis, statistical test, and line of code below was produced autonomously.

  (Render the em dash literally; `<strong>` wraps "Claude Fable 5"; `<code>` wraps `claude-fable-5`.)

---

### V1 — The Temperature Mirage
- **div id:** `chart-x-mirage` · **height:** 460 · **Type:** Scatter (markers) + raw line + raw OLS + temp-adjusted line + adjusted OLS. **Carries a metric toggle: Air temp (default) ↔ Apparent temp (heat index).**
- **Toggle control:** two-button segmented control above the chart (`.seg-filter` / `.seg-btn`, same as V4). Buttons: **Air temp** (active by default) and **Apparent temp**.
- **Toggle semantics — keep raw fixed, swap adjusted only.** The raw/uncontrolled trend does not use temperature, so it is computed **once** on the air-temp population and never moves. Only the temperature-adjusted monthly-mean line, its OLS-over-time trend, and the r/p annotation swap between metrics. Each adjusted view filters to runs that have that metric and temp-adjusts (OLS eff~temp residuals, z-scored) on its own population; the x-origin is shared so dates line up.
- **7 total traces (stable indices):**
  - 0 individual runs (raw_z markers, teal `opacity=0.25` size 5), 1 raw monthly mean (slate dashed line+markers), 2 raw OLS trend (slate dashed) — **always visible**.
  - 3 air-adjusted monthly mean (teal solid), 4 air-adjusted OLS trend (teal dashed) — `visible=True`.
  - 5 apparent-adjusted monthly mean, 6 apparent-adjusted OLS trend — `visible=False`.
- **Toggle JS (`toggleMirage`):** `Plotly.restyle(el, {visible:[...]}, [3,4,5,6])` (air → `[true,true,false,false]`, app → `[false,false,true,true]`) + `Plotly.relayout(el, {'annotations[0].text': MIRAGE_ANN[view]})`. Raw traces 0–2 are never touched.
- **X axis:** month bin midpoint date — label "Month" — ticks `MMM YY`, autoranged (future months never clipped).
- **Y axis:** z-scored aerobic efficiency — label "Aerobic efficiency (z-score)" — zeroline shown.
- **Legend:** ON, bottom: "Individual runs", "Raw (uncontrolled)", "Temperature-adjusted".
- **Annotation (index 0, top-right paper x=0.98,y=0.97):** raw prefix is identical across views (raw is fixed); only the Adjusted r/p differ.
  - **Air temp:** `Raw r=-0.194, p=0.008 -> Adjusted r=-0.068, p=0.358`
  - **Apparent temp:** `Raw r=-0.194, p=0.008 -> Adjusted r=-0.026, p=0.755 (~19% fewer than air temp)`
- **Sample-size caveat:** apparent-temp view uses fewer runs (n=149 vs air n=184) from lower `apparent_temp_c` backfill coverage; the auto-computed `(~X% fewer than air temp)` note rides in the apparent annotation.
- **Hover:** lines -> `%{x|%b %Y}<br>z = %{y:.2f}`; runs -> activity name + `z=%{y:.2f}`.
- **Edge cases:** runs missing HR or the relevant temp metric excluded per view; coverage differs by design. Months with <2 runs plot as-is.
- **Verify vs recipe:** `V1_raw_r=-0.194`, `V1_raw_p=0.008`, `V1_air_adj_r=-0.068`, `V1_air_adj_p=0.358`, `V1_app_adj_r=-0.026`, `V1_app_adj_p=0.755`, n=184, n_app=149, 20 bins.

### V2 — Athlete Archetypes
- **div id:** `chart-x-archetypes` · **height:** 520 · **Type:** PCA biplot — Scatter (markers) + 8 loading-arrow lines + labels + optional convex hulls.
- **Data:** complete-case n=237 (Run 171, TrailRun 12, MTB 54); 8 standardized features -> PCA via `numpy.linalg.svd`; k-means (k=3, hand-coded, deterministic best-of-50 from rng(42)) per recipe. **No imputation — complete cases only.** Cadence intentionally excluded from features (0% populated for MTB).
- **X axis:** PC1 score — label "PC1 — session size / effort (52.4%)".
- **Y axis:** PC2 score — label "PC2 — sport signature: HR (+) vs elevation (-) (21.0%)".
- **Markers:** color BY cluster — "Long/hard runs" n=70 = teal-dark `rgba(13,148,136,1)`; "Short/easy runs" n=121 = teal-light `rgba(94,234,212,1)`; "MTB rides" n=46 = amber. Symbol BY sport: circle=run, diamond=MTB. Size 7, opacity 0.85.
- **Loading arrows:** 8 lines from origin, each `(loading_x, loading_y) * 8.669`, slate, width 1.5, feature labels slate size 9.
- **Hulls (optional):** per-cluster convex hull, filled cluster color @0.06, not in legend.
- **Legend:** ON bottom — 3 cluster entries with counts; symbol key as slate annotation bottom-left: `circle = run   diamond = MTB`.
- **Hover:** activity name + cluster label (customdata). Arrows `hoverinfo="skip"`.
- **Edge cases:** sign convention fixed per recipe (avgHR loads +0.726 on PC2, elevation -0.346).
- **Verify vs recipe:** `V2_pc1_var=52.4%`, `V2_pc2_var=21.0%`, `V2_scale=8.669`, cluster sizes 70/121/46, n=237, inertia 1050.68.

### V3 — Two Cardiac Worlds
- **div id:** `chart-x-cardiac` · **height:** 420 · **Type:** Overlaid histograms + 2 vertical mean lines + max-HR markers.
- **Data:** avg HR — Run n=183 (mean 153.5), MTB n=54 (mean 138.0). Bins width 5, range 85-175. `barmode="overlay"`, `opacity=0.6`.
- **X axis:** "Average HR (bpm)", range 85..175. **Y axis:** "Activities".
- **Mean lines:** vertical dashed at 153.5 (teal) and 138.0 (amber), labeled.
- **"Same redline" element:** markers/ticks near top at max-HR means 168.4 (teal) and 171.1 (amber), caption `max HR nearly identical (168.4 vs 171.1)`.
- **Legend:** ON bottom — "Run" / "MTB".
- **Annotation:** top-center: `delta = 15.5 bpm | Welch t=15.74 | p=3.1e-33`.
- **Edge cases:** missing avg HR excluded; fixed bin edges aligned across traces.
- **Verify vs recipe:** `V3_welch_t=15.742`, `V3_welch_df=145.56`, `V3_welch_p=3.128e-33`, n 183/54.

### V4 — She Pays Pace, Not Heart, for Heat
- **div id:** `chart-x-heat` · **height:** 460 · **Type:** 4 Violin traces (pace) + mean-HR line on secondary y (`make_subplots` secondary_y). **Carries a metric toggle: Air temp (default) ↔ Apparent temp (heat index).**
- **Toggle control:** two-button segmented control above the chart, reusing the existing `.seg-filter` / `.seg-btn` pattern (same markup/CSS/active-state as other segment filters). Buttons: **Air temp** (active by default) and **Apparent temp**.
- **Two precomputed views, 10 total traces.** Each view = **5 traces** (4 Violin pace + 1 HR Scatter line):
  - Traces 0–4 = **air-temp view** (`average_temp_c`), `visible=True`.
  - Traces 5–9 = **apparent-temp view** (`apparent_temp_c`), `visible=False`.
  - Both views use the **identical fixed °F band edges 48/62/75** (converted to °C: 48F→8.89C, 62F→16.67C, 75F→23.89C) and the same 4 bands Cool `<48F` / Mild `48–62F` / Warm `62–75F` / Hot `>=75F`. Fixed-edge bands, not equal-sized terciles.
- **Toggle JS:** on click, `Plotly.restyle(el, {visible:[...]}, [0..9])` swaps which view's 5 traces show, and `Plotly.relayout(el, {...})` swaps the bottom stat annotation text (Welch numbers/n differ per view and can't ride along on `restyle`). Both annotation strings are precomputed and stored inline in a small JS object keyed by view (`air`/`app`). X-axis band labels are identical across views — not swapped.
- **Data (air-temp view, default):** runs with `average_temp_c` present, fixed °F bands. n=202 — Cool 64, Mild 55, Warm 67, Hot 16.
- **Data (apparent-temp view):** runs with `apparent_temp_c` present, same fixed °F bands. n=162 — Cool 62, Mild 35, Warm 44, Hot 21 (~20% fewer than air-temp due to lower `apparent_temp_c` backfill coverage). No empty bands; no low-n (<5) bands in either view.
- **X axis:** categorical "Cool (<48F)", "Mild (48-62F)", "Warm (62-75F)", "Hot (>=75F)" — label "Temperature band". Identical category array for both views.
- **Y1 (pace):** "Pace (min/mi, faster = up)" — **REVERSED** (`autorange="reversed"`),
  ticks formatted `M:SS`. **Shared/union ticks:** `tickvals`/`ticktext` computed from the union of both views' pace arrays (via `_pace_ticks`) so the pace axis is identical in both toggle states.
- **Y2 (HR):** "Mean HR (bpm)" — fixed range **[145, 160]** so the flat line reads flat. Verified valid for both views: air HR means 154.21/151.75/154.20/154.82; apparent HR means 154.3/151.6/153.6/155.9 — all within range, no widening needed.
- **Violins:** `box_visible=True`, `meanline_visible=True`, points off; cool=slate, mild=`rgba(245,158,11,0.4)`, warm=amber, hot=red (`SLOWER` #f87171); opacity 0.7. Same colors reused for both views — no new theme entries.
- **HR line:** air-temp means 154.2/151.7/154.2/154.8; apparent-temp means 154.3/151.6/153.6/155.9, teal, markers+line, secondary y. Skip `None` for any empty band (none occur in either view currently).
- **Legend:** OFF for violins; slate annotation: `teal line = mean HR (right axis)`.
- **Annotation (bottom-center, swapped per view via `relayout`):**
  - **Air temp:** `Cool 8:58 vs Hot 9:38 /mi | t=-1.77 | p=0.097 | HR flat (t=-0.27, p=0.79) | n=202`
  - **Apparent temp:** `Cool 8:55 vs Hot 9:23 /mi | t=-2.35 | p=0.027 | HR flat (t=-0.98, p=0.334) | n=162 (~20% fewer than air temp)`
- **Sample-size caveat (surfaced in both spec and chart annotation):** apparent-temp view has ~20% fewer runs than air-temp (162 vs 202) from lower `apparent_temp_c` backfill coverage. The toggle is **1:1 axis-equivalent** (identical pace ticks and HR range) but **not sample-size-equivalent** — each view's n is printed in its annotation.
- **Thesis check across views:** "pays pace, not heart" holds in both — pace slows Cool→Hot while HR stays flat. Apparent temp makes the pace effect *stronger and significant* (t=-2.347, p=0.0273) vs air temp's non-significant trend (t=-1.766, p=0.097); HR stays flat in both (apparent HR-flat t=-0.983, p=0.334; air HR-flat t=-0.27, p=0.79).
- **Edge cases:** missing metric excluded per view ("all available per view", coverage differs by design); cut points fixed 48/62/75°F (8.89/16.67/23.89°C) for both metrics, not recomputed per metric; bands not equal-sized terciles; empty band renders nothing and HR line skips `None` mean (none occur currently); pace ticks from the union of both views so they never shift on toggle.
- **Verify vs recipe — air temp:** `V4_air_welch_t=-1.766`, `V4_air_welch_p=0.0966`, HR means 154.21/151.75/154.20/154.82, n 64/55/67/16, overall n=202.
- **Verify vs recipe — apparent temp:** `V4_app_welch_t=-2.347`, `V4_app_welch_p=0.0273`, `V4_app_hrflat_t=-0.983`, `V4_app_hrflat_p=0.3335`, HR means 154.3/151.6/153.6/155.9, n 62/35/44/21, overall n=162.

### V5 — The Seasonal Handoff
- **div id:** `chart-x-seasonal` · **height:** 440 · **Type:** Filled area (run km) + bars (MTB count) on secondary y + optional faint slate temp line.
- **Data:** calendar-month aggregation SUMMED across years. Run km: Jan 146.1, Feb 75.5, Mar 93.2, Apr 126.8, May 118.3, Jun 78.2, Jul 72.4, Aug 97.5, Sep 65.5 (min), Oct 127.5, Nov 156.0, Dec 175.1. MTB rides: 6,5,8,6,6,3,0,1,4,4,5,7.
- **X axis:** "Month", Jan..Dec names. **Y1:** "Run distance (km, summed)" teal area (`fill="tozeroy"`, fill `rgba(45,212,191,0.18)`). **Y2:** "MTB rides (count)" amber bars, opacity 0.7.
- **MTB blackout band:** `add_vrect` over Jul-Sep, violet @0.10, annotation `MTB blackout - 0 July rides`.
- **Legend:** ON bottom.
- **Edge cases:** explicit 0 for July MTB (zero-height bar, not missing). Sum, not mean, across years.
- **Verify vs recipe:** `V5_total_run_km=1332.1`, `V5_total_mtb_rides=55`, `V5_sep_km=65.5` (min), `V5_jul_mtb=0`.

### V6 — Cadence Is the Gearbox
- **div id:** `chart-x-cadence` · **height:** 460 · **Type:** Scatter (HR-color-graded) + OLS line + vertical median reference.
- **Data:** runs n=201 with cadence>0. x=avg cadence (spm, single-leg), y=avg pace **min/mi**
  (REVERSED axis, faster = up, ticks `M:SS`; computed from avg speed), color=avg HR.
- **Markers:** teal sequential colorscale `[[0,'rgba(13,148,136,0.15)'],[1,'rgba(45,212,191,1)']]`, `cmin=85, cmax=171`, colorbar "Avg HR". Runs missing HR -> separate slate trace.
- **OLS line:** slate dashed. The verified fit is speed(km/h) ~ cadence (slope 0.3928,
  intercept -22.0324) — do not refit; TRANSFORM the fitted line into pace space for display
  (pace_min_mi(x) = 60 / ((slope*x + intercept) * 0.621371), sampled over the cadence range;
  renders as a smooth curve).
- **Reference:** vertical at median 83.1, slate dotted, label `median 83.1 spm`.
- **Legend:** OFF; caption `MTB excluded (no cadence data)` bottom-left.
- **Annotation:** top-left: `r=0.787 | p=1.2e-43 | cadence-HR only r=0.40`.
- **Verify vs recipe:** `V6_slope=0.3928`, `V6_intercept=-22.0324`, `V6_r=0.7872`, n=201.

### V7 — The Metronome and Its Tail
- **div id:** `chart-x-metronome` · **height:** 420 · **Type:** `make_subplots(rows=1, cols=2)` twin histograms.
- **LEFT "Run pace":** pace in **min/mi** (= 60/avg_speed_kmh / 0.621371), n=201, teal bars,
  bin 0.4 min/mi (~the original 0.25 min/km granularity); central-80% `add_vrect` p10 8:29 ->
  p90 9:52 /mi teal @0.10; median line 9:02 /mi; x ticks `M:SS`; tail annotation:
  `tail: 4 trail (300m+ gain), 8 social`. (Internal tail rule stays pace>6.5 min/km.)
- **RIGHT "MTB speed":** in **mph**, n=55, amber bars, bin 0.5 mph (~the original 1 km/h);
  lines at p10=5.7, p50=8.2, p90=9.4 mph labeled.
- **Legend:** OFF; `subplot_titles=["Run pace","MTB speed"]`.
- **Edge cases:** tail = pace>6.5, exactly 12 runs (trail rule: TrailRun OR elevation>=300m -> 4 trail, 8 social). Fixed `xbins`.
- **Verify vs recipe:** `V7_run_p10=5.272`, `V7_run_med=5.618`, `V7_run_p90=6.129`, `V7_tail_n=12`, `V7_mtb_p50=13.120`.

### V8 — Load, Monotony & the Spike Zone
- **div id:** `chart-x-load` · **height:** 480 · **Type:** violet 7d suffer-sum line (Y1) + slate ACWR line (Y2) + 4 horizontal bands + peak annotation. Whole-athlete (all sports).
- **Data:** daily axis 2024-11-20..2026-06-07 (565 days), zero-filled. 7d rolling SUM right-aligned min_periods=1 (peak 536 on 2025-09-18). ACWR = 7d rolling mean / 28d rolling mean, both min_periods=1, but **plot ACWR only from day 28 onward** (line breaks/NaN before).
- **Y1:** "7-day suffer score (sum)" violet width 1.5. **Y2:** "ACWR (7d / 28d)" slate, fixed range 0..2.2.
- **Bands (on Y2, behind):** <0.8 slate `rgba(139,148,158,0.06)`; 0.8-1.3 teal `rgba(45,212,191,0.08)`; 1.3-1.5 amber `rgba(245,158,11,0.10)`; >1.5 red `rgba(248,113,113,0.14)`. Right-edge labels, slate, size 9.
- **Peak annotation:** data-anchored: `peak 536 (2025-09-18)`, violet, arrow.
- **Annotation:** top-right: `27 days in spike zone (>1.5)`.
- **Legend:** ON bottom — "7d suffer (sum)", "ACWR".
- **Edge cases:** days with no activity = 0; null suffer_score rows contribute 0.
- **Verify vs recipe:** `V8_peak=536` on `2025-09-18`, `V8_spike_days=27`, `V8_median_acwr=1.000`, `V8_days=565`, `V8_total_suffer=18158`.

### Out of scope
- No cross-filter / shared-date sync (not added to `SYNC_IDS`).
- No detail-panel click-through (not added to `CLICK_IDS`); hover-only.
- No new data files, no pandas/scipy/sklearn, no network calls at build time.

(Charts are NOT dark-only: they are restyled live by `applyChartTheme()` and must read
correctly in both page themes — see the global theming note at the top.)

---

## Appendix A — Verified Transform Recipes (analyst Job B, pinned spot-checks)

Source for all views: `strava-data/data/activities.csv` (331 rows). Parse `start_date_local`
as datetime. Runs = sport_type in (Run, TrailRun); MTB = MountainBikeRide. Percentiles =
numpy default linear interpolation. All p-values via the validated routine in Appendix B.
**Pinned values below are METRIC (internal verification units)** — displayed values follow
the global Display-units policy (min/mi, mph, °F); convert before comparing.

### V1 recipe
- Filter: runs with non-null speed+HR+temp -> n=181. `eff = average_speed_kmh / average_heartrate`.
- Temp-adjust: OLS `eff ~ average_temp_c`; residuals. z-score both (ddof=0). Monthly bins by
  calendar year-month (20 months 2024-11..2026-06), plot mean per month. Trend lines fit on RAW
  per-run points (x = days since first run).
- Pinned: raw_r=-0.1834 p=0.01346; adj_r=-0.0627 p=0.4020; paceHR-resid-vs-temp r=0.2313
  p=0.00170; temp-vs-HR r=-0.0068 p=0.9277; first month 2024-11 n=6 raw_z=0.899 adj_z=0.767;
  raw slope -1.214e-03 /day, adj slope -4.149e-04 /day (on z).

### V2 recipe
- Filter: Run/TrailRun/MTB complete cases on 8 features (distance_km, moving_time_min,
  total_elevation_gain_m, average_speed_kmh, average_heartrate, max_heartrate, suffer_score,
  calories) -> n=237 (Run 171, TrailRun 12, MTB 54). NO imputation.
- Standardize (mean, std ddof=0). PCA: `U,S,Vt = np.linalg.svd(Z, full_matrices=False)`;
  EVR = S^2/sum(S^2); scores = U*S; loadings = rows of Vt.
- Sign convention: per PC, if the largest-|loading| feature has negative loading, flip that
  PC's loadings and scores. (Result: avgHR +0.726 on PC2.)
- K-means: k=3, best-of-50 k-means++ restarts from ONE `np.random.default_rng(42)`, keep
  lowest inertia (Appendix B code). Single-seed = degenerate 14/54/169 — do NOT use.
- Pinned: EVR PC1 52.45%, PC2 21.00%. PC1 loadings: dist .445, time .467, elev .338,
  speed .083, avgHR .082, maxHR .272, suffer .405, cal .467. PC2: dist -.237, time -.150,
  elev -.346, speed -.138, avgHR .726, maxHR .407, suffer .301, cal .024.
  Inertia 1050.68; sizes {46,70,121}. Centroids (orig units): Long/hard runs n=70: 9.08km,
  52.3min, 115m, HR 157.1, suffer 117.1. Short/easy n=121: 5.19km, 29.6min, 57m, HR 150.6,
  suffer 49.8. MTB n=46: 11.67km, 52.6min, 184m, 13.59km/h, HR 137.6. Feature means:
  dist 7.598, time 40.792, elev 98.667, speed 11.124, avgHR 149.973, maxHR 169.0,
  suffer 72.215, cal 425.422. Score ranges: PC1 [-6.24, 6.99], PC2 [-6.18, 2.59].
  Biplot arrow scale = 8.669 (= 0.9 * max|score| / max|loading|).

### V3 recipe
- Groups: non-null avg HR. Run+TrailRun n=183 mean 153.51; MTB n=54 mean 137.98.
- Histogram bins width 5 bpm, range 85-175. Welch t (Appendix B): t=15.742, df=145.56,
  p=3.128e-33. Max-HR means: run 168.39, MTB 171.07.

### V4 recipe
- Filter: runs with non-null temp AND speed -> n=201 (HR not required). pace=60/speed.
- Fixed °F band edges (not data-driven terciles): 48/62/75°F -> 8.89/16.67/23.89°C.
  cool = temp<8.89 (n=64), mild = 8.89<=temp<16.67 (n=55), warm = 16.67<=temp<23.89 (n=66),
  hot = temp>=23.89 (n=16).
- Pinned: cool pace mean 5.570 median 5.540; hot mean 5.990 median 5.885; Welch
  (cool vs hot) t=-1.766 p=0.0966. Mean HR per band (non-null HR within band):
  154.21 / 151.75 / 154.20 / 154.82; HR cool-vs-hot t=-0.275 p=0.787.

### V5 recipe
- Group by calendar month (1-12) across all years. Run km = sum distance_km (Run+TrailRun);
  MTB rides = count. Mean temp per month for context line.
- Pinned (month: run_km / mtb / temp): Jan 146.1/6/6.8, Feb 75.5/5/9.8, Mar 93.2/8/16.7,
  Apr 126.8/6/13.8, May 118.3/6/18.2, Jun 78.2/3/20.8, Jul 72.4/0/20.9, Aug 97.5/1/22.4,
  Sep 65.5/4/24.0, Oct 127.5/4/17.2, Nov 156.0/5/13.2, Dec 175.1/7/7.6.
  Totals: run 1332.1 km, MTB 55 rides. NOTE: annual run minimum is Sep (65.5), not Jul.

### V6 recipe
- Filter: runs, cadence non-null and >0 -> n=201. OLS speed~cadence: slope 0.3928,
  intercept -22.0324, r 0.7872, p 1.206e-43. Median cadence 83.10. HR colorscale 85-171.
  Cadence axis [68.5, 105.3], speed [5.01, 17.79]. 18 runs lack HR -> slate trace, kept in fit.

### V7 recipe
- Run pace n=201 (pace=60/speed): bins 0.25 min/km range ~3.25-12.0. p10=5.272, p50=5.618,
  p90=6.129. Tail = pace>6.5 -> 12 runs; trail if TrailRun OR elevation>=300m -> 4 trail,
  8 social. MTB speed n=55: bins 1 km/h range ~7-17; p10=9.246, p50=13.120, p90=15.154.

### V8 recipe
- ALL sports. Daily sum suffer_score, zero-filled 2024-11-20..2026-06-07 (565 days). Null
  suffer rows contribute 0. 7d rolling SUM right-aligned min_periods=1: peak 536 on
  2025-09-18, median 206.0. ACWR = (7d rolling mean)/(28d rolling mean) min_periods=1,
  evaluated all days but PLOT from day 28. Bands 0.8/1.3/1.5. Day counts: <0.8 -> 133,
  0.8-1.3 -> 354, 1.3-1.5 -> 51, >1.5 -> 27. Median ACWR 1.000. Monotony (if shown):
  7d mean/7d std ddof=0, min_periods=7, median 0.803. Total suffer 18158. Daily value on
  2025-09-18 = 163; on 2024-11-20 = 13.
- NOTE: legacy "61 days >1.5" from discovery does NOT reproduce; assert 27.

---

## Core Dashboard Refinements (2026-06-11)

Six approved updates (orchestrator: Claude Opus 4.8). All edits in `build_dashboard.py`;
regenerate `strava.html`. Must read correctly in BOTH light and dark themes.

**R1 — Activity calendar → SVG (match College Running Log exactly).** Replace the Plotly
heatmap `chart_calendar()` with a function returning a raw SVG/HTML string mirroring
`running-log/index.html` (CSS 433-498, HTML 1006-1164) and `running-log/visualize_log.py`
(1039-1165). Cells 11×11px `rx=2`, gap 2 (week stride 13), `label_w=28`; rest days
`fill="var(--text-tertiary)" fill-opacity="0.10"`. Day labels single-letter `S M T W T F S`
`<text class="hm-dow">` at x=0. Year labels in a 36px left column (`.hm-year-row` flex →
`.hm-year` + per-year `<svg>`). Month labels `<text class="hm-month">` at top. Intensity =
`--accent` at opacity = `mi / max_mi`, **max_mi = data-driven** (actual max across all days).
Legend = horizontal gradient bar above the grid: `.hm-legend.hm-legend-intensity` with
`0 mi` meta · `.hm-legend-grad` (140×10px, `linear-gradient(to right, color-mix(in srgb,
var(--accent) 10%, transparent), var(--accent))`) · `{max:.0f}+ mi` meta. Per-cell `<title>`
hover (`{date} · {mi:.1f} mi ({n} activities)`). Add `.hm-*` CSS (remap to `--text-tertiary`,
`--text-secondary`, `--accent`) to the CSS f-string — theme-aware via CSS vars, no Plotly
retint. Embed: inject SVG string directly at the `chart-cal` slot (drop `fig_html`). Remove
unused `CAL_COLORSCALE`.

**R2 — Overview: Longest Run on its own row + Longest MTB.** `compute_stats`: add
`longest_mtb` (max mi over `mtb_rows`). Render the 4 summary cards first, then Longest Run +
Longest MTB. `.stat-grid` `grid-template-columns: repeat(5,1fr)` → `repeat(4,1fr)` so the two
"longest" cards wrap to row 2.

**R3 — Weekly Volume rangeslider in light mode.** In `applyChartTheme()`, when
`fl.xaxis && fl.xaxis.rangeslider`, add `'xaxis.rangeslider.bgcolor': cssVar('--bg-glass')`
and `'xaxis.rangeslider.bordercolor': cssVar('--border-subtle')` to the relayout `upd`.

**R4 — Weekly Elevation Gain breakdown (mirror Weekly Volume).** Rewrite `chart_elevation`
like `chart_volume`: aggregate `weekly[wk][cat]` via `sport_category`, 3 stacked `go.Bar`
(Running/MountainBikeRide/Other) using `SPORT_COLORS`/`SPORT_DISPLAY`, `barmode="stack"`,
y-title "Elevation Gain (ft)", per-week hovertext. Drop the single `ELEVATION_COLOR` bar.

**R5 — Pace/Speed: remove trend line.** Delete the rolling-quarterly dashed trace in
`chart_pace`. Remove `_rolling_quarterly` if unused elsewhere.

**R6 — Chart subtitles legible in light mode.** Expose `window.__applyChartTheme =
applyChartTheme` in the theme IIFE; call it in `activateView` after the `Plotly.Plots.resize`
loop so hidden-tab chart titles get retinted to `--text-primary` when shown.

---

## Temperature toggles (2026-06-21)

Extends the V4 (She Pays Pace) Air temp ↔ Apparent temp toggle pattern to two more
temperature-driven charts. Same `.seg-filter`/`.seg-btn` control, same Plotly
`restyle` (trace visibility) + `relayout` (annotation text) mechanism, same baked-air /
hidden-apparent precomputation. Toggles are **independent per chart** (no shared state).
Apparent-temp views use fewer runs (lower `apparent_temp_c` backfill coverage) and surface
an auto-computed `~X% fewer` caveat. See the **V1 — The Temperature Mirage** spec above for
that chart's full toggle contract (raw-fixed / adjusted-only swap, 7 traces, `toggleMirage`).

**Heart Rate vs Temperature** (`chart_run_hr_vs_temp`, Trends tab, div `chart-run-hr-temp`):
- Two views built into one figure; air-temp scatter+regression per sport (`visible=True`),
  apparent-temp per sport (`visible=False`). Trace counts can vary (a sport could be empty),
  so the builder returns per-view `air_vis`/`app_vis` boolean arrays + `trace_idx`, and the JS
  (`toggleHrTemp`) applies them verbatim — no hard-coded indices.
- **Shared/union axis ranges** (x and y) across both views so air ↔ apparent reads 1:1.
- Hover labels read "Apparent temp: X°F" in the apparent view, "Temp: X°F" in air.
- **3 fixed annotation slots:** 0 = Run R² (teal), 1 = TrailRun R² (violet), 2 = caveat
  (slate pill, blank for air; `apparent temp: ~X% fewer runs than air temp` for apparent).
  `toggleHrTemp` swaps `annotations[0..2].text` from `air_anns`/`app_anns`.
- Builder return changed from `fig` to `(fig, meta)`; `page.py` threads `meta` into `build_js`.

## Calendar click-through (2026-06-21)

Extends the shared detail panel (previously map/HR/pace charts only, via `showDetail` /
`plotly_click` + `customdata`) to the SVG calendar (R1), which is hand-built and not a Plotly
figure.

- `chart_calendar()` (`charts_production.py`) emits `data-date="{ds}"` on every `<rect
  class="hm-cell">` that has at least one logged activity that day — **including zero-distance
  days** (e.g. RockClimbing, WeightTraining; opacity floors at 0.08 via the existing
  `max(0.08, mi/max_mi)` clamp). Rest days (no activity) get no `data-date` and stay
  non-interactive. CSS: `.hm-cell[data-date] { cursor: pointer }`, and the existing hover-scale
  pop (`transform: scale(1.4)`) is scoped to `[data-date]` only so rest days don't look
  clickable.
- `_activity_detail_json()` (`page.py`) adds a `desc` field per activity (raw `description`
  CSV column, stripped; `""` when absent).
- `template.py`: the single-activity render path used by `showDetail` is factored into
  `renderActivity(a)`, which also appends a `.d-desc` block (`white-space: pre-wrap`) when
  `a.desc` is truthy. A client-built `DAY_INDEX` (date → activity-id array, grouped from
  `ACT_DATA` at load) backs `showDay(dateStr)`, which renders every activity for that date via
  `renderActivity`, joined by a `.d-sep` divider, and opens the panel through the same
  `openPanel()` both paths share. Click listeners attach to `.hm-cell[data-date]`.

## Activity Details mini-map — route + elevation (2026-07-18)

Adds a compact **route sketch + violet elevation profile** to each GPS activity's block in
the shared detail panel (right drawer on desktop, bottom sheet on mobile), directly below the
stat tiles in `renderActivity(a)`. **Phase 1** shipped the tile-free version; **Phase 2** (below)
layers a real MapLibre basemap behind the route.

- **Data:** per-activity geometry from `data/streams/{id}.csv` via `_load_trip_geo(aid, cap=64)`
  (reused as-is — the same decimated `path`/`elev` the Places passport/peaks use). New
  `_activity_geo_json(rows)` (`page.py`) builds `GEO_DATA = { id: {path, elev, sport} }`, keyed by
  activity id, **only for rows with GPS** (`start_latlng` non-empty and a stream that yields ≥2
  points). Emitted as `var GEO_DATA` alongside `ACT_DATA` (`template.py`) and threaded through
  `build_js(act_json, geo_json, …)`. `_activity_detail_json` also gains an `"id"` field so
  `renderActivity` can look up `GEO_DATA[a.id]`.
- **Render (inline SVG, no draw hook):** `miniMap(a)` returns an HTML string appended in
  `renderActivity`; it lives entirely in the `innerHTML` write and themes for free via CSS vars.
  Route: `<svg viewBox="0 0 1 1" preserveAspectRatio="xMidYMid meet">` with two stacked
  `<polyline>`s (a neutral **casing** under the sport-colored **route**), both
  `vector-effect: non-scaling-stroke`. Route color = `var(--running)` teal (Running/TrailRun) or
  `var(--mtb)` amber (MountainBikeRide). Elevation: a separate short `<svg preserveAspectRatio="none">`
  strip — a `var(--elevation)` violet fill (`fill-opacity: 0.16`) + stroke, mirroring the Peaks
  `drawSpark` `x=j/(n-1), y=1-elev[j]` mapping.
- **CSS** (`template.py`, in the `.d-*` block): `.mm-wrap`/`.mm-map` (aspect-ratio 3/2 box on
  `--bg-elevated` with a `--border-subtle` frame), `.mm-cas` (dark casing; white in `:root.light`,
  mirroring the hero's `drawGlow` pass-1), `.mm-route`/`.mm-run`/`.mm-mtb`, `.mm-elev*`.
- **Edge cases:** indoor/no-GPS activities are absent from `GEO_DATA`, so `miniMap` returns `''`
  and the panel shows stats only. `showDay` stacks N activities → N independent self-contained SVGs
  across the `.d-sep` divider (no shared state). Theme toggle needs no JS — the route/casing/
  elevation all resolve their colors from CSS custom properties on the live `.light` class.
- **`.env`:** `config.py` now `load_dotenv(strava-data/.env)` (best-effort) so a local
  `MAPTILER_KEY` need not be exported by hand; `strava-data/.env.example` documents it (gitignored).

### Phase 2 — MapLibre Glow basemap behind the route (2026-07-19)

A spike ruled out the MapTiler **Static Maps API** (403 on the current plan — a paid feature);
tiles work, so the basemap renders via a small **per-panel MapLibre GL map**, the only free-tier
option that matches the Places hero in both themes. Full rationale + comparison:
`Plans/strava-data/detail-minimap-future-work.md`.

- **Data:** `_load_trip_geo` now also returns raw `coords` (flat `[lng,lat]`, 5dp); `_activity_geo_json`
  adds `coords` + `bbox` (`[minLng,minLat,maxLng,maxLat]`) to each `GEO_DATA` entry, keeping `path`
  (tile-free fallback) + `elev` + `sport`. Payload ≈ 395KB → ~600KB inline.
- **Basemap:** `template.py` emits `MM_KEY` (from `MAPTILER_KEY`) + `MM_TILES_OK`. `miniMap(a)` now
  emits `.mm-map` as a **container div** (with `data-mm=id`) holding the Phase 1 route as
  `.mm-fallback` SVG. `initMiniMaps()` (called from `openPanel`) lazily — via `IntersectionObserver`
  on `#detail-body` — builds one `maplibregl.Map({interactive:false})` per container: style =
  `mmStyleUrl()` (glow only: `backdrop-v4-dark` / custom Glow-light id, mirroring the hero
  `charts_places.py:1138–1152`), route drawn as **casing + sport-colored line layers** (colors from
  the live `--running`/`--mtb` CSS vars), then `fitBounds(bbox, {padding:24})` and the fallback SVG
  is hidden. Route/elevation still theme via CSS vars; `window.__miniMapRestyle` (called from
  `applyChartTheme`) `setStyle`s open maps on theme toggle and re-adds layers on `style.load`.
- **`showDay` / lifecycle:** maps are tracked in `MM_MAPS` and torn down (`map.remove()`) by
  `closeDetail` **and** at the top of `openPanel`, so stacking never leaks WebGL contexts (cap ~16);
  lazy-init means only scrolled-into-view blocks spin up a map.
- **Graceful degradation:** empty `MAPTILER_KEY` or missing `window.maplibregl` → `MM_TILES_OK` is
  false, `initMiniMaps` is a no-op, and the Phase 1 tile-free SVG stays — identical to how the hero
  degrades. Compact MapTiler/OSM attribution is kept (ToS).

## Heat & Sun — UV/temp partial-R² charts (2026-07-11)

Net-new **Exploratory** subsection ("Heat & Sun · Does Weather Predict Pace?")
answering: after removing what distance + elevation already explain, does **air
temperature**, **UV index**, or a **combined temp+UV** score best predict
endurance pace (running) / speed (MTB)? First use of the `uv_index` column.
Builders live in `charts_exploratory.py` (`chart_x_heatsun`, `chart_x_heatverdict`);
both share `_heatsun_prep(rows, sport_types, is_run)`.

**Method (shared, honest by construction):** complete-case rows with
distance/elevation/`average_temp_c`/`uv_index`/`average_speed_kmh`. Response =
pace min/mi (run) or speed mph (MTB). **Baseline** OLS `response ~ 1 + distance +
elevation`; the **residual** is the response with distance+elevation removed. Each
weather model is fit on that residual and its **partial R²** (`1 − SS_res/SS_tot`
of the residual) is the share of left-over variance it explains: **Temp** =
quadratic `resid ~ tempF + tempF²` (allows the literature inverted-U); **UV** =
linear `resid ~ uv`; **Combined ("WBGT-lite")** = `resid ~ tempF + tempF² + uv`.
No HR gate (full N). `numpy.linalg.lstsq` only (no pandas/scipy). Temperature is
shown in **°F**, running pace **min/mi `M:SS` reversed**, MTB **mph** — data stays
metric, converted at display time.

**Honesty rails (baked into captions/annotations):** UV is a **solar-load / clear-sky
proxy**, not an independent physiological driver, and is collinear with temp; the
combined score is **WBGT-lite** because humidity is unavailable (true WBGT needs it);
all effects are small — weather explains only a few percent of pace once
distance+elevation are removed. No new palette color (teal `SPORT_COLORS["Running"]`,
amber `SPORT_COLORS["MountainBikeRide"]`, slate `TEXT_SECONDARY`, dark pill
`--ann-pill-bg`). Attribution card notes these two charts were a later Opus build.

### V9 — Heat & Sun (Temperature vs UV)
- **div id:** `chart-x-heatsun` · **height:** 460 · **Type:** Scatter (markers) + fit line. **Running only** (Run+TrailRun). **Carries a metric toggle: Air temp (default) ↔ UV index.**
- **Toggle control:** two-button `.seg-filter`/`.seg-btn` (Air temp active by default, UV index).
- **4 traces (stable indices):** 0 temp scatter (teal, opacity 0.5), 1 temp quadratic curve (slate dashed) — `visible=True`; 2 UV scatter, 3 UV linear fit — `visible=False`.
- **Toggle JS (`toggleHeatSun`):** `Plotly.restyle(el,{visible:[…]},[0,1,2,3])` (temp→`[T,T,F,F]`, uv→`[F,F,T,T]`) + `Plotly.relayout` swaps `xaxis.title.text` (Air temperature (°F) ↔ UV index) and `annotations[0].text`. **Y-axis never moves.**
- **X axis:** Air temperature °F (temp view) / UV index (UV view), autoranged.
- **Y axis:** distance+elevation-residualized pace shown as `residual + mean pace`, label "Adj. pace (min/mi, faster = up)", **reversed** via explicit range `[p98.5+0.4, p1.5−0.4]`, `M:SS` ticks from `_pace_ticks`. A couple of extreme residual outliers may clip by design.
- **Annotation (index 0, swapped per view, bottom-right):**
  - **Air temp:** `Temp partial R²=0.024 · warmer → slower (no in-range optimum)`
  - **UV index:** `UV partial R²=0.020 · solar-load proxy, not a UV effect (r=0.47 with temp)`
  - Index 1 (static, top-left slate): `dashed = fit · pace holds distance & elevation fixed`.
  - **Temp optimum rule:** annotate `fastest ≈ X°F` only when the parabola vertex is the fastest-kind extremum (min for pace / max for speed) **and** within the data's temp range; otherwise report the monotonic direction. In the current data the running vertex is out-of-range → "no in-range optimum".
- **Hover:** temp → `X °F<br>adj pace M:SS /mi`; uv → `UV X.X<br>adj pace M:SS /mi`.
- **Edge cases:** rows missing any of distance/elevation/temp/UV/speed excluded; UV partial R² equals `corr(resid, uv)²` (verified).
- **Verify vs recipe:** `V9_n=173`, `V9_r2_base=0.156`, `V9_temp_pR2=0.0237`, `V9_uv_pR2=0.0202`, `V9_comb_pR2=0.0318`, `V9_collinear=0.466`, temp optimum = none (in-range).

### V10 — The Verdict (which metric predicts best?)
- **div id:** `chart-x-heatverdict` · **height:** 420 · **Type:** grouped **horizontal** bars (`barmode="group"`), one trace per sport.
- **Data:** partial R² for Temp / UV / Combined, Running (teal, n=173) vs MTB (amber, n=51). Bars labeled `X.X%` outside; x-axis `tickformat=".0%"`, range `[0, max*1.25]`.
- **Legend:** ON — `Running (n=173)` / `MTB (n=51)`. **Annotation (bottom-right slate pill):** `Running: Combined wins, but all weak · temp~UV r=0.47`.
- **Hover:** `Running · Temp<br>partial R² 0.024` etc.
- **Verify vs recipe — Running:** `V10_run_temp=0.0237`, `V10_run_uv=0.0202`, `V10_run_comb=0.0318`, best=Combined, `collinear=0.466`.
- **Verify vs recipe — MTB:** `V10_mtb_temp=0.0045`, `V10_mtb_uv=0.0112`, `V10_mtb_comb=0.0132`, `V10_mtb_r2_base=0.666`, `collinear=0.570`.

---

## Appendix B — Validated numeric routines (copy verbatim into build_dashboard.py)

p-values (matches scipy to full precision; used for V1/V3/V4/V6):

```python
import math

def betacf(a, b, x):
    EPS = 3e-12; FPMIN = 1e-300
    qab = a + b; qap = a + 1.0; qam = a - 1.0
    c = 1.0; d = 1.0 - qab * x / qap
    if abs(d) < FPMIN: d = FPMIN
    d = 1.0 / d; h = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < EPS: break
    return h

def betai(a, b, x):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    return 1.0 - bt * betacf(b, a, 1.0 - x) / b

def t_two_sided_p(t, dfree):
    return betai(dfree / 2.0, 0.5, dfree / (dfree + t * t))

def welch_ttest(x, y):   # x, y numpy arrays
    import numpy as np
    n1, n2 = len(x), len(y)
    v1, v2 = x.var(ddof=1), y.var(ddof=1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    t = (x.mean() - y.mean()) / se
    dfree = (v1/n1 + v2/n2)**2 / ((v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1))
    return t, dfree, t_two_sided_p(abs(t), dfree)

def ols_r_p(x, y):       # returns slope, intercept, r, p
    import numpy as np
    b, a = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    n = len(x)
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return b, a, r, t_two_sided_p(abs(t), n - 2)
```

Deterministic k-means (V2):

```python
import numpy as np

def kmeans_pp_init(Z, k, rng):
    n = Z.shape[0]
    centers = [Z[rng.integers(n)]]
    for _ in range(1, k):
        d2 = np.min(np.sum((Z[:, None, :] - np.array(centers)[None, :, :])**2, axis=2), axis=1)
        centers.append(Z[rng.choice(n, p=d2 / d2.sum())])
    return np.array(centers)

def lloyd(Z, k, init, iters=300, tol=1e-10):
    C = init.copy()
    for _ in range(iters):
        lab = np.argmin(np.sum((Z[:, None, :] - C[None, :, :])**2, axis=2), axis=1)
        newC = np.array([Z[lab == j].mean(0) if np.any(lab == j) else C[j] for j in range(k)])
        if np.allclose(newC, C, atol=tol): C = newC; break
        C = newC
    return lab, C, np.sum((Z - C[lab])**2)

# Procedure: 50 restarts from ONE rng, keep lowest inertia. Deterministic.
# rng = np.random.default_rng(42); 50x lloyd(Z, 3, kmeans_pp_init(Z, 3, rng))
# -> inertia 1050.6752, sizes {46, 70, 121}
```

---

## Places — Build-Ready Spec

> Building or designing here? Prefer the **`maptiler` skill** for MapTiler/MapLibre specifics
> (tile styles, static maps, SDK/data-driven styling) over ad hoc implementation or research.
> If it isn't available on this machine, fall back to reading `charts_places.py`/`template.py`
> and MapTiler/MapLibre's public docs directly — don't block on the skill.

> **UPDATE (2026-07 · open-source tiled basemap).** The hero's **basemap** is now a
> real tiled map rendered by **MapLibre GL JS** (loaded from CDN; `config.MAPLIBRE_CDN`),
> with a three-way **Glow / Street / Terrain** toggle. **Street/Terrain use MapTiler
> tiles** (`config.MAPTILER_KEY`, from the `MAPTILER_KEY` build env / Actions secret,
> domain-restricted to `ducktapegirl.github.io`); **Glow** is a tile-free transparent
> style over the hero's radial-gradient ground and is also the graceful fallback when
> MapLibre or the key is unavailable. The **route glow is unchanged in spirit** — the
> same additive (`lighter`) / `multiply` per-sport polyline overlay — but it now renders
> on a **2D `<canvas>` overlay above the MapLibre canvas**, projecting each point through
> **`map.project()`** (Web Mercator) instead of the old equirectangular `projX/projY`.
> Consequently the bespoke camera (`COSLAT` frame, `cur{s,fx,fy}`, `tweenTo`, custom
> pan/zoom/pinch/marquee) is **retired** in favor of MapLibre's native camera + gestures
> (`cooperativeGestures`), and the injected `PD` frame constants (`lng0/lngspan/lat1/
> latspan`) now serve only to reconstruct geographic **bounds** (`allBounds`, `viewBounds`)
> and **label lng/lat**. `window.placesFlyTo()` keeps its exact contract (named View or
> `{lat0,lat1,lng0,lng1}` box → `map.fitBounds`) so the Homes/Passport/Peaks deep-links are
> untouched. The sections below on the equirectangular frame, the inlined vector
> `basemap.json`, and the `hillshade.png` terrain describe the **superseded** canvas basemap
> and are retained for history; `_load_basemap`/`_load_hillshade` and those assets are no
> longer used by the hero.
>
> **FOLLOW-UP (2026-07 · Backdrop ground + full dark mode).** **Glow** now renders a real
> MapTiler **Backdrop** basemap (`backdrop-v4`) rather than the transparent style — a neutral
> greyscale ground purpose-built for data overlays. The transparent style (`tilelessStyle()`,
> formerly `glowStyle()`) is now **only** the no-tiles/no-key fallback. All three modes track
> the page theme via one `styleForMode()` table (`{glow:'backdrop-v4', street:'streets-v2',
> terrain:'outdoor-v2'}` + a `-dark` suffix in dark theme), so **Terrain now has a dark variant
> (`outdoor-v2-dark`)** — it is no longer light-only. The glow composite consequently
> simplifies to `additive = !TH.light` (the `mode!=='terrain'` special case is gone), and the
> theme toggle now restyles every mode (gated on `TILES_OK`, not `mode!=='glow'`).
>
> **FOLLOW-UP (2026-07 · light-theme label contrast).** Manual review of the new Backdrop
> ground found the non-home ("trip") label coord/sub lines (e.g. Vancouver, Sierra) hard to
> read in light theme. Measured cause: `drawLabel()`'s `alpha*0.85`/`alpha*0.9` fade on those
> lines computed as low as **3.56:1** against the real light basemaps' near-white backgrounds
> (`backdrop-v4` `hsl(0,0%,100%)`, `streets-v2` `hsl(42,49%,93%)`, `outdoor-v2`
> `hsl(120,4%,95%)`) — below WCAG AA's 4.5:1 for normal text. Fix: in light theme those
> multipliers are now `1.0` (no fade — matches the name line's alpha, which already cleared AA
> at 4.75–5.14:1 unfaded); dark theme keeps the original 0.85/0.9 fade since its dark grounds
> give 4.75:1+ headroom regardless. Home labels (full alpha, `--text-primary`) were never
> affected.
>
> **FOLLOW-UP (2026-07 · lighter Glow ground + route standoff).** Two changes, one pass. (1)
> **Lighter Glow in light theme** — the raw Backdrop ground read heavier than the pre-MapTiler
> canvas hero. Rather than a CSS wash over Backdrop, Glow's light-theme ground is now a **custom
> MapTiler style** ("BackgroundGhost", style id `019f7141-13e8-7ca3-bd1d-c8bc1184f396`) purpose-
> built for the near-white/faint-line look, selected in `styleForMode()` via
> `if(m==='glow' && isLight()) return mtStyle(GLOW_LIGHT_STYLE_ID)`. Dark-theme Glow is
> unchanged (`backdrop-v4-dark` — no custom dark counterpart yet); Street/Terrain are unchanged
> in both themes. Uses the same `MAPTILER_KEY` as every other style (one account, one
> domain-restricted key). An earlier version of this fix used a CSS `filter` wash on the stock
> Backdrop ground instead — superseded once a custom style became available, since layering a
> generic wash on a style already tuned to look right risks over- or under-lightening it. (2)
> **Route standoff** — `drawGlow()` now draws each route in **two passes**: a contrasting
> casing (white@.9 light / near-ground-dark@.85 dark, width `lw+2`, `source-over` so it isn't a
> no-op under the colored pass's `multiply`/`lighter` composite — and all casings first so none
> nicks a neighbour's colour), then the per-sport colour on top (its existing composite). Line
> weight bumped to `max(1.4, min(3.0, 0.7+z*0.18))`. Paths are projected once into a `Path2D`
> per track and stroked twice (cheaper than re-projecting on pan). Closes
> `Plans/strava-data/places-basemap-contrast-future-work.md`.
>
> **FOLLOW-UP (2026-07 · shareable activity deep-links + hash-sync fix).** The hash contract
> (`#places?v=<frame>&b=<base>`, built by `syncHashState()`/`applyHashState()`) gains a third,
> mutually-exclusive param: **`a=<activityId>`** (the Strava activity id behind a Passport
> stamp/brief chip/Peaks row), which supersedes `v=` when present — `b=` still composes
> independently. The Pass C click handlers (below) call `window.placesLinkActivity(id)` right
> after `placesFlyTo`, writing `#places?a=<id>`; on load, `applyHashState()` stashes it in
> `pendingActivity` (parallel to the existing `pendingFrame`) so the fly-to fires on
> `map.on('load')`, resolved against `window.placesFlyTargets` — a `{activityId: {lat0,lat1,
> lng0,lng1}}` map the Passport/Peaks scripts publish from their own `PC` payload (`PC[slot].id`
> alongside the existing `.fly`). An unresolvable/removed id falls back to the default (All)
> frame — no console error.
>
> Bundled in the same pass: the page-level tab router (`template.py`'s `activateView`) previously
> wrote a bare `#<section>` on every switch, which silently dropped Places' `v=`/`b=`/`a=`
> sub-state on a return visit even though the hero still showed it — the URL and the page
> disagreed. Fix: `activateView` now calls **`window.placesSyncHash()`** (`= syncHashState`)
> instead of writing the hash itself when the target section is `places`, so returning to Places
> re-asserts whatever sub-state is current; every other section is unaffected.

Pass A (Foundation + Hero) of the approved Places plan (`Plans/strava-data/places-plan.md`, `places-prespec.md`).
Design source: `mocks/places-hero-mock.html` — **port its structure/CSS/JS; this spec
enumerates every delta needed for real data.** Architecture is locked Option A: the hero is a
**bespoke `<canvas>` renderer — NOT Plotly, NOT tiles.** `chart_places_hero(rows)` (new module
`dashboard/charts_places.py`) returns one **raw HTML/`<canvas>`/JS string with real data injected
as JSON** (the `chart_calendar()` raw-string precedent). No `fig_html`, no `tidy_dark`. All numbers
below come from the analyst's verified Pass-A recipe — implement, do not re-derive.

Tone contract (pre-spec §1): neutral keepsake. No tagline, no achievement copy — a quiet `PLACES`
eyebrow, the map, five labels, a legend, one mono stat line.

### Section contract (Pass A)
- **Nav tuple:** in `page.py`, replace `("map", "Map")` with `("places", "Places")` — same
  position (after `segments`, before `exploratory`). No tab-router JS change (`.tab[data-view]`
  is generic).
- **Section HTML:** replace the whole `<section id="view-map" class="view">` with, for `view-places`:
  ```html
  <section id="view-places" class="view">
    {chart_places_hero(rows)}
  </section>
  ```
  The builder string IS the section body: one `<div class="places-hero" id="places-hero">…</div>`
  containing its own `<style>`, canvas, chrome, and `<script>` (fully self-contained). Pass B/C
  cards will be appended after the hero div, inside the same section, in the normal `.card` flow.
- **Retire `chart_map()`:** delete the builder in `charts_production.py`, its import and the
  `mp = chart_map(rows)` call in `page.py`, and remove `"chart-map"` from `CLICK_IDS`
  (`CLICK_IDS = ["chart-hr", "chart-pace"]`). This is the one sanctioned `CLICK_IDS` edit; do not
  touch `SYNC_IDS`. `MAP_CENTER_LAT/LON` in `config.py` may remain (unused) — do not repurpose.
- **Full-bleed:** the hero breaks out of `main`'s 1100px column with the negative-margin bleed:
  `.places-hero { position:relative; width:100vw; margin-left:calc(50% - 50vw); overflow:hidden;
  border-top:1px solid var(--border-subtle); border-bottom:1px solid var(--border-subtle); }`.
  Height: desktop `height:clamp(560px, calc(100svh - 150px), 900px)`; at `max-width:640px`
  `height:clamp(480px, 74svh, 760px)`. **Template.py delta 1 (required):** add
  `body { overflow-x: clip; }` so the 100vw bleed never spawns a horizontal scrollbar.
- **Template.py delta 2 (required):** at the end of `applyChartTheme()`, add
  `if (window.__placesHeroRedraw) window.__placesHeroRedraw();` — this retints the canvas on
  theme toggle AND on tab activation (activateView already calls `applyChartTheme`).
- **Do not port** the mock's `html,body{overflow:hidden}` rule or the `.mocknote` element.
- No `.section-anchor` — the on-canvas `PLACES` eyebrow replaces it.

### P1 — Places Hero
- **Container id:** `places-hero` · **canvas id:** `chart-places-hero` · **Type:** bespoke 2D
  canvas route-density map (additive glow), hand-rolled camera, tweened fly-to.
- **Data:** `data/streams/*.csv` via a new stdlib+numpy loader (no pandas). Per analyst recipe
  (pinned): 324 tracks with valid GPS (20 indoor blanks skipped); decimate each `[lng,lat]`
  polyline with RDP epsilon = 0.0001 deg (~11 m), then hard-cap 150 points by uniform stride;
  round lat/lng to 5 decimals on serialize. Expected: **21,372 total points, ~0.47 MB JSON**,
  per-track min/med/p95/max = 2/62/122/144.

#### Injected JSON (const `PD`, compact `json.dumps(..., separators=(",",":"))`)
```
{
 "lng0": -126.121, "lngspan": 58.135,      // margined All frame, west edge + span
 "lat1": 49.982,  "latspan": 18.027,       // north edge + span
 "ww": 43.8977, "wh": 18.027,              // world units: ww = lngspan*COSLAT, COSLAT=0.7551
 "tracks": [ {"c":0, "g":0, "p":[lng,lat, lng,lat, ...]}, ... ],   // flat pairs, 5-dec
 "labels": [ {"k":"home","name":"SAN DIEGO","coord":"32.95°N  117.09°W",
              "sub":"155 activities · 2025–now","u":0.xxxx,"v":0.xxxx}, ... ],
 "views":  { "sd":  {"u0":0.1500,"u1":0.1595,"v0":0.9282,"v1":0.9670},
             "bos": {"u0":0.9344,"u1":0.9490,"v0":0.4095,"v1":0.4328} }
}
```
- `c` = sport bucket index: 0 Running (Run+TrailRun+**Walk fold-in**), 1 MTB
  (MountainBikeRide+**EBikeRide+Ride fold-in**), 2 Trail·ski (AlpineSki+NordicSki+Snowboard),
  3 Hike, 4 Other (Pickleball, IceSkate, SUP — **drawn silently in slate, no legend row**).
  Pinned bucket counts: **211 / 74 / 11 / 15 / 13** (sum 324).
- `g` = group: 0 = San Diego home box (lat 32.5..33.5, lng -117.6..-116.6), 1 = Boston home box
  (lat 41.9..42.9, lng -71.8..-70.7), 2 = trip (outside both). Classify by the track's **first
  decimated stream point** (covers the 5 valid-GPS tracks that lack `start_latlng`; may differ
  from the start_latlng counts by <=5 — label counts below are hardcoded from the analyst's pins,
  never recomputed from `g`).
- At JS boot, convert once to `Float32Array` u/v: `u=(lng-PD.lng0)/PD.lngspan`,
  `v=(PD.lat1-lat)/PD.latspan` (float32 precision in 0..1 far exceeds the 5-dec source).
- Build console line (ASCII only): `[places] hero: tracks=324 pts=21372 json_kb=~470`.

#### Projection & camera (replaces the mock's `proj`)
The analyst's equirectangular + cos-lat projection, letterboxed, with the mock's `{s, fx, fy}`
camera composed on top in normalized world coords:
```
S0 = min(W / PD.ww, H / PD.wh)               // base letterbox scale, recomputed on resize
proj(u,v) = [ W/2 + (u - cur.fx) * PD.ww * S0 * cur.s,
              H/2 + (v - cur.fy) * PD.wh * S0 * cur.s ]
```
At `cur = {s:1, fx:0.5, fy:0.5}` this IS the analyst's default "All" fit (frame already carries
the +4% margin; north = up; aspect preserved — the mock's anisotropic `nx*W / ny*H` mapping is
**replaced**, not kept). Pan/zoom deltas change accordingly:
- drag: `fx -= dx/(PD.ww*S0*cur.s); fy -= dy/(PD.wh*S0*cur.s)`
- zoom-at-cursor (mock's wheel math with `W→PD.ww*S0`, `H→PD.wh*S0`); clamp `s` to **[0.65, 400]**.
- DPR capped at 2 (mock). Redraw cost is trivial (324 strokes / ~21k vertices per frame).

**Gestures — cooperative (mock delta, required).** A full-bleed ~100svh canvas that
`preventDefault`s wheel/touch would trap page scroll on the Places tab. Adopt the standard
cooperative-gesture pattern:
- Mouse: drag = pan (grab/grabbing cursor, mock). **Wheel zooms only with Ctrl/Cmd held**
  (trackpad pinch arrives as ctrlKey wheel and therefore works natively); plain wheel scrolls the
  page and shows a transient hint pill `Ctrl + scroll to zoom` (1.2 s fade). Dblclick zooms x1.8
  at cursor.
- Touch: canvas `touch-action: pan-y` (one finger scrolls the page). Map pan/pinch-zoom require
  **two active pointers** (pan by centroid delta, zoom by pinch ratio); a one-finger horizontal
  drag shows the hint `Use two fingers to move the map`.
- Hint pill: `.places-hint` — centered, Geist Mono 11px, glass pill (`var(--bg-glass)` +
  `var(--border-subtle)`), opacity-transition only.

**Tween (mock delta, required):** keep 620 ms, ease `1-(1-k)^3`, `prefers-reduced-motion` → snap;
but interpolate **log(s) geometrically** (`s = s_from * pow(s_to/s_from, e)`), fx/fy linear. The
mock's linear-in-s tween degenerates over the real 1 → ~100 zoom range.

#### View control (All · San Diego · Boston · Trips)
Fly-to targets `{s, fx, fy}`; `s` computed at click time from the current canvas size with a 0.94
inset so labels breathe:
`s_view = 0.94 * min( W / ((u1-u0)*PD.ww*S0), H / ((v1-v0)*PD.wh*S0) )`, `fx=(u0+u1)/2`,
`fy=(v0+v1)/2`.

| Button | Camera | Lens |
|---|---|---|
| All | `{s:1, fx:0.5, fy:0.5}` (exact, special-cased — frame has its own margin) | none |
| San Diego | fit `views.sd` → fx **0.1547**, fy **0.9476** (lat 32.55..33.25, lng -117.40..-116.85) | none |
| Boston | fit `views.bos` → fx **0.9417**, fy **0.4211** (lat 42.18..42.60, lng -71.80..-70.95) | none |
| Trips | **tweens to the All target — never zooms** (deterministic from any user pan/zoom state) | `trips` |

**Trips is a highlight lens:** with lens active, per-track alpha becomes
`g<2 ? a*0.20 : min(0.92, a*1.55)` — the mock's exact multipliers, keyed off the real home-box
classification `g` instead of the fake `home` flag. Home labels dim to alpha 0.34; key-trip
labels rise to 0.9 (mock parity). All/SD/Boston clear the lens.

**Fly-to hook (Pass C dependency, build now):** expose
`window.placesFlyTo(target)` where `target` is `'all' | 'sd' | 'bos'` **or** a box
`{lat0, lat1, lng0, lng1}` (south, north, west, east — converted to u/v, fit with the 0.94 inset,
tweened; lens cleared; all `[data-frame]` buttons deactivate unless the name matches).

#### Map control (Glow · Street · Terrain) + theme contract
> Per the 2026-07 update banner: the toggle is now **Glow / Street / Terrain** (MapLibre).
> The **route/glow/theme rows below still apply** to the canvas overlay — same additive
> (`lighter`) vs `multiply` composite, alphas, per-sport colors, and label ink. The change:
> `additive = !light && mode!=='terrain'` — additive only on dark grounds (Glow / dark
> Street), `multiply` on bright grounds (any light theme, and the light Terrain relief).
> The **Glow-ground gradient stays** (the tile-free `#places-hero` background). The
> **Graticule / Terrain contour rings / Terrain-ground / concentric-ellipse placeholder**
> rows are **retired** (MapLibre draws the real basemap now).

Basemap treatment only; routes/glow logic unchanged. The hero ground is driven by **hero-scoped
CSS custom properties** with `:root.light` overrides — the mock's dark commit becomes the dark
half of a theme pair:

| | Dark (default) | Light (`:root.light`) |
|---|---|---|
| Glow ground | mock gradient verbatim: `radial-gradient(120% 120% at 50% 42%, #101725 0%, #0d1117 42%, #05070a 100%)` | `radial-gradient(120% 120% at 50% 42%, var(--bg-base) 0%, var(--bg-surface) 100%)` |
| Terrain ground | mock verbatim: `#1a1512 / #120f11 / #08060a` | same as light Glow (light paper) |
| Composite mode | `globalCompositeOperation='lighter'` (additive glow — **preserve**) | `'multiply'` (ink accumulates darker; additive is invisible on light ground) |
| Route colors | computed `--running`, `--mtb`, `--elevation` (Trail·ski), `#4ade80` `HIKE_COLOR`, `--other` | same var reads → light variants resolve automatically (`#0d9488/#c2710c/#6d28d9/#475569`); Hike stays `#4ade80` (matches the calendar's existing light-mode behavior — no light hike token exists) |
| Base alphas | home tracks `0.30 + 0.12*jitter`, trip tracks `0.50 + 0.12*jitter`, `jitter = (i*0.6180339887) % 1` (deterministic organic variance replacing the mock's rng) | same × 0.85 |
| Graticule | glow `rgba(88,120,170,.09)`, terrain `rgba(120,96,72,.10)` (mock verbatim) | computed `--text-secondary` at alpha 0.10 |
| Terrain contour rings | `rgba(212,160,116,.13)` (mock verbatim) | computed `--text-secondary` at alpha 0.12 |
| Label ink | name `--text-primary`-equivalent whites (mock rgba values), coord/sub slate (mock) | computed `--text-primary` / `--text-secondary`; text shadow flips to `rgba(255,255,255,.85)` halo |
| Footer scrim | `linear-gradient(to top, rgba(5,7,10,.82), transparent)` | `rgba(255,255,255,.82)` → transparent |

The mock's dark ground literals (`#101725 #05070a #1a1512 #120f11 #08060a`, graticule/ring rgba)
are **sanctioned basemap ground tints from the design mock — they are not palette colors and must
not be extended**. No new palette hex anywhere; every sport/emphasis color is a `config.py` token
read through its CSS var. Theme detection: `document.documentElement.classList.contains('light')`,
re-read on every `window.__placesHeroRedraw()` (colors parsed to `r,g,b` once per retint).

Terrain-mode relief (Pass A placeholder for Pass C's real treatment): the mock's 5 concentric
ellipse rings, drawn **only at the SIERRA and MAINE label anchors** (the two mountain trips),
radii `r*16*0.6*rs` / `r*12*0.6*rs` with `rs = min(cur.s, 3)` (cap added so rings don't blow up at
real zoom depths). The route **terrain gradient (green/slate/red) is Pass C — out of scope here.**

#### Route rendering
Mock's draw loop verbatim except as noted: `lineJoin/lineCap='round'`,
`lw = max(0.8, 1.15*min(cur.s, 2))`, one `beginPath`/`stroke` per track, additive (dark) or
multiply (light) composite, then labels in `source-over`. No animated line-drawing. Adaptive
graticule (mock delta): real lat/lng lines, not a decorative 10x10 grid — pick step from
`[10,5,2,1,0.5,0.2,0.1,0.05]` deg, smallest with `step * S0 * cur.s >= 72px`, draw all multiples
crossing the viewport. No graticule labels.

#### Labels & declutter
Injected `labels` array (Python-computed anchors), drawn per the mock's `label()` (dot + name +
mono lines) with one fix: **`ctx.font` cannot resolve `var(--mono)`** — use literal families:
name `600 13px/11px 'Geist', ui-sans-serif, sans-serif`, coord/sub
`11px 'Geist Mono', ui-monospace, monospace`.

| Label | Anchor (u/v) | Lines | Visibility |
|---|---|---|---|
| SAN DIEGO | centroid of first points of `g==0` tracks | name · `{lat:.2f}°N  {lng:.2f}°W` (from centroid) · **`155 activities · 2025–now`** | always, alpha 1 (0.34 under Trips lens) |
| BOSTON | centroid of `g==1` first points | name · centroid coord · **`137 activities · 2024–2025`** | always, alpha 1 (0.34 under lens) |
| SIERRA | centroid of trip first-points inside lat 36.0..37.2, lng -118.9..-117.9 | `SIERRA` · `Whitney · 14,507 ft` | faint-always, alpha 0.8 (0.9 under lens) |
| MAINE | box lat 44.6..45.6, lng -71.2..-69.9 | `MAINE` · `hut ski · 3 days` | faint-always 0.8 (0.9) |
| VANCOUVER | box lat 48.9..49.5, lng -124.3..-122.9 (spans Nanaimo + Stanley Park, Wrinkle A — centroid mid-cluster is correct at this scale) | `VANCOUVER` · `49.3°N · northernmost` | faint-always 0.8 (0.9) |

- The VANCOUVER sub-line uses the analyst's verified northernmost pin (49.29°N — FLAG 3); do NOT
  ship any "northernmost Maine" copy. `155` is the verified SD count — not the pre-spec's ~145.
- The count strings above are **hardcoded from the analyst pins**, never recomputed from `g`.
- **Declutter rule (applies now; Pass C trip labels join the same system):** compute each label's
  screen rect (`measureText` + line stack + 4px pad + dot); place in priority order — homes
  (never skipped) by count desc, then key trips west→east, then (Pass C) other trips. Skip any
  label whose rect intersects an already-placed rect; skipped labels reappear as zoom separates
  them. Cull anchors >40px offscreen (mock). Named non-key trip labels are **deferred to Pass C**
  (no verified trip clusters/names exist yet); their reveal threshold is pinned now: **`cur.s >=
  3.0`**, same collision rule.
- Vertical clamp: label text-block baseline clamped to `[26, H-70]` so San Diego's 3-liner (v≈0.95,
  near the letterbox bottom at All zoom) never collides with the footer scrim; the anchor dot
  stays at the true anchor.

#### Chrome (markup contract)
Port the mock's floating chrome, restyled onto dashboard components:
```html
<div class="places-chrome">
  <div class="places-caption"><p class="places-eyebrow">Places</p></div>
  <div class="places-controls">
    <div class="seg-filter places-seg" role="group" aria-label="View">
      <span class="places-seg-lbl">View</span>
      <button class="seg-btn active" data-frame="all"    aria-pressed="true">All</button>
      <button class="seg-btn"        data-frame="sd"     aria-pressed="false">San Diego</button>
      <button class="seg-btn"        data-frame="bos"    aria-pressed="false">Boston</button>
      <button class="seg-btn"        data-frame="trips"  aria-pressed="false">Trips</button>
    </div>
    <div class="seg-filter places-seg" role="group" aria-label="Basemap">
      <span class="places-seg-lbl">Map</span>
      <button class="seg-btn active" data-base="glow"    aria-pressed="true">Glow</button>
      <button class="seg-btn"        data-base="terrain" aria-pressed="false">Terrain</button>
    </div>
  </div>
  <div class="places-foot">
    <div class="places-legend">
      <span><i class="dot" style="background:var(--running)"></i>Running</span>
      <span><i class="dot" style="background:var(--mtb)"></i>Mountain bike</span>
      <span><i class="dot" style="background:var(--elevation)"></i>Trail / ski</span>
      <span><i class="dot" style="background:#4ade80"></i>Hike</span>
    </div>
    <div class="places-stat"><b>319</b> activities · <b>28</b> regions · <b>9</b> states &amp; provinces</div>
  </div>
</div>
```
- Buttons keep BOTH the dashboard `.active` class and `aria-pressed` in sync. `.places-seg` adds
  the mock's glass-over-map treatment (`backdrop-filter: blur(10px)`, `var(--bg-glass)`,
  `var(--border)`) on top of `.seg-filter`; `.places-seg-lbl` is the mock's mono `View`/`Map`
  prefix (9px, letterspaced, `--text-tertiary`). The existing mobile `.seg-btn{min-height:40px}`
  rule applies automatically. Do NOT use `data-view` on these buttons (reserved by the tab router)
  — `data-frame`/`data-base` only; all listeners scoped inside `#places-hero`.
- Stat line is exact: **`319 activities · 28 regions · 9 states & provinces`** (319 = activities
  with start_latlng; 324 tracks are drawn — the 5 extra are valid-GPS tracks without start_latlng;
  do not "fix" the mismatch). Positions/gradients per mock footer; legend dot for Hike is the
  `HIKE_COLOR` literal (documented exception above); the other three dots are CSS vars so light
  mode retints them for free.
- No tagline `<h1>` (pre-spec removed it); eyebrow only. Canvas gets `role="img"`
  `aria-label="Map of every GPS route: San Diego and Boston home clusters plus trips across North America"`.

#### Motion, lifecycle & a11y
- Keep the mock's entrance choreography (canvas `rise` 1100ms, caption/controls/footer staggered
  `fade` 450/600/750ms) and the 620ms fly-to tween (log-s, above).
  `@media (prefers-reduced-motion: reduce)`: all CSS animations off, opacity 1, tween → snap
  (mock's `reduce` flag — preserve both halves).
- **Sizing:** a `ResizeObserver` on `#places-hero` drives `resize()` (the section is
  `display:none` until its tab activates — window-resize alone reads 0 width; the observer fires
  on first layout). Also expose `window.__placesHeroRedraw = retintAndDraw` (re-reads CSS vars,
  redraws) — called by the `applyChartTheme()` hook (Section contract, delta 2).
- Keyboard: buttons are native (focus-visible outline per mock via `--accent`). Canvas itself is
  non-focusable; all camera destinations are reachable through the View buttons.

#### Edge cases
- 20 indoor/blank stream files skipped; 25 activities without start_latlng: 5 have valid GPS and
  are drawn (classified by first stream point), 20 do not exist as drawable tracks.
- Novelty point-blobs (Pickleball x11, IceSkate, SUP) decimate to ~2 points spanning meters —
  sub-pixel slate flecks at All zoom by design (round lineCap makes them dots at deep zoom).
- Tracks with 2 identical points after decimation: draw anyway (invisible or dot — harmless).
- A key-trip label box with zero contained trip tracks → drop that label silently (assert in
  build print instead of crashing).
- No antimeridian handling needed (lng -123.97..-70.14).
- Zoom floor 0.65 / ceiling 400; 5-decimal coords (~1.1 m) stay smooth at ceiling; RDP epsilon
  ~11 m gives a slightly chunky street trace at extreme zoom — accepted (heatmap aesthetic, not
  route inspection).
- JSON budget: assert <= 0.6 MB and warn if total points drift >5% from 21,372 (data refresh).

#### Verify vs recipe (developer asserts / QA checks)
- `tracks=324`, `total_pts=21372` (±5% tolerance only on data refresh), `json <= 0.6 MB`.
- Bucket counts `211/74/11/15/13` (Running incl. 5 Walks / MTB incl. 11 EBike + 4 Ride /
  Trail·ski / Hike / silent Other) — sum 324.
- Frame constants: `lng0=-126.121, lngspan=58.135, lat1=49.982, latspan=18.027, ww=43.8977,
  wh=18.027, COSLAT=0.7551` (COSLAT from raw-extent midpoint lat 40.9685 — constant, never
  recomputed from the margined frame).
- View centers: SD `fx=0.1547, fy=0.9476`; Boston `fx=0.9417, fy=0.4211`; All `s=1, fx=fy=0.5`.
- Label strings exact: `155 activities · 2025–now` (NOT 145), `137 activities · 2024–2025`,
  `Whitney · 14,507 ft`, `hut ski · 3 days`, `49.3°N · northernmost` (no Maine-northernmost copy).
- Stat line exact: `319 activities · 28 regions · 9 states & provinces`.
- Trips button: camera target equals the All target (no zoom); lens multipliers `x0.20` (g<2) /
  `min(0.92, x1.55)` (g==2); home labels 0.34 / key trips 0.9.
- Dark = `lighter` composite on dark radial ground; light = `multiply` with light-token route
  colors; both themes legible (QA: screenshot both, Glow + Terrain).
- Plain wheel over the hero scrolls the page (hint pill appears); Ctrl/Cmd+wheel zooms;
  one-finger touch scrolls; two-finger pans/zooms.
- `prefers-reduced-motion`: no entrance animation, fly-to snaps.
- Nav shows `Places` (no `Map`); `view-map` section gone; `CLICK_IDS` no longer contains
  `chart-map`; `window.placesFlyTo` exists and accepts `'sd'` and a `{lat0,lat1,lng0,lng1}` box.
- Build print (ASCII): `[places] hero: tracks=324 pts=21372 json_kb=~470`.

---

## Places — Two Homes (Pass B)

Pass B (Module 2) of the Places plan. **Design = Opus spec-extension** (the single Fable dispatch
was spent on the Pass A hero; the aesthetic is already established). Two **equal** glass cards —
San Diego and Boston — that sit BELOW the hero inside `view-places`, in normal `.card` flow.
Neutral keepsake tone: equal weight, no arrow, not before/after. Verified numbers from the analyst
Pass-B recipe (implement live at build time per the "counts stay live" precedent; do not freeze).

### Section placement
- New builder **`chart_places_homes(rows)`** in `charts_places.py`, returning one self-contained raw
  HTML string (style + two cards + one script). Wire it in `page.py` INSIDE `#view-places`, AFTER
  the hero: `<section id="view-places" class="view">{places_hero}{places_homes}</section>` (thread a
  `places_homes` param the same way `places_hero` is threaded through
  `_build_main_charts`/`_assemble_html`/`build_page`; build it right after the hero with a
  `print("  places homes...")` line).
- **Load streams ONCE.** The hero already loads+decimates+classifies every track via `_load_tracks`.
  Refactor so the stream load is shared, not repeated: extract a module-level memoized helper (e.g.
  `_places_tracks(rows)` that caches `_load_tracks`'s `(tracks, extents)` for the process) and have
  BOTH `chart_places_hero` and `chart_places_homes` call it. No second 344-file parse.

### Data (injected JSON, const `PH`, compact `json.dumps(separators=(",",":"))`)
Reuse the hero's already-decimated tracks; filter to each home by the track group `g`
(`g==0` San Diego, `g==1` Boston) and project into each thumbnail's OWN per-metro frame:
```
{
 "sd":  { "fr": {lng0,lngspan,lat1,latspan,ww,wh},   // per-metro frame (below)
          "tracks": [ {"c":<bucket>, "p":[u,v, u,v, ...]}, ... ],  // u/v in 0..1 of the SD frame
          "mi": 782, "seg": "Canyon entrance via Salix", "segN": 34, "era": "2025–now" },
 "bos": { "fr": {...}, "tracks": [...], "mi": 530, "seg": "Cataldo East", "segN": 20,
          "era": "2024–2025" }
}
```
- **Per-metro frame** = each home's drawn-track extent + 6% margin (equal treatment = each metro fit
  to its OWN card, NOT a shared span), then the hero's projection: `ww = lngspan*COSLAT` (COSLAT
  0.7551), `wh = latspan`. Pinned boxes (raw extent + 6%): **SD lat 32.588..33.246, lng
  -117.298..-116.916**; **Boston lat 42.263..42.519, lng -71.723..-70.972**. Compute u/v in Python
  with the hero's `_uv`.
  - **SD northern-tail fallback:** if the SD thumbnail reads sparse at build/QA, clip the SD frame to
    the 99th-pct box **lat 32.635..33.100, lng -117.275..-116.985** (documented analyst alternative).
    Default to the +6% box; switch only if QA flags sparseness.
- Reused point counts at the hero's cap-150 decimation: SD ~12,491 pts / Boston ~7,668 pts (cheap;
  no lighter cap needed).
- **Stats computed LIVE at build time** (not frozen), by `start_latlng`-in-box (the Pass-A
  155/137 definition — NOT the `g` stream grouping, which differs by <=5):
  - `mi` = round(sum(distance_km in box) * KM_TO_MI). Today: SD 781.6->**782**, Boston 529.5->**530**.
    Plain `mi`, NO thousands comma (both are 3-digit).
  - `seg`/`segN` = most-repeated Strava segment: join `segment_efforts.csv` -> activity -> home box,
    `Counter` per segment_id, take `most_common(1)`, label via `segment_name` (from efforts or
    `segments_summary.csv`), count = effort tally. Skip efforts whose activity isn't in either box.
    Today: SD **Canyon entrance via Salix / 34**, Boston **Cataldo East / 20** (robust; clear
    margins 34-vs-26, 20-vs-12; identical under activity-home vs segment-location binning).
  - `era` = the home-era label, **hardcoded per home** (`2025–now` SD, `2024–2025` Boston) with
    an en-dash. This is the "moved away" narrative, NOT literal min/max (Boston has 4 return-visit
    activities in 2026 -> a literal `2024-2026` would muddy the story; keep the era label).
  - Print an ASCII line `[places] homes: sd_mi=782 sd_seg="..."x34 bos_mi=530 bos_seg="..."x20`
    and a soft `[places] NOTE:` if `mi` drifts far from 782/530 or the segment winner changes (so a
    refetch surfacing a different/joke-named winner is visible to QA -- do NOT hard-assert).

### Card markup + layout
```html
<div class="places-homes">
  <div class="places-home">
    <canvas class="places-home-map" id="chart-places-home-sd" role="img"
      aria-label="San Diego route heatmap"></canvas>
    <div class="places-home-body">
      <div class="places-home-name">San Diego</div>
      <div class="places-home-stats">
        <div class="phs-mi"><b>782</b> mi</div>
        <div class="phs-seg"><span class="phs-ovl">Most-repeated segment</span>
          Canyon entrance via Salix &middot; 34&times;</div>
        <div class="phs-era">2025&ndash;now</div>
      </div>
    </div>
  </div>
  <div class="places-home"> ... Boston (chart-places-home-bos) ... </div>
</div>
```
- **`.places-homes`**: `display:flex; gap:16px; margin-top:16px;` (matches the card grid gap). On
  `max-width:640px` -> `flex-direction:column`. The whole block sits in the 1100px content column
  (same as the now-column-aligned hero).
- **`.places-home`** (each card, EQUAL): `flex:1 1 0; min-width:0;` glass card reusing the dashboard
  card look -- `background:var(--bg-glass); border:1px solid var(--border); border-radius:16px;
  overflow:hidden;` (theme-aware, like every other `.card`). No hover-lift, no arrow.
- **`.places-home-map`** (the heatmap thumbnail): `display:block; width:100%; height:200px;`
  (mobile `height:170px`). **Theme-aware** (revised post-ship per athlete review — was originally
  dark-committed in both themes; a dark map inset inside a light card read as broken): `:root.light`
  overrides the ground to a light radial gradient (`#eef1f4`/`#e9edf2`/`#e2e7ed`); dark stays the
  original `#101725`/`#0d1117`/`#05070a`. The route glow uses the **fixed sport hexes** in both
  themes (bucket -> teal `#2dd4bf`, amber `#f59e0b`, violet `#a78bfa`, green `#4ade80`, slate
  `#8b949e` — no CSS-var reads) but the JS reads `document.documentElement.classList.contains
  ('light')` at draw time to pick the composite mode: `'lighter'` (additive glow) on the dark
  ground, `'multiply'` (ink-on-paper) on the light ground — additive 'lighter' math clips straight
  to white and the routes vanish otherwise. A `MutationObserver` on the `<html>` `.light` class
  redraws both canvases on toggle (same pattern as the passport thumbnails).
- **`.places-home-body`**: `padding:14px 16px 16px;`.
  - **`.places-home-name`**: Geist, `font-size:15px; font-weight:600; color:var(--text-primary);
    margin-bottom:8px;` -- `San Diego` / `Boston`.
  - **`.places-home-stats`**: the 3-line mono block, `font-family:'Geist Mono',...; font-size:12.5px;
    color:var(--text-secondary); display:flex; flex-direction:column; gap:4px;
    font-variant-numeric:tabular-nums;`.
    - `.phs-mi b`: `color:var(--text-primary); font-weight:600;` (the number pops; unit slate).
    - `.phs-seg`: the segment line. `.phs-ovl` = a small-caps overline BEFORE the value, IDENTICAL on
      both cards (`display:block; font-size:9.5px; letter-spacing:.14em; text-transform:uppercase;
      color:var(--text-tertiary); margin-bottom:2px;`). The value + `N&times;` follow. Long segment
      names must not overflow: `.phs-seg{ overflow-wrap:anywhere; }` (or clamp to 2 lines with
      ellipsis) -- verify no clip at card width.
    - `.phs-era`: `color:var(--text-tertiary);` -- the era label.
- **Equal treatment:** both cards identical size/height/type scale/overline wording; the only
  differences are the data values and the thumbnail geometry. Do NOT relabel the segment overline by
  sport (SD's winner is MTB, Boston's is Run -- keep the neutral `Most-repeated segment` on both).

### Thumbnail renderer (per canvas)
A stripped static draw (no pan/zoom/labels/controls) -- port only the hero's projection + glow loop:
- On boot per canvas: DPR-cap 2; `S0 = min(W/fr.ww, H/fr.wh)`; project each track point
  `x = W/2 + (u-0.5)*fr.ww*S0`, `y = H/2 + (v-0.5)*fr.wh*S0` (centered letterbox, camera fixed at
  s=1, fx=fy=0.5 -- the metro already fills the frame via its own `fr`). Or equivalently precompute
  u/v already in-frame and scale to the canvas; either matches the hero.
- `lineJoin/lineCap='round'`, `lineWidth = max(0.8, 1.0)`, additive glow, per-track alpha
  `0.34 + 0.12*deterministic_jitter` (reuse the hero's `(i*0.6180339887)%1` jitter). Sport color by
  bucket (fixed dark hexes above). No graticule needed (thumbnail); optional very-faint one is fine.
- Draw once on `ResizeObserver` (cards start in a hidden tab -> observe each `.places-home-map` so
  first layout triggers the draw, same reasoning as the hero). No theme hook (dark-committed).
- Respect `prefers-reduced-motion` only insofar as there is no animation to begin with (static draw).

### Verify vs recipe (developer asserts / QA checks)
- Two equal cards render below the hero, side-by-side on desktop, stacked on mobile.
- Thumbnails: each shows a dense, recognizable metro heatmap (SD wider coastal sprawl; Boston
  tighter) as a DARK inset in BOTH light and dark page themes.
- Stat lines exact today: SD `782 mi` / `Most-repeated segment` / `Canyon entrance via Salix &middot; 34&times;`
  / `2025&ndash;now`; Boston `530 mi` / `Cataldo East &middot; 20&times;` / `2024&ndash;2025`.
- Names computed live; build print `[places] homes:` shows sd_mi=782 bos_mi=530 and the two segment
  winners; no drift NOTE today.
- Streams loaded once (no second 344-file parse; hero build line unchanged tracks=324 pts=22045).
- Long segment names don't clip/overflow the card; overline wording identical on both cards; no arrow.
- Units policy still 0 (`min/km`,`km/h`,`kph`,`°C`); ASCII-only in Python prints.

---

## Places — Passport (Pass C · Module 3) + Peaks (Pass C · Module 4)

> **FOLLOW-UP (2026-07 · shareable links).** Every stamp/chip/peak's `fly()` handler now also
> calls `window.placesLinkActivity(id)` immediately after `placesFlyTo(fly)`, writing
> `#places?a=<activityId>` (full contract under "Places — Build-Ready Spec" above). Each `PC`
> entry gains an `id` field — the same Strava activity id already fetched for `_load_trip_geo`
> — alongside its existing `fly` box; the passport and peaks scripts each merge their entries
> into one shared `window.placesFlyTargets` lookup so a link resolves regardless of which
> script published it.

Pass C of the Places plan. **Design = Opus spec-extension** (the single Fable dispatch was
spent on the Pass A hero). Two builders — `chart_places_passport(rows)` (filmstrip of trip
stamps) and `chart_places_peaks(rows)` (a restrained record book) — sit BELOW the two-homes
cards inside `#view-places`, in normal `.card` flow, both theme-aware. Design source:
`mocks/places-passport-mock.html` — **port its structure/CSS/JS; this spec enumerates
the deltas for real data.** Both return one self-contained raw HTML string (the `chart_calendar()`
precedent). All numbers below come from the Pass-C Analyze recipe — implement, do not re-derive.

Tone (pre-spec §1, D2/D3): neutral keepsake, weighted by meaning not volume. A 3-day summit sits
beside a single morning run. Restraint over completeness.

### Analyze recipe (pinned — the analytical heart)
- **Trip clustering by time-gap-away-from-home** (Wrinkle A). Take every activity whose
  `start_latlng` falls OUTSIDE both home boxes (`_SD_BOX`/`_BOS_BOX`), sort by
  `start_date_local`, and split into clusters wherever the day-gap to the previous away activity
  `> 5 days`. Geography is ignored inside a cluster (the Pacific-NW trip roams Seattle→Vancouver
  ~180 mi and MUST stay one trip). Today: **11 clusters → 7 featured trips + 4 brief stops.**
- **Featured vs brief:** a cluster is a **featured stamp** if it matches a curated trip (below);
  a single-day/single-activity cluster with no curated match is a **brief-stop chip**. An
  UNMATCHED multi-day cluster degrades gracefully to an auto-featured stamp (first-activity title
  as caption, no region/badge) so a future trip renders without a code change — nothing dropped.
- **Curated trip metadata is editorial copy, hardcoded** (region name, caption, badge) exactly as
  the hero's key-trip detail lines are — matched to a live cluster by a **unique title substring**
  `sig` (NOT a geo box: the two Michigan trips overlap geographically). `sig` also selects the
  **signature activity** whose GPS drives the thumbnail. Curated list, in filmstrip order:

  | # | `sig` substr | Region overline | Caption | Badge |
  |---|---|---|---|---|
  | 0 | `Whitney` | `Sierra Nevada · CA` | `Mt. Whitney from Whitney Portal & JMT` | `hi` `Highest point · 14,507 ft` |
  | 1 | `Maine Hut` | `Western Maine` | `Maine Hut Trail — Days 1–3` | `east` `Easternmost · 70.2°W` |
  | 2 | `Stanley Park` | `Seattle → Vancouver` | `Vancouver — Stanley Park` | `north` `Northernmost · 49.3°N` |
  | 3 | `Snow Snake` | `Northern Michigan` | `Snow Snake` | — |
  | 4 | `Muggy` | `Mid-Michigan` | `Muggy in Michigan` | — |
  | 5 | `Jay Peak` | `Jay Peak · VT` | `Jay Peak Spring Riding` | — |
  | 6 | `Whaleback` | `Upper Valley · VT/NH` | `Whaleback & Hanover holiday` | — |

  - **Date span** and **sport tags** are computed LIVE from the cluster (`run ×3`, `nordic ski ×3`,
    `snowboard · alpine ski`, …). Dates format `Mon d–d · YYYY` (or cross-month `Mon d – Mon d · YYYY`).
  - **Badge FACTS are the pinned superlatives, not re-derived** — northernmost is **Vancouver
    49.3°N**, NOT Maine (the mock's `Northernmost · 45.2°N` on Maine is FACTUALLY WRONG — Maine gets
    `Easternmost · 70.2°W` instead). Badge classes: `hi` (red `#f87171`), `north` (blue `--accent`),
    `east` (green `#4ade80`).
- **Signature-activity geometry** (thumbnail): read that ONE activity's stream, RDP-decimate
  (eps 0.0001) + cap 120 points, emit three parallel arrays — `path` (u/v fit to the activity's
  OWN cos-lat bbox, centered/letterboxed into 0..1), `grade` (per-vertex `grade_pct/12` clamped to
  ±1 → descent/flat/climb color), `elev` (per-vertex `altitude_m` normalized 0..1 for the profile).
  Only ~11 distinct stream files are read (7 signatures + peaks, deduped) — NOT all 344.
- **Brief stops** (4 today): `The worst timing choice · Jun 2025` · `Baldface Circle Trail · Jun 2025`
  · `Omni Mt. Washington · Jul 2025` · `Mt San Jacinto from Marion Trailhead · Aug 2025`. Chip text =
  live title + `Mon YYYY`; each chip flies the hero to its activity box on click.
- **Header meta:** `<featured> trips · <states> states & <provinces> provinces`, all live: trips =
  featured count; states/provinces from `_STATE_BOXES` over ALL away-activity start points. Today
  **7 trips · 7 states & 1 province**.

### Peaks record book (Module 4) — pinned 6 rows
Genuinely singular moments; **catches home-adjacent giants trip-clustering misses (Wrinkle B —
San Jacinto sits just north of the SD box as a same-day out-and-back)**. Each row: big mono value,
slate overline, activity title, a tiny altitude-profile sparkline (reuse the passport's `elev`
loader), lat/lng in mono, click → `placesFlyTo(box)`.

| Overline | Value | Title | `sig`/id |
|---|---|---|---|
| `HIGHEST POINT` | `14,507 ft` | Mt. Whitney via Whitney Portal & JMT | `Mt. Whitney` |
| `NORTHERNMOST` | `49.3°N` | Stanley Park, Vancouver | `Stanley Park Bike` |
| `HOME-ADJACENT GIANT` | `10,800 ft` | Mt. San Jacinto from Marion Trailhead | `San Jacinto` |
| `EASTERNMOST` | `70.2°W` | Maine Hut Trail — Day 3 | `Maine Hut Trail Day 3` |
| `FIRST IN SAN DIEGO` | `Apr 2025` | (live: earliest SD-box activity title — `Time zone shakeout`) | earliest `g?` SD act |
| `LONGEST SINGLE CLIMB` | `6,752 ft` | Mt. Whitney via Whitney Portal & JMT | `Mt. Whitney` |

- Whitney legitimately holds two records (highest + longest climb); place them non-adjacent (rows
  1 & 6). Values/titles are hardcoded editorial copy EXCEPT `FIRST IN SAN DIEGO`, whose title is the
  live earliest-SD-activity name (`Time zone shakeout` today) — the "move," stated neutrally.
- lat/lng shown from each activity's `start_latlng` (`{lat:.2f}°N  {lng:.2f}°W`).

### Injected-JSON XSS rule (IMPORTANT — same as Pass B)
The geometry payload (const `PC`) carries **only numeric fields** keyed by activity id:
`{ "<aid>": {"path":[u,v,…], "grade":[…], "elev":[…]}, … }` + a parallel `fly` box per stamp/peak.
`json.dumps(separators=(",",":"))`, compact. **Every display string** (region, caption, dates,
tags, badge text, brief-stop titles, peak titles/coords) is rendered SERVER-SIDE into the card
HTML and `_html_escape`d there — NEVER spliced into the `<script>` (the athlete's activity TITLES
are third-party; `json.dumps` does not escape `<`/`/`). Each stamp/peak/chip element carries
`data-stamp="<aid>"` (geometry lookup) and `data-fly='{"lat0":…}'` OR the JS reads `fly` from `PC`
by id. Titles may contain emoji (`Snow Snake 🐍`) — fine in HTML; Python `print()` must use `_ascii()`.

### Markup / builders
- **`chart_places_passport(rows)`** → `<section>`-less raw HTML: port the mock's `.wrap/.head/
  .stripwrap/.strip/.stamp/.thumb/.body/.brief/.chips` structure and CSS **verbatim** (already
  theme-aware via `prefers-color-scheme` + `:root[data-theme]`), restyled onto dashboard tokens
  where the mock used its own `--run/--mtb/...` (map to `--running/--mtb/--elevation/--hike`). Drop
  the mock's `.foot` "design mock" note. Stamp thumbnails are **theme-aware** (dark ground
  `#0a0e16` in dark, light `#e9edf2` in light; canvas re-tints node/glow/graticule per theme and
  redraws via a `MutationObserver` on the `<html>` `.light` class). Each `.stamp` is a
  `<button>`/`article[tabindex=0]` with `data-stamp`/`data-fly`; hover reveals `↗ view on map`;
  click → `window.placesFlyTo(fly)`. Featured stamps in curated order; brief stops as `.chip`s.
- **`chart_places_peaks(rows)`** → raw HTML: a `.places-peaks` list of 6 `.peak-row`s (no mock —
  reuse the passport's thumbnail canvas code for the altitude sparkline only, drawn violet
  `--elevation`, no route). Each row: `.peak-val` (big Geist Mono), `.peak-overline` (slate
  small-caps), `.peak-title`, `<canvas class="peak-spark" data-stamp>`, `.peak-coord` (mono).
  Row is a button → `placesFlyTo(fly)`.
- **Thumbnail JS** (ported `drawThumb`): swap the seeded squiggle for the injected `path`; color
  each segment `i` by `gradeColor(grade[i])` — a **cool/warm diverging lerp**: descent blue
  `#58a6ff` (the dashboard's `--accent`) / flat slate `#8b949e` / climb amber `#f59e0b` (the MTB
  sport token). Colorblind-safe; replaces the mock's red/green pair (revised post-ship per athlete
  review — red/green is the classic colorblind-unfriendly diverging scheme). Draw the violet `elev`
  profile along the bottom. DPR-cap 2, `ResizeObserver` per canvas (cards start in a hidden tab).
  Respect `prefers-reduced-motion` (the hover-lift only; no line-drawing animation — pre-spec §7).
- **Wiring (`page.py`):** thread `places_passport` + `places_peaks` through
  `_build_main_charts`→`build_page`→`_assemble_html` exactly as `places_homes` is; render inside
  `#view-places` AFTER homes: `{places_hero}{places_homes}{places_passport}{places_peaks}`. Build
  them right after homes with `print("  places passport...")` / `print("  places peaks...")`.
- **No new palette hex** (blue/slate/amber/violet are existing tokens). **No new data files.**

### Build prints (ASCII only)
`[places] passport: featured=7 brief=4 states=7 provinces=1 geom_aids=11 json_kb=~22`
`[places] peaks: rows=6 highest=14507ft`
Soft `[places] NOTE:` if featured count drifts from 7 or a curated `sig` matches zero clusters
(a retitle/refetch surfaced) — never a hard assert (deploy must not break on data growth).

### Verify vs recipe (developer asserts / QA checks)
- 7 featured stamps in curated order; Whitney first with `Highest point · 14,507 ft`; Maine
  `Easternmost · 70.2°W` (NOT northernmost); Vancouver `Northernmost · 49.3°N`. 4 brief chips.
- Each thumbnail: a recognizable route colored by grade (Whitney climbs hard/amber to its peak;
  Michigan stays flat/slate) with a violet elevation profile; theme-aware (dark ground/dark mode,
  light ground/light mode — see "Places passport: theme-aware stamp thumbnails").
- Peaks: 6 rows, values `14,507 ft / 49.3°N / 10,800 ft / 70.2°W / Apr 2025 / 6,752 ft`; San
  Jacinto present (Wrinkle B); `FIRST IN SAN DIEGO` title is live (`Time zone shakeout`).
- Click a stamp/peak/chip → hero flies to that box (View buttons deactivate); `placesFlyTo` exists.
- Click a stamp/peak → URL becomes `#places?a=<activityId>`; reloading that URL restores the same
  zoomed activity; switching to another tab and back to Places preserves it (no bare `#places`).
- Geometry JSON carries no display strings (grep the `<script>` for a segment/activity title →
  none); titles are HTML-escaped server-side; emoji renders.
- Both themes legible; mobile: filmstrip scroll-snaps + drag-scrolls, peaks stack; no h-scroll on body.
- ASCII-only Python prints; units policy 0.

---

## Places — Basemap (Glow vector layer)

> **SUPERSEDED (2026-07).** Replaced by the MapLibre tiled basemap (see the update banner
> under "Places — Build-Ready Spec"). The Street/Terrain modes now provide the geographic
> grounding; Glow mode is a tile-free transparent style over the radial-gradient ground with
> no vector coastline. `basemap.json` + `_load_basemap()` are no longer used by the hero.
> The section below is retained for history.

Follow-on to the shipped Places build (`Plans/strava-data/places-basemap-plan.md`). Adds a faint
geographic layer under the hero's route glow so the section reads as a real map
(especially in light mode, where the glow alone was near-invisible on white).
Retires the mock's concentric-ring terrain placeholder.

### Architecture (keeps Option A intact)
- **Vector, drawn on the SAME canvas in the SAME projection** — NOT tiles, NOT a
  reprojected Mercator layer. Coastline / state-province / lake polylines are
  projected through the existing `projX`/`projY` (equirectangular + `COSLAT`), so
  they register with the routes exactly at every zoom, with no runtime network.
- **Asset:** `strava-data/assets/basemap.json` (checked in, ~80 KB), regenerated
  by `strava-data/tools/gen_basemap.py` from Natural Earth 50m coastline / admin-1
  lines / lakes — clipped to the map extent (lat 24..55, lng -135..-60), RDP-
  simplified, rounded to 3 decimals, small lakes dropped (bbox diag < 0.6°). Pure
  numeric `[lng,lat,...]` polylines → safe to inline into `<script>`.
- **Build:** `chart_places_hero` reads the asset via `_load_basemap()` (missing →
  soft WARNING, hero still works) and inlines it as `__BM_JSON__`; JS converts to
  Float32 u/v once at boot (same frame as routes). Console: `[places] basemap: json_kb=~81`.

### Render (`drawBasemap()`, called top of `draw()` under the glow)
- Order: `clearRect → drawGraticule → drawBasemap → glow tracks → labels`.
- Slate (`--text-secondary`), **faint** (D3): coast/lakes alpha 0.16 dark / 0.26
  light, admin 0.085 dark / 0.15 light; line widths 0.9/0.8/0.7. Re-read on every
  `retint()` so both themes resolve. Drawn in BOTH Glow and Terrain modes.
- **No new palette hex** (slate is a token); no new runtime dependency.

## Places — Terrain (shaded relief)

> **SUPERSEDED (2026-07).** Terrain is now a MapLibre **MapTiler `outdoor-v2`** tiled style
> (real relief/hillshade at every zoom), selected by the Terrain button. The inlined
> `hillshade.png` + `_load_hillshade()` are no longer used. Retained below for history.

Terrain-mode shaded relief (pre-spec §6.1 "mountains show through"), layered
UNDER the vector basemap. Real elevation, not the retired ring placeholder.

- **Asset:** `strava-data/assets/hillshade.png` (checked in, ~31 KB), an **LA
  (grayscale+alpha) PNG** covering a FIXED lat/lng box (lat 24..55, lng -135..-60)
  regenerated by `strava-data/tools/gen_hillshade.py`: fetches AWS Terrarium
  elevation tiles (Web Mercator), **resamples onto the hero's equirectangular
  frame** (so it registers with no runtime reprojection), hillshades (az 315 /
  alt 45 / z-factor 1.6), and encodes **alpha ∝ slope** so flats/ocean stay
  transparent and only rugged terrain paints. Posterized (lum 16 / alpha 8
  levels) → ~31 KB. Needs Pillow (`uv run --with pillow`); NOT a deploy dep —
  the build only inlines the finished PNG as a base64 data URI (`__HILLSHADE_URI__`).
- **Render (`drawHillshade()`, top of `draw()`, Terrain only):** an `Image` from
  the data URI, drawn stretched to the fixed box via `projX/projY` (equirectangular
  → exact registration). Dark ground → `source-over` (light ridges show), light
  ground → `multiply` (shadows darken the paper; highlights would wash out on
  white); globalAlpha 0.85 dark / 0.9 light, `save`/`restore` around it. Missing
  asset → `hsReady` stays false, Terrain falls back to the vector basemap.
- Console: `[places] basemap: json_kb=~81 hillshade_kb=~42` (inlined base64).

### Verify
- Coastline/borders/Great Lakes register with the home labels (San Diego on the
  SoCal coast, Boston on the MA coast, Vancouver PNW) at All zoom and after fly-to.
- Faint in both themes; light mode now legibly geographic; routes stay the subject.
- Terrain mode shows real relief (Sierra at the Whitney label, Rockies, Cascades
  near Vancouver; flat east); concentric rings gone.
- No JS errors on terrain toggle / fly / theme / Trips lens; body h-overflow 0.

---

## Places — Hero zoom/pan controls (explicit UI)

> **UPDATED (2026-07).** The `+`/`−`/reset cluster and View buttons remain, but they now
> drive the **MapLibre camera** (`map.zoomIn/zoomOut`, reset = the "All" View →
> `map.fitBounds(allBounds)`). Pan/scroll-zoom/pinch/double-click/shift-drag box-zoom are
> **MapLibre-native** with `cooperativeGestures` (ctrl+scroll / two-finger; the page still
> scrolls). The bespoke gesture + marquee code below is **retired**.

Follow-on to the shipped Places build. The hero previously relied entirely on implicit
gestures (drag, Ctrl/Cmd+scroll, pinch, dblclick) with no visible affordance — adds an
explicit `+`/`−`/reset control cluster on the map itself.

### Markup + placement
- New `.places-zoom` group inside `.places-chrome`: a `.places-zoom-pair` (two stacked
  `+`/`−` buttons in one glass pill, styled like `.places-seg`) plus a separate circular
  reset button reusing the `.places-fs` (fullscreen button) class for visual consistency.
- **Desktop:** bottom-right (`right:clamp(22px,4vw,52px); bottom:clamp(96px,17vh,140px)`)
  — clear of the mid-height Boston label and above the footer.
- **Mobile (<=640px):** top-right (`top:clamp(22px,4vh,44px); right:clamp(14px,4vw,52px)`)
  — the corner vacated once `.places-controls` (View/Map) relocates to the bottom.

### Behavior
- `+`/`−` zoom at the CURRENT CAMERA CENTER (not cursor position — there is no cursor for
  a button click), via the existing `tweenTo`/`clampS` machinery (620ms ease, snaps under
  `prefers-reduced-motion`), factor 1.5 / (1/1.5) per click.
- Both buttons `disabled` at the zoom bounds (`cur.s>=400` / `cur.s<=0.65`), updated every
  `draw()` call via `updateZoomButtons()`.
- **Reset** button triggers a `.click()` on the existing `[data-frame="all"]` View button
  rather than duplicating its target/lens/button-sync logic — single source of truth for
  "default view."
- No new palette hex; reuses `.places-fs`/`.places-seg` glass styling.

### Bonus fix bundled in (pre-existing, found via this QA pass — see mobile section)
The mobile `.places-controls` (View/Map rows) collided with `.places-foot` (legend+stat)
on every phone size tested; on the narrowest (<=360px) it also nudged the on-canvas home
labels. Verified via canvas pixel-scan (labels are drawn, not DOM, so a visual check is
required) against the OLD 96px baseline: the footer/legend collision existed on ALL sizes
tested (390/430/360/320 CSS px) and the label collision already existed on the two
narrowest. Fixed footer/legend fully (shrunk mobile `.places-foot` padding/gap, bumped the
controls offset to 116px) on all sizes tested; the deeper narrow-phone (<=360px) label
crowding is improved but not fully eliminated — flagged as a follow-up, not bundled into
this pass (would need moving the fullscreen toggle out of `.places-controls` or a broader
mobile chrome rework).

### Verify
- Zoom in/out via buttons changes `cur.s`; buttons disable at bounds; reset returns to the
  exact `{s:1,fx:0.5,fy:0.5}` default and re-syncs the View button states.
- Desktop: zoom cluster clear of Boston label and footer in both themes.
- Mobile: zoom cluster clear of the caption and the (relocated) View/Map controls; the
  View/Map-vs-footer collision is gone on 320-430px widths (canvas pixel-scan verified).

---

## Places — Hero selection zoom (desktop, Shift+drag)

> **SUPERSEDED (2026-07).** Shift+drag box-zoom is now provided by **MapLibre's built-in
> `BoxZoom` handler** (same gesture), so the bespoke marquee implementation below and the
> `#places-selrect` element are **removed**. Retained for history.

Follow-on to the zoom-controls pass. A "box zoom" affordance for desktop: hold Shift and
drag a rectangle on the hero; releasing fits the camera to it. Standard mapping-tool
pattern (matches e.g. Leaflet's `L.Map.BoxZoom`), chosen over a mode-toggle button to stay
consistent with the hero's existing modifier-key gesture language (Ctrl/Cmd+scroll to zoom).

### Behavior
- `pointerdown` with `e.pointerType==='mouse' && e.shiftKey` starts a selection instead of
  a pan (returns before `mouseDrag` is set, so the two never both fire).
- A `.places-selrect` overlay div (dashed `--accent` border, 15%-tint fill) tracks the drag
  in canvas-local px; hidden by default, `display:none !important` under `(hover:none)` so
  it can never appear on touch (the whole feature is mouse-only by design — no touch path
  sets `e.shiftKey`).
- On release: screen-rect corners convert to world u/v via the inverse of `projX`/`projY`,
  then `fitBox(u0,u1,v0,v1)` + `tweenTo` (same call the View buttons use — 620ms ease,
  snaps under `prefers-reduced-motion`). Drags under 8x8px are ignored (accidental
  Shift-click guard).
- Deactivates all `[data-frame]` buttons (a one-off custom framing, like the passport/
  peaks fly-to boxes) and calls `syncHashState()` — since no named view is active, this
  clears any stale `v=` from the hash; the custom camera position itself is NOT persisted
  across reload (consistent with fly-to boxes, which are also one-off, not named states).
- Crosshair cursor while Shift is held (`#places-hero.shift-down canvas`), tracked via
  global `keydown`/`keyup`/`blur` listeners so it works regardless of pointer position when
  the key goes down, and never gets stuck after an alt-tab.

### Verify
- Tiny Shift-drag (<8px): no camera change, no button-state change (accidental-click guard).
- Real Shift-drag: rectangle visible + tracks the drag; hides on release; camera changes to
  fit the selection; View buttons deactivate; canvas pixels differ before/after.
- A normal (non-Shift) drag immediately after still pans, unaffected (regression check).
- Both themes legible; no JS errors.

---

## Weekly Volume rangeslider light-mode fix + retint ordering (2026-07-15)

R3 (Core Dashboard Refinements, 2026-06-11) specified retinting the Weekly Volume
rangeslider's bg/border via a `Plotly.relayout` call in `applyChartTheme()`. That
JS shipped correctly, but once charts started rendering lazily (commit `8f75a68`,
"Fix nav lag: lazy-render charts and paint the right section first"), the relayout
raced the chart's own un-awaited `Plotly.newPlot()` and no longer reliably
repainted the already-drawn `<rect class="rangeslider-bg">` — it always loses,
since the Volume tab (unlike Overview) is only ever lazily rendered.

- **Superseded R3 with a CSS override** in `template.py`'s `CSS` f-string, next to
  the existing rangeslider cursor rules: `.rangeslider-bg { fill:
  var(--bg-glass) !important; fill-opacity: 1 !important; stroke:
  var(--border-subtle) !important; stroke-opacity: 1 !important; }`. Immune to
  Plotly relayout timing since the browser cascade applies it regardless of
  when/how the element is drawn. `fill-opacity`/`stroke-opacity` are forced to 1
  because Plotly bakes an rgba's alpha as a separate opacity attribute alongside
  an opaque `fill`/`stroke`, which would otherwise multiply against the CSS
  vars' own alpha. The `applyChartTheme()` branch that set
  `xaxis.rangeslider.bgcolor`/`bordercolor` is removed as dead code now that CSS
  owns this unconditionally.
- **Implemented R6's retint-after-resize ordering**, which the shipped code
  never actually did despite being spec'd: `activateView()` now calls
  `window.__applyChartTheme()` after the `Plotly.Plots.resize()` loop (inside
  the same `requestAnimationFrame` callback) instead of before it, with a
  fallback direct call when `window.Plotly` never loaded so the non-Plotly
  Places-hero canvas retint isn't lost in that edge case. This is the likely
  root cause of the rangeslider race and may also affect other lazily-rendered,
  JS-retinted elements (e.g. chart subtitles on a tab shown for the first time).

---

## Annotation pill backgrounds light-mode fix (2026-07-18)

Same root cause and same fix shape as the Weekly Volume rangeslider fix above:
applyChartTheme()'s Plotly.relayout retint of annotation bgcolor couldn't
reliably win against Plotly's own lazy-render redraw once charts started
rendering lazily. Affected every dark "pill" annotation baked via
charts_exploratory.py's `X_ANN_BG`, charts_production.py's
`chart_run_hr_vs_temp`-local `DARK_PILL`, and rollups_cards.py's reuse of
`X_ANN_BG` (e.g. the Exploratory tab's R-value and "circle = run / diamond =
MTB" symbol-key pills) — they stayed dark grey in light theme.

- Superseded the JS bgcolor retint with a CSS rule scoped to
  `.annotation .bg[style*='fill-opacity: 0.65;']` (Plotly's generic
  per-annotation background-rect class, qualified by the exact baked
  fill-opacity so annotations with no visible pill, e.g. V8's risk-band edge
  labels, are unaffected). Removed the now-dead `DARK_PILL`/`pillBg` JS
  declarations and the relayout branch that used them.
- Note for later: `X_ANN_BG` (charts_exploratory.py), the local `DARK_PILL`
  (charts_production.py's `chart_run_hr_vs_temp`), and the CSS var literal
  (template.py, now removed from JS but still baked at the two `--ann-pill-bg`
  definitions) are three independent hardcoded `rgba(13,17,23,0.65)` strings
  that happen to stay in sync by convention only. Worth a shared constant
  someday; out of scope for this fix.
