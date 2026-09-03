"""eink_route_maps.py -- PROTOTYPE: route-progress cards drawn on a real road map.

Reference implementation for the strip-map / overview / corridor / fan treatments
of idea #38 (see Project Docs/Plans/strava-data/eink-feed-plan.md). Not a build
step. The production feed builder should lift Graph (road-graph build + snapping +
crossing noding), build_route/along, Frame, draw_basemap/draw_route/draw_cities and
mock_strip out of here into strava-data/feed/ and cache the routed polylines as
an asset so the 50 MB roads file is never touched at deploy time.

Needs two Natural Earth files in a cache dir (default strava-data/assets/cache/,
gitignored; override with NE_CACHE=...):
  ne_roads.geojson   https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_roads.geojson
  ne_places.geojson  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_populated_places_simple.geojson

Run from the repo root:  uv run python strava-data/tools/eink_route_maps.py
Writes 8 PNGs + a sheet to <cache>/route-maps/.
"""
import heapq, json, math, os, sys
from PIL import Image, ImageDraw

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
S = os.environ.get("NE_CACHE", os.path.join(ROOT, "strava-data", "assets", "cache"))
sys.path.insert(0, _HERE)
import eink_cards as K  # noqa: E402
from eink_cards import (W, H, M, BLACK, DARK, LIGHT, WHITE, new_card, quantize, header, footer,  # noqa: E402
                        text, font, ic_run, ic_bike, ROUTE_LADDER, load_activities, KM_TO_MI, is_run, is_bike, mf)

HOME = (-117.12, 32.96)  # 92129 Rancho Penasquitos
BBOX = (-125.5, 30.5, -106.0, 47.5)  # lng0, lat0, lng1, lat1
OUT = os.path.join(S, "route-maps")
os.makedirs(OUT, exist_ok=True)

FALLBACK = {  # (lng, lat) for places missing from NE populated places
    "Truckee": (-120.183, 39.328), "Yosemite": (-119.588, 37.748), "Primm": (-115.39, 35.61),
    "Baker": (-116.07, 35.27), "St. George": (-113.58, 37.10), "Cedar City": (-113.06, 37.68),
    "Provo": (-111.66, 40.23), "Gila Bend": (-112.72, 32.95), "El Centro": (-115.56, 32.79),
    "Beaumont": (-116.98, 33.93), "Temecula": (-117.15, 33.49), "San Clemente": (-117.61, 33.43),
    "Oceanside": (-117.38, 33.20), "Irvine": (-117.83, 33.68), "Anaheim": (-117.91, 33.84),
    "Ventura": (-119.29, 34.27), "Victorville": (-117.29, 34.54), "Barstow": (-117.02, 34.90),
    "Yuma": (-114.63, 32.69), "Olympia": (-122.90, 47.04), "Vail": (-106.37, 39.64),
    "Grand Junction": (-108.55, 39.06), "Palm Springs": (-116.55, 33.83), "Tijuana": (-117.04, 32.51),
    "Santa Barbara": (-119.70, 34.42), "Salt Lake City": (-111.89, 40.76), "Denver": (-104.99, 39.74),
    "Seattle": (-122.33, 47.61), "Tucson": (-110.97, 32.22), "Las Cruces": (-106.78, 32.32),
}


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


# ------------------------------------------------------------------ data
def load_places():
    p = json.load(open(os.path.join(S, "ne_places.geojson")))
    out = {}
    for f in p["features"]:
        pr = f["properties"]
        if pr["adm0name"] not in ("United States of America", "Mexico"):
            continue
        key = pr["nameascii"]
        lng, lat = f["geometry"]["coordinates"]
        # prefer bigger / western duplicate (Portland OR over ME, Las Vegas NV over NM)
        if key not in out or (BBOX[0] <= lng <= BBOX[2] and not (BBOX[0] <= out[key][0][0] <= BBOX[2])) \
           or (pr["pop_max"] > out[key][1] and BBOX[0] <= lng <= BBOX[2]):
            out[key] = ((lng, lat), pr["pop_max"], pr["adm1name"])
    return out


