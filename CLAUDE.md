# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# endurance-logs — Claude workspace guide

Two endurance-data dashboards extracted from the old `Experiments` repo:

- **`strava-data/`** — the Strava dashboard, built and maintained agentically via the `/strava` multi-agent workflow. See [`strava-data/AGENTS.md`](strava-data/AGENTS.md) for the full pipeline and agent roles.
- **`Running Log/`** — the running-log dashboard (parsed from old HTML logs into an interactive page). See [`Running Log/SESSION-HANDOFF.md`](Running%20Log/SESSION-HANDOFF.md).

## Layout

```
strava-data/        fetch.py → analyze_segments.py → build_dashboard.py → strava.html
strava-export/      older one-off Strava CSV export tool (has its own .env/tokens)
Running Log/        index.html, running_log.csv, src/ (parse/visualize), strava.html copy
Claude Design/      design handoff for the running-log dashboard
.claude/agents/     strava-* specialist agents (creativity, data-analyst, developer, maintenance, qa, viz-design)
.claude/commands/   strava, strava-segments, requirements
.github/workflows/  strava-fetch.yml (Strava API → data/), deploy.yml (placeholder)
```

## Python environments — two different executables

| Project | Executable | Notes |
|---|---|---|
| Strava dashboard | bare `python` | 3.13 venv with plotly/pandas/numpy |
| Running Log | `C:\Users\Alisha\Anaconda3\python.exe` | bare `python` resolves to Anaconda2 (Python 2) on this machine |

## Build the Strava dashboard

```bash
python strava-data/build_dashboard.py   # regenerates strava-data/strava.html + Running Log/strava.html
```

`build_dashboard.py` reads CSVs in `strava-data/data/`. **Imports are restricted to stdlib + plotly + numpy — no pandas.** All data wrangling uses plain dicts/lists.

Full data pipeline (run in order if refreshing from scratch):
```bash
python strava-data/fetch.py                                   # pull from Strava API
python strava-data/analyze_segments.py                        # write segments_summary.csv
python strava-data/build_dashboard.py                         # build HTML
```

## Build the Running Log dashboard

```bash
# Regenerate CSV from source HTML logs (only needed if parse_log.py changed):
C:\Users\Alisha\Anaconda3\python.exe "Running Log/src/parse_log.py"

# Regenerate index.html:
C:\Users\Alisha\Anaconda3\python.exe "Running Log/src/visualize_log.py"
```

## Preview

`.claude/launch.json` defines preview servers (`strava-dashboard` on :8765, `running-log` on :8766), or run manually:

```bash
python -m http.server 8765 --directory strava-data     # open strava.html
python -m http.server 8766 --directory "Running Log"   # open index.html
```

## Strava dashboard architecture

`build_dashboard.py` renders all charts with Plotly in dark-theme defaults. At runtime, page JS (`applyChartTheme()`) re-styles charts via CSS custom properties for the light/dark/system toggle. Key conventions:
- Every figure must use `tidy_dark(fig)` then per-chart overrides, wrapped with `fig_html(fig, H, div_id=...)`.
- Any color introduced in a chart must be covered by `applyChartTheme()` so both themes work.
- `strava-data/dashboard-spec.md` is the source of truth for what views exist and their build recipes.

**Display units policy** (never deviate without updating the spec):
- Running pace: **min/mi** (`M:SS` format), axes reversed (faster = up/right). Never min/km.
- MTB/cycling speed: **mph**. Never km/h.
- Temperature: **°F**. Never °C.
- Data files stay metric; convert at display time only.

Sport types in data: `Running`, `TrailRun` (both teal `#2dd4bf`), `MountainBikeRide` (amber `#f59e0b`).

## Data refresh

Strava data is fetched by **`.github/workflows/strava-fetch.yml`** (manual `workflow_dispatch`), which commits new files under `strava-data/data/`. It needs repo secrets — see `MIGRATION.md`. Running locally is possible with a `strava-data/.env` + `.strava_tokens.json` (gitignored).

## Logging

`/reflect` is a **global** Claude skill (`~/.claude/skills/reflect/`) that writes a dated entry to this repo's `Claude's Log.md`.

## Deploy

`.github/workflows/deploy.yml` publishes to **GitHub Pages** on every push to `main` that touches `Running Log/index.html` or `Running Log/strava.html`. The publish root is `Running Log/`. It also supports `workflow_dispatch` for manual deploys.
