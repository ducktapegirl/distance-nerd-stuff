"""Track reading, simplification and fitting — shared by every art surface.

This is the canonical home for the cos-lat projection and the geometry helpers
the hand-built SVG artwork is made of. Before this module existed the same
`track()` / `simplify()` / `path()` lived in three places at once
(`strava-data/dashboard/art_year.py`, `landing/geometry.py`,
`strava-data/tools/poster_40for40.py`), each copy justified by the fact that
importing `dashboard.art_year` drags in `dashboard.config`, which calls
`load_dotenv()` and reads `MAPTILER_KEY`.

`nerd_common` is the designated shared package and both dashboards already
import it, so the duplication is retired here rather than extended.

⚠ Why this module cannot import a path config of its own: `running-log/` and
`strava-data/` each ship a package literally named `dashboard`, and each build
puts its own parent on `sys.path[0]`. `nerd_common` is installed and has no
notion of repo layout. So the per-activity stream directory is **injected** —
call `set_streams_dir(path)` once at import time, or pass `streams_dir=` per
call. There is no default and no guess.

`poster_40for40.py` deliberately still keeps its own copy: it is a standalone
print tool outside every build, and folding it in is a separate change.

Reads use `csv.reader` with header indices rather than `csv.DictReader`. The
art touches every stream on every build (378 files, ~700k rows) and DictReader
builds a dict per row for columns nobody asked for. Output is identical.

Dependency rule: stdlib only. Nothing here may import plotly, numpy, or either
dashboard package.
"""

import csv
import math
import os

# Set by whichever build is running; see the module docstring. Deliberately
# None rather than a guessed path — a wrong default reads as "no streams", and
# every caller here degrades silently on a missing file, so a bad guess would
# surface as art with no marks rather than as an error.
STREAMS_DIR = None


def set_streams_dir(path):
    """Point the stream readers at strava-data/data/streams for this process."""
    global STREAMS_DIR
    STREAMS_DIR = path


# Five sport families. The poster keeps six and splits snow by direction of
# travel; here all snow is one family and skating sits in "other", so a color
# is not spent on a handful of activities.
FAMILY = {
    "Run": "run", "TrailRun": "run",
    "MountainBikeRide": "mtb", "Ride": "mtb", "EBikeRide": "mtb",
    "Hike": "foot", "Walk": "foot",
    "AlpineSki": "snow", "Snowboard": "snow", "NordicSki": "snow",
    "IceSkate": "other", "RockClimbing": "other", "WeightTraining": "other",
    "Workout": "other", "Pickleball": "other", "StandUpPaddling": "other",
    "Pilates": "other",
}

COLOR = {"run": "#2dd4bf", "mtb": "#f59e0b", "foot": "#a3e635",
         "snow": "#60a5fa", "other": "#f472b6"}


def _open_stream(aid, *want, streams_dir=None):
    """(rows_iter, [column indices]) for one stream, or (None, None).

    A missing stream is normal, not exceptional — callers degrade to fewer
    marks rather than raising.
    """
    base = streams_dir or STREAMS_DIR
    if not base:
        return None, None
    fp = os.path.join(base, str(aid) + ".csv")
    if not os.path.exists(fp):
        return None, None
    f = open(fp, newline="", encoding="utf-8-sig")
    rd = csv.reader(f)
    try:
        hdr = next(rd)
        idx = [hdr.index(c) for c in want]
    except (StopIteration, ValueError):
        f.close()
        return None, None
    return (rd, f), idx


def track(aid, step=6, streams_dir=None):
    """Lat/lng track projected to local meters, recentered on its own start.

    y is negated so the result is already in SVG's y-down space. Returns [] for
    anything with fewer than four usable points.
    """
    handle, idx = _open_stream(aid, "lat", "lng", streams_dir=streams_dir)
    if handle is None:
        return []
    rd, f = handle
    ilat, ilng = idx
    pts = []
    try:
        for i, row in enumerate(rd):
            if i % step or len(row) <= ilng or not row[ilat]:
                continue
            try:
                pts.append((float(row[ilat]), float(row[ilng])))
            except ValueError:
                pass
    finally:
        f.close()
    if len(pts) < 4:
        return []
    lat0 = sum(q[0] for q in pts) / len(pts)
    k = math.cos(math.radians(lat0))
    return [((lng - pts[0][1]) * k * 111320.0, -(lat - pts[0][0]) * 110540.0)
            for lat, lng in pts]


def altitude(aid, n=48, streams_dir=None):
    """A stream's `altitude_m` column resampled to n evenly spaced points.

    Never parses lat/lng — an elevation-only direction should not pay for the
    projection. Nearest-neighbor rather than averaging: a ridgeline wants its
    peaks kept, and an averaging resample rounds them off.
    """
    handle, idx = _open_stream(aid, "altitude_m", streams_dir=streams_dir)
    if handle is None:
        return []
    rd, f = handle
    ia = idx[0]
    vals = []
    try:
        for row in rd:
            if len(row) > ia and row[ia]:
                try:
                    vals.append(float(row[ia]))
                except ValueError:
                    pass
    finally:
        f.close()
    if len(vals) < n:
        return []
    last = len(vals) - 1
    return [vals[round(i * last / (n - 1))] for i in range(n)]


def simplify(pts, eps=0.5):
    """Douglas-Peucker, iterative so a long track cannot blow the stack.

    Must run on points already projected into the units they are drawn in — a
    tolerance means nothing until the points are in that space.
    """
    n = len(pts)
    if n < 3 or eps <= 0:
        return pts
    keep = [False] * n
    keep[0] = keep[n - 1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        x1, y1 = pts[i]
        x2, y2 = pts[j]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-9
        far, fi = -1.0, -1
        for k in range(i + 1, j):
            x, y = pts[k]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
            if d > far:
                far, fi = d, k
        if far > eps:
            keep[fi] = True
            stack.append((i, fi))
            stack.append((fi, j))
    return [p for p, k in zip(pts, keep) if k]


def thin(pts, cap):
    """Evenly drop points until at most `cap` remain, always keeping the ends.

    Runs after simplify(): Douglas-Peucker removes what is geometrically
    redundant, this enforces a hard byte budget on what survives.
    """
    n = len(pts)
    if n <= cap or cap < 2:
        return pts
    return [pts[round(i * (n - 1) / (cap - 1))] for i in range(cap)]


def path(pts, nd=1):
    """"M x y L x y …" at `nd` decimal places."""
    if not pts:
        return ""
    fmt = "%%.%df %%.%df" % (nd, nd)
    return "M" + "L".join(fmt % (x, y) for x, y in pts)


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def fit(pts, x0, y0, w, h, pad=0.0):
    """Scale points into a box, preserving aspect and centering.

    Aspect is preserved rather than stretched: a route squashed to fill a
    non-square cell stops being the shape that was actually run.
    """
    if not pts:
        return []
    minx, miny, maxx, maxy = bbox(pts)
    sw, sh = max(maxx - minx, 1e-9), max(maxy - miny, 1e-9)
    s = min((w - 2 * pad) / sw, (h - 2 * pad) / sh)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    return [(x0 + w / 2 + (x - cx) * s, y0 + h / 2 + (y - cy) * s) for x, y in pts]


def rotate(pts, rad):
    c, s = math.cos(rad), math.sin(rad)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]
