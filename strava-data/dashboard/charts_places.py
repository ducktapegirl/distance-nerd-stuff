"""Places hero: a bespoke <canvas> route-density map (additive glow), ported
from Project Docs/Specs/strava-data/mocks/places-hero-mock.html with real GPS streams injected as
JSON. Returns one self-contained raw HTML string (the chart_calendar() raw-string
precedent) -- NOT a Plotly figure. All heavy Places code lives here, not in
charts_production.py. Imports are stdlib + numpy only (no pandas)."""

import datetime as _dt
import json
import math
import os
from collections import Counter

import numpy as np

from .config import KM_TO_MI, MAPTILER_KEY, STREAMS_DIR
from .data import load_segment_efforts, load_segments, mf

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


# Process-level cache so the 344-file stream parse happens exactly ONCE per build,
# shared by chart_places_hero and chart_places_homes.
_TRACKS_CACHE = None


def _places_tracks(rows):
    """Memoized _load_tracks: parse/decimate/classify every stream once, cache
    (tracks, extents) for the process."""
    global _TRACKS_CACHE
    if _TRACKS_CACHE is None:
        act_by_id = {str(r["id"]): r for r in rows}
        _TRACKS_CACHE = _load_tracks(act_by_id)
    return _TRACKS_CACHE


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
        # Homes show only name + activity/era sub-line; the raw lat/lng coord
        # line is reserved for the trip "destinations".
        labels.append({"k": "home", "name": name, "coord": "", "sub": sub,
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
    # Live counts (computed at build time from start_latlng per the pinned
    # analyst methods) so the fetch cron can't leave them stale.
    counts = _count_places(rows)

    tracks, extents = _places_tracks(rows)   # shared parse (see _places_tracks)
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

    # The Street/Terrain basemap now comes from MapLibre + MapTiler tiles at
    # runtime, so the old inlined vector coastline / hillshade PNG are no longer
    # injected (the "Glow" mode is the tile-free dark ground). The MapTiler key is
    # spliced in here from the build environment; empty -> Glow-only fallback.
    print("[places] basemap: maplibre tiles, maptiler_key=%s"
          % ("set" if MAPTILER_KEY else "MISSING (glow-only)"))

    html = (_HERO_TEMPLATE
            .replace("__PD_JSON__", pd_json)
            .replace("__MAPTILER_KEY__", MAPTILER_KEY)
            .replace("__ACT__", str(counts["act"]))
            .replace("__REGIONS__", str(counts["regions"]))
            .replace("__STATES__", str(counts["states"])))
    return html


# ─── Pass B: Two Homes cards ────────────────────────────────────────────────────

# Home-era labels (the "moved away" narrative, hardcoded per home; en-dash) --
# NOT literal min/max years (Boston has 2026 return-visits that would muddy it).
_HOME_ERA = {"sd": "2025–now", "bos": "2024–2025"}
# Home boxes reused for the live start_latlng-in-box stats (Pass-A 155/137 defn).
_HOME_BOX = {"sd": _SD_BOX, "bos": _BOS_BOX}
# Pinned stat targets for the soft drift NOTE (never hard-assert).
_HOME_PINNED = {"sd": {"mi": 782, "seg": "Canyon entrance via Salix"},
                "bos": {"mi": 530, "seg": "Cataldo East"}}


def _metro_frame(la0, la1, ln0, ln1, margin=0.06):
    """Per-metro thumbnail frame: drawn-track extent + `margin` each span, then
    the hero's projection (ww = lngspan*COSLAT, wh = latspan)."""
    ml = margin * (la1 - la0)
    mn = margin * (ln1 - ln0)
    LAT0, LAT1 = la0 - ml, la1 + ml
    LNG0, LNG1 = ln0 - mn, ln1 + mn
    lngspan, latspan = LNG1 - LNG0, LAT1 - LAT0
    return {"lng0": LNG0, "lngspan": lngspan, "lat1": LAT1, "latspan": latspan,
            "ww": lngspan * COSLAT, "wh": latspan}


def _home_stats(rows):
    """Live per-home stats by start_latlng-in-box: miles (sum distance_km * mi),
    and the most-repeated Strava segment (Counter over segment_efforts joined to
    each activity's home box). Returns {'sd':{mi,seg,segN}, 'bos':{...}}."""
    home_of_act = {}
    km = {"sd": 0.0, "bos": 0.0}
    for r in rows:
        ll = (r.get("start_latlng") or "").strip()
        home = None
        if ll:
            parts = ll.split(",")
            if len(parts) == 2:
                lat = mf(parts[0].strip())
                lng = mf(parts[1].strip())
                if lat is not None and lng is not None:
                    if _in_box(lng, lat, _SD_BOX):
                        home = "sd"
                    elif _in_box(lng, lat, _BOS_BOX):
                        home = "bos"
        home_of_act[str(r["id"])] = home
        if home:
            km[home] += mf(r.get("distance_km")) or 0

    # segment_name fallback via segments_summary.csv (efforts usually carry it).
    summary_name = {}
    try:
        for s in load_segments():
            summary_name[str(s.get("segment_id"))] = s.get("segment_name") or ""
    except Exception:
        pass

    cnt = {"sd": Counter(), "bos": Counter()}
    eff_name = {}
    for e in load_segment_efforts():
        home = home_of_act.get(str(e.get("activity_id")))
        if not home:                      # activity not in either home box -> skip
            continue
        sid = str(e.get("segment_id") or "")
        if not sid:
            continue
        cnt[home][sid] += 1
        nm = (e.get("segment_name") or "").strip()
        if nm:
            eff_name[sid] = nm

    out = {}
    for h in ("sd", "bos"):
        mi = round(km[h] * KM_TO_MI)
        top = cnt[h].most_common(1)
        if top:
            sid, n = top[0]
            seg = eff_name.get(sid) or summary_name.get(sid) or "(unknown segment)"
        else:
            seg, n = "(none)", 0
        out[h] = {"mi": mi, "seg": seg, "segN": n}
    return out


def _home_thumb_tracks(tracks, group):
    """Filter decimated tracks to one home (by group g) and frame on the DENSE
    CORE, not the full extent: the per-axis p1..p99 box (drops sparse outlier
    tails -- SD's northern tail, outlying day-trips) + 3% margin. Points outside
    the core box are dropped (tracks split into sub-polylines at gaps so no
    spurious connector lines), and the renderer uses a COVER fit so the core fills
    the thumbnail edge-to-edge. Returns (frame, thumb_tracks, n_drawn_points)."""
    home_tracks = [t for t in tracks if t["g"] == group]
    lats = np.array([la for t in home_tracks for _, la in t["pts"]], dtype=float)
    lngs = np.array([ln for t in home_tracks for ln, _ in t["pts"]], dtype=float)
    if lats.size == 0:
        # Defensive: a future data refresh could empty a home box. Degrade to a
        # blank thumbnail (unit frame, no tracks) instead of nan from percentile.
        fr = {"lng0": 0.0, "lngspan": 1.0, "lat1": 1.0, "latspan": 1.0,
              "ww": round(COSLAT, 5), "wh": 1.0}
        return fr, [], 0, 0.5, 0.5
    la0, la1 = (float(x) for x in np.percentile(lats, [1, 99]))
    ln0, ln1 = (float(x) for x in np.percentile(lngs, [1, 99]))
    fr = _metro_frame(la0, la1, ln0, ln1, margin=0.03)
    # Density center = per-axis median (robust to the sparse tails). Cover-fit
    # centers on THIS instead of the box midpoint, so each metro's dense mass
    # lands in the middle of the thumbnail (SD rises off the bottom; Boston
    # leaves the upper-right corner).
    cu, cv = _uv(float(np.median(lngs)), float(np.median(lats)), fr)

    def _in_core(ln, la):
        return la0 <= la <= la1 and ln0 <= ln <= ln1

    out = []
    n_pts = 0
    for t in home_tracks:
        run = []   # consecutive in-core points -> one sub-polyline

        def _flush():
            nonlocal n_pts
            if len(run) >= 2:
                flat = []
                for ln, la in run:
                    u, v = _uv(ln, la, fr)
                    flat.append(round(u, 4))
                    flat.append(round(v, 4))
                out.append({"c": t["c"], "p": flat})
                n_pts += len(run)

        for ln, la in t["pts"]:
            if _in_core(ln, la):
                run.append((ln, la))
            else:
                _flush()
                run = []
        _flush()

    fr_round = {k: round(val, 5) for k, val in fr.items()}
    return fr_round, out, n_pts, round(cu, 4), round(cv, 4)


def _ascii(s):
    """ASCII-safe rendering of a (possibly unicode) segment name for prints."""
    return s.encode("ascii", "replace").decode("ascii")


def chart_places_homes(rows):
    """Build the two-homes cards (San Diego / Boston) that sit below the hero in
    view-places. Returns one self-contained raw HTML string. Reuses the shared
    decimated tracks; stats are computed live at build time."""
    tracks, _extents = _places_tracks(rows)   # shared parse (no second file walk)
    stats = _home_stats(rows)

    PH = {}
    thumb_pts = {}
    thumb_ctr = {}
    for home, group in (("sd", 0), ("bos", 1)):
        fr, thumb, n_pts, cx, cy = _home_thumb_tracks(tracks, group)
        thumb_pts[home] = n_pts
        thumb_ctr[home] = (cx, cy)
        # PH carries ONLY the fields the thumbnail JS reads (fr/cx/cy/tracks).
        # The display fields (mi/seg/segN/era) are rendered server-side into the
        # card HTML via _HOME_CARD.format (seg is _html_escape'd there) -- keeping
        # the third-party segment_name out of the raw-spliced <script> JSON, which
        # json.dumps would NOT HTML-escape (stored-XSS surface).
        PH[home] = {"fr": fr, "cx": cx, "cy": cy, "tracks": thumb}

    ph_json = json.dumps(PH, separators=(",", ":"), ensure_ascii=False)

    # ── Build print + soft drift NOTE (ASCII only) ────────────────────────────
    # Display stats live in `stats`/_HOME_ERA (server-side rendered), NOT in PH.
    print('[places] homes: sd_mi=%d sd_seg="%s"x%d bos_mi=%d bos_seg="%s"x%d'
          % (stats["sd"]["mi"], _ascii(stats["sd"]["seg"]), stats["sd"]["segN"],
             stats["bos"]["mi"], _ascii(stats["bos"]["seg"]), stats["bos"]["segN"]))
    print("[places] homes thumb: sd_pts=%d bos_pts=%d "
          "sd_ctr=(%.3f,%.3f) bos_ctr=(%.3f,%.3f) (p1..p99 core, median-centered cover)"
          % (thumb_pts["sd"], thumb_pts["bos"],
             thumb_ctr["sd"][0], thumb_ctr["sd"][1],
             thumb_ctr["bos"][0], thumb_ctr["bos"][1]))
    notes = []
    for home in ("sd", "bos"):
        pin = _HOME_PINNED[home]
        if abs(stats[home]["mi"] - pin["mi"]) > 8:
            notes.append("%s mi=%d (pinned %d)" % (home, stats[home]["mi"], pin["mi"]))
        if stats[home]["seg"] != pin["seg"]:
            notes.append('%s seg="%s" (pinned "%s")'
                         % (home, _ascii(stats[home]["seg"]), pin["seg"]))
    if notes:
        print("[places] NOTE: homes drift vs pinned: %s" % "; ".join(notes))

    def _card(home, name, cid):
        st = stats[home]
        return _HOME_CARD.format(
            cid=cid, name=name, mi=st["mi"],
            seg=_html_escape(st["seg"]), segN=st["segN"],
            era=_html_escape(_HOME_ERA[home]))

    cards = (_card("sd", "San Diego", "chart-places-home-sd")
             + _card("bos", "Boston", "chart-places-home-bos"))
    return (_HOMES_TEMPLATE
            .replace("__CARDS__", cards)
            .replace("__PH_JSON__", ph_json))


def _html_escape(s):
    # Escapes text AND attribute contexts: the Pass C passport/peaks place
    # third-party activity TITLES inside aria-label="..." attributes, so quotes
    # must be escaped too or a title with a `"` injects attributes (XSS).
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


# Card markup (one per home). En-dash / times / middot are HTML entities.
_HOME_CARD = """  <div class="places-home">
    <canvas class="places-home-map" id="{cid}" role="img" aria-label="{name} route heatmap"></canvas>
    <div class="places-home-body">
      <div class="places-home-name">{name}</div>
      <div class="places-home-stats">
        <div class="phs-mi"><b>{mi}</b> mi</div>
        <div class="phs-seg"><span class="phs-ovl">Most-repeated segment</span>{seg} &middot; {segN}&times;</div>
        <div class="phs-era">{era}</div>
      </div>
    </div>
  </div>
"""


# ─── Self-contained homes HTML/CSS/JS (dark-committed thumbnails) ───────────────
# Plain string with __CARDS__ / __PH_JSON__ tokens (JS braces stay literal). The
# thumbnails are dark-committed in BOTH page themes (fixed dark ground + additive
# glow + fixed dark sport hexes) -- no CSS-var reads, no __placesHeroRedraw hook.
_HOMES_TEMPLATE = r"""<div class="places-homes">
<style>
  .places-homes{display:flex; gap:16px; margin-top:16px;}
  .places-homes .places-home{
    flex:1 1 0; min-width:0;
    background:var(--bg-glass); border:1px solid var(--border);
    border-radius:16px; overflow:hidden;
  }
  .places-homes .places-home-map{
    display:block; width:100%; height:200px;
    background:radial-gradient(120% 120% at 50% 45%, #101725 0%, #0d1117 55%, #05070a 100%);
  }
  :root.light .places-homes .places-home-map{
    background:radial-gradient(120% 120% at 50% 45%, #eef1f4 0%, #e9edf2 55%, #e2e7ed 100%);
  }
  .places-homes .places-home-body{padding:14px 16px 16px;}
  .places-homes .places-home-name{
    font-family:'Geist', ui-sans-serif, sans-serif;
    font-size:15px; font-weight:600; color:var(--text-primary); margin-bottom:8px;
  }
  .places-homes .places-home-stats{
    font-family:'Geist Mono', ui-monospace, monospace; font-size:12.5px;
    color:var(--text-secondary); display:flex; flex-direction:column; gap:4px;
    font-variant-numeric:tabular-nums;
  }
  .places-homes .phs-mi b{color:var(--text-primary); font-weight:600;}
  .places-homes .phs-seg{overflow-wrap:anywhere;}
  .places-homes .phs-ovl{
    display:block; font-size:9.5px; letter-spacing:.14em; text-transform:uppercase;
    color:var(--text-tertiary); margin-bottom:2px;
  }
  .places-homes .phs-era{color:var(--text-tertiary);}
  @media (max-width:640px){
    .places-homes{flex-direction:column;}
    /* In the stacked column, flex:1 1 0 would collapse each card's HEIGHT to ~0
       (basis 0 + grow in an auto-height container). Revert to content height. */
    .places-homes .places-home{flex:0 0 auto;}
    .places-homes .places-home-map{height:170px;}
  }
</style>
__CARDS__
<script>
(function(){
  var PH = __PH_JSON__;
  var HEX = ["#2dd4bf","#f59e0b","#a78bfa","#4ade80","#8b949e"];
  function hexA(h,a){
    var r=parseInt(h.slice(1,3),16), g=parseInt(h.slice(3,5),16), b=parseInt(h.slice(5,7),16);
    return 'rgba('+r+','+g+','+b+','+a+')';
  }
  function draw(cv, home){
    var d = PH[home]; if(!cv || !d) return;
    var ctx = cv.getContext('2d');
    var dpr = Math.min(window.devicePixelRatio||1, 2);
    var W = cv.clientWidth, H = cv.clientHeight;
    if(W===0 || H===0) return;
    cv.width = W*dpr; cv.height = H*dpr;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    var fr = d.fr, S0 = Math.max(W/fr.ww, H/fr.wh);   // COVER fit: core fills the thumbnail
    // Center on the density median (fallback to box midpoint) so the dense mass
    // sits in the middle of the thumbnail rather than a corner/edge.
    var fx = (d.cx != null) ? d.cx : 0.5, fy = (d.cy != null) ? d.cy : 0.5;
    ctx.clearRect(0,0,W,H);
    // Theme-aware ground (CSS handles the radial-gradient swap): additive glow
    // reads on the dark ground, but the same 'lighter' math clips straight to
    // white on the light ground -- switch to 'multiply' there (ink on paper),
    // matching the hero's light-mode treatment.
    var light = document.documentElement.classList.contains('light');
    ctx.globalCompositeOperation = light ? 'multiply' : 'lighter';
    ctx.lineJoin='round'; ctx.lineCap='round';
    ctx.lineWidth = Math.max(0.8, 1.0);
    var tks = d.tracks;
    for(var i=0;i<tks.length;i++){
      var t = tks[i], p = t.p, m = p.length/2;
      var jitter = (i*0.6180339887) % 1;
      var a = 0.34 + 0.12*jitter;
      ctx.strokeStyle = hexA(HEX[t.c] || HEX[4], light ? a*0.85 : a);
      ctx.beginPath();
      for(var k=0;k<m;k++){
        var x = W/2 + (p[2*k]   - fx)*fr.ww*S0;
        var y = H/2 + (p[2*k+1] - fy)*fr.wh*S0;
        if(k) ctx.lineTo(x,y); else ctx.moveTo(x,y);
      }
      ctx.stroke();
    }
    ctx.globalCompositeOperation = 'source-over';
  }
  var renders = [];
  [['sd','chart-places-home-sd'],['bos','chart-places-home-bos']].forEach(function(pair){
    var cv = document.getElementById(pair[1]);
    if(!cv) return;
    var render = function(){ draw(cv, pair[0]); };
    renders.push(render);
    // Cards start in a hidden tab -> observe each canvas so first layout draws.
    if(window.ResizeObserver){ new ResizeObserver(render).observe(cv); }
    window.addEventListener('resize', render);
    render();
  });
  // Redraw when the page theme toggles (the .light class on <html>), same as
  // the passport thumbnails, so the glow composite mode re-picks per theme.
  if(window.MutationObserver){
    new MutationObserver(function(){ renders.forEach(function(r){ r(); }); })
      .observe(document.documentElement, {attributes:true, attributeFilter:['class']});
  }
})();
</script>
</div>"""


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
  /* MapLibre paints its tiled basemap here; transparent so the hero's radial
     gradient shows through in Glow mode (Street/Terrain tiles cover it). */
  #places-hero #places-map{
    position:absolute; inset:0; width:100%; height:100%; display:block;
    background:transparent; z-index:0;   /* stacking context: map + its controls stay below */
  }
  #places-hero .maplibregl-canvas{ background:transparent; }
  /* The route glow is a 2D canvas overlay on top of the map. pointer-events:none
     lets pan/zoom/click reach the MapLibre canvas underneath. */
  #chart-places-hero{
    position:absolute; inset:0; width:100%; height:100%; display:block;
    pointer-events:none; z-index:1;
    opacity:0; animation:places-rise 1100ms ease .12s forwards;
  }
  /* Lift MapLibre's attribution + cooperative-gesture chrome clear of the footer,
     and tint the attribution glass to match the dark theme. */
  #places-hero .maplibregl-ctrl-bottom-right{ margin-bottom:clamp(58px,11vh,104px); }
  #places-hero .maplibregl-ctrl-attrib{
    background:var(--bg-glass); backdrop-filter:blur(6px);
    -webkit-backdrop-filter:blur(6px);
  }
  #places-hero .maplibregl-ctrl-attrib,
  #places-hero .maplibregl-ctrl-attrib a{ color:var(--text-tertiary); }
  #places-hero .seg-btn:disabled{ opacity:.4; cursor:default; }
  /* 3D Terrain only makes sense for a single deep-linked activity -- hidden
     rather than disabled outside that view (see curActivity in the script). */
  #places-hero .seg-btn.hero-hidden{ display:none; }
  @keyframes places-rise{from{opacity:0} to{opacity:1}}
  @keyframes places-fade{from{opacity:0; transform:translateY(6px)} to{opacity:1; transform:none}}

  #places-hero .places-chrome{position:absolute; inset:0; pointer-events:none; z-index:2}
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

  /* Explicit zoom/pan-reset controls. Desktop: bottom-right, clear of the
     mid-height Boston label and above the footer. Mobile: the top-right
     corner is vacated once .places-controls relocates to the bottom (below),
     so the zoom cluster moves there instead of fighting the bottom row. */
  #places-hero .places-zoom{
    position:absolute; right:clamp(22px,4vw,52px); bottom:clamp(96px,17vh,140px);
    display:flex; flex-direction:column; align-items:center; gap:10px;
    opacity:0; animation:places-fade 800ms ease .6s forwards;
  }
  #places-hero .places-zoom-pair{
    display:flex; flex-direction:column;
    background:var(--bg-glass); border:1px solid var(--border);
    border-radius:11px; overflow:hidden;
    backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
  }
  #places-hero .places-zoom-btn{
    display:inline-flex; align-items:center; justify-content:center;
    width:36px; height:36px; padding:0; background:transparent; border:none;
    color:var(--text-secondary); cursor:pointer;
    transition:color .18s, background .18s;
  }
  #places-hero .places-zoom-pair .places-zoom-btn:first-child{
    border-bottom:1px solid var(--border-subtle);
  }
  #places-hero .places-zoom-btn:hover{color:var(--text-primary); background:rgba(255,255,255,.06)}
  :root.light #places-hero .places-zoom-btn:hover{background:rgba(20,24,31,.05)}
  #places-hero .places-zoom-btn:focus-visible{outline:2px solid var(--accent); outline-offset:-2px}
  #places-hero .places-zoom-btn:disabled{opacity:.35; cursor:default}
  #places-hero .places-zoom-btn:disabled:hover{color:var(--text-secondary); background:transparent}
  #places-hero .places-zoom-btn svg{width:16px; height:16px; stroke:currentColor; fill:none;
    stroke-width:2; stroke-linecap:round; stroke-linejoin:round}
  @media (max-width:640px){
    #places-hero .places-controls{
      /* Pre-existing overlap (found during zoom-control QA, unrelated to it):
         the stacked mobile .places-foot (legend + stat, each wrapping to 2
         lines at narrow widths) ran taller than the old 96px clearance and
         collided with the Map row on every phone size tested (390/430/360/
         320 CSS px). Verified via canvas pixel-scan (the on-canvas home
         labels are data-driven, not a CSS box, so a purely-visual check is
         required): 116px + the footer shrink below clears the Map-row/
         legend overlap on ALL sizes tested. On the two narrowest (<=360px)
         it can still nudge the on-canvas label band -- a second, deeper
         pre-existing crowding issue on legacy-width phones that predates
         this fix too (confirmed via the same pixel-scan against the old
         96px baseline); left as a follow-up rather than a full mobile-chrome
         rework bundled into a zoom-controls change. */
      top:auto; bottom:116px;
      right:clamp(14px,4vw,52px); left:clamp(14px,4vw,52px);
      align-items:stretch;
    }
    #places-hero .places-seg{justify-content:center}
    #places-hero .places-fs{align-self:flex-end}
    #places-hero .places-foot{
      flex-direction:column; align-items:flex-start;
      gap:8px; padding-top:clamp(10px,2vh,18px); padding-bottom:clamp(10px,2vh,18px);
    }
    #places-hero .places-legend{gap:6px 14px}
    #places-hero .places-stat{text-align:left; line-height:1.35}
    #places-hero .places-zoom{
      top:clamp(22px,4vh,44px); right:clamp(14px,4vw,52px); bottom:auto;
    }
  }
  @media (prefers-reduced-motion:reduce){
    #chart-places-hero, #places-hero .places-caption,
    #places-hero .places-controls, #places-hero .places-foot, #places-hero .places-zoom{
      animation:none; opacity:1; transform:none;
    }
  }
