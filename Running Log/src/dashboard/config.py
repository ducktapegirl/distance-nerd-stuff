"""Paths, design-token colors, and other constants shared by every dashboard module."""

import os

_HERE    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = _HERE
CSV_PATH = os.path.join(BASE_DIR, "running_log.csv")
OUT_PATH = os.path.join(BASE_DIR, "index.html")


# ─── Design tokens (from design_handoff_running_log/README.md) ────────────────

ACCENT          = "#58a6ff"
ACCENT_DIM      = "rgba(88, 166, 255, 0.08)"
ACCENT_GLOW     = "rgba(88, 166, 255, 0.15)"

EASY_COLOR      = "#2dd4bf"   # teal — easy run
TEMPO_COLOR     = "#f59e0b"   # amber — tempo
LONG_COLOR      = "#a78bfa"   # violet — long run
RACE_COLOR      = "#f87171"   # coral — race
WORKOUT_COLOR   = "#60a5fa"   # blue — workout (intervals/fartlek/etc.)

BG_BASE         = "#0d1117"
BG_SURFACE      = "#161b22"
BG_ELEVATED     = "#1c2230"
BG_GLASS        = "rgba(22, 27, 34, 0.7)"
BORDER          = "rgba(48, 54, 61, 0.8)"
BORDER_SUBTLE   = "rgba(48, 54, 61, 0.4)"
TEXT_PRIMARY    = "#e6edf3"
TEXT_SECONDARY  = "#8b949e"
TEXT_TERTIARY   = "#8b949e"

PLOTLY_CDN = (
    '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" '
    'charset="utf-8"></script>'
)

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

PLOT_FONT_FAMILY = "'Geist Mono', 'Fira Code', monospace"
