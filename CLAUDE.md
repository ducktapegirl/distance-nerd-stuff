# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# distance-nerd-stuff — Claude workspace guide

Two endurance-data dashboards extracted from the old `Experiments` repo, built and maintained by **one** unified multi-agent pipeline — the `/dashboard <target>` workflow. See [`AGENTS.md`](AGENTS.md) for the full pipeline, agent roles, and the per-dashboard **profile** mechanism. Key rule: a subagent cannot spawn another subagent, so the orchestrator stages (Intake → Analyze → Ideate → Design → Build → QA → Review gate → Ship) run as a top-level skill, not an agent.

- **`strava-data/`** — the Strava dashboard (target `strava-data`). Invoke via `/dashboard strava-data` or the `/strava` alias. Strava-specific notes: [`strava-data/AGENTS.md`](strava-data/AGENTS.md); build spec + profile: [`Project Docs/Specs/strava-data/dashboard-spec.md`](Project%20Docs/Specs/strava-data/dashboard-spec.md).
- **`running-log/`** — the running-log dashboard (target `running-log`; parsed from old HTML logs into an interactive page). Invoke via `/dashboard running-log` or the `/running-log` alias. Build spec + profile: [`Project Docs/Specs/running-log/dashboard-spec.md`](Project%20Docs/Specs/running-log/dashboard-spec.md); architecture handoff: [`Project Docs/Handoffs/running-log/session-handoff.md`](Project%20Docs/Handoffs/running-log/session-handoff.md).

The shared reasoning agents (`dash-analyst`, `dash-creativity`, `dash-viz-design`, `dash-developer`) read the target's profile block; QA is target-specific (`strava-qa`, `running-log-qa`).

Human-facing documents (not agent-facing config) live under **`Project Docs/`**, grouped by category — each with per-dashboard subfolders (`strava-data/`, `running-log/`) plus cross-cutting docs at the category root: **`Plans/`** (proposed/future work), **`Specs/`** (build specs and design handoffs), **`Handoffs/`** (session handoffs and historical notes).

## Layout

```
strava-data/        authorize.py (OAuth bootstrap), fetch.py → analyze_segments.py → build_dashboard.py → ../running-log/strava.html
running-log/        index.html, running_log.csv, parse_log.py/visualize_log.py/qa.py + dashboard/ package, strava.html (Strava dashboard output), source/ (_archive/ for non-input files)
Project Docs/       human-facing docs, each category with per-dashboard subfolders (strava-data/, running-log/):
  Plans/              proposed/future work + cross-cutting
  Specs/              build specs + design handoffs: strava-data/ (dashboard-spec.md, mocks/), running-log/ (design_handoff_running_log/)
  Handoffs/           session handoffs + historical notes + migration.md
.claude/agents/     shared dash-* reasoning agents (analyst, creativity, viz-design, developer) + target-specific QA (strava-qa, running-log-qa) + strava-maintenance
.claude/qa-visual-suite.md  shared rendered-QA checks (V0-V8) both QA agents run — single source of truth
.claude/commands/   dashboard (unified orchestrator), strava + running-log (target aliases), strava-segments, requirements
.github/workflows/  strava-fetch.yml (Strava API → data/), deploy.yml (build + publish to Pages)
```

## Python environment

All scripts use a single UV-managed venv at the repo root (`pyproject.toml`). Always use `uv run` — bare `python` resolves to Anaconda2 (Python 2) on this machine.

```bash
uv sync   # install/update all deps
```

## Build the Strava dashboard

```bash
uv run python strava-data/build_dashboard.py   # regenerates running-log/strava.html
```

`build_dashboard.py` reads CSVs in `strava-data/data/` and writes `running-log/strava.html` (the Pages publish root). **Imports are restricted to stdlib + plotly + numpy — no pandas.** All data wrangling uses plain dicts/lists.

