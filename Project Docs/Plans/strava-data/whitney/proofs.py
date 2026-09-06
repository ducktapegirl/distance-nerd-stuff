"""Mt. Whitney, 1 October 2025 — five design proofs for a single-colour 11x14 print.

Read-only against ``strava-data/data/`` and the line drawings in
``Project Docs/Specs/strava-data/whitney_graphics/``. Writes proof_A..E.svg beside itself
plus a gitignored proofs.html contact sheet. Not a build step and not wired into any
workflow — this is the exploration stage, the same role that
``Project Docs/Plans/strava-data/poster/alternates/proofs.py`` played for 40 for 40.

    uv run python "Project Docs/Plans/strava-data/whitney/proofs.py"
    uv run python "Project Docs/Plans/strava-data/whitney/proofs.py" --png --dpi 300

Five layouts, each making a different element dominant and taking a different shape:

    A  ASCENT     vertical stack   the drawn peak over the measured one, summits aligned
    B  TRIPTYCH   three panels     one element per panel; the profile rotated to climb
    C  MEDALLION  circular         route in a disc, elevation wrapped round it as a ring
    D  HORIZON    landscape        the profile becomes ground, and the hikers walk on it
    E  SUMMIT     triangular       the profile exaggerated into a peak, the drawing inside

Stdlib only. Playwright is imported lazily behind --png.
"""

import argparse
import csv
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# whitney -> strava-data -> Plans -> Project Docs -> repo root
REPO = os.path.normpath(os.path.join(HERE, *[os.pardir] * 4))
DATA = os.path.join(REPO, "strava-data", "data")
ART = os.path.join(REPO, "Project Docs", "Specs", "strava-data", "whitney_graphics")

ACT_ID = "16005045227"
KM_TO_MI, M_TO_FT = 0.621371, 3.28084

# --- canvas: 11 x 14 in at 100 user units per inch, the convention 40 for 40 uses for
# --- 16 x 20, so every stroke weight carries over unchanged (1 unit = 0.254 mm).
W, H = 1100, 1400                   # portrait; design D turns the sheet
BG, INK = "#F5F0E6", "#2B2A28"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"

# One ink, so stroke weight is the only tonal variable. No opacity, no tints.
HAIR, LIGHT, MED, HERO = 1.8, 2.4, 3.0, 3.8

# Whitney's surveyed summit. The watch recorded 4421.6 m = 14,507 ft; printing that would
# hang two feet of barometric drift on a wall for a decade. Distance and gain are as measured.
SUMMIT_FT = 14505

# hikers_simple2.svg is drawn standing on its own slope. These three <path> elements are
# that slope (verified by rendering them isolated in red); dropping them frees the two
# figures to stand on a line we draw instead. Concepts that want the vignette keep it whole.
HIKER_GROUND = {4, 5, 9}
# Where the lower figure's boot meets that slope, in viewBox units — the anchor used when
# the stripped figures are stood on the elevation profile.
HIKER_FOOT = (250.0, 920.0)


# ============================================================================ data

