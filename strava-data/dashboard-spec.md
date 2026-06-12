# Strava Dashboard — View Specs

Generated 2026-06-10 by the `/strava` multi-agent pipeline running fully autonomously
(orchestrator: Claude Fable 5). Status: **SPEC — Exploratory tab V1–V8, ready to build.**

> **2026-06-11 refinements** — six targeted updates to the CORE dashboard (calendar,
> overview, volume, elevation, pace) plus a theme-sync fix. Spec in the
> "Core Dashboard Refinements (2026-06-11)" section near the end of this file.

Pipeline provenance: strava-data-analyst (discovery + verified transform recipes) →
strava-creativity (ranked menu; 8 views selected) → strava-viz-design (this spec) →
strava-developer (build) → strava-qa (validation).

---

## Exploratory Tab — Build-Ready Spec (V1–V8)

Source of truth for all conventions: `strava-data/build_dashboard.py`. Reuse `tidy_dark(fig)`
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
  other slate, elevation violet, and accent constants already defined in build_dashboard.py.
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
- **div id:** `chart-x-mirage` · **height:** 460 · **Type:** Scatter (markers) + 2 line traces + 2 OLS lines.
- **Data:** runs n=181 with HR+temp; monthly-binned z-scored aerobic efficiency (speed/HR), 20 bins 2024-11..2026-06, per recipe (raw vs temperature-adjusted residual).
- **X axis:** month bin midpoint date — label "Month" — ticks `MMM YY`, range 2024-11..2026-06.
- **Y axis:** z-scored aerobic efficiency — label "Aerobic efficiency (z-score)" — zeroline shown.
- **Traces:** (1) individual runs: markers, teal, `opacity=0.25`, size 5, behind. (2) raw monthly mean: slate dashed line+markers. (3) temp-adjusted monthly mean: teal solid line+markers. (4) OLS on raw points: slate dashed. (5) OLS on adjusted points: teal dashed.
- **Legend:** ON, bottom: "Individual runs", "Raw (uncontrolled)", "Temperature-adjusted".
- **Annotation:** top-right paper (x=0.98,y=0.97): `Raw r=-0.183, p=0.013 -> Adjusted r=-0.063, p=0.402`.
- **Hover:** lines -> `%{x|%b %Y}<br>z = %{y:.2f}`; runs -> activity name + `z=%{y:.2f}`.
- **Edge cases:** runs missing HR or temp excluded. Months with <2 runs plot as-is; guard empty bins.
- **Verify vs recipe:** `V1_raw_r=-0.183`, `V1_raw_p=0.013`, `V1_adj_r=-0.063`, `V1_adj_p=0.402`, n=181, 20 bins.

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
- **div id:** `chart-x-heat` · **height:** 460 · **Type:** 3 Violin traces (pace) + mean-HR line on secondary y (`make_subplots` secondary_y).
- **Data:** runs n=199 by temp tercile — cool <=9.0C n=66, mid n=65, warm >=18.1C n=68
  (tercile cuts computed in °C internally; displayed in °F: 9.0C -> 48.2F, 18.1C -> 64.6F).
- **X axis:** categorical "Cool (<=48°F)", "Mid", "Warm (>=65°F)" — label "Temperature tercile".
- **Y1 (pace):** "Pace (min/mi, faster = up)" — **REVERSED** (`autorange="reversed"`),
  ticks formatted `M:SS`.
- **Y2 (HR):** "Mean HR (bpm)" — fixed range ~145..160 so the flat line reads flat.
- **Violins:** `box_visible=True`, `meanline_visible=True`, points off; cool=slate, mid=`rgba(245,158,11,0.5)`, warm=amber; opacity 0.7.
- **HR line:** 154.2 / 152.2 / 154.4, teal, markers+line, secondary y.
- **Legend:** OFF for violins; slate annotation: `teal line = mean HR (right axis)`.
- **Annotation:** bottom-center, recomputed in min/mi: `Cool 8:57 vs Warm 9:24 /mi | t=-3.24 | p=0.0017 | HR flat (t=-0.19, p=0.85)`.
- **Edge cases:** missing temp excluded; cut points fixed 9.0/18.1; ties at 18.1 -> warm.
- **Verify vs recipe:** `V4_welch_t=-3.236`, `V4_welch_p=0.00170`, HR means 154.18/152.21/154.38, n 66/65/68.

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
- Filter: runs with non-null temp AND speed -> n=199 (HR not required). pace=60/speed.
- Terciles on temp: q1=9.00, q2=18.10 (33.3/66.7 percentiles). cool = temp<=9.00 (n=66),
  warm = temp>=18.10 (n=68), mid between (n=65). Ties at boundary -> warm.
- Pinned: cool pace mean 5.565 median 5.522; warm mean 5.839 median 5.698; Welch t=-3.236
  p=0.00170. Mean HR per tercile (non-null HR within tercile): 154.18 / 152.21 / 154.38;
  HR cool-vs-warm t=-0.190 p=0.849.

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
`Running Log/index.html` (CSS 433-498, HTML 1006-1164) and `Running Log/src/visualize_log.py`
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