def city_xy(places, name):
    n = name.split(",")[0]
    if n in places and BBOX[0] <= places[n][0][0] <= BBOX[2]:
        return places[n][0]
    return FALLBACK.get(n)


class Graph:
    def __init__(self):
        roads = json.load(open(os.path.join(S, "ne_roads.geojson")))
        self.adj = {}
        self.segs = []  # for context drawing: list of (type, [pts])
        def key(p):
            return (round(p[0], 3), round(p[1], 3))
        for f in roads["features"]:
            pr = f["properties"]
            if pr.get("continent") != "North America" or pr.get("type") == "Ferry Route":
                continue
            g = f["geometry"]
            lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
            for line in lines:
                if not any(BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3] for x, y in line):
                    continue
                self.segs.append((pr.get("type"), [(x, y) for x, y in line]))
                for a, b in zip(line, line[1:]):
                    ka, kb = key(a), key(b)
                    if ka == kb:
                        continue
                    w = hav(a, b)
                    self.adj.setdefault(ka, []).append((kb, w))
                    self.adj.setdefault(kb, []).append((ka, w))
        # NE road lines meet at interior vertices (or mid-segment) and often stop
        # a few hundred metres short of the road they join. Snap every dangling
        # endpoint onto the nearest *segment* of another line within ~5 km by
        # adding edges to both ends of that segment; also merge near-coincident
        # vertices (<~0.4 km).
        grid = {}
        def cell(x, y):
            return (int(math.floor(x / 0.02)), int(math.floor(y / 0.02)))
        seg_index = {}
        for si, (t, pts) in enumerate(self.segs):
            for j, (a, b) in enumerate(zip(pts, pts[1:])):
                for cx in range(cell(min(a[0], b[0]), 0)[0], cell(max(a[0], b[0]), 0)[0] + 1):
                    for cy in range(cell(0, min(a[1], b[1]))[1], cell(0, max(a[1], b[1]))[1] + 1):
                        seg_index.setdefault((cx, cy), []).append((si, key(a), key(b)))
        for k in self.adj:
            grid.setdefault(cell(*k), []).append(k)
        def pt_seg(p, a, b):
            ax, ay, bx, by = a[0] * 0.8, a[1], b[0] * 0.8, b[1]
            px_, py_ = p[0] * 0.8, p[1]
            dx, dy = bx - ax, by - ay
            L = dx * dx + dy * dy
            t = 0 if L == 0 else max(0, min(1, ((px_ - ax) * dx + (py_ - ay) * dy) / L))
            return math.hypot(px_ - (ax + t * dx), py_ - (ay + t * dy))
        added = 0
        for si, (t, pts) in enumerate(self.segs):
            for e in (pts[0], pts[-1]):
                k = key(e)
                if len(self.adj.get(k, ())) > 1:
                    continue
                cx, cy = cell(*k)
                best, bd = None, 0.06
                for dx in (-3, -2, -1, 0, 1, 2, 3):
                    for dy in (-3, -2, -1, 0, 1, 2, 3):
                        for sj, ka, kb in seg_index.get((cx + dx, cy + dy), ()):
                            if sj == si:
                                continue
                            dd = pt_seg(k, ka, kb)
                            if dd < bd:
                                best, bd = (ka, kb), dd
                if best:
                    for q in best:
                        if q != k and not any(v == q for v, _ in self.adj[k]):
                            w = hav(k, q)
                            self.adj[k].append((q, w))
                            self.adj[q].append((k, w))
                            added += 1
        # (3) node true crossings: where two segments of different lines
        # intersect, add the intersection as a node joined to all four ends.
        def cross(a, b, c, d):
            def orient(p, q, r):
                return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
            o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
            if (o1 > 0) == (o2 > 0) or (o3 > 0) == (o4 > 0) or 0 in (o1, o2, o3, o4):
                return None
            t = o3 / (o3 - o4)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        seen = set()
        for cl, items in seg_index.items():
            for i in range(len(items)):
                si, a, b = items[i]
                for j in range(i + 1, len(items)):
                    sj, c, d = items[j]
                    if si == sj or (a, b, c, d) in seen:
                        continue
                    seen.add((a, b, c, d))
                    x = cross(a, b, c, d)
                    if not x:
                        continue
                    kx = key(x)
                    for q in (a, b, c, d):
                        if q != kx and not any(v == kx for v, _ in self.adj.get(q, ())):
                            w = hav(q, kx)
                            self.adj.setdefault(kx, []).append((q, w))
                            self.adj[q].append((kx, w))
                            added += 1
        for k in list(self.adj):
            grid.setdefault(cell(*k), []).append(k) if k not in grid.get(cell(*k), ()) else None
        for k in list(self.adj):
            cx, cy = cell(*k)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for q in grid.get((cx + dx, cy + dy), ()):
                        if q != k and math.hypot((q[0] - k[0]) * 0.8, q[1] - k[1]) < 0.004 \
                           and not any(v == q for v, _ in self.adj[k]):
                            w = hav(k, q)
                            self.adj[k].append((q, w))
                            self.adj[q].append((k, w))
                            added += 1
        self.nodes = list(self.adj)
        print(f"graph: {len(self.nodes)} nodes, {len(self.segs)} segments, {added} snap edges")

    def nearest(self, p):
        return min(self.nodes, key=lambda n: (n[0] - p[0]) ** 2 * 0.7 + (n[1] - p[1]) ** 2)

    def route(self, a, b):
        sa, sb = self.nearest(a), self.nearest(b)
        dist = {sa: 0.0}
        prev = {}
        pq = [(0.0, sa)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == sb:
                break
            if d > dist.get(u, 1e18):
                continue
            for v, w in self.adj[u]:
                nd = d + w
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        if sb not in dist:
            return None
        path = [sb]
        while path[-1] != sa:
            path.append(prev[path[-1]])
        return path[::-1]


def build_route(G, places, dest, wps):
    """Route home -> each waypoint -> dest along roads. Returns pts, cum miles, city marks."""
    chain = [("92129", HOME)] + [(n, city_xy(places, n)) for n, _ in wps] + [(dest.split(",")[0], city_xy(places, dest))]
    chain = [(n, p) for n, p in chain if p]
    pts, cum, marks = [], [0.0], []
    for (n0, p0), (n1, p1) in zip(chain, chain[1:]):
        leg = G.route(p0, p1)
        if not leg:
            print("  no road route", n0, "->", n1, "(straight line)")
            leg = [p0, p1]
        if pts:
            leg = leg[1:]
        for q in leg:
            if pts:
                cum.append(cum[-1] + hav(pts[-1], q))
            pts.append(q)
        marks.append((n1, cum[-1], pts[-1]))
    return pts, cum, [("92129", 0.0, pts[0])] + marks


def along(pts, cum, mi):
    """Point at `mi` miles along the polyline."""
    if mi >= cum[-1]:
        return pts[-1]
    i = max(0, min(len(cum) - 2, next(k for k, c in enumerate(cum) if c >= mi) - 1))
    t = (mi - cum[i]) / ((cum[i + 1] - cum[i]) or 1)
    return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)


