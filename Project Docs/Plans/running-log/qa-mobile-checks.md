# Mobile-aware QA for the Running Log dashboard

**Status:** Planned
**Scope:** Add a rendered, assertable mobile-checking pass to the Running Log QA
**Effort:** ~½–1 day, phased (each phase lands independently)

## Context

The Performance-section redesign (Jul 2026) shipped three separate mobile-only
rendering bugs that all reached the user before being caught — a pace chart whose
x-axis silently autoranged to ~2010 (data crushed into the left 60% of the card), a
legend that didn't render on mobile, and edge-clipped labels. The same axis-blowout
root cause had already bitten the Strava dashboard three times in June. See
[CLAUDE.md](../../../CLAUDE.md) §"Plotly charts — mobile-safe authoring".

Why the existing QA didn't catch them:

- **`running-log/qa.py` is purely static** — it reads `index.html`/CSV as text and
  greps. It can confirm a chart `<div>` exists but can't see rendered geometry (axis
  range, legend visibility, overflow), so none of these bugs were visible to it.
- **The `running-log-qa` agent** (`.claude/agents/running-log-qa.md`) *does* have good
  rendered checks (§3.5 overlap, §3.5b edge-clipping, §3.6 contrast) — but they run
  through `mcp__Claude_Preview__*`, which **can't reach a local server on this machine**
  (it lands on `chrome-error://`; this is exactly why `tools/mobile_preview.py` exists).
  So that logic is effectively unusable locally, and it never covered the axis-blowout
  or legend-hidden failures anyway.
- **Screenshots miss this class of bug** — a blown-out axis or missing legend reads as
  merely "a bit compressed" / "not rendering"; both bugs were only pinned down by
  reading `el._fullLayout.xaxis.range` / `.showlegend` directly.

**Goal:** give the Running Log QA a rendered, *assertable* mobile pass that catches
these failures automatically, reusing the working `tools/mobile_preview.py` engine.

## Architecture decision

- **Add an opt-in `--mobile` flag to `running-log/qa.py`.** The default run stays
  static, stdlib-only, and fast; `--mobile` **lazily** imports Playwright and runs the
  rendered pass. If Playwright or the plotly CDN is unreachable, it prints a clear
  `SKIP: mobile checks unavailable (<reason>)` and does **not** fail — a distinct state,
  not a FAIL. (A sibling `qa_mobile.py` is the alternative; the flag keeps a single QA
  entry point, matching the intent to "update the QA script".)
- **Never add the mobile pass to CI.** `deploy.yml` only builds and runs
  `uv sync --no-dev` specifically to skip Playwright (a dev dependency); the `qa.py`
  line there is a path-trigger, not a run step. The mobile pass is a **local/dev + agent**
  tool only.
- **Reuse, don't duplicate, the browser engine.** Refactor `tools/mobile_preview.py`'s
  `_free_port`, `_serve`, the Chromium launch, and `MEASURE_JS` into importable helpers
  (e.g. `tools/preview_harness.py`) so both the existing CLI diagnostic and
  `qa.py --mobile` share one implementation. Keep the `mobile_preview.py` CLI intact.

## What the rendered pass does

Start the in-process `127.0.0.1` server on `running-log/`, launch a mobile-emulated
Chromium at **375×812**, load `index.html`, then for each of the 6 tabs (**overview,
volume, mix, performance, races, patterns**): activate the view (URL `#<view>` or click
`.tab[data-view="<view>"]`), wait out the ~150 ms debounced relayout + any
`window.__applyMobile()`, and run the checks against each **visible** chart
(`el.offsetParent !== null` — hidden-tab charts report `clientWidth: 0`, so they must be
activated before measuring).

**Per-chart expectations manifest** — add near `CHART_IDS` in `qa.py`, since donuts /
sparklines / heatmaps have no cartesian axis or legend and should be exempt from those
checks:

```python
MOBILE_CHART_SPECS = {
  "chart-pace-timeline":   {"tab": "performance", "axis": "time",     "legend": True},
  "chart-pr-800m":         {"tab": "performance", "axis": "time",     "legend": False},
  "chart-monthly-by-year": {"tab": "volume",      "axis": "category", "legend": False},
  "chart-donut":           {"tab": "mix",         "axis": None,       "legend": False},  # overflow-only
  # ... spark-* / heatmap → overflow-only or excluded
}
```

## Checks, by phase (stop after any phase)

### Phase 1 — the checks screenshots miss (highest value; catches this session's bugs)

