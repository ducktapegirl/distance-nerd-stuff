"""Running Log dashboard theme — thin wrapper over the shared nerd_common theme.

Supplies the two per-dashboard values (grid colour = BORDER_SUBTLE, title font =
TITLE_FONT_FAMILY) so every chart builder can keep calling the bare
``tidy_dark(fig)`` / ``fig_html(fig, ...)`` unchanged.
"""

from nerd_common.theme import fig_html as _fig_html, tidy_dark as _tidy_dark

from dashboard.config import BORDER_SUBTLE, TITLE_FONT_FAMILY


def tidy_dark(fig, *, title=None):
    return _tidy_dark(fig, title=title, gridcolor=BORDER_SUBTLE, title_font_family=TITLE_FONT_FAMILY)


def fig_html(fig, height=320, div_id=None):
    return _fig_html(fig, height, div_id=div_id)
