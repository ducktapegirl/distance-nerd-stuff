"""Geography: region clustering, home boxes, and the pinned record book.

The boxes and the peaks list are copied from ``dashboard/charts_places.py``
(``_STATE_BOXES``, ``_SD_BOX``/``_BOS_BOX``, ``_PEAKS_DEF``) rather than
imported, because that module drags in plotly and a MapTiler key. **They can
drift**: if the dashboard's copies change, these want the same edit. Hoisting
them into ``nerd_common/`` is the real fix and is deliberately out of scope.
"""

import csv
import math
import os
from functools import lru_cache

from nerd_common.format import maybe_float as mf

from .config import KM_TO_MI, STREAMS_DIR

SD_BOX = (32.5, 33.5, -117.6, -116.6)
BOS_BOX = (41.9, 42.9, -71.8, -70.7)

# (label, lat_lo, lat_hi, lng_lo, lng_hi). Coarse on purpose: a point is
# attributed to the first box that contains it, and anything uncovered falls
# into a single "elsewhere" bucket rather than being guessed at.
STATE_BOXES = [
    ("CA", 32.5, 42.0, -124.5, -114.1),
    ("NV", 35.0, 42.0, -120.0, -114.0),
    ("AZ", 31.3, 37.0, -114.8, -109.0),
    ("OR", 42.0, 46.3, -124.6, -116.4),
    ("WA", 45.5, 49.0, -124.8, -116.9),
    ("BC", 48.9, 60.0, -139.1, -114.0),
    ("MA", 41.2, 42.9, -73.5, -69.9),
    # VT before NH, and the two split at -72.0: the states overlap in
    # longitude, and first-match order otherwise files Vermont as New Hampshire.
    ("VT", 42.7, 45.1, -73.5, -72.0),
    ("NH", 42.7, 45.4, -72.0, -70.6),
    ("ME", 43.0, 47.5, -71.1, -66.9),
    ("NY", 40.5, 45.0, -79.8, -71.8),
    ("MI", 41.7, 48.3, -90.4, -82.1),
    ("QC", 45.0, 62.0, -79.8, -57.1),
]

# Hand-curated superlatives, mirroring the dashboard's Peaks record book.
PEAKS = [
    ("HIGHEST POINT", "14,507 ft", "Mt. Whitney via Whitney Portal & JMT"),
    ("NORTHERNMOST", "49.3°N", "Stanley Park, Vancouver"),
    ("HOME-ADJACENT GIANT", "10,800 ft", "Mt. San Jacinto from Marion Trailhead"),
    ("EASTERNMOST", "70.2°W", "Maine Hut Trail — Day 3"),
    ("LONGEST SINGLE CLIMB", "6,752 ft", "Mt. Whitney via Whitney Portal & JMT"),
]


def in_box(lat, lng, box):
    lo_lat, hi_lat, lo_lng, hi_lng = box
    return lo_lat <= lat <= hi_lat and lo_lng <= lng <= hi_lng


def haversine_km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def start_points(acts):
    """(lat, lng) for every activity that has one. 8% are indoor and have none."""
    pts = []
    for r in acts:
        s = (r.get("start_latlng") or "").strip()
        if not s or "," not in s:
            continue
        lat, lng = s.split(",", 1)
        lat, lng = mf(lat), mf(lng)
        if lat is not None and lng is not None:
            pts.append((lat, lng))
    return pts


def count_regions(pts, threshold_km=10.0):
    """Greedy running-centroid clustering: a point joins the first cluster
    within ``threshold_km``, else opens a new one.

    The threshold stays metric at 10 km to match the dashboard's
    ``_count_regions``, so the two agree on region counts; the cards state it
    as ~6 mi, since everything the panel shows a reader is in miles.
    """
    centroids, counts = [], []
    for p in pts:
        for i, cen in enumerate(centroids):
            if haversine_km(p, cen) <= threshold_km:
                n = counts[i]
                centroids[i] = ((cen[0] * n + p[0]) / (n + 1),
                                (cen[1] * n + p[1]) / (n + 1))
                counts[i] = n + 1
                break
        else:
            centroids.append(p)
            counts.append(1)
    return len(centroids)


def count_states(pts):
    """Distinct labelled boxes touched, plus one bucket for anything uncovered."""
    seen, uncovered = set(), 0
    for lat, lng in pts:
        for label, *box in STATE_BOXES:
            if in_box(lat, lng, tuple(box)):
                seen.add(label)
                break
        else:
            uncovered += 1
    return sorted(seen), uncovered


def home_stats(acts):
    """Miles ridden/run inside each home box."""
    out = {}
    for key, box in (("sd", SD_BOX), ("bos", BOS_BOX)):
        mi = 0.0
        n = 0
        for r in acts:
            s = (r.get("start_latlng") or "").strip()
            if not s or "," not in s:
                continue
            lat, lng = (mf(v) for v in s.split(",", 1))
            if lat is not None and lng is not None and in_box(lat, lng, box):
                mi += r["_mi"]
                n += 1
        out[key] = {"mi": mi, "n": n}
    return out


@lru_cache(maxsize=1)
def all_tracks(cap=64, max_files=400):
    """Every GPS track, heavily simplified, normalised per-track to 0..1.

    Memoized: several cards want this and the full read is ~1.8 s for 374
    files, which is fine once and wasteful four times.
    """
    tracks = []
    names = sorted(f for f in os.listdir(STREAMS_DIR) if f.endswith(".csv"))
    for name in names[:max_files]:
        pts = []
        with open(os.path.join(STREAMS_DIR, name), encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                lat, lng = mf(row.get("lat")), mf(row.get("lng"))
                if lat is not None and lng is not None:
                    pts.append((lng, lat))
        if len(pts) < 8:
            continue
        if len(pts) > cap:
            step = len(pts) / cap
            pts = [pts[int(i * step)] for i in range(cap)]
        tracks.append((name[:-4], normalise(pts)))
    return tuple(tracks)


def normalise(pts):
    """Scale a lng/lat track so its dominant axis spans 0..1.

    Latitude degrees are ~1/cos(lat) wider on the ground than longitude
    degrees; without the correction every route renders squashed.
    """
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    coslat = math.cos(math.radians((y0 + y1) / 2)) or 1.0
    w = max((x1 - x0) * coslat, 1e-9)
    h = max(y1 - y0, 1e-9)
    scale = max(w, h)
    path = [((x - x0) * coslat / scale, (h - (y - y0)) / scale) for x, y in pts]
    return {"path": path, "w": w / scale, "h": h / scale}
