# HANDOFF: "The Seasonal Handoff" chart still broken on mobile

> Status as of commit `98958dc`. The bug only manifests on the **deployed** GitHub Pages
> site. The previous session ran in a network-isolated remote sandbox and could not load
> the live page — it could only rebuild a local approximation, which disagreed with
> production. Continue from an environment with network access (desktop app) so you can
> inspect the live page directly.

## Symptom

`chart-x-seasonal` ("The Seasonal Handoff", Exploratory tab) on mobile: plot crammed into
the left third, bars don't span width, and the **left y-axis shows a negative range**
(screenshot showed ~0 / −50 / −100) instead of the correct run-distance range (0..~184 km).
**Only this one chart is affected.**

## What's already been tried (all on `main`, all deployed green)

1. `0ed37d1` / merged `9f9c99c` — deeper right margin `r=80` + `automargin=True` on both
   y-axes in `chart_x_seasonal` (`strava-data/dashboard/charts_exploratory.py`).
   → made it worse (cramped/overlap).
2. `44d61ab` — removed `automargin=True`, kept `r=80`. → no change for the user.
3. `98958dc` — pinned `plotly==5.24.1` in `pyproject.toml` (was unpinned → resolved to
   6.8.0) to match the hard-pinned runtime CDN `plotly.js 2.35.2`
   (`strava-data/dashboard/config.py:16`). Rebuilt; vendored JS now == CDN (2.35.2).
   → a local headless render (Playwright + vendored 2.35.2, forcing the exploratory view
   active then `Plotly.Plots.resize`) shows the chart FIXED: `yRange [0,184.3]`,
   `y2Range [0,8.4]`, fills card width, matches the known-good `chart_x_load` sibling.
   → but the user still sees it broken live.

Deploy status confirmed via GitHub Actions: runs for `9f9c99c`, `44d61ab`, `98958dc` all
`completed/success`. Production is serving the latest build.

## Leading hypothesis to test FIRST

The negative y-axis range is the key tell. The chart lives in `#view-exploratory`, which
is **not** the default-active tab, so it first renders while hidden (`display:none`,
container width 0). A width-0 initial Plotly render of this categorical-x dual-axis chart
likely computes a **garbage autorange** (the negative range). On tab activation,
`activateView()` (`strava-data/dashboard/template.py`, ~line 931) only calls
`Plotly.Plots.resize(el)` — which resizes but does **not** re-run autorange — so the bad
range persists. The local test happened to dodge this (chromium timing / nonzero hidden
width), which is why local shows fixed but prod doesn't. **This is plausibly the real root
cause and is independent of the plotly version.**

### Decisive ~30-second live test (on the broken page, Exploratory tab open):
```js
// 1. What's actually live + how is the chart laid out?
(()=>{const el=document.getElementById('chart-x-seasonal');const f=el._fullLayout;
return JSON.stringify({plotly:Plotly.version,cardW:el.closest('.card').clientWidth,
svgW:Math.round(el.querySelector('svg.main-svg').getBoundingClientRect().width),
size:f._size,yRange:f.yaxis.range,y2Range:f.yaxis2&&f.yaxis2.range})})()

// 2. Does a full re-autorange fix it live? If YES → root cause confirmed.
(()=>{const el=document.getElementById('chart-x-seasonal');
Plotly.relayout(el,{'xaxis.autorange':true,'yaxis.autorange':true,'yaxis2.autorange':true});})()
```
- If snippet 1 shows `plotly` != `2.35.2` → CDN/edge caching is serving a stale runtime
  (different problem: cache-bust / wait for Fastly).
- If snippet 1 shows a negative `yRange` and snippet 2 visually fixes the chart → confirmed
  hidden-render autorange bug. **Fix:** in `activateView()` (template.py ~931), after the
  `Plotly.Plots.resize(el)` loop, also re-autorange charts in the newly-activated view —
  e.g. `Plotly.relayout(el,{'xaxis.autorange':true,'yaxis.autorange':true,'yaxis2.autorange':true})`,
  or switch to lazy-init (only `newPlot` a view's charts the first time it's shown), or use
  `Plotly.react`. Apply narrowly (or to all initially-hidden views) and re-verify live.

## Also worth ruling out (network available)
- `curl -s https://ducktapegirl.github.io/strava.html | grep -o 'plotly-[0-9.]*min.js'`
  and grep the `chart-x-seasonal` `newPlot` JSON for `"range"` — confirms the *served*
  file matches the repo build (rules out stale Pages artifact / caching).
- Load the live URL in a real browser at phone width and reproduce via the actual tab
  click (not a forced view toggle). The sandbox couldn't replicate this flow because map
  tiles fail offline and throw a pageerror that interrupts init JS locally.

## Repo orientation
- Chart builder: `strava-data/dashboard/charts_exploratory.py` → `chart_x_seasonal()`.
- Theme/legend defaults: `strava-data/dashboard/theme.py` `tidy_dark()` (legend at y=-0.25).
- Page assembly / embedding: `strava-data/dashboard/page.py` (v5, `fig_html(v5,440,"chart-x-seasonal")`).
- Tab activation + mobile resize/thinTicks JS: `strava-data/dashboard/template.py` (~931, ~955).
- Runtime CDN pin: `strava-data/dashboard/config.py:16` (and `Running Log/src/dashboard/config.py:34`).
- Build: `uv run python strava-data/build_dashboard.py` → writes `Running Log/strava.html`
  (gitignored). Deploy: `.github/workflows/deploy.yml` (uv sync → build both → Pages).
- QA agent (has a §6.5c under-fill check added earlier): `.claude/agents/strava-qa.md`.

## Open question on the plotly pin
The `plotly==5.24.1` pin (`98958dc`) is defensible regardless (build/runtime should match),
but if the real cause is the autorange-on-activation bug above, the pin may be incidental.
Recommend keeping it (versions should match) once the true root cause is confirmed.
