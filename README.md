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
- **An e-paper feed** — the same data cut into 64 single-fact "cards" for a
  little 800×480 grey-scale panel stuck to the fridge. Seventeen of them
  rotate, one a day. No colour, no JavaScript, nothing smaller than 26 px,
  because at 235 PPI the whole screen is about the size of a credit card.

All of it is static pages, rebuilt from data + a few Python scripts, and
published with GitHub Pages.

## Built by a team of robots (sort of)

The Strava dashboard isn't hand-coded — it's built and maintained by a
small crew of Claude agents, each with one job: one decides what's
interesting in the data, one designs how a new chart should look, one writes
the actual code, one checks the result before it ships. I (a human) approve
each stage along the way. It's equal parts "I wanted these specific charts"
and "I wanted to see how far an agentic build pipeline could go." Curious
how it works under the hood? See [`strava-data/AGENTS.md`](strava-data/AGENTS.md).

## Filing an issue

Want something fixed or added? [Open an issue](https://github.com/ducktapegirl/distance-nerd-stuff/issues/new/choose) — there are three forms, and each needs the right tag:

- **Bug report** — something's broken, wrong, or looks off. This form auto-tags itself **`bug`**.
- **New view / chart idea** — propose a question you want a dashboard to answer. This form
  auto-tags itself **`enhancement`**.
- **General enhancement** — anything else you'd like improved that isn't a new chart or view
  (navigation, layout, exports, workflow, etc.). This form auto-tags itself **`enhancement`**.

Filing an issue with the `bug` or `enhancement` tag doesn't trigger anything by itself — only I
can apply the `agent:ready` label, and nothing happens until I do. Once it's applied, the issue
may get picked up and routed automatically: `bug` reports go straight to a fix, and `enhancement`
requests go through the full design pipeline if rough or get built more directly if specific
(based on your own "how formed is this idea?" answer on the form). You'll see progress as label changes
(`agent:in-progress` → `agent:done`) and eventually a pull request that closes the issue.

## Poking at the code

The data here is mine — the Strava dashboard is built from CSVs pulled
through my personal Strava API credentials, so you can't just clone this and
get a working dashboard with your own data. But the build scripts themselves
are plain Python and free to read or borrow from.

Needs [uv](https://docs.astral.sh/uv/) for Python dependencies (plotly +
numpy, no pandas).

```bash
uv sync                                          # install dependencies
uv run python running-log/visualize_log.py       # build running-log/index.html
uv run python strava-data/build_dashboard.py     # build running-log/strava.html
uv run python strava-data/build_feed.py          # build the e-paper feed
```

Everything builds into `running-log/`, which is also what GitHub Pages
publishes. None of the generated HTML is committed.

### Previewing locally

Serve that one directory and open whichever page you want:

```bash
uv run python -m http.server 8765 --directory running-log
```

| URL | What it is |
|---|---|
| `http://127.0.0.1:8765/index.html` | Running Log dashboard |
| `http://127.0.0.1:8765/strava.html` | Strava dashboard |
| `http://127.0.0.1:8765/epaper-all.html` | proof sheet — every card at real panel size, filterable to the rotation |
| `http://127.0.0.1:8765/epaper.html` | exactly what the panel gets today |
| `http://127.0.0.1:8765/epaper/<id>.html` | one card on its own, e.g. `/epaper/haiku.html` |

Use **`127.0.0.1`**, not `localhost` — the Strava dashboard's maps are
restricted by MapTiler to that origin. On Windows, prefix commands with
`uv run`; a bare `python` may resolve to something ancient.

For the e-paper cards there's an automated pass over all of it — the feed's
structure, and every card's text size, stroke width, overlap and clipping at
800×480:

```bash
uv run python tools/epaper_check.py
```

It writes a screenshot of each card to `tools/preview-output/epaper/`, so you
can look at what the numbers passed.

See [`CLAUDE.md`](CLAUDE.md) for the full build pipeline (fetch → analyze →
build → deploy) and [`Project Docs/Handoffs/migration.md`](Project%20Docs/Handoffs/migration.md) for
one-time repo setup notes (GitHub Actions secrets, etc.).

## Future work

Ideas that are written up but not built yet, pulled from the `Project Docs/Plans/` folder:

- **Places hero mobile crowding** — on narrow phones (≤360px) the Places hero's
  bottom controls (fullscreen toggle + filters) can collide with the data-driven
  home-location labels drawn on the map canvas; there's just not enough vertical
  room at that width. A few fix options are on the table, from carving the
  fullscreen toggle out into its own element to a bigger mobile-chrome rework.
  See [`Project Docs/Plans/strava-data/places-future-work.md`](Project%20Docs/Plans/strava-data/places-future-work.md).
- **Adaptive Places superlatives** — the Passport badges and Peaks record book
  ("Highest point · 14,507 ft," "Northernmost · 49.3°N," …) are hardcoded
  editorial copy today, so a bigger hike next week never supersedes an old
  record, and a forked repo with different Strava data would render false
  claims instead of blank ones. The plan splits the pinned copy into an
  editorial config file, adds a CI step that detects when live data beats it,
  and extends the `strava-maintenance` agent to propose the actual edit.
  See [`Project Docs/Plans/strava-data/adaptive-superlatives-future-work.md`](Project%20Docs/Plans/strava-data/adaptive-superlatives-future-work.md).
- **Bring your own data (forkable strava-data/)** — right now this repo really
  is mine-only: home cities, superlatives, and even the analytics snippet are
  hardcoded to me, and a fork would crash or quietly render someone else's
  records. The plan: fix the genuine bugs and leaks, strip the personal data a
  fork shouldn't ship, and add a `FORKING.md` + from-zero setup walkthrough so
  the entry point (`strava-data/`, not the Running Log) is obvious. Depends on
  the adaptive-superlatives work above; honestly not sure it's worth it yet.
  See [`Project Docs/Plans/strava-data/byod-forkable-future-work.md`](Project%20Docs/Plans/strava-data/byod-forkable-future-work.md).
- **A real WBGT heat-stress index** — the Exploratory tab's heat-vs-pace charts
  run on a "WBGT-lite" proxy (temperature + UV) today because the data has no
  humidity or solar readings. The plan is to pull those fields from the weather
  API already in use and compute an actual WBGT (wet-bulb globe temperature) —
  though the honest expectation is it'll explain only a few more percent of pace
  variance than the proxy already does.
  See [`Project Docs/Plans/strava-data/wbgt-future-work.md`](Project%20Docs/Plans/strava-data/wbgt-future-work.md).
- **Clickable Strava activity links** — the Activity Details panel (desktop side
  panel and mobile bottom sheet) shows an activity's name as plain text. The plan
  turns the name into a link out to the real activity on Strava so a logged-in
  viewer can click through. It's a very small change: the Strava activity id is
  already in the data and already embedded in the page (just as the `ACT_DATA`
  key), and one `renderActivity()` function covers both form factors — so it's
  ~2 lines plus a little link CSS, no data-pipeline work.
  See [`Project Docs/Plans/strava-data/activity-links-future-work.md`](Project%20Docs/Plans/strava-data/activity-links-future-work.md).
- **The orphaned summer03log.html** — `running-log/source/` has a real training
  log (~495 miles, ~95 entries) that the parser never reads: `parse_log.py`'s
  file list starts at fall 2003, and the summer log uses a different layout
  (weekly totals, no per-day date headers) that the existing parser can't key
  off anyway. It's kept as a live file (not archived) since it's real data, just
  unwired — parsing it would need a second, layout-specific parse path.
  See [`Project Docs/Plans/running-log/summer03-log-future-work.md`](Project%20Docs/Plans/running-log/summer03-log-future-work.md).
