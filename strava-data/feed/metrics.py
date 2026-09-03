"""Pure computations over the Strava CSVs. No rendering, no I/O beyond reads.

Every function returns plain dicts/floats so the same numbers feed the RSS
writer, the JSON export, and the SVG cards without diverging.

Units follow the repo's display policy: miles, feet, min/mi, mph, degrees F.
Data files stay metric; conversion happens here, once.
"""

import csv
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta

from nerd_common.format import maybe_float as mf

from .config import (
    ACT_CSV, ATHLETE_JSON, BIKE_TYPES, GEAR_JSON, KM_TO_MI, M_TO_FT,
    RUN_TYPES, SEG_CSV, STREAMS_DIR,
)

# A shoe with no notification_distance set still deserves a replacement bar.
DEFAULT_SHOE_LIMIT_MI = 400.0


# --- loading -------------------------------------------------------------

def _read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load():
    """Load everything the cards need, once, into one bundle."""
    acts = _read_csv(ACT_CSV)
    for r in acts:
        r["_dt"] = datetime.strptime(r["start_date_local"], "%Y-%m-%d %H:%M:%S")
        r["_date"] = r["_dt"].date()
        r["_mi"] = (mf(r["distance_km"]) or 0.0) * KM_TO_MI
        r["_ft"] = (mf(r["total_elevation_gain_m"]) or 0.0) * M_TO_FT
    acts.sort(key=lambda r: r["_dt"])

    segs = _read_csv(SEG_CSV) if os.path.exists(SEG_CSV) else []

    with open(GEAR_JSON, encoding="utf-8") as f:
        gear = json.load(f)
    with open(ATHLETE_JSON, encoding="utf-8") as f:
        athlete = json.load(f)

    return {
        "acts": acts,
        "segs": segs,
        "gear": gear,
        "athlete": athlete,
        # "Today" is the last day with data, not the wall clock: the fetch runs
        # on a cron, so a wall-clock "days since" would drift with the schedule
        # rather than describing the athlete.
        "asof": acts[-1]["_date"] if acts else date.today(),
    }


# --- small helpers -------------------------------------------------------

def is_run(r):
    return r["sport_type"] in RUN_TYPES


def is_bike(r):
    return r["sport_type"] in BIKE_TYPES


def window(acts, asof, days):
    """Activities in the ``days``-day window ending at ``asof`` (inclusive)."""
    start = asof - timedelta(days=days - 1)
    return [r for r in acts if start <= r["_date"] <= asof]


# --- metrics -------------------------------------------------------------

def totals(acts, pred=None):
    rows = [r for r in acts if pred(r)] if pred else acts
    return {
        "n": len(rows),
        "mi": sum(r["_mi"] for r in rows),
        "ft": sum(r["_ft"] for r in rows),
        "hours": sum((mf(r["moving_time_min"]) or 0.0) for r in rows) / 60.0,
    }


def acwr(acts, asof):
    """Acute:chronic workload ratio from daily suffer score (7d mean / 28d mean).

    Same quantity the dashboard's V8 "Load, Monotony & the Spike Zone" chart
    plots, reduced to the single number you'd actually glance at.
    """
    day = Counter()
    for r in acts:
        s = mf(r["suffer_score"])
        if s:
            day[r["_date"]] += s

    def mean(n):
        return sum(day.get(asof - timedelta(days=i), 0.0) for i in range(n)) / n

    acute, chronic = mean(7), mean(28)
    ratio = acute / chronic if chronic else None
    if ratio is None:
        band = "no data"
    elif ratio < 0.8:
        band = "detrained"
    elif ratio <= 1.3:
        band = "steady"
    elif ratio <= 1.5:
        band = "spiking"
    else:
        band = "danger"
    return {"acute": acute, "chronic": chronic, "ratio": ratio, "band": band}


def streaks(acts, asof):
    days = sorted({r["_date"] for r in acts})
    dayset = set(days)

    cur, probe = 0, asof
    while probe in dayset:
        cur += 1
        probe -= timedelta(days=1)

    best, run = (1, 1) if days else (0, 0)
    for a, b in zip(days, days[1:]):
        run = run + 1 if (b - a).days == 1 else 1
        best = max(best, run)

    span = (days[-1] - days[0]).days + 1 if days else 0
    return {
        "current": cur,
        "longest": best,
        "active_days": len(days),
        "span_days": span,
        "days_since": (asof - days[-1]).days if days else None,
        "dayset": dayset,
    }


