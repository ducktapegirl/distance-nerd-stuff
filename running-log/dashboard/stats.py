"""Headline stats, race-record extraction, and PR-card computation."""

from collections import defaultdict
from datetime import date

from dashboard.config import EASY_COLOR, LONG_COLOR, RACE_COLOR, TEMPO_COLOR, WORKOUT_COLOR
from dashboard.data import classify_race, maybe_float, normalize_distance, parse_time_seconds, season_label


def compute_stats(rows):
    total_miles = 0.0
    active_days = set()
    weekly      = defaultdict(float)
    races_count = 0
    all_dates_with_miles = []

    for r in rows:
        if not r["date"]:
            continue
        m = maybe_float(r["miles"])
        if m and m > 0:
            total_miles += m
            active_days.add(r["date"])
            weekly[(r["year"], r["week_of_year"])] += m
            all_dates_with_miles.append(r["date"])
        if r["is_race"] == "1":
            # Count classified races only (skip the omitted Mud Run)
            cat = classify_race(r["date"], r["race_distance"])
            if cat:
                races_count += 1

    n_weeks = len(weekly) or 1
    avg_per_week = total_miles / n_weeks
    peak_week = max(weekly.values()) if weekly else 0

    # Longest streak of consecutive calendar days with miles > 0
    sorted_dates = sorted(set(all_dates_with_miles))
    longest = cur = 0
    prev = None
    for ds in sorted_dates:
        cd = date.fromisoformat(ds)
        cur = cur + 1 if (prev and (cd - prev).days == 1) else 1
        longest = max(longest, cur)
        prev = cd

    if sorted_dates:
        first = date.fromisoformat(sorted_dates[0])
        last  = date.fromisoformat(sorted_dates[-1])
        span  = (last - first).days + 1
        active_pct = round(100 * len(active_days) / span)
    else:
        active_pct = 0

    return {
        "totalMiles":         int(round(total_miles)),
        "avgMilesPerWeek":    int(round(avg_per_week)),
        "peakWeekMiles":      int(round(peak_week)),
        "totalRaces":         races_count,
        "longestStreak":      longest,
        "activeDayPercentage": active_pct,
    }


# ─── Race extraction (categorized + PR-flagged) ───────────────────────────────

def build_race_records(rows):
    """Returns dict of {crossCountry, indoorTrack, outdoorTrack} → list of races,
    each with: date, season, race, distance, distance_bucket, time, time_seconds,
    pr (bool — best of distance bucket within its category), surface_distance_key
    (for separating XC 5k from track 5k in PR computation)."""

    cats = {"crossCountry": [], "indoorTrack": [], "outdoorTrack": []}

    for r in rows:
        if r["is_race"] != "1":
            continue
        cat = classify_race(r["date"], r["race_distance"])
        if cat is None:
            continue

        bucket = normalize_distance(r["race_distance"])
        secs   = parse_time_seconds(r["race_time"])
        is_relay = (r["race_time"] or "").strip().endswith("*")

        cats[cat].append({
            "date":       r["date"],
            "season":     season_label(r["date"], cat),
            "race":       r["race_name"] or "Race",
            "distance":   r["race_distance"],
            "bucket":     bucket,
            "time":       (r["race_time"] or "").rstrip("*"),
            "time_seconds": secs,
            "is_relay":   is_relay,
            "category":   cat,
        })

    # Sort each category chronologically
    for cat_list in cats.values():
        cat_list.sort(key=lambda x: x["date"])

    # PR flagging — min time per (category, bucket), excluding relays + invalid
    # times. Only flag buckets that have a corresponding PR card; this keeps the
    # per-race PR badge consistent with the Performance tab.
    pr_eligible = {(cat, b) for _, buckets, cats_, _ in PR_CARD_SPECS
                   for cat in cats_ for b in buckets}
    for cat, items in cats.items():
        best_per_bucket = {}
        for item in items:
            if item["is_relay"] or item["bucket"] is None or item["time_seconds"] is None:
                continue
            if (cat, item["bucket"]) not in pr_eligible:
                continue
            b = item["bucket"]
            if b not in best_per_bucket or item["time_seconds"] < best_per_bucket[b]["time_seconds"]:
                best_per_bucket[b] = item
        for item in items:
            item["pr"] = item is best_per_bucket.get(item["bucket"])

    return cats


# ─── PR cards (Performance section) ───────────────────────────────────────────
# 7 cards: 800m, Mile, 1500m, 3k Steeple, 5k (track), 5k XC, 6k XC.