def mf(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load():
    with open(os.path.join(DATA, "activities.csv"), encoding="utf-8-sig") as f:
        act = next(r for r in csv.DictReader(f) if r["id"] == ACT_ID)
    pts, alt, dist, tim = [], [], [], []
    with open(os.path.join(DATA, "streams", ACT_ID + ".csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            la, lo = mf(row.get("lat")), mf(row.get("lng"))
            a, d, t = mf(row.get("altitude_m")), mf(row.get("distance_m")), mf(row.get("t"))
            if None in (la, lo, a, d, t):
                continue
            pts.append((lo, la))
            alt.append(a)
            dist.append(d)
            tim.append(t)
    act["_pts"], act["_alt"], act["_dist"], act["_t"] = pts, alt, dist, tim
    act["_mi"] = (mf(act["distance_km"]) or 0) * KM_TO_MI
    act["_ft"] = (mf(act["total_elevation_gain_m"]) or 0) * M_TO_FT
    act["_summit"] = alt.index(max(alt))
    return act


# ------------------------------------------------------------------- geometry
# metres / douglas_peucker / fit are lifted from strava-data/tools/poster_40for40.py
# (lines 135, 178, 214). Copied rather than imported: these poster tools are deliberately
# standalone and stdlib-only, and gen_poster_glyphs.py already duplicates douglas_peucker
# for the same reason.

def metres(pts):
    """Equirectangular metres with a cos(lat) correction."""
    lat0 = sum(p[1] for p in pts) / len(pts)
    kx = math.cos(math.radians(lat0)) * 111_320.0
    return [(lng * kx, lat * 110_540.0) for lng, lat in pts]


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
            stack.append((i0, bi))
            stack.append((bi, i1))
    return [p for p, k in zip(pts, keep) if k]


def route_at(act, x, y, w, h, tol_m=6.0, pad=0.0, rotate=False):
    """The GPS trace fitted into a box. Returns (points, summit_point).

    The hike is a 0.955-Jaccard out-and-back with start and finish 10 m apart, so the return
    line lands on the outbound one and the whole trace draws as a single line. Nothing is
    gained by splitting the strands, and offsetting them would read as a rendering fault.

    No point cap: 40 for 40 needs one because it draws forty thumbnails, but here the route
    is the subject and the switchbacks are its signature. At hero size a 6 m tolerance is
    well under half a stroke width.
    """
    m = metres(act["_pts"])
    if rotate:                       # the track is 1.50 landscape; turn it for a tall panel
        m = [(-py, px) for px, py in m]
    x0, y0 = min(p[0] for p in m), max(p[1] for p in m)
    local = [(px - x0, y0 - py) for px, py in m]
    keep = douglas_peucker(local, tol_m)
    pw = max(p[0] for p in keep) or 1e-9
    ph = max(p[1] for p in keep) or 1e-9
    k = min(w * (1 - 2 * pad) / pw, h * (1 - 2 * pad) / ph)
    ox, oy = x + (w - pw * k) / 2, y + (h - ph * k) / 2
    pts = [(ox + px * k, oy + py * k) for px, py in keep]
    si = act["_summit"]
    sp = (ox + local[si][0] * k, oy + local[si][1] * k)
    return pts, sp


# ------------------------------------------------------------------ elevation

def profile_at(act, x, y, w, h, xaxis="dist", tol=0.35):
    """Elevation profile fitted into a box: baseline at y+h, apex at y.

    Returns (points, summit_point, exaggeration). The natural aspect of this profile is
    19:1 — 22.3 miles against 6,146 ft of relief — so at 1:1 it is a flat line. The vertical
    exaggeration is therefore a *design* parameter, and is reported so it can be recorded.
    """
    alt = act["_alt"]
    xv = act["_dist"] if xaxis == "dist" else act["_t"]
    a0, a1 = min(alt), max(alt)
    span = max(xv[-1] - xv[0], 1e-9)
    rng = max(a1 - a0, 1e-9)
    pts = [(x + (v - xv[0]) / span * w, y + h - (a - a0) / rng * h)
           for v, a in zip(xv, alt)]
    pts = douglas_peucker(pts, tol)
    si = act["_summit"]
    sp = (x + (xv[si] - xv[0]) / span * w, y + h - (alt[si] - a0) / rng * h)
    natural = w * rng / max(act["_dist"][-1], 1e-9)      # the same profile at 1:1
    return pts, sp, h / natural


def profile_y(pts, px):
    """Height of the drawn profile at an x, for standing something on it."""
    return min(pts, key=lambda p: abs(p[0] - px))[1]


def polar_profile(act, cx, cy, r0, r1, start=-math.pi / 2, xaxis="dist"):
    """Elevation wrapped into a ring: angle from distance, radius from altitude.

    An out-and-back climbs for half the circle and descends for the other half, so the ring
    swells symmetrically to its maximum directly opposite the start.
    """
    alt = act["_alt"]
    xv = act["_dist"] if xaxis == "dist" else act["_t"]
    a0, a1 = min(alt), max(alt)
    span = max(xv[-1] - xv[0], 1e-9)
    rng = max(a1 - a0, 1e-9)
    out = []
    for v, a in zip(xv, alt):
        ang = start + (v - xv[0]) / span * 2 * math.pi
        r = r0 + (a - a0) / rng * (r1 - r0)
        out.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    out = douglas_peucker(out, 0.3)
    si = act["_summit"]
    ang = start + (xv[si] - xv[0]) / span * 2 * math.pi
    return out, (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))


# =========================================================================== art
# The drawings are Illustrator exports: a viewBox with no width/height, one .st0 class
# (fill:none, stroke:#000, stroke-width:2px) and nothing but <path class="st0"> elements
# whose d is an M followed by relative cubics, never closed. They are open strokes — the
# opposite of poster_40for40.py's filled evenodd glyphs — so gen_poster_glyphs.py's parser,
# which splits on the letter M and pairs every number as a point, cannot read them, and its
# `<path d="` regex matches nothing because the real attribute order is class, then d.
#
# They are emitted verbatim inside a transform group instead: no flattening, no JSON
# intermediate, curves stay curves. Two things that has to get right:
#   * strip <defs><style> and class="st0". Two drawings inlined into one sheet would each
#     define .st0, which silently defeats per-element stroke weights.
#   * vector-effect="non-scaling-stroke" holds the stroke constant in final sheet units.
#     Without it, scaling the 1345-wide peak down to 850 turns its 2px stroke into 1.3
#     units = 0.32 mm, far too light to print.
_PATH_RE = re.compile(r'<path[^>]*\bd="([^"]*)"')
_TOK = re.compile(r"[MmCcLlHhVvQqSsTtAaZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?")


def flatten(d, steps=10):
    """Path 'd' -> polylines. Used only to measure ink bounds and locate the highest point;
    the rendered output always carries the original curves."""
    toks = _TOK.findall(d)
    i = 0
    cx = cy = sx = sy = 0.0
    cmd = None
    c2 = q1 = None
    subs, cur = [], []

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v

    while i < len(toks):
        if toks[i][0].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                if cur:
                    cur.append((sx, sy))
                    subs.append(cur)
                    cur = []
                cx, cy = sx, sy
                continue
        rel, C = cmd.islower(), cmd.upper()
        if C == "M":
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            if cur:
                subs.append(cur)
            cur = [(x, y)]
            cx = sx = x
            cy = sy = y
            cmd = "l" if rel else "L"       # further pairs after an M are linetos
            c2 = q1 = None
        elif C == "L":
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            cur.append((x, y))
            cx, cy = x, y
            c2 = q1 = None
        elif C in "HV":
            v = num()
            if C == "H":
                x, y = (cx + v if rel else v), cy
            else:
                x, y = cx, (cy + v if rel else v)
            cur.append((x, y))
            cx, cy = x, y
            c2 = q1 = None
        elif C in "CS":
            if C == "C":
                x1, y1 = num(), num()
                if rel:
                    x1, y1 = cx + x1, cy + y1
            else:
                x1, y1 = (2 * cx - c2[0], 2 * cy - c2[1]) if c2 else (cx, cy)
            x2, y2 = num(), num()
            x, y = num(), num()
            if rel:
                x2, y2, x, y = cx + x2, cy + y2, cx + x, cy + y
            for s in range(1, steps + 1):
                t = s / steps
                u = 1 - t
                cur.append((u ** 3 * cx + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3 * x,
                            u ** 3 * cy + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t ** 3 * y))
            c2, q1 = (x2, y2), None
            cx, cy = x, y
        elif C in "QT":
            if C == "Q":
                x1, y1 = num(), num()
                if rel:
                    x1, y1 = cx + x1, cy + y1
            else:
                x1, y1 = (2 * cx - q1[0], 2 * cy - q1[1]) if q1 else (cx, cy)
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            for s in range(1, steps + 1):
                t = s / steps
                u = 1 - t
                cur.append((u * u * cx + 2 * u * t * x1 + t * t * x,
                            u * u * cy + 2 * u * t * y1 + t * t * y))
            q1, c2 = (x1, y1), None
            cx, cy = x, y
        elif C == "A":
            for _ in range(5):
                num()
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            cur.append((x, y))
            cx, cy = x, y
            c2 = q1 = None
        else:
            raise SystemExit("unhandled path command %r" % cmd)
    if cur:
        subs.append(cur)
    return subs


_ART_CACHE = {}


def art(name, drop=()):
    """Load a drawing: path data, true ink box, and where its highest point sits across it.

    The ink box is measured rather than assumed. It happens to sit exactly 1.0 unit inside
    the viewBox on all four sides (Illustrator's stroke padding), but measuring means a
    redrawn asset cannot silently shift a layout that aligns to its summit.
    """
    key = (name, tuple(sorted(drop)))
    if key not in _ART_CACHE:
        with open(os.path.join(ART, name), encoding="utf-8") as f:
            txt = f.read()
        ds = [d for i, d in enumerate(_PATH_RE.findall(txt)) if i not in drop]
        if not ds:
            sys.exit("no <path> elements found in " + name)
        pts = [p for d in ds for sub in flatten(d) for p in sub]
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        top = min(pts, key=lambda p: p[1])
        _ART_CACHE[key] = {"d": ds, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
                           "peak": (top[0] - x0) / max(x1 - x0, 1e-9)}
    return _ART_CACHE[key]


def art_at(a, s, tx, ty, sw):
    return (f'<g transform="translate({tx:.2f},{ty:.2f}) scale({s:.5f})" fill="none" '
            f'stroke="{INK}" stroke-width="{sw}" stroke-linecap="round" '
            f'stroke-linejoin="round" vector-effect="non-scaling-stroke">'
            + "".join(f'<path d="{d}"/>' for d in a["d"]) + "</g>")


def art_box(a, x, y, w, h, sw):
    """Contain-fit into a rect, centred. Returns (svg, drawn_w, drawn_h, peak_x)."""
    s = min(w / a["w"], h / a["h"])
    dw, dh = a["w"] * s, a["h"] * s
    tx, ty = x + (w - dw) / 2 - a["x"] * s, y + (h - dh) / 2 - a["y"] * s
    return art_at(a, s, tx, ty, sw), dw, dh, tx + (a["x"] + a["peak"] * a["w"]) * s


def art_width(a, left, top, w, sw):
    """Scale to a width with its ink box's top-left at (left, top). Returns (svg, h, peak_x)."""
    s = w / a["w"]
    tx, ty = left - a["x"] * s, top - a["y"] * s
    return art_at(a, s, tx, ty, sw), a["h"] * s, tx + (a["x"] + a["peak"] * a["w"]) * s


def art_anchor(a, s, anchor, at, sw):
    """Place at scale s so the viewBox point `anchor` lands on the sheet point `at`."""
    return art_at(a, s, at[0] - anchor[0] * s, at[1] - anchor[1] * s, sw)


# ==================================================================== primitives

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def poly(pts, sw, dash=None):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polyline points="{d}" fill="none" stroke="{INK}" stroke-width="{sw}" '
            f'stroke-linejoin="round" stroke-linecap="round"{da}/>')


def text(x, y, s, size, anchor="start", family=SANS, spacing=0, weight=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{INK}" '
            f'letter-spacing="{spacing}">{esc(s)}</text>')


def line(x1, y1, x2, y2, sw=HAIR):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{INK}" stroke-width="{sw}" stroke-linecap="round"/>')


def summit_mark(p, r=9.0, sw=MED):
    """The one device shared by all five proofs: the same open ring marks the summit on the
    map and on the profile, which is what ties the two readings of the day together."""
    return (f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{r}" fill="none" '
            f'stroke="{INK}" stroke-width="{sw}"/>')


def frame(body, w=W, h=H):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="{BG}"/>'
            + body + "</svg>")


