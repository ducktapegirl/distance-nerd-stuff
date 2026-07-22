# Future work: parse the orphaned summer03log.html

**Status:** proposed / scoped · **Created:** 2026-07-22 · **Owner:** unassigned

## Why

`running-log/source/summer03log.html` is a real training log — roughly 495 miles
across ~95 entries, per its own "Summer Total: 495.15" header — but it's invisible
to the dashboard. `parse_log.py`'s `FILES` list (`parse_log.py:26-33`) starts at
`("fall", "03")`; nothing before fall 2003 is read. `running_log.csv` has zero rows
with `source_file = summer03log.html` to show for it.

It's parked deliberately, not lost: of the 122 files originally in `source/`, this
is the one file that's real season-shaped data but isn't wired into the parser, so
it was kept in `source/` (not moved to `source/_archive/` with the ~106 site-dump
files — images, an `.exe`, non-log pages) during the 2026-07-21 repo cleanup.

## Why it's not a one-line fix

Adding `("summer", "03")` to `FILES` parses to **nothing** — the file uses a
different layout than every log that *is* parsed:

- Working logs (fall03 → spring07) have day-by-day tables whose header row reads
  `Weekday, Month Day` (e.g. `Friday, November 14`), which `parse_date_header()`
  (`parse_log.py:206`) pattern-matches to extract the date.
- `summer03log.html` has no such headers at all — its bold text is season/weekly
  totals (`Summer Total: 495.15`) and bare mileage numbers (`8.5`, `6.25`, `5+2`,
  `<7`, …), with no per-day workout/minutes/miles table structure to key off of.

So every one of its ~97 tables fails `parse_date_header()` and is silently
skipped — that's *why* it currently contributes 0 rows even though the file has
real content.

## What it would take

1. **Inspect the actual markup** of `summer03log.html` to find its real
   structure (weekly rows? a single running list? something else) — the fix
   depends entirely on what's actually there.
2. **Write a second parse path** (a `parse_file_summer_totals()` or similar)
   specific to that layout, since it can't share `parse_date_header()` /
   `extract_data()` with the day-by-day format.
3. Decide what a "date" even means for entries that may only have a week-level
   granularity — `running_log.csv`'s schema assumes one row per day
   (`CSV_COLUMNS`, `parse_log.py`), so weekly-total-only entries may need an
   approximate date, a `week_of_year`-only row, or a schema tweak.
4. Add `("summer", "03")` to `FILES` once the new path exists.

## Decisions still open

- Is a coarser (weekly, not daily) row acceptable for this one season, or should
  it be skipped unless real daily entries can be recovered?
- Does 495 miles of pre-tracked-log summer base training move any headline
  stats/records enough to be worth the effort?

## Verification (once implemented)

1. `uv run python running-log/src/parse_log.py` — confirm summer03log.html now
   reports parsed entries (not "missing") and the new rows appear in
   `running_log.csv` with `source_file = summer03log.html`.
2. `uv run python running-log/src/visualize_log.py` — rebuild `index.html`;
   spot-check that summer 2003 volume shows up in the Volume tab without
   breaking season/year ordering elsewhere.
3. `uv run python running-log/src/qa.py` — confirm no regressions.

## Out of scope

- The other 106 files in `running-log/source/_archive/` — those are confirmed
  non-log site content (images, `.exe`, non-log HTML pages), not parseable data.
- Any change to the fall03→spring07 parse path — this is additive only.
