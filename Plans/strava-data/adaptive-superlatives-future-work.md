# Future work: adaptive Places superlatives (Passport badges + Peaks record book)

**Status:** proposed / not started · **Created:** 2026-07-18 · **Owner:** unassigned

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
candidates from data, diff them against what's currently pinned in code, and hand a human (or a
reviewed PR) a small, concrete change — not a live-rendered "always trust the data" system.

This is why a periodic **Claude skill** fits better than a build-time Python check: it needs
judgment (does this new peak deserve a badge? what should the caption say?), it runs occasionally
(after a data refresh or on demand), and its output is a proposed diff to review, not a page that
silently changes.

## Proposed shape: `/strava-superlatives` skill

A new skill (`.claude/skills/strava-superlatives/` or a `.claude/commands/strava-superlatives.md`
slash command, TBD — see Open Questions) that:

1. **Computes live candidates** for each superlative category directly from `strava-data/data/*.csv`
   + `data/streams/*.csv`: max `total_elevation_gain_m` single-activity peak, max/min latitude
   (northernmost/southernmost) and longitude (easternmost/westernmost) among away-activity start
   points, tallest "home-adjacent" peak (needs a definition — see below), longest single climb
   (max altitude gain within one continuous ascent in a stream), first activity in each home box.
2. **Diffs against the pinned dicts** — reads `_PASSPORT_TRIPS` badges and `_PEAKS_DEF` values out of
   `charts_places.py` (source-parse or a small extracted data file, see Open Questions) and compares
   live candidates to pinned `value`/`sig`.
3. **Reports, doesn't rewrite silently.** Output is a short list: "current pinned Highest point =
   14,507 ft (Mt. Whitney); live candidate = 15,200 ft (activity 'Long's Peak', 2026-07-24) — update?"
   For each drifted entry, propose the literal code edit (new `value`, `title`, `sig`) but let the
   human/agent confirm caption wording before editing `charts_places.py`.
4. **Flags fork mismatches as a distinct case**: if a pinned `sig` matches zero activities in the
   current athlete's data *and* the athlete's total activity count is large enough that this isn't
   just "haven't gone yet," suggest the entry be cleared or replaced rather than left as dead
   editorial copy pointing at someone else's trip.

## Immediate hardening (independent of the skill, worth doing regardless)

These are cheap correctness fixes that reduce the blast radius for forks even before the skill
exists — call out separately since they don't require the skill to land:

- **Guard `_peaks_data()`** (`:1946`) to skip appending a row when `act is None` (mirroring the
  Passport loop's existing `if sigact is None: continue` at `:1855-1856`), so a fork's Peaks book
  shows fewer rows instead of invented ones.
- **Guard `_centroid()`** (`:338`) or its callers against empty `pts`, and/or make `_SD_BOX`/
  `_BOS_BOX` configurable (e.g. `dashboard/config.py`, or a small `homes.json` read at build time)
  so a fork can set their own home cities in one place instead of hunting through
  `charts_places.py` — and so the build degrades (skip the home cards / print a warning) instead of
  crashing when the boxes don't match the data.

## Open questions

- **Where do `_PASSPORT_TRIPS`/`_PEAKS_DEF` live?** Keeping them as Python dicts in
  `charts_places.py` is simplest today but means the skill has to edit source code. Extracting them
  to a small YAML/JSON "editorial config" file (superlative value + title + `sig` + badge) would let
  the skill propose a data-file diff instead of a code diff — lower risk, easier to review, and
  arguably cleaner for forks to swap out too. Worth deciding before building the skill rather than
  after.
- **Definition of "home-adjacent giant."** Right now it's one hardcoded row (San Jacinto). A live
  version needs a rule — e.g. "tallest peak whose start point is within N miles of a home box" —
  that a human should sign off on before the skill starts proposing replacements for it.
- **Cadence / trigger.** Options: (a) manual slash command run whenever the athlete feels like it;
  (b) chained onto `strava-fetch.yml`'s data refresh as an optional check step (report-only, doesn't
  block deploy); (c) a periodic Routine (see `mcp__Claude_Code_Remote__create_trigger`) that pings
  the athlete when a candidate drifts. Start with (a); consider (b)/(c) once the skill is proven out.
- **Scope of "compute live":** easternmost/northernmost/highest-point are cheap and unambiguous.
  "Longest single climb" needs a climb-segmentation heuristic (contiguous ascent in a stream) that
  doesn't exist yet anywhere in the codebase — may need its own small analysis pass, possibly
  reusing `strava-data-analyst`'s existing methods if any overlap with segment/climb analysis.
- **Does this want a new agent, or is the existing `strava-maintenance` agent (health-checks the
  pipeline, read-only + web research) the right home for this instead of a new skill?** Superlative
  drift-checking is conceptually similar to "is the dashboard still healthy," but maintenance is
  read-only/no-edits today — this would need either a new capability there or a separate skill that
  can propose (not necessarily apply) edits.

## Suggested phases (once open questions are resolved)

1. **Analyze:** pin down the live-computation recipe for each of the 6 Peaks rows + Passport badges,
   verify against today's known values (Whitney 14,507 ft, Vancouver 49.3°N, Maine 70.2°W, San
   Jacinto 10,800 ft) the same way `strava-data-analyst` verifies other Places numbers.
2. **Decide config location** for the pinned dicts (stay in `charts_places.py` vs. extract to a data
   file) — this shapes everything downstream.
3. **Build the skill**: read live data + pinned config, diff, print a human-readable report with
   proposed edits; no auto-apply in v1.
4. **Harden for forks** independent of the skill (the two guard fixes above), so a fresh clone is
   safe on day one even before anyone runs the skill.
5. **QA:** run the skill against the current repo (should report "no drift"), then against a
   synthetic fork-like dataset (no activities in `_SD_BOX`/`_BOS_BOX`, no title matching any `sig`)
   to confirm it reports cleanly instead of crashing or inventing claims.
6. **Optional v2:** wire into a Routine (per Open Questions on cadence) once the manual flow is
   trusted.

## Related

- Feature build plan: [`Plans/strava-data/places-plan.md`](places-plan.md) (original Places build,
  established the hardcoded-editorial-copy pattern this doc is trying to loosen).
- Unrelated open item on the same section: [`Plans/strava-data/places-future-work.md`](places-future-work.md)
  (mobile chrome crowding — different problem, same file).