# ======================================================================= designs
# Each returns (svg, note) where note records the exaggeration actually used.

TITLE = "Mt. Whitney"
DATE = "OCTOBER 1, 2025"


def design_a(act, xaxis):
    """A · ASCENT — the drawn peak above the measured one, summits aligned."""
    side = 85
    cw = W - 2 * side
    body = []

    # The profile spans the full measure; the drawing is then narrowed until its own summit
    # sits on the same vertical. Whitney_Peak peaks at 55.1% of its width, the day peaks at
    # 50.9% of its distance, so without this they miss by ~39 units and the rhyme is lost.
    base, ph = 1010.0, 300.0
    pts, sp, exag = profile_at(act, side, base - ph, cw, ph, xaxis)

    a = art("Whitney_Peak.svg")
    aw = (sp[0] - side) / a["peak"]                  # width that puts its peak on sp.x
    aw = min(aw, cw)
    svg, ah, peak_x = art_width(a, sp[0] - a["peak"] * aw, 180.0, aw, LIGHT)
    body.append(svg)

    body.append(poly(pts, HERO))
    body.append(line(side, base, side + cw, base, HAIR))
    body.append(summit_mark(sp))
    # the vertical that carries the eye from the drawn summit down to the measured one
    body.append(f'<line x1="{sp[0]:.1f}" y1="{180.0 + ah + 14:.1f}" x2="{sp[0]:.1f}" '
                f'y2="{sp[1] - 9 - 6:.1f}" stroke="{INK}" stroke-width="{HAIR}" '
                f'stroke-dasharray="2 9" stroke-linecap="round"/>')

    # two figures, ground stripped, stood on the climb at about a third of the way
    hk = art("hikers_simple2.svg", HIKER_GROUND)
    fx = side + cw * 0.26
    body.append(art_anchor(hk, 205.0 / hk["h"], HIKER_FOOT,
                           (fx, profile_y(pts, fx)), MED))

    # type block, then the route as a small mark opposite it
    body.append(text(side, 1148, TITLE, 74, family=SERIF, spacing=-1))
    body.append(text(side, 1196, DATE, 19, spacing=5))
    body.append(text(side, 1258, " · ".join(
        (f"{act['_mi']:.1f} MILES", f"{act['_ft']:,.0f} FT GAINED",
         f"{SUMMIT_FT:,} FT")), 16, spacing=2.5))
    rp, rsp = route_at(act, side + cw - 215, 1090, 215, 190, tol_m=9.0, pad=0.05)
    body.append(poly(rp, LIGHT))
    body.append(summit_mark(rsp, 6.0, LIGHT))
    return frame("".join(body)), f"profile {exag:.1f}x vertical exaggeration"


