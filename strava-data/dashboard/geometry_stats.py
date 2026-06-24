"""Pure math helpers: scatter-plot geometry, validated numeric routines, and
GPS-stream tortuosity. No Plotly figure construction lives here."""

import csv
import math
import os
from datetime import datetime

import numpy as np
import plotly.graph_objects as go

from .config import PLOT_FONT_FAMILY, STREAMS_DIR
from .data import fmt_pace, mf

# ─── Scatter-plot helpers (correlation line + R²) ─────────────────────────────

def _haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _linreg(xs, ys):
    """Simple OLS. Returns (slope, intercept, r2) or (None, None, None)."""
    n = len(xs)
    if n < 3:
        return None, None, None
    mx = sum(xs) / n
    my = sum(ys) / n
    ss_xy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    ss_xx = sum((x - mx) ** 2 for x in xs)
    ss_yy = sum((y - my) ** 2 for y in ys)
    if ss_xx == 0 or ss_yy == 0:
        return None, None, None
    slope     = ss_xy / ss_xx
    intercept = my - slope * mx
    r2        = (ss_xy ** 2) / (ss_xx * ss_yy)
    return slope, intercept, r2


def _add_regression_line(fig, xs, ys, color):
    """Add OLS trendline trace; return R² or None."""
    slope, intercept, r2 = _linreg(xs, ys)
    if slope is None:
        return None
    x0, x1 = min(xs), max(xs)
    fig.add_trace(go.Scatter(
        x=[x0, x1],
        y=[slope * x0 + intercept, slope * x1 + intercept],
        mode="lines",
        line=dict(color=color, width=1.5, dash="dash"),
        showlegend=False,
        hoverinfo="skip",
    ))
    return r2


def _r2_annotations(entries):
    """
    entries: list of (r2, color, x_paper, y_paper)
    Returns Plotly annotation dicts positioned in paper coordinates.
    """
    anns = []
    for r2, color, xp, yp in entries:
        if r2 is None:
            continue
        anns.append(dict(
            x=xp, y=yp,
            xref="paper", yref="paper",
            text=f"R²={r2:.2f}",
            showarrow=False,
            font=dict(color=color, size=10, family=PLOT_FONT_FAMILY),
            xanchor="right", yanchor="top",
            bgcolor="rgba(0,0,0,0)",
        ))
    return anns


def _pace_ticks(ys):
    """Tick vals + text for a min/mi pace axis from a list of float pace values."""
    if not ys:
        return [], []
    lo, hi = min(ys), max(ys)
    vals, texts = [], []
    v = int(lo)
    while v <= int(hi) + 1:
        vals.append(v)
        texts.append(fmt_pace(v))
        v += 1
    return vals, texts


