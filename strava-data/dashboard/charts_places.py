"""Places hero: a bespoke <canvas> route-density map (additive glow), ported
from strava-data/mocks/places-hero-mock.html with real GPS streams injected as
JSON. Returns one self-contained raw HTML string (the chart_calendar() raw-string
precedent) -- NOT a Plotly figure. All heavy Places code lives here, not in
charts_production.py. Imports are stdlib + numpy only (no pandas)."""

import json
import math
import os

from .config import STREAMS_DIR
from .data import mf

# ── Pinned constants (analyst Pass-A recipe; see dashboard-spec "Places") ──────
# COSLAT is the cosine of the RAW-extent midpoint latitude (40.9685) -- a frozen
# constant, never recomputed from the margined frame.
COSLAT = 0.7551
RDP_EPS = 0.0001          # degrees (~11 m)
POINT_CAP = 150           # hard cap per track, uniform stride

# Sport -> legend bucket index (with the analyst's folds).
_RUN_SPORTS  = {"Run", "TrailRun", "Walk"}                 # Walk folds into Running
_MTB_SPORTS  = {"MountainBikeRide", "EBikeRide", "Ride"}    # EBike/Ride fold into MTB
_SKI_SPORTS  = {"AlpineSki", "NordicSki", "Snowboard"}      # Trail / ski
_HIKE_SPORTS = {"Hike"}
# everything else (Pickleball, IceSkate, StandUpPaddling, ...) -> Other (silent)

# Home classification boxes (lat_lo, lat_hi, lng_lo, lng_hi).
_SD_BOX  = (32.5, 33.5, -117.6, -116.6)
_BOS_BOX = (41.9, 42.9, -71.8, -70.7)

# Key-trip label anchor boxes (centroid of contained trip first-points).
_SIERRA_BOX    = (36.0, 37.2, -118.9, -117.9)
_MAINE_BOX     = (44.6, 45.6, -71.2, -69.9)
_VANCOUVER_BOX = (48.9, 49.5, -124.3, -122.9)

# View-button framing boxes (lat_lo, lat_hi, lng_lo, lng_hi).
_VIEW_SD_BOX  = (32.55, 33.25, -117.40, -116.85)
_VIEW_BOS_BOX = (42.18, 42.60, -71.80, -70.95)

# DESCRIPTIVE (non-numeric) label copy stays hardcoded; the activity COUNTS in
# the home sub-lines are computed live at build time (see _count_places) so the
# fetch cron can't leave them stale. Era labels + key-trip details are static.
_SD_ERA   = "2025–now"
_BOS_ERA  = "2024–2025"
_SIERRA_DETAIL    = "Whitney · 14,507 ft"
_MAINE_DETAIL     = "hut ski · 3 days"
_VANCOUVER_DETAIL = "49.3°N · northernmost"

# States / provinces bounding-box table (name, lat_lo, lat_hi, lng_lo, lng_hi),
# priority-ordered: the tightly-interleaved New England states (VT/NH/ME) resolve
# before MA, then broad North-America coverage so plausible future trips land
# somewhere. Each start point is assigned to the FIRST matching box; distinct
# assigned boxes are counted. Verified to yield the pinned 9 (CA MA MI WA ME VT
# NH NY BC) with zero uncovered points on today's 319 start points.
_STATE_BOXES = [
    ("CA", 32.30, 42.10, -124.50, -114.00),
    ("WA", 45.50, 49.00, -124.85, -116.90),
    ("BC", 49.00, 60.10, -139.10, -114.00),
    ("MI", 41.65, 48.35, -90.50, -82.10),
    ("NY", 40.40, 45.05, -79.90, -73.30),
    ("VT", 42.70, 45.05, -73.45, -71.50),
    ("NH", 42.70, 45.35, -72.55, -70.60),
    ("ME", 43.00, 47.50, -71.10, -66.90),
    ("MA", 41.20, 42.90, -73.55, -69.85),
    ("OR", 41.90, 46.30, -124.60, -116.45),
    ("NV", 35.00, 42.05, -120.10, -114.00),
    ("AZ", 31.30, 37.05, -114.90, -109.00),
    ("UT", 36.95, 42.05, -114.10, -108.95),
    ("ID", 41.95, 49.05, -117.30, -111.00),
    ("MT", 44.30, 49.05, -116.10, -104.00),
    ("WY", 40.95, 45.05, -111.10, -104.00),
    ("CO", 36.95, 41.05, -109.10, -102.00),
    ("NM", 31.30, 37.05, -109.10, -103.00),
    ("TX", 25.80, 36.55, -106.70, -93.50),
    ("MN", 43.45, 49.40, -97.30, -89.45),
    ("WI", 42.45, 47.10, -92.90, -86.75),
    ("IL", 36.95, 42.55, -91.55, -87.00),
    ("IN", 37.75, 41.80, -88.10, -84.75),
    ("OH", 38.35, 42.35, -84.85, -80.50),
    ("PA", 39.70, 42.30, -80.55, -74.65),
    ("NJ", 38.90, 41.40, -75.60, -73.85),
    ("CT", 40.95, 42.10, -73.75, -71.75),
    ("RI", 41.10, 42.05, -71.90, -71.10),
    ("MD", 37.90, 39.75, -79.50, -75.00),
    ("VA", 36.50, 39.50, -83.70, -75.20),
    ("NC", 33.80, 36.60, -84.35, -75.40),
    ("GA", 30.35, 35.05, -85.65, -80.80),
    ("FL", 24.40, 31.05, -87.65, -79.95),
    ("TN", 34.95, 36.70, -90.35, -81.60),
    ("AB", 48.95, 60.10, -120.10, -109.95),
    ("SK", 48.95, 60.10, -110.05, -101.30),
    ("MB", 48.95, 60.10, -102.05, -88.90),
    ("ON", 41.65, 56.90, -95.20, -74.30),
    ("QC", 44.95, 62.60, -79.80, -57.05),
]


