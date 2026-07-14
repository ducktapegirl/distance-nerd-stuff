"""Regenerate the Places hero vector basemap asset (strava-data/assets/basemap.json).

Pulls Natural Earth 50m coastline / state-province lines / lakes, clips them to
the North-America map extent, simplifies (RDP), rounds to 3 decimals, and writes
compact flat [lng,lat,...] polyline arrays. The build (charts_places.py) inlines
this JSON into the self-contained hero -- no runtime network. Re-run only when the
map extent or source data changes:

    uv run python strava-data/tools/gen_basemap.py

Sources (public domain, Natural Earth):
    ne_50m_coastline, ne_50m_admin_1_states_provinces_lines, ne_50m_lakes
Requires network; stdlib + urllib only (no GDAL/rasterio)."""
import json, math, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "basemap.json"))
BASE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
        "master/geojson")

# Clip box: the hero frame (lat 31.96..49.98, lng -126.12..-67.99) + generous
# margin so panning/zoom-out still shows geographic context.
LAT0, LAT1 = 24.0, 55.0
LNG0, LNG1 = -135.0, -60.0

# Per-layer RDP tolerance (deg) -- coastline finer (reads at metro zoom), admin
# and lakes coarser. Coords rounded to 3 decimals (~100 m) afterward.
EPS = {"coast": 0.014, "admin": 0.025, "lakes": 0.03}

# Drop tiny lakes: keep only rings whose bounding-box diagonal exceeds this (deg)
# so the Great Lakes + a few big ones remain but the map isn't peppered with
# hundreds of ponds (weight + visual noise for a faint basemap).
LAKE_MIN_DIAG = 0.6


def _rdp(pts, eps):
    n = len(pts)
    if n < 3:
        return list(pts)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        den = math.hypot(dx, dy)
        dmax, idx = 0.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = (math.hypot(px - ax, py - ay) if den == 0
                 else abs(dy * px - dx * py + bx * ay - by * ax) / den)
            if d > dmax:
                dmax, idx = d, i
        if dmax > eps and idx != -1:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [pts[i] for i in range(n) if keep[i]]


def _in(ln, la):
    return LNG0 <= ln <= LNG1 and LAT0 <= la <= LAT1


def _clip_runs(coords):
    """Split a coordinate ring/line into runs of in-box vertices (one extra
    vertex of context kept on each side so a clipped line reaches the edge)."""
    runs, run = [], []
    n = len(coords)
    for i, (ln, la) in enumerate(coords):
        if _in(ln, la):
            if not run and i > 0:
                run.append(coords[i - 1])          # lead-in context vertex
            run.append((ln, la))
        else:
            if run:
                run.append((ln, la))               # lead-out context vertex
                runs.append(run)
                run = []
    if run:
        runs.append(run)
    return runs


def _iter_lines(geom):
    t = geom.get("type")
    c = geom.get("coordinates")
    if t == "LineString":
        yield [(p[0], p[1]) for p in c]
    elif t == "MultiLineString":
        for line in c:
            yield [(p[0], p[1]) for p in line]
    elif t == "Polygon":
        for ring in c:
            yield [(p[0], p[1]) for p in ring]
    elif t == "MultiPolygon":
        for poly in c:
            for ring in poly:
                yield [(p[0], p[1]) for p in ring]


def _fetch(name):
    url = "%s/%s.geojson" % (BASE, name)
    print("  fetching %s ..." % name)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def _diag(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


def _layer(name, eps, min_diag=0.0):
    gj = _fetch(name)
    out, nseg, npts = [], 0, 0
    for feat in gj.get("features", []):
        for line in _iter_lines(feat.get("geometry") or {}):
            if min_diag and _diag(line) < min_diag:
                continue                           # drop tiny rings (small lakes)
            for run in _clip_runs(line):
                simp = _rdp(run, eps)
                if len(simp) < 2:
                    continue
                flat = []
                for ln, la in simp:
                    flat.append(round(ln, 3))
                    flat.append(round(la, 3))
                out.append(flat)
                nseg += 1
                npts += len(simp)
    print("    -> %d polylines, %d points" % (nseg, npts))
    return out


def main():
    sources = {
        "coast": "ne_50m_coastline",
        "admin": "ne_50m_admin_1_states_provinces_lines",
        "lakes": "ne_50m_lakes",
    }
    data = {key: _layer(src, EPS[key],
                         LAKE_MIN_DIAG if key == "lakes" else 0.0)
            for key, src in sources.items()}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    txt = json.dumps(data, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print("wrote %s (%.1f KB)" % (OUT, len(txt.encode("utf-8")) / 1024.0))


if __name__ == "__main__":
    main()