def design_b(act, xaxis):
    """B · TRIPTYCH — three tall panels, one element each, in a single frame."""
    side, top, gap = 75, 130, 52
    pw = (W - 2 * side - 2 * gap) / 3
    ph = 980.0
    body = []
    cap_y = top + ph + 46            # one shared caption baseline across all three panels
    sub_y = cap_y + 30

    def panel(i):
        return side + i * (pw + gap)

    for i in range(3):
        x = panel(i)
        body.append(f'<rect x="{x:.1f}" y="{top}" width="{pw:.1f}" height="{ph}" '
                    f'fill="none" stroke="{INK}" stroke-width="{HAIR}"/>')

    # 1 · the mountain, with the figures below it. A 1.97-aspect drawing in a 282-wide panel
    #     can never be taller than ~143 units, so the panel is filled by pairing it with the
    #     figures rather than by scaling a landscape drawing into a portrait hole.
    a = art("Whitney_Peak_Vignette.svg")
    svg, ah, _ = art_width(a, panel(0) + 8, top + 250, pw - 16, LIGHT)
    body.append(svg)
    hk1 = art("hikers_simple2.svg", HIKER_GROUND)
    s1 = 285.0 / hk1["h"]
    body.append(art_anchor(hk1, s1, (hk1["x"] + hk1["w"] / 2, hk1["y"] + hk1["h"]),
                           (panel(0) + pw / 2, top + ph - 80), MED))
    body.append(text(panel(0) + pw / 2, cap_y, "THE MOUNTAIN", 17, "middle", spacing=4))
    body.append(text(panel(0) + pw / 2, sub_y, f"{SUMMIT_FT:,} FT", 15, "middle", spacing=2))

    # 2 · the climb — the profile turned 90 deg so distance runs bottom to top. This is what
    #     makes a tall narrow panel work at all: it stops being a chart and becomes an ascent.
    px, py = panel(1) + 30, top + 40
    bw, bh = pw - 60, ph - 80
    prof, sp, exag = profile_at(act, 0, 0, bh, bw, xaxis)     # built wide, then rotated
    rot = [(px + (bw - v), py + bh - u) for u, v in prof]
    body.append(poly(rot, MED))
    body.append(line(px + bw, py, px + bw, py + bh, HAIR))
    body.append(summit_mark((px + (bw - sp[1]), py + bh - sp[0]), 7.0, LIGHT))
    body.append(text(panel(1) + pw / 2, cap_y, "THE CLIMB", 17, "middle", spacing=4))
    body.append(text(panel(1) + pw / 2, sub_y,
                     f"{act['_mi']:.1f} MI · {act['_ft']:,.0f} FT", 15, "middle", spacing=2))

    # 3 · the line — the track turned to portrait so it fills the column
    rp, rsp = route_at(act, panel(2) + 22, top + 30, pw - 44, ph - 60, tol_m=4.0, rotate=True)
    body.append(poly(rp, MED))
    body.append(summit_mark(rsp, 7.0, LIGHT))
    body.append(text(panel(2) + pw / 2, cap_y, "THE LINE", 17, "middle", spacing=4))
    body.append(text(panel(2) + pw / 2, sub_y, "22.3 MI OUT AND BACK", 15, "middle", spacing=2))

    body.append(text(W / 2, 100, TITLE, 60, "middle", family=SERIF, spacing=-1))
    body.append(text(W / 2, 1322, DATE, 19, "middle", spacing=6))
    return frame("".join(body)), f"profile {exag:.1f}x exaggeration, rotated 90 deg"


