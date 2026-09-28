# Future work

Ideas that are written up but not built yet. Each links to its full plan in this folder.

- **Places hero mobile crowding** — on narrow phones (≤360px) the Places hero's
  bottom controls (fullscreen toggle + filters) can collide with the data-driven
  home-location labels drawn on the map canvas; there's just not enough vertical
  room at that width. A few fix options are on the table, from carving the
  fullscreen toggle out into its own element to a bigger mobile-chrome rework.
  See [`strava-data/places-future-work.md`](strava-data/places-future-work.md).
- **Adaptive Places superlatives** — the Passport badges and Peaks record book
  ("Highest point · 14,507 ft," "Northernmost · 49.3°N," …) are hardcoded
  editorial copy today, so a bigger hike next week never supersedes an old
  record, and a forked repo with different Strava data would render false
  claims instead of blank ones. The plan splits the pinned copy into an
  editorial config file, adds a CI step that detects when live data beats it,
  and extends the `strava-maintenance` agent to propose the actual edit.
  See [`strava-data/adaptive-superlatives-future-work.md`](strava-data/adaptive-superlatives-future-work.md).
- **Bring your own data (forkable strava-data/)** — right now this repo really
  is mine-only: home cities, superlatives, and even the analytics snippet are
  hardcoded to me, and a fork would crash or quietly render someone else's
  records. The plan: fix the genuine bugs and leaks, strip the personal data a
  fork shouldn't ship, and add a `FORKING.md` + from-zero setup walkthrough so
  the entry point (`strava-data/`, not the Running Log) is obvious. Depends on
  the adaptive-superlatives work above; honestly not sure it's worth it yet.
  See [`strava-data/byod-forkable-future-work.md`](strava-data/byod-forkable-future-work.md).
- **A real WBGT heat-stress index** — the Exploratory tab's heat-vs-pace charts
  run on a "WBGT-lite" proxy (temperature + UV) today because the data has no
  humidity or solar readings. The plan is to pull those fields from the weather
  API already in use and compute an actual WBGT (wet-bulb globe temperature) —
  though the honest expectation is it'll explain only a few more percent of pace
  variance than the proxy already does.
  See [`strava-data/wbgt-future-work.md`](strava-data/wbgt-future-work.md).
- **Clickable Strava activity links** — the Activity Details panel (desktop side
  panel and mobile bottom sheet) shows an activity's name as plain text. The plan
  turns the name into a link out to the real activity on Strava so a logged-in
  viewer can click through. It's a very small change: the Strava activity id is
  already in the data and already embedded in the page (just as the `ACT_DATA`
  key), and one `renderActivity()` function covers both form factors — so it's
  ~2 lines plus a little link CSS, no data-pipeline work.
  See [`strava-data/activity-links-future-work.md`](strava-data/activity-links-future-work.md).
- **The orphaned summer03log.html** — `running-log/source/` has a real training
  log (~495 miles, ~95 entries) that the parser never reads: `parse_log.py`'s
  file list starts at fall 2003, and the summer log uses a different layout
  (weekly totals, no per-day date headers) that the existing parser can't key
  off anyway. It's kept as a live file (not archived) since it's real data, just
  unwired — parsing it would need a second, layout-specific parse path.
  See [`running-log/summer03-log-future-work.md`](running-log/summer03-log-future-work.md).