1. **Renders** — `el._fullLayout` present and no console errors for the chart (build/JS breakage).
2. **No horizontal overflow** — from `MEASURE_JS`: `overflowPx <= 2` and `fillRatio` in
   ~[0.9, 1.02] (chart fills its card, doesn't spill past `.card{overflow:hidden}`). All charts.
3. **Axis range not blown out** *(the headline check)* — for `axis: "time" | "category"`,
   compute the actual data extent from `el.data` (min/max plotted x) and FAIL if
   `_fullLayout.xaxis.range` extends beyond it by more than a tolerance (time: end ≤ ~2 months
   past the last point, or ≤ ~10–15% padding; category: within `[-0.5, ncats-0.5] ± ε`). This is
   the annotation-autorange bug that recurred 4×.
4. **Legend present where expected** — for `legend: True`, assert `_fullLayout.showlegend === true`,
   a `.legend` node exists, and it sits inside `svg.main-svg` (not clipped). Catches stale-JS
   hiding and small-plot suppression.

### Phase 2 — port the agent's rendered logic into the runnable harness

5. **Label overlap** — lift `running-log-qa.md` §3.5 `eval` (label-vs-data + label-vs-label
   intersection) verbatim; FAIL on `marksHit ≥ 3 || overlapPx > 200` or any label-label overlap
   (keep its leader-line false-positive caveat → WARN needing a screenshot).
6. **Edge clipping** — lift §3.5b (annotation bbox vs `svg.main-svg`, >2 px = clipped); any clip = FAIL.

### Phase 3 — stretch

7. **Theme contrast at mobile width** — port §3.6 contrast audit; toggle
   `.theme-toggle button[data-theme="dark"]`, run in both themes; contrast <2.0 = FAIL, 2.0–3.0 = WARN.
8. **Rewire the agent** — update `.claude/agents/running-log-qa.md` to drive automated
   measurements through `qa.py --mobile` (the transport that works here) and screenshots via
   `tools/mobile_preview.py`, instead of the non-functional Preview-MCP `preview_eval` calls.

## Files

- **`running-log/qa.py`** — `--mobile` flag + lazy Playwright import + graceful SKIP;
  `MOBILE_CHART_SPECS` manifest; new check functions; extend the runner/reporter to print a
  mobile section and exit non-zero on FAIL.
- **`tools/preview_harness.py`** (new) — engine extracted from `tools/mobile_preview.py`
  (`_serve`, `_free_port`, Chromium launch, `MEASURE_JS`, a tab-activation helper);
  `mobile_preview.py` imports from it.
- **`.claude/agents/running-log-qa.md`** — Phase 3 only.

## Verification

1. **Green baseline:** `uv run python "running-log/qa.py" --mobile` on the current build → all PASS.
2. **Bug-injection regression (the important one — proves the checks actually bite):**
   - Remove `range=_PR_X_RANGE` from `chart_pace_timeline` → rebuild → `--mobile` must FAIL the
     axis-blowout check on `chart-pace-timeline`. Revert.
   - Re-add the old `template.py` `simplify()` line that hid the pace legend on mobile → rebuild →
     must FAIL the legend-present check. Revert.
3. **Graceful skip:** in an env without Playwright/CDN → prints `SKIP`, exits 0; the static suite
   still runs and passes.
4. **CI untouched:** `deploy.yml` still runs `uv sync --no-dev`; the mobile pass is never invoked there.

## Model & effort per phase

| Phase | Model | Effort | Rationale |
|---|---|---|---|
| P1 (harness refactor + 4 checks + manifest + bug-injection verify) | Sonnet 5 | medium | Mechanical, well-specified; the manifest + tolerances need one tuning pass |
| P2 (port overlap + edge-clipping) | Sonnet 5 | low–med | Lift existing agent `eval` snippets into the harness |
| P3 (contrast + agent rewire) | Sonnet 5 / Opus | med | Contrast port + agent-prompt judgment |

## Related docs

- [Performance Section Redesign](performance-section-redesign.md) — the source of the bugs these checks target
- [Mobile Redesign Plan](../mobile-redesign-plan.md) — the intended mobile UX
- [CLAUDE.md](../../../CLAUDE.md) §"Plotly charts — mobile-safe authoring" — the rules these checks enforce
- `.claude/agents/running-log-qa.md` — the visual-QA agent whose logic Phase 2/3 reuse
- `tools/mobile_preview.py` — the working local browser-measurement engine
