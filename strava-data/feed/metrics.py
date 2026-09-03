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
    RUN_TYPES, SEG_CSV, SEG_EFF_CSV, STREAMS_DIR,
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
    efforts = _read_csv(SEG_EFF_CSV) if os.path.exists(SEG_EFF_CSV) else []

    with open(GEAR_JSON, encoding="utf-8") as f:
        gear = json.load(f)
    with open(ATHLETE_JSON, encoding="utf-8") as f:
        athlete = json.load(f)

    return {
        "acts": acts,
        "segs": segs,
        "efforts": efforts,
        "gear": gear,
        "athlete": athlete,
        # "Today" is the last day with data, not the wall clock: the fetch runs
        # on a cron, so a wall-clock "days since" would drift with the schedule
        # rather than describing the athlete.
        "asof": acts[-1]["_date"] if acts else date.today(),
    }


# --- small helpers -------------------------------------------------------

def activity_by_id(acts):
    """Activities keyed by string id, for joining segment efforts."""
    return {str(r["id"]): r for r in acts}


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


# --- metrics added for the full card catalogue ---------------------------

def rest_days(acts, asof):
    """Days since the last full rest day, and the longest rest gap ever."""
    days = sorted({r["_date"] for r in acts})
    dayset = set(days)
    since, probe = 0, asof
    while probe in dayset:
        since += 1
        probe -= timedelta(days=1)
    gaps = [(b - a).days - 1 for a, b in zip(days, days[1:]) if (b - a).days > 1]
    return {"since_rest": since, "longest_gap": max(gaps) if gaps else 0,
            "rest_days": sum(gaps)}


def by_weekday(acts):
    """Activity count and miles per weekday, Monday first."""
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]
    n = Counter()
    mi = Counter()
    for r in acts:
        k = r["_dt"].weekday()
        n[k] += 1
        mi[k] += r["_mi"]
    return [(names[i], n[i], mi[i]) for i in range(7)]