def _bucket(sport):
    if sport in _RUN_SPORTS:  return 0
    if sport in _MTB_SPORTS:  return 1
    if sport in _SKI_SPORTS:  return 2
    if sport in _HIKE_SPORTS: return 3
    return 4


def _rdp(pts, eps):
    """Ramer-Douglas-Peucker on an [lng,lat] polyline (perpendicular distance in
    the raw degree plane). Iterative to avoid recursion limits on long streams."""
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
        dx = bx - ax
        dy = by - ay
        denom = math.hypot(dx, dy)
        dmax = 0.0
        idx = -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if denom == 0.0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * px - dx * py + bx * ay - by * ax) / denom
            if d > dmax:
                dmax = d
                idx = i
        if dmax > eps and idx != -1:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [pts[i] for i in range(n) if keep[i]]


def _stride_cap(pts, cap=POINT_CAP):
    """Hard-cap to `cap` points by uniform stride (endpoints included)."""
    n = len(pts)
    if n <= cap:
        return pts
    return [pts[round(i * (n - 1) / (cap - 1))] for i in range(cap)]


def _load_tracks(act_by_id):
    """Read data/streams/*.csv (stdlib csv via numpy-free parsing), skip the
    blank-GPS files, RDP-decimate + stride-cap each [lng,lat] polyline, round to
    5 decimals, and classify sport bucket `c` and home/trip group `g`.

    Returns (tracks, extents) where tracks is a list of dicts
    {c, g, pts:[(lng,lat),...], first:(lng,lat)} and extents is the raw drawn
    bounding box (lat_min, lat_max, lng_min, lng_max)."""
    import csv

    tracks = []
    lat_min = lat_max = lng_min = lng_max = None

    for fn in sorted(os.listdir(STREAMS_DIR)):
        if not fn.endswith(".csv"):
            continue
        aid = fn[:-4]
        raw = []
        with open(os.path.join(STREAMS_DIR, fn), encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                ln = mf((row.get("lng") or "").strip())
                la = mf((row.get("lat") or "").strip())
                if ln is None or la is None:
                    continue
                raw.append((ln, la))
        if not raw:                       # blank-GPS (indoor) file -> skip
            continue

        dec = _stride_cap(_rdp(raw, RDP_EPS))
        dec = [(round(ln, 5), round(la, 5)) for ln, la in dec]
        first = dec[0]

        sport = (act_by_id.get(aid) or {}).get("sport_type", "")
        c = _bucket(sport)
        g = _group(first)

        tracks.append({"c": c, "g": g, "pts": dec, "first": first})
        for ln, la in dec:
            lat_min = la if lat_min is None else min(lat_min, la)
            lat_max = la if lat_max is None else max(lat_max, la)
            lng_min = ln if lng_min is None else min(lng_min, ln)
            lng_max = ln if lng_max is None else max(lng_max, ln)

    return tracks, (lat_min, lat_max, lng_min, lng_max)


def _in_box(lng, lat, box):
    lat_lo, lat_hi, lng_lo, lng_hi = box
    return lat_lo <= lat <= lat_hi and lng_lo <= lng <= lng_hi


def _start_points(rows):
    """(lng, lat) for every activity with a non-empty start_latlng. The CSV
    stores start_latlng as 'lat,lng' (mirrors the retired chart_map parser)."""
    pts = []
    for r in rows:
        ll = (r.get("start_latlng") or "").strip()
        if not ll:
            continue
        parts = ll.split(",")
        if len(parts) != 2:
            continue
        lat = mf(parts[0].strip())
        lng = mf(parts[1].strip())
        if lat is None or lng is None:
            continue
        pts.append((lng, lat))
    return pts


def _haversine_km(a, b):
    (lng1, lat1), (lng2, lat2) = a, b
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _count_regions(pts, threshold_km=10.0):
    """Greedy spatial clustering: each point joins the first existing cluster
    whose running-mean centroid is within `threshold_km`, else opens a new
    cluster. Returns the cluster count (28 today at 10 km)."""
    clusters = []   # each: [cen_lng, cen_lat, n]
    for lng, lat in pts:
        joined = False
        for c in clusters:
            if _haversine_km((lng, lat), (c[0], c[1])) <= threshold_km:
                n = c[2]
                c[0] = (c[0] * n + lng) / (n + 1)
                c[1] = (c[1] * n + lat) / (n + 1)
                c[2] = n + 1
                joined = True
                break
        if not joined:
            clusters.append([lng, lat, 1])
    return len(clusters)


def _count_states(pts):
    """Distinct US states + Canadian provinces via the _STATE_BOXES table. Each
    point is assigned to the first matching box; distinct boxes are counted.
    Points outside every box become their own 'unknown' bucket (never silently
    dropped) and are returned so the caller can print a coverage warning.
    Returns (distinct_count, uncovered_points)."""
    seen = set()
    uncovered = []
    for lng, lat in pts:
        hit = None
        for name, la, lb, lo, hi in _STATE_BOXES:
            if la <= lat <= lb and lo <= lng <= hi:
                hit = name
                break
        if hit is None:
            uncovered.append((lat, lng))
        else:
            seen.add(hit)
    # Uncovered points count as their own region-free bucket (one extra "unknown"
    # slot only if at least one exists) so a coverage gap can never undercount.
    return len(seen) + (1 if uncovered else 0), uncovered


def _count_places(rows):
    """All build-time Places counts, computed from start_latlng per the pinned
    analyst methods. Returns a dict of ints + the uncovered-point list."""
    pts = _start_points(rows)
    sd_n = sum(1 for lng, lat in pts if _in_box(lng, lat, _SD_BOX))
    bos_n = sum(1 for lng, lat in pts if _in_box(lng, lat, _BOS_BOX))
    regions = _count_regions(pts)
    states, uncovered = _count_states(pts)
    return {"act": len(pts), "sd": sd_n, "bos": bos_n,
            "regions": regions, "states": states, "uncovered": uncovered}


def _group(first):
    ln, la = first
    if _in_box(ln, la, _SD_BOX):
        return 0
    if _in_box(ln, la, _BOS_BOX):
        return 1
    return 2


def _compute_frame(extents):
    """Margined 'All' frame (+4% each span), edges rounded to 3 decimals; spans
    are the difference of the rounded edges (reproduces the pinned constants:
    lng0=-126.121, lngspan=58.135, lat1=49.982, latspan=18.027, ww=43.8977)."""
    lat_min, lat_max, lng_min, lng_max = extents
    lat_pad = 0.04 * (lat_max - lat_min)
    lng_pad = 0.04 * (lng_max - lng_min)
    lat0 = round(lat_min - lat_pad, 3)
    lat1 = round(lat_max + lat_pad, 3)
    lng0 = round(lng_min - lng_pad, 3)
    lng1 = round(lng_max + lng_pad, 3)
    lngspan = round(lng1 - lng0, 3)
    latspan = round(lat1 - lat0, 3)
    ww = round(lngspan * COSLAT, 4)
    wh = latspan
    return {"lng0": lng0, "lngspan": lngspan, "lat1": lat1, "latspan": latspan,
            "ww": ww, "wh": wh}


def _uv(lng, lat, fr):
    u = (lng - fr["lng0"]) / fr["lngspan"]
    v = (fr["lat1"] - lat) / fr["latspan"]
    return u, v


def _centroid(pts):
    n = len(pts)
    return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n


def _build_labels(tracks, fr, sd_n, bos_n):
    """Python-computed label anchors. Home centroids drive the coord line; the
    activity COUNTS in the sub-lines are computed at build time (sd_n/bos_n from
    start_latlng-in-box) while the era + key-trip detail copy stays hardcoded.
    Ordered by declutter priority: homes (count desc) then key trips west->east.
    A key-trip box with zero contained trips is dropped silently (asserted in the
    build print)."""
    sd_pts, bos_pts = [], []
    trip_pts = []
    for t in tracks:
        ln, la = t["first"]
        if t["g"] == 0:
            sd_pts.append((ln, la))
        elif t["g"] == 1:
            bos_pts.append((ln, la))
        else:
            trip_pts.append((ln, la))

    def trip_centroid(box):
        inside = [(ln, la) for ln, la in trip_pts if _in_box(ln, la, box)]
        return (_centroid(inside) if inside else None), len(inside)

    labels = []
    dropped = []

    # Homes (always drawn; count desc: SD 155 > Boston 137). The count portion
    # is live; only the era label is hardcoded.
    sd_sub  = "%d activities · %s" % (sd_n, _SD_ERA)
    bos_sub = "%d activities · %s" % (bos_n, _BOS_ERA)
    for name, pts, sub in (("SAN DIEGO", sd_pts, sd_sub),
                           ("BOSTON", bos_pts, bos_sub)):
        clng, clat = _centroid(pts)
        u, v = _uv(clng, clat, fr)
        coord = "%.2f°N  %.2f°W" % (clat, abs(clng))
        labels.append({"k": "home", "name": name, "coord": coord, "sub": sub,
                       "u": round(u, 4), "v": round(v, 4)})

    # Key trips, west -> east (Vancouver, Sierra, Maine).
    for name, box, detail in (("VANCOUVER", _VANCOUVER_BOX, _VANCOUVER_DETAIL),
                              ("SIERRA", _SIERRA_BOX, _SIERRA_DETAIL),
                              ("MAINE", _MAINE_BOX, _MAINE_DETAIL)):
        cen, ntrip = trip_centroid(box)
        if cen is None:
            dropped.append(name)
            continue
        clng, clat = cen
        u, v = _uv(clng, clat, fr)
        labels.append({"k": "trip", "name": name, "coord": detail, "sub": "",
                       "u": round(u, 4), "v": round(v, 4)})

    return labels, dropped


def _build_views(fr):
    """View-button framing boxes -> u/v rects for the fly-to fit math."""
    views = {}
    for key, box in (("sd", _VIEW_SD_BOX), ("bos", _VIEW_BOS_BOX)):
        lat_lo, lat_hi, lng_lo, lng_hi = box
        u0, v_north = _uv(lng_lo, lat_hi, fr)   # west edge, north edge
        u1, v_south = _uv(lng_hi, lat_lo, fr)   # east edge, south edge
        views[key] = {"u0": round(u0, 4), "u1": round(u1, 4),
                      "v0": round(v_north, 4), "v1": round(v_south, 4)}
    return views


def chart_places_hero(rows):
    """Build the Places hero: load streams, assemble the injected `PD` payload,
    and return one self-contained raw HTML string (style + canvas + chrome +
    script). `rows` supplies sport_type per activity id."""
    act_by_id = {str(r["id"]): r for r in rows}

    # Live counts (computed at build time from start_latlng per the pinned
    # analyst methods) so the fetch cron can't leave them stale.
    counts = _count_places(rows)

    tracks, extents = _load_tracks(act_by_id)
    fr = _compute_frame(extents)
    labels, dropped = _build_labels(tracks, fr, counts["sd"], counts["bos"])
    views = _build_views(fr)

    total_pts = sum(len(t["pts"]) for t in tracks)

    pd_tracks = [
        {"c": t["c"], "g": t["g"],
         "p": [v for pt in t["pts"] for v in pt]}
        for t in tracks
    ]
    PD = {
        "lng0": fr["lng0"], "lngspan": fr["lngspan"],
        "lat1": fr["lat1"], "latspan": fr["latspan"],
        "ww": fr["ww"], "wh": fr["wh"],
        "tracks": pd_tracks,
        "labels": labels,
        "views": views,
    }
    pd_json = json.dumps(PD, separators=(",", ":"), ensure_ascii=False)
    json_bytes = len(pd_json.encode("utf-8"))
    json_kb = json_bytes / 1024.0

    # ── Build console lines + soft checks (ASCII only) ────────────────────────
    print("[places] hero: tracks=%d pts=%d json_kb=~%d"
          % (len(tracks), total_pts, round(json_kb)))
    print("[places] counts: act=%d sd=%d bos=%d regions=%d states=%d"
          % (counts["act"], counts["sd"], counts["bos"],
             counts["regions"], counts["states"]))
    if counts["uncovered"]:
        print("[places] WARNING: %d start point(s) outside every state box "
              "(counted as an 'unknown' bucket): %s"
              % (len(counts["uncovered"]),
                 ", ".join("%.3f,%.3f" % (la, ln) for la, ln in counts["uncovered"])))
    # Soft drift note vs the analyst pins (never hard-assert -- data grows).
    _pinned = {"act": 319, "sd": 155, "bos": 137, "regions": 28, "states": 9}
    _diffs = ["%s %d!=%d" % (k, counts[k], _pinned[k])
              for k in ("act", "sd", "bos", "regions", "states")
              if counts[k] != _pinned[k]]
    if _diffs:
        print("[places] NOTE: count drift vs pinned (319/155/137/28/9): %s"
              % ", ".join(_diffs))
    if dropped:
        print("[places] WARNING: dropped key-trip labels (no contained tracks): %s"
              % ",".join(dropped))
    # Soft budget check: warn and continue (never break the deploy on data growth).
    if json_bytes > 0.6 * 1024 * 1024:
        print("[places] WARNING: injected JSON %.2f MB exceeds 0.6 MB budget"
              % (json_bytes / 1048576.0))
    drift = abs(total_pts - 21372) / 21372.0
    if drift > 0.05:
        print("[places] WARNING: total points %d drift %.1f%% from 21372 (>5%%)"
              % (total_pts, drift * 100))

    html = (_HERO_TEMPLATE
            .replace("__PD_JSON__", pd_json)
            .replace("__ACT__", str(counts["act"]))
            .replace("__REGIONS__", str(counts["regions"]))
            .replace("__STATES__", str(counts["states"])))
    return html


# ─── Self-contained hero HTML/CSS/JS (ported from the mock; hardenings applied) ─
# Plain string with a __PD_JSON__ token so the JS braces stay literal. The label
# strings carry unicode (deg/middot/en-dash) as injected JSON DATA -- that is
# fine; only Python print() output must be ASCII. Simpler-option note: the ground
# gradients are baked directly into the :root / :root.light selectors (rather than
# via named hero CSS custom properties) -- functionally identical theme pair, one
# fewer indirection. The mock's dark ground literals are sanctioned basemap tints.
_HERO_TEMPLATE = r"""<div class="places-hero" id="places-hero">
<style>
  #places-hero{
    position:relative; width:100%;
    overflow:hidden;
    border:1px solid var(--border-subtle);
    border-radius:16px;
    height:clamp(560px, calc(100svh - 150px), 900px);
    background:radial-gradient(120% 120% at 50% 42%, #101725 0%, #0d1117 42%, #05070a 100%);
    transition:background .6s ease;
  }
  #places-hero:fullscreen{
    width:100vw; height:100vh; max-height:none; border:none; border-radius:0;
  }
  #places-hero.terrain{
    background:radial-gradient(120% 120% at 50% 42%, #1a1512 0%, #120f11 44%, #08060a 100%);
  }
  :root.light #places-hero{
    background:radial-gradient(120% 120% at 50% 42%, var(--bg-base) 0%, var(--bg-surface) 100%);
  }
  :root.light #places-hero.terrain{
    background:radial-gradient(120% 120% at 50% 42%, var(--bg-base) 0%, var(--bg-surface) 100%);
  }
  #places-hero canvas{
    position:absolute; inset:0; width:100%; height:100%; display:block;
    cursor:grab; touch-action:pan-y;
    opacity:0; animation:places-rise 1100ms ease .12s forwards;
  }
  #places-hero canvas:active{cursor:grabbing}
  @keyframes places-rise{from{opacity:0} to{opacity:1}}
  @keyframes places-fade{from{opacity:0; transform:translateY(6px)} to{opacity:1; transform:none}}

  #places-hero .places-chrome{position:absolute; inset:0; pointer-events:none}
  #places-hero .places-chrome > *{pointer-events:auto}

  #places-hero .places-caption{
    position:absolute; top:clamp(22px,4vh,44px); left:clamp(22px,4vw,52px);
    opacity:0; animation:places-fade 800ms ease .45s forwards;
  }
  #places-hero .places-eyebrow{
    font-family:'Geist Mono',ui-monospace,monospace; font-size:11px;
    letter-spacing:.34em; text-transform:uppercase; color:var(--text-tertiary); margin:0;
  }
  #places-hero .places-controls{
    position:absolute; top:clamp(22px,4vh,44px); right:clamp(22px,4vw,52px);
    display:flex; flex-direction:column; gap:10px; align-items:flex-end;
    opacity:0; animation:places-fade 800ms ease .6s forwards;
  }
  #places-hero .places-seg{
    background:var(--bg-glass); border:1px solid var(--border);
    backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
    margin-bottom:0;
  }
  #places-hero .places-seg-lbl{
    font-family:'Geist Mono',ui-monospace,monospace; font-size:9px;
    letter-spacing:.16em; text-transform:uppercase; color:var(--text-tertiary);
    align-self:center; padding:0 8px 0 6px;
  }
  #places-hero .places-foot{
    position:absolute; left:0; right:0; bottom:0;
    padding:clamp(16px,3vh,30px) clamp(22px,4vw,52px);
    display:flex; justify-content:space-between; align-items:flex-end;
    gap:20px; flex-wrap:wrap;
    background:linear-gradient(to top, rgba(5,7,10,.82), transparent);
    opacity:0; animation:places-fade 800ms ease .75s forwards;
  }
  :root.light #places-hero .places-foot{
    background:linear-gradient(to top, rgba(255,255,255,.82), transparent);
  }
  #places-hero .places-legend{display:flex; gap:16px; flex-wrap:wrap}
  #places-hero .places-legend span{
    display:inline-flex; align-items:center; gap:7px; font-size:12px; color:var(--text-secondary);
  }
  #places-hero .places-legend .dot{width:9px; height:9px; border-radius:50%}
  #places-hero .places-stat{
    font-family:'Geist Mono',ui-monospace,monospace; font-size:12px;
    color:var(--text-secondary); letter-spacing:.02em; text-align:right;
    font-variant-numeric:tabular-nums;
  }
  #places-hero .places-stat b{color:var(--text-primary); font-weight:500}
  #places-hero .places-hint{
    position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
    font-family:'Geist Mono',ui-monospace,monospace; font-size:11px;
    color:var(--text-secondary); background:var(--bg-glass);
    border:1px solid var(--border-subtle); padding:8px 14px; border-radius:999px;
    backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
    opacity:0; pointer-events:none; transition:opacity .25s ease; white-space:nowrap;
  }
  #places-hero .places-hint.show{opacity:1}
  #places-hero .places-fs{
    display:inline-flex; align-items:center; justify-content:center;
    width:34px; height:34px; padding:0;
    background:var(--bg-glass); border:1px solid var(--border);
    border-radius:10px; color:var(--text-secondary); cursor:pointer;
    backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
    transition:color .18s, background .18s;
  }
  #places-hero .places-fs:hover{color:var(--text-primary)}
  #places-hero .places-fs:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
  #places-hero .places-fs svg{width:16px; height:16px; stroke:currentColor; fill:none;
    stroke-width:2; stroke-linecap:round; stroke-linejoin:round}
  @media (max-width:640px){
    #places-hero .places-controls{
      top:auto; bottom:96px; right:clamp(14px,4vw,52px); left:clamp(14px,4vw,52px);
      align-items:stretch;
    }
    #places-hero .places-seg{justify-content:center}
    #places-hero .places-fs{align-self:flex-end}
    #places-hero .places-foot{flex-direction:column; align-items:flex-start}
    #places-hero .places-stat{text-align:left}
  }
  @media (prefers-reduced-motion:reduce){
    #places-hero canvas, #places-hero .places-caption,
    #places-hero .places-controls, #places-hero .places-foot{
      animation:none; opacity:1; transform:none;
    }
  }
</style>

<canvas id="chart-places-hero" role="img"
  aria-label="Map of every GPS route: San Diego and Boston home clusters plus trips across North America"></canvas>

<div class="places-chrome">
  <div class="places-caption"><p class="places-eyebrow">Places</p></div>
  <div class="places-controls">
    <button class="places-fs" id="places-fs" type="button"
            aria-label="Toggle fullscreen" title="Fullscreen" aria-pressed="false">
      <svg class="fs-open" viewBox="0 0 24 24"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
      <svg class="fs-close" viewBox="0 0 24 24" style="display:none"><path d="M8 3v3a2 2 0 0 1-2 2H3M16 3v3a2 2 0 0 0 2 2h3M8 21v-3a2 2 0 0 0-2-2H3M16 21v-3a2 2 0 0 1 2-2h3"/></svg>
    </button>
    <div class="seg-filter places-seg" role="group" aria-label="View">
      <span class="places-seg-lbl">View</span>
      <button class="seg-btn active" data-frame="all"    aria-pressed="true">All</button>
      <button class="seg-btn"        data-frame="sd"     aria-pressed="false">San Diego</button>
      <button class="seg-btn"        data-frame="bos"    aria-pressed="false">Boston</button>
      <button class="seg-btn"        data-frame="trips"  aria-pressed="false">Trips</button>
    </div>
    <div class="seg-filter places-seg" role="group" aria-label="Basemap">
      <span class="places-seg-lbl">Map</span>
      <button class="seg-btn active" data-base="glow"    aria-pressed="true">Glow</button>
      <button class="seg-btn"        data-base="terrain" aria-pressed="false">Terrain</button>
    </div>
  </div>
  <div class="places-foot">
    <div class="places-legend">
      <span><i class="dot" style="background:var(--running)"></i>Running</span>
      <span><i class="dot" style="background:var(--mtb)"></i>Mountain bike</span>
      <span><i class="dot" style="background:var(--elevation)"></i>Trail / ski</span>
      <span><i class="dot" style="background:#4ade80"></i>Hike</span>
    </div>
    <div class="places-stat"><b>__ACT__</b> activities &middot; <b>__REGIONS__</b> regions &middot; <b>__STATES__</b> states &amp; provinces</div>
  </div>
  <div class="places-hint" id="places-hint"></div>
</div>

<script>
(function(){
  var PD = __PD_JSON__;
  var hero = document.getElementById('places-hero');
  var cv   = document.getElementById('chart-places-hero');
  if(!cv) return;
  var ctx  = cv.getContext('2d');
  var hint = document.getElementById('places-hint');
  var reduce = matchMedia('(prefers-reduced-motion:reduce)').matches;

  var W=0, H=0, dpr=1, S0=1;

  // Flatten track coords to Float32 u/v once at boot (float32 in 0..1 far
  // exceeds the 5-decimal source precision). HIKE bucket keeps its literal.
  var TRACKS = PD.tracks.map(function(t, i){
    var p = t.p, m = p.length/2;
    var uv = new Float32Array(p.length);
    for(var k=0;k<m;k++){
      var lng=p[2*k], lat=p[2*k+1];
      uv[2*k]   = (lng - PD.lng0)/PD.lngspan;
      uv[2*k+1] = (PD.lat1 - lat)/PD.latspan;
    }
    // deterministic organic alpha jitter (replaces the mock's rng)
    var jitter = (i*0.6180339887) % 1;
    return {c:t.c, g:t.g, uv:uv, n:m,
            base:(t.g<2 ? 0.30 : 0.50) + 0.12*jitter};
  });

  // ── Theme colors (re-read on every retint) ──────────────────────────────
  var probe = document.createElement('span');
  probe.style.display='none'; hero.appendChild(probe);
  function readVar(name){
    probe.style.color = 'var('+name+')';
    var c = getComputedStyle(probe).color; // "rgb(r, g, b)" / "rgba(...)"
    var m = c.match(/(\d+)[,\s]+(\d+)[,\s]+(\d+)/);
    return m ? [ +m[1], +m[2], +m[3] ] : [230,237,243];
  }
  function hexRGB(h){
    return [ parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16) ];
  }
  var TH = null;
  function retint(){
    var light = document.documentElement.classList.contains('light');
    TH = {
      light: light,
      route: [ readVar('--running'), readVar('--mtb'), readVar('--elevation'),
               hexRGB('#4ade80'), readVar('--other') ],
      tp: readVar('--text-primary'),
      ts: readVar('--text-secondary')
    };
  }

  // view/camera state
  var cur = {s:1, fx:0.5, fy:0.5};
  var anim = null, terrain=false, lens='none';

  function clampS(s){ return Math.min(400, Math.max(0.65, s)); }

  function resize(){
    dpr = Math.min(window.devicePixelRatio||1, 2);
    W = hero.clientWidth; H = hero.clientHeight;
    if(W===0 || H===0) return;
    S0 = Math.min(W/PD.ww, H/PD.wh);
    cv.width = W*dpr; cv.height = H*dpr;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    draw();
  }

  function projX(u){ return W/2 + (u - cur.fx)*PD.ww*S0*cur.s; }
  function projY(v){ return H/2 + (v - cur.fy)*PD.wh*S0*cur.s; }

  // ── graticule (adaptive real lat/lng lines) ─────────────────────────────
  var STEPS=[10,5,2,1,0.5,0.2,0.1,0.05];
  function drawGraticule(){
    var pxPerDeg = S0*cur.s;           // vertical px per degree latitude
    var step = STEPS[STEPS.length-1];
    for(var i=0;i<STEPS.length;i++){ if(STEPS[i]*pxPerDeg >= 72){ step=STEPS[i]; break; } }
    ctx.lineWidth=1;
    ctx.strokeStyle = TH.light ? 'rgba('+TH.ts[0]+','+TH.ts[1]+','+TH.ts[2]+',0.10)'
                     : (terrain ? 'rgba(120,96,72,.10)' : 'rgba(88,120,170,.09)');
    // visible lng range from screen edges
    var uMin = cur.fx + (0 - W/2)/(PD.ww*S0*cur.s);
    var uMax = cur.fx + (W - W/2)/(PD.ww*S0*cur.s);
    var lngMin = PD.lng0 + uMin*PD.lngspan, lngMax = PD.lng0 + uMax*PD.lngspan;
    var lo = Math.ceil(lngMin/step)*step, hi = lngMax;
    for(var g=lo; g<=hi; g+=step){
      var x = projX((g - PD.lng0)/PD.lngspan);
      ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke();
    }
    var vMin = cur.fy + (0 - H/2)/(PD.wh*S0*cur.s);
    var vMax = cur.fy + (H - H/2)/(PD.wh*S0*cur.s);
    var latMax = PD.lat1 - vMin*PD.latspan, latMin = PD.lat1 - vMax*PD.latspan;
    var loLat = Math.ceil(latMin/step)*step;
    for(var la=loLat; la<=latMax; la+=step){
      var y = projY((PD.lat1 - la)/PD.latspan);
      ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke();
    }
  }

  // terrain relief placeholder: concentric rings at the two mountain trips
  function drawContours(){
    var anchors = [];
    for(var i=0;i<PD.labels.length;i++){
      var L=PD.labels[i];
      if(L.name==='SIERRA' || L.name==='MAINE') anchors.push(L);
    }
    ctx.strokeStyle = TH.light ? 'rgba('+TH.ts[0]+','+TH.ts[1]+','+TH.ts[2]+',0.12)'
                               : 'rgba(212,160,116,.13)';
    ctx.lineWidth=1;
    var rs = Math.min(cur.s, 3);
    for(var a=0;a<anchors.length;a++){
      var cx=projX(anchors[a].u), cy=projY(anchors[a].v);
      for(var r=1;r<=5;r++){
        ctx.beginPath();
        ctx.ellipse(cx,cy, r*16*0.6*rs, r*12*0.6*rs, 0,0,6.283);
        ctx.stroke();
      }
    }
  }

  function draw(){
    if(!TH) retint();
    if(W===0) return;
    ctx.clearRect(0,0,W,H);
    if(terrain) drawContours();
    drawGraticule();

    ctx.globalCompositeOperation = TH.light ? 'multiply' : 'lighter';
    ctx.lineJoin='round'; ctx.lineCap='round';
    var lw = Math.max(0.8, 1.15*Math.min(cur.s,2));
    ctx.lineWidth = lw;
    var alphaMul = TH.light ? 0.85 : 1.0;

    for(var ti=0;ti<TRACKS.length;ti++){
      var t = TRACKS[ti], a = t.base;
      if(lens==='trips') a = (t.g<2) ? a*0.20 : Math.min(0.92, a*1.55);
      a *= alphaMul;
      var col = TH.route[t.c];
      ctx.strokeStyle = 'rgba('+col[0]+','+col[1]+','+col[2]+','+a+')';
      ctx.beginPath();
      var uv=t.uv;
      for(var k=0;k<t.n;k++){
        var x=projX(uv[2*k]), y=projY(uv[2*k+1]);
        if(k) ctx.lineTo(x,y); else ctx.moveTo(x,y);
      }
      ctx.stroke();
    }
    ctx.globalCompositeOperation='source-over';
    drawLabels();
  }

  // ── labels + declutter ──────────────────────────────────────────────────
  function rectsOverlap(a,b){
    return !(a.x2 < b.x1 || b.x2 < a.x1 || a.y2 < b.y1 || b.y2 < a.y1);
  }
  function drawLabels(){
    var placed=[];
    for(var i=0;i<PD.labels.length;i++){
      var L=PD.labels[i];
      var x=projX(L.u), y=projY(L.v);
      if(x<-40||x>W+40||y<-40||y>H+40) continue;   // cull offscreen anchors
      var home = (L.k==='home');
      // alpha per lens state
      var alpha;
      if(home) alpha = (lens==='trips') ? 0.34 : 1.0;
      else     alpha = (lens==='trips') ? 0.9  : 0.8;

      // measure block
      ctx.font='600 '+(home?13:11)+"px 'Geist', ui-sans-serif, sans-serif";
      var w = ctx.measureText(L.name).width;
      ctx.font="11px 'Geist Mono', ui-monospace, monospace";
      if(L.coord) w=Math.max(w, ctx.measureText(L.coord).width);
      if(L.sub)   w=Math.max(w, ctx.measureText(L.sub).width);
      var lines = 1 + (L.coord?1:0) + (L.sub?1:0);
      var by = Math.max(26, Math.min(H-70, y));   // clamp text baseline (vertical)
      // Horizontal edge-guard (mirror of the vertical clamp): draw rightward from
      // the dot by default, but if the measured text block would spill past the
      // right edge, flip it to render leftward (right-aligned). West edge handled
      // symmetrically. The whole multi-line block moves as a unit; the anchor dot
      // stays at its true position. gap = dot->text offset (10), pad = edge inset.
      var GAP=10, PAD=8;
      var dir=1;                                   // +1 = text right of dot
      if(x + GAP + w + PAD > W) dir=-1;            // spills east -> flip west
      if(dir<0 && x - GAP - w - PAD < 0) dir=1;    // would also spill west -> keep east
      var rect = (dir>0)
        ? {x1:x, y1:by-14, x2:x+2+GAP+w, y2:by-14+8+lines*15}
        : {x1:x-GAP-w, y1:by-14, x2:x+2, y2:by-14+8+lines*15};

      if(!home){
        var hit=false;
        for(var p=0;p<placed.length;p++){ if(rectsOverlap(rect, placed[p])){ hit=true; break; } }
        if(hit) continue;
      }
      placed.push(rect);
      drawLabel(L, x, y, by, home, alpha, dir, w);
    }
  }
  function drawLabel(L, x, y, by, home, alpha, dir, w){
    var tp=TH.tp, ts=TH.ts;
    // dir<0 -> text block sits left of the dot (right-aligned so its far edge
    // hugs the dot); dir>0 -> classic left-aligned block to the right of the dot.
    var GAP=10;
    ctx.textAlign = (dir<0) ? 'right' : 'left';
    var tx = x + dir*GAP;
    ctx.shadowColor = TH.light ? 'rgba(255,255,255,.85)' : 'rgba(0,0,0,.85)';
    ctx.shadowBlur = 8;
    // anchor dot at true anchor
    ctx.beginPath(); ctx.arc(x, y, home?3:2.2, 0, 6.283);
    var dot = home?tp:ts;
    ctx.fillStyle='rgba('+dot[0]+','+dot[1]+','+dot[2]+','+alpha+')'; ctx.fill();
    // name
    ctx.font='600 '+(home?13:11)+"px 'Geist', ui-sans-serif, sans-serif";
    var nm = home?tp:ts;
    ctx.fillStyle='rgba('+nm[0]+','+nm[1]+','+nm[2]+','+alpha+')';
    ctx.fillText(L.name, tx, by+4);
    ctx.font="11px 'Geist Mono', ui-monospace, monospace";
    if(L.coord){
      ctx.fillStyle='rgba('+ts[0]+','+ts[1]+','+ts[2]+','+(alpha*0.85)+')';
      ctx.fillText(L.coord, tx, by+20);
    }
    if(L.sub){
      ctx.fillStyle='rgba('+ts[0]+','+ts[1]+','+ts[2]+','+(alpha*0.9)+')';
      ctx.fillText(L.sub, tx, by+35);
    }
    ctx.shadowBlur=0;
  }

  // ── tween (geometric log-s, linear fx/fy) ───────────────────────────────
  function tweenTo(v, newLens){
    lens = (newLens===undefined) ? lens : newLens;
    if(reduce){ cur={s:v.s, fx:v.fx, fy:v.fy}; draw(); return; }
    var from={s:cur.s, fx:cur.fx, fy:cur.fy}, t0=performance.now(), dur=620;
    cancelAnimationFrame(anim);
    (function frame(now){
      var k=Math.min(1,(now-t0)/dur), e=1-Math.pow(1-k,3);
      cur.s  = from.s * Math.pow(v.s/from.s, e);
      cur.fx = from.fx + (v.fx-from.fx)*e;
      cur.fy = from.fy + (v.fy-from.fy)*e;
      draw();
      if(k<1) anim=requestAnimationFrame(frame);
    })(t0);
  }

  function fitBox(u0,u1,v0,v1){
    var s = 0.94 * Math.min( W/((u1-u0)*PD.ww*S0), H/((v1-v0)*PD.wh*S0) );
    return {s:clampS(s), fx:(u0+u1)/2, fy:(v0+v1)/2};
  }
  function frameTarget(name){
    if(name==='all' || name==='trips') return {s:1, fx:0.5, fy:0.5};
    var vw = PD.views[name];
    return fitBox(vw.u0, vw.u1, vw.v0, vw.v1);
  }

  // Public fly-to hook (Pass C dependency).
  window.placesFlyTo = function(target){
    var name=null, tgt;
    if(typeof target==='string'){
      name=target;
      tgt = frameTarget(target);
      tweenTo(tgt, target==='trips' ? 'trips' : 'none');
    } else if(target && typeof target==='object'){
      var u0=(target.lng0-PD.lng0)/PD.lngspan, u1=(target.lng1-PD.lng0)/PD.lngspan;
      var v0=(PD.lat1-target.lat1)/PD.latspan, v1=(PD.lat1-target.lat0)/PD.latspan;
      tweenTo(fitBox(u0,u1,v0,v1), 'none');
    }
    // deactivate frame buttons unless the name matches
    hero.querySelectorAll('[data-frame]').forEach(function(b){
      var on = (b.dataset.frame===name);
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on?'true':'false');
    });
  };

  // ── controls ────────────────────────────────────────────────────────────
  hero.querySelectorAll('[data-frame]').forEach(function(b){
    b.addEventListener('click', function(){
      hero.querySelectorAll('[data-frame]').forEach(function(o){
        var on=(o===b); o.classList.toggle('active', on);
        o.setAttribute('aria-pressed', on?'true':'false');
      });
      var v=b.dataset.frame;
      tweenTo(frameTarget(v), v==='trips' ? 'trips' : 'none');
    });
  });
  hero.querySelectorAll('[data-base]').forEach(function(b){
    b.addEventListener('click', function(){
      hero.querySelectorAll('[data-base]').forEach(function(o){
        var on=(o===b); o.classList.toggle('active', on);
        o.setAttribute('aria-pressed', on?'true':'false');
      });
      terrain = b.dataset.base==='terrain';
      hero.classList.toggle('terrain', terrain);
      draw();
    });
  });

  // ── fullscreen toggle (feature-detected) ────────────────────────────────
  var fsBtn = document.getElementById('places-fs');
  var fsSupported = !!(hero.requestFullscreen);
  if(fsBtn){
    if(!fsSupported){
      fsBtn.style.display='none';   // e.g. iOS Safari on non-video elements
    } else {
      fsBtn.addEventListener('click', function(){
        if(!document.fullscreenElement){ hero.requestFullscreen(); }
        else { document.exitFullscreen(); }
      });
      document.addEventListener('fullscreenchange', function(){
        var on = (document.fullscreenElement===hero);
        var open=fsBtn.querySelector('.fs-open'), close=fsBtn.querySelector('.fs-close');
        if(open)  open.style.display  = on ? 'none' : '';
        if(close) close.style.display = on ? '' : 'none';
        fsBtn.setAttribute('aria-pressed', on?'true':'false');
        resize();   // belt-and-suspenders with the ResizeObserver
      });
    }
  }

  // ── hint pill ───────────────────────────────────────────────────────────
  var hintT=null;
  function showHint(msg){
    if(!hint) return;
    hint.textContent=msg; hint.classList.add('show');
    clearTimeout(hintT);
    hintT=setTimeout(function(){ hint.classList.remove('show'); }, 1200);
  }

  function zoomAt(mx,my,factor){
    var wx=cur.fx+(mx-W/2)/(PD.ww*S0*cur.s);
    var wy=cur.fy+(my-H/2)/(PD.wh*S0*cur.s);
    cur.s=clampS(cur.s*factor);
    cur.fx=wx-(mx-W/2)/(PD.ww*S0*cur.s);
    cur.fy=wy-(my-H/2)/(PD.wh*S0*cur.s);
    draw();
  }

  // ── cooperative gestures ────────────────────────────────────────────────
  var pointers=new Map(), mouseDrag=false, lx=0, ly=0, lastDist=0, lastCx=0, lastCy=0;
  function localXY(e){ var r=cv.getBoundingClientRect(); return [e.clientX-r.left, e.clientY-r.top]; }

  cv.addEventListener('pointerdown', function(e){
    pointers.set(e.pointerId, {x:e.clientX, y:e.clientY});
    cancelAnimationFrame(anim);
    if(e.pointerType==='mouse'){ mouseDrag=true; lx=e.clientX; ly=e.clientY; cv.setPointerCapture(e.pointerId); }
    else if(pointers.size===2){
      var pts=[...pointers.values()];
      lastDist=Math.hypot(pts[0].x-pts[1].x, pts[0].y-pts[1].y);
      lastCx=(pts[0].x+pts[1].x)/2; lastCy=(pts[0].y+pts[1].y)/2;
    }
  });
  cv.addEventListener('pointermove', function(e){
    if(e.pointerType==='mouse'){
      if(!mouseDrag) return;
      cur.fx -= (e.clientX-lx)/(PD.ww*S0*cur.s);
      cur.fy -= (e.clientY-ly)/(PD.wh*S0*cur.s);
      lx=e.clientX; ly=e.clientY; draw(); return;
    }
    // touch
    if(!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, {x:e.clientX, y:e.clientY});
    if(pointers.size>=2){
      e.preventDefault();
      var pts=[...pointers.values()];
      var dist=Math.hypot(pts[0].x-pts[1].x, pts[0].y-pts[1].y);
      var cxp=(pts[0].x+pts[1].x)/2, cyp=(pts[0].y+pts[1].y)/2;
      // pan by centroid delta
      cur.fx -= (cxp-lastCx)/(PD.ww*S0*cur.s);
      cur.fy -= (cyp-lastCy)/(PD.wh*S0*cur.s);
      // zoom by pinch ratio, anchored at centroid
      if(lastDist>0){
        var r=cv.getBoundingClientRect();
        zoomAt(cxp-r.left, cyp-r.top, dist/lastDist);
      }
      lastDist=dist; lastCx=cxp; lastCy=cyp;
      draw();
    } else {
      // one-finger horizontal intent -> hint (page still scrolls via pan-y)
      var d0=pointers.get(e.pointerId);
      showHint('Use two fingers to move the map');
    }
  });
  function endPointer(e){
    pointers.delete(e.pointerId);
    if(e.pointerType==='mouse') mouseDrag=false;
    if(pointers.size<2) lastDist=0;
  }
  cv.addEventListener('pointerup', endPointer);
  cv.addEventListener('pointercancel', endPointer);

  cv.addEventListener('wheel', function(e){
    if(e.ctrlKey || e.metaKey){          // trackpad pinch arrives as ctrlKey wheel
      e.preventDefault();
      cancelAnimationFrame(anim);
      var xy=localXY(e);
      zoomAt(xy[0], xy[1], Math.exp(-e.deltaY*0.0012));
    } else {
      showHint('Ctrl + scroll to zoom');   // no preventDefault -> page scrolls
    }
  }, {passive:false});

  cv.addEventListener('dblclick', function(e){
    e.preventDefault();
    cancelAnimationFrame(anim);
    var xy=localXY(e);
    zoomAt(xy[0], xy[1], 1.8);
  });

  // ── lifecycle ───────────────────────────────────────────────────────────
  window.__placesHeroRedraw = function(){ retint(); resize(); };
  if(window.ResizeObserver){
    var ro=new ResizeObserver(function(){ resize(); });
    ro.observe(hero);
  }
  window.addEventListener('resize', resize);
  retint();
  resize();
})();
</script>
</div>"""
