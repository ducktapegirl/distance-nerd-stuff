# endurance-logs

Personal endurance-data dashboards: a **Strava** activity dashboard and a **Running Log** dashboard, extracted from a larger experiments repo into their own home.

- **Strava dashboard** — aggregate views of Strava activity data, built and maintained through a multi-agent Claude workflow. Pipeline and agent roles: [`strava-data/AGENTS.md`](strava-data/AGENTS.md).
- **Running Log** — decades of running logs parsed into an interactive page. Handoff notes: [`Running Log/SESSION-HANDOFF.md`](Running%20Log/SESSION-HANDOFF.md).

## Quick start

```bash
python strava-data/build_dashboard.py            # build strava-data/strava.html
python -m http.server 8765 --directory strava-data   # preview
```

See [`CLAUDE.md`](CLAUDE.md) for the workspace guide and [`MIGRATION.md`](MIGRATION.md) for the post-extraction setup checklist (GitHub Actions secrets, deploy, plugins).