Full data pipeline (run in order if refreshing from scratch):
```bash
uv run python strava-data/fetch.py                                   # pull from Strava API
uv run python strava-data/analyze_segments.py                        # write segments_summary.csv
uv run python strava-data/build_dashboard.py                         # build HTML
```

## Build the Running Log dashboard

```bash
# Regenerate CSV from source HTML logs (only needed if parse_log.py changed):
uv run python "running-log/parse_log.py"

# Regenerate index.html:
uv run python "running-log/visualize_log.py"
```

## Preview

A local, gitignored `.claude/launch.json` (not committed — set it up per your machine) can
define preview servers. Otherwise run
manually — both dashboards' HTML lives under `running-log/`:

```bash
uv run python -m http.server 8765 --directory "running-log" # open index.html or strava.html
```

When accessing locally, use **`http://127.0.0.1`** instead of `localhost` to satisfy Maplify API restrictions.

**Mobile / visual checks:** the Claude Preview MCP cannot reach a local server on this machine (its Chromium lands on `chrome-error://`). Use `tools/mobile_preview.py` instead — an in-process `127.0.0.1` server plus a mobile-emulated Playwright Chromium in one host process. **Run it un-sandboxed** (the page loads `plotly.js` from the CDN). It prints chart fill/range measurements and saves screenshots; pass `--url` to check the live site. Setup once: `uv add --dev playwright` + `uv run playwright install chromium`. The deployed site is **`https://ducktapegirl.github.io/distance-nerd-stuff/`** (project page — repo subpath; the bare `ducktapegirl.github.io/strava.html` 404s).

## Plotly charts — mobile-safe authoring

Both dashboards render Plotly charts into fixed-height, `overflow:hidden` cards **and** ship per-chart JavaScript in their `dashboard/template.py` (`applyChartTheme()` plus a mobile pass — `simplify()`, `thinTicks()`, a `DENSE` list — keyed by chart div id). Three separate mobile-rendering bugs (June–July 2026) traced to the same two traps, so when adding or redesigning any `chart_*`:

- **Never anchor chart chrome in data coordinates on a chart that must work at mobile widths.** Direct-label annotations, `add_vrect(..., annotation_text=...)` pills, or any `xref="x"`/`"y"` annotation whose text extends past the data force Plotly's autorange to widen the axis to keep that text on-canvas. The widening is proportionally huge on a ~300px mobile plot: a 2003–2007 x-axis silently stretched to ~2010 (running-log pace chart), and a category x-axis stretched from `[-0.5, 11.5]` to `[-0.5, 17.35]` (strava Seasonal Handoff), each compressing the data into the left ~60% of the card while looking fine on desktop. Use a legend or `xref="paper"` chrome instead, **and** pin an explicit axis `range=` so autorange can't expand (the running-log PR-progression/timeline/pace charts share `_PR_X_RANGE` for exactly this).

- **When redesigning an existing chart, `grep template.py` for its div id first, before calling it done.** The mobile JS special-cases charts by id and encodes assumptions about the chart's *previous* design: `simplify()` may force `showlegend`/`nticks`, and `DENSE` auto-thins ticks. These silently fight a redesign — a leftover `simplify()` line that hid the pace chart's old 7-item legend kept hiding its new 4-item legend on mobile until the line was removed, and the chart lingered in `DENSE` after gaining a fixed `dtick`. Reconcile or delete that JS in the same change, and set `showlegend`/`dtick` explicitly in the Python figure rather than relying on defaults the JS can override.

- **Verify mobile by measuring, not just screenshotting.** A blown-out axis range or a missing legend reads as merely "a bit compressed" or "not rendering" in a screenshot. Confirm with real values via `tools/mobile_preview.py --eval` (or the browser MCP) at a 375px width: read `el._fullLayout.xaxis.range`, `.showlegend`, and tick-label `transform` (rotation), and compare against a sibling chart in the same section.

## Running Log dashboard architecture

