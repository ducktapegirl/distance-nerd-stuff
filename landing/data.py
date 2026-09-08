"""Read the two CSVs and reduce each to the handful of numbers a tile shows.

Deliberately thin. The tiles carry two or three stat lines apiece — the art is
the point, not the numbers — so this computes exactly those and stops. Anything
richer belongs in the dashboard the tile links to.
"""

import csv
import os

from .config import ACTIVITIES_CSV, RUNNING_LOG_CSV

KM_PER_MILE = 1.609344


def _rows(path, encoding):
    """Read a CSV to a list of dicts; empty list if the file isn't there.

    Missing inputs are normal, not exceptional: strava-data/data/streams/ and
    friends are gitignored, and a fresh clone or a fork PR may have only some of
    them. The page degrades to fewer stat lines rather than failing the build.
    """
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding=encoding) as f:
        return list(csv.DictReader(f))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def load_college():
    """running_log.csv → {rows, stats}. utf-8-sig: the file carries a BOM."""
    rows = _rows(RUNNING_LOG_CSV, "utf-8-sig")
    if not rows:
        return {"rows": [], "stats": []}

    dates = sorted(r["date"] for r in rows if r.get("date"))
    miles = sum(_num(r.get("miles")) for r in rows)
    return {
        "rows": rows,
        "kicker": f"{dates[0][:4]} – {dates[-1][:4]}",
        "stats": [
            f"{len(rows):,} runs",
            f"{miles:,.0f} miles",
        ],
    }


def load_strava():
    """activities.csv → {rows, stats}. Streams are not read here."""
    rows = _rows(ACTIVITIES_CSV, "utf-8")
    if not rows:
        return {"rows": [], "stats": []}

    dates = sorted(r["start_date_local"] for r in rows if r.get("start_date_local"))
    miles = sum(_num(r.get("distance_km")) for r in rows) / KM_PER_MILE
    sports = len({r.get("sport_type") for r in rows if r.get("sport_type")})
    return {
        "rows": rows,
        "kicker": f"{dates[0][:4]} – {dates[-1][:4]}",
        "stats": [
            f"{len(rows):,} activities",
            f"{miles:,.0f} miles",
            f"{sports} sports",
        ],
    }