# ------------------------------------------------------------------ map drawing
class Frame:
    """Equirectangular fit of a lng/lat box into a pixel box, aspect-preserving."""
    def __init__(self, box_px, lng0, lat0, lng1, lat1, pad=0.06):
        self.x0, self.y0, self.x1, self.y1 = box_px
        self.k = math.cos(math.radians((lat0 + lat1) / 2))
        dl = (lng1 - lng0) * pad
        dp = (lat1 - lat0) * pad
        lng0, lng1, lat0, lat1 = lng0 - dl, lng1 + dl, lat0 - dp, lat1 + dp
        w, h = self.x1 - self.x0, self.y1 - self.y0
        self.s = min(w / ((lng1 - lng0) * self.k), h / (lat1 - lat0))
        self.cx = (lng0 + lng1) / 2
        self.cy = (lat0 + lat1) / 2
        self.mx, self.my = (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2

    def xy(self, p):
        return (self.mx + (p[0] - self.cx) * self.k * self.s, self.my - (p[1] - self.cy) * self.s)

    def inside(self, p, margin=0):
        x, y = self.xy(p)
        return self.x0 - margin <= x <= self.x1 + margin and self.y0 - margin <= y <= self.y1 + margin


BASEMAP = json.load(open(os.path.join(ROOT, "strava-data", "assets", "basemap.json")))


def draw_basemap(d, fr, coast=DARK, admin=LIGHT, lakes=LIGHT, w=2):
    for layer, col, ww in (("lakes", lakes, w), ("admin", admin, w), ("coast", coast, w)):
        for flat in BASEMAP[layer]:
            pts = [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]
            if not any(fr.inside(p, 50) for p in pts[::5]):
                continue
            d.line([fr.xy(p) for p in pts], fill=col, width=ww)


def draw_roads_context(d, fr, G, col=LIGHT, w=2, types=("Major Highway",)):
    for t, pts in G.segs:
        if t not in types:
            continue
        if not any(fr.inside(p, 30) for p in pts[::4]):
            continue
        d.line([fr.xy(p) for p in pts], fill=col, width=w)


def draw_dashed(d, pts_px, fill, width, dash=14, gap=10):
    on, acc = True, 0.0
    for a, b in zip(pts_px, pts_px[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        pos = 0.0
        while pos < seg:
            run = (dash if on else gap) - acc
            end = min(seg, pos + run)
            if on:
                t0, t1 = pos / seg, end / seg
                d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                        (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill=fill, width=width)
            acc += end - pos
            pos = end
            if acc >= (dash if on else gap) - 1e-6:
                on, acc = not on, 0.0


def draw_route(d, fr, pts, cum, done_mi, w_done=6, w_todo=4):
    px = [fr.xy(p) for p in pts]
    i_done = next((k for k, c in enumerate(cum) if c >= done_mi), len(cum) - 1)
    m = fr.xy(along(pts, cum, done_mi))
    done_px = px[:i_done] + [m]
    todo_px = [m] + px[i_done:]
    if len(todo_px) > 1:
        d.line(todo_px, fill=WHITE, width=w_todo + 6, joint="curve")
        draw_dashed(d, todo_px, DARK, w_todo)
    if len(done_px) > 1:
        d.line(done_px, fill=WHITE, width=w_done + 6, joint="curve")
        d.line(done_px, fill=BLACK, width=w_done, joint="curve")
    return m


def draw_cities(d, fr, marks, done_mi, size=18, skip=()):
    placed = []
    for name, mi, p in marks:
        x, y = fr.xy(p)
        if not fr.inside(p):
            continue
        done = mi <= done_mi
        r = 7 if name != "92129" else 9
        d.ellipse([x - r, y - r, x + r, y + r], fill=BLACK if done else WHITE, outline=BLACK, width=3)
        if name in skip:
            continue
        # label: right of the dot unless near the right edge; nudge to avoid overlap
        f = font(size, done)
        tw_ = d.textlength(name, font=f)
        lx, anchor = x + 12, "lm"
        if lx + tw_ > fr.x1 - 4:
            lx, anchor = x - 12, "rm"
        ly = y
        for _ in range(6):
            if all(abs(ly - py) > size + 2 or abs(lx - plx) > tw_ + 10 for plx, py in placed):
                break
            ly += size + 2
        placed.append((lx, ly))
        d.rectangle([lx - 3 if anchor == "lm" else lx - tw_ - 3, ly - size / 2 - 1,
                     lx + tw_ + 3 if anchor == "lm" else lx + 3, ly + size / 2 + 1], fill=WHITE)
        text(d, (lx, ly), name, size, BLACK if done else DARK, bold=done, anchor=anchor)


def marker(d, xy, icon, size=48):
    x, y = xy
    d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=WHITE, outline=BLACK, width=4)
    d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=BLACK)
    # icon in a rounded box above
    bx0, by0 = x - 30 - size - 16, y - size / 2 - 8
    d.rounded_rectangle([bx0, by0, bx0 + size + 16, by0 + size + 16], radius=10, fill=WHITE, outline=BLACK, width=3)
    d.polygon([(x - 20, y), (x - 31, y - 9), (x - 31, y + 9)], fill=BLACK)
    icon(d, bx0 + size / 2 + 8, y, size, BLACK)


def scale_bar(d, fr, x, y, miles=100):
    lat = fr.cy
    px = miles / (69.0 * fr.k) * fr.k * fr.s  # miles -> deg lng -> px
    d.line([x, y, x + px, y], fill=BLACK, width=3)
    d.line([x, y - 6, x, y + 6], fill=BLACK, width=3)
    d.line([x + px, y - 6, x + px, y + 6], fill=BLACK, width=3)
    text(d, (x + px / 2, y - 8), f"{miles} mi", 15, DARK, bold=False, anchor="md")


def map_box(img, box):
    """Return (sub-image, draw) for a map window that we paste back, clipped."""
    x0, y0, x1, y1 = [int(v) for v in box]
    sub = Image.new("L", (x1 - x0, y1 - y0), WHITE)
    return sub, ImageDraw.Draw(sub), (x0, y0)


def frame_for(box_local, pts, extra=()):
    xs = [p[0] for p in pts] + [p[0] for p in extra]
    ys = [p[1] for p in pts] + [p[1] for p in extra]
    return Frame(box_local, min(xs), min(ys), max(xs), max(ys))


# ------------------------------------------------------------------ mockups
def mock_overview(R, sport, G):
    pts, cum, marks, total, dest, icon, verb = R
    img, d = new_card()
    y = header(d, f"92129 -> {dest}", kicker=f"{sport}: on the road map", right=f"{total:,.0f} of {cum[-1]:,.0f} mi")
    box = (M, y + 12, W - M, H - 132)
    sub, sd, off = map_box(img, box)
    fr = frame_for((0, 0, sub.width, sub.height), pts, [HOME])
    draw_basemap(sd, fr)
    draw_roads_context(sd, fr, G, LIGHT, 2)
    m = draw_route(sd, fr, pts, cum, total)
    draw_cities(sd, fr, marks, total)
    marker(sd, m, icon)
    scale_bar(sd, fr, 16, sub.height - 16)
    sd.rectangle([0, 0, sub.width - 1, sub.height - 1], outline=BLACK, width=3)
    img.paste(sub, off)
    passed = [mk for mk in marks if mk[1] <= total]
    nxt = next((mk for mk in marks if mk[1] > total), marks[-1])
    text(d, (M, H - 116), f"{total:,.0f} mi {verb}  |  {cum[-1] - total:,.0f} to {dest}", 24, BLACK, anchor="la")
    text(d, (M, H - 84), f"passed {passed[-1][0]}  -  next {nxt[0]} in {nxt[1] - total:,.0f} mi", 20, DARK, bold=False, anchor="la")
    footer(d, "thick = travelled, dashed = still to go  |  roads: Natural Earth 10m, routed along highways")
    return img


def mock_strip(R, sport, G):
    pts, cum, marks, total, dest, icon, verb = R
    img, d = new_card()
    y = header(d, f"92129 -> {dest}", kicker=f"{sport}: strip map", right=f"{total:,.0f} of {cum[-1]:,.0f} mi")
    # left ribbon: rotate route so start->end points up
    box = (M, y + 12, M + 330, H - 60)
    sub, sd, off = map_box(img, box)
    a, b = pts[0], pts[-1]
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    ang = math.atan2(b[1] - a[1], (b[0] - a[0]) * k)
    rot = math.pi / 2 - ang
    def r(p):
        x, yy = (p[0] - a[0]) * k, (p[1] - a[1])
        return (x * math.cos(rot) - yy * math.sin(rot), x * math.sin(rot) + yy * math.cos(rot))
    rp = [r(p) for p in pts]
    xs, ys = [p[0] for p in rp], [p[1] for p in rp]
    pad = 0.08
    w_, h_ = (max(xs) - min(xs)) or 1e-6, (max(ys) - min(ys)) or 1e-6
    sc = min((sub.width - 120) / w_, (sub.height - 70) / h_)
    ox = (sub.width - w_ * sc) / 2 - min(xs) * sc
    oy = sub.height - 35 + min(ys) * sc
    def px(p):
        q = r(p)
        return (ox + q[0] * sc, oy - q[1] * sc)
    ppx = [px(p) for p in pts]
    sd.rectangle([0, 0, sub.width - 1, sub.height - 1], fill=LIGHT)
    # road ribbon
    i_done = next((k for k, c in enumerate(cum) if c >= total), len(cum) - 1)
    mpt = px(along(pts, cum, total))
    sd.line(ppx, fill=WHITE, width=22, joint="curve")
    sd.line(ppx, fill=DARK, width=14, joint="curve")
    sd.line(ppx[:i_done] + [mpt], fill=BLACK, width=14, joint="curve")
    # mile ticks every 100
    for mi in range(100, int(cum[-1]), 100):
        q = px(along(pts, cum, mi))
        sd.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], fill=WHITE)
    # city labels
    lastY = 1e9
    for name, mi, p in marks:
        q = px(p)
        done = mi <= total
        sd.ellipse([q[0] - 8, q[1] - 8, q[0] + 8, q[1] + 8], fill=WHITE, outline=BLACK, width=3)
        ly = q[1]
        if lastY - ly < 22:
            ly = lastY - 22
        lastY = ly
        side = "lm" if q[0] < sub.width / 2 else "rm"
        lx = q[0] + 16 if side == "lm" else q[0] - 16
        text(sd, (lx, ly - 8), name, 17, BLACK if done else DARK, bold=done, anchor=side)
        text(sd, (lx, ly + 10), f"{mi:,.0f} mi", 13, DARK, bold=False, anchor=side)
    marker(sd, mpt, icon, 40)
    img.paste(sub, off)
    # right column
    rx = M + 360
    icon(d, rx + 40, y + 60, 72, BLACK)
    text(d, (rx + 100, y + 40), f"{total:,.0f}", 72, BLACK, anchor="la")
    text(d, (rx + 100, y + 118), f"miles {verb} so far", 20, DARK, bold=False, anchor="la")
    passed = [mk for mk in marks if mk[1] <= total]
    nxt = next((mk for mk in marks if mk[1] > total), marks[-1])
    rows = [("to go", f"{cum[-1] - total:,.0f} mi"), ("last passed", passed[-1][0]),
            ("next up", f"{nxt[0]} in {nxt[1] - total:,.0f} mi"), ("progress", f"{100 * total / cum[-1]:.0f}%")]
    yy = y + 160
    for lbl, val in rows:
        text(d, (rx, yy), lbl.upper(), 15, DARK, anchor="la")
        text(d, (rx, yy + 20), val, 26, BLACK, anchor="la", maxw=W - M - rx)
        yy += 66
    # inset locator
    ib = (rx, H - 190, W - M, H - 60)
    isub, isd, ioff = map_box(img, ib)
    ifr = frame_for((0, 0, isub.width, isub.height), pts, [HOME])
    draw_basemap(isd, ifr, DARK, LIGHT, LIGHT, 1)
    draw_route(isd, ifr, pts, cum, total, 3, 2)
    mm = ifr.xy(along(pts, cum, total))
    isd.ellipse([mm[0] - 6, mm[1] - 6, mm[0] + 6, mm[1] + 6], fill=BLACK)
    isd.rectangle([0, 0, isub.width - 1, isub.height - 1], outline=BLACK, width=2)
    img.paste(isub, ioff)
    footer(d, "ribbon = the real highway, rotated so the destination is up; ticks every 100 mi")
    return img


