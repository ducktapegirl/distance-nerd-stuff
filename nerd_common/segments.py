"""Strava segments excluded from every record, chart, card and summary.

Some segments are noise — a joke name on a ten-second stretch of trail that
says nothing about the athlete — yet they still win "latest PR" and crowd the
leaderboards. This is the one list of them. The raw CSVs under
``strava-data/data/`` keep every effort (the fetch layer is never edited to
hide data); each reader drops these rows at load time instead:

- ``strava-data/analyze_segments.py`` (so ``segments_summary.csv`` omits them)
- ``strava-data/dashboard/data.py`` (``load_segments``, ``load_segment_efforts``)
- ``strava-data/feed/metrics.py`` (``load``, for both e-paper panels)

To exclude another segment, add its id here — nowhere else. ``strava-data/qa.py``
fails if an excluded segment's name still reaches the built dashboard.
"""

# segment_id -> name. Ids are strings because the CSVs are read as text; the
# name is for the reader of this file and for the qa.py check.
EXCLUDED_SEGMENTS = {
    "6790509": "Oops, I crapped my pants on Lenkeit bridge",
}


def is_excluded(row):
    """True when a segment or segment-effort row belongs to an excluded segment."""
    return str(row.get("segment_id", "")).strip() in EXCLUDED_SEGMENTS


def drop_excluded(rows):
    """Return ``rows`` without any row from an excluded segment."""
    return [r for r in rows if not is_excluded(r)]
