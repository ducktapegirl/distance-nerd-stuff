"""40 for 40 — a printable 16x20 poster of forty 2025 GPS routes.

Standalone: reads ``strava-data/data/`` directly, imports nothing from ``feed/`` or
``dashboard/``, and writes to ``Project Docs/Plans/strava-data/poster/``. It is not part of
any build or workflow — run it by hand when the print is wanted.

    uv run python strava-data/tools/poster_40for40.py            # poster.svg + README.md
    uv run python strava-data/tools/poster_40for40.py --png      # + poster.png at 300 dpi
    uv run python strava-data/tools/poster_40for40.py --swap <out_id>:<in_id> ...

Selection is "variety first": a per-sport quota, four mandatory routes, one pick reserved for
every region visited, and a grid-cell Jaccard test so two laps of the same loop don't both make
the wall. Ten runner-ups are listed so any pick can be swapped by id.
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "strava-data", "data")
STREAMS = os.path.join(DATA, "streams")
OUT_DIR = os.path.join(REPO, "Project Docs", "Plans", "strava-data", "poster")

YEAR = "2025"
N = 40
KM_TO_MI = 0.621371
M_TO_FT = 3.28084

# --- canvas: 16 x 20 in at 100 user units per inch ------------------------
W, H = 1600, 2000
COLS, ROWS = 5, 8
SIDE, TOP, BOTTOM = 110, 200, 260
STROKE = 3.6                       # ~0.9 mm on paper
CELL_PAD = 0.16

BG, INK, MUTED = "#F5F0E6", "#2B2A28", "#8A857B"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"

# --- sport families -----------------------------------------------------------
# A family is one colour and one legend figure, so the split is by how a route *looks and
# reads*, not by Strava's enum:
#   * Ride / EBikeRide are absent — cycling on this poster means mountain biking.
#   * Road and trail running are one family. They are the same motion on the same feet and
#     the shapes are indistinguishable at thumbnail size; the README still names the real
#     sport of every pick.
#   * Snow splits by direction of travel, which is what changes the shape of the track:
#     downhill (lift laps, a dense scribble on one hillside) against nordic (a long line
#     out and back). Ice skating goes with nordic as the other flat glide — 2025 has one,
#     a 0.7 mi pond skate, below MIN_MI and so never actually a candidate.
FAMILY = {"Run": "run", "TrailRun": "run", "MountainBikeRide": "mtb", "Hike": "hike",
          "Walk": "walk", "AlpineSki": "downhill", "Snowboard": "downhill",
          "NordicSki": "nordic", "IceSkate": "nordic"}
# Six families, six colours, no new hex: nordic inherits the green that road-and-trail
# merging freed up.
COLOR = {"run": "#1F6F78", "mtb": "#C8602A", "hike": "#7A3E5F",
         "walk": "#9A8F7E", "downhill": "#5B8DB8", "nordic": "#4E7A3A"}
LABEL = {"run": "Run", "mtb": "Mountain bike", "hike": "Hike",
         "walk": "Walk", "downhill": "Downhill", "nordic": "Nordic"}
# What a single activity is called, for the README. A family name would print "Run" against
# a trail run and "Downhill" against a snowboard, losing what you need to judge a swap.
SPORT_LABEL = {"Run": "Run", "TrailRun": "Trail run", "MountainBikeRide": "Mountain bike",
               "Hike": "Hike", "Walk": "Walk", "AlpineSki": "Alpine ski",
               "Snowboard": "Snowboard", "NordicSki": "Nordic ski", "IceSkate": "Ice skate"}
ORDER = ["run", "mtb", "hike", "walk", "downhill", "nordic"]
QUOTA = {"run": 20, "mtb": 10, "hike": 5, "downhill": 2, "nordic": 2, "walk": 1}
RUNNER_UP_QUOTA = {"run": 4, "mtb": 3, "hike": 1, "downhill": 1, "nordic": 1}
BY_SIZE = ("hike", "downhill", "nordic")   # ranked by miles; the rest spread over the year
MIN_MI = 1.0

# Merging a family for the legend must not quietly empty the poster of a terrain. Road and
# trail runs share a colour and a figure, but they do not share a shape — a canyon loop
# scribbles where a road run draws a long line — and on distance alone the road runs win
# every window, which took all eight trail runs off the sheet. This reserves part of the
# merged quota for the sport that would otherwise lose. Set the count to 0 to let distance
# decide on its own.
SUB_QUOTA = {"run": {"TrailRun": 4}}

# (date prefix, name fragment) — resolved to ids at runtime so a re-fetch can't break them.
MUST = [("2025-10-01", "Whitney"), ("2025-06-15", "Baldface"),
        ("2025-08-24", "San Jacinto"), ("2025-06-23", "40 for 40")]

REGION_KM = 10.0                    # same greedy clustering as feed/places.count_regions
CELL_M = 100.0                      # grid for the route-similarity signature


# ============================================================================ data

def mf(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load():
    with open(os.path.join(DATA, "activities.csv"), encoding="utf-8-sig") as f:
        acts = [r for r in csv.DictReader(f) if r["start_date_local"].startswith(YEAR)]
    out = []
    for r in acts:
        fam = FAMILY.get(r["sport_type"])
        if fam is None:
            continue
        path = os.path.join(STREAMS, f"{r['id']}.csv")
        if not os.path.exists(path):
            continue
        pts = []
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                lat, lng = mf(row.get("lat")), mf(row.get("lng"))
                if lat is not None and lng is not None:
                    pts.append((lng, lat))
        if len(pts) < 8:
            continue
        r["_fam"] = fam
        r["_pts"] = pts
        r["_mi"] = (mf(r["distance_km"]) or 0.0) * KM_TO_MI
        r["_ft"] = (mf(r["total_elevation_gain_m"]) or 0.0) * M_TO_FT
        r["_date"] = r["start_date_local"][:10]
        r["_cells"] = cells(pts)
        out.append(r)
    out.sort(key=lambda r: r["start_date_local"])
    return out


# ------------------------------------------------------------------- geometry

def metres(pts):
    """Absolute equirectangular metres (shared origin), so two tracks are comparable."""
    lat0 = sum(p[1] for p in pts) / len(pts)
    kx = math.cos(math.radians(lat0)) * 111_320.0
    return [(lng * kx, lat * 110_540.0) for lng, lat in pts]


def cells(pts):
    return frozenset((int(x // CELL_M), int(y // CELL_M)) for x, y in metres(pts))


def jaccard(a, b):
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def haversine_km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dl = math.radians(b[0] - a[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def assign_regions(acts, threshold_km=REGION_KM):
    """Greedy running-centroid clustering of start points (as feed/places.count_regions)."""
    centroids, counts = [], []
    for r in acts:
        p = r["_pts"][0]
        for i, cen in enumerate(centroids):
            if haversine_km(p, cen) <= threshold_km:
                n = counts[i]
                centroids[i] = ((cen[0] * n + p[0]) / (n + 1), (cen[1] * n + p[1]) / (n + 1))
                counts[i] = n + 1
                r["_region"] = i
                break
        else:
            r["_region"] = len(centroids)
            centroids.append(p)
            counts.append(1)
    return centroids


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


def shape(pts, tol_m=8.0, cap=600):
    """Track -> simplified path in local metres, origin top-left, y down."""
    m = metres(pts)
    x0, y0 = min(x for x, _ in m), max(y for _, y in m)
    m = [(x - x0, y0 - y) for x, y in m]
    s = douglas_peucker(m, tol_m)
    while len(s) > cap:
        tol_m *= 1.5
        s = douglas_peucker(m, tol_m)
    return s, max(x for x, _ in s), max(y for _, y in s)


def fit(path, w, h, x, y, cw, ch, pad):
    k = min(cw * (1 - 2 * pad) / max(w, 1e-9), ch * (1 - 2 * pad) / max(h, 1e-9))
    ox, oy = x + (cw - w * k) / 2, y + (ch - h * k) / 2
    return [(ox + px * k, oy + py * k) for px, py in path]


# ======================================================================== select

def resolve_musts(acts):
    ids = []
    for date, frag in MUST:
        hits = [r for r in acts if r["_date"] == date and frag.lower() in r["name"].lower()]
        if not hits:
            sys.exit(f"mandatory route not found: {date} / {frag!r}")
        ids.append(hits[0]["id"])
    return ids


def max_sim(r, chosen):
    return max((jaccard(r["_cells"], c["_cells"]) for c in chosen), default=0.0)


def take(pool, chosen, threshold):
    """Longest candidate not matching anything chosen; else the least-similar one."""
    ranked = sorted(pool, key=lambda r: -r["_mi"])
    for r in ranked:
        if max_sim(r, chosen) < threshold:
            return r
    return min(ranked, key=lambda r: max_sim(r, chosen)) if ranked else None


def select(acts, threshold, n=N):
    cand = [r for r in acts if r["_mi"] >= MIN_MI]
    assign_regions(cand)
    by_id = {r["id"]: r for r in cand}
    chosen, why = [], {}

    def add(r, reason):
        chosen.append(r)
        why[r["id"]] = reason

    for cid in resolve_musts(acts):
        add(by_id[cid] if cid in by_id else next(r for r in acts if r["id"] == cid), "must")

    # one pick per region visited, longest candidate there
    for reg in sorted({r["_region"] for r in cand}):
        if any(c.get("_region") == reg for c in chosen):
            continue
        r = take([r for r in cand if r["_region"] == reg], chosen, threshold)
        if r:
            add(r, "region")

    # Reserved slots inside a merged family, spread across the year like the family fill.
    for fam, subs in SUB_QUOTA.items():
        for sport, need in subs.items():
            pool = sorted((r for r in cand
                           if r["_fam"] == fam and r["sport_type"] == sport),
                          key=lambda r: r["start_date_local"])
            for i in range(need):
                if i >= len(pool):
                    break
                lo, hi = int(i * len(pool) / need), int((i + 1) * len(pool) / need)
                window = [w for w in pool[lo:hi] if w not in chosen]
                r = take(window, chosen, threshold)
                if r:
                    add(r, "terrain")

    quota = dict(QUOTA)
    for c in chosen:
        quota[c["_fam"]] = quota.get(c["_fam"], 0) - 1
    # keep the total at n: any overshoot from musts/regions comes out of the run quota
    quota["run"] += n - sum(QUOTA.values())
    over = -sum(v for v in quota.values() if v < 0)
    quota = {k: max(v, 0) for k, v in quota.items()}
    quota["run"] = max(quota["run"] - over, 0)

    for fam in ORDER:
        need = quota.get(fam, 0)
        pool = [r for r in cand if r["_fam"] == fam and r not in chosen]
        if need <= 0 or not pool:
            continue
        if fam in BY_SIZE:
            for _ in range(need):
                r = take(pool, chosen, threshold)
                if r is None:
                    break
                add(r, "size")
                pool.remove(r)
            continue
        # Spread over the year: cut the family's whole calendar into one window per
        # pick (including picks the musts/regions already made) and skip any window
        # that already holds one, so a region pick in March doesn't leave April empty.
        fam_all = sorted((r for r in cand if r["_fam"] == fam), key=lambda r: r["start_date_local"])
        windows = need + sum(1 for c in chosen if c["_fam"] == fam)
        step = len(fam_all) / windows
        for i in range(windows):
            window = fam_all[int(i * step):int((i + 1) * step)]
            if need <= 0 or any(w in chosen for w in window):
                continue
            r = take(window, chosen, threshold)
            if r:
                add(r, "spread")
                need -= 1
        while need > 0:                    # windows collided; top up from anywhere
            r = take([w for w in pool if w not in chosen], chosen, threshold)
            if r is None:
                break
            add(r, "spread")
            need -= 1

    chosen.sort(key=lambda r: r["start_date_local"])
    if len(chosen) != n:
        sys.exit(f"selected {len(chosen)} routes, wanted {n}")

    runners = []
    for fam, k in RUNNER_UP_QUOTA.items():
        rest = sorted((r for r in cand if r["_fam"] == fam and r not in chosen),
                      key=lambda r: (max_sim(r, chosen) >= threshold, -r["_mi"]))
        runners += rest[:k]
    return chosen, runners, why


def apply_swaps(chosen, acts, swaps):
    by_id = {r["id"]: r for r in acts}
    ids = [r["id"] for r in chosen]
    for s in swaps:
        out_id, in_id = s.split(":", 1)
        if out_id not in ids:
            sys.exit(f"--swap: {out_id} is not a current pick")
        if in_id not in by_id:
            sys.exit(f"--swap: {in_id} has no GPS track in {YEAR}")
        ids[ids.index(out_id)] = in_id
    return sorted((by_id[i] for i in ids), key=lambda r: r["start_date_local"])


# =========================================================================== svg

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def polyline(pts, stroke, sw=STROKE):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f'<polyline points="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>')


def text(x, y, s, size, family=SERIF, anchor="start", fill=INK, spacing=0, weight=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}" '
            f'letter-spacing="{spacing}">{esc(s)}</text>')


# --- glyph legend ---------------------------------------------------------------
# One figure per sport instead of a word. The art is a hand-made continuous-line drawing
# vectorised into ``assets/poster_glyphs.json`` by ``gen_poster_glyphs.py`` — see that
# script for the shape of the data. Two consequences matter here:
#
#   * A glyph is a FILLED outline (fill-rule evenodd), not a stroked centreline, so its
#     line weight is baked into the shape at whatever size it is drawn. Stroking the
#     outline in the same colour grows the ink on both sides, which is how GLYPH_WEIGHT
#     brings the figures up to the routes' 3.6 u without redrawing them.
#   * The sheet's six drawings now map one to one onto the six families, with the
#     snowboarder carrying downhill and the skier nordic.
GLYPH_SRC = {"run": "run", "mtb": "bike", "hike": "hike",
             "walk": "walk", "downhill": "board", "nordic": "ski"}
# Optical correction, applied on top of the common height, for figures whose box holds
# more than the athlete. The hiker's ground line climbs and the snowboarder is crouched
# over a board as long as she is tall, so fitting their boxes lands both heads well below
# everyone else's on a shared baseline. The cyclist needs none: she sits low because she
# is bent over the bars, which is simply true.
GLYPH_OPTICAL = {"hike": 1.08, "downhill": 1.12}
GLYPH_WEIGHT = 1.0                  # added ink, in the glyph's own 100-box units
GLYPH_H = 58.9                      # every figure is drawn to this height, not this width
GLYPH_GAP = 40.0                    # between figures; the row is a cluster, not a spread
CAPTION_DROP = 14                   # date caption baseline, above the grid's bottom edge
FOOTER_BASE = H - 70                # the summary line's baseline
FOOTER_CAP = 14                     # its cap height, for finding the top of the text


def load_glyphs(path=os.path.join(REPO, "strava-data", "assets", "poster_glyphs.json")):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    missing = sorted(set(GLYPH_SRC.values()) - set(raw))
    if missing:
        sys.exit(f"{path} is missing {missing} — re-run gen_poster_glyphs.py")
    out = {}
    for name, d in raw.items():
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
        xs, ys = nums[0::2], nums[1::2]
        if not xs:
            sys.exit(f"glyph {name!r} is empty — re-run gen_poster_glyphs.py")
        out[name] = {"d": d, "x0": min(xs), "x1": max(xs),
                     "y0": min(ys), "y1": max(ys)}
    return out


def glyph_size(fam, art):
    """Scale and drawn width for one figure.

    Scaling to a common *height* rather than to the 100-box keeps every athlete the
    same size. Fitting the box instead would shrink the two figures that carry
    equipment — the bike and the skis make those drawings wide, so the box forces the
    person inside them down to about three-quarters of everyone else.
    """
    g = art[GLYPH_SRC[fam]]
    s = GLYPH_H * GLYPH_OPTICAL.get(fam, 1.0) / max(g["y1"] - g["y0"], 1e-9)
    return s, (g["x1"] - g["x0"]) * s


def glyph(fam, x, base, colour, art):
    """Draw a figure with its ink starting at ``x`` and standing on ``base``."""
    g = art[GLYPH_SRC[fam]]
    s, _ = glyph_size(fam, art)
    tx, ty = x - g["x0"] * s, base - g["y1"] * s
    return (f'<path d="{g["d"]}" transform="translate({tx:.1f},{ty:.1f}) '
            f'scale({s:.4f})" fill="{colour}" fill-rule="evenodd" '
            f'stroke="{colour}" stroke-width="{GLYPH_WEIGHT:.2f}" stroke-linejoin="round"/>')


def render(rows):
    cw = (W - 2 * SIDE) / COLS
    ch = (H - TOP - BOTTOM) / ROWS
    body = [f'<rect width="{W}" height="{H}" fill="{BG}"/>',
            text(SIDE, 120, "40 for 40", 64, spacing=-1),
            text(W - SIDE, 118, "TWO THOUSAND TWENTY-FIVE", 20, SANS, "end", MUTED, 4)]
    for i, r in enumerate(rows):
        rr, c = divmod(i, COLS)
        path, w, h = shape(r["_pts"])
        pts = fit(path, w, h, SIDE + c * cw, TOP + rr * ch, cw, ch, CELL_PAD)
        body.append(polyline(pts, COLOR[r["_fam"]]))
        body.append(text(SIDE + c * cw + cw / 2, TOP + (rr + 1) * ch - CAPTION_DROP,
                         r["_date"][5:].replace("-", " · "), 15, SANS, "middle", MUTED, 2))

    # The legend is one centred cluster sitting in the white band between the last row of
    # dates and the summary line. Both edges of that band are derived from the type that
    # bounds it rather than typed in, so moving either piece keeps the row centred.
    fams = [f for f in ORDER if any(r["_fam"] == f for r in rows)]
    art = load_glyphs()
    sizes = [glyph_size(f, art) for f in fams]
    widths = [w for _, w in sizes]
    tallest = max(GLYPH_H * GLYPH_OPTICAL.get(f, 1.0) for f in fams)
    band_top = TOP + ROWS * ch - CAPTION_DROP
    band_bottom = FOOTER_BASE - FOOTER_CAP
    base = (band_top + band_bottom) / 2 + tallest / 2
    x = (W - (sum(widths) + GLYPH_GAP * (len(fams) - 1))) / 2
    for f, w in zip(fams, widths):
        body.append(glyph(f, x, base, COLOR[f], art))
        x += w + GLYPH_GAP

    miles = sum(r["_mi"] for r in rows)
    climb = sum(r["_ft"] for r in rows)
    body.append(text(W / 2, FOOTER_BASE,
                     f"forty routes · {miles:,.0f} miles · {climb:,.0f} ft of climbing",
                     20, SANS, "middle", MUTED, 2))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}">' + "".join(body) + "</svg>")


def rasterise(svg_path, png_path, dpi=300):
    from playwright.sync_api import sync_playwright
    scale = dpi / 100.0
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
        pg.goto("file:///" + svg_path.replace("\\", "/"))
        pg.screenshot(path=png_path)
        b.close()


# ======================================================================== report

def line(r, chosen, why):
    others = [c for c in chosen if c is not r]
    return (f"| `{r['id']}` | {r['_date']} | {SPORT_LABEL[r['sport_type']]} | {r['_mi']:.1f} | "
            f"{r['_ft']:,.0f} | {r.get('_region', '-')} | {max_sim(r, others):.2f} | {why} | "
            f"{esc(r['name'])} |")


def write_readme(path, chosen, runners, why, threshold, pairs):
    hdr = ("| id | date | sport | mi | ft | region | matched | picked | name |\n"
           "|---|---|---|---|---|---|---|---|---|")
    fam_counts = Counter(r["_fam"] for r in chosen)
    lines = [
        "# 40 for 40 — poster build",
        "",
        "Generated by `strava-data/tools/poster_40for40.py`. `poster.svg` is the print master "
        "(16 × 20 in, 100 user units per inch); `poster.png` is a 300 dpi raster of the same file.",
        "",
        "**Fonts.** Text is live `<text>` — title in Georgia, captions in Helvetica/Arial. "
        "A print shop that lacks them will substitute; ask for the PNG or have them outline the "
        "type from the SVG.",
        "",
        "## Selection",
        "",
        f"Variety-first: quota {dict(QUOTA)}, four mandatory routes, one pick reserved per "
        f"region (start points clustered at {REGION_KM:.0f} km), and any candidate whose grid-cell "
        f"Jaccard against an existing pick is ≥ {threshold} is treated as the same route and skipped. "
        f"Chosen mix: {', '.join(f'{LABEL[f]} {fam_counts[f]}' for f in ORDER if fam_counts[f])}.",
        "",
        "`matched` is each pick's highest similarity to any other pick (1.0 = identical cells).",
        "",
        "### The forty", "", hdr,
    ]
    lines += [line(r, chosen, why.get(r["id"], "swap")) for r in chosen]
    lines += ["", f"Most similar pair among the forty: {pairs[0][0]:.2f} — "
                  f"{pairs[0][1]['name']} ({pairs[0][1]['_date']}) vs "
                  f"{pairs[0][2]['name']} ({pairs[0][2]['_date']}).", "",
              "### Ten runner-ups", "",
              "Swap one in with `--swap <out_id>:<in_id>`; the grid re-sorts by date.", "", hdr]
    lines += [line(r, chosen, "runner-up") for r in runners]
    # newline="\n" wherever text is written: Python translates to CRLF on Windows,
    # where this is developed, while git stores LF, so without it every run of the
    # tool leaves the repo dirty with a diff that has no content in it.
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--png", action="store_true", help="also rasterise at --dpi via Playwright")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--swap", action="append", default=[], metavar="OUT_ID:IN_ID")
    ap.add_argument("--match-threshold", type=float, default=0.5)
    ap.add_argument("--out", default=OUT_DIR)
    a = ap.parse_args()

    acts = load()
    chosen, runners, why = select(acts, a.match_threshold)
    if a.swap:
        chosen = apply_swaps(chosen, acts, a.swap)

    pairs = sorted(((jaccard(x["_cells"], y["_cells"]), x, y)
                    for i, x in enumerate(chosen) for y in chosen[i + 1:]),
                   key=lambda t: -t[0])
    os.makedirs(a.out, exist_ok=True)
    svg_path = os.path.join(a.out, "poster.svg")
    with open(svg_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(chosen))
    write_readme(os.path.join(a.out, "README.md"), chosen, runners, why, a.match_threshold, pairs)
    if a.png:
        rasterise(svg_path, os.path.join(a.out, "poster.png"), a.dpi)

    print(f"{len(chosen)} routes, {Counter(r['_fam'] for r in chosen)}")
    print(f"regions covered: {sorted({r.get('_region') for r in chosen})}")
    print(f"max pairwise similarity: {pairs[0][0]:.2f}")
    for r in chosen:
        print(f"  {r['_date']} {r['_fam']:5s} {r['_mi']:5.1f} mi  {why.get(r['id'], 'swap'):6s} {r['id']}  {r['name']}")
    print("runner-ups:")
    for r in runners:
        print(f"  {r['_date']} {r['_fam']:5s} {r['_mi']:5.1f} mi  sim {max_sim(r, chosen):.2f}  {r['id']}  {r['name']}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
