# distance-nerd-stuff

*seriously, who cares?*

I do, apparently. This is a little personal corner of the internet for poking
at my own endurance sports data: a **Strava dashboard** for activities pulling using the Strava API
activities (2024+), and a **Running Log**: my college running log that predated Strava entirely (2003-2007).

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

The Strava dashboard isn't hand-coded — it's built and maintained by a
small crew of Claude agents, each with one job: one decides what's
interesting in the data, one designs how a new chart should look, one writes
the actual code, one checks the result before it ships. I (a human) approve
each stage along the way. It's equal parts "I wanted these specific charts"
and "I wanted to see how far an agentic build pipeline could go." Curious
how it works under the hood? See [`strava-data/AGENTS.md`](strava-data/AGENTS.md).

## Poking at the code

The data here is mine — the Strava dashboard is built from CSVs pulled
through my personal Strava API credentials, so you can't just clone this and
get a working dashboard with your own data. But the build scripts themselves
are plain Python and free to read or borrow from.

Needs [uv](https://docs.astral.sh/uv/) for Python dependencies (plotly +
numpy, no pandas).

```bash
uv sync                                          # install dependencies
uv run python strava-data/build_dashboard.py     # build Running Log/strava.html
uv run python -m http.server 8765 --directory "Running Log"   # preview at localhost:8765
```

See [`CLAUDE.md`](CLAUDE.md) for the full build pipeline (fetch → analyze →
build → deploy) and [`Handoffs/migration.md`](Handoffs/migration.md) for
one-time repo setup notes (GitHub Actions secrets, etc.).

## Future work

Ideas that are written up but not built yet, pulled from the `Plans/` folder:

- **Places hero mobile crowding** — on narrow phones (≤360px) the Places hero's
  bottom controls (fullscreen toggle + filters) can collide with the data-driven
  home-location labels drawn on the map canvas; there's just not enough vertical
  room at that width. A few fix options are on the table, from carving the
  fullscreen toggle out into its own element to a bigger mobile-chrome rework.
  See [`Plans/strava-data/places-future-work.md`](Plans/strava-data/places-future-work.md).
- **A real WBGT heat-stress index** — the Exploratory tab's heat-vs-pace charts
  run on a "WBGT-lite" proxy (temperature + UV) today because the data has no
  humidity or solar readings. The plan is to pull those fields from the weather
  API already in use and compute an actual WBGT (wet-bulb globe temperature) —
  though the honest expectation is it'll explain only a few more percent of pace
  variance than the proxy already does.
  See [`Plans/strava-data/wbgt-future-work.md`](Plans/strava-data/wbgt-future-work.md).
