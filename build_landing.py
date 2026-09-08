#!/usr/bin/env python3
"""Build the landing page → running-log/index.html

The site's front door: two glass tiles, running log on the left and Strava on
the right, each fronted by an artistic SVG derived from that dashboard's data —
Ring of Seasons and Route Grid, both in landing/art.py.

Usage: uv run python build_landing.py  (from repo root)
"""

import os

from landing.config import OUT_PATH
from landing.page import build_html


def main():
    html = build_html()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUT_PATH}")
    print(f"  {len(html):,} bytes")


if __name__ == "__main__":
    main()
