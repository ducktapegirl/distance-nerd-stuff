# Strava Dashboard — Multi-Agent System

> **The pipeline is now unified.** Both the Strava dashboard and the Running Log dashboard
> are built and maintained by **one** multi-agent pipeline, documented at the repo-root
> [`AGENTS.md`](../AGENTS.md). This file records the Strava-specific pieces; read the root
> doc for the full role map, the profile mechanism, and the key rule.

## The Strava pipeline the agents serve
```
fetch.py  →  analyze_segments.py  →  build_dashboard.py  →  strava.html  →  deploy.yml  →  GitHub Pages
(Strava API)  (segment rollups)      (Plotly charts)        (gitignored,     (publishes    (pipeline end)
                                                             lands in         running-log/)
                                                             running-log/)
```
`build_dashboard.py` writes `running-log/strava.html` (`OUT_HTML` in `dashboard/config.py`) —
a gitignored build artifact placed in `running-log/` because that directory is the GitHub
Pages publish root shared by both dashboards. It is never committed; `deploy.yml` rebuilds and
publishes it. The deployed site, not the local file, is the end of the pipeline.

## How to invoke
- `/dashboard strava-data` — build a new view through the full pipeline.
- `/strava` — back-compat alias for `/dashboard strava-data`.
- `/dashboard strava-data maintenance` (or `/strava maintenance`) — run just the
  `strava-maintenance` health-check agent.

## Strava-specific agents
- `strava-qa` — the Strava dashboard's QA agent (build/spec/data/edge/HTML + a responsive
  light/dark visual smoke test). Target-specific because its build command, imperial units
  policy, and checks differ from Running Log's.
- `strava-maintenance` — breakage + upstream (Strava API / Plotly / Claude Code) + dep/code
  health. Read-only + web research; proposes, never fixes. Kept as a dedicated agent because
  the live Strava API genuinely needs an upstream watch (Running Log is frozen).

The reasoning agents (analyst, creativity, viz-design, developer) are the **shared**
`dash-*` agents in `.claude/agents/`; they read the Strava **Pipeline profile** block at the
top of `Project Docs/Specs/strava-data/dashboard-spec.md`. (The former `strava-data-analyst`,
`strava-creativity`, `strava-viz-design`, and `strava-developer` agents were retired in
favor of these — same roles, now profile-driven.)

## Frontend-design dependency
Enable the official **frontend-design** plugin via `/plugin` so the ideation agents can use
its aesthetic guidance. The dashboard's identity (dark glass, Geist fonts,
teal/amber/slate/violet) is the constraint the skill pushes within.
