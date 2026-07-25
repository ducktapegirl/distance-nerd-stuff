# Shared Visual QA Suite (V0–V8)

The rendered-layer checks both dashboard QA agents run. `strava-qa` and `running-log-qa` each
own their target-specific stages (build, spec, units, data, static `qa.py`) and delegate the
**visual/rendered** pass to this file.

This exists because the two agents previously carried byte-identical copies of these checks and
had already drifted apart. Treat this file as the single source of truth: fix a check here, not
in an agent.

**Check IDs are stable.** Report them as `V0`…`V8` regardless of which agent invoked the suite,
so reports from the two dashboards are directly comparable. (These IDs replace the old
per-agent numbering — `strava-qa` §6.5 and `running-log-qa` §3.5 were the same check.)

| ID | Check | Script |
|---|---|---|
| V0 | Transport + viewport sweep contract | — (this file) |
| V1 | Render smoke + console errors | — (transport report) |
| V2 | Label-overlap + tick-label collisions | `tools/qa-checks/label-overlap.js` |
| V3 | Edge-clipping / truncation vs the figure edge | `tools/qa-checks/edge-clip.js` |
| V4 | Width-fill / under-fill (figure vs card) | `tools/qa-checks/width-fill.js` |
| V5 | Theme contrast audit, light + dark | `tools/qa-checks/contrast.js` |
| V6 | Axis-range blowout + plot-area fill + legend | `tools/qa-checks/axis-fill.js` |
| V7 | Hover/datatip theme-mismatch | `tools/qa-checks/hover-theme.js` |
| V8 | Page-level overlap, overflow, tap targets | `tools/qa-checks/dom-overlap.js` |

**The checks live in `tools/qa-checks/*.js`, not in this file.** Each is a plain expression
returning JSON, so the same file runs unchanged under either browser transport: pass
`--eval @tools/qa-checks/<name>.js` to `mobile_preview.py`, or `Read` the file and hand its
contents to `preview_eval`. Fix a check in its `.js` file — this document describes intent,
thresholds, and how to judge the output.

Each script carries a header comment explaining what it catches and why the neighbouring checks
can't. Read that header before overriding a verdict.

---

## Invocation contract

The calling agent supplies this parameter block. Nothing dashboard-specific is hardcoded below.

```
target:    strava-data | running-log
page:      the built HTML under running-log/ (strava.html | index.html)
tabs:      the ordered tab list for this target
chart ids: the expected chart div ids for this target
exempt:    charts with no cartesian axis or legend — donuts, sparklines,
           heatmaps, calendars, maps. Skip axis-oriented checks for these;
           still run V3 / V4.
```

---

## V0 — Transport + viewport sweep contract

### Transport

**This repo is worked on from several Claude Code environments — local desktop, the mobile app,
web/remote containers — and browser tooling differs in each.** Do not assume a transport is
available, do not assume a failure means the dashboard is broken, and never present a run made
with reduced tooling as a full pass. **Probe, then declare what you used.**

The `tools/qa-checks/*.js` files are the specification of **what** to measure. Run them through
whichever transport actually loads the page — they are plain expressions returning JSON, so they
work unchanged under either.

| | Transport | Requires | Strengths | Blind spots |
|---|---|---|---|---|
| **T1** | Preview MCP (`mcp__Claude_Preview__preview_*`) | the MCP provisioned **and** able to reach the served page | `preview_snapshot` accessibility tree, `preview_click`, `preview_console_logs`, screenshots | resize only — no true mobile emulation (no touch, DPR 1), so tap-target and touch-affordance checks are approximations |
| **T2** | `tools/mobile_preview.py` (in-process server + Playwright) | Bash, Playwright, a resolvable Chromium, and network egress to `cdn.plot.ly` | real device emulation (touch, DPR 2), precise geometry, deterministic settle control, screenshots | no accessibility tree; each run is a fresh process |
| **T3** | Static only | nothing beyond `Read`/`Grep`/`Bash` | always available; the caller's static checks | cannot see rendered geometry — **V1–V8 are unavailable** |