</style>

<div id="places-map" aria-hidden="true"></div>
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
      <button class="seg-btn active" data-base="glow"    aria-pressed="true">Overview</button>
      <button class="seg-btn"        data-base="street"  aria-pressed="false">Street</button>
      <button class="seg-btn hero-hidden" data-base="terrain" aria-pressed="false">3D Terrain</button>
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
  <div class="places-zoom" role="group" aria-label="Zoom">
    <div class="places-zoom-pair">
      <button class="places-zoom-btn" id="places-zoom-in" type="button" aria-label="Zoom in">
        <svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
      <button class="places-zoom-btn" id="places-zoom-out" type="button" aria-label="Zoom out">
        <svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
    </div>
    <button class="places-fs" id="places-zoom-reset" type="button"
            aria-label="Reset view" title="Reset to default view">
      <svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><polyline points="21 3 21 9 15 9"/></svg>
    </button>
  </div>
</div>

<script>
(function(){
  var PD = __PD_JSON__;
  var hero = document.getElementById('places-hero');
  var cv   = document.getElementById('chart-places-hero');
  if(!cv) return;
  var ctx  = cv.getContext('2d');
  var reduce = matchMedia('(prefers-reduced-motion:reduce)').matches;

  // ── injected data ─────────────────────────────────────────────────────────
  // Tracks keep their raw [lng,lat,...] pairs; MapLibre owns the Web Mercator
  // projection now, so every point is projected through map.project() at draw
  // time (no bespoke equirectangular frame -> perfect tile registration at all
  // latitudes). base = per-track glow alpha + golden-ratio jitter (unchanged).
  var TRACKS = PD.tracks.map(function(t, i){
    var jitter = (i*0.6180339887) % 1;
    return {c:t.c, g:t.g, p:t.p, n:t.p.length/2,
            base:(t.g<2 ? 0.30 : 0.50) + 0.12*jitter};
  });
  // Labels arrive as normalized u/v (the old frame); reconstruct lng/lat once so
  // they project through the map exactly like the routes.
  var LABELS = PD.labels.map(function(L){
    return {k:L.k, name:L.name, coord:L.coord, sub:L.sub,
            lng: PD.lng0 + L.u*PD.lngspan, lat: PD.lat1 - L.v*PD.latspan};
  });
  // Geographic bounds for the framed views (reconstructed from the old u/v rects).
  var allBounds = [[PD.lng0, PD.lat1 - PD.latspan], [PD.lng0 + PD.lngspan, PD.lat1]];
  function viewBounds(name){
    var vw = PD.views[name];
    if(!vw) return allBounds;
    var west  = PD.lng0 + vw.u0*PD.lngspan, east  = PD.lng0 + vw.u1*PD.lngspan;
    var north = PD.lat1 - vw.v0*PD.latspan, south = PD.lat1 - vw.v1*PD.latspan;
    return [[west, south], [east, north]];
  }

  // ── theme colors (re-read on every retint) ────────────────────────────────
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
  function isLight(){ return document.documentElement.classList.contains('light'); }
  var TH = null;
  function retint(){
    TH = {
      light: isLight(),
      route: [ readVar('--running'), readVar('--mtb'), readVar('--elevation'),
               hexRGB('#4ade80'), readVar('--other') ],
      tp: readVar('--text-primary'),
      ts: readVar('--text-secondary'),
      accent: readVar('--accent')
    };
  }

  // ── MapLibre basemap (Glow / Street / Terrain) ────────────────────────────
  var MT_KEY = "__MAPTILER_KEY__";
  var HAS_ML = !!window.maplibregl;
  var TILES_OK = HAS_ML && MT_KEY.length > 0;
  var mode = 'glow';                     // glow | street | terrain
  var lens = 'none';                     // 'trips' dims the two home clusters
  var map = null;

  function tilelessStyle(){
    // Tile-free: a transparent background so the hero's radial-gradient ground
    // shows through. This is ONLY the graceful-degradation ground when tiles/key
    // are absent -- it is not a selectable look (Glow renders Backdrop tiles).
    return {version:8, sources:{}, layers:[
      {id:'bg', type:'background', paint:{'background-color':'rgba(0,0,0,0)'}}
    ]};
  }
  function mtStyle(slug){ return 'https://api.maptiler.com/maps/'+slug+'/style.json?key='+MT_KEY; }
  // Each mode maps to a MapTiler style whose exact '-dark' counterpart is used in
  // dark theme, so every basemap tracks the page theme through one code path.
  // terrain's slug is the drape surface for real 3D terrain (outdoor-v4's
  // hillshading/contours read best pitched) -- see applyTerrainState().
  var SLUGS = {glow:'backdrop-v4', street:'streets-v4', terrain:'outdoor-v4'}; //Consider aquarelle-v4 for streets
  // Glow's light-theme ground is a custom MapTiler style ("BackgroundGhost") tuned
  // to the near-white/faint-line look the hero had before the MapTiler conversion --
  // lighter than stock Backdrop, so no CSS wash is layered on top of it. Dark theme
  // still uses backdrop-v4-dark (no custom dark counterpart exists yet).
  var GLOW_LIGHT_STYLE_ID = '019f7141-13e8-7ca3-bd1d-c8bc1184f396';
  function styleForMode(m){
    if(!TILES_OK) return tilelessStyle();
    if(m==='glow' && isLight()) return mtStyle(GLOW_LIGHT_STYLE_ID);
    var slug = SLUGS[m] || SLUGS.glow;
    return mtStyle(slug + (isLight() ? '' : '-dark'));
  }
  function applyMapStyle(){
    if(!map) return;
    // Strip any active 3D terrain before swapping styles: MapLibre's style-diff
    // throws (AbortError / "_checkLoaded") when a raster-dem source tied to
    // setTerrain() isn't present in the incoming style. applyTerrainState()
    // (on 'idle', once the new style has settled) re-adds it if still wanted.
    if(map.getTerrain()) map.setTerrain(null);
    if(map.getLayer(ROUTE_LAYER)) map.removeLayer(ROUTE_LAYER);
    if(map.getSource(ROUTE_SRC)) map.removeSource(ROUTE_SRC);
    if(map.getSource(TERRAIN_SRC)) map.removeSource(TERRAIN_SRC);
    map.setStyle(styleForMode(mode));
  }
  // Reflect the active basemap mode as a class on the hero so CSS can target a
  // single mode.
  function setModeClass(){
    hero.classList.toggle('terrain', mode==='terrain');
  }

  function initMap(){
    if(map || !HAS_ML) return;
    map = new maplibregl.Map({
      container: 'places-map',
      style: styleForMode(mode),
      bounds: allBounds,
      fitBoundsOptions: {padding: 34, animate: false},
      attributionControl: {compact: true},
      dragRotate: false, pitchWithRotate: false,
      renderWorldCopies: false, minZoom: 1, maxZoom: 16, maxPitch: 75, fadeDuration: 120
    });
    if(map.touchZoomRotate) map.touchZoomRotate.disableRotation();
    map.on('move', drawGlow);
    map.on('styledata', drawGlow);
    // setStyle() (basemap switch) wipes custom sources/layers, so re-assert 3D
    // terrain once the new style has settled. 'style.load' looked like the right
    // event (it's what MapTiler's own docs use) but empirically does NOT fire
    // reliably for setStyle() calls after the map's initial style -- confirmed via
    // direct event tracing: after a setStyle() call, sourcedata/styledata/idle all
    // fired but style.load never did, silently leaving terrain permanently missing
    // with no console error. 'idle' (fires once the map has fully finished
    // rendering, incl. all sources) fired reliably in every case tested.
    map.on('idle', applyTerrainState);
    map.on('load', function(){
      if(pendingActivity){ flyToActivity(pendingActivity, false); }
      else if(pendingFrame){ goFrame(pendingFrame, false); }
      updateTerrainButtonVisibility();
      applyTerrainState();
      drawGlow();
    });
  }

  // ── 3D terrain (single-activity view only) ────────────────────────────────
  var TERRAIN_SRC = 'places-terrain-dem';
  var ROUTE_SRC = 'places-activity-route';
  var ROUTE_LAYER = 'places-activity-route-line';
  var terrainActive = false;   // tracks whether we've already eased/enabled rotate
  function applyTerrainState(){
    if(!map) return;
    var want = (mode==='terrain' && !!curActivity && TILES_OK);
    if(want){
      if(!map.getSource(TERRAIN_SRC)){
        map.addSource(TERRAIN_SRC, {
          type: 'raster-dem',
          url: 'https://api.maptiler.com/tiles/terrain-rgb-v2/tiles.json?key=' + MT_KEY,
          tileSize: 512
        });
      }
      map.setTerrain({source: TERRAIN_SRC, exaggeration: 1.5});
      var coords = window.placesRouteCoords && window.placesRouteCoords[curActivity];
      if(coords && coords.length >= 4){
        var line = [];
        for(var i=0; i<coords.length; i+=2){ line.push([coords[i], coords[i+1]]); }
        var geojson = {type:'Feature', properties:{},
                        geometry:{type:'LineString', coordinates: line}};
        var src = map.getSource(ROUTE_SRC);
        if(src){ src.setData(geojson); }
        else {
          map.addSource(ROUTE_SRC, {type:'geojson', data: geojson});
          map.addLayer({
            id: ROUTE_LAYER, type: 'line', source: ROUTE_SRC,
            layout: {'line-cap':'round', 'line-join':'round'},
            paint: {
              'line-color': 'rgb(' + (TH ? TH.accent.join(',') : '245,158,11') + ')',
              'line-width': 4, 'line-opacity': 0.95
            }
          });
        }
      }
      if(!terrainActive){
        map.easeTo({pitch: 60, duration: 700});
        map.dragRotate.enable();
        if(map.touchZoomRotate) map.touchZoomRotate.enableRotation();
        terrainActive = true;
      }
    } else if(terrainActive){
      map.setTerrain(null);
      if(map.getLayer(ROUTE_LAYER)) map.removeLayer(ROUTE_LAYER);
      if(map.getSource(ROUTE_SRC)) map.removeSource(ROUTE_SRC);
      map.easeTo({pitch: 0, bearing: 0, duration: 500});
      map.dragRotate.disable();
      if(map.touchZoomRotate) map.touchZoomRotate.disableRotation();
      terrainActive = false;
    }
  }
  // Show/hide the 3D Terrain basemap button -- it only means something once an
  // activity is deep-linked (see curActivity).
  function updateTerrainButtonVisibility(){
    var btn = hero.querySelector('[data-base="terrain"]');
    if(btn) btn.classList.toggle('hero-hidden', !(curActivity && TILES_OK));
  }

  // ── projection + glow overlay ─────────────────────────────────────────────
  var dpr = 1;
  function fallbackProject(lng, lat){
    // Only used when MapLibre is unavailable: a static equirectangular fit of the
    // full extent, so the glow still renders (no pan/zoom) rather than a blank box.
    var w = hero.clientWidth, h = hero.clientHeight;
    var s = Math.min(w/PD.ww, h/PD.wh);
    var u = (lng - PD.lng0)/PD.lngspan, v = (PD.lat1 - lat)/PD.latspan;
    return [ w/2 + (u-0.5)*PD.ww*s, h/2 + (v-0.5)*PD.wh*s ];
  }
  function projectPt(lng, lat){
    if(map){ var p = map.project([lng, lat]); return [p.x, p.y]; }
    return fallbackProject(lng, lat);
  }
  function sizeCanvas(w, h){
    dpr = Math.min(window.devicePixelRatio||1, 2);
    var nw = Math.round(w*dpr), nh = Math.round(h*dpr);
    if(cv.width!==nw || cv.height!==nh){ cv.width=nw; cv.height=nh; }
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  function drawGlow(){
    if(!TH) retint();
    var w = hero.clientWidth, h = hero.clientHeight;
    if(!w || !h) return;
    sizeCanvas(w, h);
    ctx.clearRect(0,0,w,h);

    ctx.lineJoin='round'; ctx.lineCap='round';
    // Zoom-scaled stroke, a touch heavier than the original so colored routes read
    // against both the near-white light ground and busy Street/Terrain detail.
    var z = map ? map.getZoom() : 3.6;
    var lw = Math.max(1.4, Math.min(3.0, 0.7 + z*0.18));
    var alphaMul = TH.light ? 0.85 : 1.0;

    // Project each track's polyline once into a Path2D (with its colored-pass
    // alpha), then stroke every path twice below — cheaper than re-projecting.
    var paths = [];
    for(var ti=0; ti<TRACKS.length; ti++){
      var t = TRACKS[ti], a = t.base;
      if(lens==='trips') a = (t.g<2) ? a*0.20 : Math.min(0.92, a*1.55);
      a *= alphaMul;
      var pth = new Path2D();
      var p = t.p;
      for(var k=0; k<t.n; k++){
        var xy = projectPt(p[2*k], p[2*k+1]);
        if(k) pth.lineTo(xy[0], xy[1]); else pth.moveTo(xy[0], xy[1]);
      }
      paths.push({path:pth, a:a, c:t.c});
    }

    // Pass 1 — contrasting casing/standoff. Drawn source-over (a white casing
    // under 'multiply', or a dark one under 'lighter', would be a no-op), and
    // BEFORE any colored line so a casing never nicks a neighbour's color. White
    // on light, near-ground-dark on dark; faded with each route's own alpha.
    ctx.globalCompositeOperation = 'source-over';
    ctx.lineWidth = lw + 2.0;
    ctx.strokeStyle = TH.light ? 'rgba(255,255,255,0.9)' : 'rgba(13,17,23,0.85)';
    for(var ci=0; ci<paths.length; ci++){
      ctx.globalAlpha = paths[ci].a;
      ctx.stroke(paths[ci].path);
    }
    ctx.globalAlpha = 1;

    // Pass 2 — the per-sport color. Additive bloom on the dark grounds; multiply
    // as ink-on-paper on the light grounds. Sits on top of the casing.
    ctx.globalCompositeOperation = TH.light ? 'multiply' : 'lighter';
    ctx.lineWidth = lw;
    for(var pi=0; pi<paths.length; pi++){
      var col = TH.route[paths[pi].c];
      ctx.strokeStyle = 'rgba('+col[0]+','+col[1]+','+col[2]+','+paths[pi].a+')';
      ctx.stroke(paths[pi].path);
    }

    ctx.globalCompositeOperation='source-over';
    drawLabels();
    updateZoomButtons();
  }

  // ── labels + declutter ──────────────────────────────────────────────────
  function rectsOverlap(a,b){
    return !(a.x2 < b.x1 || b.x2 < a.x1 || a.y2 < b.y1 || b.y2 < a.y1);
  }
  function drawLabels(){
    var W = hero.clientWidth, H = hero.clientHeight;
    var placed=[];
    for(var i=0;i<LABELS.length;i++){
      var L=LABELS[i];
      var xy=projectPt(L.lng, L.lat), x=xy[0], y=xy[1];
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
    var ly = by+4;
    ctx.fillText(L.name, tx, ly);
    ctx.font="11px 'Geist Mono', ui-monospace, monospace";
    // Stack the mono sub-lines with a running offset so a label without a
    // coord line (the homes) closes the gap instead of leaving a hole.
    // Light theme: real near-white basemaps need the coord/sub lines at full alpha
    // to clear WCAG AA (4.5:1) -- the old 0.85x/0.9x fade measured as low as 3.56:1
    // against Backdrop/Street/Terrain's near-white light grounds. Dark theme keeps
    // the original fade (huge contrast headroom against the dark grounds there).
    var coordMul = TH.light ? 1.0 : 0.85;
    var subMul   = TH.light ? 1.0 : 0.9;
    if(L.coord){
      ly += 16;
      ctx.fillStyle='rgba('+ts[0]+','+ts[1]+','+ts[2]+','+(alpha*coordMul)+')';
      ctx.fillText(L.coord, tx, ly);
    }
    if(L.sub){
      ly += 15;
      ctx.fillStyle='rgba('+ts[0]+','+ts[1]+','+ts[2]+','+(alpha*subMul)+')';
      ctx.fillText(L.sub, tx, ly);
    }
    ctx.shadowBlur=0;
  }

  // ── camera framing (MapLibre) ─────────────────────────────────────────────
  var pendingFrame = null;    // a View to apply once the map finishes loading
  var pendingActivity = null; // an activity id (?a=) to fly to once the map loads
  var curActivity = null;     // the currently deep-linked activity id, or null
  function setFrameButtons(name){
    hero.querySelectorAll('[data-frame]').forEach(function(b){
      var on = (b.dataset.frame===name);
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on?'true':'false');
    });
  }
  function goFrame(v, animate){
    lens = (v==='trips') ? 'trips' : 'none';
    var bounds = (v==='sd' || v==='bos') ? viewBounds(v) : allBounds;
    var pad = (v==='sd' || v==='bos') ? 60 : 34;
    if(map){
      map.fitBounds(bounds, {padding: pad, duration: 620,
                             animate: animate!==false && !reduce});
    }
    drawGlow();
  }

  // Public fly-to hook: the passport stamps, home cards, and peak rows call this
  // to zoom the main map onto a route (a named View, or a {lat0,lat1,lng0,lng1}
  // box). Contract preserved from the canvas hero so those callers are untouched.
  window.placesFlyTo = function(target, animate){
    var anim = (animate!==false) && !reduce;   // default animated; false = jump
    var name = null;
    if(typeof target==='string'){
      name = target;
      goFrame(target, animate);
    } else if(target && typeof target==='object'){
      lens = 'none';
      if(map){
        map.fitBounds([[target.lng0, target.lat0], [target.lng1, target.lat1]],
                      {padding: 50, duration: 620, animate: anim});
      }
      drawGlow();
    }
    setFrameButtons(name);
  };

  // ── controls ──────────────────────────────────────────────────────────────
  // Persist the View/Map selection into '#places?v=<frame>&b=<base>' (defaults
  // v=all, b=glow are omitted) so a reload restores it -- same history.replaceState
  // mechanism the page-level tab router uses.
  function syncHashState(){
    var activeFrame = hero.querySelector('[data-frame].active');
    var activeBase = hero.querySelector('[data-base].active');
    var v = activeFrame ? activeFrame.dataset.frame : 'all';
    var bmode = activeBase ? activeBase.dataset.base : 'glow';
    var parts = [];
    // A deep-linked activity (?a=) supersedes a named frame (?v=); base is independent.
    if(curActivity) parts.push('a='+encodeURIComponent(curActivity));
    else if(v && v!=='all') parts.push('v='+v);
    if(bmode && bmode!=='glow') parts.push('b='+bmode);
    var suffix = parts.length ? ('?'+parts.join('&')) : '';
    history.replaceState(null, '', '#places'+suffix);
  }
  // Exposed so the page tab-router can re-assert Places' sub-state when Places
  // becomes active again (otherwise it writes a bare '#places', desyncing the URL
  // from the still-shown map).
  window.placesSyncHash = syncHashState;
  function setBaseButtons(m){
    hero.querySelectorAll('[data-base]').forEach(function(b){
      var on=(b.dataset.base===m); b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on?'true':'false');
    });
  }
  // Entering a single-activity deep link: record the id, and -- unless the user
  // had explicitly chosen Street -- default the basemap to 3D Terrain (the whole
  // point of showing terrain only makes sense for one route). See applyTerrainState().
  function enterActivity(id){
    curActivity = String(id);
    if(mode!=='street' && mode!=='terrain' && TILES_OK){
      mode = 'terrain';
      setModeClass();
      setBaseButtons('terrain');
      applyMapStyle();
    }
    updateTerrainButtonVisibility();
    applyTerrainState();
  }
  // Leaving single-activity view (a View button, or an unresolved deep link):
  // 3D Terrain has no meaning without an activity, so fall back to Overview.
  function exitActivityMode(){
    curActivity = null;
    updateTerrainButtonVisibility();
    if(mode==='terrain'){
      mode = 'glow';
      setModeClass();
      setBaseButtons('glow');
      applyMapStyle();
    }
    applyTerrainState();
  }
  // Deep-link hook for stamp/peak clicks: record the activity id -> '#places?a=<id>'.
  // placesFlyTo already cleared the frame buttons for a box target.
  window.placesLinkActivity = function(id){
    if(id){ enterActivity(id); } else { exitActivityMode(); }
    syncHashState();
  };
  // Resolve a deep-linked activity id to its fly box (published by the passport +
  // peaks scripts into window.placesFlyTargets) and zoom to it. Unknown id falls
  // back to the default frame, no console error.
  function flyToActivity(id, animate){
    var box = window.placesFlyTargets && window.placesFlyTargets[id];
    if(!box){ exitActivityMode(); goFrame('all', animate); return; }
    enterActivity(id);
    window.placesFlyTo(box, animate);
  }
  hero.querySelectorAll('[data-frame]').forEach(function(b){
    b.addEventListener('click', function(){
      exitActivityMode();          // a named frame supersedes any ?a= deep link
      setFrameButtons(b.dataset.frame);
      goFrame(b.dataset.frame, true);
      syncHashState();
    });
  });
  // Street/Terrain need MapLibre + a MapTiler key; disable them otherwise so the
  // hero stays on the tile-free Glow ground rather than a broken map.
  hero.querySelectorAll('[data-base]').forEach(function(b){
    var m = b.dataset.base;
    if((m==='street' || m==='terrain') && !TILES_OK){
      b.disabled = true;
      b.title = 'Map tiles unavailable';
      return;
    }
    b.addEventListener('click', function(){
      setBaseButtons(m);
      mode = m;
      setModeClass();
      applyMapStyle();
      applyTerrainState();
      drawGlow();
      syncHashState();
    });
  });

  // Restore the View/Map selection from the URL hash on boot. Map selection sets
  // `mode` before initMap so the map opens on the right basemap; the View is
  // deferred to map 'load' via pendingFrame (no visible fly on first paint).
  (function applyHashState(){
    var h = location.hash || '';
    var qIdx = h.indexOf('?');
    if(h.indexOf('places')===-1 || qIdx===-1) return;
    var params = new URLSearchParams(h.slice(qIdx+1));
    var v = params.get('v'), bmode = params.get('b'), a = params.get('a');
    if((bmode==='street' || bmode==='terrain') && TILES_OK){
      mode = bmode;
    } else if(a && TILES_OK){
      // A deep-linked activity with no explicit basemap override defaults to
      // 3D Terrain (mirrors enterActivity()'s default for stamp/peak clicks).
      mode = 'terrain';
    }
    if(mode==='street' || mode==='terrain') setBaseButtons(mode);
    if(a){
      // Deep link to a specific activity: defer the fly to map 'load' (the fly
      // targets are published by the passport/peaks scripts, which run after this).
      pendingActivity = a;
      curActivity = a;
      setFrameButtons(null);
    } else if(v==='sd' || v==='bos' || v==='trips'){
      pendingFrame = v;
      lens = (v==='trips') ? 'trips' : 'none';
      setFrameButtons(v);
    }
    updateTerrainButtonVisibility();
  })();
  setModeClass();   // set the boot mode class (glow by default, or hash-restored)

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
        if(map) map.resize();
        drawGlow();
      });
    }
  }

  // ── explicit zoom / reset controls (wired to the MapLibre camera) ─────────
  var zoomInBtn = document.getElementById('places-zoom-in');
  var zoomOutBtn = document.getElementById('places-zoom-out');
  var zoomResetBtn = document.getElementById('places-zoom-reset');
  function updateZoomButtons(){
    if(!zoomInBtn || !map) return;
    var z = map.getZoom();
    zoomInBtn.disabled  = z >= map.getMaxZoom() - 1e-3;
    zoomOutBtn.disabled = z <= map.getMinZoom() + 1e-3;
  }
  if(zoomInBtn)  zoomInBtn.addEventListener('click', function(){ if(map) map.zoomIn(); });
  if(zoomOutBtn) zoomOutBtn.addEventListener('click', function(){ if(map) map.zoomOut(); });
  if(zoomResetBtn) zoomResetBtn.addEventListener('click', function(){
    // Reuse the "All" view button's own click handler (single source of truth
    // for the default camera + lens-clear + button-sync), rather than
    // duplicating its target/lens logic here.
    var allBtn = hero.querySelector('[data-frame="all"]');
    if(allBtn) allBtn.click();
  });

  // Pan / scroll-zoom / pinch / double-click zoom / shift-drag box-zoom are all
  // handled natively by MapLibre (with cooperativeGestures so the page still
  // scrolls). The glow overlay tracks the camera via map.on('move', drawGlow).

  // ── lifecycle ─────────────────────────────────────────────────────────────
  // Re-inked by the page theme toggle (template.py applyChartTheme): retint the
  // glow, and swap every mode's light/dark basemap variant. Only skip the restyle
  // when there are no tiles (the ground is pure CSS, so setStyle would just flash).
  window.__placesHeroRedraw = function(){
    retint();
    if(TILES_OK) applyMapStyle();
    drawGlow();
  };
  // The Places section can mount hidden (inactive tab); create the map lazily on
  // the first non-zero size, then keep it resized. WebGL context init on a 0x0
  // container is unreliable, so deferring avoids a blank map on first activation.
  if(window.ResizeObserver){
    var ro=new ResizeObserver(function(){
      if(!map){ if(hero.clientWidth>0) initMap(); }
      else { map.resize(); }
      drawGlow();
    });
    ro.observe(hero);
  }
  window.addEventListener('resize', function(){ if(map) map.resize(); drawGlow(); });
  retint();
  if(hero.clientWidth>0) initMap();
  drawGlow();
})();
</script>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# Pass C — Passport (Module 3) + Peaks (Module 4)
#
# Both builders sit BELOW the two-homes cards inside #view-places and return one
# self-contained raw HTML string each. The analytical heart is trip-clustering by
# time-gap-away-from-home (Wrinkle A) + a peaks record book that catches the
# home-adjacent giants trip-clustering misses (Wrinkle B). Editorial copy (region
# names, captions, badges) is hardcoded exactly as the hero's key-trip detail is;
# structure, dates, sport tags, geometry and the states/provinces count are LIVE.
#
# INJECTED-JSON XSS RULE (as Pass B): the geometry payload `PC` carries ONLY
# numeric arrays + fly boxes, keyed by an opaque slot id. Every display string
# (region/caption/dates/tags/badge/title/coord) is rendered SERVER-SIDE into the
# card HTML and _html_escape'd there -- the athlete's activity TITLES are
# third-party and json.dumps does NOT escape </script>.
# ═══════════════════════════════════════════════════════════════════════════════

