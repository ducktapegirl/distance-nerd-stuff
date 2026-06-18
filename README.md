# distance-nerd-stuff

*seriously, who cares?*

I do, apparently. This is a little personal corner of the internet for poking
at my own endurance-sports data: a **Strava dashboard** for cycling/running
activities, and a **Running Log** dashboard for decades of races and training
logs that predate Strava entirely.

**Live:**
- 🏃 Running Log — https://ducktapegirl.github.io/distance-nerd-stuff/
- 🚴 Strava dashboard — https://ducktapegirl.github.io/distance-nerd-stuff/strava.html

## What's actually here

- **Strava dashboard** — charts and stats built from my Strava activity
  history: pace trends, segment performance, mountain bike speed, that kind
  of thing. Refreshed automatically a few times a week.
- **Running Log** — my running history going back well before Strava
  existed, parsed out of old hand-kept HTML logs into one browsable,
  searchable page.

Both are static pages, rebuilt from data + a couple of Python scripts, and
published with GitHub Pages.

## Built by a team of robots (sort of)

The Strava dashboard isn't just hand-coded — it's built and maintained by a
small crew of Claude agents, each with one job: one decides what's
interesting in the data, one designs how a new chart should look, one writes
the actual code, one checks the result before it ships. I (a human) approve
each stage along the way. It's equal parts "I wanted these specific charts"
and "I wanted to see how far an agentic build pipeline could go." Curious
how it works under the hood? See [`strava-data/AGENTS.md`](strava-data/AGENTS.md).

## Running it yourself

Needs [uv](https://docs.astral.sh/uv/) for Python dependencies (plotly +
numpy, no pandas).

```bash
uv sync                                          # install dependencies
uv run python strava-data/build_dashboard.py     # build Running Log/strava.html
uv run python -m http.server 8765 --directory "Running Log"   # preview at localhost:8765
```

See [`CLAUDE.md`](CLAUDE.md) for the full build pipeline (fetch → analyze →
build → deploy) and [`MIGRATION.md`](MIGRATION.md) for one-time repo setup
notes (GitHub Actions secrets, etc.).
