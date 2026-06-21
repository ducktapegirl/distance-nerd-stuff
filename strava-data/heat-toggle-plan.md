# Plan: Temp ↔ Apparent-Temp toggle on the heat violin chart

> Status: **planned, not yet implemented.** This is a handoff doc for running the
> `/strava` orchestrator pipeline (Design → Build → QA → Review → Ship) on this change.
>
> **Update (2026-06-21):** the 4-fixed-band conversion described in an earlier version of
> this doc has already shipped on `main` (commit `2ca0920`, "Split V4 heat violin into 4
> fixed °F bands"). `chart_x_heat` now bins on fixed 48/62/75°F edges (cool/mild/warm/hot)
> instead of percentile terciles. **Only the temp ↔ apparent-temp toggle below remains.**

## Context

The Strava dashboard recently gained two new weather fields — `apparent_temp_c`
(heat index) and `uv_index` — now backfilled into `strava-data/data/activities.csv`.
The chart **"She Pays Pace, Not Heart, for Heat"** currently visualizes pace/HR vs.
**air temperature** only (`average_temp_c`). The goal is to let a viewer toggle the
*same* chart between **air temperature** and **apparent temperature (heat index)** so
the two can be compared 1:1.

## Current state of the chart (as of `2ca0920`)

`chart_x_heat(rows)` in `strava-data/dashboard/charts_exploratory.py:370-459`:
- Filters to `_x_runs(rows)`, requires `average_speed_kmh` and `average_temp_c` present.
- Bins on **fixed °F edges 48/62/75** (converted to °C: 8.89/16.67/23.89) into 4 bands:
  Cool `<48`, Mild `48–62`, Warm `62–75`, Hot `>=75`.
- 4 `go.Violin` traces (pace, min/mi, colors: slate / `rgba(245,158,11,0.4)` / amber /
  `SLOWER` red) + 1 `go.Scatter` mean-HR line on secondary y, via
  `make_subplots(specs=[[{"secondary_y": True}]])`.
- Pace axis reversed, `M:SS` ticks via `_pace_ticks`. HR axis fixed `[145, 160]`.
- Bottom annotation: Cool-vs-Hot Welch t/p on pace + HR-flat Welch t/p.
- Returns `dict(t, p, hr_means, n_cool, n_mild, n_warm, n_hot)`.
- Wired at `page.py:220` (`v4, v4m = chart_x_heat(rows)`), stats printed at
  `page.py:221-223`, rendered at `page.py:447` (`fig_html(v4,460,"chart-x-heat")`), caption
  at `page.py:448`.
- Spec block: `dashboard-spec.md:130-144` (already describes the 4-band version).
- `SLOWER` is already covered by `applyChartTheme()` in `template.py` — no new color-theme
  work needed for the existing 4 bands.

**Locked decision carried over:** *"All available per view"* — the air-temp view uses
every run with `average_temp_c`; the apparent-temp view uses every run with
`apparent_temp_c` (coverage differs, since `apparent_temp_c` backfill coverage is lower).

## How the work should be done: the `/strava` agentic orchestrator

This should be executed through the **`/strava` orchestrator skill**
(`.claude/commands/strava.md`, `strava-data/AGENTS.md`), not by hand. The view is already
chosen and fully specified, so **Intake and Ideate can be skipped**. Stages to run:

- **Design** — dispatch `strava-data-analyst` (Job B, verification) to confirm per-band
  counts and per-view Welch stats for `apparent_temp_c` under the existing fixed edges
  (the air-temp numbers are already verified and in the spec); dispatch `strava-viz-design`
  to write the updated V4 spec block describing the toggle. Orchestrator writes it to
  `strava-data/dashboard-spec.md`. **User approves the spec.**
- **Build** — dispatch `strava-developer` to implement (details below).
- **QA** — dispatch `strava-qa` (build integrity, units policy, theme audit, toggle works
  in Preview MCP, label/clip checks). Loop back to Build on failures.
- **Review gate** — `/code-review` + `/security-review` over the diff.
- **Ship** — rebuild both `strava-data/strava.html` and `Running Log/strava.html`.

The orchestrator pauses for user approval between stages (as designed).

## Build details (for `strava-developer`)

Target: `chart_x_heat(rows)` in `strava-data/dashboard/charts_exploratory.py:370-459`.

1. **Factor out a per-metric helper.** Extract the existing body (lines 372-407, 449-450,
   457-459) into a helper that takes the metric column name (`"average_temp_c"` or
   `"apparent_temp_c"`) and returns: the 4 binned pace arrays (mi), `hr_means`, Welch
   t/p (cool vs hot), HR-flat t/p, and per-band n. Call it twice — once per metric. Keep the
   same fixed 48/62/75°F edges for both (already the literal `f_to_c` constants — reuse
   as-is, do not recompute per metric).
2. **Traces.** Build both views into one figure: each view = **4 Violin traces + 1 HR
   Scatter line = 5 traces** → 10 traces total. Air-temp view visible by default
   (`visible=True`), apparent-temp view `visible=False`. Keep all existing visual styling
   (colors, `box_visible`, `meanline_visible`, `points=False`) for both views — same colors
   reused, not new ones, so no new theme entries are needed.
3. **Shared axes for 1:1 comparison.** Compute the pace `tickvals`/`ticktext` from the
   **union** of both views' pace arrays (reuse `_pace_ticks`) so the y-axis is identical in
   both toggle states. HR axis can stay fixed `[145, 160]` unless the apparent-temp HR means
   fall outside that range (check during Design verification; widen only if needed, applying
   the same range to both views either way).
4. **Toggle UI — reuse the existing segment-filter pattern** (`.seg-filter`/`.seg-btn` in
   `page.py:404-408` + `template.py:403-424`, `filterSegs`-style JS in
   `template.py:556-568`):
   - Two buttons: **Air temp** (active default) / **Apparent temp** (heat index), placed
     above `{fig_html(v4,460,"chart-x-heat")}` at `page.py:447`.
   - JS: `Plotly.restyle(el, {visible: [...]}, [0..9])` to swap which view's 5 traces show.
   - The bottom **stat annotation** text differs per view (different Welch numbers, possibly
     different n) and can't be toggled via `restyle` — also call `Plotly.relayout` to swap
     the annotation text on click (store both precomputed strings, e.g. in a small JS object
     keyed by view, embedded inline next to the toggle markup). Band labels (x categories)
     are identical across views — no swap needed there.
5. **Stats + return dict.** Return both views' Welch stats; update the `v4m` shape and the
   `print(...)` at `page.py:221-223` to report both metrics (e.g. prefix keys with `air_`/
   `app_`, or nest per-view dicts).
6. **Caption.** Update `page.py:448` to mention the new toggle (current caption already
   correctly describes 4 bands — only needs a sentence about switching between air temp and
   heat index).

### Edge cases
- A band may be empty for one metric (e.g. Hot `>=75°F` likely has very few/zero runs under
  `apparent_temp_c` given lower overall coverage, or conversely more under apparent temp
  since heat index runs hotter than air temp). Empty violin renders nothing — acceptable;
  HR line must skip `None` band means (already handled by existing `hr_mean` helper pattern).
- Apparent-temp view will have a smaller n than air-temp view — surface both n's in the
  annotation/spec so this isn't read as 1:1 sample-equivalent, just 1:1 axis-equivalent.

## Spec update (for `strava-viz-design` / orchestrator)
Extend the **V4 — She Pays Pace, Not Heart, for Heat** block in
`strava-data/dashboard-spec.md:130-144`: document the two precomputed views, the toggle
control, shared axis limits derived from the union, and per-view Welch/n numbers (air-temp
numbers already present; add apparent-temp numbers once the analyst verifies them).

## Verification (end-to-end)
1. `uv run python strava-data/build_dashboard.py` → clean exit.
2. `grep -nE '°C|min/km|km/h' "Running Log/strava.html"` over the new chart region → 0 hits
   (units policy).
3. Preview MCP (strava-qa): open `chart-x-heat`, click both toggle buttons, screenshot each
   state, check console for errors, verify the pace axis is identical between states and
   both light and dark themes render all four violins + the toggle correctly in each view.
4. Confirm no other chart changed (diff scoped to `charts_exploratory.py` heat function,
   `page.py` heat card + stats print, `template.py` JS/CSS if toggle JS is added, and
   `dashboard-spec.md` V4).

## Critical files
- `strava-data/dashboard/charts_exploratory.py` (`chart_x_heat`, 370–459)
- `strava-data/dashboard/page.py` (build call ~220, stats print ~221-223, card/caption
  ~445–449, toggle markup; segment-filter reference ~404–408)
- `strava-data/dashboard/template.py` (toggle JS ~556–568, `.seg-btn` CSS ~403–424)
- `strava-data/dashboard-spec.md` (V4 block 130–144)
- Orchestrator: `.claude/commands/strava.md`, `strava-data/AGENTS.md`
