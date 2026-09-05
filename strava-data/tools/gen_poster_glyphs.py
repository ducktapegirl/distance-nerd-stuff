"""Turn the traced one-line figure sheet into the poster's sport glyphs.

Input is ``strava-data/assets/one_line_figures.svg`` — a hand-made continuous-line
drawing of six sports (running, walking, cross-country skiing, snowboarding, hiking,
mountain biking), vectorised into a single ``<path>`` of M/L/Z subpaths with
``fill-rule="evenodd"``. It is the **outline of the ink**, not a stroked centreline, so
a glyph is filled rather than stroked and its line weight is baked into the shape.

Output is ``strava-data/assets/poster_glyphs.json``: the six figures, each cleaned of
tracing specks, simplified, and normalised into a 100x100 box.

    uv run python strava-data/tools/gen_poster_glyphs.py

Re-run this only when the drawing changes — ``poster_40for40.py`` reads the JSON and
does no tracing of its own.
"""

import argparse
import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))
SRC = os.path.join(ASSETS, "one_line_figures.svg")
OUT = os.path.join(ASSETS, "poster_glyphs.json")

# The sheet is a tidy 3x2 grid; names come from the file's own <desc>.
GRID = {(0, 0): "run", (0, 1): "walk", (0, 2): "ski",
        (1, 0): "board", (1, 1): "hike", (1, 2): "bike"}

SIMPLIFY_TOL = 0.7      # source units; the sheet is 1536 wide
SPECK_SIZE = 2.5        # a ring smaller than this, in the normalised 100-box...
SPECK_DIST = 4.0        # ...and further than this from any real ring, is tracing noise
REAL_RING = 5.0         # a ring at least this big is part of the drawing


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
        seg = math.hypot(dx, dy) or 1e-12
        best, bi = 0.0, -1
        for i in range(i0 + 1, i1):
            x, y = pts[i]
            d = abs(dy * x - dx * y + x1 * y0 - y1 * x0) / seg
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True
            stack += [(i0, bi), (bi, i1)]
    return [p for p, k in zip(pts, keep) if k]


def rings(d):
    """The sheet uses only M / L / Z, so every subpath is a closed ring of points."""
    out = []
    for chunk in d.split("M")[1:]:
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", chunk)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if len(pts) >= 3:
            out.append(pts)
    return out


def size(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def centre(ring):
    return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))


def cluster(rs, cols=3, rows=2, w=1536, h=1024):
    groups = {}
    for r in rs:
        cx, cy = centre(r)
        key = (min(int(cy / (h / rows)), rows - 1), min(int(cx / (w / cols)), cols - 1))
        groups.setdefault(key, []).append(r)
    return groups


def despeck(rs, scale):
    """Drop isolated tracing dots.

    A small ring that sits *on* the drawing is real — an eye, a wheel hub, the knot of a
    hand. A small ring floating in white space is vectoriser noise. The one in this sheet
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
        cx, cy = centre(r)
        near = min((math.hypot(cx - x, cy - y) * scale
                    for big in real for x, y in big), default=0.0)
        if near <= SPECK_DIST:
            kept.append(r)
    return kept


def figure(rs, box=100.0):
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
        s = douglas_peucker(r, SIMPLIFY_TOL)
        if len(s) < 3:
            continue
        pts = [((x - x0) * k + ox, (y - y0) * k + oy) for x, y in s]
        parts.append("M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    with open(a.src, encoding="utf-8") as f:
        d = re.search(r'<path d="(.*?)"', f.read(), re.S).group(1)
    groups = cluster(rings(d))
    if len(groups) != 6:
        raise SystemExit(f"expected a 3x2 sheet, found {len(groups)} clusters")

    out = {}
    for key, rs in sorted(groups.items()):
        name = GRID[key]
        before = len(rs)
        out[name] = figure(rs)
        after = out[name].count("M")
        print(f"{name:6s} rings {before:3d} -> {after:3d}   {len(out[name]):6d} chars")

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