# Canadian provinces present in _STATE_BOXES (everything else there is a US state).
_PROVINCES = {"BC", "AB", "SK", "MB", "ON", "QC"}

_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Sport -> passport tag word. Unknowns fall back to a lowercased sport type.
_SPORT_TAG = {
    "Run": "run", "TrailRun": "trail run", "Walk": "walk", "Hike": "hike",
    "NordicSki": "nordic ski", "AlpineSki": "alpine ski", "Snowboard": "snowboard",
    "Ride": "ride", "EBikeRide": "e-bike", "MountainBikeRide": "mtb",
    "StandUpPaddling": "SUP", "IceSkate": "skate", "Pickleball": "pickleball",
}

# Curated featured-trip copy, in filmstrip order. Matched to a live cluster by a
# UNIQUE title substring `sig` (NOT a geo box -- the two Michigan trips overlap
# geographically). `sig` also selects the signature activity whose GPS drives the
# thumbnail. Badge facts are the PINNED superlatives (northernmost = Vancouver,
# NOT the mock's factually-wrong "Maine 45.2N"). badge = (css_class, text) | None.
_PASSPORT_TRIPS = [
    {"sig": "Whitney",      "region": "Sierra Nevada · CA",
     "caption": "Mt. Whitney from Whitney Portal & JMT",
     "badge": ("hi",    "Highest point · 14,507 ft")},
    {"sig": "Maine Hut",    "region": "Western Maine",
     "caption": "Maine Hut Trail — Days 1–3",
     "badge": ("east",  "Easternmost · 70.2°W")},
    {"sig": "Stanley Park", "region": "Seattle → Vancouver",
     "caption": "Vancouver — Stanley Park",
     "badge": ("north", "Northernmost · 49.3°N")},
    {"sig": "Snow Snake",   "region": "Northern Michigan",
     "caption": "Snow Snake",                         "badge": None},
    {"sig": "Muggy",        "region": "Mid-Michigan",
     "caption": "Muggy in Michigan",                  "badge": None},
    {"sig": "Jay Peak",     "region": "Jay Peak · VT",
     "caption": "Jay Peak Spring Riding",             "badge": None},
    {"sig": "Whaleback",    "region": "Upper Valley · VT/NH",
     "caption": "Whaleback & Hanover holiday",        "badge": None},
]