PR_CARD_SPECS = [
    # (label,     buckets,           categories,                              color)
    ("800m",      ["800m"],          ("indoorTrack", "outdoorTrack"),         WORKOUT_COLOR),
    ("Mile",      ["Mile"],          ("indoorTrack", "outdoorTrack"),         EASY_COLOR),
    ("1500m",     ["1500m"],         ("indoorTrack", "outdoorTrack"),         TEMPO_COLOR),
    ("3k Steeple",["3k steeple"],    ("outdoorTrack",),                       LONG_COLOR),
    ("5k Track",  ["5k"],            ("indoorTrack", "outdoorTrack"),         RACE_COLOR),
    ("5k XC",     ["5k"],            ("crossCountry",),                       EASY_COLOR),
    ("6k XC",     ["6k"],            ("crossCountry",),                       LONG_COLOR),
]


def compute_pr_cards(races_by_cat):
    cards = []
    for label, buckets, cats, color in PR_CARD_SPECS:
        best = None
        for cat in cats:
            for race in races_by_cat[cat]:
                if race["is_relay"] or race["bucket"] not in buckets or race["time_seconds"] is None:
                    continue
                if best is None or race["time_seconds"] < best["time_seconds"]:
                    best = race
        if best:
            cards.append({
                "label":  label,
                "time":   best["time"],
                "season": best["season"],
                "color":  color,
            })
        else:
            cards.append({"label": label, "time": "—", "season": "no data", "color": color})
    return cards


# ─── Laps Around MIT's Tracks ────────────────────────────────────────────────
# Input is the hand-curated mit_track_laps.csv (see data.load_track_laps).

TRACK_LAP_TRACKS = ("indoor", "outdoor")
TRACK_LAP_KINDS  = ("workout", "race", "easy")
# The four college school years the log covers, in display order. Any row that
# falls outside them is appended after these, sorted, rather than dropped.
TRACK_LAP_YEARS  = ("2003–04", "2004–05", "2005–06", "2006–07")
METERS_PER_MILE  = 1609.344


def _school_year_label(date_str):
    """'2004-02-10' -> '2003–04' (school year runs August through July)."""
    y, m = int(date_str[0:4]), int(date_str[5:7])
    start = y if m >= 8 else y - 1
    return f"{start}–{(start + 1) % 100:02d}"


def compute_track_laps(rows):
    """Per-track lap/mile totals and a per-school-year indoor/outdoor split.

    Returns None when there are no usable rows. Rows are sorted by date (ties
    broken on track, kind, meters, laps) before summing so float totals are
    reproducible byte for byte.
    """
    clean = []
    for r in rows or []:
        d = (r.get("date") or "").strip()
        track = (r.get("track") or "").strip().lower()
        kind = (r.get("kind") or "").strip().lower()
        laps = maybe_float(r.get("laps"))
        meters = maybe_float(r.get("meters"))
        if len(d) < 7 or track not in TRACK_LAP_TRACKS or laps is None:
            continue
        try:
            year = _school_year_label(d)
        except ValueError:
            continue
        clean.append((d, track, kind, meters or 0.0, laps, year))
    if not clean:
        return None
    clean.sort()

    tracks = {
        t: {"laps": 0.0, "meters": 0.0, "by_kind": {k: 0.0 for k in TRACK_LAP_KINDS}}
        for t in TRACK_LAP_TRACKS
    }
    by_year = defaultdict(lambda: {t: 0.0 for t in TRACK_LAP_TRACKS})
    for d, track, kind, meters, laps, year in clean:
        t = tracks[track]
        t["laps"] += laps
        t["meters"] += meters
        if kind in t["by_kind"]:
            t["by_kind"][kind] += laps
        by_year[year][track] += laps

    for t in tracks.values():
        t["laps_display"] = int(round(t["laps"]))
        t["miles"] = round(t["meters"] / METERS_PER_MILE, 1)
        t["by_kind_display"] = {k: int(round(v)) for k, v in t["by_kind"].items()}

    extra = sorted(y for y in by_year if y not in TRACK_LAP_YEARS)
    years = []
    for label in list(TRACK_LAP_YEARS) + extra:
        v = by_year.get(label, {t: 0.0 for t in TRACK_LAP_TRACKS})
        years.append({
            "label":   label,
            "indoor":  v["indoor"],
            "outdoor": v["outdoor"],
            "total":   v["indoor"] + v["outdoor"],
        })
    return {"tracks": tracks, "years": years}
