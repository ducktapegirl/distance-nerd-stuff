"""Turn the hand-made one-line drawings into the poster's sport glyphs.

Two inputs, both in ``strava-data/assets/`` and both outlines of the ink rather than
stroked centerlines, so a glyph is *filled* (fill-rule evenodd) and its line weight is
baked into the shape:

* ``one_line_figures.svg`` — a 3x2 sheet of six sports (running, walking, cross-country
  skiing, snowboarding, hiking, mountain biking), already vectorised into a single
  ``<path>`` of M/L/Z subpaths. Subpaths cluster by grid position.
* ``one_line_downhill_pair.png`` — a later drawing of a skier and a snowboarder together,
  supplied as a raster. It is traced here with marching squares at a sub-pixel iso-level,
  which gives smooth curves instead of a pixel staircase.

Output is ``strava-data/assets/poster_glyphs.json``: every figure cleaned of tracing
specks, simplified, and normalized into a 100x100 box.

    uv run python strava-data/tools/gen_poster_glyphs.py

Re-run this only when a drawing changes — ``poster_40for40.py`` reads the JSON and does no
tracing of its own.
"""

import argparse
import json
import math
import os
import re
import struct
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))
SHEET = os.path.join(ASSETS, "one_line_figures.svg")
OUT = os.path.join(ASSETS, "poster_glyphs.json")

# The sheet is a tidy 3x2 grid; names come from the file's own <desc>.
GRID = {(0, 0): "run", (0, 1): "walk", (0, 2): "ski",
        (1, 0): "board", (1, 1): "hike", (1, 2): "bike"}

# Standalone raster figures, merged into the same JSON: name -> filename in assets/.
RASTERS = {"skiboard": "one_line_downhill_pair.png"}

SIMPLIFY_TOL = 0.7      # source units; the sheet is 1536 wide
SPECK_SIZE = 2.5        # a ring smaller than this, in the normalized 100-box...
SPECK_DIST = 4.0        # ...and further than this from any real ring, is tracing noise
REAL_RING = 5.0         # a ring at least this big is part of the drawing

INK_LEVEL = 0.25        # raster: iso-level on the darkness field, 0 page .. 1 pen
RASTER_TOL = 1.6        # raster: simplification tolerance, in source pixels
RASTER_MIN_RING = 8.0   # raster: drop rings smaller than this, in source pixels


# ─────────────────────────────────────────────────────────────── shared geometry

def douglas_peucker(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i0, i1 = stack.pop()
        (x0, y0), (x1, y1) = pts[i0], pts[i1]
        dx, dy = x1 - x0, y1 - y0
        seg = math.hypot(dx, dy)
        best, bi = 0.0, -1
        for i in range(i0 + 1, i1):
            x, y = pts[i]
            # A ring that repeats its first point as its last gives a zero-length
            # baseline; measure radially there, or every distance computes as zero and
            # the whole ring collapses to two points.
            d = (math.hypot(x - x0, y - y0) if seg < 1e-9
                 else abs(dy * x - dx * y + x1 * y0 - y1 * x0) / seg)
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True
            stack += [(i0, bi), (bi, i1)]
    return [p for p, k in zip(pts, keep) if k]


def simplify_closed(ring, tol):
    """Simplify a ring that repeats its first point as its last.

    Douglas-Peucker anchors on its two endpoints, so on such a ring it has no baseline
    to work from. Cutting at the point furthest from the start gives it two open arcs.
    Sheet rings do not repeat their first point and go through ``douglas_peucker``
    directly, which is what produced the committed six — do not "unify" the two paths
    without re-checking those figures.
    """
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    if len(pts) < 4:
        return pts
    x0, y0 = pts[0]
    m = max(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - x0, pts[i][1] - y0))
    if m < 2 or m > len(pts) - 2:
        return douglas_peucker(pts + [pts[0]], tol)
    return douglas_peucker(pts[:m + 1], tol)[:-1] + douglas_peucker(pts[m:] + [pts[0]], tol)[:-1]


def size(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def center(ring):
    return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))


