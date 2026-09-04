"""Pure computations over the Strava CSVs. No rendering, no I/O beyond reads.

Every function returns plain dicts/floats so the same numbers feed the RSS
writer, the JSON export, and the SVG cards without diverging.

Units follow the repo's display policy: miles, feet, min/mi, mph, degrees F.
Data files stay metric; conversion happens here, once.
"""

import csv
import json
import os
import re
from collections import Counter
from datetime import date, datetime, timedelta

from nerd_common.format import maybe_float as mf

from .config import (
    ACT_CSV, ATHLETE_JSON, BIKE_TYPES, GEAR_JSON, KM_TO_MI, M_TO_FT,
    RUN_TYPES, RUNLOG_CSV, SEG_CSV, SEG_EFF_CSV, STREAMS_DIR,
)

# A shoe with no notification_distance set still deserves a replacement bar.
DEFAULT_SHOE_LIMIT_MI = 400.0


# --- loading -------------------------------------------------------------

def _read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _read_runlog():
    """The 2003-2007 paper-era log, typed and dated. Empty if the CSV is gone.

    ``week_of_year`` in the file is already the ISO week, so ``(year, week)``
    joins straight onto ``date.isocalendar()`` for the then-and-now cards.
    """
    if not os.path.exists(RUNLOG_CSV):
        return []
    rows = _read_csv(RUNLOG_CSV)
    out = []
    for r in rows:
        try:
            r["_date"] = datetime.strptime(r["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        r["_mi"] = mf(r.get("miles")) or 0.0
        r["_pace"] = mf(r.get("pace_min_per_mile"))
        r["_week"] = (int(r["year"]), int(r["week_of_year"]))
        r["_race"] = r.get("is_race") == "1"
        out.append(r)
    out.sort(key=lambda r: r["_date"])
    return out


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
    runlog = _read_runlog()

    with open(GEAR_JSON, encoding="utf-8") as f:
        gear = json.load(f)
    with open(ATHLETE_JSON, encoding="utf-8") as f:
        athlete = json.load(f)

    return {
        "acts": acts,
        "segs": segs,
        "efforts": efforts,
        "runlog": runlog,
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


# (pattern, label). Matched whole-word with an optional plural, not as a
# substring: "owl" is inside "slowly" and "seal" inside "sealed", and the
# substring test that shipped first counted both as sightings. Order fixes the
# label a multi-word pattern reports under.
ANIMALS = [
    (r"coyote", "Coyote"),
    (r"snake|rattler", "Snake"),
    (r"owl", "Owl"),
    (r"mule deer|deer", "Deer"),
    (r"quail", "Quail"),
    (r"lizard", "Lizard"),
    (r"hawk", "Hawk"),
    (r"bobcat", "Bobcat"),
    (r"roadrunner", "Roadrunner"),
    (r"turkey", "Turkey"),
    (r"rabbit|bunny", "Rabbit"),
    (r"tarantula", "Tarantula"),
    (r"skunk", "Skunk"),
    (r"heron", "Heron"),
    (r"seal", "Seal"),
    (r"dolphin", "Dolphin"),
    (r"whale", "Whale"),
    (r"fox", "Fox"),
]

_ANIMAL_RX = [(re.compile(rf"\b(?:{rx})s?\b", re.I), label) for rx, label in ANIMALS]


def animal_hits(r):
    """Species labels mentioned in one activity's name or description."""
    blob = f"{r.get('name', '')} {r.get('description', '')}"
    return [label for rx, label in _ANIMAL_RX if rx.search(blob)]


def animal_sightings(acts):
    """Activities mentioning wildlife, newest first, plus a species tally.

    ``last_seen`` keeps the most recent activity per species, which is what
    the scoreboard's footer reports.
    """
    hits = []
    last_seen = {}
    for r in acts:                      # acts arrive oldest-first
        found = animal_hits(r)
        if found:
            hits.append((r, found))
            for label in found:
                last_seen[label] = r
    counts = Counter(a for _, found in hits for a in found)
    return {"hits": list(reversed(hits)), "counts": counts.most_common(),
            "n": len(hits), "last_seen": last_seen,
            "total": sum(counts.values())}


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


# --- metrics added for the merged card set -------------------------------

def segment_of_month(efforts, segs, asof, days=30):
    """The segment ridden/run most in the ``days`` before ``asof``.

    Ties break on total lifetime efforts, so a segment done twice this month
    and two hundred times overall beats one done twice ever.
    """
    by_id = {s["segment_id"]: s for s in segs}
    cutoff = (asof - timedelta(days=days - 1)).isoformat()
    recent = Counter(e["segment_id"] for e in efforts
                     if e["start_date_local"][:10] >= cutoff and e["segment_id"] in by_id)
    if not recent:
        return None
    sid, n30 = max(recent.items(),
                   key=lambda kv: (kv[1], int(by_id[kv[0]].get("effort_count") or 0)))
    seg = by_id[sid]

    mine = sorted((e for e in efforts if e["segment_id"] == sid),
                  key=lambda e: e["start_date_local"])
    times = [mf(e["elapsed_time_s"]) for e in mine]
    times = [t for t in times if t]
    if not times:
        return None
    trend = mf(seg.get("recent_trend"))
    return {
        "seg": seg,
        "name": seg["segment_name"].strip(),
        "n30": n30,
        "efforts": mine,
        "times": times,
        "best_s": min(times),
        "latest_s": times[-1],
        "worst_s": max(times),
        "trend": trend,
        # recent_trend is a percentage and negative is faster.
        "trend_word": ("faster lately" if trend is not None and trend < -1 else
                       "slower lately" if trend is not None and trend > 1 else
                       "holding steady"),
        "sport": mine[-1]["sport_type"],
        "mi": (mf(seg["segment_distance_m"]) or 0.0) / 1000.0 * KM_TO_MI,
        "grade": mf(seg["segment_avg_grade"]) or 0.0,
        "where": ", ".join(x for x in (seg.get("segment_city"), seg.get("segment_state")) if x),
        "total": int(seg.get("effort_count") or 0),
        "avg_hr": mf(seg.get("avg_heartrate")),
        "first": (seg.get("first_effort") or "")[:10],
    }


# Strava's own auto-generated names: "Morning Run", "Evening Mountain Bike
# Ride". A hall of fame of those would be a hall of fame of nothing.
DEFAULT_NAME = re.compile(
    r"^(Morning|Afternoon|Lunch|Evening|Night)\s+"
    r"(Run|Ride|Mountain Bike Ride|Pickleball|Weight Training|Rock Climb|Hike|"
    r"Walk|Workout|.*Ski|Ice Skate|Snowboard|Pilates)$")

_PUNCT = re.compile(r"[!?,'\"]")
_NON_ASCII = re.compile(r"[^\x00-\x7f]")


def name_score(r):
    """How much personality an activity title has. Punctuation and emoji are
    the tell: a named run is a story, a default one is a timestamp."""
    n = r.get("name") or ""
    return (len(_PUNCT.findall(n)) * 3
            + min(len(n), 40) / 8
            + (int(r["kudos_count"]) if (r.get("kudos_count") or "").isdigit() else 0) / 2
            + (2 if _NON_ASCII.search(n) else 0))


def named_activities(acts):
    """Activities the athlete actually named, best-scoring first."""
    named = [r for r in acts
             if (r.get("name") or "").strip()
             and not DEFAULT_NAME.match(r["name"].strip())
             and r["name"].strip() != "Warm Up"]
    return sorted(named, key=name_score, reverse=True)


def uv_week(acts, asof):
    """UV dose for the ISO week of ``asof``: sum of uv_index x moving hours.

    Only 339 of 374 activities carry a UV value; the rest are indoor or
    predate the field, and are excluded rather than counted as zero.
    """
    year, week, _ = asof.isocalendar()
    monday = asof - timedelta(days=asof.weekday())
    days = [0.0] * 7
    rows = []
    for r in acts:
        if r["_date"].isocalendar()[:2] != (year, week):
            continue
        uv = mf(r.get("uv_index"))
        if uv is None:
            continue
        hours = (mf(r["moving_time_min"]) or 0.0) / 60.0
        days[r["_date"].weekday()] += uv * hours
        rows.append((uv, r))
    peak = max(rows, key=lambda p: p[0]) if rows else None
    return {"days": days, "total": sum(days), "n": len(rows),
            "monday": monday, "week": week, "year": year,
            "peak_uv": peak[0] if peak else None,
            "peak_act": peak[1] if peak else None}


def runlog_week(runlog, iso_week):
    """Paper-era log rows for one ``(year, week)``, in date order."""
    return [r for r in runlog if r["_week"] == iso_week]


def race_anniversary(runlog, today):
    """A race from the old log falling near ``today``'s calendar date.

    Deliberately keyed to the **build date**, not to ``asof``: an anniversary
    that arrived while the fetch cron was asleep is still an anniversary. Picks
    the nearest race within +/-7 days, else the next one coming up.
    """
    races = [r for r in runlog if r["_race"] and (r.get("race_name") or "").strip()]
    if not races:
        return None

    def offset(r):
        """Days from today to this race's month-day, wrapped into -182..183."""
        d = r["_date"]
        try:
            this_year = date(today.year, d.month, d.day)
        except ValueError:                      # 29 February in a common year
            this_year = date(today.year, d.month, 28)
        n = (this_year - today).days
        return n - 365 if n > 183 else n + 365 if n < -182 else n

    near = [(offset(r), r) for r in races]
    within = [p for p in near if abs(p[0]) <= 7]
    if within:
        # Nearest first; a race on the day itself wins over one three days out.
        delta, race = min(within, key=lambda p: (abs(p[0]), p[0]))
    else:
        upcoming = [p for p in near if p[0] > 0] or near
        delta, race = min(upcoming, key=lambda p: p[0])

    years = today.year - race["_date"].year
    if delta == 0:
        when = f"{years} years ago today" if years else "today"
    elif delta > 0:
        when = f"in {delta} day{'s' if delta != 1 else ''}"
    else:
        n = -delta
        when = f"{n} day{'s' if n != 1 else ''} ago"
    return {"race": race, "delta": delta, "years": years, "when": when,
            "name": race["race_name"].strip(),
            "distance": (race.get("race_distance") or "").strip(),
            "time": (race.get("race_time") or "").strip(),
            "comments": (race.get("comments") or "").strip()}


# --- haiku ---------------------------------------------------------------
# Five-seven-five from the newest activity's own numbers. No model, no
# network: a fixed vocabulary, a dozen templates per line, and a syllable
# count that decides which of them are legal today. Seeded by the activity id,
# so the same ride always writes the same poem.

_NUMBER_WORDS = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
]

_VOWEL_RUN = re.compile(r"[aeiouy]+")
_VOWELS = "aeiouy"

# Words the vowel-group rule below gets wrong. Small on purpose: the card's
# vocabulary is fixed, so the exceptions are enumerable rather than guessed at.
_SYLLABLE_LEXICON = {
    "thirteen": 2, "fourteen": 2, "fifteen": 2, "sixteen": 2, "seventeen": 3,
    "eighteen": 2, "nineteen": 2, "going": 2, "being": 2, "doing": 2,
    "hour": 1, "quail": 1, "coyote": 3, "roadrunner": 3,
}


def _syllables_word(word):
    w = word.lower().strip("'")
    if not w:
        return 0
    if w in _SYLLABLE_LEXICON:
        return _SYLLABLE_LEXICON[w]
    # "-es" after a sibilant is its own syllable ("watches"); elsewhere it is
    # just a plural and the "e" is silent ("miles").
    extra = 0
    if w.endswith(("ses", "zes", "xes", "ges", "ches", "shes")):
        w, extra = w[:-2], 1
    elif w.endswith("es") and not w.endswith("ies"):
        w = w[:-1]
    elif w.endswith("s") and not w.endswith(("ss", "us", "is")):
        w = w[:-1]
    # Silent "-ed": "logged", "moved" -- but not "wanted", "faded".
    if w.endswith("ed") and len(w) > 3 and w[-3] not in "td":
        w = w[:-2] or w
    n = len(_VOWEL_RUN.findall(w))
    if w.endswith("e") and n > 1:
        # "-le" is a syllable of its own after a consonant ("little") but not
        # after a vowel ("mile").
        syllabic_le = w.endswith("le") and len(w) > 2 and w[-3] not in _VOWELS
        if not (syllabic_le or w.endswith(("ee", "ye", "oe"))):
            n -= 1
    return max(n, 1) + extra


def syllables(text):
    """Vowel-group syllable count, the standard cheap English approximation.

    Verified against every word in the card's own vocabulary; the lexicon
    above carries the handful it would otherwise miss. Good enough that a
    5-7-5 assembled from that vocabulary actually scans when read aloud,
    which is the whole bar here.
    """
    return sum(_syllables_word(w) for w in re.findall(r"[a-z']+", text.lower()))


def _number_word(x):
    n = int(round(x))
    return _NUMBER_WORDS[n] if 0 <= n < len(_NUMBER_WORDS) else str(n)


def _temp_word(f):
    if f is None:
        return None
    if f < 45:
        return "cold"
    if f < 60:
        return "cool"
    if f < 75:
        return "mild"
    if f < 88:
        return "warm"
    return "hot"


_SUFFER_WORDS = [(30, "easy"), (60, "steady"), (100, "hard"), (150, "brutal"),
                 (10 ** 9, "savage")]

# Three banks of templates. Each is written at several fixed-word lengths on
# purpose: the substituted words vary from one to four syllables ("hot" vs
# "savage", "six" vs "seventeen", "owl" vs "tarantula"), so a bank of one
# phrasing per idea would collapse onto the two or three that happen to scan
# today. Several in each bank use no variable at all and always fit.
_LINE1 = [
    "{Temp} light on the trail", "{Temp} air, moving legs", "{Temp} wind, and the dust",
    "{Temp} morning, and dust", "{Temp} sun on the road", "The trail is {suffer}",
    "The {sport} was {suffer}", "The {suffer} {sport} ends", "A {suffer} {sport} home",
    "{Number} miles before dawn", "{Number} miles of {sport}", "{Number} miles in the {temp}",
    "{Number} {sport} miles logged", "Out for {number} miles now",
    "The {sport} begins now", "{Sport}, and nothing else",
    "The {noun} in the brush", "A {noun} on the road",
]
_LINE2 = [
    "{temp} wind and the sound of breath", "a {temp} wind, and the long road",
    "the {temp} air, the same old road", "the road, the {temp} wind, the light",
    "{temp} morning, then the long climb", "nothing but the {temp} wind now",
    "the light goes gold on the hills", "the hills give nothing away",
    "the legs remember the climb", "one long shadow on the road",
    "breathing, and the road, and dust", "{number} miles of {suffer} breathing",
    "{number} miles under {temp} skies", "{number} miles, and the {temp} wind",
    "{number} miles, and the legs held on", "a {suffer} hour, and nothing more",
    "a {suffer} {sport}, honestly logged", "the {sport} was {suffer} today",
    "the {noun} watches from the brush", "a {noun} crossed the road ahead",
]
_LINE3 = [
    "The legs remember", "Nothing else to say", "The trail keeps its own",
    "Home before the heat", "Log it and move on", "Breathing, and the road",
    "Enough for today", "Nothing to prove here", "The road, and then home",
    "{Temp} air, then coffee", "{Temp} wind at the door", "{Temp} light, and the dust",
    "A {suffer} good day", "The {sport} was enough", "{Number} miles, all of them",
    "The {noun} is still there", "The {noun}, and the dust",
]


def _article(line):
    """Fix "a easy run" -> "an easy run". Both are one syllable, so this can
    run after the templates are chosen without disturbing the count."""
    return re.sub(r"\b([Aa]) (?=[aeiouAEIOU])", lambda m: m.group(1) + "n ", line)


def haiku(act, sightings=None):
    """A 5-7-5 built from one activity, chosen deterministically by its id.

    ``sightings`` is the wildlife tally, so a run that saw a coyote can say so.
    """
    if not act:
        return None
    mi = act["_mi"]
    temp_c = mf(act.get("average_temp_c"))
    temp = _temp_word(temp_c * 9 / 5 + 32 if temp_c is not None else None) or "still"
    suffer = mf(act.get("suffer_score"))
    suffer_word = next(w for lim, w in _SUFFER_WORDS if (suffer or 0) < lim)
    sport = ("trail run" if act["sport_type"] == "TrailRun" else
             "ride" if act["sport_type"] in BIKE_TYPES else "run")
    # Only this activity's own sightings. With none, the {noun} templates drop
    # out entirely rather than defaulting to a plausible animal: the card would
    # otherwise claim a hawk that nobody saw.
    nouns = (sightings or {}).get(str(act["id"])) or []

    seed = int(act["id"]) if str(act["id"]).isdigit() else abs(hash(act["id"]))
    ctx = {"sport": sport, "Sport": sport.capitalize(),
           "temp": temp, "Temp": temp.capitalize(),
           "suffer": suffer_word,
           "number": _number_word(mi), "Number": _number_word(mi).capitalize(),
           "noun": nouns[seed % len(nouns)].lower() if nouns else ""}

    lines = []
    for i, (bank, target) in enumerate(((_LINE1, 5), (_LINE2, 7), (_LINE3, 5))):
        usable = [t for t in bank
                  if (nouns or "{noun}" not in t)
                  # A gym session has no miles; "Zero run miles logged" is a
                  # worse line than simply not counting them.
                  and (mi >= 0.5 or "{number}" not in t.lower())]
        rendered = [_article(t.format(**ctx)) for t in usable]
        # Rotate the bank by the seed, then take the first line that scans.
        # A different offset per line keeps the three from moving in lockstep.
        off = (seed // (10 ** i)) % len(usable)
        order = rendered[off:] + rendered[:off]
        fits = [s for s in order if syllables(s) == target]
        lines.append(fits[0] if fits else
                     min(order, key=lambda s: abs(syllables(s) - target)))
    return {"lines": lines, "act": act,
            "counts": [syllables(s) for s in lines],
            "exact": all(syllables(s) == t for s, t in zip(lines, (5, 7, 5)))}
