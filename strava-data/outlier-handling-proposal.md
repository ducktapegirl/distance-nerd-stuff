# Proposal: Statistically Rigorous Outlier Handling for the Strava Dashboard

> Status: **draft proposal for review** — not yet approved or implemented.

## Why this exists

The dashboard owner believes many plots are "skewed by outliers" and wants a
principled, statistically defensible way to clean up the story of each chart
without cherry-picking.

**Key empirical finding (profiling `data/activities.csv`, n=339):** the *average*
fields are already clean — there are essentially no absurd sensor glitches
(max avg run pace 19:16/mi, max avg HR 171 bpm, max cadence 105 spm — all
physiologically real). The perceived skew comes from three things, not bad data:

1. **Category contamination** — walks/hikes logged as `Run`/`TrailRun` stretch
   pace to ~19 min/mi (median 9:03); GPS-test/treadmill activities as short as
   0.05 mi pollute distributions.
2. **Genuine extremes** — a few real long/hard efforts (suffer score median 54,
   max 269) and a real walk-pace tail.
3. **Framing** — fixed histogram bin ranges and min/max-driven axis scaling let a
   single legitimate extreme stretch an axis or empty out the bins that matter.

So the rigorous move is **robust estimators + standardized minimum-activity gating
+ smarter axis/bin framing**, with deletion reserved only for truly impossible
values. Nothing real gets silently hidden.

**Chosen direction:**
- **Robustify, don't delete** genuine extremes (Theil–Sen regression, median/MAD scaling).
- **Disclose** via ghost (faded/hollow) points plus a small "n excluded / method" note.
- **Scope:** a validity gate applied everywhere (cheap, protects aggregates + future
  data), then upgrade the handful of most outlier-skewed charts.

## The statistical framework

Three layers, each with a single declared, uniform rule — this is what makes it
rigorous rather than ad-hoc. Each chart uses the layers appropriate to it.

### Layer 1 — Validity gate (data cleaning, applied everywhere)

Remove only *physiologically/physically impossible* values — these are errors, not
outliers, so removing them is uncontroversial. Bounds are deliberately wide (well
outside observed p01/p99), so they only ever catch true sensor failures:

| Field          | Drop if outside     | Observed range |
|----------------|---------------------|----------------|
| avg HR         | 60–220 bpm          | 85–171         |
| max HR         | 90–230 bpm          | 120–183        |
| avg run pace   | 3:30–25:00 /mi      | 5:26–19:16     |
| avg MTB speed  | 1–40 mph            | 4.4–10.6       |
| max speed      | < 60 mph            | up to 32 (real)|
| run cadence    | 50–130 spm          | 68–105         |
| temp           | −20–130 °F          | 6–91           |
| elevation gain | ≥ 0; ≤ 1500 ft/mi   | sane           |

This protects the **aggregates** (weekly volume/elevation, calendar, ACWR,
suffer-load) — where one glitch inflates a whole week/day — without trimming a real
big week.

### Layer 2 — Category/eligibility gate (standardize what already exists)

Charts today use scattered, inconsistent `distance_km < 1.5` skips and sport
filters. Standardize named predicates so every running chart treats walks and
GPS-test blips identically:

- **Min running activity:** distance ≥ ~1.0 mi *and* duration ≥ a few minutes
  (kills 0.05 mi test blips). Threshold tunable; document it.
- **Optional "is this a run" guard:** very slow paces (> ~16 min/mi) are walks;
  surface them as a separate ghosted series rather than mixing them into the run
  pace distribution/regression. Off by default if undesired.

### Layer 3 — Statistical outlier handling (chart-type specific)

Genuine extremes that survive Layers 1–2 are **kept** but prevented from distorting
estimates/framing:

- **Scatter + regression** (pace↔HR, HR↔temp, cadence↔pace, segment scatters):
  switch the trend line from OLS to **Theil–Sen** (median of pairwise slopes) —
  resistant to extremes, deletes nothing. Show every point; render statistically
  extreme ones as **hollow/faded "ghost" markers**. Annotate "fit: Theil–Sen;
  n ghosted = k".
- **Univariate fences:** upgrade the existing `_remove_outliers` (Tukey IQR) to also
  compute a **modified z-score (median ± k·MAD, Iglewicz–Hoaglin, threshold 3.5)**.
  MAD is more robust than IQR at these sample sizes. Use the flag to *style* points
  (ghost), not delete them.