def mock_corridor(R, sport, G, places):
    pts, cum, marks, total, dest, icon, verb = R
    img, d = new_card()
    y = header(d, "You are here", kicker=f"{sport}: 92129 -> {dest}", right=f"{total:,.0f} of {cum[-1]:,.0f} mi")
    box = (M, y + 12, W - M, H - 150)
    sub, sd, off = map_box(img, box)
    c = along(pts, cum, total)
    half_mi = 70
    k = math.cos(math.radians(c[1]))
    dlng, dlat = half_mi / (69.0 * k), half_mi / 69.0
    fr = Frame((0, 0, sub.width, sub.height), c[0] - dlng, c[1] - dlat * 0.8, c[0] + dlng, c[1] + dlat * 0.8, pad=0)
    draw_basemap(sd, fr, DARK, LIGHT, LIGHT, 2)
    draw_roads_context(sd, fr, G, LIGHT, 2, ("Major Highway", "Secondary Highway", "Beltway"))
    m = draw_route(sd, fr, pts, cum, total, 8, 5)
    # towns in window
    towns = [(n, v[0]) for n, v in places.items() if fr.inside(v[0]) and v[1] >= 15000]
    towns.sort(key=lambda t: -places[t[0]][1])
    placed = []
    for n, p in towns[:9]:
        x, yy = fr.xy(p)
        if any(abs(x - a) < 90 and abs(yy - b) < 24 for a, b in placed):
            continue
        placed.append((x, yy))
        sd.rectangle([x - 4, yy - 4, x + 4, yy + 4], fill=DARK)
        text(sd, (x + 9, yy), n, 16, DARK, bold=False, anchor="lm")
    draw_cities(sd, fr, marks, total, 20)
    # distance rings 25/50 mi
    for mi in (25, 50):
        rr = mi / 69.0 * fr.s
        sd.ellipse([m[0] - rr, m[1] - rr, m[0] + rr, m[1] + rr], outline=LIGHT, width=2)
        text(sd, (m[0] + rr * 0.71, m[1] - rr * 0.71), f"{mi} mi", 13, DARK, bold=False, anchor="lm")
    marker(sd, m, icon)
    scale_bar(sd, fr, sub.width - 120, sub.height - 16, 25)
    # inset locator
    iw, ih = 150, 130
    isub = Image.new("L", (iw, ih), WHITE)
    isd = ImageDraw.Draw(isub)
    ifr = frame_for((0, 0, iw, ih), pts, [HOME])
    draw_basemap(isd, ifr, DARK, LIGHT, LIGHT, 1)
    draw_route(isd, ifr, pts, cum, total, 3, 2)
    mm = ifr.xy(c)
    isd.rectangle([mm[0] - 8, mm[1] - 8, mm[0] + 8, mm[1] + 8], outline=BLACK, width=2)
    isd.rectangle([0, 0, iw - 1, ih - 1], outline=BLACK, width=2)
    sub.paste(isub, (sub.width - iw - 8, 8))
    sd.rectangle([0, 0, sub.width - 1, sub.height - 1], outline=BLACK, width=3)
    img.paste(sub, off)
    passed = [mk for mk in marks if mk[1] <= total]
    nxt = next((mk for mk in marks if mk[1] > total), marks[-1])
    cols = [(f"{total:,.0f} mi", verb), (f"{passed[-1][0]}", f"passed, {total - passed[-1][1]:,.0f} mi back"),
            (f"{nxt[0]}", f"next, {nxt[1] - total:,.0f} mi ahead"), (f"{cum[-1] - total:,.0f} mi", f"to {dest}")]
    cw = (W - 2 * M) / 4
    for i, (num, lbl) in enumerate(cols):
        cx = M + cw * i + cw / 2
        text(d, (cx, H - 130), num, 28 if d.textlength(num, font=font(28)) <= cw - 10 else 22, BLACK, anchor="ma", maxw=cw - 10)
        text(d, (cx, H - 96), lbl, 16, DARK, bold=False, anchor="ma", maxw=cw - 10)
    footer(d, "window is +/-70 mi around your position; grey = other highways, squares = towns over 15k")
    return img


