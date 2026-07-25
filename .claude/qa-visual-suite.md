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

| ID | Check | Status |
|---|---|---|
| V0 | Transport + viewport sweep contract | active |
| V1 | Render smoke + console errors | active |
| V2 | Label-overlap (label-vs-data, label-vs-label) | active |
| V3 | Edge-clipping / truncation vs the figure edge | active |
| V4 | Width-fill / under-fill (figure vs card) | active |
| V5 | Theme contrast audit, light + dark | active |
| V6 | Axis-range blowout + plot-area fill | **not yet implemented** — see `Project Docs/Plans/qa-agent-consolidation.md` Phase 2 |
| V7 | Hover/datatip theme-mismatch | **not yet implemented** — Phase 2 |
| V8 | General DOM element overlap | **not yet implemented** — Phase 2 |

V6–V8 are reserved but not yet written. **Report them as `NOT RUN (not implemented)`** — never
as PASS. They cover real gaps (axis blowout, datatip theming, page-level overlap) that nothing
in V0–V5 detects, so silently omitting them would overstate coverage.

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

The JS snippets below are the specification of **what** to measure. Run the equivalent
measurement through whichever transport actually loads the page — they are plain expressions
returning JSON, so they run unchanged under either browser transport.

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

**Run V2–V5 in *each* pass.** Mobile reflow — collapsed legends, a much narrower plot area,
thinned ticks, stacked cards — routinely introduces overlap and edge-clipping that never
appears at desktop width, so the 390px pass is not optional. Tag every row in every table with
a **Viewport** column (`desktop` / `mobile`).

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

For each tab, activate the tab, then run:

```javascript
(function() {
  function ix(a, b) {
    var x = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
    var y = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    return x * y;
  }
  var results = [];
  document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
    if (el.offsetParent === null) return;            // skip charts on hidden tabs
    var id = el.id || 'unnamed';

    // 1. data-mark rects: scatter/box/bar points...
    var marks = [];
    el.querySelectorAll('.scatterlayer .point, .barlayer .point, .boxlayer .point, .violinlayer path.violin')
      .forEach(function(p) {
        var r = p.getBoundingClientRect();
        if (r.width || r.height) marks.push(r);
      });
    // ...plus points sampled along line traces
    el.querySelectorAll('.scatterlayer .js-line').forEach(function(path) {
      var L = path.getTotalLength ? path.getTotalLength() : 0;
      var m = path.getScreenCTM();
      if (!L || !m) return;
      var step = Math.max(6, L / 150);
      for (var d = 0; d <= L; d += step) {
        var pt = path.getPointAtLength(d);
        var sx = m.a * pt.x + m.c * pt.y + m.e;
        var sy = m.b * pt.x + m.d * pt.y + m.f;
        marks.push({left: sx - 2, right: sx + 2, top: sy - 2, bottom: sy + 2});
      }
    });

    // 2. label rects: legend + every annotation
    var labels = [];
    var lg = el.querySelector('.legend');
    if (lg) labels.push({kind: 'legend', r: lg.getBoundingClientRect()});
    el.querySelectorAll('.infolayer .annotation').forEach(function(a, i) {
      labels.push({
        kind: 'annotation[' + i + '] "' + a.textContent.trim().slice(0, 40) + '"',
        r: a.getBoundingClientRect()
      });
    });

    // 3. label-vs-data and label-vs-label intersections
    var labelData = [], labelLabel = [];
    labels.forEach(function(lab) {
      var hits = 0, px = 0;
      marks.forEach(function(mr) { var o = ix(lab.r, mr); if (o > 0) { hits++; px += o; } });
      if (hits > 0) labelData.push({label: lab.kind, marksHit: hits, overlapPx: Math.round(px)});
    });
    for (var i = 0; i < labels.length; i++)
      for (var j = i + 1; j < labels.length; j++) {
        var o = ix(labels[i].r, labels[j].r);
        if (o > 25) labelLabel.push({a: labels[i].kind, b: labels[j].kind, overlapPx: Math.round(o)});
      }

    results.push({
      id: id,
      labelData: labelData,
      labelLabel: labelLabel,
      status: (labelData.some(function(d) { return d.marksHit >= 3 || d.overlapPx > 200; })
               || labelLabel.length > 0) ? 'CHECK' : 'OK'
    });
  });
  return JSON.stringify(results, null, 2);
})()
```

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

```javascript
(function() {
  var out = [];
  document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
    if (el.offsetParent === null) return;                 // visible charts only
    var svg = el.querySelector('svg.main-svg'); if (!svg) return;
    var sv = svg.getBoundingClientRect();                 // the clip viewport
    el.querySelectorAll('.infolayer .annotation').forEach(function(a, i) {
      var t = a.querySelector('text');
      var txt = (t ? t.textContent : a.textContent).trim();
      var r = a.getBoundingClientRect(); if (!r.width && !r.height) return;
      var over = {left: Math.round(sv.left - r.left), right: Math.round(r.right - sv.right),
                  top: Math.round(sv.top - r.top),    bottom: Math.round(r.bottom - sv.bottom)};
      var sides = Object.keys(over).filter(function(k) { return over[k] > 2; }); // >2px = clipped
      if (sides.length) {
        var vl = Math.max(r.left, sv.left), vr = Math.min(r.right, sv.right),
            vt = Math.max(r.top, sv.top),   vb = Math.min(r.bottom, sv.bottom);
        var hidden = Math.round((1 - (Math.max(0, vr - vl) * Math.max(0, vb - vt)) /
                                 (r.width * r.height)) * 100);
        out.push({chart: el.id, ann: i, text: txt.slice(0, 45),
                  clippedSides: sides, overflowPx: over, hiddenPct: hidden});
      }
    });
  });
  return JSON.stringify({clippedCount: out.length, items: out}, null, 2);
})()
```

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

