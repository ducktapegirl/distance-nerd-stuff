#!/usr/bin/env python3
"""
Backfill average_temp_c in activities.csv using Open-Meteo historical weather.

Reads the existing CSV, finds rows where average_temp_c is blank but
start_latlng and start_date_local are present, fetches the temperature
for each, and rewrites the CSV in-place.

Usage:
    python backfill_weather.py           # all activities missing temp
    python backfill_weather.py --dry-run # preview without writing
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

# Allow emoji in activity names on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from weather import fetch_weather_temp

_HERE    = Path(__file__).parent
DATA_DIR = _HERE / "data"
ACT_CSV  = DATA_DIR / "activities.csv"


def parse_latlng(s: str):
    """Parse 'lat,lon' string into (float, float) or (None, None)."""
    if not s or not s.strip():
        return None, None
    parts = s.strip().split(",")
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None, None


def main():
    parser = argparse.ArgumentParser(description="Backfill weather temperature into activities.csv")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be updated without writing.")
    args = parser.parse_args()

    if not ACT_CSV.exists():
        sys.exit(f"Not found: {ACT_CSV}")

    # Read full CSV
    with open(ACT_CSV, newline="", encoding="utf-8-sig") as f:
        reader    = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows      = list(reader)

    if "average_temp_c" not in fieldnames:
        sys.exit("'average_temp_c' column not found in activities.csv — unexpected schema.")

    # Identify rows that need backfill
    to_fill = [
        r for r in rows
        if not r.get("average_temp_c")          # blank / zero / None
        and r.get("start_latlng")
        and r.get("start_date_local")
    ]

    total   = len(rows)
    missing = len(to_fill)
    print(f"Activities total:            {total}")
    print(f"Missing average_temp_c:      {missing}")
    print(f"Already have average_temp_c: {total - missing}")

    if missing == 0:
        print("Nothing to do.")
        return

    if args.dry_run:
        print("\n[dry-run] Would fetch temperature for:")
        for r in to_fill[:10]:
            print(f"  {r['start_date_local'][:10]}  {r['name'][:50]}")
        if missing > 10:
            print(f"  … and {missing - 10} more.")
        return

    print(f"\nFetching temperatures from Open-Meteo…  (~{missing * 0.15:.0f}s minimum)\n")

    updated = 0
    errors  = 0

    for i, r in enumerate(to_fill, 1):
        lat, lon = parse_latlng(r["start_latlng"])
        if lat is None:
            continue

        try:
            dt_local = datetime.strptime(r["start_date_local"][:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        temp = fetch_weather_temp(lat, lon, dt_local)

        status = ""
        if temp is not None:
            r["average_temp_c"] = temp
            updated += 1
            status = f"{temp:.1f}°C"
        else:
            errors += 1
            status = "no data"

        print(f"  [{i:3d}/{missing}] {r['start_date_local'][:10]}  "
              f"{r['name'][:40]:<40}  {status}")

    print(f"\n  Updated: {updated}   No data: {errors}")

    if updated == 0:
        print("Nothing changed — skipping write.")
        return

    # Rewrite CSV (preserve column order)
    with open(ACT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Saved → {ACT_CSV}")


if __name__ == "__main__":
    main()
