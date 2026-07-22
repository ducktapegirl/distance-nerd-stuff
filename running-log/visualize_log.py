#!/usr/bin/env python3
"""
visualize_log.py — Build the redesigned running log dashboard from running_log.csv.

Usage:  uv run python running-log/visualize_log.py  (from repo root)
Input:  running_log.csv  (running-log/, alongside this script)
Output: index.html      (running-log/, alongside this script)

Design follows Project Docs/Specs/running-log/design_handoff_running_log/readme.md:
dark glass UI, top-tab nav, 6 sections (Overview, Volume, Workout Mix,
Performance, Races, Patterns), Geist + Geist Mono typography. Charts use
Plotly (themed dark); layout, cards, race rows, search, and heatmap are
hand-rolled HTML/SVG.
"""

from dashboard.config import OUT_PATH
from dashboard.data import load_rows
from dashboard.page import build_html
from dashboard.stats import build_race_records


def main():
    rows = load_rows()
    html_out = build_html(rows)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)
    races = build_race_records(rows)
    print(f"Wrote {OUT_PATH}")
    print(f"  rows: {len(rows)}")
    print(f"  races: XC={len(races['crossCountry'])}, "
          f"Indoor={len(races['indoorTrack'])}, "
          f"Outdoor={len(races['outdoorTrack'])}, "
          f"total={sum(len(v) for v in races.values())}")


if __name__ == "__main__":
    main()
