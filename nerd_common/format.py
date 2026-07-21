"""Small numeric / time formatting helpers shared by both dashboards.

Only the genuinely-identical helpers live here. Each dashboard keeps its own
``fmt_time`` (they differ: strava formats decimal *minutes* as ``H:MM:SS``,
Running Log formats *seconds* as ``M:SS.ss``) and its own domain parsers.
"""


def maybe_float(s):
    """Return ``float(s)``, or ``None`` when ``s`` is missing/non-numeric."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def mmss(total_seconds):
    """Round to whole seconds and format as ``M:SS`` (e.g. ``393.4 -> '6:33'``)."""
    secs = round(total_seconds)
    return f"{secs // 60}:{secs % 60:02d}"


def fmt_pace(decimal_minutes):
    """Format a pace given in decimal minutes as ``M:SS``.

    Unit-agnostic: the caller decides whether the minutes are per-km or per-mile.
    """
    return mmss(decimal_minutes * 60)
