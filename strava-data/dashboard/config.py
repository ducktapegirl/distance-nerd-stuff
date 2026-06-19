"""Paths, conversions, colors, and fonts shared by every dashboard module."""

import os

_HERE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_HERE, "data")
ACT_CSV      = os.path.join(DATA_DIR, "activities.csv")
SEG_CSV      = os.path.join(DATA_DIR, "segments_summary.csv")
SEG_EFF_CSV  = os.path.join(DATA_DIR, "segment_efforts.csv")
STREAMS_DIR  = os.path.join(DATA_DIR, "streams")

# Generated output (gitignored). The Running Log dir is the GitHub Pages publish root.
OUT_HTML = os.path.normpath(os.path.join(_HERE, "..", "Running Log", "strava.html"))

PLOTLY_CDN = (
    '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>'
)

KM_TO_MI = 0.621371
M_TO_FT  = 3.28084

SPORT_DISPLAY = {
    "Running":          "Running",
    "MountainBikeRide": "Mountain Bike Ride",
    "Other":            "Other",
}

# Categorical sport colors — tuned for hue separation, matching the running-log
# workout-type palette (teal / amber / slate). Used by both themes.
SPORT_COLORS = {
    "Running":          "#2dd4bf",
    "MountainBikeRide": "#f59e0b",
    "Other":            "#8b949e",
}

# Trail Running — violet, distinct from teal Running and amber MTB
TRAIL_RUN_COLOR = "#a78bfa"

# Plotly figure colors — dark defaults. The theme toggle JS overrides these
# at runtime via Plotly.relayout reading the CSS custom properties.
BG_BASE        = "#0d1117"
BG_SURFACE     = "#161b22"
BG_ELEVATED    = "#1c2230"
BG_GLASS       = "rgba(22, 27, 34, 0.7)"
BORDER         = "rgba(48, 54, 61, 0.8)"
BORDER_SUBTLE  = "rgba(48, 54, 61, 0.4)"
TEXT_PRIMARY   = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_TERTIARY  = "#8b949e"
GRID           = "rgba(48, 54, 61, 0.4)"
ACCENT         = "#58a6ff"
ACCENT_DIM     = "rgba(88, 166, 255, 0.08)"
ACCENT_GLOW    = "rgba(88, 166, 255, 0.15)"

# Semantic trend colors for segment bars
FASTER  = "#2dd4bf"
SLOWER  = "#f87171"
NEUTRAL = "#58a6ff"
ELEVATION_COLOR = "#a78bfa"  # violet for elevation, distinct from accent blue

PLOT_FONT_FAMILY = "'Geist Mono', 'Fira Code', monospace"
TITLE_FONT_FAMILY = "'Geist', sans-serif"

# 92129 (Rancho Penasquitos, San Diego) — fixed map center
MAP_CENTER_LAT = 32.9545
MAP_CENTER_LON = -117.0910

# Used by segment "fastest"/"consistency" card builders (rollups_cards.py)
RUN_EMOJI = "\U0001f3c3‍♀️"   # woman running
MTB_EMOJI = "\U0001f6b5‍♀️"   # woman mountain biking