def despeck(rs, scale):
    """Drop isolated tracing dots.

    A small ring that sits *on* the drawing is real — an eye, a wheel hub, the knot of a
    hand. A small ring floating in white space is vectoriser noise. The one in the sheet
    is two dots 30 units clear of the walker, which also stretched her bounding box and
    left her under-sized in her cell. Distance is measured to any substantial ring, not
    just the longest one, because these figures are split across several large rings.
    """
    real = [r for r in rs if size(r) * scale >= REAL_RING]
    kept = []
    for r in rs:
        if size(r) * scale >= SPECK_SIZE:
            kept.append(r)
            continue
        cx, cy = center(r)
        near = min((math.hypot(cx - x, cy - y) * scale
                    for big in real for x, y in big), default=0.0)
        if near <= SPECK_DIST:
            kept.append(r)
    return kept


def figure(rs, tol, simplify=douglas_peucker, box=100.0):
    """Rings -> one evenodd path string, normalized into a ``box`` square."""
    xs = [p[0] for r in rs for p in r]
    ys = [p[1] for r in rs for p in r]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    rs = despeck(rs, box / span)                    # then re-fit: specks skew the box
    xs = [p[0] for r in rs for p in r]
    ys = [p[1] for r in rs for p in r]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    k = box / max(x1 - x0, y1 - y0)
    ox, oy = (box - (x1 - x0) * k) / 2, (box - (y1 - y0) * k) / 2
    parts = []
    for r in rs:
        s = simplify(r, tol)
        if len(s) < 3:
            continue
        pts = [((x - x0) * k + ox, (y - y0) * k + oy) for x, y in s]
        parts.append("M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
    return "".join(parts)


# ──────────────────────────────────────────────────────────── the vector sheet

def sheet_rings(d):
    """The sheet uses only M / L / Z, so every subpath is a closed ring of points."""
    out = []
    for chunk in d.split("M")[1:]:
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", chunk)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if len(pts) >= 3:
            out.append(pts)
    return out


def cluster(rs, cols=3, rows=2, w=1536, h=1024):
    groups = {}
    for r in rs:
        cx, cy = center(r)
        key = (min(int(cy / (h / rows)), rows - 1), min(int(cx / (w / cols)), cols - 1))
        groups.setdefault(key, []).append(r)
    return groups


# ─────────────────────────────────────────────────────────── the raster figures

def decode_png(path):
    """8-bit non-interlaced PNG -> (h, w, channels) uint8. There is no Pillow here."""
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{path} is not a PNG")
    idat, i = bytearray(), 8
    w = h = nch = 0
    while i < len(d):
        ln = struct.unpack(">I", d[i:i + 4])[0]
        typ, body = d[i + 4:i + 8], d[i + 8:i + 8 + ln]
        if typ == b"IHDR":
            w, h, bd, ct, _c, _f, inter = struct.unpack(">IIBBBBB", body)
            if bd != 8 or inter:
                raise SystemExit(f"{path}: only 8-bit non-interlaced PNG is supported")
            nch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        i += 12 + ln
    raw = zlib.decompress(bytes(idat))
    stride = w * nch
    out = np.zeros((h, stride), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.uint8)
    pos = 0
    for y in range(h):
        ft = raw[pos]
        pos += 1
        cur = np.frombuffer(raw[pos:pos + stride], dtype=np.uint8).copy()
        pos += stride
        if ft == 2:                                 # Up: the common case, vectorised
            cur = (cur.astype(np.int16) + prev.astype(np.int16)).astype(np.uint8)
        elif ft != 0:
            for x in range(stride):
                a = int(cur[x - nch]) if x >= nch else 0
                b = int(prev[x])
                c = int(prev[x - nch]) if x >= nch else 0
                if ft == 1:
                    add = a
                elif ft == 3:
                    add = (a + b) >> 1
                else:                               # Paeth
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    add = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[x] = (int(cur[x]) + add) & 0xFF
        out[y] = cur
        prev = cur
    return out.reshape(h, w, nch)


def ink_field(img):
    """1.0 where the pen is, 0.0 on the page. Flat art, so darkness alone is enough."""
    rgb = img[:, :, :3].astype(np.float32) / 255.0
    if img.shape[2] in (2, 4):                      # composite onto white
        a = img[:, :, -1].astype(np.float32) / 255.0
        rgb = rgb * a[..., None] + (1.0 - a[..., None])
    return 1.0 - (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2])


# A cell's four edges, each as the two corners it joins. Corner bits, high to low:
# 8 top-left, 4 top-right, 2 bottom-right, 1 bottom-left.
EDGE_CORNERS = {0: (8, 4), 1: (4, 2), 2: (1, 2), 3: (8, 1)}


