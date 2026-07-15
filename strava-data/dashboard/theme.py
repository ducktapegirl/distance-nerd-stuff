"""Shared Plotly styling: dark-theme defaults and HTML embedding."""

import json

from plotly.utils import PlotlyJSONEncoder

from .config import (
    BG_ELEVATED, BORDER, GRID, PLOT_FONT_FAMILY, TEXT_PRIMARY,
    TEXT_SECONDARY, TEXT_TERTIARY, TITLE_FONT_FAMILY,
)


def tidy_dark(fig, *, title=None):
    """Apply dark-theme defaults. Per-chart overrides MUST come AFTER this call."""
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
            font=dict(color=TEXT_PRIMARY, size=12, family=TITLE_FONT_FAMILY),
            x=0, xanchor="left",
        ))
    fig.update_xaxes(
        gridcolor=GRID, zerolinecolor=GRID,
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(color=TEXT_TERTIARY, size=10),
        title_font=dict(color=TEXT_SECONDARY, size=11),
    )
    fig.update_yaxes(
        gridcolor=GRID, zerolinecolor=GRID,
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(color=TEXT_TERTIARY, size=10),
        title_font=dict(color=TEXT_SECONDARY, size=11),
    )
    return fig


_CHART_CONFIG = {"displayModeBar": False, "responsive": True}


def fig_html(fig, height=None, div_id=None):
    """Emit a chart as an inert placeholder div + a JSON spec script, instead of
    an inline ``Plotly.newPlot`` that runs during page parse.

    The page's ``renderView()`` (template.py) reads the spec and calls
    ``Plotly.newPlot`` only when the chart's section is first shown. Deferring
    rendering off the initial parse is what stops a direct link / tab switch from
    stalling behind every *other* section's charts, and — because the chart is
    only ever plotted while its container is visible — it renders at the correct
    width (no 0-width-then-resize snap). The placeholder reserves the chart's
    height so the card doesn't jump when it fills in.
    """
    div_id = div_id or f"chart-{id(fig)}"
    spec = fig.to_plotly_json()
    spec["config"] = _CHART_CONFIG
    payload = json.dumps(spec, cls=PlotlyJSONEncoder).replace("</", "<\\/")
    return (
        f'<div id="{div_id}" class="lazy-chart" data-plotly="{div_id}" '
        f'style="height:{height or 450}px"></div>'
        f'<script type="application/json" data-plotly-spec="{div_id}">{payload}</script>'
    )
