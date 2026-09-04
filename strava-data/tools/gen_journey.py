"""Regenerate the Journey card road corridors (strava-data/assets/journey_routes.json).

Pulls Natural Earth 10m roads, keeps the US major-highway network, welds it into
a routable graph, and shortest-paths from 92129 out to each corridor's
destination. Writes the routed polyline, its cumulative mileage, and the cities
the road passes. The build (feed/geo.py) reads that asset -- no runtime network,
no routing at build time. Re-run only when the corridors or source data change:

    uv run python strava-data/tools/gen_journey.py

Source (public domain, Natural Earth): ne_10m_roads. ~50 MB, downloaded to a
temp file and never committed -- same treatment gen_basemap.py gives its sources.
Requires network; stdlib + urllib only.
"""
import heapq, json, math, os, tempfile, urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "journey_routes.json"))
SRC = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
       "master/geojson/ne_10m_roads.geojson")

HOME = (32.9545, -117.0910)          # 92129, Rancho Penasquitos
HOME_LABEL = "San Diego"

KEEP_TYPES = {"Major Highway", "Beltway"}
SNAP = 0.02              # degrees (~2 km) -- node welding tolerance
NEAR_MI = 70.0           # a city this close to the route counts as a milepost
MIN_GAP_MI = 120.0       # thin mileposts so labels have room on an 800px card
R_KM = 6371.0
MI = 0.621371

# One corridor per sport. Running goes east and ends at Boston (the Places
# section's two-homes story); riding goes southeast to Austin. The two share
# ~1% of their geometry, so the cards read as different journeys.
CORRIDORS = {
    "run": {
        "label": "running",
        "dest": ("Boston", 42.3601, -71.0589),
        "road": "I-8 → I-10 → I-40",
        "cities": [
            ("Los Angeles", 34.05, -118.24), ("Phoenix", 33.45, -112.07),
            ("Flagstaff", 35.20, -111.65), ("Albuquerque", 35.08, -106.65),
            ("Amarillo", 35.22, -101.83), ("Oklahoma City", 35.47, -97.52),
            ("Tulsa", 36.15, -95.99), ("St. Louis", 38.63, -90.20),
            ("Indianapolis", 39.77, -86.16), ("Columbus", 39.96, -83.00),
            ("Pittsburgh", 40.44, -79.996), ("New York City", 40.71, -74.01),
            ("Boston", 42.36, -71.06),
        ],
    },
    "bike": {
        "label": "riding",
        "dest": ("Austin", 30.2672, -97.7431),
        "road": "I-8 → I-10",
        "cities": [
            ("Yuma", 32.69, -114.62), ("Phoenix", 33.45, -112.07),
            ("Tucson", 32.22, -110.97), ("Las Cruces", 32.31, -106.78),
            ("El Paso", 31.76, -106.49), ("Van Horn", 31.04, -104.83),
            ("Fort Stockton", 30.89, -102.88), ("Ozona", 30.71, -101.20),
            ("San Antonio", 29.42, -98.49), ("Austin", 30.27, -97.74),
        ],
    },
}


def hav(a, b):
    """Great-circle distance in km between two (lat, lng) pairs."""
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_KM * math.asin(math.sqrt(h))


class Welder:
    """Spatial hash that reuses an existing node within SNAP of a new point.

    Natural Earth is a cartographic layer, not a routing network: segment
    endpoints are near-coincident rather than identical. Plain grid rounding is
    not enough to join them -- two endpoints 1 km apart can straddle a cell
    boundary, which shattered the network into 229 components and made obviously
    reachable cities unroutable. Searching the 3x3 neighbourhood fixes it.
    """

    def __init__(self, tol=SNAP):
        self.tol = tol
        self.cells = defaultdict(list)
        self.nodes = {}
        self._next = 0

    def add(self, lat, lng):
        cx, cy = int(lat / self.tol), int(lng / self.tol)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for nid in self.cells[(cx + dx, cy + dy)]:
                    nlat, nlng = self.nodes[nid]
                    if abs(nlat - lat) <= self.tol and abs(nlng - lng) <= self.tol:
                        return nid
        nid = self._next
        self._next += 1
        self.nodes[nid] = (lat, lng)
        self.cells[(cx, cy)].append(nid)
        return nid