def marching_squares(f, level):
    """Contour rings at the iso-level, interpolated onto cell edges.

    Which edges a contour crosses is derived from the corner bits rather than read from
    a hand-written case table: an edge is crossed exactly when its two corners fall on
    opposite sides of the level. That removes the table as a place to get it wrong.
    """
    g = f >= level
    c = (g[:-1, :-1].astype(np.uint8) * 8 + g[:-1, 1:].astype(np.uint8) * 4
         + g[1:, 1:].astype(np.uint8) * 2 + g[1:, :-1].astype(np.uint8))
    ys, xs = np.nonzero((c != 0) & (c != 15))

    def ipol(v0, v1, p0, p1):
        t = 0.5 if v1 == v0 else (level - v0) / (v1 - v0)
        t = min(max(t, 0.0), 1.0)
        return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)

    segs = []
    for y, x in zip(ys.tolist(), xs.tolist()):
        case = int(c[y, x])
        v00, v01 = float(f[y, x]), float(f[y, x + 1])
        v11, v10 = float(f[y + 1, x + 1]), float(f[y + 1, x])
        cut = [e for e, (a, b) in EDGE_CORNERS.items() if bool(case & a) != bool(case & b)]
        pt = {0: ipol(v00, v01, (x, y), (x + 1, y)),
              1: ipol(v01, v11, (x + 1, y), (x + 1, y + 1)),
              2: ipol(v10, v11, (x, y + 1), (x + 1, y + 1)),
              3: ipol(v00, v10, (x, y), (x, y + 1))}
        if len(cut) == 2:
            pairs = [(cut[0], cut[1])]
        elif len(cut) == 4:                         # saddle: the cell average breaks the tie
            avg = (v00 + v01 + v11 + v10) / 4.0
            pairs = ([(0, 3), (1, 2)] if (avg >= level) == bool(case & 8)
                     else [(0, 1), (2, 3)])
        else:
            continue
        for a, b in pairs:
            segs.append((pt[a], pt[b]))
    return chain(segs)


def chain(segs, q=1e-6):
    """Join segments into closed rings, ignoring their direction.

    Every crossing point is shared by exactly two cells, so the segments form loops in
    which each vertex has degree two. Walking that graph undirected avoids having to
    orient each segment consistently, and evenodd filling does not care about winding.
    Getting this wrong is what turns a figure into a fan of triangles.
    """
    def key(p):
        return (round(p[0] / q), round(p[1] / q))

    incident = {}
    for idx, (a, b) in enumerate(segs):
        incident.setdefault(key(a), []).append(idx)
        incident.setdefault(key(b), []).append(idx)

    used, rings = set(), []
    for i in range(len(segs)):
        if i in used:
            continue
        used.add(i)
        a0, b0 = segs[i]
        ring = [a0, b0]
        cur, start = b0, key(a0)
        while key(cur) != start:
            nxt = next((j for j in incident.get(key(cur), ()) if j not in used), None)
            if nxt is None:
                break
            used.add(nxt)
            a, b = segs[nxt]
            cur = b if key(a) == key(cur) else a     # step to the far end
            ring.append(cur)
        if len(ring) >= 4:
            rings.append(ring)
    return rings


def raster_rings(path):
    img = decode_png(path)
    rings = [r for r in marching_squares(ink_field(img), INK_LEVEL)
             if size(r) >= RASTER_MIN_RING]
    if not rings:
        raise SystemExit(f"{path}: nothing traced at level {INK_LEVEL}")
    return rings, img.shape


# ────────────────────────────────────────────────────────────────────── driver

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    with open(a.sheet, encoding="utf-8") as f:
        d = re.search(r'<path d="(.*?)"', f.read(), re.S).group(1)
    groups = cluster(sheet_rings(d))
    if len(groups) != 6:
        raise SystemExit(f"expected a 3x2 sheet, found {len(groups)} clusters")

    out = {}
    for key, rs in sorted(groups.items()):
        name = GRID[key]
        out[name] = figure(rs, SIMPLIFY_TOL)
        print(f"{name:9s} sheet   rings {len(rs):3d} -> {out[name].count('M'):3d}"
              f"   {len(out[name]):6d} chars")

    for name, filename in RASTERS.items():
        rings, shape = raster_rings(os.path.join(ASSETS, filename))
        out[name] = figure(rings, RASTER_TOL, simplify=simplify_closed)
        print(f"{name:9s} raster  rings {len(rings):3d} -> {out[name].count('M'):3d}"
              f"   {len(out[name]):6d} chars   from {shape[1]}x{shape[0]}")

    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
