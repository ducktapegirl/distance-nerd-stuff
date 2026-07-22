# Future work: clickable Strava links from the Activity Details panel

**Status:** proposed / scoped · **Created:** 2026-07-18 · **Owner:** unassigned

## Why

The Activity Details panel — the right-side panel on desktop, the bottom sheet on
mobile — shows an activity's name, date, and stats when you click a calendar day
or a point on the HR/Pace/Map charts. The activity **name** is plain text today.
It would be handy for it to link out to the real activity on Strava
(`https://www.strava.com/activities/<id>`) so a viewer who's logged in to Strava
can click straight through to the source activity. Applies to both desktop and
mobile, on the name only.

## Effort: very small (~one sitting)

The hard part — getting the Strava activity id onto the page — is already done:

- **The id is already in the data.** It's the first column of
  `strava-data/data/activities.csv`, captured by `fetch.py`
  (`"id": d.get("id")`, `fetch.py:251`), and it *is* the numeric id used in the
  Strava activity URL. **No fetch / workflow / CSV change is needed.**
- **The id is already embedded in the page.** `_activity_detail_json()`
  (`strava-data/dashboard/page.py:52-76`) keys the client-side `ACT_DATA` blob by
  `str(r["id"])`.
- **One renderer covers both form factors.** `renderActivity(a)`
  (`strava-data/dashboard/template.py:701-715`) builds the panel body for the
  desktop side panel and the mobile bottom sheet alike — same HTML, different CSS
  — so a single edit reaches both.

Today the name is rendered as plain text at `template.py:704`:
`'<div class="d-name">' + esc(a.name) + '</div>'`.

## What changes

Three small edits, no data-pipeline work:

1. **`strava-data/dashboard/page.py`** — the id is currently only the *key* of
   `ACT_DATA`, and `renderActivity(a)` receives the value object, not the key. Add
   the id inside the per-activity dict in `_activity_detail_json()` (line ~65):
   `"id": str(r["id"]),`.
2. **`strava-data/dashboard/template.py`** — in `renderActivity()` (line 704),
   wrap the name in an anchor:
   `https://www.strava.com/activities/<id>` with `target="_blank"` and
   `rel="noopener noreferrer"`. Keep using the existing `esc()` helper for the
   name text.
3. **`strava-data/dashboard/template.py`** (CSS near `.d-name`, line 473) — ~2
   lines of link styling using the theme `--accent` token so it reads as a link
   and works in both light and dark themes (per the theme/units policy in
   `CLAUDE.md`).

## Decisions (sensible defaults — easy to change)

- **All activity types** get the link (runs, trail runs, MTB all have Strava ids).
- **Opens in a new tab.**
- **Only the name** becomes a link; the stat tiles stay as-is.
- **No auth handling** is possible or needed on a static dashboard — the link
  points at the canonical Strava URL, and Strava itself handles login and
  private-activity gating for the viewer. If the viewer isn't logged in (or the
  activity is private and not theirs), Strava shows its own login/permission page.

## Verification

1. Rebuild: `uv run python strava-data/build_dashboard.py` (regenerates
   `running-log/strava.html`).
2. Preview via `tools/mobile_preview.py` (or the `strava-qa` flow): open the
   detail panel on **desktop** (side panel) and **mobile** (bottom sheet); confirm
   the name renders as a link, hover styling works in **light and dark**, and the
   `href` is `https://www.strava.com/activities/<id>` with the correct id.
3. Spot-check one id against `strava-data/data/activities.csv` and confirm the URL
   loads the right activity on strava.com.

## Out of scope

- No changes to `fetch.py`, the GitHub workflows, or the CSV schema.
- Not adding links elsewhere (segment rollup cards, calendar cells) unless asked.
