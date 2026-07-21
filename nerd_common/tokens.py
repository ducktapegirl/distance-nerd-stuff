"""Design tokens shared verbatim by both dashboards.

These colours, fonts, and the Plotly CDN tag were previously copy-pasted into
each dashboard's config.py. Domain-specific palettes (SPORT_COLORS, TYPE_COLORS,
YEAR_PALETTE, …) deliberately stay in each dashboard's own config — only the
truly-common design tokens live here.
"""

# Accent
ACCENT      = "#58a6ff"
ACCENT_DIM  = "rgba(88, 166, 255, 0.08)"
ACCENT_GLOW = "rgba(88, 166, 255, 0.15)"

# Backgrounds / surfaces
BG_BASE     = "#0d1117"
BG_SURFACE  = "#161b22"
BG_ELEVATED = "#1c2230"
BG_GLASS    = "rgba(22, 27, 34, 0.7)"

# Borders
BORDER        = "rgba(48, 54, 61, 0.8)"
BORDER_SUBTLE = "rgba(48, 54, 61, 0.4)"

# Text
TEXT_PRIMARY   = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_TERTIARY  = "#8b949e"

# Fonts
PLOT_FONT_FAMILY  = "'Geist Mono', 'Fira Code', monospace"
TITLE_FONT_FAMILY = "'Geist', sans-serif"

# Plotly runtime, pinned to match plotly==5.24.1 in pyproject.toml.
PLOTLY_CDN = (
    '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>'
)
