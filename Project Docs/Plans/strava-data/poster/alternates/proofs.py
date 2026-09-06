"""40 for 40 — the four design proofs, kept as a record of the choice.

ARCHIVED, not a build step. This is the script as it stood when the four layouts were
put side by side and A was picked; the poster that shipped is
strava-data/tools/poster_40for40.py. Its selection rules are the ORIGINAL ones and
have since diverged: quotas differ, road bikes and e-bikes are still their own family,
trail running still has its own colour, and there is none of the region or
route-similarity logic that came later. Re-running it reproduces the proofs as they were
seen, not the alternates under today's rules.

Read-only against the data. Writes proof_A..D.svg beside itself, plus a gitignored
proofs.html contact sheet.

    uv run python "Project Docs/Plans/strava-data/poster/alternates/proofs.py"
"""
import csv, math, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
# alternates -> poster -> strava-data -> Plans -> Project Docs -> repo root
ROOT = os.path.normpath(os.path.join(HERE, *[os.pardir] * 5))

OUT = HERE
STREAMS = os.path.join(ROOT, "strava-data", "data", "streams")

W, H = 1600, 2000            # 16x20 aspect, 100 units per inch
BG = "#F5F0E6"
INK = "#2B2A28"
MUTED = "#8A857B"
FAMILY = {"Run": "run", "TrailRun": "trail", "MountainBikeRide": "mtb", "Ride": "bike",
          "EBikeRide": "bike", "Hike": "hike", "Walk": "walk", "AlpineSki": "snow",
          "NordicSki": "snow", "Snowboard": "snow", "IceSkate": "snow"}
COLOR = {"run": "#1F6F78", "trail": "#4E7A3A", "mtb": "#C8602A", "bike": "#D9A441",
         "hike": "#7A3E5F", "walk": "#9A8F7E", "snow": "#5B8DB8"}
LABEL = {"run": "Run", "trail": "Trail run", "mtb": "Mountain bike", "bike": "Bike / e-bike",
         "hike": "Hike", "walk": "Walk", "snow": "Snow &amp; ice"}
ORDER = ["run", "trail", "mtb", "bike", "hike", "walk", "snow"]


def load():
    acts = [r for r in csv.DictReader(open(os.path.join(ROOT, "strava-data/data/activities.csv"), encoding="utf-8-sig"))
            if r["start_date_local"].startswith("2025")]
    out = []
    for r in acts:
        pts, alt = [], []
        with open(os.path.join(STREAMS, r["id"] + ".csv"), encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    pts.append((float(row["lng"]), float(row["lat"])))
                except ValueError:
                    continue
                try:
                    alt.append(float(row["altitude_m"]))
                except ValueError:
                    alt.append(alt[-1] if alt else 0.0)
        if len(pts) < 8:
            continue
        r["_pts"], r["_alt"] = pts, alt
        r["_mi"] = float(r["distance_km"] or 0) * 0.621371
        r["_ft"] = float(r["total_elevation_gain_m"] or 0) * 3.28084
        r["_fam"] = FAMILY.get(r["sport_type"], "walk")
        out.append(r)
    return sorted(out, key=lambda r: r["start_date_local"])


def pick40(acts):
    """Variety-first: quota per family, then spread picks across the year."""
    quota = {"run": 16, "mtb": 8, "hike": 5, "trail": 4, "snow": 4, "bike": 2, "walk": 1}
    chosen = []
    for fam, n in quota.items():
        pool = [r for r in acts if r["_fam"] == fam and r["_mi"] >= 1.0]
        pool.sort(key=lambda r: r["start_date_local"])
        if fam in ("hike", "snow"):                    # the big days are the point
            pool.sort(key=lambda r: -r["_mi"])
            chosen += pool[:n]
            continue
        # evenly spaced through the year, preferring the longer of neighbours
        if len(pool) <= n:
            chosen += pool
            continue
        step = len(pool) / n
        for i in range(n):
            lo, hi = int(i * step), int((i + 1) * step)
            chosen.append(max(pool[lo:hi], key=lambda r: r["_mi"]))
    return sorted(chosen, key=lambda r: r["start_date_local"])[:40]


def simplify(pts, n=240):
    if len(pts) <= n:
        return pts
    step = len(pts) / n
    return [pts[int(i * step)] for i in range(n)] + [pts[-1]]


def project(pts):
    """Equirectangular with cos(lat) correction, in metres, origin at bbox min."""
    lat0 = sum(p[1] for p in pts) / len(pts)
    k = math.cos(math.radians(lat0)) * 111_320
    xs = [(p[0]) * k for p in pts]
    ys = [-(p[1]) * 110_540 for p in pts]
    x0, y0 = min(xs), min(ys)
    xs = [x - x0 for x in xs]; ys = [y - y0 for y in ys]
    return list(zip(xs, ys)), max(xs), max(ys)


def fit(path, w, h, x, y, cw, ch, pad=0.0, scale=None):
    aw, ah = cw * (1 - 2 * pad), ch * (1 - 2 * pad)
    k = scale if scale else min(aw / max(w, 1e-9), ah / max(h, 1e-9))
    ox = x + (cw - w * k) / 2
    oy = y + (ch - h * k) / 2
    return [(ox + px * k, oy + py * k) for px, py in path]


def poly(pts, stroke, sw, opacity=1.0, fill="none"):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f'<polyline points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linejoin="round" stroke-linecap="round" opacity="{opacity}"/>')


