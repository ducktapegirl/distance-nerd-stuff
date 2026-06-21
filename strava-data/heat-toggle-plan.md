# Plan: Temp ↔ Apparent-Temp toggle on the heat violin chart (4 fixed bands)

> Status: **planned, not yet implemented.** This is a handoff doc for running the
> `/strava` orchestrator pipeline (Design → Build → QA → Review → Ship) on this change.

## Context

The Strava dashboard recently gained two new weather fields — `apparent_temp_c`
(heat index) and `uv_index` — now backfilled into `strava-data/data/activities.csv`.
The chart **"She Pays Pace, Not Heart, for Heat"** currently visualizes pace/HR vs.
**air temperature** only (`average_temp_c`). The goal is to let a viewer toggle the
*same* chart between **air temperature** and **apparent temperature (heat index)** so
the two can be compared 1:1.

Two design decisions were locked with the user:
1. **Re-bin from 3 percentile terciles → 4 fixed temperature bands** (the current code
   is still 3 terciles; no 4-band version exists anywhere in the repo — confirmed across
   `main`, the `claude/strava-weather-uv-heat-ayem1u` branch, git history, and
   `dashboard-spec.md`). Fixed edges: **48 / 62 / 75 °F**, applied identically to both
   metrics.
2. **"All available per view"** — the air-temp view uses every run with `average_temp_c`;
   the apparent-temp view uses every run with `apparent_temp_c` (coverage differs).

Outcome: one chart, a small toggle, both views precomputed, identical bins and identical
axis limits so switching is a clean apples-to-apples comparison. **Only this one chart
changes.**

## How the work should be done: the `/strava` agentic orchestrator

This should be executed through the **`/strava` orchestrator skill**
(`.claude/commands/strava.md`, `strava-data/AGENTS.md`), not by hand. The view is already
chosen and fully specified, so **Intake and Ideate can be skipped**. Stages to run:

- **Design** — dispatch `strava-data-analyst` (Job B, verification) to confirm per-band
  counts and per-view Welch stats for both metrics under the fixed edges; dispatch
  `strava-viz-design` to write the updated V4 spec block. Orchestrator writes it to
  `strava-data/dashboard-spec.md`. **User approves the spec.**
- **Build** — dispatch `strava-developer` to implement (details below).
- **QA** — dispatch `strava-qa` (build integrity, units policy, theme audit, toggle works
  in Preview MCP, label/clip checks). Loop back to Build on failures.
- **Review gate** — `/code-review` + `/security-review` over the diff.
- **Ship** — rebuild both `strava-data/strava.html` and `Running Log/strava.html`.

The orchestrator pauses for user approval between stages (as designed).

## The binning (locked)

Bin in **°C internally** (data stays metric), display labels in **°F** (units policy).
Edges 48/62/75 °F → °C equivalents **8.89 / 16.67 / 23.89**. Four bands:

| Band | °F | °C |
|------|-----|-----|
| Cold | < 48 | < 8.89 |
| Cool | 48–62 | 8.89–16.67 |
| Mild | 62–75 | 16.67–23.89 |
| Hot  | ≥ 75 | ≥ 23.89 |

Same edges for **both** metrics — this is what makes the bins comparable.

## Build details (for `strava-developer`)

Target: `chart_x_heat(rows)` in `strava-data/dashboard/charts_exploratory.py:370`
(wired at `page.py:220` and rendered at `page.py:447`).

1. **Two precomputed datasets, one figure.** Refactor the per-row extraction into a small
   helper that takes the metric column name and returns the 4 binned pace arrays + per-band
   mean HR + Welch stats. Call it twice: once with `average_temp_c`, once with
   `apparent_temp_c`. "All available per view": each pass keeps every run that has a valid
   value for *its* metric (plus valid `average_speed_kmh`).
