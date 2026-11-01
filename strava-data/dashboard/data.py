"""CSV loaders and small per-row formatting/categorization helpers."""

import csv
import os
from datetime import datetime, timedelta

from nerd_common.format import fmt_pace, mmss
from nerd_common.format import maybe_float as mf
from nerd_common.segments import drop_excluded

from .config import ACT_CSV, KM_TO_MI, M_TO_FT, SEG_CSV, SEG_EFF_CSV


def load_activities():
    with open(ACT_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def load_segments():
    with open(SEG_CSV, encoding="utf-8-sig") as f:
        return drop_excluded(csv.DictReader(f))

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
        return drop_excluded(csv.DictReader(f))

def activity_dict(rows):
    """Return activities keyed by string ID."""
    return {str(r["id"]): r for r in rows}


# ─── All-time records (calendar marks + detail-panel chips) ─────────────────
# One family per mark set. Bike is MountainBikeRide only, matching the rest of
# the dashboard's MTB convention; Run folds TrailRun in.
RECORD_FAMILIES = (
    ("run",  "run",       ("Run", "TrailRun")),
    ("bike", "bike ride", ("MountainBikeRide",)),
    ("hike", "hike",      ("Hike",)),
)


def activity_records(rows):
    """{activity_id: [record, ...]} for the all-time longest-distance and
    most-elevation activity in each RECORD_FAMILIES family. A record is
    {"family", "metric": "dist"|"elev", "label", "value"}. Zero/blank values
    never hold a record; ties go to the earliest activity (then lowest id) so
    the result is deterministic."""
    out = {}
    for fam, noun, types in RECORD_FAMILIES:
        fam_rows = [r for r in rows if r.get("sport_type") in types]
        for metric, col in (("dist", "distance_km"), ("elev", "total_elevation_gain_m")):
            cands = [(mf(r.get(col)) or 0, r) for r in fam_rows]
            cands = [(v, r) for v, r in cands if v > 0]
            if not cands:
                continue
            # Max value; among equals, earliest start then lowest id.
            best_v = max(v for v, _ in cands)
            best = min((r for v, r in cands if v == best_v),
                       key=lambda r: (r.get("start_date_local") or "", int(r["id"])))
            if metric == "dist":
                label, value = f"Longest {noun}", f"{best_v * KM_TO_MI:.1f} mi"
            else:
                label, value = f"Most climbing on a {noun}", f"{round(best_v * M_TO_FT):,} ft"
            out.setdefault(str(best["id"]), []).append(
                {"family": fam, "metric": metric, "label": label, "value": value})
    return out