def text(x, y, s, size, weight=400, anchor="start", fill=INK, spacing=0, family="Georgia, 'Times New Roman', serif"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}" letter-spacing="{spacing}">{s}</text>')


SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"


def legend(y, fams_present, x0=140, gap=None):
    parts = []
    items = [f for f in ORDER if f in fams_present]
    gap = gap or (W - 2 * x0) / max(len(items) - 1, 1)
    for i, f in enumerate(items):
        x = x0 + i * gap
        parts.append(f'<line x1="{x-38:.0f}" y1="{y}" x2="{x-8:.0f}" y2="{y}" stroke="{COLOR[f]}" stroke-width="5" stroke-linecap="round"/>')
        parts.append(text(x, y + 6, LABEL[f], 20, 400, "start", MUTED, 0.5, SANS))
    return "".join(parts)


def frame(body, title_block=True):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<rect width="{W}" height="{H}" fill="{BG}"/>{body}</svg>')


# ---------------------------------------------------------------- A · grid
def design_a(rows):
    cols, nrow = 5, 8
    top, bottom, side = 200, 260, 110
    cw = (W - 2 * side) / cols
    ch = (H - top - bottom) / nrow
    body = []
    body.append(text(side, 120, "40 for 40", 64, 400, "start", INK, -1))
    body.append(text(W - side, 118, "TWO THOUSAND TWENTY-FIVE", 20, 400, "end", MUTED, 4, SANS))
    for i, r in enumerate(rows):
        rr, c = divmod(i, cols)
        path, w, h = project(simplify(r["_pts"]))
        pts = fit(path, w, h, side + c * cw, top + rr * ch, cw, ch, pad=0.16)
        body.append(poly(pts, COLOR[r["_fam"]], 3.6))
        cx = side + c * cw + cw / 2
        body.append(text(cx, top + (rr + 1) * ch - 14, r["start_date_local"][5:10].replace("-", " · "), 15, 400, "middle", MUTED, 2, SANS))
    body.append(legend(H - 150, {r["_fam"] for r in rows}, x0=side + 40, gap=(W - 2 * side - 80) / 6))
    total = sum(r["_mi"] for r in rows)
    body.append(text(W / 2, H - 80, f"forty routes · {total:,.0f} miles · {sum(r['_ft'] for r in rows):,.0f} ft of climbing", 20, 400, "middle", MUTED, 2, SANS))
    return frame("".join(body))


