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

- **Config location: extract to a data file.** `_PASSPORT_TRIPS`/`_PEAKS_DEF` move out of
  `charts_places.py` into a small YAML/JSON editorial config (value + title + activity-id + badge
  per entry). The detection step diffs a data file, not Python source — lower risk, and a fork gets
  one obvious file to replace instead of hunting through the builder code.
- **Automation level: report only for v1.** Nothing auto-edits the data file or opens a PR. Output
  is a printed/logged diff a human acts on by hand.
- **Architecture: split CI detection from agent judgment — these cannot be the same thing.**
  `strava-fetch.yml` is a GitHub Actions workflow (deterministic scripts only); it cannot invoke a
  Claude agent mid-run. So the design is two pieces, not one:
  - **CI step (deterministic, in `strava-fetch.yml`):** a plain Python check, same pattern as the
    existing `_pinned`/`_HOME_PINNED` soft-drift prints in `charts_places.py`, that computes live
    superlative candidates and prints a NOTE to the workflow log when a candidate beats what's in
    the editorial config file. Report-only; never blocks the deploy.
  - **Agent step (`strava-maintenance`, run manually or via a Routine):** reads that signal (the
    latest drift NOTE, or just re-runs the live computation itself) and is what actually proposes
    the concrete data-file edit — deciding wording, whether a new category deserves a badge at all,
    etc. This is the "judgment" layer; it never runs inside CI.
  - `strava-maintenance`'s current toolset (Read/Grep/Glob/Bash/WebSearch/WebFetch +
    `check-strava-connection`/`get-athlete-profile`) already includes `Bash`, so it can run the same
    Python live-computation script CI uses without needing new MCP tools — the extension is scope
    (a new responsibility: propose superlative-config edits), not new tool access.
- **"Home-adjacent giant": define by distance threshold, not left permanently manual.** Rule =
  tallest peak (by `total_elevation_gain_m`) whose start point is within **N miles** of a home box.
  **N is still an open numeric detail** — pick it during the Analyze phase by checking what value
  keeps San Jacinto in and doesn't pull in something unintended, then pin it in the config alongside
  the boxes.
- **`sig` matching: move from title-substring to pinned activity ID.** Today's `sig` (e.g.
  `"Whitney"` matched against the activity title) breaks silently if the activity is ever renamed on
  Strava. Switching to a pinned Strava activity ID is more robust; the data file can still carry a
  human-readable label alongside the ID for reviewability (id is the match key, label is just
  commentary).
- **No history of superseded records.** When a superlative changes, the old value is simply
  replaced — no "previously: Whitney, 14,507 ft" footnote. Keeps the Peaks book reading as a current
  record book, not a change-log; also keeps the data file and display simpler.

## Immediate hardening (independent of the above, worth doing regardless)

Cheap correctness fixes that reduce the blast radius for forks even before any of the above lands:

- **Guard `_peaks_data()`** (`:1946`) to skip appending a row when `act is None` (mirroring the
  Passport loop's existing `if sigact is None: continue` at `:1855-1856`), so a fork's Peaks book
  shows fewer rows instead of invented ones.
- **Guard `_centroid()`** (`:338`) or its callers against empty `pts`, and/or make `_SD_BOX`/
  `_BOS_BOX` configurable (e.g. `dashboard/config.py`, or the same editorial data file) so a fork can
  set their own home cities in one place — and so the build degrades (skip the home cards / print a
  warning) instead of crashing when the boxes don't match the data.

## Remaining open items

Everything structural is decided; these are implementation details to settle during Analyze, not
before:

- **Distance threshold N** for "home-adjacent giant" (see above) — pick empirically against today's
  data, confirm San Jacinto stays in.
- **"Longest single climb" computation.** Needs a climb-segmentation heuristic (contiguous ascent
  within one activity's altitude stream) that doesn't exist anywhere in the codebase yet — check
  whether `strava-data-analyst`'s existing methods have anything reusable, or whether this is a new
  small analysis pass.
- **Data file format/schema** (YAML vs. JSON, exact field names) — pick whichever is more pleasant to
  hand-edit; JSON is already used elsewhere in the build (no new dependency), YAML is more readable
  for a hand-curated editorial file. Lean YAML unless it'd require adding a new parsing dependency.

## Suggested phases

1. **Analyze:** pin the live-computation recipe for each of the 6 Peaks rows + Passport badges
   (including the home-adjacent-giant threshold and the longest-climb heuristic), verify against
   today's known values (Whitney 14,507 ft, Vancouver 49.3°N, Maine 70.2°W, San Jacinto 10,800 ft).
2. **Extract the editorial config** — move `_PASSPORT_TRIPS`/`_PEAKS_DEF` to the new data file, keyed
   by activity ID instead of title substring; update `charts_places.py` to read from it.
3. **Harden for forks** (the two guard fixes above) so a fresh clone is safe on day one.
4. **Build the CI detection step** — deterministic script in `strava-fetch.yml`, same soft-NOTE
   pattern as existing drift checks, diffing live candidates against the new config file.
5. **Extend `strava-maintenance`** to read the drift signal (or recompute it) and propose the
   concrete config-file edit — report only, no auto-apply.
6. **QA:** confirm the CI step reports "no drift" on the current repo; run both the CI script and the
   extended `strava-maintenance` pass against a synthetic fork-like dataset (no activities in the
   home boxes, no activity ID matching any pinned entry) to confirm clean reporting instead of
   crashing or inventing claims.
7. **Optional v2:** wire `strava-maintenance`'s superlative check into a Routine
   (`mcp__Claude_Code_Remote__create_trigger`) once the manual flow is trusted, so a drift gets
   surfaced without remembering to ask.

## Related

- Feature build plan: [`Plans/strava-data/places-plan.md`](places-plan.md) (original Places build,
  established the hardcoded-editorial-copy pattern this doc is trying to loosen).
- Unrelated open item on the same section: [`Plans/strava-data/places-future-work.md`](places-future-work.md)
  (mobile chrome crowding — different problem, same file).
