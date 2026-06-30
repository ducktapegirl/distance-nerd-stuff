#!/usr/bin/env python3
"""
Backfill retroactive Strava segments into segment_efforts.csv.

When you create a new Strava segment, Strava retroactively matches it against
your existing activities (the matching window only reaches back ~1 year). Those
new segment efforts live on Strava's side but are absent from the local dataset,
because fetch.py never re-fetches an activity it has already pulled.

This script re-fetches ONLY the activity detail endpoint (1 request per activity,
vs. fetch.py's 3 with streams + laps) for activities in a recent time window,
re-extracts their current segment efforts, and merges them into
data/segment_efforts.csv with replace-semantics: every re-fetched activity's
rows are replaced wholesale, so newly-matched segments appear and nothing is
duplicated. The run is therefore idempotent.

It reuses fetch.py's auth, rate limiter (95 req / 15 min + 429 handling), and
segment-effort extraction, so a few hundred detail calls stay safely under
Strava's limits.

Usage:
    python backfill_segments.py                 # ~13-month window (396 days)
    python backfill_segments.py --dry-run       # preview targets, no API calls
    python backfill_segments.py --days 30       # only the last 30 days
    python backfill_segments.py --since 2025-01-01   # on/after a date

After running, regenerate the rollup + dashboard:
    python analyze_segments.py
    python build_dashboard.py
"""
import argparse
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow emoji in activity names on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tqdm import tqdm

from fetch import (get_access_token, api_get, extract_segment_efforts,
                   SEGMENT_EFFORTS_FIELDS)

_HERE       = Path(__file__).parent
DATA_DIR    = _HERE / "data"
ACT_CSV     = DATA_DIR / "activities.csv"
EFFORTS_CSV = DATA_DIR / "segment_efforts.csv"

DEFAULT_DAYS = 396   # ~13 months — a buffer past Strava's ~1-year match window


def parse_local_dt(s):
    """Parse 'YYYY-MM-DD HH:MM:SS' (as written by fetch.py) into a datetime."""
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip()[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def load_target_activities(cutoff):
    """Return [(activity_id, start_dt)] for activities on/after `cutoff`."""
    if not ACT_CSV.exists():
        sys.exit(f"Not found: {ACT_CSV}")
    targets = []
    with open(ACT_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            aid = (row.get("id") or "").strip()
            dt = parse_local_dt(row.get("start_date_local"))
            if aid and dt and dt >= cutoff:
                targets.append((aid, dt))
    targets.sort(key=lambda t: t[1])   # oldest first, for readable progress
    return targets


def load_existing_efforts():
    """Return (rows, header). Verifies the header matches the current schema."""
    if not EFFORTS_CSV.exists():
        return [], None
    with open(EFFORTS_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = list(reader)
    # Same drift guard as fetch.py's csv_append: appending/merging under a stale
    # header silently corrupts the file (see KNOWN-ISSUES.md, 2026-06-10).
    if header != SEGMENT_EFFORTS_FIELDS:
        sys.exit(
            f"{EFFORTS_CSV.name}: header has {len(header)} cols but the schema "
            f"has {len(SEGMENT_EFFORTS_FIELDS)} — migrate the file before backfilling."
        )
    return rows, header


def main():
    parser = argparse.ArgumentParser(
        description="Backfill retroactive segments into segment_efforts.csv.")
    parser.add_argument("--since", type=str, default=None,
                        help="Re-fetch activities on/after YYYY-MM-DD.")
    parser.add_argument("--days", type=int, default=None,
                        help=f"Re-fetch activities in the last N days "
                             f"(default {DEFAULT_DAYS}).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be re-fetched without calling the API.")
    args = parser.parse_args()

    # Resolve the cutoff: --since wins, then --days, then the default window.
    if args.since:
        try:
            cutoff = datetime.fromisoformat(args.since)
        except ValueError:
            sys.exit(f"Invalid --since date: {args.since!r} (expected YYYY-MM-DD)")
        window_desc = f"on/after {args.since}"
    else:
        days = args.days if args.days is not None else DEFAULT_DAYS
        cutoff = datetime.now() - timedelta(days=days)
        window_desc = f"last {days} days (on/after {cutoff:%Y-%m-%d})"

    targets = load_target_activities(cutoff)
    n = len(targets)

    print(f"Window:               {window_desc}")
    print(f"Activities to re-fetch: {n}")
    if n:
        print(f"Date range:           {targets[0][1]:%Y-%m-%d} → {targets[-1][1]:%Y-%m-%d}")

    if n == 0:
        print("Nothing to do.")
        return

    if args.dry_run:
        # One detail call each, throttled at 95 / 15 min.
        windows = (n + 94) // 95
        est_min = max(0, windows - 1) * 15
        print(f"\n[dry-run] {n} detail requests (1 per activity), "
              f"~{est_min} min minimum at the 95/15-min cap. No API calls made.")
        for aid, dt in targets[:10]:
            print(f"  {dt:%Y-%m-%d}  activity {aid}")
        if n > 10:
            print(f"  … and {n - 10} more.")
        return

    existing_rows, _ = load_existing_efforts()
    old_effort_ids = {r.get("effort_id") for r in existing_rows}
    old_segment_ids = {r.get("segment_id") for r in existing_rows}

    token = get_access_token()

    refetched_ids = set()
    fresh_rows = []
    not_found = 0

    print(f"\nRe-fetching detail for {n} activities…\n")
    for aid, _ in tqdm(targets, unit="activity", ncols=80):
        detail = api_get(f"/activities/{aid}", token)
        if detail is None:
            not_found += 1
            tqdm.write(f"  {aid}: 404 — leaving existing rows untouched")
            continue
        refetched_ids.add(str(aid))
        fresh_rows.extend(extract_segment_efforts(aid, detail))

    # Merge with replace-semantics: drop every re-fetched activity's old rows,
    # then add back the freshly-extracted set (which includes new segments).
    kept = [r for r in existing_rows if str(r.get("activity_id")) not in refetched_ids]
    merged = kept + fresh_rows

    new_effort_ids = {r.get("effort_id") for r in fresh_rows}
    new_segment_ids = {r.get("segment_id") for r in fresh_rows}
    net_new_efforts = new_effort_ids - old_effort_ids
    net_new_segments = new_segment_ids - old_segment_ids

    print(f"\n  Activities re-fetched:  {len(refetched_ids)}")
    if not_found:
        print(f"  Skipped (404):          {not_found}")
    print(f"  Efforts before → after: {len(existing_rows)} → {len(merged)}")
    print(f"  Net-new efforts:        {len(net_new_efforts)}")
    print(f"  Net-new segments:       {len(net_new_segments)}")

    if not refetched_ids:
        print("\nNothing was re-fetched — leaving the file unchanged.")
        return

    # Rewrite the file (DictWriter drops the activity_id sport-type, etc. cleanly
    # via extrasaction="ignore", matching fetch.py's csv writers).
    with open(EFFORTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SEGMENT_EFFORTS_FIELDS,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged)
    print(f"\n  Saved → {EFFORTS_CSV}")

    print("\nNext steps to refresh the rollup + dashboard:")
    print("  uv run python strava-data/analyze_segments.py")
    print("  uv run python strava-data/build_dashboard.py")


if __name__ == "__main__":
    main()