# ------------------------------------------------------------- B · treemap
def squarify(items, x, y, w, h, out):
    """Squarified treemap (Bruls et al.). items = [(weight, obj)] sorted desc."""
    if not items:
        return
    total = sum(v for v, _ in items)
    if len(items) == 1:
        out.append((x, y, w, h, items[0][1])); return
    horizontal = w >= h
    side = h if horizontal else w
    row, best = [], None
    for i in range(len(items)):
        row.append(items[i])
        s = sum(v for v, _ in row) / total * (w * h)
        thick = s / side
        worst = max(max(thick / (v / total * w * h / thick), (v / total * w * h / thick) / thick) for v, _ in row)
        if best is not None and worst > best:
            row.pop(); break
        best = worst
    s = sum(v for v, _ in row) / total * (w * h)
    thick = s / side
    off = 0
    for v, obj in row:
        length = v / total * w * h / thick
        if horizontal:
            out.append((x, y + off, thick, length, obj))
        else:
            out.append((x + off, y, length, thick, obj))
        off += length
    rest = items[len(row):]
    if horizontal:
        squarify(rest, x + thick, y, w - thick, h, out)
    else:
        squarify(rest, x, y + thick, w, h - thick, out)


def tint(hexc, amt=0.86):
    r, g, b = int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16)
    br, bg_, bb = 0xF5, 0xF0, 0xE6
    return "#%02X%02X%02X" % (int(r + (br - r) * amt), int(g + (bg_ - g) * amt), int(b + (bb - b) * amt))


def design_b(rows):
    side, top, bottom = 90, 190, 210
    items = sorted(((max(r["_mi"], 1.2), r) for r in rows), key=lambda t: -t[0])
    cells = []
    squarify(items, side, top, W - 2 * side, H - top - bottom, cells)
    body = [text(side, 118, "40 for 40", 64, 400, "start", INK, -1),
            text(W - side, 116, "EACH TILE IS SIZED BY ITS MILES", 18, 400, "end", MUTED, 4, SANS)]
    g = 7
    for x, y, w, h, r in cells:
        col = COLOR[r["_fam"]]
        body.append(f'<rect x="{x+g/2:.1f}" y="{y+g/2:.1f}" width="{w-g:.1f}" height="{h-g:.1f}" fill="{tint(col)}" rx="3"/>')
        path, pw, ph = project(simplify(r["_pts"]))
        pts = fit(path, pw, ph, x, y, w, h, pad=0.17)
        body.append(poly(pts, col, 3.2 if min(w, h) > 150 else 2.4))
        if min(w, h) > 120:
            body.append(text(x + g / 2 + 12, y + h - g / 2 - 12, f"{r['_mi']:.0f} mi", 15, 400, "start", col, 1, SANS))
    body.append(legend(H - 120, {r["_fam"] for r in rows}, x0=side + 40, gap=(W - 2 * side - 80) / 6))
    return frame("".join(body))


# ----------------------------------------------------------- C · elevation
def design_c(rows):
    side, top, bottom = 150, 260, 260
    n = len(rows)
    band = (H - top - bottom) / n
    gmax = max(max(r["_alt"]) - min(r["_alt"]) for r in rows)
    body = [text(side, 118, "40 for 40", 64, 400, "start", INK, -1),
            text(W - side, 116, "FORTY ELEVATION PROFILES, 2025", 18, 400, "end", MUTED, 4, SANS)]
    # draw back-to-front so nearer (lower) ribbons occlude
    for i, r in enumerate(rows):
        alt = simplify(r["_alt"], 260)
        a0 = min(alt)
        base = top + (i + 1) * band + 40
        rng = max(max(alt) - a0, 1.0)
        amp = band * (0.9 + 3.6 * math.sqrt(rng / gmax))   # own range -> sqrt-scaled height
        pts = [(side + j / (len(alt) - 1) * (W - 2 * side), base - (a - a0) / rng * amp) for j, a in enumerate(alt)]
        fillpts = pts + [(W - side, base), (side, base)]
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in fillpts)
        body.append(f'<polygon points="{d}" fill="{BG}"/>')
        body.append(poly(pts, COLOR[r["_fam"]], 2.8))
        body.append(text(side - 18, base + 4, r["start_date_local"][5:10].replace("-", "·"), 13, 400, "end", MUTED, 1, SANS))
    body.append(legend(H - 110, {r["_fam"] for r in rows}, x0=side + 40, gap=(W - 2 * side - 80) / 6))
    return frame("".join(body))


