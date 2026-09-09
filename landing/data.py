"""Read the two CSVs and reduce each to the handful of numbers a tile shows.

Deliberately thin. The tiles carry two or three stat lines apiece — the art is
the point, not the numbers — so this computes exactly those and stops. Anything
richer belongs in the dashboard the tile links to.
"""

import csv
import os

from nerd_common.geometry import set_streams_dir, track

from .config import ACTIVITIES_CSV, RUNNING_LOG_CSV, STREAMS_DIR

# nerd_common is an installed package and has no notion of repo layout, so the
# stream directory is injected rather than guessed. This is the only landing
# module that reads streams, so this is the only place it needs saying.
set_streams_dir(STREAMS_DIR)

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
        return {"rows": [], "tracks": {}, "stats": []}

    dates = sorted(r["date"] for r in rows if r.get("date"))
    # The log carries a row per logged day — rest days, pool sessions and blanks
    # included — so len(rows) is not a run count. It read 1,274 against 1,138
    # rows that actually recorded distance, overstating the front door by ~12%.
    # Counting the rows with mileage also makes the two stats describe the same
    # set, since that is exactly what `miles` sums over.
    #
    # Cross-training is deliberately NOT filtered out of that. `workout_type` is
    # free text with 52 distinct values; only 9 rows with mileage look like
    # cross-training at all, and 6 of those are hybrids ("run/aquajog") that did
    # include running. Classifying 52 strings to move 3 rows and 22 miles would
    # invent a judgement the running-log dashboard itself declines to make — its
    # WORKOUT_TYPE_MAP folds bike, pool and elliptical in with intervals.
    ran = [r for r in rows if _num(r.get("miles")) > 0]
    miles = sum(_num(r.get("miles")) for r in ran)
    return {
        "rows": rows,
        "kicker": f"{dates[0][:4]} – {dates[-1][:4]}",
        "stats": [
            f"{len(ran):,} runs",
            f"{miles:,.0f} miles",
        ],
    }


def load_strava():
    """activities.csv → {rows, tracks, stats}.

    `tracks` is the per-activity GPS the Route Grid tile draws — every stream
    that has one, projected and recentered by geometry.track(). Reading all 378
    costs about 1.5 s, which is the most expensive thing this build does and
    still nothing beside `uv sync`; they are committed, so CI, fork PRs and
    fresh clones all have them and no precomputed asset is needed.

    Loading every track rather than only the 48 that get drawn is deliberate:
    the grid ranks candidates on the *shape* of their bounding box, so the
    selection cannot be made before the geometry is in hand.
    """
    rows = _rows(ACTIVITIES_CSV, "utf-8")
    if not rows:
        return {"rows": [], "tracks": {}, "stats": []}

    tracks = {}
    for r in rows:
        t = track(r["id"], step=8)
        if t:
            tracks[r["id"]] = t

    dates = sorted(r["start_date_local"] for r in rows if r.get("start_date_local"))
    miles = sum(_num(r.get("distance_km")) for r in rows) / KM_PER_MILE
    sports = len({r.get("sport_type") for r in rows if r.get("sport_type")})
    return {
        "rows": rows,
        "tracks": tracks,
        "kicker": f"{dates[0][:4]} – {dates[-1][:4]}",
        "stats": [
            f"{len(rows):,} activities",
            f"{miles:,.0f} miles",
            f"{sports} sports",
        ],
    }