def mock_fan(R, sport, G, places, reached_routes):
    pts, cum, marks, total, dest, icon, verb = R
    img, d = new_card()
    y = header(d, f"{len(reached_routes)} cities reached", kicker=f"{sport}: the web so far", right=f"now -> {dest}")
    box = (M, y + 12, W - M, H - 132)
    sub, sd, off = map_box(img, box)
    allpts = list(pts) + [p for rp, _ in reached_routes for p in rp[::20]]
    fr = frame_for((0, 0, sub.width, sub.height), allpts, [HOME])
    draw_basemap(sd, fr)
    for rp, name in reached_routes:
        sd.line([fr.xy(p) for p in rp], fill=DARK, width=3, joint="curve")
    m = draw_route(sd, fr, pts, cum, total)
    placed = [fr.xy(HOME)]
    for rp, name in sorted(reached_routes, key=lambda t: -len(t[0])):
        x, yy = fr.xy(rp[-1])
        sd.ellipse([x - 7, yy - 7, x + 7, yy + 7], fill=BLACK)
        if any(abs(x - a) < 110 and abs(yy - b) < 20 for a, b in placed):
            continue
        placed.append((x, yy))
        text(sd, (x + 10, yy), name, 15, BLACK, anchor="lm")
    draw_cities(sd, fr, [marks[0], marks[-1]], total)
    marker(sd, m, icon)
    sd.rectangle([0, 0, sub.width - 1, sub.height - 1], outline=BLACK, width=3)
    img.paste(sub, off)
    text(d, (M, H - 116), f"{total:,.0f} mi {verb}  |  {cum[-1] - total:,.0f} to {dest}", 24, BLACK, anchor="la")
    text(d, (M, H - 84), "solid grey = destinations already reached, dashed = the current target", 20, DARK, bold=False, anchor="la")
    footer(d, "every rung of the ladder you've completed stays on the map")
    return img


