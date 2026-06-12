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

## Build the Strava dashboard

```bash
python strava-data/build_dashboard.py   # regenerates strava-data/strava.html
```

Use the **bare `python`** (3.13 venv with plotly/pandas/numpy). `build_dashboard.py` reads the CSVs in `strava-data/data/`.

## Preview

`.claude/launch.json` defines preview servers (`strava-dashboard` on :8765, `running-log` on :8766), or run manually:

```bash
python -m http.server 8765 --directory strava-data     # open strava.html
python -m http.server 8766 --directory "Running Log"   # open index.html
```

## Data refresh

Strava data is fetched by **`.github/workflows/strava-fetch.yml`** (manual `workflow_dispatch`), which commits new files under `strava-data/data/`. It needs repo secrets — see `MIGRATION.md`. Running locally is possible with a `strava-data/.env` + `.strava_tokens.json` (gitignored).

## Logging

`/reflect` is a **global** Claude skill (`~/.claude/skills/reflect/`) that writes a dated entry to this repo's `Claude's Log.md`.

## Deploy

The old Netlify hook was intentionally not carried over. `.github/workflows/deploy.yml` is a commented placeholder — finish wiring it to your chosen target (see `MIGRATION.md`).
