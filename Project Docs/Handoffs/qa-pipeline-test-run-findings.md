# QA Pipeline Test Run — Banked Findings

**Status:** BANKED — nothing in this file has been fixed. The user explicitly chose "bank the
report" over fixing anything now (2026-07-25). This file exists so the findings and their
context survive until that changes.

## Context

`Project Docs/Plans/qa-agent-consolidation.md` Phases 1–4 rebuilt the two dashboards' QA agents:
extracted a shared rendered-check suite (`.claude/qa-visual-suite.md`), added an
environment-adaptive browser transport (`tools/mobile_preview.py`, T1/T2/T3), added four new
checks (V6 axis-fill, V7 hover-theme, V8 dom-overlap, plus a V2 tick-collision extension), and
fixed a real bug the new checks found — `applyChartTheme()` was a complete no-op on both
dashboards (see `git log` on `nerd_common/theme.py` / `f8f2096`).

That work left three specific defects open, found and fixed manually during Phase 2/4
development:

1. White hover-tooltip pill in dark mode on two Strava histogram charts (V7)
2. 7 of 10 Strava exploratory-tab charts clipping annotation text at 390px (V3)
3. Theme-toggle buttons and the bottom-sheet close button under the 40px tap-target minimum (V8)

To validate the rebuilt pipeline — not just the individual checks in isolation — the user asked
to run `strava-qa` as a **blind test**: dispatched with no mention of the three known findings,
to see whether the suite surfaced them independently under real conditions (a CDN-blocked
container, cold agent, no prior context). Full agent-authored report is in the conversation
transcript preceding this file; this document distills it into actionable items.

## Test run result: the pipeline validated successfully

- **All three known findings were rediscovered independently**, each with photographic proof
  (forced-hover screenshot for V7, cut-off annotation text quoted verbatim for V3, exact pixel
  dimensions for V8).
- **The transport layer worked without hand-holding.** The agent hit `plotly-cdn-unreachable`,
  retried with `--offline-plotly` per V0's documented guidance, confirmed zero version drift,
  and got full V1–V8 coverage — the exact recovery path Phase 3 was built for, executed cold.
- **The suite's judgment caveats held.** The PCA-biplot leader-line false positive
  (`chart-x-archetypes`) was correctly recognized, re-run markers-only, and passed — not just
  detected, *correctly dismissed*. Grazing overlaps on three other charts were judged PASS per
  the suite's own grazing rule rather than over-flagged.
- **It found more than it was asked to confirm** — two bugs in the QA scripts themselves and one
  previously-unknown, systemic dashboard defect. That is the substance of this handoff.

Nothing below was expected going in except items 4, 6 (partial), and 7. Items 1, 2, 3, 5 are new.

---

## A. QA-suite bugs (fix in `tools/qa-checks/`, no dashboard changes)

These are bugs in the check scripts written during Phase 2, not dashboard defects. Fixing them
doesn't change any chart output — only what the suite is capable of reporting correctly.

### A1. `axis-fill.js` misjudges multi-subplot charts

**File:** `tools/qa-checks/axis-fill.js`
**Found on:** `chart-x-metronome` (`strava-data/dashboard/charts_exploratory.py`) — a two-subplot
figure with separate `xaxis` (run pace) and `xaxis2` (MTB speed) domains.

**Problem:** the script reads only `fl.xaxis` for the range, but pools x-values from **every**
trace on the chart — including traces that belong to `xaxis2` — when computing the "true" data
extent. For a dual-subplot chart this compares the first subplot's range against the *combined*
data range of both subplots, producing a spurious result (observed: `dataFillFrac: 1.063`,
which reads as inconsistent — axis narrower than the data it supposedly bounds).

**Verified by hand it's a false alarm, not a real bug:** `xaxis` range `[5.4, 19.4]` vs its own
trace data `[5.43, 19.27]` (pad 6%/6%, fine); `xaxis2` range `[4, 11]` vs its own trace data
`[4.39, 10.56]` (pad 6%/7%, fine). Both real axes are correctly ranged.

**Fix:** scope data-extent collection per-trace by that trace's `xaxis` property (`"x"`/`"x2"`
maps to `fl.xaxis`/`fl.xaxis2`) instead of pooling all traces against a single axis object. Loop
over `Object.keys(fl)` matching `/^xaxis\d*$/` the way `applyChartTheme()` already does in both
`template.py` files, and evaluate each subplot's axis against only its own traces' data.