2. **Traces.** Build both views into one figure: each view = **4 Violin traces + 1 HR
   Scatter line = 5 traces** → 10 traces total. Air-temp view visible by default,
   apparent-temp view `visible=False`. Keep `box_visible`, `meanline_visible`, `points=False`,
   reversed pace axis, `M:SS` ticks, and the existing color language (slate/amber families +
   teal HR line). A 4th band needs a 4th violin color — if a new color is introduced it
   **must** be added to `applyChartTheme()` (CLAUDE.md rule).
3. **Shared axes for 1:1 comparison.** Compute the pace `tickvals`/`ticktext` and y-range,
   and the secondary HR-axis range, from the **union of both views' data** (reuse
   `_pace_ticks`), so both toggle states render on identical axes. X bands are identical by
   construction.
4. **Toggle UI — reuse the existing segment-filter pattern** (do not invent a new one):
   - Button group markup like `page.py:404-408` (`.seg-filter` / `.seg-btn`, CSS already in
     `template.py:403-424`, already theme-covered) placed above `{fig_html(v4,460,"chart-x-heat")}`
     at `page.py:447`. Two buttons: **Air temp** (active default) / **Apparent temp**.
   - JS like `filterSegs` (`template.py:556-568`) using `Plotly.restyle(el, {visible: ...})`
     to show one view's 5 traces and hide the other's.
   - The bottom **stat annotation** (Cool/Hot mean pace, t, p, HR-flat clause) differs per
     view and annotations can't be toggled via `restyle` — also `Plotly.relayout` the
     annotation text on toggle (store both strings on the element, e.g. as `data-*` attrs or
     inline in the JS). X-band labels are identical across views, so they need no swap.
5. **Stats + return dict.** Recompute Welch (coldest vs hottest band) and HR-flat per view.
   Update the `v4m` return keys and the `print(...)` at `page.py:221-223` (currently
   `n_cool/n_mid/n_warm/q1/q2`) to the new 4-band/two-view shape.
6. **Caption.** Update `page.py:448` from "three temperature bands — cool, mid, and warm"
   to four bands and mention the air/apparent toggle.

### Edge cases
- A band may be empty for one metric (e.g. Hot ≥75 °F is likely empty under air temp but
  populated under apparent temp). An empty violin renders nothing — acceptable; the HR line
  must skip `None` band means. QA should confirm no crash and no misleading gaps.
- Apparent-temp view has fewer runs (per-view counts surfaced by the analyst).

## Spec update (for `strava-viz-design` / orchestrator)
Rewrite the **V4 — She Pays Pace, Not Heart, for Heat** block in
`strava-data/dashboard-spec.md:130-143`: 4 fixed bands (48/62/75 °F edges), two precomputed
views with a toggle, shared axis limits from the union, per-view Welch values, and the
verify-vs-recipe numbers for both metrics.

## Verification (end-to-end)
1. `uv run python strava-data/build_dashboard.py` → clean exit.
2. `grep -nE '°C|min/km|km/h' "Running Log/strava.html"` over the new chart region → 0 hits
   (units policy).
3. Preview MCP (strava-qa): open `chart-x-heat`, click both toggle buttons, screenshot each
   state, check console for errors, verify axes are identical between states and both light
   and dark themes render all four violins + the toggle correctly.
4. Confirm no other chart changed (diff scoped to `charts_exploratory.py` heat function,
   `page.py` heat card + stats print, `template.py` JS/CSS if a new toggle fn is added, and
   `dashboard-spec.md` V4).

## Critical files
- `strava-data/dashboard/charts_exploratory.py` (`chart_x_heat`, ~370–459)
- `strava-data/dashboard/page.py` (build call ~220, stats print ~221, card/caption ~445–449,
  toggle markup; segment-filter reference ~404–408)
- `strava-data/dashboard/template.py` (toggle JS ~556–568, `.seg-btn` CSS ~403–424,
  `applyChartTheme` if a new color is added)
- `strava-data/dashboard-spec.md` (V4 block ~130–143)
- Orchestrator: `.claude/commands/strava.md`, `strava-data/AGENTS.md`