# -------------------------------------------------------------- D · radial
def design_d(rows):
    cx, cy = W / 2, H / 2 + 40
    R = 600
    body = []
    n = len(rows)
    for i, r in enumerate(rows):
        ang = -math.pi / 2 + i / n * 2 * math.pi
        path, w, h = project(simplify(r["_pts"]))
        size = 60 + 90 * math.sqrt(min(r["_mi"], 22) / 22)   # sqrt-scaled by miles
        px, py = cx + R * math.cos(ang), cy + R * math.sin(ang)
        pts = fit(path, w, h, px - size / 2, py - size / 2, size, size)
        body.append(poly(pts, COLOR[r["_fam"]], 3.4))
        # tick + month label on the inner ring
        tx, ty = cx + (R - 150) * math.cos(ang), cy + (R - 150) * math.sin(ang)
        body.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="3" fill="{COLOR[r["_fam"]]}"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{R-150}" fill="none" stroke="{MUTED}" stroke-width="1" opacity="0.5"/>')
    body.append(text(cx, cy + 40, "40", 240, 400, "middle", INK, -8))
    body.append(text(cx, cy + 150, "FOR FORTY", 26, 400, "middle", MUTED, 8, SANS))
    body.append(text(cx, cy + 192, "clockwise from January", 18, 400, "middle", MUTED, 2, SANS))
    body.append(legend(H - 120, {r["_fam"] for r in rows}, x0=180, gap=(W - 360) / 6))
    return frame("".join(body))


def main():
    acts = load()
    rows = pick40(acts)
    print("picked", len(rows), collections.Counter(r["_fam"] for r in rows), file=sys.stderr)
    for r in rows:
        print(f"  {r['start_date_local'][:10]} {r['sport_type']:16s} {r['_mi']:5.1f} mi  {r['name'][:40]}", file=sys.stderr)
    designs = [("A", "The Grid", design_a(rows), "5×8 small multiples, uniform cells, aspect-fitted, one line per route, colour by sport, date under each."),
               ("B", "The Mosaic", design_b(rows), "Squarified treemap: tile area is proportional to miles, tinted by sport. Whitney dominates; the mile trial is a chip."),
               ("C", "Ridgelines", design_c(rows), "Forty elevation profiles stacked in date order with a shared vertical scale. Skis saw-tooth, hikes tower, runs ripple."),
               ("D", "The Year Ring", design_d(rows), "Routes on a clock face, January at 12, size ∝ √miles, a typographic 40 at the centre.")]
    cards = []
    for key, name, svg, blurb in designs:
        path = os.path.join(OUT, f"proof_{key}.svg")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        cards.append(f'<figure><div class="p">{svg}</div><figcaption><b>{key} · {name}</b><br>{blurb}</figcaption></figure>')
    html = ("<!doctype html><meta charset=utf-8><title>40 for 40 proofs</title><style>"
            "body{margin:0;padding:24px;background:#e9e4da;font:15px/1.45 -apple-system,Segoe UI,Helvetica,sans-serif;color:#333}"
            "h1{font-weight:500;margin:0 0 16px}.g{display:grid;grid-template-columns:repeat(2,1fr);gap:28px}"
            "figure{margin:0}.p svg{width:100%;height:auto;display:block;box-shadow:0 8px 30px rgba(0,0,0,.25)}"
            "figcaption{margin-top:10px;max-width:60ch}</style>"
            "<h1>40 for 40 — four proofs from the real 2025 tracks (16×20 aspect)</h1><div class=g>" + "".join(cards) + "</div>")
    with open(os.path.join(OUT, "proofs.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("wrote", os.path.join(OUT, "proofs.html"), file=sys.stderr)


if __name__ == "__main__":
    main()