`visualize_log.py` is a thin entrypoint; the actual chart builders, data helpers, page sections, and HTML/CSS/JS templates live in the `running-log/dashboard/` package (`config.py`, `data.py`, `stats.py`, `theme.py`, `charts.py`, `components.py`, `sections.py`, `template.py`, `page.py`) — add new `chart_*`/`section_*` functions there, not in `visualize_log.py` itself.

## Strava dashboard architecture

`build_dashboard.py` is a thin entrypoint; the actual chart builders, data helpers, and page assembly live in the `strava-data/dashboard/` package (`config.py`, `data.py`, `geometry_stats.py`, `theme.py`, `charts_production.py`, `charts_exploratory.py`, `rollups_cards.py`, `template.py`, `page.py`) — add new `chart_*` functions there, not in `build_dashboard.py` itself. It renders all charts with Plotly in dark-theme defaults. At runtime, page JS (`applyChartTheme()`) re-styles charts via CSS custom properties for the light/dark/system toggle. Key conventions:
- Every figure must use `tidy_dark(fig)` then per-chart overrides, wrapped with `fig_html(fig, H, div_id=...)`.
- Any color introduced in a chart must be covered by `applyChartTheme()` so both themes work.
- `Project Docs/Specs/strava-data/dashboard-spec.md` is the source of truth for what views exist and their build recipes.

**Display units policy** (never deviate without updating the spec):
- Running pace: **min/mi** (`M:SS` format), axes reversed (faster = up/right). Never min/km.
- MTB/cycling speed: **mph**. Never km/h.
- Temperature: **°F**. Never °C.
- Data files stay metric; convert at display time only.

Sport types in data: `Running`, `TrailRun` (both teal `#2dd4bf`), `MountainBikeRide` (amber `#f59e0b`).

## Source-of-truth split (avoid merge conflicts)

The generated dashboards (`running-log/index.html`, `running-log/strava.html`) are **gitignored** — never committed. This keeps two sources of truth cleanly separated:
- **Data** is owned by the fetch workflow → commits only `strava-data/data/`.
- **Features** (page structure/styling) are owned by the Python build scripts, committed locally.

Because the HTML is never in git, a `git pull` of fresh remote data can't conflict with local feature work. The HTML is rebuilt from data + Python by the deploy workflow.

## Data refresh

Strava data is fetched by **`.github/workflows/strava-fetch.yml`** (cron + manual `workflow_dispatch`), which commits new files under `strava-data/data/` only — **it does not build or commit HTML**. That push triggers `deploy.yml`, which rebuilds and publishes. It needs repo secrets — see `Project Docs/Handoffs/migration.md`. Running locally is possible with a `strava-data/.env` + `.strava_tokens.json` (gitignored). First-time local auth: `uv run python strava-data/authorize.py`.

**What `fetch.py` writes under `strava-data/data/`:** `athlete.json`, `gear.json`, `activities.csv`, `segment_efforts.csv`, `segments_summary.csv` (via `analyze_segments.py`), `streams/{id}.csv` (per-activity GPS/HR/pace time-series — used by the Places views), and `laps/{id}.csv` (per-activity lap splits). **`laps/` is fetched but not yet consumed by any build — retained intentionally for future lap-level / interval views. Do not flag it as dead data or prune it.**

## Logging

`/reflect` is a **global** Claude skill (`~/.claude/skills/reflect/`) that writes a dated entry to this repo's `Claude's Log.md`.

## Deploy

`.github/workflows/deploy.yml` **builds both dashboards from source** (`uv sync` → `build_dashboard.py` + `visualize_log.py`) and publishes the `running-log/` dir to **GitHub Pages**. It triggers on pushes to `main` that touch the data, build scripts, running-log source, or the Python env (`pyproject.toml`/`uv.lock`) — including the data-only commits from `strava-fetch.yml` — plus `workflow_dispatch` for manual deploys.