def design_c(act, xaxis):
    """C · MEDALLION — the route in a disc, the elevation wrapped round it as a ring."""
    cx, cy = W / 2, 590.0
    r0, r1 = 290.0, 410.0
    body = []

    # A wide radius swing is what makes this read as terrain rather than as a slightly
    # wobbly circle: r1/r0 = 1.41, so the trailhead ring and the summit ring are plainly
    # different circles. The dashed guide is the low point — the trailhead elevation.
    ring, sp = polar_profile(act, cx, cy, r0, r1, xaxis=xaxis)
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r0}" fill="none" stroke="{INK}" '
                f'stroke-width="{HAIR}" stroke-dasharray="2 9"/>')
    body.append(poly(ring, MED))
    body.append(summit_mark(sp, 9.0, MED))

    rp, rsp = route_at(act, cx - 250, cy - 195, 500, 390, tol_m=4.0)
    body.append(poly(rp, HERO))
    body.append(summit_mark(rsp))

    # Below the disc, the drawing and the figures share one baseline so the band reads as a
    # single register rather than as two leftovers.
    a = art("Whitney_Peak.svg")
    aw, atop = 560.0, 1050.0
    svg, ah, _ = art_width(a, cx - aw / 2, atop, aw, LIGHT)
    body.append(svg)
    hk = art("hikers_simple2.svg", HIKER_GROUND)
    s = 200.0 / hk["h"]
    body.append(art_anchor(hk, s, (hk["x"], hk["y"] + hk["h"]), (85.0, atop + ah), MED))

    body.append(text(cx, 105, TITLE, 66, "middle", family=SERIF, spacing=-1))
    body.append(text(cx, 148, DATE, 19, "middle", spacing=6))
    body.append(text(cx, 1355, " · ".join(
        (f"{act['_mi']:.1f} MILES", f"{act['_ft']:,.0f} FT GAINED",
         f"{SUMMIT_FT:,} FT")), 16, "middle", spacing=2.5))
    return frame("".join(body)), f"elevation as a polar ring, radius {r0:.0f}-{r1:.0f}"


