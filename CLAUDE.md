# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# distance-nerd-stuff — Claude workspace guide

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
.github/workflows/  strava-fetch.yml (Strava API → data/), deploy.yml (build + publish to Pages)
```

## Python environment

All scripts use a single UV-managed venv at the repo root (`pyproject.toml`). Always use `uv run` — bare `python` resolves to Anaconda2 (Python 2) on this machine.

```bash
uv sync   # install/update all deps
```

## Build the Strava dashboard

```bash
uv run python strava-data/build_dashboard.py   # regenerates Running Log/strava.html
```

`build_dashboard.py` reads CSVs in `strava-data/data/` and writes `Running Log/strava.html` (the Pages publish root). **Imports are restricted to stdlib + plotly + numpy — no pandas.** All data wrangling uses plain dicts/lists.

Full data pipeline (run in order if refreshing from scratch):
```bash
uv run python strava-data/fetch.py                                   # pull from Strava API
uv run python strava-data/analyze_segments.py                        # write segments_summary.csv
uv run python strava-data/build_dashboard.py                         # build HTML
```

## Build the Running Log dashboard

```bash
# Regenerate CSV from source HTML logs (only needed if parse_log.py changed):
uv run python "Running Log/src/parse_log.py"

# Regenerate index.html:
uv run python "Running Log/src/visualize_log.py"
```

## Preview

`.claude/launch.json` defines preview servers (`strava-dashboard` on :8765, `running-log` on :8766), or run manually:

```bash
uv run python -m http.server 8765 --directory strava-data     # open strava.html
uv run python -m http.server 8766 --directory "Running Log"   # open index.html
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

## Source-of-truth split (avoid merge conflicts)

The generated dashboards (`Running Log/index.html`, `Running Log/strava.html`) are **gitignored** — never committed. This keeps two sources of truth cleanly separated:
- **Data** is owned by the fetch workflow → commits only `strava-data/data/`.
- **Features** (page structure/styling) are owned by the Python build scripts, committed locally.

Because the HTML is never in git, a `git pull` of fresh remote data can't conflict with local feature work. The HTML is rebuilt from data + Python by the deploy workflow.

## Data refresh

Strava data is fetched by **`.github/workflows/strava-fetch.yml`** (cron + manual `workflow_dispatch`), which commits new files under `strava-data/data/` only — **it does not build or commit HTML**. That push triggers `deploy.yml`, which rebuilds and publishes. It needs repo secrets — see `MIGRATION.md`. Running locally is possible with a `strava-data/.env` + `.strava_tokens.json` (gitignored).

## Logging

`/reflect` is a **global** Claude skill (`~/.claude/skills/reflect/`) that writes a dated entry to this repo's `Claude's Log.md`.

## Deploy

`.github/workflows/deploy.yml` **builds both dashboards from source** (`uv sync` → `build_dashboard.py` + `visualize_log.py`) and publishes the `Running Log/` dir to **GitHub Pages**. It triggers on pushes to `main` that touch the data, build scripts, running-log source, or the Python env (`pyproject.toml`/`uv.lock`) — including the data-only commits from `strava-fetch.yml` — plus `workflow_dispatch` for manual deploys.
