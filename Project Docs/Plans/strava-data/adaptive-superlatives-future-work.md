# Future work: adaptive Places superlatives (Passport badges + Peaks record book)

**Status:** proposed / design decisions resolved · **Created:** 2026-07-18 · **Owner:** unassigned

## Why

The Places section's "superlatives" — Passport badges (`_PASSPORT_TRIPS`, `charts_places.py:1598`)
and the Peaks record book (`_PEAKS_DEF`, `charts_places.py:1622`) — are 100% hardcoded editorial
copy. Trip *clustering* (`_away_clusters`, `:1765`) and geometry are computed live from
`data/streams/*.csv`, but the actual superlative claims ("Highest point · 14,507 ft", "Northernmost
· 49.3°N", …) are pinned strings matched to an activity by a literal title substring (`sig`).

Two concrete problems follow from that design, surfaced while explaining the feature:

1. **A new personal-record activity never supersedes an old superlative.** If a bigger hike happens
   next week, it either becomes a new (unbadged) filmstrip stamp or a brief-stop chip — it never
   competes with or replaces "Highest point · 14,507 ft" in the Peaks book. The only signal is a
   build-console NOTE when the featured count drifts from the pinned 7 (`:1990-1992`) — a hint for a
   human, not a fix.
2. **A fork with different Strava data gets false claims, not blank ones.** `_peaks_data()`
   (`:1913-1948`) appends a Peaks row **unconditionally**, even when `_find_act()` finds no matching
   activity for `sig` — so a fork would render "Highest point · 14,507 ft · Mt. Whitney…" for an
   athlete who never went there (only the sparkline/coordinates go missing). The hardcoded
   `_SD_BOX`/`_BOS_BOX` home boxes (`:33-34`) compound this: if no activity falls inside either box,
   `_centroid()` (`:338`) divides by zero and the build crashes outright.

Goal of this doc: sketch how to make superlatives **self-updating for the athlete who owns the
repo**, and **safe-by-default for anyone who forks it**, without turning the Places section into a
generic analytics feature that loses its editorial voice.

## What "adaptive" should and shouldn't mean

Superlatives aren't pure data — "Home-adjacent giant" and trip captions are curatorial judgment
calls (which peak counts as "home-adjacent," what a trip is called, which badge is worth showing).
Fully auto-computing and auto-publishing prose risks silently replacing good copy with awkward
generated text. So the design goal is **assisted, not autonomous**: compute the real superlative
candidates from data, diff them against what's currently pinned, and hand a human a small, concrete
change to review — never a silent rewrite.

## Design decisions (resolved 2026-07-18)

These were walked through explicitly rather than left as options — pinning them here so the phases
below aren't re-litigating settled ground.

### Two files, not one — mirrors the repo's existing data/features split

`CLAUDE.md` already draws a line between data the fetch workflow owns and features the build owns
(`running-log/index.html`/`strava.html` are gitignored specifically to keep those separate). The
same split applies here:

- **`strava-data/superlatives.json`** (exact path TBD in Build) — the **hand-curated editorial
  config**: the extracted `_PASSPORT_TRIPS`/`_PEAKS_DEF`, one entry per category, each carrying a
  pinned Strava **activity ID** (match key), a human-readable label (commentary only), the display
  value/caption/badge text, and the dismiss list (below). Owned and hand-edited by a human, same as
  the Python build scripts today — never touched by CI.
- **`strava-data/data/superlatives_drift.json`** — a small **machine-generated signal file**,
  written by the new CI detection step and committed by the *existing* `git add strava-data/data/`
  step in `strava-fetch.yml` (`:89-100`), right alongside the CSVs it already stages. Regenerated in
  full on every fetch; nothing hand-edits it.

`strava-maintenance` reads the drift file directly — no GitHub Actions log scraping needed.

### Shared computation, not duplicated logic

The live-candidate computation (highest point, northernmost/easternmost, home-adjacent giant,
longest climb, first-in-home-city) must not be written twice. `dashboard/config.py` has no coupling
that would block reuse outside a full dashboard build — it's just path/color/font constants plus one
env var (`MAPTILER_KEY`, irrelevant here, defaults to `""`). So: put the live-computation recipe in
one shared module (e.g. `strava-data/dashboard/superlatives.py`, alongside the existing
`geometry_stats.py`), imported both by `charts_places.py` (to render) and by a thin new CLI script
(e.g. `strava-data/check_superlatives.py`) that the workflow calls and that only does the diff +
write the drift file.

### CI detection step, chained into the existing fetch workflow

`strava-fetch.yml` already runs "Analyze segments" (`:83-84`) before "Commit new data files"
(`:89-100`). The new step slots in right after segment analysis and before the commit, so
`superlatives_drift.json` rides along in the same commit as everything else that fetch produces.
Report-only — never fails the job or blocks `deploy.yml`.

### `strava-maintenance` extension is the judgment layer, not CI

CI (deterministic script) can only compute-and-diff. `strava-maintenance` (run manually, or later via
a Routine) is what reads the drift file and actually proposes the concrete edit to
`superlatives.json` — wording, whether a new category is even badge-worthy — matching its existing
Bash-based, read/propose-only style. No new MCP tools needed, just a new responsibility.

### Unify duplicate facts between Passport and Peaks

3 of the 6 Peaks rows (Highest point, Northernmost, Easternmost) already duplicate facts shown as
Passport badges on the Whitney/Vancouver/Maine stamps — same superlative, told from two
independently hardcoded lists today. `superlatives.json` holds **one entry per fact**, referenced by
both the Passport badge renderer and the Peaks row renderer, so updating "highest point" updates
both displays together instead of risking the two silently disagreeing after a partial edit.

### "First in San Diego" — a smaller bug worth fixing as part of this work, not before it

`_peaks_data()` already resolves this row's activity live (`:1919-1923`, `first_sd` = the actual
earliest SD-box activity) — only the *displayed* value (`"Apr 2025"`) is a hardcoded string despite
the real date sitting right there. It doesn't need the pinned-value/drift-detection machinery at all
— it's a pure live-compute-and-render fix (same pattern as the brief-stop chips' date formatting at
`:1892`). Not urgent enough to peel off as an immediate standalone fix; land it during Build/Extract
when `superlatives.json` and the renderer are already being touched.