def main():
    rows = load_activities()
    places = load_places()
    G = Graph()
    sheet_cards = []
    for sport, sel, icon, verb in (("Running", is_run, ic_run, "run"), ("Biking", is_bike, ic_bike, "ridden")):
        total = sum((mf(r["distance_km"]) or 0) * KM_TO_MI for r in rows if sel(r))
        dest, dist, wps = next(x for x in ROUTE_LADDER if x[1] > total)
        print(sport, f"{total:.0f} mi -> {dest} ({dist} ladder mi)")
        pts, cum, marks = build_route(G, places, dest, wps)
        print(f"  routed {cum[-1]:.0f} road mi, {len(pts)} pts")
        R = (pts, cum, marks, total, dest.split(",")[0], icon, verb)
        # reached routes for the fan (skip those that fail / out of bbox)
        reached = []
        for name, dm, w in ROUTE_LADDER:
            if dm > total:
                break
            p = city_xy(places, name)
            if not p or not (BBOX[0] <= p[0] <= BBOX[2]):
                continue
            rp = G.route(HOME, p)
            if rp:
                reached.append((rp, name.split(",")[0]))
        for tag, fn in (("overview", lambda: mock_overview(R, sport, G)),
                        ("strip", lambda: mock_strip(R, sport, G)),
                        ("corridor", lambda: mock_corridor(R, sport, G, places)),
                        ("fan", lambda: mock_fan(R, sport, G, places, reached))):
            img = quantize(fn())
            K.verify(img)
            path = os.path.join(OUT, f"{sport.lower()}-{tag}.png")
            img.save(path)
            sheet_cards.append((len(sheet_cards) + 1, f"{sport.lower()}-{tag}", img, f"{sport} - {tag}"))
            print("  wrote", path)
    K.contact_sheet(sheet_cards, os.path.join(OUT, "route-maps-sheet.png"))


if __name__ == "__main__":
    main()