def design_d(act, xaxis):
    """D · HORIZON — landscape; the profile stops being a chart and becomes ground."""
    w, h = H, W                       # the same 11x14 sheet, turned
    side = 95
    cw = w - 2 * side
    body = []

    base, ph = 880.0, 430.0
    pts, sp, exag = profile_at(act, side, base - ph, cw, ph, xaxis)

    # The drawing sits behind as a backdrop ridge at the lightest weight, pushed left and
    # sized so its base clears the profile's apex entirely. Two mountains that nearly
    # register read as a printing fault; two that plainly do not read as a range.
    # Peak_Vignette rather than Whitney_Wide: Wide carries foreground boulders, and a
    # boulder field floating above the terrain line reads as debris, not as distance.
    a = art("Whitney_Peak_Vignette.svg")
    svg, ah, _ = art_width(a, 60, 130, cw * 0.51, HAIR)
    body.append(svg)

    body.append(poly(pts, HERO))
    body.append(summit_mark(sp))
    body.append(line(side, base, side + cw, base, HAIR))

    # the two figures, ground stripped, standing on the terrain at about four miles in
    hk = art("hikers_simple2.svg", HIKER_GROUND)
    fx = side + cw * (4.0 / act["_mi"])
    body.append(art_anchor(hk, 255.0 / hk["h"], HIKER_FOOT, (fx, profile_y(pts, fx)), MED))

    body.append(text(w - side, 152, TITLE, 76, "end", family=SERIF, spacing=-1))
    body.append(text(w - side, 198, DATE, 19, "end", spacing=5))
    rp, rsp = route_at(act, w - side - 240, base + 32, 240, 142, tol_m=9.0)
    body.append(poly(rp, LIGHT))
    body.append(summit_mark(rsp, 6.0, LIGHT))
    body.append(text(side, base + 78, " · ".join(
        (f"{act['_mi']:.1f} MILES", f"{act['_ft']:,.0f} FT GAINED",
         f"{SUMMIT_FT:,} FT")), 16, spacing=2.5))
    return frame("".join(body), w, h), f"profile {exag:.1f}x exaggeration"


