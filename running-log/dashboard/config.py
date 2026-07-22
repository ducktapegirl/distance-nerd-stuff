"""Paths, design-token colors, and other constants shared by every dashboard module."""

import os

_HERE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = _HERE
CSV_PATH = os.path.join(BASE_DIR, "running_log.csv")
OUT_PATH = os.path.join(BASE_DIR, "index.html")


# ─── Design tokens (from Project Docs/Specs/running-log/design_handoff_running_log/readme.md) ──
# The dark-theme tokens below (ACCENT*/BG_*/BORDER*/TEXT_*/fonts/PLOTLY_CDN) are
# shared verbatim with the Strava dashboard and live in nerd_common.tokens.
from nerd_common.tokens import (  # noqa: E402
    ACCENT, ACCENT_DIM, ACCENT_GLOW,
    BG_BASE, BG_ELEVATED, BG_GLASS, BG_SURFACE,
    BORDER, BORDER_SUBTLE,
    PLOT_FONT_FAMILY, PLOTLY_CDN,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    TITLE_FONT_FAMILY,
)

# Running-log-specific workout-type palette (kept local — domain-specific).
EASY_COLOR      = "#2dd4bf"   # teal — easy run
TEMPO_COLOR     = "#f59e0b"   # amber — tempo
LONG_COLOR      = "#a78bfa"   # violet — long run
RACE_COLOR      = "#f87171"   # coral — race
WORKOUT_COLOR   = "#60a5fa"   # blue — workout (intervals/fartlek/etc.)

# CSV workout_type → 5 design types
WORKOUT_TYPE_MAP = {
    "run":         "easy",
    "":            "easy",
    "long run":    "long",
    "grass loops": "long",
    "tempo":       "tempo",
    "intervals":   "workout",
    "fartlek":     "workout",
    "hills":       "workout",
    "pre-meet":    "workout",
    "strides":     "workout",
    "bike":        "workout",
    "elliptical":  "workout",
    "pool":        "workout",
    "swim":        "workout",
    "aquajog":     "workout",
    "aqua jog":    "workout",
    "drills":      "workout",
}

TYPE_COLORS = {
    "easy":    EASY_COLOR,
    "long":    LONG_COLOR,
    "tempo":   TEMPO_COLOR,
    "workout": WORKOUT_COLOR,
    "race":    RACE_COLOR,
}

TYPE_LABELS = {
    "easy":    "Easy",
    "long":    "Long",
    "tempo":   "Tempo",
    "workout": "Workout",
    "race":    "Race",
}

# ─── Performance-section event-group color scheme (3 colors) ──────────────────
# Used by the combined pace-over-time chart, the season-best slope chart, and
# the PR timeline strip so all three "read" as the same story. Reuses the
# existing EASY/LONG/RACE tokens — no new hex introduced.
#   Middle distance (800m, Mile, 1500m)   -> EASY_COLOR (teal)
#   3k / steeple    (3k, 3k steeple)      -> LONG_COLOR (violet)
#   5k / 6k         (5k, 6k)              -> RACE_COLOR (coral)
EVENT_GROUPS = [
    ("Middle distance", ("800m", "Mile", "1500m"), EASY_COLOR),
    ("3k / Steeple",    ("3k", "3k steeple"),       LONG_COLOR),
    ("5k / 6k",         ("5k", "6k"),                RACE_COLOR),
]

# Raw distance bucket -> event-group color (derived from EVENT_GROUPS above),
# for charts keyed by bucket (combined pace chart, season-best slope chart).
EVENT_GROUP_COLORS = {
    bucket: color for _, buckets, color in EVENT_GROUPS for bucket in buckets
}

# PR-card label -> event-group color, for chart_pr_timeline's 7 rows (keyed by
# PR_CARD_SPECS label, which splits "5k Track"/"5k XC"/"6k XC" rather than
# using a single raw bucket).
EVENT_GROUP_COLOR_BY_PR_LABEL = {
    "800m":       EASY_COLOR,
    "Mile":       EASY_COLOR,
    "1500m":      EASY_COLOR,
    "3k Steeple": LONG_COLOR,
    "5k Track":   RACE_COLOR,
    "5k XC":      RACE_COLOR,
    "6k XC":      RACE_COLOR,
}

DOW_ORDER  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
DOW_SHORT  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
SEASON_ORDER = ["fall", "winter", "spring", "summer"]

# Cycled by index for per-year traces (Monthly Mileage by Year chart)
YEAR_PALETTE = [
    "#58a6ff", "#2dd4bf", "#a78bfa", "#f59e0b", "#f87171",
    "#34d399", "#60a5fa", "#fb7185", "#e879f9", "#fcd34d",
]

# Dark-theme palette for the fine-grained workout types stacked in
# "Miles by Workout Type per Season". Easy/long/tempo/workout/race relatives
# are kept in the same hue family as TYPE_COLORS so the chart reads as a
# refinement of the donut directly above it.
WORKOUT_MIX_COLORS = {
    "run":          "#2dd4bf",   # teal
    "long run":     "#a78bfa",   # violet
    "intervals":    "#3b82f6",   # blue
    "tempo":        "#f59e0b",   # amber
    "fartlek":      "#ec4899",   # pink
    "hills":        "#c084fc",   # lavender
    "pre-meet":     "#84cc16",   # lime
    "aquajog":      "#67e8f9",   # light cyan
    "pool":         "#0891b2",   # dark cyan
    "bike":         "#64748b",   # slate
    "elliptical":   "#d1d5db",   # pale gray
    "grass loops":  "#16a34a",   # forest green
    "swim":         "#7dd3fc",   # pale sky
    "other":        "#475569",   # dark slate
}