def week_shape(acts, asof, weeks_back=8):
    """This week's miles per weekday against the median of recent weeks."""
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    this_start = asof - timedelta(days=asof.weekday())
    cur = [0.0] * 7
    hist = [[] for _ in range(7)]
    for r in acts:
        d = r["_date"]
        if d >= this_start:
            cur[d.weekday()] += r["_mi"]
        elif (this_start - d).days <= weeks_back * 7:
            hist[d.weekday()].append(r["_mi"])
    med = [sorted(h)[len(h) // 2] if h else 0.0 for h in hist]
    return list(zip(names, cur, med))


def monthly_miles(acts, months=13):
    """Trailing calendar months as ``(label, miles)``, oldest first."""
    m = Counter()
    for r in acts:
        m[(r["_dt"].year, r["_dt"].month)] += r["_mi"]
    keys = sorted(m)[-months:]
    return [(f"{y}-{mo:02d}", m[(y, mo)]) for y, mo in keys]


def sport_split(acts, asof, days=365):
    """Activity counts by sport in a trailing window, biggest first."""
    c = Counter(r["sport_type"] for r in window(acts, asof, days))
    return c.most_common()


def hour_histogram(acts):
    c = Counter(r["_dt"].hour for r in acts)
    return [(h, c.get(h, 0)) for h in range(24)]


def segment_leaderboard(segs, top=5):
    rows = sorted(segs, key=lambda s: -int(s["effort_count"]))[:top]
    return [{"name": s["segment_name"].strip(), "n": int(s["effort_count"]),
             "best_s": int(float(s["best_time_s"])),
             "trend": mf(s["recent_trend"])} for s in rows]


def segment_trends(segs, min_efforts=5):
    """Segments with enough history to have a meaningful trend, best first.

    ``recent_trend`` is a percentage: negative is faster. Only 266 of 751
    segments have one at all - the rest are single-effort.
    """
    rows = [s for s in segs
            if s.get("recent_trend") and int(s["effort_count"]) >= min_efforts]
    rows.sort(key=lambda s: mf(s["recent_trend"]))
    return [{"name": s["segment_name"].strip(), "trend": mf(s["recent_trend"]),
             "n": int(s["effort_count"])} for s in rows]


def bikes(gear):
    out = [dict(g, id=gid) for gid, g in gear.items()
           if gid.startswith("b") and not g.get("retired")]
    out.sort(key=lambda g: -(g.get("converted_distance") or 0))
    return out


def retired_gear(gear):
    return [dict(g, id=gid) for gid, g in gear.items() if g.get("retired")]


def temps(acts):
    """Temperature extremes in Fahrenheit, and the activities that set them."""
    rows = [(mf(r["average_temp_c"]), r) for r in acts if mf(r["average_temp_c"]) is not None]
    if not rows:
        return None
    rows.sort(key=lambda p: p[0])
    to_f = lambda c: c * 9 / 5 + 32
    return {"min_f": to_f(rows[0][0]), "min_act": rows[0][1],
            "max_f": to_f(rows[-1][0]), "max_act": rows[-1][1], "n": len(rows)}


def uv_max(acts):
    rows = [(mf(r["uv_index"]), r) for r in acts if mf(r["uv_index"]) is not None]
    if not rows:
        return None
    uv, act = max(rows, key=lambda p: p[0])
    return {"uv": uv, "act": act, "n": len(rows)}


def longest(acts, pred, key="_mi"):
    rows = [r for r in acts if pred(r)]
    return max(rows, key=lambda r: r[key]) if rows else None


def top_kudos(acts):
    rows = [r for r in acts if (r.get("kudos_count") or "").isdigit()]
    return max(rows, key=lambda r: int(r["kudos_count"])) if rows else None


def on_this_day(acts, asof):
    """Prior-year activities on the same calendar day, most recent first."""
    return sorted([r for r in acts
                   if (r["_dt"].month, r["_dt"].day) == (asof.month, asof.day)
                   and r["_dt"].year < asof.year],
                  key=lambda r: r["_dt"], reverse=True)


def year_ago_week(acts, asof):
    """The same week one year back - far denser than a single calendar day."""
    target = asof - timedelta(days=365)
    lo, hi = target - timedelta(days=3), target + timedelta(days=3)
    return sorted([r for r in acts if lo <= r["_date"] <= hi], key=lambda r: r["_dt"])


ANIMALS = ("coyote", "deer", "rabbit", "bunny", "snake", "rattler", "hawk",
           "lizard", "tarantula", "bobcat", "skunk", "owl", "heron", "seal",
           "dolphin", "whale", "turkey", "fox", "mule deer")


def animal_sightings(acts):
    """Descriptions and titles mentioning wildlife, newest first."""
    hits = []
    for r in acts:
        blob = f"{r.get('name', '')} {r.get('description', '')}".lower()
        found = sorted({a for a in ANIMALS if a in blob})
        if found:
            hits.append((r, found))
    counts = Counter(a for _, found in hits for a in found)
    return {"hits": list(reversed(hits)), "counts": counts.most_common(), "n": len(hits)}


def emoji_titles(acts):
    """Titles that are entirely non-ASCII symbols - pure emoji names."""
    out = []
    for r in acts:
        name = (r.get("name") or "").strip()
        if name and all(ord(ch) > 0x2000 or ch.isspace() for ch in name):
            out.append(r)
    return out


def devices(acts):
    return Counter(r.get("device_name") or "unknown" for r in acts).most_common()


def dataset_stats(acts):
    n_streams = len([f for f in os.listdir(STREAMS_DIR) if f.endswith(".csv")]) \
        if os.path.isdir(STREAMS_DIR) else 0
    size_mb = sum(os.path.getsize(os.path.join(STREAMS_DIR, f))
                  for f in os.listdir(STREAMS_DIR) if f.endswith(".csv")) / 1e6 \
        if os.path.isdir(STREAMS_DIR) else 0.0
    return {"acts": len(acts), "streams": n_streams, "mb": size_mb}


def laps_for(act):
    """Lap splits for one activity, or None. 79 of 374 files hold a single
    whole-activity lap, so plenty of activities have nothing to show."""
    path = os.path.join(os.path.dirname(STREAMS_DIR), "laps", f"{act['id']}.csv")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return rows if len(rows) > 1 else None


def last_with_laps(acts):
    for r in reversed(acts):
        if laps_for(r):
            return r
    return None


def route_for(act, max_points=180):
    """Normalised path for one specific activity, or None."""
    from .places import normalise
    path = os.path.join(STREAMS_DIR, f"{act['id']}.csv")
    if not os.path.exists(path):
        return None
    pts = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            lat, lng = mf(row.get("lat")), mf(row.get("lng"))
            if lat is not None and lng is not None:
                pts.append((lng, lat))
    if len(pts) < 8:
        return None
    if len(pts) > max_points:
        step = len(pts) / max_points
        pts = [pts[int(i * step)] for i in range(max_points)]
    return normalise(pts)


def segment_pace_by_grade(efforts, act_by_id):
    """Per-segment average pace (min/mi) against grade, split run vs MTB.

    Feeds the crossover card: the grade at which running overtakes riding.
    """
    from collections import defaultdict
    groups = defaultdict(lambda: defaultdict(list))
    meta = {}
    for e in efforts:
        act = act_by_id.get(str(e["activity_id"]))
        if not act:
            continue
        sport = act["sport_type"]
        group = "run" if sport in RUN_TYPES else ("bike" if sport in BIKE_TYPES else None)
        dist = mf(e["segment_distance_m"])
        secs = mf(e["elapsed_time_s"])
        grade = mf(e["segment_avg_grade"])
        if not group or not dist or not secs or grade is None or dist < 100:
            continue
        groups[group][e["segment_id"]].append((secs, dist))
        meta[e["segment_id"]] = grade
    out = {}
    for group, segs in groups.items():
        xs, ys = [], []
        for sid, vals in segs.items():
            mean_s = sum(v[0] for v in vals) / len(vals)
            dist_mi = vals[0][1] * KM_TO_MI / 1000.0
            if dist_mi <= 0:
                continue
            xs.append(meta[sid])
            ys.append(mean_s / 60.0 / dist_mi)
        out[group] = (xs, ys)
    return out