def _iter_lines(geom):
    t, c = geom.get("type"), geom.get("coordinates")
    if t == "LineString":
        return [c]
    if t == "MultiLineString":
        return c
    return []


def build_graph(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    adj = defaultdict(dict)
    w = Welder()
    for feat in data["features"]:
        p = feat["properties"]
        if p.get("sov_a3") != "USA" or p.get("type") not in KEEP_TYPES:
            continue
        for coords in _iter_lines(feat["geometry"]):
            prev = None
            for lng, lat in coords:
                k = w.add(lat, lng)
                if prev is not None and prev != k:
                    d = hav(w.nodes[prev], w.nodes[k])
                    if d and (k not in adj[prev] or d < adj[prev][k]):
                        adj[prev][k] = d
                        adj[k][prev] = d
                prev = k
    return adj, w.nodes


def main_component(adj, nodes):
    """Node ids in the largest connected component.

    Natural Earth leaves a few hundred small orphan clusters; snapping a city to
    one produces a silent "no route" for a city that is plainly reachable.
    """
    seen, best = set(), set()
    for n in nodes:
        if n in seen:
            continue
        stack, comp = [n], set()
        seen.add(n)
        while stack:
            u = stack.pop()
            comp.add(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        if len(comp) > len(best):
            best = comp
    return best


def route(adj, nodes, a, b, allowed):
    """Dijkstra between two (lat, lng) points. Returns (path, miles)."""
    near = lambda pt: min(allowed, key=lambda k: hav(nodes[k], pt))
    s, t = near(a), near(b)
    dist, prev, pq, seen = {s: 0.0}, {}, [(0.0, s)], set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        if u == t:
            break
        for v, wgt in adj[u].items():
            nd = d + wgt
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if t not in dist:
        raise SystemExit("no route between %s and %s" % (a, b))
    path, cur = [], t
    while cur != s:
        path.append(nodes[cur])
        cur = prev[cur]
    path.append(nodes[s])
    path.reverse()
    return path, dist[t] * MI


def cumulative(path):
    out = [0.0]
    for a, b in zip(path, path[1:]):
        out.append(out[-1] + hav(a, b) * MI)
    return out


def mileposts(path, cum, cities):
    """Cities the route passes, with the mileage at which it passes them."""
    found = []
    for name, la, lo in cities:
        i = min(range(len(path)), key=lambda k: hav(path[k], (la, lo)))
        off = hav(path[i], (la, lo)) * MI
        if off <= NEAR_MI:
            found.append((cum[i], name, off))
    found.sort()
    keep = []
    for mi, name, off in found:
        if not keep or mi - keep[-1][0] >= MIN_GAP_MI:
            keep.append((mi, name, off))
    return keep


def main():
    tmp = os.path.join(tempfile.gettempdir(), "ne_10m_roads.geojson")
    if not os.path.exists(tmp):
        print("downloading %s ..." % SRC)
        urllib.request.urlretrieve(SRC, tmp)
    print("building graph from %s" % tmp)
    adj, nodes = build_graph(tmp)
    mc = main_component(adj, nodes)
    print("  %d nodes, %d edges, main component %d" %
          (len(nodes), sum(len(v) for v in adj.values()) // 2, len(mc)))

    out = {"home": {"lat": HOME[0], "lng": HOME[1], "label": HOME_LABEL},
           "corridors": {}}
    for key, spec in CORRIDORS.items():
        dname, dlat, dlng = spec["dest"]
        path, total = route(adj, nodes, HOME, (dlat, dlng), mc)
        cum = cumulative(path)
        posts = mileposts(path, cum, spec["cities"])
        out["corridors"][key] = {
            "label": spec["label"],
            "road": spec["road"],
            "destination": dname,
            "total_mi": round(total, 1),
            "path": [[round(la, 4), round(lo, 4)] for la, lo in path],
            "cum_mi": [round(v, 1) for v in cum],
            "mileposts": [{"mi": round(mi, 1), "name": n, "off_mi": round(o, 1)}
                          for mi, n, o in posts],
        }
        print("  %-5s -> %-8s %7.0f mi, %d points, %d mileposts"
              % (key, dname, total, len(path), len(posts)))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    txt = json.dumps(out, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print("wrote %s (%.1f KB)" % (OUT, len(txt.encode("utf-8")) / 1024.0))


if __name__ == "__main__":
    main()
