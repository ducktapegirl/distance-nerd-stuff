#!/usr/bin/env python3
"""Build Strava activity dashboard → Running Log/strava.html

Styled to match the College Running Log dashboard (dark-glass + CSS-variable
theming, light/dark/system toggle, frosted cards). All chart-card UI is
CSS-variable-driven so the theme toggle works without regenerating figures.
"""

import os

from dashboard.config import OUT_HTML
from dashboard.data import load_activities, load_segments
from dashboard.page import build_page


def main():
    print("Loading data...")
    rows = load_activities()
    segs = load_segments()
    print(f"  {len(rows)} activities, {len(segs)} segments")
    print("Building dashboard...")
    html = build_page(rows, segs)
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"-> {OUT_HTML}")
    print(f"   {len(html):,} bytes")


if __name__ == "__main__":
    main()
