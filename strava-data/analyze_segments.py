"""
Strava Segment Analyzer

Reads data/segment_efforts.csv (produced by fetch.py) and writes:
  data/segments_summary.csv    one row per segment with stats + trend
  data/segments_map.html       interactive Plotly map of segment locations

Usage:
  python analyze_segments.py
  python analyze_segments.py --min-efforts 3   # only segments run 3+ times
"""

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

# Console may be cp1252 (Windows); segment names and trend arrows contain
# unicode. Replace unencodable chars instead of crashing mid-run.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(errors="replace")

_HERE = Path(__file__).parent
DATA_DIR = _HERE / "data"
EFFORTS_CSV = DATA_DIR / "segment_efforts.csv"
SUMMARY_CSV = DATA_DIR / "segments_summary.csv"
MAP_HTML = DATA_DIR / "segments_map.html"

ACTIVITIES_CSV = DATA_DIR / "activities.csv"

SUMMARY_FIELDS = [
    "segment_id", "segment_name", "segment_city", "segment_state",
    "segment_distance_m", "segment_avg_grade",
    "start_lat", "start_lng",
    "sport_types",    # comma-separated unique sport types for this segment
    "effort_count",
    "first_effort", "last_effort",
    "best_time_s", "worst_time_s", "pr_date",
    "recent_trend",   # seconds/effort on last-5 efforts (negative = getting faster)
    "avg_heartrate",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_efforts():
    if not EFFORTS_CSV.exists():
        raise SystemExit(
            f"{EFFORTS_CSV} not found. Run fetch.py first."
        )
    with open(EFFORTS_CSV, newline="", encoding="utf-8") as f:
        efforts = list(csv.DictReader(f))

    # Backfill sport_type from activities.csv for efforts that predate the field
    missing = any(not e.get("sport_type") for e in efforts)
    if missing and ACTIVITIES_CSV.exists():
        with open(ACTIVITIES_CSV, newline="", encoding="utf-8") as f:
            sport_by_id = {r["id"]: r.get("sport_type", "") for r in csv.DictReader(f)}
        for e in efforts:
            if not e.get("sport_type"):
                e["sport_type"] = sport_by_id.get(str(e.get("activity_id", "")), "")

    return efforts


def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Per-segment aggregation
# ---------------------------------------------------------------------------

def aggregate(efforts):
    by_seg = defaultdict(list)
    for e in efforts:
        sid = e.get("segment_id")
        if sid:
            by_seg[sid].append(e)

    rows = []
    for sid, seg_efforts in by_seg.items():
        # Sort by date ascending
        seg_efforts.sort(key=lambda e: e.get("start_date_local") or "")

        times = [safe_int(e["elapsed_time_s"]) for e in seg_efforts
                 if safe_int(e["elapsed_time_s"])]
        if not times:
            continue

        best_idx = times.index(min(times))
        hr_vals = [safe_float(e["average_heartrate"]) for e in seg_efforts
                   if safe_float(e["average_heartrate"])]

        # Linear trend over last 5 efforts (slope of time vs. effort index)
        recent = times[-5:]
        trend = _linear_slope(recent) if len(recent) >= 2 else None

        sport_types = ",".join(sorted({
            e.get("sport_type", "") for e in seg_efforts if e.get("sport_type")
        }))

        first = seg_efforts[0]
        rows.append({
            "segment_id":         sid,
            "segment_name":       first.get("segment_name"),
            "segment_city":       first.get("segment_city"),
            "segment_state":      first.get("segment_state"),
            "segment_distance_m": first.get("segment_distance_m"),
            "segment_avg_grade":  first.get("segment_avg_grade"),
            "start_lat":          first.get("segment_start_lat"),
            "start_lng":          first.get("segment_start_lng"),
            "sport_types":        sport_types,
            "effort_count":       len(seg_efforts),
            "first_effort":       seg_efforts[0].get("start_date_local"),
            "last_effort":        seg_efforts[-1].get("start_date_local"),
            "best_time_s":        min(times),
            "worst_time_s":       max(times),
            "pr_date":            seg_efforts[best_idx].get("start_date_local"),
            "recent_trend":       round(trend, 2) if trend is not None else None,
            "avg_heartrate":      round(sum(hr_vals) / len(hr_vals), 1) if hr_vals else None,
        })

    rows.sort(key=lambda r: r["effort_count"], reverse=True)
    return rows


def _linear_slope(values):
    """Return slope of a simple linear regression of values vs. index."""
    n = len(values)
    if n < 2:
        return None
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((xs[i] - mean_x) * (values[i] - mean_y) for i in range(n))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

def fmt_time(seconds):
    if seconds is None:
        return "—"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def trend_arrow(slope):
    if slope is None:
        return ""
    if slope < -1:
        return "↓ faster"
    if slope > 1:
        return "↑ slower"
    return "→ flat"


def build_map(summary_rows):
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("  plotly not installed — skipping map. Run: pip install plotly")
        return

    rows_with_coords = [
        r for r in summary_rows
        if safe_float(r.get("start_lat")) and safe_float(r.get("start_lng"))
    ]
    if not rows_with_coords:
        print("  No segment coordinates found — skipping map.")
        return

    lats = [float(r["start_lat"]) for r in rows_with_coords]
    lngs = [float(r["start_lng"]) for r in rows_with_coords]
    counts = [r["effort_count"] for r in rows_with_coords]
    max_count = max(counts) if counts else 1

    # Size: 8–28px proportional to effort count
    sizes = [8 + 20 * (c / max_count) for c in counts]

    # Color: by effort count (more = darker blue)
    colors = counts

    texts = []
    for r in rows_with_coords:
        trend = trend_arrow(safe_float(r.get("recent_trend")))
        dist_km = round(safe_float(r["segment_distance_m"]) / 1000, 2) \
            if safe_float(r["segment_distance_m"]) else "?"
        texts.append(
            f"<b>{r['segment_name']}</b><br>"
            f"Efforts: {r['effort_count']}<br>"
            f"Best: {fmt_time(safe_int(r['best_time_s']))}<br>"
            f"Distance: {dist_km} km<br>"
            f"Trend: {trend if trend else '—'}"
        )

    fig = go.Figure(go.Scattermap(
        lat=lats,
        lon=lngs,
        mode="markers",
        marker=dict(
            size=sizes,
            color=colors,
            colorscale="Blues",
            showscale=True,
            colorbar=dict(title="Efforts"),
            opacity=0.85,
        ),
        text=texts,
        hoverinfo="text",
    ))

    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)

    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(lat=center_lat, lon=center_lng),
            zoom=11,
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(
            text="My Strava Segments",
            font=dict(size=18),
        ),
        height=700,
    )

    fig.write_html(str(MAP_HTML), include_plotlyjs="cdn")
    print(f"  Saved {MAP_HTML}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Analyze Strava segment efforts.")
    p.add_argument("--min-efforts", type=int, default=1,
                   help="Only include segments run at least N times.")
    return p.parse_args()


def main():
    args = parse_args()

    print("Loading segment efforts...")
    efforts = load_efforts()
    print(f"  {len(efforts)} effort rows across all activities.")

    print("Aggregating by segment...")
    summary = aggregate(efforts)
    if args.min_efforts > 1:
        summary = [r for r in summary if r["effort_count"] >= args.min_efforts]

    # Write summary CSV
    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(summary)
    print(f"  Saved {SUMMARY_CSV}  ({len(summary)} segments)")

    # Print top-10 to console
    print("\nTop 10 most-run segments:")
    print(f"  {'Efforts':>7}  {'Best':>7}  {'Trend':<12}  Name")
    print("  " + "-" * 60)
    for r in summary[:10]:
        trend = trend_arrow(safe_float(r.get("recent_trend")))
        print(f"  {r['effort_count']:>7}  "
              f"{fmt_time(safe_int(r['best_time_s'])):>7}  "
              f"{trend:<12}  "
              f"{r['segment_name']}")

    # Build map
    print("\nBuilding segment map...")
    build_map(summary)

    print("\nDone. Next: run /strava-segments in Claude Code for interactive analysis.")


if __name__ == "__main__":
    main()