### Category rules

- **"Home-adjacent giant": distance threshold + absolute floor.** Tallest peak (by
  `total_elevation_gain_m`) that is BOTH within **N miles** of a home box AND clears a minimum
  elevation-gain floor (e.g. ~5,000 ft, exact number TBD in Analyze) — if nothing nearby clears the
  bar, the category simply reports nothing that cycle rather than crowning a molehill. `N` itself is
  still an open numeric detail (see Remaining open items).
- **`sig` matching: pinned activity ID, not title substring.** Today's `sig` (e.g. `"Whitney"`
  matched against the activity title) breaks silently on a Strava rename. `superlatives.json` keys
  each entry by activity ID; a label field stays for human readability but isn't the match key.
- **No history of superseded records.** A changed superlative just replaces the old value — no
  "previously: X" footnote. Keeps the Peaks book reading as a current record, not a change-log.

### v1 scope: all 6 categories, with a graceful-degradation escape hatch

Ships covering all 6 Peaks categories rather than staging the 2 harder ones (home-adjacent giant,
longest climb) behind a v2. **But** if either heuristic proves genuinely fiddly during Analyze (climb
segmentation especially), that one category is allowed to degrade to "stays manual, no live
detection yet" so the other 5 still ship on schedule — the v1 label doesn't force a hard block on
the whole feature over one hard heuristic.

### Drift surfaces in the existing completion email

`strava-fetch.yml`'s completion email (`:118-168`) already reports activity/stream counts on every
run. Add one more line when the CI step finds a live candidate beating a pinned value — no new
notification channel, reuses infra that's already there and already something the athlete reads.

### Dismiss/acknowledge mechanism

