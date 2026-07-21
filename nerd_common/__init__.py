"""Shared helpers for the distance-nerd-stuff dashboards.

A tiny package that holds the design tokens, Plotly dark-theme helpers, and
numeric/time formatters that were previously duplicated between the two
dashboard packages (strava-data/dashboard and Running Log/src/dashboard).

Dependency rule: this package may import only the standard library, plotly, and
numpy — the same constraint the Strava build is held to — so either dashboard
can depend on it without pulling in anything new.
"""
