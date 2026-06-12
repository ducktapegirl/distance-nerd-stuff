# Running Log Redesign — Session Handoff
_Written: 2026-05-10; updated 2026-05-10 evening session_

## Branch
`running-log-redesign` — pushed to `origin`, tracking set up.
Open a PR: <https://github.com/ducktapegirl/experiments-in-mcp/pull/new/running-log-redesign>

Latest commit: `57d2e8d` — "Restore cross-chart date sync, add click-to-detail panel, fix PR grid"

## Goal
Replace the old Plotly dashboard with the dark glass / top-tab design from
`Claude Design/design_handoff_running_log/`. See that folder's `README.md` for
the full design spec — colors, type scale, components.

## Pipeline
```
source/*.html  →  src/parse_log.py  →  running_log.csv
running_log.csv  →  src/visualize_log.py  →  index.html
```

Regenerate dashboard:
```bash
cd "Running Log"
C:\Users\Alisha\Anaconda3\python.exe src/visualize_log.py
start "" index.html
```

Note: `python` resolves to Anaconda2 (Python 2) on this machine — always use the full Anaconda3 path above.

If you change the parser, regenerate CSV first:
```bash
C:\Users\Alisha\Anaconda3\python.exe src/parse_log.py
```

## What's done in this branch
| Item | Status |
|------|--------|
| New branch off `main` | ✅ |
| `parse_log.py` strips date ordinals (`th`/`st`/`nd`/`rd`) | ✅ |
| `running_log.csv` regenerated — race names clean | ✅ |
| `visualize_log.py` rewritten end-to-end | ✅ |
| Six section views (Overview / Volume / Workout Mix / Performance / Races / Patterns) | ✅ |
| Race classification: 31 XC / 29 Indoor / 39 Outdoor (Mud Run omitted) | ✅ |
| 7 PR cards: 800m / Mile / 1500m / 3k Steeple / 5k Track / 5k XC / 6k XC | ✅ |
| Plotly themed dark (transparent bg, accent #58a6ff, Geist Mono ticks) | ✅ |
| Hand-rolled SVG calendar heatmap with workout-type / miles-intensity toggle | ✅ |
| Notes search with type-pill filters and live highlighting | ✅ |
| Cross-chart date sync (plotly_relayout, 5 date-axis charts) | ✅ |
| Click-to-detail side panel (charts, heatmap cells, race cards) | ✅ |
| PR grid: 4-on-top / 3-on-bottom layout (4×2, user confirmed preference) | ✅ |
| Notes list renders all matching entries (was capped at 200) | ✅ |
| Stats spot-check: totals match manual CSV calc (6120 mi / 63 peak / 17d streak / 64%) | ✅ |
| 5K progression: season-best overlay polyline (dotted accent, diamond markers) | ✅ |
| Per-race PR flag gated on `PR_CARD_SPECS` (1500m steeple no longer false-PR) | ✅ |

## Open / known issues to address next session
1. **Strava button** still links to `strava.com/dashboard` — left as-is per user direction (revisit when a real local Strava dashboard exists; `strava-data/` currently has only raw CSVs).
2. **`Rewrite Ideas.md`** — larger pass of UI tweaks (theme toggle, title size, axis-label contrast, Training Notes table layout, default heatmap mode, Volume/Mix/Performance/Races/Patterns layout fixes). Out of scope this session.

## Reference files
- **Design spec**: [Claude Design/design_handoff_running_log/README.md](Claude Design/design_handoff_running_log/README.md)
- **Design HTML prototype**: [Claude Design/design_handoff_running_log/Running Log Dashboard.html](Claude Design/design_handoff_running_log/Running Log Dashboard.html) — open side-by-side for visual comparison
- **Tweaks panel** (skipped for v1): [Claude Design/design_handoff_running_log/tweaks-panel.jsx](Claude Design/design_handoff_running_log/tweaks-panel.jsx)

## Key data facts

### CSV columns (after `parse_log.py` fix)
```
date, year, month, day, day_of_week, week_of_year, season,
workout_type, minutes, minutes_raw, miles, pace_min_per_mile,
comments, extras,
is_race, race_name, race_distance, race_time,
source_file
```
No `place` column. The leading "th, "/"st, " prefixes were date ordinals
("April 7**th**, …"), not placement digits — there is no place data in the
source headers. If placement is ever needed, look for it in `comments`
(e.g. "37/224 runners").

`is_race` values are `"1"` / `"0"` (strings), not `True`/`False`.

### Race classification rules (in `classify_race()`)
- **Cross country**: `month ∈ {9, 10}` or `month == 11 and day < 25`
- **Indoor track**: `month == 12` or `month <= 2` or `month == 3 and day < 28`
- **Outdoor track**: `month == 3 and day >= 28` or `month ∈ {4, 5}`
- **Omitted**: `2004-06-06` (Camp Pendleton Mud Run, summer road race)

### Workout-type mapping (CSV → 5 design types)
See `WORKOUT_TYPE_MAP` in `visualize_log.py`. Anything not listed falls back
to `easy`.

### Design tokens (subset)
```
ACCENT          = #58a6ff
EASY            = #2dd4bf  (teal)
TEMPO           = #f59e0b  (amber)
LONG            = #a78bfa  (violet)
RACE            = #f87171  (coral)
WORKOUT         = #60a5fa  (blue)
BG_BASE         = #0d1117
BG_GLASS        = rgba(22, 27, 34, 0.7)
Font: Geist (body), Geist Mono (numbers)
```

### Click-to-detail panel (added 2026-05-10)
- Data: `build_day_index(rows)` → per-date map embedded as `<script id="day-index" type="application/json">` (1164 keys, 645 KB)
- Click sources: `plotly_click` on `chart-cumulative`, `chart-easy-pace`, `chart-pace-timeline`, `chart-5k-prog`; `click` on `.hm-cell[data-date]` (populated heatmap cells only — rest days have no `data-date`); `click` on `.race-card[data-date]` (keyboard accessible)
- Close: × button, backdrop click, Escape key
- HTML-escaped via `esc()` helper; `</` escaped to `<\/` in JSON blob

### Cross-chart date sync (added 2026-05-10)
- `DATE_CHART_IDS = ["chart-cumulative","chart-weekly","chart-easy-pace","chart-5k-prog","chart-pace-timeline"]`
- `syncing` flag prevents feedback loops; early-return guard ignores events with no axis range info

## How to verify after changes
1. `C:\Users\Alisha\Anaconda3\python.exe src/visualize_log.py` — should print `XC=31, Indoor=29, Outdoor=39, total=99`
2. `start "" index.html` — opens in default browser (don't use `preview_start` for static HTML)
3. Click each top tab: Overview / Volume / Workout Mix / Performance / Races / Patterns
4. On Overview: zoom a date chart → switch to Volume/Performance → other date charts should match range
5. Click a chart point, a heatmap cell, and a race card → detail panel slides in with notes
6. On Races: each sub-tab (Cross Country / Indoor / Outdoor) shows its race count; PR badges visible