def design_e(act, xaxis):
    """E · SUMMIT — the profile exaggerated until it is the composition."""
    side = 70
    cw = W - 2 * side
    body = []

    base, ph = 1090.0, 620.0
    pts, sp, exag = profile_at(act, side, base - ph, cw, ph, xaxis)

    # The drawing nested inside the envelope the data makes, summits on one vertical. Width
    # and height are chosen so the drawing stays inside the triangle: at 36% of the way down
    # the profile the envelope is ~630 units wide, so a 480-wide drawing clears both flanks.
    a = art("Whitney_Peak.svg")
    aw = cw * 0.46
    svg, ah, _ = art_width(a, sp[0] - a["peak"] * aw, base - ph * 0.44, aw, HAIR)
    body.append(svg)

    body.append(poly(pts, HERO))
    body.append(summit_mark(sp, 11.0))
    body.append(line(side, base, side + cw, base, LIGHT))

    hk = art("hikers_simple2.svg", HIKER_GROUND)
    fx = side + cw * 0.11
    body.append(art_anchor(hk, 185.0 / hk["h"], HIKER_FOOT, (fx, profile_y(pts, fx)), LIGHT))

    # type set into the two corners the triangle opens up
    body.append(text(side, 196, TITLE, 72, family=SERIF, spacing=-1))
    body.append(text(W - side, 190, DATE, 19, "end", spacing=5))
    body.append(text(W - side, 232, f"{SUMMIT_FT:,} FT", 19, "end", spacing=5))
    rp, rsp = route_at(act, side, base + 55, 230, 175, tol_m=9.0)
    body.append(poly(rp, LIGHT))
    body.append(summit_mark(rsp, 6.0, LIGHT))
    body.append(text(W - side, base + 150, " · ".join(
        (f"{act['_mi']:.1f} MILES", f"{act['_ft']:,.0f} FT GAINED")), 16, "end", spacing=2.5))
    return frame("".join(body)), f"profile {exag:.1f}x exaggeration"


DESIGNS = [
    ("A", "Ascent", design_a, W, H,
     "Vertical stack. The drawn peak sits directly above the measured one and their summits "
     "are aligned on one vertical, so the eye reads the same mountain twice — once observed, "
     "once recorded. The mountain leads, the profile answers, route and figures are accents."),
    ("B", "Triptych", design_b, W, H,
     "Three tall panels in one frame, one element each, unified by a shared caption baseline "
     "rather than by any line crossing the gaps. The profile is turned 90 degrees so distance "
     "climbs the panel: that is what stops a narrow column reading as a squeezed chart."),
    ("C", "Medallion", design_c, W, H,
     "Circular. The route is the hero inside a disc and the elevation is wrapped around it as "
     "a polar ring — because the day is an out-and-back the ring swells symmetrically to its "
     "widest directly opposite the start. The only concept that does not rhyme profile "
     "against drawing."),
    ("D", "Horizon", design_d, H, W,
     "Landscape. The profile stops being a chart and becomes ground: the figures stand on the "
     "terrain line at the point four miles in where they really were. The drawing falls back "
     "to a light backdrop ridge, deliberately not summit-aligned so it reads as another peak."),
    ("E", "Summit", design_e, W, H,
     "Triangular. The profile is exaggerated until the composition is its silhouette, and the "
     "drawing is nested inside that envelope with the summits on one vertical — the observed "
     "mountain inside the measured one. Type sits in the corners the triangle opens up."),
]


