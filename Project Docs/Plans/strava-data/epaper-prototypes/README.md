> **Archived reference — not a build step on this branch.**
> Copied from branch `claude/strava-rss-feed-display-uoiv93` (`Project Docs/Plans/strava-data/eink-cards/`)
> so its two overview images survive that branch's deletion. Everything below describes
> *that* branch's Pillow prototype, including a device ("reTerminal E1005, 800x650") that
> does not exist — the real panel is the reTerminal Sticky, 800x480. The 17 per-card PNGs,
> the strip-map mocks and `strava-data/tools/eink_cards.py` were **not** copied; recover them
> with `git show claude/strava-rss-feed-display-uoiv93:<path>` while that branch survives.
> The shipped implementation is `strava-data/feed/` — see
> [`../epaper-feed-plan.md`](../epaper-feed-plan.md) for what was carried across.

---

# E-paper cards — prototype contact sheet

Candidate "cards" for a **reTerminal E1005** (3.97", 800×650, 4-level greyscale) fed by
SenseCraft HMI. This is an **idea picker**, not a build step: every card is rendered from
the real data in `strava-data/data/` (and `running-log/running_log.csv`) by
`strava-data/tools/eink_cards.py`, snapped to the panel's four grey levels
(0 / 85 / 170 / 255), and tiled into `contact-sheet.png`. Pick favourites; the follow-on
work is a real feed builder (RSS + PNG enclosures) for the chosen views.

Regenerate: `uv run python strava-data/tools/eink_cards.py` (Pillow is a dev dependency).

| # | Card | Idea | Template | Data used |
|---|------|------|----------|-----------|
| 01 | Latest activity + route | #1 | Map + stats | latest activity with a GPS stream; RDP-simplified polyline, 1 km scale bar |
| 02 | Week in review | #11 | Card grid | ISO week of the latest activity vs the week before |
| 03 | Streak + training load | #19/#20 | Hero | consecutive ISO weeks with a run; ACWR = 7d/28d mean suffer score |
| 04 | Personal records | #25 | List | all-time records across activities.csv |
| 05 | Segment of the month | #26 | Hero + sparkline | most-repeated segment in the last 30 days of efforts |
| 06 | Route progress — running | #38 | Map + stats | lifetime run miles on a 92129 road-distance ladder |
| 07 | Route progress — biking | #38 | Map + stats | lifetime MTB + Ride + EBike miles on the same ladder |
| 08 | Passport | #33 | Badge wall | `_passport_data` trip clusters (same as the dashboard's Places tab) |
| 09 | Two cardiac worlds | #43 | Hero pair | avg HR per activity, run vs MTB |
| 10 | Gear odometer | #48 | Card grid | gear.json miles vs Strava's replacement alert |
| 11 | This week in 2004 | #51 | Then & now | same ISO week in the 2003-era log vs now |
| 12 | Wildlife scoreboard | #56 | List | animal words in descriptions/names (whole-word match) |
| 13 | Segment name of the day | #30 | Hero | word-list + length scoring, rotates daily by date hash |
| 14 | Activity-name hall of fame | #32 | List | non-default names, rotates weekly |
| 15 | Achievement unlocked | #60 | Badge wall | latest activity vs history: records, milestones, PRs, firsts |
| 16 | Joggernaut index | #62 | Hero | streak × load-sanity × variety × kudos (deliberately silly) |
| 17 | Latest wildlife sighting | #8 | Hero | most recent activity mentioning an animal |

Notes
- Road distances in the route ladder are approximate driving miles from 92129, hand-typed
  in `ROUTE_LADDER`; waypoints carry cumulative miles so the marker position is honest.
- Icons are geometric Pillow primitives (no font glyphs), drawn at 1× and quantized, so they
  survive the 2-bit panel without dithering artefacts.
- Data is as of the latest activity in `activities.csv` at render time; the sample week has no
  runs, which is why cards 02 and 11 show 0 run miles.