#### The probe

1. **Probe T2** — `uv run python tools/mobile_preview.py --probe --page <target page>`.
   Exit **0** = usable. Exit **2** = not; the JSON `reason` says which piece is missing:
   - `playwright-not-installed` → `uv add --dev playwright && uv run playwright install chromium`
   - `chromium-not-launchable` → no Chromium this Playwright can drive (the script already
     falls back to any Chromium it can find under `PLAYWRIGHT_BROWSERS_PATH`, so this means
     there genuinely isn't one)
   - `plotly-cdn-unreachable` → **T2-degraded**, see below. Re-run un-sandboxed first; if it
     still fails, this environment's network policy blocks the CDN.
2. **Probe T1** — `preview_start` on the page, then confirm the URL is not `chrome-error://`
   and a screenshot is non-blank.
3. If neither, **T3**.

Cache the verdict for the whole run — do not re-probe per tab.

#### T2-degraded (browser works, CDN blocked)

A real and easily-misread state: the browser launches and the page loads, but `plotly.js` never
arrives, so **no chart renders**. Everything chart-scoped (V2–V7) is unavailable, while
page-level DOM and theme checks still work because they don't depend on Plotly. Do **not**
report empty charts as FAILs — that is the environment, not the dashboard. Report the
chart checks as `NOT RUN (plotly CDN unreachable)` and run what remains. Pass
`--plotly-timeout 2000` so each invocation stops paying the full 15s wait.

#### Using both when both are live

Split by strength rather than picking one — that is where the information gain is:

| Check | Preferred | Degraded behavior |
|---|---|---|
| V1 render + console errors | T1 | `preview_console_logs` is richer; under T2 read the report's `console_errors` |
| V2 overlap, V3 edge-clip, V4 width-fill, V6 axis-range | **T2** | pure geometry — needs the real DPR and emulated width to be trustworthy. On T1, flag results as *resize-emulated* |
| V5 contrast, V7 hover/datatip theme | either | both read computed style |
| V8 DOM overlap + tap targets | **T1 + T2** | T2 gives true touch-target geometry; T1's a11y tree also catches elements that look fine but are unreachable |
| Mobile checklist (bottom sheet, swipe, spark stacking) | **T2** | needs touch emulation; on T1 these degrade to visual-only confirmation |

#### T2 invocation reference

```
--probe                     report usability and exit (0 usable / 2 not)
--page /index.html          which built page to serve (default /strava.html)
--desktop                   TRUE desktop render: 1440x900, DPR 1, no touch.
                            REQUIRED for the desktop pass -- without it a wide
                            viewport is still mobile-emulated, which is not a
                            desktop render
--theme light|dark|system   click the theme toggle after load and settle
--eval @tools/qa-checks/x.js  run a check file (or a raw JS expression)
--click '<selector>'        repeatable; use to activate tabs
--screenshot <path>         save a PNG
--offline-plotly            serve plotly.js from the installed plotly
                            package instead of the CDN -- turns
                            T2-degraded back into a full T2 run with no
                            network. Warns loudly if the vendored build
                            isn't the one the page pins
--plotly-timeout <ms>       lower it when the CDN is known blocked
```

**If the probe reports `plotly-cdn-unreachable`, retry with `--offline-plotly` before
falling back to T2-degraded** — it usually recovers full chart coverage outright. It
does not help the Strava map tab, which needs `unpkg.com`. See
`Project Docs/Handoffs/qa-visual-verification.md`.

### Viewport sweep

Run the full suite at **two** viewports:

1. **Desktop — 1440×900.**
2. **Mobile — 390×844** (an iPhone-class width, below the `@media (max-width: 640px)` tier).

Set the viewport via the transport's size option — `preview_start`'s width/height arguments
(preferred) or `preview_screenshot`'s under Preview MCP; `--width`/`--height` under
`mobile_preview.py`. Re-open or resize between passes and wait ~1s for relayout: the page
debounces a `resize`/`visualViewport` listener that calls `Plotly.Plots.resize()` and toggles
the mobile chart simplifications.

**Run V2–V8 in *each* pass.** Mobile reflow — collapsed legends, a much narrower plot area,
thinned ticks, stacked cards — routinely introduces overlap and edge-clipping that never
appears at desktop width, so the 390px pass is not optional. Tag every row in every table with
a **Viewport** column (`desktop` / `mobile`). V5 and V7 additionally run once per theme, so a
full sweep is 2 viewports × 2 themes for those two.

### Tab handling

Switch tabs with `preview_click` on `.tab[data-view="<name>"]` (or the equivalent click through
your transport). **Hidden views keep their charts in the DOM**, so every audit below filters to
visible charts with `el.offsetParent !== null`. Charts that first render in a hidden tab may
not have been fitted — activate the tab and wait for relayout before measuring.

---

## V1 — Render smoke + console errors

Screenshot the page and check the console for errors. Confirm charts **actually render** — not
merely that the source contains their divs. Confirm every expected chart id from the parameter
block is present and rendered.

Under Preview MCP use `preview_console_logs`; under `mobile_preview.py` the report surfaces a
`warning` when `window.Plotly` never appeared (usually a blocked CDN from a sandboxed run —
retry un-sandboxed before reporting it as a failure).

---

## V2 — Label-overlap detection

Goal: find legends/annotations that **obscure plotted data** or **collide with each other**.

**Labels positioned outside the plot *area* are acceptable — never flag a label merely for
sitting in the margin.** Only actual intersection with data marks or other labels counts here.
Sitting in the margin is fine; spilling past the *figure's own edge* so the text is cut off is
NOT — that clipping is a separate FAIL caught by V3. **"Outside the plot area" and "outside the
figure" are different things: the first is allowed, the second is a defect.**

Run **`tools/qa-checks/label-overlap.js`** (activate each tab first; the script filters to
visible charts itself).

Evaluate:

- `OK` → PASS.
- `CHECK` → take a screenshot and visually confirm. FAIL only if the label visibly obscures data
  marks or another label; otherwise PASS with a note (grazing one faded background point is
  negligible).
- **Leader/connector-line false positives:** the line-sampling step treats every `.js-line` as
  data, so a label deliberately placed at the tip of its own pointer line — e.g. the Strava V2
  archetypes (PCA biplot) loading-arrow labels, where each arrow runs from the origin out to its
  label — will show a high `marksHit` against its OWN connector. That is not data occlusion.
  When a `CHECK` is driven by line hits, re-run with the `.js-line` sampling block removed
  (markers only: `.scatterlayer .point, .barlayer .point, .boxlayer .point,
  .violinlayer path.violin`) and judge against that; if markers-only is clean (only 1–2 grazed
  points, < ~50px), PASS.
- Charts without standard layers — sparklines, calendars, heatmaps, maps → note as **N/A**.

**Tick-label collisions (`tickStatus` / `tickTick`) are reported separately** from the
legend/annotation verdict, because crowded or rotated tick labels collide with each other long
before anything touches the legend, and a wall of tick rows would otherwise bury that signal.
Judge them on their own:

- `tickStatus: OK` → PASS.
- `tickStatus: CHECK` → each item reports `gapPx` (actual separation) against `needPx` (what the
  text needs), plus `rotated`. `frac` is how far short the gap falls. A gap near zero is
  unreadable text and a **FAIL**; within ~15% of `needPx` is worth a screenshot. Fix by thinning
  ticks (`dtick`/`nticks`) or rotating (`tickangle`) in the Python figure rather than relying on
  page-JS defaults.

  **Rotation is handled, and this matters.** Plotly auto-rotates crowded ticks, and a
  bounding-box test would flag every rotated label as overlapping — `getBoundingClientRect`
  returns the axis-aligned box, so 30° "Jul 2003"/"Jan 2004" labels 22px apart measure as 47×34
  boxes "52% overlapping" while reading perfectly. Since rotation is the *fix* for crowding, an
  AABB test flags the fix. The script instead measures along-axis extent for unrotated ticks and
  the perpendicular gap between baselines (`spacing × |sin angle|`) for rotated ones. If you
  ever replace this check, keep that distinction.

For FAIL items suggest a concrete fix: move the annotation outside the plot area
(`xref`/`yref="paper"`, coordinates beyond [0,1], **with the margin on that side deepened
enough to keep the whole label inside the figure** — verify with V3; an offset like `y=-0.20`
clips if the margin is too shallow), reposition to an empty quadrant, or push the legend
further below (`y=-0.35`).

Report one row per chart: | Chart ID | Tab | Viewport | Status | Detail |

---

## V3 — Edge-clipping / truncation detection

A label placed in the margin (`yref="paper"` with y<0 or y>1, an `xanchor` overhang, etc.) is
only acceptable if it still renders **inside the figure's SVG viewport**. When the margin is too
shallow for the offset, Plotly draws the text past the `svg.main-svg` edge and the browser clips
it: the label is fully present in the DOM and in `data-unformatted`, but the user sees only a
sliver or nothing. **V2 does not catch this** — the clipped text overlaps no data and no other
label — so run this separate pass on **every** tab.

Run **`tools/qa-checks/edge-clip.js`** (activate each tab first; the script filters to
visible charts itself).

Evaluate:

- `clippedCount: 0` → PASS.
- Any item → **FAIL**: the label text is cut off by the figure edge. Cite the chart, the side(s),
  and `hiddenPct`, and screenshot the offending chart as proof.
- **Subplot titles count.** `subplot_titles=[...]` render as annotations at the top of each
  subplot, so a too-shallow **top** margin (the `tidy_dark` default is `t=20`, tight for the
  size-16 title font) clips their tops — this pass catches that as a `top` overflow.

Suggested fix: deepen the margin on the clipped side enough to contain the label
(`fig.update_layout(margin=dict(b=...))` for a bottom stat line, `dict(t=...)` for clipped
subplot titles) and/or pull the paper offset back toward [0,1]. After the fix the label must sit
fully inside `svg.main-svg`; re-run until `clippedCount: 0`.

Report one row per clipped label: | Chart ID | Tab | Viewport | Side(s) | Hidden % | Status |
(A margin that contains a label at 1440px often clips it at 390px.)

---

## V4 — Width-fill / under-fill detection

V0's mobile checklist catches a chart that **overflows** its card; this pass catches the inverse
— a chart that renders **narrower than its card**, leaving dead space beside the plot so the
y-axis labels and data don't span the available width. Most common on **mobile**, on **dual-axis
(`secondary_y`) charts whose right margin is too tight** for the right axis title/ticks, and on
charts that first rendered in a hidden tab and weren't re-fit. V2 and V3 do **not** catch it —
the chart occludes nothing and clips nothing, it's just too small.

Run **`tools/qa-checks/width-fill.js`** (activate each tab first; the script filters to
visible charts itself).

Evaluate:

- `fillPct >= 90` → PASS (the chart spans essentially the whole card width).
- `fillPct < 90` → **FAIL**: the chart under-fills its card. Screenshot it as proof and cite the
  fill %.
- `fillPct > 100` → the overflow case; flag it and cross-check against the caller's mobile
  checklist.

Suggested fix: ensure the figure has **no fixed `layout.width`**; for dual-axis (`secondary_y`)
charts deepen `margin.r` (e.g. `r=80`, as Strava's `chart_x_load` does) and set `automargin=True`
on the y-axes so the right axis fits without squeezing the plot; and confirm the chart re-fits
after its tab is activated (the page calls `Plotly.Plots.resize` on tab switch). Rebuild and
re-run until `fillPct >= 90` at both viewports.

**Caveat:** this measures the *figure* against its card, not the *plot area*. A chart whose axis
range is blown out still fills its card at 100% and passes here — that failure is V6's job.

Report one row per chart: | Chart ID | Tab | Viewport | Chart px | Card px | Fill % | Status |

---

## V5 — Theme audit, light AND dark

Both pages have a theme toggle (`.theme-toggle button[data-theme="light"|"dark"|"system"]`).
`applyChartTheme()` in the page JS restyles charts from CSS variables when toggled. Verify every
chart's text is legible in **both** themes at **both** viewports — 4 combinations:
desktop/light, desktop/dark, mobile/light, mobile/dark. Mobile retints the same CSS variables,
but the narrower layout can surface issues the desktop pass misses.

For each theme (`light`, then `dark`):

1. Switch: click `.theme-toggle button[data-theme="light"]` (or `"dark"`). Wait ~1s for relayout.
2. On each tab, run:

Run **`tools/qa-checks/contrast.js`** (activate each tab first; the script filters to
visible charts itself).

3. Thresholds: contrast **< 2.0 = FAIL** (effectively invisible), **2.0–3.0 = WARN**.
   Note: semi-transparent pill backgrounds composite with the page, so computed contrast is
   approximate — confirm borderline cases on the screenshot before failing them.
4. Screenshot a chart-heavy tab in **both themes** at **each viewport** (4 shots), plus any
   failing tab. The caller names which tab and any target-specific elements to confirm.

**Caveat:** this is a *contrast* test, so it cannot detect a theme **mismatch** — light text on a
leftover dark pill in light mode scores high contrast and passes here. That failure is V7's job.

Report per theme: | Chart ID | Tab | Viewport | Theme | Worst contrast | Status |

---

## V6 — Axis-range blowout, plot-area fill, legend presence

Run **`tools/qa-checks/axis-fill.js`** on every tab, at both viewports.

Catches the failure `CLAUDE.md` documents under "Plotly charts — mobile-safe authoring":
chart chrome anchored in **data** coordinates forces autorange to widen the axis to keep the
text on canvas, compressing the data into part of the card while looking fine on desktop.
**V4 cannot see this** — the figure still fills its card at 100%; the defect is inside the
figure. Three verdicts per chart, reported separately so none masks another:

- **`axisStatus`**
  - `FAIL` — an **autoranged** axis overruns the data by more than 15% of the data span
    (or, for a category axis, more than 0.6 beyond `[-0.5, n-0.5]`). This is the blowout.
    Fix by moving data-coordinate chrome to `xref="paper"` **and** pinning an explicit `range=`.
  - `PINNED` — the axis is wider than this chart's data but the range was **set explicitly**.
    That is a deliberate authoring choice, not a defect: running-log's PR charts share
    `_PR_X_RANGE` so the small-multiples are comparable. **Never report PINNED as a failure** —
    pinning is the prescribed fix, and flagging it would flag the fix as the bug.
  - `OK` — within tolerance, or no cartesian x-axis (donuts, sparklines, heatmaps, maps report
    `axis: "n/a"`).
- **`plotStatus`** — `WARN` when the plot area is under 55% of the figure width. The floor is
  calibrated, not guessed: a labelled mobile chart bottoms out near 59% (a ~65px left margin for
  tick text on a ~297px figure is unavoidable) and typical charts sit at 70–76%, so 55% flags
  only charts paying for something extra — usually a dual-axis (`secondary_y`) chart with a wide
  fixed `margin.r`. Fix with `automargin=True` rather than a hardcoded margin.
- **`legendStatus`** — `FAIL` when `showlegend` is true but no `.legend` node rendered. Catches
  the stale-`simplify()` failure where page JS hides a legend the chart's redesign now needs.

Report: | Chart ID | Tab | Viewport | axisStatus | dataFill % | plotFrac | legend | Status |

## V7 — Hover/datatip theme mismatch

Run **`tools/qa-checks/hover-theme.js`** once per theme, at both viewports.

**V5 structurally cannot catch this.** A dark hover pill surviving into light mode holds *light*
text on a *dark* background — high contrast, so V5 passes it — while looking obviously wrong.
The defect is a theme **mismatch**, not a legibility failure, so this check compares each
surface's background **luminance** against the page's instead of computing a ratio.

It also needs a hover to exist: Plotly builds `.hoverlayer .hovertext` only in response to one,
so nothing in the resting DOM reveals it. The script triggers hover via `Plotly.Fx.hover()`
rather than a synthetic `mousemove`, which is unreliable under touch emulation.

- `DARK-IN-LIGHT` / `LIGHT-IN-DARK` on `hoverPillFill` → **FAIL**. The page's
  `applyChartTheme()` is not restyling `hoverlabel` for that chart.
- The same luminance test is applied to annotation pills (`rect.bg`) and chart titles, which
  share the failure mode.
- **Async:** returns a Promise, so it needs a transport that awaits it (`mobile_preview.py`
  does). Under T1, confirm `preview_eval` resolves promises before trusting a clean result.

Report: | Chart ID | Tab | Viewport | Theme | Pill fill | Verdict | Status |

## V8 — Page-level overlap, overflow, and tap targets

Run **`tools/qa-checks/dom-overlap.js`** at both viewports.

Everything in V2–V7 is scoped to the inside of a chart's SVG. This is the only check that looks
at the **page**: cards colliding, a stat tile running under the theme toggle, the document
scrolling sideways. Those are the failures a narrow viewport produces first.

- **`overlap`** — pairwise intersection over rendered **siblings only**, above 24px. Nesting
  (a card containing its heading) and deliberate overlays (`#detail-panel`, backdrops) are
  excluded; without those exclusions the output is a wall of true-but-useless hits. `CHECK`
  means screenshot and judge — `fracOfSmaller` tells you how much of the smaller element is
  covered.
- **`horizontalOverflow`** — `FAIL` when `scrollWidth > innerWidth + 2`. On failure the report
  names the widest offending elements so the fix is obvious.
- **`tapTargets`** — `WARN` below 40px per `Project Docs/Plans/mobile-redesign-plan.md`.
  **Only evaluated on the mobile tier** (≤640px or a coarse pointer); at desktop it reports
  `N/A (desktop pointer)`, since dense toolbar buttons are fine under a mouse and would
  otherwise bury the real mobile findings.

Report: | Viewport | Overlaps | Overflow px | Tap targets < 40px | Status |

---

## Reporting

Return a markdown checklist with PASS / FAIL / WARN / N/A per check. Cover **both viewports**
(desktop 1440 + mobile 390), with the **Viewport** column populated in every table.

**Open the visual section with the transport actually used and any resulting coverage loss.**
This is not optional — it is what keeps a thin run from reading like a clean one. Four shapes:

```
Transport: T2 (mobile_preview.py, Chromium 141, 390x844 @2x mobile-emulated)
           T1 unavailable (Preview MCP not provisioned in this environment)
Coverage:  V1-V8 full.
```
```
Transport: T1 (Preview MCP, 390x844 resize-emulated) + T2 (geometry)
Coverage:  V1-V8 full.
```
```
Transport: T2-degraded (browser OK, cdn.plot.ly blocked by network policy)
Coverage:  V1-V7 NOT RUN (no chart renders without plotly.js).
           V8 / DOM + theme checks ran normally. Charts unverified.
```
```
Transport: T3 (static only - no browser available in this environment)
Coverage:  V1-V8 NOT RUN. Partial QA pass; the visual layer is unverified.
```

A run made with reduced tooling is a **legitimate, clearly-labeled result** — never a silent
pass, and never a FAIL merely because a transport was missing. If no browser transport is
available, say so plainly and report V1–V8 as `NOT RUN`; the caller's static checks still apply.

For each FAIL/WARN add a one-sentence description and, if obvious, a suggested fix. End with the
screenshots taken and which viewport/theme/tab each shows.