**Risk of not fixing:** low today (one chart), but any future multi-axis/subplot chart on either
dashboard will get a wrong V6 verdict — most likely a false FAIL that has to be manually
dismissed, same as this run did.

### A2. `label-overlap.js` has no axis-title-vs-legend check

**File:** `tools/qa-checks/label-overlap.js`
**Found via:** manual bounding-box measurement during the test run (not by the script itself —
this is a **coverage gap**, not a wrong verdict).

**Problem:** the script's label set is `.legend` + `.infolayer .annotation` (see the V2 section
of `.claude/qa-visual-suite.md`). It does not include `.g-xtitle`/`.g-ytitle`, so it cannot
detect an axis title colliding with the legend — which is exactly finding B3 below.

**Fix:** add axis-title elements to the existing `labels` array (same pattern already used for
annotations), so title-vs-legend and title-vs-data intersections are caught by the existing
intersection logic without new code paths. Mind the same false-positive traps V2 already guards
against (leader lines, rotated text) don't apply here since titles aren't rotated or
connector-anchored — this addition should be lower-risk than the tick-collision work in V2 was.

**Note on sequencing:** fixing this makes finding B3 (below) auto-detectable by the suite going
forward, which is the reason to do A2 before deciding whether/how to fix B3 in the dashboard —
otherwise a dashboard fix for B3 has no regression check.

---

## B. Strava dashboard defects (require `dash-developer` + the real QA/review gate)

These change chart output, so per `AGENTS.md`'s least-privilege rule they should go through the
actual Build stage (`dash-developer` edits, `strava-qa` re-validates, `/code-review` gates) —
not be patched ad hoc. Ranked by the test run's own severity ordering.

### B1. [Known, severity 1] 7 of 10 exploratory-tab charts clip annotation text at 390px

**Charts:** `chart-x-mirage`, `chart-x-heat`, `chart-x-seasonal`, `chart-x-cadence`,
`chart-x-heatsun` (both sides), `chart-x-heatverdict`. Only `chart-x-archetypes`,
`chart-x-metronome`, `chart-x-load` clip nothing. Zero clipping on any Trends-tab chart, and zero
at desktop width — mobile-only.
**File:** `strava-data/dashboard/charts_exploratory.py`
**Symptom (verbatim quotes from the clipped text, captured by the test run):** "Raw" invisibly
clipped from "Raw r=-0.195, p=0.008…" (`chart-x-mirage`, 8% hidden); bottom stat line reading
"...t=-0.27," with its closing clause cut off (`chart-x-heat`, 36% hidden — the worst case);
"MTB blackout - 3 July ride[s]" cut mid-word (`chart-x-seasonal`, 6%); top r/p annotation running
off the right edge (`chart-x-cadence`, 10%); bottom R² annotation colliding with the "11:00"
y-tick and a separate top annotation cut mid-word "elevati[on]" (`chart-x-heatsun`, 22% + 16%,
two independent clips on one chart); "Running" prefix missing from "Running: Combined wins…"
(`chart-x-heatverdict`, 14%).
**Likely cause (per `CLAUDE.md`'s documented pattern):** stat-annotation text sized/positioned
for desktop margins that don't scale down at 390px. Notably the two most recently added charts
per the page's own "About this section" copy (Heat & Sun / `heatsun`, and The Verdict /
`heatverdict`) both clip — consistent with not having gone through a mobile-safety pass.
**Fix direction:** deepen `margin.l`/`margin.r` on mobile for these charts, or shrink/wrap the
annotation font below a width breakpoint, per the "Plotly charts — mobile-safe authoring"
section of `CLAUDE.md`. Re-run V3 until `clippedCount: 0` at 390px on all 10 exploratory charts.

### B2. [Known, partially] `chart-x-metronome` tick collisions + missing from `DENSE`

**File:** `strava-data/dashboard/template.py:1329-1335` (the `DENSE` array)
**Symptom:** at 390px, `chart-x-metronome`'s rotated pace-axis tick labels ("6:00"…"14:00")
overlap each other (measured gap 7.8px vs 11.5px needed, 32% short) to the point of being an
illegible mush (screenshotted). Two of its stat annotations also render literally interleaved.
**Root cause:** `DENSE` (the mobile tick-thinning list, quoted below) only lists 6 ids, all from
the Trends/Volume tabs — none of the 10 `chart-x-*` Exploratory ids are in it, so
`thinTicks()`'s mobile pass never runs on any Exploratory chart, `chart-x-metronome` included:

```js
var DENSE = [
  {id: 'chart-volume', dual: false},
  {id: 'chart-elevation', dual: false},   // <- stale id, see B7
  {id: 'chart-hr', dual: false},
  {id: 'chart-pace', dual: true},
  {id: 'chart-run-pace-hr', dual: false},
  {id: 'chart-run-hr-temp', dual: false}
];
```
**Fix direction:** add `{id: 'chart-x-metronome', dual: false}` (and audit whether any other
Exploratory chart has the same dense-tick problem at 390px — this run only deep-dove
`chart-x-metronome`). The interleaved-annotation half of this finding is a separate layout issue
like B1, likely fixed by the same margin/annotation-sizing work.

### B3. [New] Systemic axis-title/legend collision at mobile — not yet auto-detected

**Found via:** manual bounding-box measurement in the test run (see A2 — the suite can't catch
this yet). **This is the most consequential new finding** because of its breadth.
**Symptom:** at 390px, the x-axis title collides with the legend on effectively every chart with
a below-plot legend. **Zero occurrences at desktop on the same charts.** Measured overlap
(px²), most severe first: `chart-x-archetypes` 1969, `chart-x-heatverdict` 1591, `chart-hr` 472,
`chart-x-mirage`/`chart-x-seasonal` 431 each, `chart-pace` 318, `chart-run-seg-pace-tort` 232,
`chart-run-pace-hr` 172, `chart-run-hr-temp` 138, `chart-run-seg-grade`/`hr-grade` 146 each,
`chart-mtb-seg-pace-tort`/`grade`/`hr-grade` 70 each, plus `chart-elev` (Volume tab, confirmed
visually: "Week" label overlapping the "Other" legend swatch). At least 15 charts across
Exploratory, Trends, and Volume.
**Root cause:** the legend wraps to multiple rows at 390px width (it doesn't at 1440px), but the
axis title's vertical offset is a fixed value tuned for a single-row desktop legend — so at
mobile width the title lands inside the now-taller legend block instead of below it.
**Fix direction:** push `margin.b` down dynamically based on legend row count at render time, or
reposition the axis title above the legend rather than relying on a fixed offset — both are
`nerd_common/theme.py` / `template.py` changes since the behavior is shared across this many
charts, not a per-chart fix. **Do A2 first** so this has an automated regression check before a
fix is attempted, otherwise there's no way to confirm all ~15 charts are actually clear.

### B4. [Known] White hover-tooltip pill in dark mode

**Charts:** `chart-x-cardiac`, `chart-x-metronome` (confirmed both viewports)
**Symptom:** hovering a data point in dark mode shows a stark white tooltip pill with teal text
on an otherwise near-black chart — `applyChartTheme()` is not restyling `hoverlabel` for these
two. Confirmed pre-existing (not a Phase 4 regression) by testing before/after that fix.
**Suspected common thread:** both are **histogram**-type traces; other Exploratory charts
(scatter/violin/bar) retint correctly. Worth checking whether Plotly derives histogram hover
styling from the trace rather than the layout (the same category of issue Strava's own
`rangeslider-bg` / annotation-pill CSS-override comments in `template.py:565-591` already
document for a different reason — the JS `Plotly.relayout` retint losing a race against Plotly's
own redraw).
**Fix direction:** either extend `applyChartTheme()`'s relayout call to explicitly target
`data[i].hoverlabel` on histogram traces, or — if the CSS-override root cause applies here too —
add a CSS rule alongside the existing `.rangeslider-bg` / `.annotation .bg` overrides in
`template.py` rather than fighting the relayout race again.

### B5. [New] `chart-x-cadence` plot area under-filled at mobile

**File:** `strava-data/dashboard/charts_exploratory.py` (V6 WARN, threshold 0.55 calibrated in
Phase 2 — this chart measured 0.506, just below it)
**Symptom:** at 390px the plot area is only 51% of figure width; margins measured `l=68 r=86`.
**Likely cause:** the chart has a colorbar (per its "Avg HR" right-axis in the exploratory spec)
whose fixed `margin.r` is too wide for mobile — the same colorbar also implicated in the
`chart-x-cadence` V2 collision (annotation overlapping the "Avg HR" colorbar title, same run).
**Fix direction:** `automargin=True` on the colorbar/right axis so it sizes to content instead of
a fixed margin, per the suggested fix already documented in `.claude/qa-visual-suite.md`'s V6
section.

### B6. [Known] Tap targets under 40px — likely affects BOTH dashboards, not just Strava

**Found:** theme-toggle buttons at 36×36 (explicit `.theme-toggle button { width: 36px; height:
36px; }` inside a `@media (max-width:640px)` block); the bottom-sheet close button at 37×30.
**Important scope correction to the original finding:** the 36×36 theme-toggle rule exists
**verbatim in both** `strava-data/dashboard/template.py:605` and
`running-log/dashboard/template.py:912` — same selector, same media query, same values. This
was only exercised on Strava in this test run, but it is very likely present on the Running Log
dashboard too and should be checked/fixed in both places together, not just Strava's.
**Fix direction:** bump both rules to `40px` in their respective `@media (max-width:640px)`
blocks; separately size the bottom-sheet close button to at least 40×40 (currently 37×30, so
both dimensions need adjusting, not just height).

### B7. [New, trivial] Stale `DENSE` list id

**File:** `strava-data/dashboard/template.py:1331`
**Symptom:** `DENSE` references `chart-elevation`; the actual div id (per
`strava-data/dashboard/page.py:417,623`) is `chart-elev`. `document.getElementById` silently
returns `null` for the stale id and the guard on the next line (`if (!el || !el._fullLayout)
return;`) no-ops it away — currently harmless because `chart-elev`'s tick count happens to be
low enough not to need thinning, but it means this chart has *never* actually received mobile
tick-thinning despite appearing to be configured for it.
**Fix:** change `'chart-elevation'` to `'chart-elev'` on line 1331. Trivial, bundle with B2.

---

## Decisions made

- **Bank, don't fix.** Presented with "fix QA suite only" / "fix everything now" / "bank the
  report," the user chose to bank. Nothing above has been touched.
- **QA-suite bugs (A) are cheap, contained, and don't need the full pipeline** — they're
  tooling-only changes to `tools/qa-checks/*.js` with no dashboard/chart impact, so they don't
  need `dash-developer` or a review gate the way the dashboard fixes (B) do.
- **Dashboard fixes (B) should go through the real pipeline**, not ad hoc edits, per `AGENTS.md`'s
  least-privilege rule (only `dash-developer` edits build code; QA agents run but don't edit).
- **B3 depends on A2.** Fixing the dashboard's axis-title/legend collision without first patching
  `label-overlap.js` to detect it leaves no automated way to confirm the fix actually worked
  across all ~15 affected charts.
- **B6's scope was corrected** during this write-up: the same 36×36 rule exists in both
  dashboards' `template.py`, so treat it as a two-dashboard fix even though it was only observed
  via the Strava test run.

## Next steps (suggested order, not mandatory)

1. Fix A1 and A2 in `tools/qa-checks/`. Verify A1 against `chart-x-metronome` (should report both
   subplot axes OK, no false blowout). Verify A2 by re-running `label-overlap.js` against the
   current (unfixed) dashboard and confirming it now reports the B3 collisions on its own.
2. Decide whether to fix B1–B7 via a real `/dashboard strava-data` pipeline run (Build →
   `strava-qa` → review gate) or a smaller targeted session. B1, B2, B3, B5 are all
   `charts_exploratory.py`/`template.py` mobile-layout work and could reasonably be one batch;
   B4 (histogram hover) may need separate investigation into Plotly's hover-styling precedence;
   B6 touches both dashboards; B7 is a one-line bundle-in with B2.
3. Re-run `strava-qa` (and, if B6 is fixed in both places, `running-log-qa`) after any dashboard
   fix to confirm clean, using the shared suite as the regression check.

## Prompt to get started next time

```
Read Project Docs/Handoffs/qa-pipeline-test-run-findings.md in full. It documents 7 banked
findings from a blind test run of the strava-qa agent (2 QA-script bugs in tools/qa-checks/,
5 Strava dashboard defects — one of which likely also affects running-log).

Start with section A (the QA-script bugs): fix axis-fill.js's multi-subplot blind spot and
add an axis-title-vs-legend check to label-overlap.js, exactly as each finding's "Fix"
paragraph describes. These are tools-only changes — no dashboard code, no pipeline agents
needed. Verify A1 against chart-x-metronome and A2 by re-running the check against the
current dashboard build to confirm it now catches the B3 collisions on its own.

Then tell me what you found and ask how I want to handle section B (the dashboard defects)
before touching any dashboard code — B3 depends on A2 being done first, and B6 needs
checking against both dashboards' template.py, not just Strava's.
```
