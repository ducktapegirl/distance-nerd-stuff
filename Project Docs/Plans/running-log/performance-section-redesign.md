# Performance Section Redesign — Running Log Dashboard

**Status:** Planned
**Scope:** Visual improvements to race-performance storytelling
**Effort:** ~2–3 hours implementation + iteration + QA
**Branch:** `feature/performance-section-redesign`

## Problem Statement

The Performance section of the Running Log dashboard (99 races, 2003–2007) has three visual problems that muddy the story:

1. **Combined "Race Pace Over Time" chart is noisy**: 7 color buckets + 3 marker shapes + 7-item legend + 7 dotted "season-best" trend lines that zigzag across each other with little signal.
2. **Season-best trend lines are uninformative**: They connect each season's single fastest race chronologically, producing crossing noise rather than trend.
3. **Per-distance PR charts are inconsistent**: Y-tick spacing is adapted per chart (5s/10s/30s at `charts.py:270-283`), so 5k Track shows 10s ticks while 5k XC shows 30s; x-ranges also differ, breaking the small-multiples pattern.

Research basis (small-multiples best practices):
- Consistent axis scales enable fair comparison across charts ([Inforiver](https://inforiver.com/insights/managing-chart-axis-scaling-in-small-multiples/), [XD.gov data standards](https://xdgov.github.io/data-design-standards/components/small-multiples/))
- Multi-line charts degrade past ~4–5 series ([Domo](https://www.domo.com/learn/charts/multi-line-chart))
- Truncated y-axes are acceptable for race times *if* the scaling rule is consistent and visible
- Prefer direct labels over long legends

## Definition of Done

The Performance section is done when all of the following hold simultaneously:

- Combined pace chart shows exactly 3 event-group colors, no dotted trend lines, direct labels (no legend).
- All 5 per-distance PR-progression charts share the rounded-range/~5-tick policy, the 5k Track + 5k XC pair share an identical y-range/step, and all 5 share the Jul 2003–Jul 2007 x-window.
- Two new charts (`chart_season_best_slope`, `chart_pr_timeline`) are built, correctly exclude relay races, and gap (not interpolate or drop) any (distance bucket, season) pair with zero qualifying races.
- `section_performance` renders charts in the order: PR cards → combined pace chart → season-best slope → PR timeline strip → 5 per-distance PR charts.
- `uv run python "running-log/qa.py"` passes with expectations updated to match the new chart set.
- `tools/mobile_preview.py` runs successfully (no hard-coded Linux path) and visual checks pass on desktop + mobile, light + dark.
- No gitignored HTML output is committed — only source changes (`dashboard/*.py`, `visualize_log.py`, `qa.py`, `tools/mobile_preview.py`) are on the branch.

## Resolved ambiguities

- **Relay exclusion**: Relays are excluded from PR determination everywhere in this section — both `chart_season_best_slope`'s "fastest non-relay race time per bucket+season" and `chart_pr_timeline`'s cumulative-PR rows exclude relay races.
- **Empty season/bucket pairs**: If a (distance bucket, season) pair has no qualifying races, gap the line for that bucket at that season (skip the point; do not interpolate or carry the prior value forward).

## Approved Changes

### 1. Combined chart — `chart_pace_timeline` (charts.py:351-409)

**Simplify in place** (keep min/mi pace axis):
- Remove the 7 dotted season-best trend lines (delete `_pace_trendlines` helper).
- Regroup 7 buckets → 3 event-group colors:
  - Middle distance (800m, Mile, 1500m) → teal `EASY`
  - 3k / steeple (3k, 3k steeple) → violet `LONG`
  - 5k / 6k (5k, 6k) → coral `RACE`
- Replace the 7-item legend with direct labels (one per group, anchored at right edge near group's last point).
- Raise non-PR marker opacity from fully opaque → ~0.55 to reduce clutter; PR stars and relay diamonds unchanged.
- Update section caption: remove "dotted line = season-best trend".

**Result:** ~3 colors instead of 7, no overlapping trend lines, one honest comparison.

### 2. Per-distance PR charts — `chart_pr_progression` (charts.py:219-285)

**Replace adaptive tick logic with a rounded-range, ~5-tick policy:**
- Compute data min/max, pick step from `{5, 10, 15, 20, 30, 60}` s that yields 4–6 ticks after rounding range outward to step multiples.
- Range = rounded boundaries; keep all ticks (don't drop boundary labels — they're now clean M:SS values).
- Keep faster-up orientation via explicit reversed `range=[hi, lo]`.
- **5k shared axis**: Mark both 5k Track + 5k XC with `axis_group="5k"` in `PR_PROGRESSION_SPECS`. Compute union min/max so both get identical range and step.
- **Unified x-axis**: All charts get `range=["2003-07-01", "2007-07-31"]`, `dtick="M6"`, `tickformat="%b %Y"`.
- Raise non-PR race opacity 0.35 → ~0.55.
- **Keep** the regression line (user's choice) and PR stars unchanged.

**Result:** Small multiples work as a set; 5k Track and 5k XC are directly comparable; all five charts show 4–6 clean ticks at consistent M:SS intervals.

### 3. New enrichment charts

#### `chart_season_best_slope` — "Did I get faster each year?"
Removes race-to-race noise, shows seasonal improvement without clutter.
- One point per (distance bucket, season): fastest non-relay race time for that bucket+season. If a bucket has no qualifying race in a given season, gap the line at that point (no interpolation).
- Seasons on x-axis (categorical: Fall 2003, Winter 2003, Spring 2004, … Spring 2007); y = **% behind eventual PR** (0% = PR, axis reversed so faster is up).
- One line+markers per bucket, colored by 3 event groups; direct-labeled lines at right edge.
- Height ~300px.

**Why:** Answers the question "did I improve year-over-year?" more clearly than a scatter of 99 individual races.

#### `chart_pr_timeline` — "When did breakthroughs happen?"
A horizontal strip showing when each PR fell.
- x = same 2003-07→2007-07 date range; y = one categorical row per PR-card distance (800m, Mile, 1500m, 3k Steeple, 5k Track, 5k XC, 6k XC).
- A star marker at each cumulative-PR date (every non-relay race that beat the prior best), with hover = date, time, race name.
- Row color = event group.
- Height ~240px.

**Why:** Reveals whether breakthroughs clustered in certain seasons (e.g. a cohort of PRs in Fall 2005) or were steady throughout.

### Section layout (`section_performance`, sections.py:127-154)

New order:
1. PR cards grid (unchanged)
2. Simplified combined pace chart
3. **NEW:** Season-best slope chart
4. **NEW:** PR timeline strip
5. Five per-distance PR-progression charts (with improved axes)

## Implementation Milestones

Ordered by dependency. Each milestone ends with its own test point — don't proceed to the next until the current one's test point passes. This catches drift early instead of only at the final verification pass.

**M0 — Fix `tools/mobile_preview.py` (prerequisite)**
- Remove hard-coded Linux chromium path (`/opt/pw-browsers/chromium`); use Playwright default or fallback.
- *Test point:* `uv run python tools/mobile_preview.py` runs against the current (pre-redesign) build without crashing on browser launch.
- *Why first:* every later visual-check test point depends on this working.

**M1 — Add 3-color event-group tokens to `config.py`**
- Add/confirm mapping: Middle distance → `EASY`, 3k/steeple → `LONG`, 5k/6k → `RACE`.
- *Test point:* tokens importable from `charts.py`; no build needed yet.

**M2 — Rewrite `chart_pace_timeline` (charts.py:351-409)**
- Depends on M1.
- *Test point:* `uv run python "running-log/visualize_log.py"` builds cleanly; visually confirm 3 colors, no trend lines, direct labels (via M0's mobile_preview).

**M3 — Rewrite `chart_pr_progression` axis logic (charts.py:219-285)**
- Independent of M2; can be done in either order relative to it.
- *Test point:* build cleanly; confirm each of the 5 charts shows 4–6 ticks at round M:SS values, 5k Track/XC share identical range/step, all 5 share the Jul 2003–Jul 2007 x-window.

**M4 — Add `chart_season_best_slope`**
- Depends on M1 (color tokens). Independent of M2/M3.
- Apply resolved ambiguities: exclude relays, gap empty season/bucket points.
- *Test point:* build cleanly; spot-check at least one known-empty (bucket, season) pair renders as a gap, not an interpolated point.

**M5 — Add `chart_pr_timeline`**
- Depends on M1. Independent of M2/M3/M4.
- Apply resolved ambiguity: exclude relays from cumulative-PR rows.
- *Test point:* build cleanly; hover on a star marker shows date/time/race name; row colors match event groups.

**M6 — Reorder `section_performance` (sections.py:127-154)**
- Depends on M2, M3, M4, M5 all existing.
- *Test point:* build cleanly; confirm chart order matches Definition of Done.

**M7 — Update `qa.py` expectations**
- Depends on M2–M6 (needs final chart-id/trace-count shape).
- Update chart-id/trace-count assertions to match the new chart set (2 removed trend-line traces, 2 new charts added, updated tick/range assertions for PR-progression charts).
- *Test point:* `uv run python "running-log/qa.py"` passes.

**M8 — Full verification pass**
- Run the Verification checklist below in full (build, qa.py, visual checks on desktop/mobile/light/dark).
- *Test point:* every item in the Verification checklist is checked off.

## Design conventions to respect

- Call `tidy_dark(fig)` first; per-chart axis overrides **after**.
- Use only stdlib + plotly + numpy; no pandas.
- Colors only from existing `config.py` tokens (so light/dark theme JS keeps working).
- Format time values with `fmt_time` / `fmt_pace` (M:SS).

## Verification checklist

1. **Build cleanly**: `uv run python "running-log/visualize_log.py"` → `running-log/index.html` builds, race counts unchanged (XC=31, Indoor=29, Outdoor=39).
2. **Regression suite**: `uv run python "running-log/qa.py"` passes (expectations updated per M7).
3. **Visual checks** (via the (fixed) `tools/mobile_preview.py`, run un-sandboxed):
   - No season-best dotted lines on combined chart ✓
   - ≤3 colors + direct labels on combined chart ✓
   - Every per-distance chart has 4–6 y-ticks at round M:SS values ✓
   - 5k Track and 5k XC show **identical** y-ranges/steps ✓
   - All five share Jul 2003–Jul 2007 x-window ✓
   - New charts render with no label overlap ✓
   - Empty (bucket, season) pairs render as gaps, not interpolated points ✓
   - Relay races excluded from both new charts' PR determination ✓
   - Light theme toggle works; all new colors are theme-aware ✓
4. **No gitignored output committed**: Only source changes on the branch.

## Model & effort per phase

| Phase | Model | Effort | Rationale |
|---|---|---|---|
| Implementation (charts, sections, config, qa, mobile_preview fix) | Sonnet 5 | medium | Well-specified mechanical edits |
| Visual iteration (screenshot → adjust ranges, labels, opacity) | Fable / Opus | medium | Visual-design judgment needed |
| QA (qa.py, both themes, mobile) | Sonnet 5 | low-medium | Checklist-driven |
| Code review | default | low | Small, contained diff |

## Related docs
- [Session Handoff — Running Log Dashboard](../Handoffs/running-log/session-handoff.md)
- [Design Handoff — Running Log](../Specs/running-log/design_handoff_running_log/readme.md)
- [CLAUDE.md — Running Log Architecture](../../CLAUDE.md)
