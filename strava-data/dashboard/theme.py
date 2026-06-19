"""Shared Plotly styling: dark-theme defaults and HTML embedding."""

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


def fig_html(fig, height=None, div_id=None):
    kwargs = dict(
        full_html=False,
        include_plotlyjs=False,
        config={"displayModeBar": False, "responsive": True},
    )
    if height:
        kwargs["default_height"] = f"{height}px"
    if div_id:
        kwargs["div_id"] = div_id
    return fig.to_html(**kwargs)
