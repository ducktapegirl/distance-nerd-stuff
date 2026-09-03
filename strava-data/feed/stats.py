"""The small amount of statistics the cards need.

Reimplemented rather than imported from ``dashboard/geometry_stats.py``: that
module pulls in plotly and ``dashboard/config.py`` (which loads dotenv and
reads MAPTILER_KEY), and the whole premise of this build is not having Plotly
in it. Kept to what the cards actually use.
"""

import numpy as np


def ols(xs, ys):
    """Least-squares fit. Returns ``(slope, intercept, r2, n)`` or None."""
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 3 or np.ptp(x) == 0:
        return None
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 0.0
    return slope, float(intercept), r2, int(x.size)


def crossover(fit_a, fit_b):
    """Where two fitted lines meet on x, or None if they are parallel."""
    if not fit_a or not fit_b:
        return None
    (sa, ia, _, _), (sb, ib, _, _) = fit_a, fit_b
    if abs(sa - sb) < 1e-9:
        return None
    return (ib - ia) / (sa - sb)


def cv(values):
    """Coefficient of variation - the dashboard's segment-consistency metric."""
    a = np.asarray(values, dtype=float)
    if a.size < 2 or a.mean() == 0:
        return None
    return float(a.std(ddof=0) / a.mean())