# ========================================================================== output

def rasterise(svg_path, png_path, w, h, dpi=300):
    from playwright.sync_api import sync_playwright
    scale = dpi / 100.0
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        pg.goto("file:///" + os.path.abspath(svg_path).replace("\\", "/"))
        pg.screenshot(path=png_path)
        b.close()


def write(path, s):
    # newline="\n" on every text write: without it Windows CRLF translation dirties the
    # SVGs on every run, which this repo has already had to fix once.
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--png", action="store_true", help="also rasterise each proof")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--profile-x", choices=("dist", "time"), default="dist",
                    help="x-axis of every elevation profile: distance (summit at 50.9%%, "
                         "symmetric) or elapsed time (summit at 56%%, honest about the day)")
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()

    act = load()
    si = act["_summit"]
    print(f"{act['name']}  {act['start_date_local']}", file=sys.stderr)
    print(f"  {len(act['_pts']):,} stream points   {act['_mi']:.2f} mi   "
          f"{act['_ft']:,.0f} ft gained", file=sys.stderr)
    print(f"  low {min(act['_alt']) * M_TO_FT:,.0f} ft   high "
          f"{max(act['_alt']) * M_TO_FT:,.0f} ft (printing {SUMMIT_FT:,} ft)", file=sys.stderr)
    print(f"  summit at {act['_dist'][si] * 0.000621371:.2f} mi "
          f"({act['_dist'][si] / act['_dist'][-1]:.1%} of distance), "
          f"{act['_t'][si] / 3600:.2f} h ({act['_t'][si] / act['_t'][-1]:.1%} of elapsed)",
          file=sys.stderr)
    print(f"  profile x-axis: {args.profile_x}", file=sys.stderr)

    cards = []
    for key, name, fn, w, h, blurb in DESIGNS:
        svg, note = fn(act, args.profile_x)
        path = os.path.join(args.out, f"proof_{key}.svg")
        write(path, svg)
        print(f"  {key} · {name:10s} {w}x{h}  {note}", file=sys.stderr)
        if args.png:
            rasterise(path, os.path.join(args.out, f"proof_{key}.png"), w, h, args.dpi)
        cards.append(
            f'<figure><div class="p">{svg}</div><figcaption><b>{key} · {name}</b> '
            f'<span class=n>{esc(note)}</span><br>{esc(blurb)}</figcaption></figure>')

    html = (
        "<!doctype html><meta charset=utf-8><title>Mt. Whitney — five proofs</title><style>"
        "body{margin:0;padding:28px;background:#e9e4da;"
        "font:15px/1.5 -apple-system,Segoe UI,Helvetica,sans-serif;color:#33312e}"
        "h1{font-weight:500;margin:0 0 4px;font-size:22px}"
        "p.sub{margin:0 0 22px;color:#6d675e}"
        ".g{display:grid;grid-template-columns:repeat(2,1fr);gap:30px}"
        "figure{margin:0}.p svg{width:100%;height:auto;display:block;"
        "box-shadow:0 8px 30px rgba(0,0,0,.25)}"
        "figcaption{margin-top:10px;max-width:62ch}"
        ".n{color:#6d675e;font-size:13px}</style>"
        f"<h1>Mt. Whitney · 1 October 2025 — five proofs</h1>"
        f"<p class=sub>11&times;14 in at 100 units per inch &middot; one ink "
        f"{INK} on {BG} &middot; profile x-axis: {args.profile_x}</p>"
        "<div class=g>" + "".join(cards) + "</div>")
    write(os.path.join(args.out, "proofs.html"), html)
    print("wrote " + os.path.join(args.out, "proofs.html"), file=sys.stderr)


if __name__ == "__main__":
    main()
