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

Pass A (Foundation + Hero) of the approved Places plan (`places-plan.md`, `places-prespec.md`).
Design source: `strava-data/mocks/places-hero-mock.html` — **port its structure/CSS/JS; this spec
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

#### Map control (Glow · Terrain) + theme contract
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