# Peaks record book (Module 4): singular moments, catches Wrinkle-B giants. Each
# row's value/title is hardcoded editorial copy; `sig` finds the source activity
# for the sparkline + lat/lng. FIRST-IN-SAN-DIEGO is special-cased to the live
# earliest SD-box activity (its title is the athlete's, rendered/escaped here).
_PEAKS_DEF = [
    {"overline": "HIGHEST POINT",        "value": "14,507 ft",
     "title": "Mt. Whitney via Whitney Portal & JMT", "sig": "Mt. Whitney"},
    {"overline": "NORTHERNMOST",         "value": "49.3°N",
     "title": "Stanley Park, Vancouver",             "sig": "Stanley Park Bike"},
    {"overline": "HOME-ADJACENT GIANT",  "value": "10,800 ft",
     "title": "Mt. San Jacinto from Marion Trailhead", "sig": "San Jacinto"},
    {"overline": "EASTERNMOST",          "value": "70.2°W",
     "title": "Maine Hut Trail — Day 3",        "sig": "Maine Hut Trail Day 3"},
    {"overline": "FIRST IN SAN DIEGO",   "value": "Apr 2025",
     "title": None,                                  "sig": "__first_sd__"},
    {"overline": "LONGEST SINGLE CLIMB", "value": "6,752 ft",
     "title": "Mt. Whitney via Whitney Portal & JMT", "sig": "Mt. Whitney"},
]


