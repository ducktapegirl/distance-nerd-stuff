"""CSV loaders and small per-row formatting/categorization helpers."""

import csv
import os
from datetime import datetime, timedelta

from .config import ACT_CSV, SEG_CSV, SEG_EFF_CSV


def load_activities():
    with open(ACT_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def load_segments():
    with open(SEG_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def mf(s):
    try:    return float(s)
    except: return None

def sport_category(sport_type):
    if sport_type in ("Run", "TrailRun"):  return "Running"
    if sport_type == "MountainBikeRide":   return "MountainBikeRide"
    return "Other"

def week_start(date_str):
    d = datetime.strptime(date_str[:10], "%Y-%m-%d")
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")

def fmt_time(total_min):
    secs = round((total_min or 0) * 60)
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fmt_pace(pace_min_per_km):
    secs = round(pace_min_per_km * 60)
    return f"{secs // 60}:{secs % 60:02d}"

def fmt_seg_time(secs):
    secs = round(float(secs))
    return f"{secs // 60}:{secs % 60:02d}"

def load_segment_efforts():
    if not os.path.exists(SEG_EFF_CSV):
        return []
    with open(SEG_EFF_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def activity_dict(rows):
    """Return activities keyed by string ID."""
    return {str(r["id"]): r for r in rows}
