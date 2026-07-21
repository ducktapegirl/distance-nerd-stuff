"""Strava dashboard theme — thin wrapper over the shared nerd_common theme.

Supplies the two per-dashboard values (grid colour = GRID, title font =
TITLE_FONT_FAMILY) so every chart builder can keep calling the bare
``tidy_dark(fig)`` / ``fig_html(fig, ...)`` unchanged.
"""

from nerd_common.theme import fig_html as _fig_html, tidy_dark as _tidy_dark

from .config import GRID, TITLE_FONT_FAMILY


def tidy_dark(fig, *, title=None):
    """Apply dark-theme defaults. Per-chart overrides MUST come AFTER this call."""
    return _tidy_dark(fig, title=title, gridcolor=GRID, title_font_family=TITLE_FONT_FAMILY)


def fig_html(fig, height=None, div_id=None):
    return _fig_html(fig, height or 450, div_id=div_id)