def last_30_strip(acts, asof):
    """30 booleans, oldest first, one per day: was there an activity?"""
    dayset = {r["_date"] for r in acts}
    return [(asof - timedelta(days=29 - i)) in dayset for i in range(30)]


def shoes(gear, acts):
    """Non-retired shoes with a replacement threshold and how far past it."""
    out = []
    used = Counter(r["gear_id"] for r in acts if r.get("gear_id"))
    for gid, g in gear.items():
        if not gid.startswith("g") or g.get("retired"):
            continue
        # notification_distance comes back in the athlete's *display* units,
        # i.e. miles here - the values (400, 450, 0) only make sense against a
        # 470-mile shoe that way. 0 means the reminder was never set.
        limit_mi = g.get("notification_distance") or DEFAULT_SHOE_LIMIT_MI
        mi = g.get("converted_distance") or 0.0   # already miles - a units trap
        out.append({
            "id": gid,
            # nickname is often a fragment ("- New shoes"); name is the full
            # "ASICS DS Trainer - New shoes" and reads better on its own.
            "name": g.get("name") or g.get("nickname") or gid,
            "mi": mi,
            "limit_mi": limit_mi,
            "frac": mi / limit_mi if limit_mi else 0.0,
            "over": mi > limit_mi,
            "runs": used.get(gid, 0),
        })
    out.sort(key=lambda s: -s["frac"])
    return out


def latest_pr(segs, asof):
    """The most recent segment PR, plus how many were set in trailing windows."""
    dated = []
    for s in segs:
        if not s.get("pr_date"):
            continue
        try:
            d = datetime.strptime(s["pr_date"][:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        dated.append((d, s))
    if not dated:
        return None
    dated.sort(key=lambda p: p[0], reverse=True)

    counts = {w: sum(1 for d, _ in dated if (asof - d).days < w) for w in (30, 90, 365)}
    d, s = dated[0]
    return {
        "date": d,
        "name": s["segment_name"],
        "best_s": int(float(s["best_time_s"])),
        "efforts": int(s["effort_count"]),
        "counts": counts,
    }


def title_of_day(acts, ordinal):
    """A deterministic pick from the activities that have a description.

    Rotates by date so the panel changes daily with no device-side state.
    """
    told = [r for r in acts if (r.get("description") or "").strip()]
    if not told:
        told = acts
    return told[ordinal % len(told)] if told else None


def route_of_day(acts, ordinal, max_points=180):
    """A deterministic GPS activity, its path normalised into a 0..1 box.

    Reads one streams file only - the whole streams dir is 42 MB and a card
    that needs one route should not pay for all of it.
    """
    gps = [r for r in acts if os.path.exists(os.path.join(STREAMS_DIR, f"{r['id']}.csv"))]
    if not gps:
        return None
    act = gps[ordinal % len(gps)]

    pts = []
    with open(os.path.join(STREAMS_DIR, f"{act['id']}.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            lat, lng = mf(row.get("lat")), mf(row.get("lng"))
            if lat is not None and lng is not None:
                pts.append((lng, lat))
    if len(pts) < 8:
        return None

    if len(pts) > max_points:
        step = len(pts) / max_points
        pts = [pts[int(i * step)] for i in range(max_points)]

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    # Latitude degrees are ~1/cos(lat) wider than longitude degrees on the
    # ground; without this the route comes out squashed.
    import math
    coslat = math.cos(math.radians((y0 + y1) / 2)) or 1.0
    w = max((x1 - x0) * coslat, 1e-9)
    h = max(y1 - y0, 1e-9)
    scale = max(w, h)
    # Normalise so the dominant axis spans 0..1 and report the other axis's
    # extent, rather than letterboxing into a square. A wide, flat route can
    # then be scaled to fill the card's rectangle instead of being penned into
    # the middle third of a square.
    path = [((x - x0) * coslat / scale, (h - (y - y0)) / scale) for x, y in pts]
    return {"act": act, "path": path, "w": w / scale, "h": h / scale}


def everest(acts):
    ft = sum(r["_ft"] for r in acts)
    return {"ft": ft, "multiple": ft / 29032.0}


def ytd_compare(acts, asof):
    """Year-to-date miles vs the same calendar date one year earlier."""
    def upto(year):
        return sum(r["_mi"] for r in acts
                   if r["_dt"].year == year
                   and (r["_dt"].month, r["_dt"].day) <= (asof.month, asof.day))
    return {"year": asof.year, "this": upto(asof.year), "last": upto(asof.year - 1)}