- **Distributions / histograms / violins** (cardiac HR, metronome pace, heat bands):
  don't delete; set **robust axis/bin ranges from percentiles** (p1–p99) so the bulk
  fills the frame, plus a "+k beyond axis" tail annotation.
- **PCA / clustering** (archetypes): replace mean/SD `standardize()` with a **robust
  scale (median/MAD)** so one ultra doesn't dominate the principal axes.
- **Aggregates / time-series** (volume, elevation, calendar, ACWR, pace/HR over
  time): rely on Layer 1 only — real big weeks stay. Optionally ghost
  Layer-1-failing points on the two per-activity time series.

## Guardrails that keep this honest

1. **One declared rule per layer**, applied uniformly — never per-point judgment.
2. **Symmetric** — fences trim both tails; never only the inconvenient one.
3. **Always disclose n** affected, on-chart, in display units.
4. **Default to keeping data** (ghost) over deleting; deletion only at Layer 1.
5. **Document** every threshold in the spec so it's reproducible.

## What would change in code

All work lives in `strava-data/dashboard/`; build via
`uv run python strava-data/build_dashboard.py`.

1. **`dashboard/data.py`** — `valid_activity(row)` (Layer 1) + `is_eligible_run(row,
   min_mi=1.0, ...)` (Layer 2), replacing scattered inline `km < 1.5` checks. Apply
   `valid_activity` once after load so *all* charts inherit it.
2. **`dashboard/geometry_stats.py`** — `theil_sen()` +
   `_add_robust_regression_line()`; `modified_zscore_flags()` (median/MAD);
   `robust_range()` percentile helper; `robust_standardize()`; refactor
   `_remove_outliers` to `partition_outliers()` returning `(inliers, ghosts)`.
3. **`charts_production.py`** — Theil–Sen + ghost markers on the regression scatters
   (`chart_run_pace_vs_hr`, `chart_run_hr_vs_temp`, the 6 `*_seg_*` via
   `_scatter_two_axis`); use the shared eligibility predicate.
4. **`charts_exploratory.py`** — V3 cardiac & V7 metronome: robust percentile
   bin/axis ranges + tail note. V6 cadence: Theil–Sen + ghosts. V2 archetypes: robust
   standardize. V1/V4/V5/V8 likely unchanged (verify).
5. **`config.py`** — named constants for the bounds + a `GHOST_*` marker style, so no
   new hex is hardcoded and `applyChartTheme()` can retint.
6. **Captions** — `.plot-caption` notes under each upgraded chart (method + n);
   on-chart notes use `X_ANN_BG` pill + `X_SLATE` text for both themes.
7. **`dashboard-spec.md`** — new **"Appendix C — Outlier & Validity Policy"** with the
   three layers, every threshold, and which chart uses which; update any pinned
   Appendix-A values that shift.

**Reuse (don't rebuild):** `_remove_outliers`, `_add_regression_line`,
`_r2_annotations`, `_pace_ticks`, `standardize`, `ols_r_p` (geometry_stats.py);
`mf`, `sport_category`, formatters (data.py); `fig_html`, `tidy_dark`, color
constants, `applyChartTheme()`.

## How we'd verify

1. Build is clean (`build_dashboard.py`, no tracebacks); `strava.html` regenerates.
2. Print per-chart `n_total / n_ghosted / n_dropped`; confirm Layer-1 drops ≈ 0 on
   current data (proves the gate isn't trimming real efforts) and eligibility gating
   removes the expected sub-1-mi blips.
3. Visual QA (strava-qa / Preview MCP) in **light and dark**: ghosts visible but
   de-emphasized, captions legible, axes no longer stretched by one extreme, no
   overlap/clipping.
4. Units policy intact: pace min/mi, speed mph, temp °F, distance mi, elevation ft.
5. Theil–Sen slope close to OLS on already-clean charts; visibly steadier where
   extremes existed.
6. Run `/code-review` before shipping.

## Tunable choices (defaults picked; easy to revisit)

- Min running distance/duration for eligibility (default ≥ 1.0 mi).
- Whether to split walk-pace runs into their own ghost series (Layer 2 optional).
- MAD threshold (default 3.5) and percentile framing band (default p1–p99).
