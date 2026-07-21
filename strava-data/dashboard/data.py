"""CSV loaders and small per-row formatting/categorization helpers."""

import csv
import os
from datetime import datetime, timedelta

from nerd_common.format import fmt_pace, mmss
from nerd_common.format import maybe_float as mf

from .config import ACT_CSV, SEG_CSV, SEG_EFF_CSV


def load_activities():
    with open(ACT_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def load_segments():
    with open(SEG_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

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

def fmt_seg_time(secs):
    return mmss(float(secs))

def load_segment_efforts():
    if not os.path.exists(SEG_EFF_CSV):
        return []
    with open(SEG_EFF_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def activity_dict(rows):
    """Return activities keyed by string ID."""
    return {str(r["id"]): r for r in rows}
