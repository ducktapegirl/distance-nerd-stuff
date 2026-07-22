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