Because the fetch cron runs every 2 weeks (`cron: "0 6 1,15 * *"`), an un-dismissable drift would
re-report — and re-email — the same candidate forever until the config is edited, even after the
athlete has consciously decided not to update yet (e.g. "seen it, that hike wasn't really trip-worthy
enough for a badge"). `superlatives.json` carries a small dismissed-activity-ID list per category so
an acknowledged candidate stops re-triggering the NOTE/email until something *new* beats the pinned
value.

## Immediate hardening (independent of the above, worth doing regardless)

Cheap correctness fixes that reduce the blast radius for forks even before any of the above lands:

- **Guard `_peaks_data()`** (`:1946`) to skip appending a row when `act is None` (mirroring the
  Passport loop's existing `if sigact is None: continue` at `:1855-1856`), so a fork's Peaks book
  shows fewer rows instead of invented ones.
- **Guard `_centroid()`** (`:338`) or its callers against empty `pts`, and/or make `_SD_BOX`/
  `_BOS_BOX` configurable (e.g. `dashboard/config.py`, or `superlatives.json`) so a fork can set their
  own home cities in one place — and so the build degrades (skip the home cards / print a warning)
  instead of crashing when the boxes don't match the data.

## Remaining open items

Everything structural is decided; these are implementation details to settle during Analyze, not
before:

- **Distance threshold N** and **elevation-gain floor** for "home-adjacent giant" — pick empirically
  against today's data, confirm San Jacinto stays in and nothing unintended gets pulled in.
- **"Longest single climb" computation.** Needs a climb-segmentation heuristic (contiguous ascent
  within one activity's altitude stream) that doesn't exist anywhere in the codebase yet — check
  whether `strava-data-analyst`'s existing methods have anything reusable, or whether this is a new
  small analysis pass. Covered by the graceful-degradation escape hatch above if it stalls.
- **Exact file paths/schema** for `superlatives.json` and `superlatives_drift.json` (field names,
  where the dismiss list lives) — settle in Build once the shared module's data shapes are drafted.

## Suggested phases

1. **Analyze:** pin the live-computation recipe for each of the 6 Peaks rows + Passport badges
   (including the home-adjacent-giant threshold/floor and the longest-climb heuristic), verify
   against today's known values (Whitney 14,507 ft, Vancouver 49.3°N, Maine 70.2°W, San Jacinto
   10,800 ft). Flag now if either hard heuristic should invoke the degrade-gracefully clause.
2. **Extract the editorial config** — create `strava-data/superlatives.json` from
   `_PASSPORT_TRIPS`/`_PEAKS_DEF`, keyed by activity ID; unify the 3 facts duplicated between
   Passport badges and Peaks rows into single shared entries; add the dismiss-list field; update
   `charts_places.py` to read from it instead of the hardcoded dicts; while touching this code, fix
   "First in San Diego" to compute its displayed month/year from `first_sd`'s real date instead of
   the hardcoded string.
3. **Harden for forks** (the two guard fixes above) so a fresh clone is safe on day one.
4. **Build the shared computation module** (`dashboard/superlatives.py`) + the thin CI script
   (`check_superlatives.py`) that diffs live candidates against `superlatives.json`, respects the
   dismiss list, and writes `strava-data/data/superlatives_drift.json`.
5. **Wire into `strava-fetch.yml`**: new step after "Analyze segments," before "Commit new data
   files"; extend the completion email with a drift line.
6. **Extend `strava-maintenance`** to read the drift file and propose the concrete
   `superlatives.json` edit — report only, no auto-apply.
7. **QA:** confirm the CI step reports "no drift" on the current repo; confirm a dismissed candidate
   stops re-triggering; run both the CI script and the extended `strava-maintenance` pass against a
   synthetic fork-like dataset (no activities in the home boxes, no activity ID matching any pinned
   entry) to confirm clean reporting instead of crashing or inventing claims.
8. **Optional v2:** wire `strava-maintenance`'s superlative check into a Routine
   (`mcp__Claude_Code_Remote__create_trigger`) once the manual flow is trusted, so a drift gets
   surfaced without remembering to ask.

## Related

- Feature build plan: [`Plans/strava-data/places-plan.md`](places-plan.md) (original Places build,
  established the hardcoded-editorial-copy pattern this doc is trying to loosen).
- Unrelated open item on the same section: [`Plans/strava-data/places-future-work.md`](places-future-work.md)
  (mobile chrome crowding — different problem, same file).