def _iqr_upper_fence(vals, k=1.5):
    """Tukey upper fence (q3 + k*iqr) of vals; falls back to max for n<4 or a
    degenerate (zero-IQR) distribution. Used as a robust 'cap' so a lone extreme
    value doesn't compress a color/opacity scale."""
    n = len(vals)
    if n < 4:
        return max(vals, default=0.0)
    s = sorted(vals)
    q1 = s[n // 4]
    q3 = s[(3 * n) // 4]
    iqr = q3 - q1
    fence = q3 + k * iqr
    if iqr == 0 or fence <= 0:
        return max(vals)
    return fence


def _remove_outliers(xs, ys, texts, iqr_k=1.5):
    """
    Remove outliers from paired (xs, ys, texts) lists using Tukey's IQR fence
    applied independently on each axis. Points must pass *both* fences to be
    kept. Inputs must already be free of None values.

    Returns (xs_clean, ys_clean, texts_clean).
    """
    def _fence(vals):
        n = len(vals)
        if n < 4:
            return -math.inf, math.inf
        s = sorted(vals)
        q1 = s[n // 4]
        q3 = s[(3 * n) // 4]
        iqr = q3 - q1
        return q1 - iqr_k * iqr, q3 + iqr_k * iqr

    x_lo, x_hi = _fence(xs)
    y_lo, y_hi = _fence(ys)

    out_x, out_y, out_t = [], [], []
    for x, y, t in zip(xs, ys, texts):
        if x_lo <= x <= x_hi and y_lo <= y <= y_hi:
            out_x.append(x)
            out_y.append(y)
            out_t.append(t)
    return out_x, out_y, out_t


# ─── Validated numeric routines (Appendix B — copied verbatim) ─────────────────
# p-values (matches scipy to full precision; used for V1/V3/V4/V6) and a
# deterministic by-hand k-means (V2). These power the Exploratory tab only.

def betacf(a, b, x):
    EPS = 3e-12; FPMIN = 1e-300
    qab = a + b; qap = a + 1.0; qam = a - 1.0
    c = 1.0; d = 1.0 - qab * x / qap
    if abs(d) < FPMIN: d = FPMIN
    d = 1.0 / d; h = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < EPS: break
    return h

def betai(a, b, x):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    return 1.0 - bt * betacf(b, a, 1.0 - x) / b

def t_two_sided_p(t, dfree):
    return betai(dfree / 2.0, 0.5, dfree / (dfree + t * t))

def welch_ttest(x, y):   # x, y numpy arrays
    n1, n2 = len(x), len(y)
    v1, v2 = x.var(ddof=1), y.var(ddof=1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    t = (x.mean() - y.mean()) / se
    dfree = (v1/n1 + v2/n2)**2 / ((v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1))
    return t, dfree, t_two_sided_p(abs(t), dfree)

def ols_r_p(x, y):       # returns slope, intercept, r, p
    b, a = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    n = len(x)
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return b, a, r, t_two_sided_p(abs(t), n - 2)

def standardize(M):
    """Column-wise z-score with population std (ddof=0)."""
    mean = M.mean(axis=0)
    std = M.std(axis=0)
    return (M - mean) / std, mean, std

def pca_svd(Z):
    """PCA via SVD. Returns scores, loadings (rows=PC), explained-variance ratio.
    Sign convention: per PC, if the largest-|loading| feature is negative, flip
    that PC's loadings and scores."""
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    evr = S**2 / np.sum(S**2)
    scores = U * S
    loadings = Vt.copy()
    for k in range(loadings.shape[0]):
        j = np.argmax(np.abs(loadings[k]))
        if loadings[k, j] < 0:
            loadings[k] *= -1.0
            scores[:, k] *= -1.0
    return scores, loadings, evr

def kmeans_pp_init(Z, k, rng):
    n = Z.shape[0]
    centers = [Z[rng.integers(n)]]
    for _ in range(1, k):
        d2 = np.min(np.sum((Z[:, None, :] - np.array(centers)[None, :, :])**2, axis=2), axis=1)
        centers.append(Z[rng.choice(n, p=d2 / d2.sum())])
    return np.array(centers)

def lloyd(Z, k, init, iters=300, tol=1e-10):
    C = init.copy()
    for _ in range(iters):
        lab = np.argmin(np.sum((Z[:, None, :] - C[None, :, :])**2, axis=2), axis=1)
        newC = np.array([Z[lab == j].mean(0) if np.any(lab == j) else C[j] for j in range(k)])
        if np.allclose(newC, C, atol=tol): C = newC; break
        C = newC
    return lab, C, np.sum((Z - C[lab])**2)

def kmeans_best(Z, k=3, restarts=50, seed=42):
    """Best-of-`restarts` k-means++ from ONE rng(seed); keep lowest inertia."""
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(restarts):
        lab, C, inertia = lloyd(Z, k, kmeans_pp_init(Z, k, rng))
        if best is None or inertia < best[2]:
            best = (lab, C, inertia)
    return best


# ─── Tortuosity computation from GPS streams ──────────────────────────────────

def compute_tortuosity_map(seg_efforts, act_by_id):
    """
    For each unique segment, use one GPS stream to compute:
        tortuosity = GPS path length / straight-line endpoint distance

    Returns {segment_id: tortuosity_float}.
    Segments without a usable stream are omitted.
    """
    print("  computing tortuosity from GPS streams...")
    # Pick one representative effort per segment (first with a stream)
    seen = {}
    for e in seg_efforts:
        sid = e.get("segment_id", "")
        if sid and sid not in seen:
            seen[sid] = e

    tort_map = {}
    for sid, e in seen.items():
        aid = str(e.get("activity_id", ""))
        stream_path = os.path.join(STREAMS_DIR, f"{aid}.csv")
        if not os.path.exists(stream_path):
            continue

        # Compute time offset of this effort within the activity
        act = act_by_id.get(aid, {})
        act_start_s  = act.get("start_date_local", "")
        eff_start_s  = e.get("start_date_local", "")
        elapsed_s    = mf(e.get("elapsed_time_s")) or 0
        if not act_start_s or not eff_start_s or elapsed_s <= 0:
            continue
        try:
            act_dt  = datetime.strptime(act_start_s[:19], "%Y-%m-%d %H:%M:%S")
            eff_dt  = datetime.strptime(eff_start_s[:19], "%Y-%m-%d %H:%M:%S")
            offset  = (eff_dt - act_dt).total_seconds()
        except ValueError:
            continue

        t0, t1 = offset, offset + elapsed_s

        # Read stream and extract GPS window
        try:
            with open(stream_path, encoding="utf-8-sig") as sf:
                srows = list(csv.DictReader(sf))
        except OSError:
            continue

        pts = []
        for row in srows:
            t = mf(row.get("t"))
            if t is None or not (t0 <= t <= t1):
                continue
            lat = mf(row.get("lat"))
            lng = mf(row.get("lng"))
            if lat and lng:
                pts.append((lat, lng))

        if len(pts) < 2:
            continue

        # Path length via consecutive haversine
        path_m = sum(
            _haversine_m(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
            for i in range(len(pts) - 1)
        )
        straight_m = _haversine_m(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1])

        if straight_m < 5:          # endpoints essentially the same → skip
            continue
        tort = path_m / straight_m
        if 1.0 <= tort <= 50:       # sanity bounds
            tort_map[sid] = round(tort, 3)

    print(f"    tortuosity computed for {len(tort_map)} segments")
    return tort_map

