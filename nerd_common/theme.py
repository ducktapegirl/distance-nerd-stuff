"""Shared Plotly dark-theme styling and HTML-embedding helpers.

Both dashboards style their figures identically apart from two values (the grid
colour and the title font), so those are parameters here. Each dashboard has a
thin local theme.py that supplies its two values and re-exports tidy_dark /
fig_html, letting every chart builder keep calling the bare tidy_dark(fig) and
fig_html(fig, ...) unchanged.
"""

import json

from plotly.utils import PlotlyJSONEncoder

from .tokens import (
    BG_ELEVATED, BORDER, PLOT_FONT_FAMILY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)


def tidy_dark(fig, *, title=None, gridcolor, title_font_family):
    """Apply dark-theme defaults. Per-chart overrides MUST come AFTER this call.

    ``gridcolor`` and ``title_font_family`` are supplied by each dashboard's
    thin theme wrapper (they happen to resolve to the same values today, but are
    kept as parameters so a dashboard can diverge without forking this file).
    """
    fig.update_layout(
        plot_bgcolor  = "rgba(0,0,0,0)",
        paper_bgcolor = "rgba(0,0,0,0)",
        font          = dict(family=PLOT_FONT_FAMILY, color=TEXT_SECONDARY, size=11),
        margin        = dict(t=20 if not title else 50, b=40, l=50, r=20),
        hovermode     = "closest",
        legend        = dict(
            orientation="h", yanchor="bottom", y=-0.25, x=0.5, xanchor="center",
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_SECONDARY, size=10, family=PLOT_FONT_FAMILY),
        ),
        hoverlabel    = dict(
            bgcolor=BG_ELEVATED, bordercolor=BORDER,
            font=dict(family=PLOT_FONT_FAMILY, color=TEXT_PRIMARY, size=11),
        ),
    )
    if title:
        fig.update_layout(title=dict(
            text=title,
            font=dict(color=TEXT_PRIMARY, size=12, family=title_font_family),
            x=0, xanchor="left",
        ))
    for update_axes in (fig.update_xaxes, fig.update_yaxes):
        update_axes(
            gridcolor=gridcolor, zerolinecolor=gridcolor,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(color=TEXT_TERTIARY, size=10),
            title_font=dict(color=TEXT_SECONDARY, size=11),
        )
    return fig


_CHART_CONFIG = {"displayModeBar": False, "responsive": True}


def fig_html(fig, height, div_id=None):
    """Emit a chart as an inert placeholder div + a JSON spec script, instead of
    an inline ``Plotly.newPlot`` that runs during page parse.

    The page's ``renderView()`` (template.py) reads the spec and calls
    ``Plotly.newPlot`` only when the chart's section is first shown. Deferring
    rendering off the initial parse is what stops a direct link / tab switch from
    stalling behind every *other* section's charts, and — because the chart is
    only ever plotted while its container is visible — it renders at the correct
    width (no 0-width-then-resize snap). The placeholder reserves the chart's
    height so the card doesn't jump when it fills in.

    ``height`` is already resolved to a concrete pixel value by the caller's
    thin wrapper (strava defaults to 450, Running Log to 320).
    """
    div_id = div_id or f"chart-{id(fig)}"
    spec = fig.to_plotly_json()
    spec["config"] = _CHART_CONFIG
    payload = json.dumps(spec, cls=PlotlyJSONEncoder).replace("</", "<\\/")
    return (
        f'<div id="{div_id}" class="lazy-chart" data-plotly="{div_id}" '
        f'style="height:{height}px"></div>'
        f'<script type="application/json" data-plotly-spec="{div_id}">{payload}</script>'
    )