For each tab, activate the tab, wait ~1s for relayout, then run:

```javascript
(function() {
  var out = [];
  document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
    if (el.offsetParent === null) return;                 // visible charts only
    var svg = el.querySelector('svg.main-svg'); if (!svg) return;
    var card = el.closest('.card');                        // the chart's container
    var host = card || el.parentElement;
    var cs = getComputedStyle(host);
    var inner = host.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    var chartW = svg.getBoundingClientRect().width;
    var fill = inner > 0 ? +(chartW / inner * 100).toFixed(1) : null;
    out.push({chart: el.id, chartPx: Math.round(chartW), cardPx: Math.round(inner),
              fillPct: fill, status: (fill !== null && fill < 90) ? 'FAIL' : 'OK'});
  });
  return JSON.stringify(out, null, 2);
})()
```

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

```javascript
(function() {
  function lum(c) {
    var m = (c || '').match(/rgba?\(([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/);
    if (!m) return null;
    var f = [m[1], m[2], m[3]].map(function(v) {
      v = parseFloat(v) / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
  }
  function contrast(a, b) {
    var la = lum(a), lb = lum(b);
    if (la === null || lb === null) return null;
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }
  var pageBg = getComputedStyle(document.body).backgroundColor;
  var results = [];
  document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
    if (el.offsetParent === null) return;
    var bad = [];
    var groups = {
      tick: '.xtick text, .ytick text',
      axisTitle: '.g-xtitle text, .g-ytitle text, .g-x2title text, .g-y2title text',
      legend: '.legend text',
      annotation: '.infolayer .annotation text',
      colorbar: '.infolayer .cbaxis text, .infolayer [class*="colorbar"] text'
    };
    Object.keys(groups).forEach(function(kind) {
      el.querySelectorAll(groups[kind]).forEach(function(t) {
        var fill = getComputedStyle(t).fill;
        // annotations may sit on a bg pill — compare against the pill, not the page
        var bg = pageBg;
        if (kind === 'annotation') {
          var pill = t.closest('.annotation') &&
                     t.closest('.annotation').querySelector('rect.bg');
          var pf = pill ? getComputedStyle(pill).fill : null;
          if (pf && pf !== 'none' && !/rgba?\([^)]*,\s*0\)/.test(pf)) bg = pf;
        }
        var cr = contrast(fill, bg);
        if (cr !== null && cr < 3.0) {
          bad.push({kind: kind, fill: fill, contrast: +cr.toFixed(2),
                    sample: t.textContent.slice(0, 25)});
        }
      });
    });
    results.push({id: el.id, badCount: bad.length, worst: bad.slice(0, 5)});
  });
  return JSON.stringify(results, null, 2);
})()
```

3. Thresholds: contrast **< 2.0 = FAIL** (effectively invisible), **2.0–3.0 = WARN**.
   Note: semi-transparent pill backgrounds composite with the page, so computed contrast is
   approximate — confirm borderline cases on the screenshot before failing them.
4. Screenshot a chart-heavy tab in **both themes** at **each viewport** (4 shots), plus any
   failing tab. The caller names which tab and any target-specific elements to confirm.

**Caveat:** this is a *contrast* test, so it cannot detect a theme **mismatch** — light text on a
leftover dark pill in light mode scores high contrast and passes here. That failure is V7's job.

Report per theme: | Chart ID | Tab | Viewport | Theme | Worst contrast | Status |

---

## V6 — Axis-range blowout + plot-area fill

**NOT YET IMPLEMENTED** (Phase 2). Report as `NOT RUN (not implemented)`.

Will compare `el._fullLayout.xaxis.range` against the true data extent from `el.data` to catch
the autorange blowout documented in `CLAUDE.md` §"Plotly charts — mobile-safe authoring", where
data-coordinate-anchored chart chrome silently widens the axis and compresses the data into the
left portion of the card. Also plot-area-vs-figure margin ratio and a `showlegend` assertion.

## V7 — Hover/datatip theme-mismatch

**NOT YET IMPLEMENTED** (Phase 2). Report as `NOT RUN (not implemented)`.

Will hover data points programmatically and check `.hoverlayer .hovertext` background luminance
against the page background, catching dark-themed datatips surviving into light mode — which V5
cannot detect (see its caveat).

## V8 — General DOM element overlap

**NOT YET IMPLEMENTED** (Phase 2). Report as `NOT RUN (not implemented)`.

Will check bounding-box intersection across non-Plotly page chrome (cards, stat tiles, tab
strip, theme toggle, detail panel) plus a horizontal-overflow assertion. Everything in V0–V5 is
scoped to the inside of a chart's SVG; nothing currently checks the page itself.

---

## Reporting

Return a markdown checklist with PASS / FAIL / WARN / N/A per check. Cover **both viewports**
(desktop 1440 + mobile 390), with the **Viewport** column populated in every table.

**Open the visual section with the transport actually used and any resulting coverage loss.**
This is not optional — it is what keeps a thin run from reading like a clean one. Four shapes:

```
Transport: T2 (mobile_preview.py, Chromium 141, 390x844 @2x mobile-emulated)
           T1 unavailable (Preview MCP not provisioned in this environment)
Coverage:  V1-V5 full. V6-V8 not implemented.
```
```
Transport: T1 (Preview MCP, 390x844 resize-emulated) + T2 (geometry)
Coverage:  V1-V5 full.
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