def _pdate(s):
    """Parse start_date_local ('YYYY-MM-DDTHH:MM:SS[Z]') -> datetime or None."""
    s = (s or "").strip().replace("Z", "")
    if not s:
        return None
    try:
        return _dt.datetime.fromisoformat(s)
    except ValueError:
        try:
            return _dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None


def _act_latlng(r):
    """(lat, lng) from an activity's start_latlng ('lat,lng'), or None."""
    ll = (r.get("start_latlng") or "").strip()
    if not ll:
        return None
    parts = ll.split(",")
    if len(parts) != 2:
        return None
    lat, lng = mf(parts[0].strip()), mf(parts[1].strip())
    return (lat, lng) if lat is not None and lng is not None else None


def _act_home(r):
    """'sd' | 'bos' | None for an activity, by start_latlng-in-home-box."""
    ll = _act_latlng(r)
    if ll is None:
        return None
    lat, lng = ll
    if _in_box(lng, lat, _SD_BOX):
        return "sd"
    if _in_box(lng, lat, _BOS_BOX):
        return "bos"
    return None


def _rdp_keep(xy, eps):
    """RDP returning the KEPT indices (so parallel altitude/grade arrays subset
    the same way). Iterative; mirrors _rdp's perpendicular-distance test."""
    n = len(xy)
    if n < 3:
        return list(range(n))
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = xy[a]
        bx, by = xy[b]
        dx, dy = bx - ax, by - ay
        den = math.hypot(dx, dy)
        dmax = 0.0
        idx = -1
        for i in range(a + 1, b):
            px, py = xy[i]
            d = (math.hypot(px - ax, py - ay) if den == 0
                 else abs(dy * px - dx * py + bx * ay - by * ax) / den)
            if d > dmax:
                dmax = d
                idx = i
        if dmax > eps and idx != -1:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [i for i in range(n) if keep[i]]


