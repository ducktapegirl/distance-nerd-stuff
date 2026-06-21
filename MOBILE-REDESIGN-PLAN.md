# Mobile-friendly redesign for both dashboards

## Context

The Strava dashboard (`strava-data/dashboard/`) and Running Log dashboard (`Running Log/src/dashboard/`) were previously made "responsive" (CSS grid breakpoints, `responsive: true` on Plotly, a viewport meta tag) but that only covers generic reflow, not a real mobile experience. On an actual phone today:

- Plotly charts have **fixed px heights** (260–540px) and only re-resize when switching tabs, never on viewport resize/rotation — so charts can render mis-sized after the page loads on a phone.
- The tab nav is a `flex-wrap` strip that wraps into a messy multi-row block on narrow screens instead of behaving like an app nav.
- Touch targets (theme toggle, segment/pill buttons) are often 22–36px — below the ~44px tap-target guideline.
- The Strava detail/side panel becomes an **accidental** full-viewport overlay below 600px (via `max-width: 100vw`) rather than an intentional mobile pattern. Running Log has the identical component and the same problem.
- Typography is all fixed px; some labels are 9–10px, unreadable on a phone.
- Breakpoints are scattered and ad-hoc per component (560/600/700/760/800/900px) with no cohesive mobile tier.

Decisions made with the user up front:
1. **Scope**: both dashboards get the same mobile pass in one effort (same patterns applied independently in each codebase — no cross-file coupling, since `template.py` is intentionally separate per dashboard).
2. **Nav**: replace wrapping tabs with a **single-row horizontally-scrolling tab strip** (scroll-snap), not a hamburger or bottom bar.
3. **Detail panel**: convert to a **bottom sheet** (slides up from bottom, swipe-down/backdrop-tap to dismiss) instead of the accidental full-screen overlay. Apply to both dashboards' detail panels for consistency.
4. **Charts**: genuinely **simplify** for mobile (shorter aspect-ratio heights, collapsed legends, thinned tick labels) — not just shrink the same dense chart into a smaller box.

## Breakpoint strategy

Replace the scattered 560/600/700/760/800/900px breakpoints with two tiers, defined independently in each file's CSS string (same numbers/semantics in both, no shared code):
- `@media (max-width: 900px)` — tablet tier, keep existing column-reduction rules (stat-grid, type-stat-grid, pr-grid).
- `@media (max-width: 640px)` — new unified mobile tier. All "true mobile" rules (nav, touch targets, chart height/simplification, bottom sheet, base typography floor) live in one consolidated block per file, replacing the old 560/600/700/760/800 ad-hoc queries.

## Implementation, in order

1. **Fluid typography** (`clamp()` on h1/wordmark/stat numbers in both `template.py`s) — independent of breakpoints, lowest risk, ship first.
2. **Consolidate breakpoints** into the new `@media (max-width:640px)` block in both files, folding in the existing 560/600/700/760/800 rules.
3. **Touch targets**: inside the 640px block, bump `.theme-toggle button`, `.tab`, `.seg-btn`/`.chart-toggle`/`.hm-toggle`/`.race-tab`/`.filter-pill` to ≥40px (primary `.tab` nav to the full 44px).
4. **Scroll-snap tab nav**: `.tabnav { flex-wrap:nowrap; overflow-x:auto; scroll-snap-type:x proximity; -webkit-overflow-scrolling:touch; scrollbar-width:none }` + `.tab { scroll-snap-align:start; flex:0 0 auto }`, both files. Optionally auto-center the active tab via `scrollIntoView` in the existing tab-click handler.
5. **Responsive chart heights**: add `@media (max-width:640px) { .js-plotly-plot { height:auto !important; aspect-ratio:4/3; max-height:70vh } }` (overrides Plotly's inline `height:Npx`), plus a **global debounced `resize`/`visualViewport` listener** calling `Plotly.Plots.resize()` on all `.view.active .js-plotly-plot` elements — this is the real fix for charts never resizing outside of tab-switches. No changes needed to `fig_html()` call sites or per-chart height args.
6. **Chart simplification** via a `matchMedia('(max-width:640px)')`-driven JS block that calls `Plotly.relayout()`/`restyle()` on specific dense charts (mirrors the existing toggle-trace pattern already in the codebase):
   - Strava: hide rangeslider + thin x-ticks on Volume; shrink/truncate segment-name tick labels on Top Segments; shorten violin category labels on the heat/temp chart; hide the 8 PCA loading-label annotations on the archetypes biplot (requires a small additive change to `charts_exploratory.py`'s `chart_x_archetypes()` to return the annotation index range, mirroring the existing `hr_temp_meta` pattern).
   - Running Log: hide legend on Pace Timeline and Monthly-Mileage-by-Year (rely on hover tooltips, which already exist); thin x-tick density on Workout Mix by Season.
7. **Bottom sheet for detail panel**, both dashboards: swap `.detail-panel`'s mobile transform from `translateX` (side) to `translateY` (bottom), `top:auto`, `max-height:85vh`, rounded top corners, grab-handle affordance. Existing `closeDetail()`/backdrop-click/Escape handlers need no logic changes (only toggle `.open`); add a touch swipe-down-to-dismiss handler gated to `matchMedia('(max-width:640px)')`. Running Log's existing narrow `@media (max-width:600px){.detail-panel{width:100vw}}` override gets removed and replaced by this same pattern.

## Files touched

- `strava-data/dashboard/template.py` — CSS consolidation, touch targets, scroll-snap nav, chart-height override, resize listener, chart-simplify JS, bottom-sheet CSS/JS.
- `strava-data/dashboard/charts_exploratory.py` — `chart_x_archetypes()` returns loading-label annotation index range for mobile hide/show.
- `Running Log/src/dashboard/template.py` — same categories of changes as Strava's `template.py`, applied independently (including removing its existing narrow detail-panel mobile override at the old 600px breakpoint).
- No changes needed to `page.py`, `sections.py`, `theme.py`, `rollups_cards.py`, `charts_production.py`, `charts.py`, `components.py`, `config.py`, `data.py`, `stats.py` — chart height/legend/tick adjustments are handled client-side via CSS + `Plotly.relayout`/`restyle`, not by touching Python height/layout args at the source.

## Verification

1. Rebuild both: `uv run python strava-data/build_dashboard.py` and `uv run python "Running Log/src/visualize_log.py"`.
2. Open `Running Log/strava.html` and `Running Log/index.html` in a browser with devtools device emulation at 375px (iPhone SE), 390px (iPhone 12/13/14), 414px (Plus/Pro Max), and 768px (tablet, to confirm the 900px tier is untouched).
3. Check: tab strip scrolls horizontally without wrapping; tap targets feel reachable; charts visibly resize when the emulated viewport is resized/rotated without a tab switch; Volume/Top-Segments/Heat/Archetypes (Strava) and Pace-Timeline/Monthly-by-Year/Workout-Mix (Running Log) show their simplified mobile variants; tapping a detail point opens a bottom sheet (not a full-screen side panel), dismissible via backdrop tap, Escape, and swipe-down.
4. Toggle light/dark/system theme at each width to confirm `applyChartTheme()` still works untouched.
5. Verify desktop (>900px) rendering is pixel-unchanged by diffing before/after screenshots at one wide viewport.
