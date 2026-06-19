"""CSV loading, row-level parsing/formatting, and race-classification helpers."""

import csv

from dashboard.config import CSV_PATH, WORKOUT_TYPE_MAP


def load_rows():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def maybe_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_time_seconds(s):
    """'19:32' → 1172.0, '11:21.5' → 681.5, '5:39' → 339.0. None on failure."""
    if not s:
        return None
    s = s.strip().rstrip("*").rstrip("?")
    s = s.replace(".x", "")
    parts = s.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return None
    return None


def fmt_pace(pace_min):
    total_s = round(pace_min * 60)
    return f"{total_s // 60}:{total_s % 60:02d}"


def fmt_time(secs):
    secs = round(secs, 2)
    whole = int(secs)
    frac  = secs - whole
    m, s  = whole // 60, whole % 60
    if frac >= 0.005:
        return f"{m}:{s:02d}.{int(round(frac*100)):02d}"
    return f"{m}:{s:02d}"


def map_type(workout_type, is_race):
    if is_race:
        return "race"
    key = (workout_type or "").lower().strip()
    return WORKOUT_TYPE_MAP.get(key, "easy")


# ─── Race classification (per user rules) ─────────────────────────────────────
# - Cross country: fall, before Thanksgiving, 5k or 6k (no steeple)
# - Indoor track:  December through late March, 800m through 5k
# - Outdoor track: from spring break onward, includes steeplechase
# - Mud Run (2004-06-06): omitted per user

def classify_race(date_str, distance):
    if not date_str or not distance:
        return None
    y, m, d = (int(p) for p in date_str.split("-"))

    # Omit the one summer Mud Run
    if date_str == "2004-06-06":
        return None

    # Cross country: Sep / Oct / Nov-before-25
    if (m in (9, 10)) or (m == 11 and d < 25):
        return "crossCountry"

    # Indoor track: Dec through ~late March
    if m == 12 or m <= 2:
        return "indoorTrack"
    if m == 3 and d < 28:           # 2006-03-29 / 2007-03-31 are spring-break FL outdoor meets
        return "indoorTrack"

    # Outdoor track: late March / April / May (any distance, includes steeple)
    if (m == 3 and d >= 28) or m in (4, 5):
        return "outdoorTrack"

    return None  # summer / unclassified


# ─── Distance buckets (for PR cards and race-card display) ────────────────────

def normalize_distance(raw):
    """Map raw `race_distance` text to a canonical bucket. Returns None if
    we don't want to track this distance for PRs."""
    if not raw:
        return None
    s = raw.strip().lower()
    if "steeple" in s and "1500" in s:
        return "1500m steeple"   # one-off time trial 2007-04-07
    if "steeple" in s:
        return "3k steeple"
    if "dmr" in s or "leg" in s:
        return None              # relay leg, not standalone
    if s in ("800", "800m"):
        return "800m"
    if s in ("1000",):
        return "1000m"
    if s in ("1500", "1500m"):
        return "1500m"
    if s in ("mile", "1600m"):
        return "Mile"
    if s in ("3k", "3000m"):
        return "3k"
    if s in ("5k", "5000m", "5k (short)"):
        return "5k"
    if s in ("6k", "6k (short 100m)"):
        return "6k"
    if s in ("4k",):
        return "4k"
    if s == "4822m":
        return "4822m"
    return s.upper()


# Display label for a race row's "season + distance" line
def season_label(date_str, category):
    y, m, _ = (int(p) for p in date_str.split("-"))
    if category == "crossCountry":
        return f"Fall {y}"
    if category == "indoorTrack":
        # December stays in the year that follows
        season_year = y + 1 if m == 12 else y
        return f"Indoor {season_year}"
    if category == "outdoorTrack":
        return f"Spring {y}"
    return ""
