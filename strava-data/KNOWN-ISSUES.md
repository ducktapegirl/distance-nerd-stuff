# Known Issues — Strava Data Pipeline

## segment_efforts.csv schema drift (header/row mismatch)

**Status:** RESOLVED 2026-06-10 (Option A implemented same day; details below kept for reference)

**Resolution summary:**
- Migrated `data/segment_efforts.csv` to the 21-column schema: captured `sport_type` from
  index 1 of the 186 drifted rows, backfilled it for the 1,255 older rows via
  `activity_id` → `activities.csv` join (0 mismatches, 0 missing). Backup kept at
  `data/segment_efforts.csv.bak-20260610` (not committed).
- Added the header-mismatch guard to `csv_append()` in `fetch.py` — future schema drift
  now fails loudly before writing.
- Regenerated `segments_summary.csv` via `analyze_segments.py`: 616 → 693 segments
  (77 segments from the drifted weeks were previously dropped/mis-keyed). Rebuilt both
  dashboard HTML outputs.
- Bonus fix: `analyze_segments.py` crashed on cp1252 consoles printing unicode trend
  arrows/segment names; stdout now reconfigured with `errors="replace"`.
- All verification steps below passed (1,441 rows, uniform 21-col width, pandas loads
  clean, date range through 2026-06-07, drifted-row spot-check values land in the
  correct columns).

---

*Original report (for reference):*
**Severity:** Data loss on read — 186 of 1,441 effort rows (13%), including *all* efforts
fetched since 2026-04-20, are silently dropped or misaligned by standard CSV readers.

### Symptom

`data/segment_efforts.csv` has a **20-column header** but every row appended since
2026-04-20 has **21 fields**. Effects depend on the reader:

- `pandas.read_csv` (C engine): the 186 over-wide rows error out or get skipped
  (with `on_bad_lines="skip"` they vanish silently). Any analysis quietly excludes
  the most recent ~7 weeks of efforts (17 activities, 2026-04-20 → 2026-06-07).
- Naive `csv.DictReader`: the 21st value lands in `None`/rest-key, and **every column
  after `activity_id` is shifted one position right** for those rows — e.g.
  `segment_id` holds a sport string, `elapsed_time_s` holds `moving_time_s`, etc.
  Numbers parse "successfully" but are wrong.

### Root cause

A `sport_type` field was added to the effort schema in `fetch.py`, but the on-disk
file was never migrated:

- `fetch.py:92-93` — `SEGMENT_EFFORTS_FIELDS` now starts
  `["activity_id", "sport_type", "segment_id", ...]` (21 fields).
- `fetch.py:387-395` — `csv_append()` only writes a header **when the file does not
  exist** (`write_header = not path.exists()`). It never checks that the existing
  header matches `fieldnames`.
- The file on disk still has the original 20-column header
  (`activity_id,segment_id,segment_name,...` — no `sport_type`).

So every fetch since the field was added appends 21-value rows under the 20-column
header, with the rogue `sport_type` value sitting at **index 1**, between
`activity_id` and `segment_id`.

### Affected data

- File: `strava-data/data/segment_efforts.csv`
- Clean rows: 1,255 (20 fields, through 2026-04-19)
- Drifted rows: 186 (21 fields, efforts dated 2026-04-20 → 2026-06-07, 17 activities)
- Not affected: `activities.csv`, `segments_summary.csv` (and none of the 8
  Exploratory-tab charts read this file)

### Verified read-side workaround (recovery recipe)

Until the file is fixed, read with the `csv` module and normalize row width
(validated to recover all 1,441 rows during the 2026-06-10 analysis):

```python
import csv

with open("strava-data/data/segment_efforts.csv", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)          # 20 columns, no sport_type
    rows = []
    for rec in reader:
        if len(rec) == 21:         # drifted row: sport_type was inserted at index 1
            rec = rec[:1] + rec[2:]
        rows.append(dict(zip(header, rec)))
```

(If you *want* the sport_type, capture `rec[1]` before dropping it.)

### Potential fixes (pick one data fix + the guard)

**Option A — migrate the file forward (recommended).** One-time script:
read with the recipe above, keep the captured `sport_type` for 21-field rows,
backfill it for the 1,255 old rows by joining `activity_id` →
`activities.csv.sport_type`, then rewrite the whole file with the new 21-column
header matching `SEGMENT_EFFORTS_FIELDS`. Keeps the new field, heals history,
and matches what `fetch.py` already writes. Back up the original first.

**Option B — roll the schema back.** Remove `"sport_type"` from
`SEGMENT_EFFORTS_FIELDS` in `fetch.py` (the `DictWriter(..., extrasaction="ignore")`
makes this safe — the value is simply no longer written), then rewrite the 186
drifted rows once using the recovery recipe to drop index 1. Simplest, but loses
a useful field; per-effort sport can still be derived by joining to
`activities.csv`.

**Option C — full refetch.** Delete `segment_efforts.csv` and re-run `fetch.py`
so `csv_append` writes a fresh 21-column header. Cleanest result, but re-fetching
all activity details is slow and costs Strava API quota.

**Guard (do this regardless):** make `csv_append()` in `fetch.py` fail loudly on
drift instead of corrupting silently:

```python
def csv_append(path, rows, fieldnames):
    if not rows:
        return
    write_header = not path.exists()
    if not write_header:
        with open(path, newline="", encoding="utf-8") as f:
            existing = next(csv.reader(f))
        if existing != fieldnames:
            raise SystemExit(
                f"{path.name}: header {len(existing)} cols != schema "
                f"{len(fieldnames)} cols - migrate the file before fetching"
            )
    ...
```

### Verification after fixing

1. `python -c` check: every row has exactly `len(header)` fields.
2. Row count still 1,441 (no rows lost in migration).
3. `pandas.read_csv("data/segment_efforts.csv")` loads 1,441 rows with no
   warnings, and `start_date_local.max()` is 2026-06-07 (the recent rows are back).
4. Spot-check one drifted-era row against the Strava website (effort time matches
   `elapsed_time_s`, not a shifted neighbor).