def _load_trip_geo(aid, cap=120):
    """Read ONE activity's stream and return decimated thumbnail geometry:
    {path:[u,v,...] fit to the route's own cos-lat bbox, aspect preserved;
     grade:[g,...] = grade_pct/12 clamped to +-1 (descent/flat/climb color);
     elev:[e,...] = altitude_m normalized 0..1; bbox:(lat0,lat1,lng0,lng1)}.
    Only the handful of signature/peak streams are read (not all 344)."""
    import csv
    fn = os.path.join(STREAMS_DIR, str(aid) + ".csv")
    if not os.path.exists(fn):
        return None
    raw = []
    with open(fn, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ln = mf((row.get("lng") or "").strip())
            la = mf((row.get("lat") or "").strip())
            if ln is None or la is None:
                continue
            al = mf((row.get("altitude_m") or "").strip())
            gr = mf((row.get("grade_pct") or "").strip())
            raw.append((ln, la, al if al is not None else 0.0,
                        gr if gr is not None else 0.0))
    if len(raw) < 2:
        return None
    xy = [(p[0], p[1]) for p in raw]
    idx = _rdp_keep(xy, RDP_EPS)
    if len(idx) > cap:
        idx = [idx[round(i * (len(idx) - 1) / (cap - 1))] for i in range(cap)]
    pts = [raw[i] for i in idx]
    lngs = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    alts = [p[2] for p in pts]
    grs = [p[3] for p in pts]
    ln0, ln1 = min(lngs), max(lngs)
    la0, la1 = min(lats), max(lats)
    coslat = math.cos(math.radians((la0 + la1) / 2.0))
    ww = (ln1 - ln0) * coslat or 1e-6
    wh = (la1 - la0) or 1e-6
    sc = 1.0 / max(ww, wh)                      # uniform scale -> aspect preserved
    cln, cla = (ln0 + ln1) / 2.0, (la0 + la1) / 2.0
    path = []
    for ln, la in zip(lngs, lats):
        path.append(round(0.5 + (ln - cln) * coslat * sc, 4))
        path.append(round(0.5 - (la - cla) * sc, 4))
    amin, amax = min(alts), max(alts)
    asp = (amax - amin) or 1.0
    elev = [round((a - amin) / asp, 3) for a in alts]
    grade = [round(max(-1.0, min(1.0, g / 12.0)), 3) for g in grs]
    # Raw decimated lng/lat (flat, 5dp) for callers that project themselves — e.g.
    # the detail mini-map's MapLibre basemap. Existing callers ignore this key.
    coords = []
    for ln, la in zip(lngs, lats):
        coords.append(round(ln, 5))
        coords.append(round(la, 5))
    return {"path": path, "grade": grade, "elev": elev, "coords": coords,
            "bbox": (la0, la1, ln0, ln1)}


def _fly_box(lat0, lat1, lng0, lng1, pad=0.05):
    """A placesFlyTo target box (south, north, west, east) with a small pad."""
    return {"lat0": round(lat0 - pad, 4), "lat1": round(lat1 + pad, 4),
            "lng0": round(lng0 - pad, 4), "lng1": round(lng1 + pad, 4)}


def _away_clusters(rows):
    """Cluster every away activity (start_latlng outside both home boxes) by
    time-gap-away-from-home: a new cluster starts wherever the day-gap to the
    previous away activity exceeds 5 days. Geography is ignored inside a cluster
    (Wrinkle A: the Pacific-NW trip roams Seattle->Vancouver and stays one)."""
    away = []
    for r in rows:
        d = _pdate(r.get("start_date_local"))
        ll = _act_latlng(r)
        if d and ll and _act_home(r) is None:
            away.append((d, ll, r))
    away.sort(key=lambda x: x[0])
    clusters, cur = [], []
    for d, ll, r in away:
        if cur and (d.date() - cur[-1][0].date()).days > 5:
            clusters.append(cur)
            cur = []
        cur.append((d, ll, r))
    if cur:
        clusters.append(cur)
    return clusters


def _sport_tags(sports):
    """'nordic ski x3', 'run x3', 'snowboard . alpine ski' (dot-joined, count>1
    suffixed). Ordered by frequency then first appearance."""
    c = Counter(sports)
    parts = []
    for sp, n in c.most_common():
        word = _SPORT_TAG.get(sp, (sp or "").lower())
        parts.append("%s ×%d" % (word, n) if n > 1 else word)
    return " · ".join(parts)


def _date_span(d0, d1):
    """'Feb 7–9 · 2025' / 'Sep 29 – Oct 2 · 2025' / cross-year."""
    if d0.year == d1.year and d0.month == d1.month:
        if d0.day == d1.day:
            return "%s %d · %d" % (_MONTHS[d0.month], d0.day, d0.year)
        return "%s %d–%d · %d" % (_MONTHS[d0.month], d0.day, d1.day, d0.year)
    if d0.year == d1.year:
        return "%s %d – %s %d · %d" % (
            _MONTHS[d0.month], d0.day, _MONTHS[d1.month], d1.day, d0.year)
    return "%s %d %d – %s %d %d" % (
        _MONTHS[d0.month], d0.day, d0.year, _MONTHS[d1.month], d1.day, d1.year)


def _states_provinces(rows):
    """Live distinct US states / Canadian provinces spanned by ALL away
    activities, via _STATE_BOXES (first-match). Returns (n_states, n_provinces)."""
    seen = set()
    for r in rows:
        if _act_home(r) is not None:
            continue
        ll = _act_latlng(r)
        if ll is None:
            continue
        lat, lng = ll
        for name, la, lb, lo, hi in _STATE_BOXES:
            if la <= lat <= lb and lo <= lng <= hi:
                seen.add(name)
                break
    prov = sum(1 for s in seen if s in _PROVINCES)
    return len(seen) - prov, prov


def _find_act(rows, sub):
    """First activity whose title contains `sub` (case-insensitive)."""
    sub = sub.lower()
    for r in rows:
        if sub in (r.get("name") or "").lower():
            return r
    return None


def _passport_data(rows):
    """Assemble the passport: featured stamps (curated order), brief-stop chips,
    the geometry payload PC (slot -> {path,grade,elev,fly}), and header counts."""
    clusters = _away_clusters(rows)
    used = set()                       # cluster indices claimed by a curated trip
    featured = []                      # display dicts, curated order
    pc = {}

    for spec in _PASSPORT_TRIPS:
        sig = spec["sig"].lower()
        for ci, c in enumerate(clusters):
            if ci in used:
                continue
            sigact = next((r for _, _, r in c if sig in (r.get("name") or "").lower()),
                          None)
            if sigact is None:
                continue
            used.add(ci)
            d0, d1 = c[0][0], c[-1][0]
            lats = [ll[0] for _, ll, _ in c]
            lngs = [ll[1] for _, ll, _ in c]
            slot = "t%d" % len(featured)
            geo = _load_trip_geo(sigact["id"]) or {}
            pc[slot] = {"path": geo.get("path", []), "grade": geo.get("grade", []),
                        "elev": geo.get("elev", []), "coords": geo.get("coords", []),
                        "id": sigact["id"],
                        "fly": _fly_box(min(lats), max(lats), min(lngs), max(lngs))}
            featured.append({
                "slot": slot, "region": spec["region"], "caption": spec["caption"],
                "dates": _date_span(d0, d1),
                "tags": _sport_tags([r.get("sport_type") for _, _, r in c]),
                "badge": spec["badge"]})
            break

    # Brief stops = single-day/single-activity clusters not claimed as featured.
    # Unmatched MULTI-day clusters degrade to auto-featured (graceful; no code
    # change needed for a future trip) rather than vanishing.
    brief = []
    for ci, c in enumerate(clusters):
        if ci in used:
            continue
        d0, d1 = c[0][0], c[-1][0]
        if len(c) == 1 and (d1 - d0).days == 0:
            r = c[0][2]
            ll = c[0][1]
            slot = "b%d" % len(brief)
            geo = _load_trip_geo(r["id"])
            if geo:
                la0, la1, ln0, ln1 = geo["bbox"]
            else:
                la0, la1, ln0, ln1 = ll[0], ll[0], ll[1], ll[1]
            pc[slot] = {"fly": _fly_box(la0, la1, ln0, ln1), "id": r["id"],
                        "coords": (geo or {}).get("coords", [])}
            brief.append({"slot": slot, "title": r.get("name") or "",
                          "date": "%s %d" % (_MONTHS[d0.month], d0.year)})
        else:
            lats = [ll[0] for _, ll, _ in c]
            lngs = [ll[1] for _, ll, _ in c]
            sigact = max(c, key=lambda x: (mf(x[2].get("total_elevation_gain_m")) or 0,
                                           mf(x[2].get("distance_km")) or 0))[2]
            slot = "t%d" % len(featured)
            geo = _load_trip_geo(sigact["id"]) or {}
            pc[slot] = {"path": geo.get("path", []), "grade": geo.get("grade", []),
                        "elev": geo.get("elev", []), "coords": geo.get("coords", []),
                        "id": sigact["id"],
                        "fly": _fly_box(min(lats), max(lats), min(lngs), max(lngs))}
            featured.append({
                "slot": slot, "region": "", "caption": sigact.get("name") or "",
                "dates": _date_span(d0, d1),
                "tags": _sport_tags([r.get("sport_type") for _, _, r in c]),
                "badge": None})

    n_states, n_prov = _states_provinces(rows)
    return featured, brief, pc, n_states, n_prov


def _peaks_data(rows):
    """Assemble the 6 peak rows: display dicts (server-side strings) + geometry
    payload keyed by slot (elev sparkline + fly box)."""
    peaks = []
    pc = {}
    # First-in-San-Diego = earliest SD-box activity (the 'move', stated neutrally).
    sd_acts = sorted(
        ((_pdate(r.get("start_date_local")), r) for r in rows if _act_home(r) == "sd"
         and _pdate(r.get("start_date_local"))),
        key=lambda x: x[0])
    first_sd = sd_acts[0][1] if sd_acts else None

    for i, spec in enumerate(_PEAKS_DEF):
        if spec["sig"] == "__first_sd__":
            act = first_sd
            title = (act.get("name") if act else "") or ""
        else:
            act = _find_act(rows, spec["sig"])
            title = spec["title"]
        slot = "p%d" % i
        coord = ""
        if act is not None:
            geo = _load_trip_geo(act["id"])
            ll = _act_latlng(act)
            if ll:
                coord = "%.2f°N  %.2f°W" % (ll[0], -ll[1])
            if geo:
                la0, la1, ln0, ln1 = geo["bbox"]
                pc[slot] = {"elev": geo["elev"], "id": act["id"],
                            "coords": geo.get("coords", []),
                            "fly": _fly_box(la0, la1, ln0, ln1)}
            elif ll:
                pc[slot] = {"elev": [], "id": act["id"],
                            "fly": _fly_box(ll[0], ll[0], ll[1], ll[1])}
        peaks.append({"slot": slot, "overline": spec["overline"],
                      "value": spec["value"], "title": title, "coord": coord})
    return peaks, pc


def _badge_html(badge):
    if not badge:
        return ""
    cls, text = badge
    return ('<span class="badge %s">%s</span>'
            % (_html_escape(cls), _html_escape(text)))


def chart_places_passport(rows):
    """Passport filmstrip of trip stamps + brief-stop chips. Returns one
    self-contained raw HTML string (geometry injected as slot-keyed numeric
    JSON; every display string rendered/escaped server-side)."""
    featured, brief, pc, n_states, n_prov = _passport_data(rows)
    pc_json = json.dumps(pc, separators=(",", ":"), ensure_ascii=False)

    stamps = []
    for f in featured:
        region = ('<div class="region">%s</div>' % _html_escape(f["region"])
                  if f["region"] else "")
        stamps.append(_STAMP.format(
            slot=_html_escape(f["slot"]), badge=_badge_html(f["badge"]),
            region=region, title=_html_escape(f["caption"]),
            dates=_html_escape(f["dates"]), tags=_html_escape(f["tags"])))
    chips = []
    for b in brief:
        chips.append(_CHIP.format(
            slot=_html_escape(b["slot"]),
            title=_html_escape(b["title"]), date=_html_escape(b["date"])))

    prov_word = "province" if n_prov == 1 else "provinces"
    state_word = "state" if n_states == 1 else "states"
    meta = ("<b>%d</b> trips · <b>%d</b> %s &amp; <b>%d</b> %s"
            % (len(featured), n_states, state_word, n_prov, prov_word))

    geom = sum(1 for v in pc.values() if v.get("path"))
    print("[places] passport: featured=%d brief=%d states=%d provinces=%d "
          "geom_aids=%d json_kb=~%d"
          % (len(featured), len(brief), n_states, n_prov, geom,
             round(len(pc_json.encode("utf-8")) / 1024.0)))
    if len(featured) != 7:
        print("[places] NOTE: passport featured=%d (pinned 7) -- trip set drifted"
              % len(featured))

    return (_PASSPORT_TEMPLATE
            .replace("__STAMPS__", "".join(stamps))
            .replace("__CHIPS__", "".join(chips))
            .replace("__META__", meta)
            .replace("__PC_JSON__", pc_json))


def chart_places_peaks(rows):
    """Peaks record book (~6 rows). Returns one self-contained raw HTML string."""
    peaks, pc = _peaks_data(rows)
    pc_json = json.dumps(pc, separators=(",", ":"), ensure_ascii=False)

    rows_html = []
    for p in peaks:
        coord = ('<div class="peak-coord">%s</div>' % _html_escape(p["coord"])
                 if p["coord"] else "")
        rows_html.append(_PEAK_ROW.format(
            slot=_html_escape(p["slot"]), value=_html_escape(p["value"]),
            overline=_html_escape(p["overline"]), title=_html_escape(p["title"]),
            coord=coord))

    print("[places] peaks: rows=%d highest=14507ft" % len(peaks))

    return (_PEAKS_TEMPLATE
            .replace("__ROWS__", "".join(rows_html))
            .replace("__PC_JSON__", pc_json))


# ─── Passport markup fragments (server-side rendered; strings _html_escape'd) ───
_STAMP = """  <article class="stamp" tabindex="0" role="button" data-stamp="{slot}"
    aria-label="{title} - view on map">
    <div class="thumb"><canvas data-stamp="{slot}"></canvas>{badge}
      <span class="viewmap">↗ view on map</span></div>
    <div class="body">{region}
      <h3 class="title">{title}</h3>
      <div class="rowmeta"><span>{dates}</span><span class="tags">{tags}</span></div>
    </div>
  </article>
"""

_CHIP = ('  <span class="chip" tabindex="0" role="button" data-stamp="{slot}">'
         '<i class="dot"></i>{title} · {date}</span>\n')

_PEAK_ROW = """  <div class="peak-row" tabindex="0" role="button" data-stamp="{slot}"
    aria-label="{overline}: {title}">
    <div class="peak-val">{value}</div>
    <div class="peak-main">
      <div class="peak-overline">{overline}</div>
      <div class="peak-title">{title}</div>
    </div>
    <canvas class="peak-spark" data-stamp="{slot}"></canvas>
    {coord}
  </div>
"""


# ─── Passport HTML/CSS/JS (ported from places-passport-mock.html; theme-aware) ──
# Mock structure/CSS ported; the mock's own --run/--mtb/... palette is replaced by
# the dashboard theme tokens, and the "design mock" foot note is dropped. Thumb
# insets stay dark in BOTH themes (little map windows, pre-spec Module 3). Route
# color = terrain grade (green/slate/red); elevation profile = violet. Click a
# stamp/chip -> window.placesFlyTo(fly) (the Pass A hero hook).
_PASSPORT_TEMPLATE = r"""<div class="places-passport">
<style>
  .places-passport{margin-top:34px}
  .places-passport .pp-head{display:flex; align-items:flex-end; justify-content:space-between;
    gap:24px; flex-wrap:wrap; margin-bottom:20px}
  .places-passport .pp-lede{max-width:560px}
  .places-passport .pp-eyebrow{font-family:'Geist Mono',ui-monospace,monospace; font-size:11px;
    letter-spacing:.28em; text-transform:uppercase; color:var(--text-tertiary); margin:0 0 10px}
  .places-passport h3.pp-h{margin:0 0 8px; font-size:clamp(21px,3vw,30px); font-weight:600;
    letter-spacing:-.02em; color:var(--text-primary)}
  .places-passport .pp-sub{margin:0; color:var(--text-secondary); font-size:15px; text-wrap:pretty}
  .places-passport .pp-right{display:flex; flex-direction:column; gap:10px; align-items:flex-end}
  .places-passport .pp-count{font-family:'Geist Mono',ui-monospace,monospace; font-size:12.5px;
    color:var(--text-secondary); font-variant-numeric:tabular-nums}
  .places-passport .pp-count b{color:var(--text-primary); font-weight:600}
  .places-passport .gradkey{display:flex; align-items:center; gap:8px;
    font-family:'Geist Mono',ui-monospace,monospace; font-size:10.5px;
    color:var(--text-tertiary); letter-spacing:.04em}
  .places-passport .gradbar{width:96px; height:7px; border-radius:4px;
    background:linear-gradient(90deg,#58a6ff,#8b949e 50%,#f59e0b)}

  /* pp-strip-outer wraps the (masked) stripwrap + the two nav arrows. Arrows are
     SIBLINGS of stripwrap (not descendants) so the edge-fade mask never dims
     them. */
  .places-passport .pp-strip-outer{position:relative}
  .places-passport .stripwrap{position:relative;
    -webkit-mask-image:linear-gradient(to right,transparent,#000 26px,#000 calc(100% - 26px),transparent);
    mask-image:linear-gradient(to right,transparent,#000 26px,#000 calc(100% - 26px),transparent)}
  .places-passport .strip{display:flex; gap:16px; overflow-x:auto; padding:6px 4px 16px;
    scroll-snap-type:x proximity; scrollbar-width:thin;
    scrollbar-color:var(--border) transparent}
  .places-passport .strip::-webkit-scrollbar{height:8px}
  .places-passport .strip::-webkit-scrollbar-thumb{background:var(--border); border-radius:8px}

  .places-passport .pp-arrow{position:absolute; top:81px; transform:translateY(-50%);
    z-index:3; width:36px; height:36px; padding:0; display:flex; align-items:center;
    justify-content:center; border-radius:50%; cursor:pointer;
    background:var(--bg-glass); border:1px solid var(--border); color:var(--text-secondary);
    backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
    box-shadow:0 4px 14px rgba(0,0,0,.18);
    transition:opacity .2s ease, color .18s, background .18s}
  .places-passport .pp-arrow:hover{color:var(--text-primary);
    border-color:color-mix(in srgb,var(--accent) 40%,var(--border))}
  .places-passport .pp-arrow:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
  .places-passport .pp-arrow-l{left:-4px}
  .places-passport .pp-arrow-r{right:-4px}
  .places-passport .pp-arrow.hidden{opacity:0; pointer-events:none}
  .places-passport .pp-arrow svg{width:18px; height:18px; stroke:currentColor; fill:none;
    stroke-width:2; stroke-linecap:round; stroke-linejoin:round}
  /* Touch devices swipe the strip natively -- hide the arrows there. */
  @media (hover:none){ .places-passport .pp-arrow{display:none} }
  @media (prefers-reduced-motion:reduce){ .places-passport .pp-arrow{transition:opacity .2s ease} }

  .places-passport .stamp{flex:0 0 clamp(260px,74vw,300px); scroll-snap-align:center;
    background:var(--bg-glass); border:1px solid var(--border); border-radius:16px; overflow:hidden;
    cursor:pointer; transition:transform .2s ease, box-shadow .2s ease, border-color .2s;
    box-shadow:0 1px 2px rgba(0,0,0,.04)}
  .places-passport .stamp:hover{transform:translateY(-4px);
    border-color:color-mix(in srgb,var(--accent) 45%,var(--border));
    box-shadow:0 12px 30px rgba(0,0,0,.16)}
  .places-passport .stamp:focus-visible{outline:2px solid var(--accent); outline-offset:3px}

  .places-passport .thumb{position:relative; height:150px; background:#0a0e16; overflow:hidden}
  :root.light .places-passport .thumb{background:#e9edf2}
  .places-passport .thumb canvas{width:100%; height:100%; display:block}
  .places-passport .badge{position:absolute; left:10px; top:10px;
    font-family:'Geist Mono',ui-monospace,monospace; font-size:10px; letter-spacing:.06em;
    text-transform:uppercase; color:#e6edf3; padding:5px 9px; border-radius:7px;
    background:rgba(10,14,22,.66); border:1px solid rgba(230,237,243,.16); backdrop-filter:blur(3px)}
  .places-passport .badge.hi{color:#fca5a5; border-color:rgba(248,113,113,.4)}
  .places-passport .badge.north{color:#93c5fd; border-color:rgba(88,166,255,.4)}
  .places-passport .badge.east{color:#4ade80; border-color:rgba(74,222,128,.4)}
  .places-passport .viewmap{position:absolute; right:10px; bottom:10px;
    font-family:'Geist Mono',ui-monospace,monospace; font-size:10.5px; color:#c9d1d9;
    opacity:0; transform:translateY(4px); transition:.2s;
    background:rgba(10,14,22,.6); padding:4px 8px; border-radius:6px}
  .places-passport .stamp:hover .viewmap,
  .places-passport .stamp:focus-visible .viewmap{opacity:1; transform:none}

  .places-passport .body{padding:14px 16px 17px}
  .places-passport .region{font-family:'Geist Mono',ui-monospace,monospace; font-size:10.5px;
    letter-spacing:.14em; text-transform:uppercase; color:var(--text-tertiary); margin-bottom:7px}
  .places-passport .title{margin:0 0 11px; font-size:16.5px; font-weight:600; line-height:1.28;
    letter-spacing:-.01em; text-wrap:balance; color:var(--text-primary)}
  .places-passport .rowmeta{display:flex; align-items:center; justify-content:space-between;
    gap:10px; font-family:'Geist Mono',ui-monospace,monospace; font-size:11.5px;
    color:var(--text-secondary); font-variant-numeric:tabular-nums}
  .places-passport .tags{color:var(--text-tertiary); text-align:right}

  .places-passport .brief{margin-top:22px; padding-top:20px; border-top:1px solid var(--border)}
  .places-passport .brief h4{font-family:'Geist Mono',ui-monospace,monospace; font-size:11px;
    letter-spacing:.2em; text-transform:uppercase; color:var(--text-tertiary); font-weight:500;
    margin:0 0 12px}
  .places-passport .chips{display:flex; flex-wrap:wrap; gap:9px}
  .places-passport .chip{font-size:12.5px; color:var(--text-secondary); background:var(--bg-surface);
    border:1px solid var(--border); padding:6px 11px; border-radius:999px; cursor:pointer;
    transition:.16s}
  .places-passport .chip:hover{color:var(--text-primary);
    border-color:color-mix(in srgb,var(--accent) 40%,var(--border))}
  .places-passport .chip:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
  .places-passport .chip .dot{display:inline-block; width:5px; height:5px; border-radius:50%;
    margin-right:7px; background:var(--text-tertiary); vertical-align:middle}

  @media (max-width:640px){
    .places-passport .pp-head{align-items:flex-start}
    .places-passport .pp-right{align-items:flex-start}
  }
  @media (prefers-reduced-motion:reduce){ .places-passport .stamp{transition:none} }
</style>

<div class="pp-head">
  <div class="pp-lede">
    <p class="pp-eyebrow">Places · The Passport</p>
    <h3 class="pp-h">Everywhere that wasn't home</h3>
    <p class="pp-sub">Each stretch of days away from Boston or San&nbsp;Diego gets one stamp &mdash;
      weighted by memory, not miles. A multi-day summit sits beside a single morning run.</p>
  </div>
  <div class="pp-right">
    <div class="pp-count">__META__</div>
    <div class="gradkey"><span>descent</span><span class="gradbar"></span><span>climb</span></div>
  </div>
</div>

<div class="pp-strip-outer">
  <button class="pp-arrow pp-arrow-l hidden" id="places-arrow-l" type="button"
          aria-label="Scroll trips left">
    <svg viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>
  </button>
  <div class="stripwrap">
    <div class="strip" id="places-strip">
__STAMPS__
    </div>
  </div>
  <button class="pp-arrow pp-arrow-r hidden" id="places-arrow-r" type="button"
          aria-label="Scroll trips right">
    <svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>
  </button>
</div>

<div class="brief">
  <h4>…and a few brief stops</h4>
  <div class="chips">
__CHIPS__
  </div>
</div>

<script>
(function(){
  var PC = __PC_JSON__;
  var root = document.querySelector('.places-passport');
  if(!root) return;

  // Publish each target's fly box under its stable Strava activity id so the hero
  // can resolve a '#places?a=<id>' deep link on load (merged with the peaks payload).
  window.placesFlyTargets = window.placesFlyTargets || {};
  window.placesRouteCoords = window.placesRouteCoords || {};
  Object.keys(PC).forEach(function(s){
    var e = PC[s]; if(e && e.id && e.fly){ window.placesFlyTargets[e.id] = e.fly; }
    if(e && e.id && e.coords && e.coords.length){ window.placesRouteCoords[e.id] = e.coords; }
  });

  // grade -> color (cool descent blue, flat slate, warm climb amber) -- reuses
  // the dashboard's existing --accent / MTB tokens, not new hex. Colorblind-safe
  // cool/warm diverging pair (replaces the red/green scheme).
  function gradeColor(g){
    var D=[88,166,255], S=[139,148,158], C=[245,158,11], a, b, k;
    if(g<0){ a=S; b=D; k=Math.min(1,-g); } else { a=S; b=C; k=Math.min(1,g); }
    return 'rgb('+Math.round(a[0]+(b[0]-a[0])*k)+','+Math.round(a[1]+(b[1]-a[1])*k)+','
      +Math.round(a[2]+(b[2]-a[2])*k)+')';
  }

  function drawThumb(cv){
    var d = PC[cv.getAttribute('data-stamp')];
    if(!d || !d.path || d.path.length<4) return;
    var dpr=Math.min(window.devicePixelRatio||1,2);
    var w=cv.clientWidth, h=cv.clientHeight; if(!w||!h) return;
    cv.width=w*dpr; cv.height=h*dpr;
    var ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);
    var light = document.documentElement.classList.contains('light');
    ctx.clearRect(0,0,w,h);
    // faint graticule (theme-aware: light thumbnails read as light map windows)
    ctx.strokeStyle = light ? 'rgba(120,130,150,.16)' : 'rgba(88,120,170,.08)';
    ctx.lineWidth=1;
    for(var i=1;i<5;i++){ ctx.beginPath();ctx.moveTo(i/5*w,0);ctx.lineTo(i/5*w,h);ctx.stroke();
      ctx.beginPath();ctx.moveTo(0,i/5*h);ctx.lineTo(w,i/5*h);ctx.stroke(); }
    var P=d.path, N=P.length/2, grade=d.grade||[], elev=d.elev||[];
    // uniform-fit the route bbox into the upper region (aspect preserved)
    var mx=22, top=8, botLimit=h*0.66;
    var umin=1e9,umax=-1e9,vmin=1e9,vmax=-1e9;
    for(var q=0;q<N;q++){ var u=P[2*q],v=P[2*q+1];
      if(u<umin)umin=u; if(u>umax)umax=u; if(v<vmin)vmin=v; if(v>vmax)vmax=v; }
    var Wr=w-2*mx, Hr=botLimit-top;
    var S=Math.min(Wr/((umax-umin)||1e-6), Hr/((vmax-vmin)||1e-6));
    var ox=mx+(Wr-(umax-umin)*S)/2 - umin*S, oy=top+(Hr-(vmax-vmin)*S)/2 - vmin*S;
    function X(u){ return ox+u*S; } function Y(v){ return oy+v*S; }
    // Softer glow on the light ground (a heavy neon halo reads muddy on paper).
    ctx.lineJoin=ctx.lineCap='round'; ctx.lineWidth=2.4; ctx.shadowBlur = light ? 2 : 6;
    for(var k=1;k<N;k++){
      var col=gradeColor(grade[k]!=null?grade[k]:0); ctx.strokeStyle=col; ctx.shadowColor=col;
      ctx.beginPath(); ctx.moveTo(X(P[2*(k-1)]),Y(P[2*(k-1)+1]));
      ctx.lineTo(X(P[2*k]),Y(P[2*k+1])); ctx.stroke();
    }
    ctx.shadowBlur=0;
    // start/end nodes: dark ink on the light ground, near-white on the dark
    ctx.fillStyle = light ? 'rgba(28,33,40,.9)' : 'rgba(230,237,243,.9)';
    ctx.beginPath();ctx.arc(X(P[0]),Y(P[1]),2.6,0,6.283);ctx.fill();
    ctx.beginPath();ctx.arc(X(P[2*(N-1)]),Y(P[2*(N-1)+1]),2.6,0,6.283);ctx.fill();
    // violet elevation profile along the bottom
    if(elev.length>1){
      var bandH=h-(h*0.72)-6, me=elev.length;
      function ex(j){ return mx+(j/(me-1))*(w-2*mx); }
      function ey(j){ return h-6-elev[j]*bandH; }
      ctx.beginPath(); ctx.moveTo(mx,h-6);
      for(var j=0;j<me;j++) ctx.lineTo(ex(j),ey(j));
      ctx.lineTo(w-mx,h-6); ctx.closePath();
      ctx.fillStyle='rgba(167,139,250,.16)'; ctx.fill();
      ctx.strokeStyle='rgba(167,139,250,.55)'; ctx.lineWidth=1.3; ctx.beginPath();
      for(var j2=0;j2<me;j2++){ j2?ctx.lineTo(ex(j2),ey(j2)):ctx.moveTo(ex(j2),ey(j2)); }
      ctx.stroke();
    }
  }

  function drawAll(){ root.querySelectorAll('.thumb canvas').forEach(drawThumb); }
  var strip=document.getElementById('places-strip');
  if(window.ResizeObserver){ new ResizeObserver(drawAll).observe(strip); }
  window.addEventListener('resize', function(){ clearTimeout(window.__ppRt);
    window.__ppRt=setTimeout(drawAll,150); });
  // Redraw thumbnails when the page theme toggles (the .light class on <html>),
  // so their ground/nodes/glow re-tint like the hero.
  if(window.MutationObserver){
    new MutationObserver(drawAll).observe(document.documentElement,
      {attributes:true, attributeFilter:['class']});
  }
  drawAll();

  // click / keyboard -> fly the hero to this trip's box
  function fly(el){
    var d=PC[el.getAttribute('data-stamp')];
    if(d && d.fly && window.placesFlyTo){
      window.placesFlyTo(d.fly);
      if(d.id && window.placesLinkActivity){ window.placesLinkActivity(d.id); }
      var hero=document.getElementById('places-hero');
      if(hero && hero.scrollIntoView) hero.scrollIntoView({behavior:'smooth', block:'center'});
    }
  }
  var dragged=false;
  root.querySelectorAll('[data-stamp]').forEach(function(el){
    if(el.tagName==='CANVAS') return;
    el.addEventListener('click', function(){ if(!dragged) fly(el); });
    el.addEventListener('keydown', function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); fly(el); } });
  });

  // drag-to-scroll the filmstrip (suppress the click that ends a drag)
  var down=false, sx, sl;
  strip.addEventListener('pointerdown', function(e){ down=true; dragged=false;
    sx=e.clientX; sl=strip.scrollLeft; });
  strip.addEventListener('pointermove', function(e){
    if(!down) return;
    if(Math.abs(e.clientX-sx)>4){ dragged=true; strip.scrollLeft=sl-(e.clientX-sx); } });
  function up(){ down=false; setTimeout(function(){ dragged=false; },0); }
  strip.addEventListener('pointerup', up);
  strip.addEventListener('pointerleave', up);

  // explicit scroll arrows (desktop affordance; touch swipes natively)
  var reduce = matchMedia('(prefers-reduced-motion:reduce)').matches;
  var arL = document.getElementById('places-arrow-l');
  var arR = document.getElementById('places-arrow-r');
  function stepPx(){
    var s = strip.querySelector('.stamp');
    return s ? Math.round(s.getBoundingClientRect().width + 16) : Math.round(strip.clientWidth * 0.8);
  }
  function updateArrows(){
    if(!arL || !arR) return;
    var maxX = strip.scrollWidth - strip.clientWidth;
    var x = strip.scrollLeft;
    var noOverflow = maxX < 4;
    arL.classList.toggle('hidden', noOverflow || x <= 2);
    arR.classList.toggle('hidden', noOverflow || x >= maxX - 2);
  }
  function nudge(dir){
    strip.scrollBy({left: dir * stepPx(), behavior: reduce ? 'auto' : 'smooth'});
  }
  if(arL) arL.addEventListener('click', function(){ nudge(-1); });
  if(arR) arR.addEventListener('click', function(){ nudge(1); });
  strip.addEventListener('scroll', updateArrows, {passive:true});
  if(window.ResizeObserver){ new ResizeObserver(updateArrows).observe(strip); }
  updateArrows();
})();
</script>
</div>"""


# ─── Peaks record book HTML/CSS/JS (no mock; reuses the elevation-profile draw) ─
_PEAKS_TEMPLATE = r"""<div class="places-peaks">
<style>
  .places-peaks{margin-top:30px}
  .places-peaks .pk-eyebrow{font-family:'Geist Mono',ui-monospace,monospace; font-size:11px;
    letter-spacing:.28em; text-transform:uppercase; color:var(--text-tertiary); margin:0 0 4px}
  .places-peaks h3.pk-h{margin:0 0 18px; font-size:clamp(21px,3vw,30px); font-weight:600;
    letter-spacing:-.02em; color:var(--text-primary)}
  .places-peaks .peak-row{display:grid;
    grid-template-columns:minmax(96px,120px) 1fr 108px minmax(120px,150px);
    align-items:center; gap:18px; padding:16px 6px; border-top:1px solid var(--border);
    cursor:pointer; transition:background .16s}
  .places-peaks .peak-row:last-child{border-bottom:1px solid var(--border)}
  .places-peaks .peak-row:hover{background:var(--bg-glass)}
  .places-peaks .peak-row:focus-visible{outline:2px solid var(--accent); outline-offset:-2px}
  .places-peaks .peak-val{font-family:'Geist Mono',ui-monospace,monospace;
    font-size:clamp(20px,2.6vw,26px); font-weight:600; color:var(--text-primary);
    letter-spacing:-.01em; font-variant-numeric:tabular-nums}
  .places-peaks .peak-overline{font-family:'Geist Mono',ui-monospace,monospace; font-size:10px;
    letter-spacing:.16em; text-transform:uppercase; color:var(--text-tertiary); margin-bottom:4px}
  .places-peaks .peak-title{font-size:15px; color:var(--text-primary); line-height:1.3;
    text-wrap:pretty}
  .places-peaks .peak-spark{width:108px; height:38px; display:block}
  .places-peaks .peak-coord{font-family:'Geist Mono',ui-monospace,monospace; font-size:11.5px;
    color:var(--text-secondary); text-align:right; font-variant-numeric:tabular-nums}
  @media (max-width:640px){
    .places-peaks .peak-row{grid-template-columns:minmax(84px,100px) 1fr; gap:6px 14px;
      grid-template-areas:"val main" "spark coord"}
    .places-peaks .peak-val{grid-area:val} .places-peaks .peak-main{grid-area:main}
    .places-peaks .peak-spark{grid-area:spark; width:100px}
    .places-peaks .peak-coord{grid-area:coord; align-self:center}
  }
</style>

<p class="pk-eyebrow">Places · The Peaks</p>
<h3 class="pk-h">A short record book</h3>
__ROWS__

<script>
(function(){
  var PC = __PC_JSON__;
  var root = document.querySelector('.places-peaks');
  if(!root) return;

  // Publish each target's fly box under its stable Strava activity id so the hero
  // can resolve a '#places?a=<id>' deep link on load (merged with the passport payload).
  window.placesFlyTargets = window.placesFlyTargets || {};
  window.placesRouteCoords = window.placesRouteCoords || {};
  Object.keys(PC).forEach(function(s){
    var e = PC[s]; if(e && e.id && e.fly){ window.placesFlyTargets[e.id] = e.fly; }
    if(e && e.id && e.coords && e.coords.length){ window.placesRouteCoords[e.id] = e.coords; }
  });

  function drawSpark(cv){
    var d = PC[cv.getAttribute('data-stamp')];
    if(!d || !d.elev || d.elev.length<2) return;
    var elev=d.elev, dpr=Math.min(window.devicePixelRatio||1,2);
    var w=cv.clientWidth, h=cv.clientHeight; if(!w||!h) return;
    cv.width=w*dpr; cv.height=h*dpr;
    var ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,w,h);
    var pad=3, me=elev.length, bandH=h-2*pad;
    function ex(j){ return pad+(j/(me-1))*(w-2*pad); }
    function ey(j){ return h-pad-elev[j]*bandH; }
    ctx.beginPath(); ctx.moveTo(ex(0),h-pad);
    for(var j=0;j<me;j++) ctx.lineTo(ex(j),ey(j));
    ctx.lineTo(ex(me-1),h-pad); ctx.closePath();
    ctx.fillStyle='rgba(167,139,250,.16)'; ctx.fill();
    ctx.strokeStyle='rgba(167,139,250,.7)'; ctx.lineWidth=1.4; ctx.lineJoin='round';
    ctx.beginPath();
    for(var k=0;k<me;k++){ k?ctx.lineTo(ex(k),ey(k)):ctx.moveTo(ex(k),ey(k)); }
    ctx.stroke();
  }
  function drawAll(){ root.querySelectorAll('.peak-spark').forEach(drawSpark); }
  if(window.ResizeObserver){ new ResizeObserver(drawAll).observe(root); }
  window.addEventListener('resize', function(){ clearTimeout(window.__pkRt);
    window.__pkRt=setTimeout(drawAll,150); });
  drawAll();

  function fly(el){
    var d=PC[el.getAttribute('data-stamp')];
    if(d && d.fly && window.placesFlyTo){
      window.placesFlyTo(d.fly);
      if(d.id && window.placesLinkActivity){ window.placesLinkActivity(d.id); }
      var hero=document.getElementById('places-hero');
      if(hero && hero.scrollIntoView) hero.scrollIntoView({behavior:'smooth', block:'center'});
    }
  }
  root.querySelectorAll('.peak-row').forEach(function(el){
    el.addEventListener('click', function(){ fly(el); });
    el.addEventListener('keydown', function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); fly(el); } });
  });
})();
</script>
</div>"""
