# RESOLVED: "The Seasonal Handoff" chart mobile render

> Fixed 2026-06-22 — fix `ea2c194`, tooling `f466d32`. Verified at 375px on the live
> site. Kept as a record; the bug is closed.

## Root cause (confirmed by measurement, not theory)

`chart-x-seasonal` lives in `#view-exploratory`, which is `display:none` until its tab is
opened. A chart laid out while hidden renders at **0 width**, so Plotly leaves the SVG at
its ~700px default. `activateView()` (`strava-data/dashboard/template.py`) resized charts
**synchronously, right after toggling `display`**, so it read `clientWidth: 0` and the SVG
stayed 700px — overflowing the ~345px mobile card (clipped by `.card{overflow:hidden}`).
That is the "cut off between Jul and Aug" symptom; a later window-resize then shrank it to
an underfill.

Measured at 375px (`tools/mobile_preview.py`): after the tab click the chart was
`svgW 700` vs `cardW 345`. The old "negative y-axis range" was a *separate, already-gone*
artifact — under the pinned plotly (5.24.1 build / 2.35.2 runtime) the build-time autorange
is correct (`yRange [0,184]`, `y2Range [0,8.4]`) even at 0 width.

## Fix

In `activateView()`, defer the per-chart `Plotly.Plots.resize(el)` (and `thinTicks`) into a
`requestAnimationFrame` scoped to the newly-active view, so the now-visible card has real
width before resizing. Removed the blanket autorange relayout from the earlier attempt
(`49efdf2`) — it was unnecessary *and* clobbered charts that set intentional fixed ranges
(cardiac x-axis, load/heat y2). Result: `svgW 700 → 297` (= card content width), stable
after a resize; `chart-x-load` keeps its fixed `y2 [0,2.2]`.

## How to verify (this was the real blocker the whole time)

The Claude Preview MCP can't reach a local server on this machine, **and the prod URL in
the prior version of this doc was wrong** (it 404'd, so every "prod check" silently failed).

- **Tool:** `tools/mobile_preview.py` — in-process `127.0.0.1` server + mobile-emulated
  Playwright Chromium in one host process. **Run un-sandboxed** (page loads plotly.js from
  `cdn.plot.ly`). Prints chart fill/range measurements and saves screenshots.
- **Correct prod URL:** `https://ducktapegirl.github.io/distance-nerd-stuff/strava.html`
  (project page — served under the repo subpath; the bare `ducktapegirl.github.io/strava.html`
  is a 404).

```
# Local build:
uv run python strava-data/build_dashboard.py
uv run python tools/mobile_preview.py \
  --click '.tab[data-view="exploratory"]' \
  --measure chart-x-seasonal --resize-probe --screenshot out/seasonal.png

# Live site:
uv run python tools/mobile_preview.py \
  --url https://ducktapegirl.github.io/distance-nerd-stuff/strava.html \
  --click '.tab[data-view="exploratory"]' --measure chart-x-seasonal
```
Pass criteria: `svgW ≈ elW` (chart fills its card), ranges sane, stable after `--resize-probe`.
