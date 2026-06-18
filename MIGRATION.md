# Migration notes — extracted from `Experiments`

This repo was split out of `C:\Users\Alisha\Documents\Experiments` on 2026-06-12.
It holds the **Running Log** and **Strava** projects so they can be developed,
versioned, and deployed independently of the MATLAB/Simscape work.

## What came over

- `strava-data/` (incl. `data/`, ~40 MB of activity/stream/lap CSVs)
- `strava-export/` (older one-off export tool)
- `Running Log/` (minus its `.netlify/` link — see below)
- `Claude Design/design_handoff_running_log/`
- `Running Log/running_log_story_handoff.md` (was in `Create Presentations/`)
- `Agent Strava Plan.md`, `Claude's Log.md`
- `.github/workflows/strava-fetch.yml`
- `.claude/agents/strava-*.md`, `.claude/commands/{strava,strava-segments,requirements}.md`, and local `.claude/{settings.json,settings.local.json,launch.json}` (gitignored)

Fresh git history — the old history stays in `Experiments`.

## What deliberately did **not** come over

- **Netlify hook** (`.netlify/`, `Running Log/.netlify/`). Deploy is being replaced by a GitHub Action — see `.github/workflows/deploy.yml`.
- `/reflect` + `document_work.py` were **elevated to a global Claude skill** at `~/.claude/skills/reflect/` (shared across all projects on this machine; not stored in this repo). `Claude's Log.md` itself did come over.
- All MATLAB/Simscape and other unrelated experiments.

## Manual setup checklist

1. **GitHub Actions secrets** — recreate on `ducktapegirl/distance-nerd-stuff` for `strava-fetch.yml`
   (they previously lived only on the `Experiments` repo):
   ```bash
   gh secret set STRAVA_CLIENT_ID      --repo ducktapegirl/distance-nerd-stuff
   gh secret set STRAVA_CLIENT_SECRET  --repo ducktapegirl/distance-nerd-stuff
   gh secret set STRAVA_REFRESH_TOKEN  --repo ducktapegirl/distance-nerd-stuff
   gh secret set GH_PAT                --repo ducktapegirl/distance-nerd-stuff   # PAT with Secrets: write (token rotation)
   gh secret set SMTP_USER            --repo ducktapegirl/distance-nerd-stuff
   gh secret set SMTP_PASSWORD        --repo ducktapegirl/distance-nerd-stuff
   gh secret set ALERT_TO             --repo ducktapegirl/distance-nerd-stuff
   ```
2. **`frontend-design` plugin** — enable via `/plugin` so the Strava viz/ideation agents can use it.
3. **Deploy workflow** — finish `.github/workflows/deploy.yml` (pick Netlify / GitHub Pages / Cloudflare Pages, add its secret, remove the `if: false` guard).
4. **Local Strava fetch (optional)** — to run `strava-data/fetch.py` locally, create `strava-data/.env` + `.strava_tokens.json` (gitignored), or reuse the credentials in `strava-export/`.
5. **Python env** — use the bare `python` (3.13 venv with plotly/pandas) for `build_dashboard.py`.
6. **Merge the cleanup branch in `Experiments`** — the migrated files were removed there on branch `chore/extract-endurance-logs` (not pushed/merged automatically). Merge it once you've confirmed this repo is good.
