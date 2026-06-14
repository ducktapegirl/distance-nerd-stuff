#!/usr/bin/env python3
"""Build Strava activity dashboard → strava-data/strava.html + Running Log/strava.html

Styled to match the College Running Log dashboard (dark-glass + CSS-variable
theming, light/dark/system toggle, frosted cards). All chart-card UI is
CSS-variable-driven so the theme toggle works without regenerating figures.
"""

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─── Config ───────────────────────────────────────────────────────────────────

_HERE    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_HERE, "data")
ACT_CSV      = os.path.join(DATA_DIR, "activities.csv")
SEG_CSV      = os.path.join(DATA_DIR, "segments_summary.csv")
SEG_EFF_CSV  = os.path.join(DATA_DIR, "segment_efforts.csv")
STREAMS_DIR  = os.path.join(DATA_DIR, "streams")

# Source-controlled copy
OUT_HTML       = os.path.join(_HERE, "strava.html")
# Netlify publish target (the Running Log dir is the publish root for ducktape.netlify.app)
DEPLOY_HTML    = os.path.normpath(os.path.join(_HERE, "..", "Running Log", "strava.html"))

PLOTLY_CDN = (
    '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>'
)

KM_TO_MI = 0.621371
M_TO_FT  = 3.28084

SPORT_DISPLAY = {
    "Running":          "Running",
    "MountainBikeRide": "Mountain Bike Ride",
    "Other":            "Other",
}

# Categorical sport colors — tuned for hue separation, matching the running-log
# workout-type palette (teal / amber / slate). Used by both themes.
SPORT_COLORS = {
    "Running":          "#2dd4bf",
    "MountainBikeRide": "#f59e0b",
    "Other":            "#8b949e",
}

# Trail Running — violet, distinct from teal Running and amber MTB
TRAIL_RUN_COLOR = "#a78bfa"

# Plotly figure colors — dark defaults. The theme toggle JS overrides these
# at runtime via Plotly.relayout reading the CSS custom properties.
BG_BASE        = "#0d1117"
BG_SURFACE     = "#161b22"
BG_ELEVATED    = "#1c2230"
BG_GLASS       = "rgba(22, 27, 34, 0.7)"
BORDER         = "rgba(48, 54, 61, 0.8)"
BORDER_SUBTLE  = "rgba(48, 54, 61, 0.4)"
TEXT_PRIMARY   = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_TERTIARY  = "#8b949e"
GRID           = "rgba(48, 54, 61, 0.4)"
ACCENT         = "#58a6ff"
ACCENT_DIM     = "rgba(88, 166, 255, 0.08)"
ACCENT_GLOW    = "rgba(88, 166, 255, 0.15)"

# Semantic trend colors for segment bars
FASTER  = "#2dd4bf"
SLOWER  = "#f87171"
NEUTRAL = "#58a6ff"
ELEVATION_COLOR = "#a78bfa"  # violet for elevation, distinct from accent blue

PLOT_FONT_FAMILY = "'Geist Mono', 'Fira Code', monospace"
TITLE_FONT_FAMILY = "'Geist', sans-serif"

# 92129 (Rancho Penasquitos, San Diego) — fixed map center
MAP_CENTER_LAT = 32.9545
MAP_CENTER_LON = -117.0910

# ─── Data helpers ─────────────────────────────────────────────────────────────

def load_activities():
    with open(ACT_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def load_segments():
    with open(SEG_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def mf(s):
    try:    return float(s)
    except: return None

def sport_category(sport_type):
    if sport_type in ("Run", "TrailRun"):  return "Running"
    if sport_type == "MountainBikeRide":   return "MountainBikeRide"
    return "Other"

def week_start(date_str):
    d = datetime.strptime(date_str[:10], "%Y-%m-%d")
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")

def fmt_time(total_min):
    secs = round((total_min or 0) * 60)
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fmt_pace(pace_min_per_km):
    secs = round(pace_min_per_km * 60)
    return f"{secs // 60}:{secs % 60:02d}"

def fmt_seg_time(secs):
    secs = round(float(secs))
    return f"{secs // 60}:{secs % 60:02d}"

def load_segment_efforts():
    if not os.path.exists(SEG_EFF_CSV):
        return []
    with open(SEG_EFF_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def activity_dict(rows):
    """Return activities keyed by string ID."""
    return {str(r["id"]): r for r in rows}

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


# ─── Plotly helpers ───────────────────────────────────────────────────────────

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

# ─── Chart builders ───────────────────────────────────────────────────────────

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

def chart_calendar(rows):
    """Hand-built SVG calendar (one grid per year), ported from the College
    Running Log heatmap. Returns a raw HTML/SVG string (not a go.Figure) so the
    cells inherit CSS variables and retint automatically with the page theme.
    Intensity = --accent at fill-opacity = clamp(mi / max_mi, 0.08, 1.0); the
    max is data-driven (actual max across all days)."""
    day_dist  = defaultdict(float)
    day_count = defaultdict(int)
    for r in rows:
        ds = r["start_date_local"][:10]
        day_dist[ds]  += mf(r["distance_km"]) or 0
        day_count[ds] += 1

    if not day_dist:
        return "<div class='hm-grid'>No data</div>", 0.0

    years  = sorted({ds[:4] for ds in day_dist})
    max_mi = max((km * KM_TO_MI for km in day_dist.values()), default=0.0)

    cell    = 11
    gap     = 2
    label_w = 28
    week_w  = cell + gap   # 13
    n_weeks = 54
    top_pad = 14           # room for month labels
    svg_w   = label_w + n_weeks * week_w + 8
    svg_h   = top_pad + 7 * week_w + 8

    rows_html = []
    for year in years:
        # Per-cell grids keyed by (dow, wnum) using %U week numbering, dow Sun..Sat.
        cells = []
        month_week = {}
        # Collect this year's days; track first week-number per month for labels.
        year_days = {}
        for ds, km in day_dist.items():
            if not ds.startswith(year):
                continue
            d    = datetime.strptime(ds, "%Y-%m-%d")
            wnum = int(d.strftime("%U"))
            dow  = (d.weekday() + 1) % 7
            m    = d.month
            if m not in month_week or wnum < month_week[m]:
                month_week[m] = wnum
            year_days[(dow, wnum)] = (ds, km * KM_TO_MI, day_count[ds])

        for wnum in range(n_weeks):
            for dow in range(7):
                x = label_w + wnum * week_w
                y = top_pad + dow * week_w
                rec = year_days.get((dow, wnum))
                if rec and rec[1] > 0:
                    ds, mi, cnt = rec
                    op = min(1.0, max(0.08, mi / max_mi)) if max_mi else 0.08
                    title = (f"{ds} · {mi:.1f} mi "
                             f"({cnt} {'activity' if cnt == 1 else 'activities'})")
                    cells.append(
                        f'<rect class="hm-cell" x="{x}" y="{y}" width="{cell}" '
                        f'height="{cell}" rx="2" fill="var(--accent)" '
                        f'fill-opacity="{op:.2f}"><title>{title}</title></rect>'
                    )
                else:
                    cells.append(
                        f'<rect class="hm-cell" x="{x}" y="{y}" width="{cell}" '
                        f'height="{cell}" rx="2" fill="var(--text-tertiary)" '
                        f'fill-opacity="0.10"></rect>'
                    )

        # Month labels at the top of each year's svg, at the first week of each month.
        month_labels = []
        for m, w in sorted(month_week.items()):
            mx = label_w + w * week_w
            month_labels.append(
                f'<text x="{mx}" y="10" class="hm-month">{MONTH_NAMES[m-1]}</text>'
            )

        # Day-of-week single-letter labels S,M,T,W,T,F,S at x=0 (fixed y per spec).
        dow_ys = [23, 36, 49, 62, 75, 88, 101]
        dow_labels = [
            f'<text x="0" y="{dow_ys[i]}" class="hm-dow">{lbl}</text>'
            for i, lbl in enumerate(("S", "M", "T", "W", "T", "F", "S"))
        ]

        rows_html.append(f"""
          <div class="hm-year-row">
            <div class="hm-year">{year}</div>
            <svg viewBox="0 0 {svg_w} {svg_h}" width="100%" preserveAspectRatio="xMinYMid meet">
              {"".join(month_labels)}
              {"".join(dow_labels)}
              {"".join(cells)}
            </svg>
          </div>""")

    legend = (
        '<div class="hm-legend hm-legend-intensity">'
        '<span class="hm-legend-meta">0 mi</span>'
        '<span class="hm-legend-grad"></span>'
        f'<span class="hm-legend-meta">{max_mi:.0f}+ mi</span>'
        '</div>'
    )
    grid = f'<div class="hm-grid">{"".join(rows_html)}</div>'
    return legend + grid, max_mi


def chart_volume(rows):
    weekly = defaultdict(lambda: defaultdict(float))
    weekly_other_sports = defaultdict(set)
    for r in rows:
        wk  = week_start(r["start_date_local"])
        cat = sport_category(r["sport_type"])
        weekly[wk][cat] += (mf(r["distance_km"]) or 0) * KM_TO_MI
        if cat == "Other":
            weekly_other_sports[wk].add(r["sport_type"])

    all_weeks = sorted(weekly)
    if not all_weeks:
        return go.Figure()

    fig = go.Figure()
    for cat in ["Running", "MountainBikeRide", "Other"]:
        ys = [round(weekly[wk].get(cat, 0), 2) for wk in all_weeks]
        if cat == "Other":
            texts = [
                f"Week of {wk}<br>Other: {weekly[wk].get(cat,0):.1f} mi"
                + (("<br>" + "<br>".join(sorted(weekly_other_sports[wk])))
                   if weekly_other_sports[wk] else "")
                for wk in all_weeks
            ]
        else:
            texts = [
                f"Week of {wk}<br>{SPORT_DISPLAY[cat]}: {weekly[wk].get(cat,0):.1f} mi"
                for wk in all_weeks
            ]
        fig.add_trace(go.Bar(
            x=all_weeks, y=ys, name=SPORT_DISPLAY[cat],
            marker_color=SPORT_COLORS[cat],
            marker_line_width=0,
            hovertext=texts, hoverinfo="text",
        ))

    tidy_dark(fig)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(
            title="Week", tickformat="%b %Y", showgrid=False,
            rangeslider=dict(visible=True, thickness=0.07,
                             bordercolor=BORDER_SUBTLE, borderwidth=1,
                             bgcolor=BG_GLASS),
        ),
        yaxis=dict(title="Distance (mi)"),
        # Stacked legend would collide with the bottom rangeslider (thickness
        # 0.07) and its mini-bar preview; place it horizontally fully below the
        # rangeslider + "Week" axis title, with extra bottom margin so nothing
        # clips.
        legend=dict(orientation="h", yanchor="top", y=-0.45,
                    x=0, xanchor="left"),
        margin=dict(b=130),
    )
    return fig


def chart_heartrate(rows):
    by_cat = defaultdict(lambda: {"x": [], "y": [], "ids": [], "text": []})
    for r in rows:
        hr = mf(r["average_heartrate"])
        if not hr or hr <= 0:
            continue
        cat = sport_category(r["sport_type"])
        ds  = r["start_date_local"][:10]
        by_cat[cat]["x"].append(ds)
        by_cat[cat]["y"].append(hr)
        by_cat[cat]["ids"].append(r["id"])
        sport_label = r["sport_type"] if cat == "Other" else SPORT_DISPLAY[cat]
        by_cat[cat]["text"].append(
            f"{r['name']}<br>{ds}<br>HR: {hr:.0f} bpm<br>{sport_label}"
        )

    fig = go.Figure()
    for cat in ["Running", "MountainBikeRide", "Other"]:
        d = by_cat[cat]
        if not d["x"]:
            continue
        fig.add_trace(go.Scatter(
            x=d["x"], y=d["y"], mode="markers",
            name=SPORT_DISPLAY[cat],
            marker=dict(color=SPORT_COLORS[cat], size=7, opacity=0.75,
                        line=dict(width=0)),
            hovertext=d["text"], hoverinfo="text",
            customdata=d["ids"],
        ))

    tidy_dark(fig)
    fig.update_layout(
        xaxis=dict(title="Date", showgrid=False),
        yaxis=dict(title="Avg Heart Rate (bpm)"),
    )
    return fig


def chart_pace(rows):
    by_cat = defaultdict(lambda: {"x": [], "y": [], "ids": [], "text": []})
    for r in rows:
        speed = mf(r["average_speed_kmh"])
        if not speed or speed <= 0:
            continue
        cat = sport_category(r["sport_type"])
        if cat not in ("Running", "MountainBikeRide"):
            continue
        ds  = r["start_date_local"][:10]
        val = (60.0 / (speed * KM_TO_MI)) if cat == "Running" else speed * KM_TO_MI
        label = (fmt_pace(val) + " /mi") if cat == "Running" else f"{val:.1f} mph"
        by_cat[cat]["x"].append(ds)
        by_cat[cat]["y"].append(round(val, 3))
        by_cat[cat]["ids"].append(r["id"])
        by_cat[cat]["text"].append(f"{r['name']}<br>{ds}<br>{label}<br>{r['sport_type']}")

    fig = go.Figure()
    run_vals = []
    mtb_vals = []

    for cat in ["Running", "MountainBikeRide"]:
        d = by_cat[cat]
        if not d["x"]:
            continue
        pairs = sorted(zip(d["x"], d["y"], d["ids"], d["text"]))
        xs, ys, ids, texts = map(list, zip(*pairs))
        yaxis = "y" if cat == "Running" else "y2"

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers", name=SPORT_DISPLAY[cat],
            marker=dict(color=SPORT_COLORS[cat], size=7, opacity=0.75,
                        line=dict(width=0)),
            hovertext=texts, hoverinfo="text",
            customdata=ids, yaxis=yaxis,
        ))

        if cat == "Running":
            run_vals = ys
        else:
            mtb_vals = ys

    run_range = [max(run_vals) * 1.05, min(run_vals) * 0.95] if run_vals else None
    mtb_range = [min(mtb_vals) * 0.90, max(mtb_vals) * 1.10] if mtb_vals else None

    run_tick_vals, run_tick_text = [], []
    if run_vals:
        lo, hi = min(run_vals) - 1.0, max(run_vals) + 1.0
        v = int(lo)
        while v <= hi:
            run_tick_vals.append(v)
            run_tick_text.append(fmt_pace(v))
            v += 1

    tidy_dark(fig)
    fig.update_layout(
        xaxis=dict(title="Date", showgrid=False),
        yaxis=dict(
            title="Pace (min/mi)", range=run_range,
            tickvals=run_tick_vals, ticktext=run_tick_text,
            gridcolor=GRID, zerolinecolor=GRID,
            tickfont=dict(color=TEXT_TERTIARY, size=10),
            title_font=dict(color=TEXT_SECONDARY, size=11),
        ),
        yaxis2=dict(
            title="Speed (mph)", range=mtb_range,
            overlaying="y", side="right",
            gridcolor="rgba(0,0,0,0)", zerolinecolor="rgba(0,0,0,0)",
            tickfont=dict(color=TEXT_TERTIARY, size=10),
            title_font=dict(color=TEXT_SECONDARY, size=11),
        ),
    )
    return fig


def chart_elevation(rows):
    # Mirror chart_volume: weekly elevation gain (ft) stacked by sport category.
    weekly = defaultdict(lambda: defaultdict(float))
    weekly_other_sports = defaultdict(set)
    for r in rows:
        wk  = week_start(r["start_date_local"])
        cat = sport_category(r["sport_type"])
        weekly[wk][cat] += (mf(r["total_elevation_gain_m"]) or 0) * M_TO_FT
        if cat == "Other":
            weekly_other_sports[wk].add(r["sport_type"])

    all_weeks = sorted(weekly)
    if not all_weeks:
        return go.Figure()

    fig = go.Figure()
    for cat in ["Running", "MountainBikeRide", "Other"]:
        ys = [round(weekly[wk].get(cat, 0), 1) for wk in all_weeks]
        if cat == "Other":
            texts = [
                f"Week of {wk}<br>Other: {weekly[wk].get(cat,0):,.0f} ft"
                + (("<br>" + "<br>".join(sorted(weekly_other_sports[wk])))
                   if weekly_other_sports[wk] else "")
                for wk in all_weeks
            ]
        else:
            texts = [
                f"Week of {wk}<br>{SPORT_DISPLAY[cat]}: {weekly[wk].get(cat,0):,.0f} ft"
                for wk in all_weeks
            ]
        fig.add_trace(go.Bar(
            x=all_weeks, y=ys, name=SPORT_DISPLAY[cat],
            marker_color=SPORT_COLORS[cat],
            marker_line_width=0,
            hovertext=texts, hoverinfo="text",
        ))

    tidy_dark(fig)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Week", tickformat="%b %Y", showgrid=False),
        yaxis=dict(title="Elevation Gain (ft)"),
    )
    return fig


def chart_segment_prs(segs):
    valid = [s for s in segs if s.get("effort_count") and s.get("best_time_s")]
    top20 = sorted(valid, key=lambda s: int(s["effort_count"]), reverse=True)[:20]
    top20 = list(reversed(top20))  # bottom-to-top for horizontal bar

    all_times = [mf(s["best_time_s"]) or 0 for s in top20]
    tv, tt = [], []
    if all_times:
        lo, hi = min(all_times), max(all_times)
        step  = 30
        start = int(lo // step) * step
        end   = int(hi // step) * step + step * 2
        tv = list(range(start, end, step))
        tt = [fmt_seg_time(v) for v in tv]

    fig = go.Figure()
    for sport_key, emoji, display_name in [
        ("Run",              "🏃‍♀️", "Running"),
        ("MountainBikeRide", "🚵‍♀️", "Mountain Bike Ride"),
    ]:
        subset = [s for s in top20 if s.get("sport_types", "").strip() == sport_key]
        if not subset:
            fig.add_trace(go.Bar(
                x=[], y=[], orientation="h",
                name=f"{emoji} {display_name}",
                marker_color=SPORT_COLORS.get(
                    "Running" if sport_key == "Run" else "MountainBikeRide", NEUTRAL
                ),
                hoverinfo="text",
            ))
            continue

        def _trend_arrow(tr):
            if tr < -2:  return "↓"
            if tr > 2:   return "↑"
            return "→"

        names  = [
            f"{s['segment_name']} ({s['effort_count']}) "
            f"{_trend_arrow(mf(s.get('recent_trend','0')) or 0)} {emoji}"
            for s in subset
        ]
        times  = [mf(s["best_time_s"]) or 0 for s in subset]
        trends = [mf(s.get("recent_trend", "0")) or 0 for s in subset]
        counts = [int(s["effort_count"]) for s in subset]
        colors = [
            FASTER if tr < -2 else (SLOWER if tr > 2 else NEUTRAL)
            for tr in trends
        ]
        texts = [
            f"{s['segment_name']}<br>PR: {fmt_seg_time(bt)}<br>Efforts: {c}<br>Trend: {tr:+.1f}s<br>Sport: {s.get('sport_types','')}"
            for s, bt, c, tr in zip(subset, times, counts, trends)
        ]
        fig.add_trace(go.Bar(
            x=times, y=names, orientation="h",
            marker_color=colors,
            marker_line_width=0,
            hovertext=texts, hoverinfo="text",
            name=f"{emoji} {display_name}",
        ))

    tidy_dark(fig)
    fig.update_layout(
        xaxis=dict(
            title="Best Time", tickvals=tv, ticktext=tt,
            showgrid=True, gridcolor=GRID,
        ),
        yaxis=dict(tickfont=dict(size=10, color=TEXT_TERTIARY)),
        barmode="overlay",
        showlegend=False,
        margin=dict(t=20, b=60, l=260, r=20),
    )
    return fig


def chart_map(rows):
    by_cat = defaultdict(lambda: {"lat": [], "lon": [], "text": [], "ids": []})
    for r in rows:
        ll = r.get("start_latlng", "").strip()
        if not ll:
            continue
        parts = ll.split(",")
        if len(parts) != 2:
            continue
        lat = mf(parts[0].strip())
        lon = mf(parts[1].strip())
        if lat is None or lon is None:
            continue
        cat = sport_category(r["sport_type"])
        ds  = r["start_date_local"][:10]
        km  = mf(r["distance_km"]) or 0
        by_cat[cat]["lat"].append(lat)
        by_cat[cat]["lon"].append(lon)
        by_cat[cat]["ids"].append(r["id"])
        by_cat[cat]["text"].append(f"{r['name']}<br>{ds}<br>{km * KM_TO_MI:.1f} mi")

    fig = go.Figure()
    for cat in ["Running", "MountainBikeRide", "Other"]:
        d = by_cat[cat]
        if not d["lat"]:
            continue
        fig.add_trace(go.Scattermap(
            lat=d["lat"], lon=d["lon"],
            mode="markers", name=SPORT_DISPLAY[cat],
            marker=dict(color=SPORT_COLORS[cat], size=9, opacity=0.85),
            hovertext=d["text"], hoverinfo="text",
            customdata=d["ids"],
        ))

    fig.update_layout(
        map=dict(
            style="carto-positron",
            center=dict(lat=MAP_CENTER_LAT, lon=MAP_CENTER_LON),
            zoom=11,
        ),
        legend=dict(
            orientation="h", y=0, x=0.5, xanchor="center",
            bgcolor="rgba(255,255,255,0.85)", bordercolor="#ccc", borderwidth=1,
            font=dict(color="#11161d", size=11, family=PLOT_FONT_FAMILY),
        ),
        margin=dict(t=10, b=10, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_SECONDARY, family=PLOT_FONT_FAMILY),
        hoverlabel=dict(
            bgcolor=BG_ELEVATED, bordercolor=BORDER,
            font=dict(family=PLOT_FONT_FAMILY, color=TEXT_PRIMARY, size=11),
        ),
    )
    return fig

# ─── New scatter plots ────────────────────────────────────────────────────────

RUN_COLOR   = SPORT_COLORS["Running"]      # teal  #2dd4bf
TRAIL_COLOR = TRAIL_RUN_COLOR              # violet #a78bfa
MTB_COLOR   = SPORT_COLORS["MountainBikeRide"]  # amber #f59e0b


# ── 1. Running: avg pace vs avg HR (activity-level, >1.5 km) ─────────────────

def chart_run_pace_vs_hr(rows):
    by = {
        "Run":      {"x": [], "y": [], "text": []},
        "TrailRun": {"x": [], "y": [], "text": []},
    }
    for r in rows:
        st = r.get("sport_type", "")
        if st not in ("Run", "TrailRun"):
            continue
        km    = mf(r["distance_km"]) or 0
        if km < 1.5:
            continue
        hr    = mf(r["average_heartrate"])
        speed = mf(r["average_speed_kmh"])
        if not hr or not speed or hr <= 0 or speed <= 0:
            continue
        pace  = 60.0 / (speed * KM_TO_MI)   # min/mi
        ds    = r["start_date_local"][:10]
        by[st]["x"].append(hr)
        by[st]["y"].append(round(pace, 4))
        by[st]["text"].append(
            f"{r['name']}<br>{ds}<br>{st}<br>"
            f"Pace: {fmt_pace(pace)}/mi<br>HR: {hr:.0f} bpm"
        )

    fig = go.Figure()
    colors  = {"Run": RUN_COLOR, "TrailRun": TRAIL_COLOR}
    labels  = {"Run": "Running", "TrailRun": "Trail Running"}
    r2_entries = []

    for st in ("Run", "TrailRun"):
        d = by[st]
        if not d["x"]:
            continue
        xs, ys, ts = _remove_outliers(d["x"], d["y"], d["text"])
        if not xs:
            continue
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers",
            name=labels[st],
            marker=dict(color=colors[st], size=7, opacity=0.75, line=dict(width=0)),
            hovertext=ts, hoverinfo="text",
        ))
        r2 = _add_regression_line(fig, xs, ys, colors[st])
        yp = 0.15 if st == "Run" else 0.05
        r2_entries.append((r2, colors[st], 0.98, yp))

    all_y = by["Run"]["y"] + by["TrailRun"]["y"]
    tv, tt = _pace_ticks(all_y)

    tidy_dark(fig)
    fig.update_layout(
        title=dict(text="Pace vs Heart Rate · Running Activities",
                   font=dict(color=TEXT_PRIMARY, size=12, family=TITLE_FONT_FAMILY),
                   x=0, xanchor="left"),
        xaxis=dict(title="Avg Heart Rate (bpm)"),
        yaxis=dict(title="Avg Pace (min/mi)", tickvals=tv, ticktext=tt,
                   autorange="reversed"),
        annotations=_r2_annotations(r2_entries),
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


# ── 2. Running: avg HR vs temperature °F (activity-level, >1.5 km) ───────────

def chart_run_hr_vs_temp(rows):
    by = {
        "Run":      {"x": [], "y": [], "text": []},
        "TrailRun": {"x": [], "y": [], "text": []},
    }
    for r in rows:
        st = r.get("sport_type", "")
        if st not in ("Run", "TrailRun"):
            continue
        km = mf(r["distance_km"]) or 0
        if km < 1.5:
            continue
        hr   = mf(r["average_heartrate"])
        tc   = mf(r["average_temp_c"])
        if not hr or tc is None or hr <= 0:
            continue
        tf   = tc * 9 / 5 + 32          # °C → °F
        ds   = r["start_date_local"][:10]
        by[st]["x"].append(round(tf, 1))
        by[st]["y"].append(hr)
        by[st]["text"].append(
            f"{r['name']}<br>{ds}<br>{st}<br>"
            f"Temp: {tf:.0f}°F<br>HR: {hr:.0f} bpm"
        )

    fig = go.Figure()
    colors  = {"Run": RUN_COLOR, "TrailRun": TRAIL_COLOR}
    labels  = {"Run": "Running", "TrailRun": "Trail Running"}
    r2_entries = []

    for st in ("Run", "TrailRun"):
        d = by[st]
        if not d["x"]:
            continue
        xs, ys, ts = _remove_outliers(d["x"], d["y"], d["text"])
        if not xs:
            continue
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers",
            name=labels[st],
            marker=dict(color=colors[st], size=7, opacity=0.75, line=dict(width=0)),
            hovertext=ts, hoverinfo="text",
        ))
        r2 = _add_regression_line(fig, xs, ys, colors[st])
        yp = 0.95 if st == "Run" else 0.85
        r2_entries.append((r2, colors[st], 0.98, yp))

    tidy_dark(fig)
    fig.update_layout(
        title=dict(text="Heart Rate vs Temperature · Running Activities",
                   font=dict(color=TEXT_PRIMARY, size=12, family=TITLE_FONT_FAMILY),
                   x=0, xanchor="left"),
        xaxis=dict(title="Temperature (°F)"),
        yaxis=dict(title="Avg Heart Rate (bpm)"),
        annotations=_r2_annotations(r2_entries),
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


# ─── Segment data preparation ─────────────────────────────────────────────────

def _seg_effort_points(seg_efforts, act_by_id, tort_map,
                       sport_filter, exclude_sports=("EBikeRide",)):
    """
    Build lists for segment scatter plots.

    sport_filter : tuple of sport_type strings to include, e.g. ("Run","TrailRun")
    Returns dict keyed by sport_type → {paces, hrs, grades, torts, texts}
    """
    out = {st: {"paces": [], "hrs": [], "grades": [], "torts": [], "texts": []}
           for st in sport_filter}

    for e in seg_efforts:
        aid   = str(e.get("activity_id", ""))
        act   = act_by_id.get(aid, {})
        sport = act.get("sport_type", "")
        if sport not in sport_filter or sport in exclude_sports:
            continue

        dist_m  = mf(e.get("segment_distance_m")) or 0
        elapsed = mf(e.get("elapsed_time_s")) or 0
        hr      = mf(e.get("average_heartrate"))
        grade   = mf(e.get("segment_avg_grade"))
        sid     = e.get("segment_id", "")
        name    = e.get("segment_name", "")
        ds      = (e.get("start_date_local") or "")[:10]

        if dist_m <= 0 or elapsed <= 0:
            continue

        # Pace / speed
        if sport == "MountainBikeRide":
            pace = (dist_m / elapsed) * 3.6 * KM_TO_MI   # mph
            pace_label = f"{pace:.1f} mph"
        else:
            pace = (elapsed / dist_m) * (1000 / 60) / KM_TO_MI  # min/mi
            pace_label = f"{fmt_pace(pace)}/mi"

        tort = tort_map.get(sid)

        parts = [f"{name}", f"{ds}", f"{sport}", f"Pace: {pace_label}"]
        if grade is not None:
            parts.append(f"Grade: {grade:.1f}%")
        if hr:
            parts.append(f"HR: {hr:.0f} bpm")
        if tort:
            parts.append(f"Tortuosity: {tort:.2f}")
        text = "<br>".join(parts)

        d = out[sport]
        d["paces"].append(round(pace, 4))
        d["hrs"].append(hr)
        d["grades"].append(grade)
        d["torts"].append(tort)
        d["texts"].append(text)

    return out


def _scatter_two_axis(x_label, y_label,
                      series,          # list of (xs, ys, name, color, texts)
                      title,
                      y_reversed=False,
                      y_ticks=None):   # (vals, texts) for pace axis
    """Generic scatter with regression lines + R² annotations."""
    fig = go.Figure()
    r2_entries = []
    y_positions = [0.95, 0.85, 0.75]

    for i, (xs, ys, name, color, texts) in enumerate(series):
        # Filter None pairs, then remove outliers
        pairs = [(x, y, t) for x, y, t in zip(xs, ys, texts)
                 if x is not None and y is not None]
        if not pairs:
            continue
        pxs, pys, pts = zip(*pairs)
        pxs, pys, pts = _remove_outliers(list(pxs), list(pys), list(pts))

        fig.add_trace(go.Scatter(
            x=pxs, y=pys, mode="markers",
            name=name,
            marker=dict(color=color, size=7, opacity=0.75, line=dict(width=0)),
            hovertext=pts, hoverinfo="text",
        ))
        r2 = _add_regression_line(fig, pxs, pys, color)
        yp = y_positions[i] if i < len(y_positions) else 0.05
        r2_entries.append((r2, color, 0.98, yp))

    tidy_dark(fig)
    y_upd = dict(title=y_label)
    if y_reversed:
        y_upd["autorange"] = "reversed"
    if y_ticks:
        y_upd["tickvals"], y_upd["ticktext"] = y_ticks

    fig.update_layout(
        title=dict(text=title,
                   font=dict(color=TEXT_PRIMARY, size=12, family=TITLE_FONT_FAMILY),
                   x=0, xanchor="left"),
        xaxis=dict(title=x_label),
        yaxis=y_upd,
        annotations=_r2_annotations(r2_entries),
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


# ── 3. Running segments: pace vs tortuosity ───────────────────────────────────

def chart_run_seg_pace_vs_tortuosity(seg_data):
    run   = seg_data.get("Run",      {})
    trail = seg_data.get("TrailRun", {})
    all_y = [y for y in run["paces"] + trail["paces"] if y]
    tv, tt = _pace_ticks(all_y)
    return _scatter_two_axis(
        x_label="Tortuosity (path length / straight-line distance)",
        y_label="Pace (min/mi)",
        series=[
            (run["torts"],   run["paces"],   "Running",       RUN_COLOR,   run["texts"]),
            (trail["torts"], trail["paces"], "Trail Running", TRAIL_COLOR, trail["texts"]),
        ],
        title="Pace vs Tortuosity · Running Segments",
        y_reversed=True,
        y_ticks=(tv, tt) if tv else None,
    )


# ── 4. Running segments: pace vs grade ───────────────────────────────────────

def chart_run_seg_pace_vs_grade(seg_data):
    run   = seg_data.get("Run",      {})
    trail = seg_data.get("TrailRun", {})
    all_y = [y for y in run["paces"] + trail["paces"] if y]
    tv, tt = _pace_ticks(all_y)
    return _scatter_two_axis(
        x_label="Segment Grade (%)",
        y_label="Pace (min/mi)",
        series=[
            (run["grades"],   run["paces"],   "Running",       RUN_COLOR,   run["texts"]),
            (trail["grades"], trail["paces"], "Trail Running", TRAIL_COLOR, trail["texts"]),
        ],
        title="Pace vs Grade · Running Segments",
        y_reversed=True,
        y_ticks=(tv, tt) if tv else None,
    )


# ── 5. Running segments: HR vs grade ─────────────────────────────────────────

def chart_run_seg_hr_vs_grade(seg_data):
    run   = seg_data.get("Run",      {})
    trail = seg_data.get("TrailRun", {})
    return _scatter_two_axis(
        x_label="Segment Grade (%)",
        y_label="Avg Heart Rate (bpm)",
        series=[
            (run["grades"],   run["hrs"],   "Running",       RUN_COLOR,   run["texts"]),
            (trail["grades"], trail["hrs"], "Trail Running", TRAIL_COLOR, trail["texts"]),
        ],
        title="Heart Rate vs Grade · Running Segments",
    )


# ── 6. MTB segments: pace vs tortuosity ──────────────────────────────────────

def chart_mtb_seg_pace_vs_tortuosity(seg_data):
    mtb = seg_data.get("MountainBikeRide", {})
    return _scatter_two_axis(
        x_label="Tortuosity (path length / straight-line distance)",
        y_label="Speed (mph)",
        series=[
            (mtb["torts"], mtb["paces"], "MTB", MTB_COLOR, mtb["texts"]),
        ],
        title="Speed vs Tortuosity · MTB Segments",
    )


# ── 7. MTB segments: pace vs grade ────────────────────────────────────────────

def chart_mtb_seg_pace_vs_grade(seg_data):
    mtb = seg_data.get("MountainBikeRide", {})
    return _scatter_two_axis(
        x_label="Segment Grade (%)",
        y_label="Speed (mph)",
        series=[
            (mtb["grades"], mtb["paces"], "MTB", MTB_COLOR, mtb["texts"]),
        ],
        title="Speed vs Grade · MTB Segments",
    )


# ── 8. MTB segments: HR vs grade ─────────────────────────────────────────────

def chart_mtb_seg_hr_vs_grade(seg_data):
    mtb = seg_data.get("MountainBikeRide", {})
    return _scatter_two_axis(
        x_label="Segment Grade (%)",
        y_label="Avg Heart Rate (bpm)",
        series=[
            (mtb["grades"], mtb["hrs"], "MTB", MTB_COLOR, mtb["texts"]),
        ],
        title="Heart Rate vs Grade · MTB Segments",
    )


# ─── Exploratory tab (V1-V8) — chart builders ─────────────────────────────────
# Colors by NAME from the existing palette (no new hex):
#   running teal  = SPORT_COLORS["Running"]      "#2dd4bf"
#   MTB amber     = SPORT_COLORS["MountainBikeRide"] "#f59e0b"
#   slate         = TEXT_SECONDARY               "#8b949e"
#   violet        = ELEVATION_COLOR              "#a78bfa"
#   accent (blue) = ACCENT                       "#58a6ff"
# Derived shades of the running teal (stated explicitly, not a new palette):
#   teal-dark  = rgba(13,148,136,1)   teal-light = rgba(94,234,212,1)
X_TEAL   = SPORT_COLORS["Running"]
X_AMBER  = SPORT_COLORS["MountainBikeRide"]
X_SLATE  = TEXT_SECONDARY
X_VIOLET = ELEVATION_COLOR
X_TEAL_DARK  = "rgba(13,148,136,1)"
X_TEAL_LIGHT = "rgba(94,234,212,1)"
X_ANN_BG = "rgba(13,17,23,0.65)"

# (MONTH_NAMES removed — identical to MONTH_NAMES defined earlier)


def _x_ann(fig, x, y, text, color=None, xanchor="right", yanchor="top",
           arrow=False, ax=0, ay=-30, ref="paper"):
    """Standard Exploratory annotation: plot font, size 10, dark bg pill."""
    fig.add_annotation(
        x=x, y=y, xref=ref, yref=ref if ref == "paper" else ref,
        text=text, showarrow=arrow, ax=ax, ay=ay,
        arrowcolor=color or X_VIOLET, arrowwidth=1,
        font=dict(family=PLOT_FONT_FAMILY, size=10,
                  color=color or X_SLATE),
        bgcolor=X_ANN_BG, bordercolor="rgba(0,0,0,0)",
        xanchor=xanchor, yanchor=yanchor,
    )


def _x_runs(rows):
    """Run/TrailRun typed records for Exploratory views."""
    out = []
    for r in rows:
        if r["sport_type"] not in ("Run", "TrailRun"):
            continue
        out.append(r)
    return out


def _x_month_key(date_str):
    return date_str[:7]  # YYYY-MM


def chart_x_mirage(rows):
    """V1 - The Temperature Mirage."""
    # Filter: runs with non-null speed + HR + temp -> n=181
    eff, temp, dates, names = [], [], [], []
    for r in _x_runs(rows):
        sp = mf(r["average_speed_kmh"]); hr = mf(r["average_heartrate"]); tp = mf(r["average_temp_c"])
        if sp is None or hr is None or tp is None or hr == 0:
            continue
        eff.append(sp / hr); temp.append(tp)
        dates.append(datetime.strptime(r["start_date_local"][:10], "%Y-%m-%d"))
        names.append(r["name"])
    eff = np.array(eff); temp = np.array(temp)
    n = len(eff)

    # Temp-adjust: OLS eff ~ temp; residuals
    b, a = np.polyfit(temp, eff, 1)
    resid = eff - (a + b * temp)
    # z-score both (ddof=0)
    raw_z = (eff - eff.mean()) / eff.std()
    adj_z = (resid - resid.mean()) / resid.std()

    first = min(dates)
    days = np.array([(d - first).days for d in dates], dtype=float)

    # Trend lines fit on RAW per-run points (x = days since first run)
    raw_slope, raw_int, raw_r, raw_p = ols_r_p(days, raw_z)
    adj_slope, adj_int, adj_r, adj_p = ols_r_p(days, adj_z)

    # Monthly bins (calendar year-month), mean per month
    mk = [_x_month_key(d.strftime("%Y-%m-%d")) for d in dates]
    months = sorted(set(mk))
    mid_dates, raw_means, adj_means = [], [], []
    for m in months:
        idx = [i for i, k in enumerate(mk) if k == m]
        if not idx:
            continue
        y, mm = int(m[:4]), int(m[5:7])
        mid_dates.append(datetime(y, mm, 15))
        raw_means.append(float(np.mean([raw_z[i] for i in idx])))
        adj_means.append(float(np.mean([adj_z[i] for i in idx])))

    fig = go.Figure()
    # (1) individual runs (behind)
    fig.add_trace(go.Scatter(
        x=dates, y=raw_z, mode="markers", name="Individual runs",
        marker=dict(color=X_TEAL, opacity=0.25, size=5),
        customdata=names,
        hovertemplate="%{customdata}<br>z=%{y:.2f}<extra></extra>",
    ))
    # (2) raw monthly mean
    fig.add_trace(go.Scatter(
        x=mid_dates, y=raw_means, mode="lines+markers", name="Raw (uncontrolled)",
        line=dict(color=X_SLATE, dash="dash"), marker=dict(color=X_SLATE, size=6),
        hovertemplate="%{x|%b %Y}<br>z = %{y:.2f}<extra></extra>",
    ))
    # (3) temp-adjusted monthly mean
    fig.add_trace(go.Scatter(
        x=mid_dates, y=adj_means, mode="lines+markers", name="Temperature-adjusted",
        line=dict(color=X_TEAL), marker=dict(color=X_TEAL, size=6),
        hovertemplate="%{x|%b %Y}<br>z = %{y:.2f}<extra></extra>",
    ))
    # (4) OLS on raw points (slate dashed) / (5) OLS on adjusted points (teal dashed)
    xline = np.array([days.min(), days.max()])
    xdt = [first + timedelta(days=int(d)) for d in xline]
    fig.add_trace(go.Scatter(
        x=xdt, y=raw_int + raw_slope * xline, mode="lines",
        line=dict(color=X_SLATE, dash="dash", width=1.5),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=xdt, y=adj_int + adj_slope * xline, mode="lines",
        line=dict(color=X_TEAL, dash="dash", width=1.5),
        showlegend=False, hoverinfo="skip",
    ))

    tidy_dark(fig)
    fig.update_layout(showlegend=True)
    # Let Plotly autorange so future months are never clipped (was frozen range).
    fig.update_xaxes(title_text="Month", tickformat="%b %y")
    fig.update_yaxes(title_text="Aerobic efficiency (z-score)", zeroline=True)
    _x_ann(fig, 0.98, 0.97,
           f"Raw r={raw_r:.3f}, p={raw_p:.3f} -> Adjusted r={adj_r:.3f}, p={adj_p:.3f}")
    return fig, dict(n=n, bins=len(months), raw_r=raw_r, raw_p=raw_p,
                     adj_r=adj_r, adj_p=adj_p)


X_V2_FEATURES = ["distance_km", "moving_time_min", "total_elevation_gain_m",
                 "average_speed_kmh", "average_heartrate", "max_heartrate",
                 "suffer_score", "calories"]
X_V2_LABELS = ["dist", "time", "elev", "speed", "avgHR", "maxHR", "suffer", "cal"]


def chart_x_archetypes(rows):
    """V2 - Athlete Archetypes (PCA biplot + k-means)."""
    feats, sports, names = [], [], []
    for r in rows:
        st = r["sport_type"]
        if st not in ("Run", "TrailRun", "MountainBikeRide"):
            continue
        vals = [mf(r[c]) for c in X_V2_FEATURES]
        if any(v is None for v in vals):  # complete cases only, no imputation
            continue
        feats.append(vals)
        sports.append(st)
        names.append(r["name"])
    M = np.array(feats, dtype=float)
    n = len(M)

    Z, _, _ = standardize(M)
    scores, loadings, evr = pca_svd(Z)
    lab, C, inertia = kmeans_best(Z, k=3, restarts=50, seed=42)

    pc1, pc2 = scores[:, 0], scores[:, 1]

    # Identify cluster meaning by centroid distance (orig units) so legend labels
    # are stable. Long/hard = highest mean distance among the two run-dominant
    # clusters; MTB = cluster whose members are mostly MTB.
    sports_arr = np.array(sports)
    clusters = sorted(set(lab.tolist()))
    info = {}
    for c in clusters:
        mask = lab == c
        mtb_frac = np.mean(sports_arr[mask] == "MountainBikeRide")
        info[c] = dict(mtb_frac=mtb_frac, mean_dist=M[mask, 0].mean(), size=int(mask.sum()))
    mtb_cluster = max(clusters, key=lambda c: info[c]["mtb_frac"])
    run_clusters = [c for c in clusters if c != mtb_cluster]
    long_cluster = max(run_clusters, key=lambda c: info[c]["mean_dist"])
    short_cluster = [c for c in run_clusters if c != long_cluster][0]
    label_of = {long_cluster: "Long/hard runs", short_cluster: "Short/easy runs",
                mtb_cluster: "MTB rides"}
    color_of = {long_cluster: X_TEAL_DARK, short_cluster: X_TEAL_LIGHT,
                mtb_cluster: X_AMBER}

    # Biplot arrow scale = 0.9 * max|score| / max|loading| (PC1/PC2 plane)
    max_score = max(abs(pc1).max(), abs(pc2).max())
    max_load = max(abs(loadings[0]).max(), abs(loadings[1]).max())
    scale = 0.9 * max_score / max_load  # ~8.669

    fig = go.Figure()
    # convex hulls per cluster (filled, faint), not in legend
    for c in clusters:
        mask = lab == c
        pts = np.column_stack([pc1[mask], pc2[mask]])
        hull = _x_convex_hull(pts)
        if hull is not None and len(hull) >= 3:
            hx = list(hull[:, 0]) + [hull[0, 0]]
            hy = list(hull[:, 1]) + [hull[0, 1]]
            fig.add_trace(go.Scatter(
                x=hx, y=hy, mode="lines", fill="toself",
                fillcolor=_x_rgba(color_of[c], 0.06),
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False, hoverinfo="skip",
            ))
    # markers: color by cluster, symbol by sport
    for c in clusters:
        mask = lab == c
        symbols = ["diamond" if s == "MountainBikeRide" else "circle"
                   for s in sports_arr[mask]]
        cd = [[names[i], label_of[c]] for i in np.where(mask)[0]]
        fig.add_trace(go.Scatter(
            x=pc1[mask], y=pc2[mask], mode="markers",
            name=f"{label_of[c]} (n={int(mask.sum())})",
            marker=dict(color=color_of[c], size=7, opacity=0.85,
                        symbol=symbols),
            customdata=cd,
            hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
        ))
    # 8 loading arrows from origin, with labels ringed at a common OUTER RADIUS.
    # The short arrow tips land mid-cloud; instead place every label at
    # R_label = 0.98 * max_score along its arrow's unit direction so labels ring
    # the sparse perimeter (right/upper-right/lower-right) regardless of arrow
    # length, and extend each line out to its label so the line still points at it.
    R_label = 0.98 * max_score
    for j, lbl in enumerate(X_V2_LABELS):
        lx, ly = loadings[0, j] * scale, loadings[1, j] * scale
        mag = math.hypot(lx, ly) or 1.0
        ux, uy = lx / mag, ly / mag
        ex, ey = ux * R_label, uy * R_label  # label / line-end position on outer ring
        fig.add_trace(go.Scatter(
            x=[0, ex], y=[0, ey], mode="lines",
            line=dict(color=X_SLATE, width=1.5),
            showlegend=False, hoverinfo="skip",
        ))
        # Pill bg uses the theme-adaptive X_ANN_BG (== DARK_PILL) so applyChartTheme()
        # retints it in light mode (it relayouts ALL annotations by index, paper- or
        # data-anchored).
        fig.add_annotation(x=ex, y=ey, text=lbl, showarrow=False,
                           font=dict(family=PLOT_FONT_FAMILY, size=9, color=X_SLATE),
                           bgcolor=X_ANN_BG)

    tidy_dark(fig)
    fig.update_layout(showlegend=True)
    fig.update_xaxes(title_text=f"PC1 - session size / effort ({evr[0]*100:.1f}%)")
    fig.update_yaxes(title_text=f"PC2 - sport signature: HR (+) vs elevation (-) ({evr[1]*100:.1f}%)")
    fig.add_annotation(x=0.02, y=0.02, xref="paper", yref="paper",
                       text="circle = run   diamond = MTB", showarrow=False,
                       font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
                       bgcolor=X_ANN_BG, xanchor="left", yanchor="bottom")
    sizes = {label_of[c]: info[c]["size"] for c in clusters}
    return fig, dict(n=n, evr1=evr[0]*100, evr2=evr[1]*100, scale=scale,
                     inertia=inertia, sizes=sizes)


def _x_rgba(color, alpha):
    """Return an rgba() string with given alpha from a hex or rgba color."""
    if color.startswith("rgba"):
        parts = color[color.index("(")+1:color.index(")")].split(",")
        r, g, b = parts[0].strip(), parts[1].strip(), parts[2].strip()
        return f"rgba({r},{g},{b},{alpha})"
    h = color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _x_convex_hull(points):
    """Andrew's monotone chain convex hull. points: Nx2 array. Returns hull
    vertices CCW, or None if fewer than 3 unique points."""
    pts = sorted(set(map(tuple, points.tolist())))
    if len(pts) < 3:
        return None
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    return np.array(hull)


def chart_x_cardiac(rows):
    """V3 - Two Cardiac Worlds."""
    run_hr, mtb_hr, run_max, mtb_max = [], [], [], []
    for r in rows:
        hr = mf(r["average_heartrate"])
        mx = mf(r["max_heartrate"])
        if hr is None:
            continue
        if r["sport_type"] in ("Run", "TrailRun"):
            run_hr.append(hr)
            if mx is not None: run_max.append(mx)
        elif r["sport_type"] == "MountainBikeRide":
            mtb_hr.append(hr)
            if mx is not None: mtb_max.append(mx)
    run = np.array(run_hr); mtb = np.array(mtb_hr)
    run_mean, mtb_mean = run.mean(), mtb.mean()
    run_max_m = float(np.mean(run_max)); mtb_max_m = float(np.mean(mtb_max))
    t, df, p = welch_ttest(run, mtb)

    # Derive bin/axis bounds from data (was frozen at 85-175).
    all_hr = np.concatenate([run, mtb])
    lo = math.floor(all_hr.min() / 5) * 5 - 5
    hi = math.ceil(all_hr.max() / 5) * 5 + 5
    bins = dict(start=lo, end=hi, size=5)
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=run, name="Run", marker_color=X_TEAL,
                               opacity=0.6, xbins=bins))
    fig.add_trace(go.Histogram(x=mtb, name="MTB", marker_color=X_AMBER,
                               opacity=0.6, xbins=bins))
    fig.update_layout(barmode="overlay")

    # mean lines
    for mval, col in [(run_mean, X_TEAL), (mtb_mean, X_AMBER)]:
        fig.add_vline(x=mval, line=dict(color=col, dash="dash", width=1.5))
    # max-HR markers near top
    fig.add_trace(go.Scatter(
        x=[run_max_m, mtb_max_m], y=[0, 0], mode="markers",
        marker=dict(color=[X_TEAL, X_AMBER], symbol="triangle-down", size=10),
        yaxis="y2", showlegend=False, hoverinfo="skip",
    ))

    tidy_dark(fig)
    fig.update_layout(showlegend=True,
                      yaxis2=dict(overlaying="y", side="right", range=[0, 1],
                                  showticklabels=False, showgrid=False))
    fig.update_xaxes(title_text="Average HR (bpm)", range=[lo, hi])
    fig.update_yaxes(title_text="Activities")
    # Extra top margin so the stat annotation sits cleanly above the plot area.
    fig.update_layout(margin=dict(t=60, b=40, l=50, r=20))
    fig.add_annotation(x=run_mean, yref="paper", y=0.95, text=f"Run mean {run_mean:.1f}")
    fig.add_annotation(x=mtb_mean, yref="paper", y=0.88, text=f"MTB mean {mtb_mean:.1f}",
                       font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_AMBER))
    # Moved fully above the plot area (was y=0.97 inside, overlapping the teal bars);
    # y=1.10 + the larger top margin keeps it clear of the in-plot "Run mean" label.
    fig.add_annotation(x=0.5, y=1.10, xref="paper", yref="paper",
                       text=f"delta = {run_mean-mtb_mean:.1f} bpm | Welch t={t:.2f} | p={p:.1e}",
                       showarrow=False, xanchor="center", yanchor="bottom",
                       font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
                       bgcolor=X_ANN_BG)
    fig.add_annotation(x=0.5, y=0.88, xref="paper", yref="paper",
                       text=f"max HR nearly identical ({run_max_m:.1f} vs {mtb_max_m:.1f})",
                       showarrow=False, xanchor="center", yanchor="top",
                       font=dict(family=PLOT_FONT_FAMILY, size=9, color=X_SLATE),
                       bgcolor=X_ANN_BG)
    # labeled vertical mean lines as annotations
    return fig, dict(t=t, df=df, p=p, n_run=len(run), n_mtb=len(mtb))


def chart_x_heat(rows):
    """V4 - She Pays Pace, Not Heart, for Heat."""
    temps, paces, hrs = [], [], []
    for r in _x_runs(rows):
        sp = mf(r["average_speed_kmh"]); tp = mf(r["average_temp_c"])
        if sp is None or tp is None or sp == 0:
            continue
        temps.append(tp); paces.append(60.0 / sp); hrs.append(mf(r["average_heartrate"]))
    temps = np.array(temps); paces = np.array(paces)
    # Fixed tercile cut points per recipe (rounded to 2dp to avoid float-interp
    # drift in the linear percentile). cool = temp < 9.00 (the lone temp==9.00
    # falls to mid); warm = temp >= 18.10 (ties at 18.10 -> warm). Yields n 66/65/68.
    q1 = round(np.percentile(temps, 100/3.0), 2)  # 9.00
    q2 = round(np.percentile(temps, 200/3.0), 2)  # 18.10
    cool = temps < q1
    warm = temps >= q2
    mid = ~cool & ~warm

    pace_cool, pace_mid, pace_warm = paces[cool], paces[mid], paces[warm]

    def hr_mean(mask):
        vals = [hrs[i] for i in np.where(mask)[0] if hrs[i] is not None]
        return float(np.mean(vals)) if vals else None
    hr_means = [hr_mean(cool), hr_mean(mid), hr_mean(warm)]

    t, df, p = welch_ttest(pace_cool, pace_warm)
    # HR cool vs warm Welch
    hc = np.array([hrs[i] for i in np.where(cool)[0] if hrs[i] is not None])
    hw = np.array([hrs[i] for i in np.where(warm)[0] if hrs[i] is not None])
    hrt, hrdf, hrp = welch_ttest(hc, hw)

    # Display in min/mi (= min/km / KM_TO_MI). Stats (Welch) stay in metric space
    # — the t/p are scale-invariant under the constant divisor, so no re-test.
    def to_mi(arr):
        return np.asarray(arr) / KM_TO_MI
    pace_cool_mi, pace_mid_mi, pace_warm_mi = to_mi(pace_cool), to_mi(pace_mid), to_mi(pace_warm)
    # Tercile cut temps displayed in F (q1=9.0C->48F, q2=18.1C->65F).
    q1_f = q1 * 9 / 5 + 32
    q2_f = q2 * 9 / 5 + 32
    cats = [f"Cool (<={q1_f:.0f}F)", "Mid", f"Warm (>={q2_f:.0f}F)"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    viodata = [(pace_cool_mi, X_SLATE), (pace_mid_mi, "rgba(245,158,11,0.5)"),
               (pace_warm_mi, X_AMBER)]
    for cat, (data, col) in zip(cats, viodata):
        # customdata carries M:SS pace strings since Plotly can't format min:sec natively.
        cd = [fmt_pace(v) for v in data]
        fig.add_trace(go.Violin(
            x=[cat]*len(data), y=data, name=cat, fillcolor=_x_rgba(col, 0.4),
            line_color=col, opacity=0.7, box_visible=True, meanline_visible=True,
            points=False, showlegend=False, customdata=cd,
            hovertemplate="%{x}<br>%{customdata} /mi<extra></extra>",
        ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=cats, y=hr_means, mode="lines+markers", line=dict(color=X_TEAL),
        marker=dict(color=X_TEAL), showlegend=False,
        hovertemplate="%{x}<br>mean HR %{y:.1f}<extra></extra>",
    ), secondary_y=True)

    tidy_dark(fig)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title_text="Temperature tercile")
    # min/mi pace ticks (M:SS), axis REVERSED so faster reads up.
    pv, pt = _pace_ticks(np.concatenate([pace_cool_mi, pace_mid_mi, pace_warm_mi]).tolist())
    fig.update_yaxes(title_text="Pace (min/mi, faster = up)", autorange="reversed",
                     tickvals=pv, ticktext=pt, secondary_y=False)
    fig.update_yaxes(title_text="Mean HR (bpm)", range=[145, 160], secondary_y=True)
    # Bottom margin holds both the x-axis title and the stat annotation below it.
    # b=96 (was 80) gives the y=-0.16 stat line room to sit fully inside the
    # 460px figure; at b=80 + y=-0.20 the text rendered past the SVG bottom edge.
    fig.update_layout(margin=dict(b=96))
    fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper",
                       text="teal line = mean HR (right axis)", showarrow=False,
                       xanchor="left", yanchor="top",
                       font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
                       bgcolor=X_ANN_BG)
    # Annotation per spec, recomputed in min/mi (M:SS). HR-flat clause pinned.
    # Sits fully BELOW the plot area (was y=0.02 inside, crossed the Mid violin's
    # long lower tail). y=-0.16 clears the "Temperature tercile" axis title while
    # staying inside the figure's bottom margin (b=96); y=-0.20 clipped at the edge.
    cool_mss = fmt_pace(float(pace_cool_mi.mean()))
    warm_mss = fmt_pace(float(pace_warm_mi.mean()))
    fig.add_annotation(
        x=0.5, y=-0.16, xref="paper", yref="paper", xanchor="center", yanchor="top",
        text=(f"Cool {cool_mss} vs Warm {warm_mss} /mi | "
              f"t={t:.2f} | p={p:.4f} | HR flat (t={hrt:.2f}, p={hrp:.2f})"),
        showarrow=False, font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
        bgcolor=X_ANN_BG)
    return fig, dict(t=t, p=p, hr_means=hr_means,
                     n_cool=int(cool.sum()), n_mid=int(mid.sum()), n_warm=int(warm.sum()),
                     q1=q1, q2=q2)


def chart_x_seasonal(rows):
    """V5 - The Seasonal Handoff."""
    run_km = [0.0]*12
    mtb_cnt = [0]*12
    temp_sum = [0.0]*12
    temp_n = [0]*12
    total_run = 0.0; total_mtb = 0
    for r in rows:
        m = int(r["start_date_local"][5:7]) - 1
        st = r["sport_type"]
        if st in ("Run", "TrailRun"):
            d = mf(r["distance_km"]) or 0
            run_km[m] += d; total_run += d
        elif st == "MountainBikeRide":
            mtb_cnt[m] += 1; total_mtb += 1
        tp = mf(r["average_temp_c"])
        if tp is not None:
            temp_sum[m] += tp; temp_n[m] += 1
    # Mean temp per month, displayed in F (policy: never display C).
    temp_mean = [(temp_sum[i]/temp_n[i]) * 9 / 5 + 32 if temp_n[i] else None
                 for i in range(12)]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=MONTH_NAMES, y=run_km, mode="lines", name="Run distance (km, summed)",
        fill="tozeroy", fillcolor="rgba(45,212,191,0.18)", line=dict(color=X_TEAL),
        hovertemplate="%{x}<br>%{y:.1f} km<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=MONTH_NAMES, y=mtb_cnt, name="MTB rides (count)",
        marker_color=X_AMBER, opacity=0.7,
        hovertemplate="%{x}<br>%{y} rides<extra></extra>",
    ), secondary_y=True)
    # faint slate temp line
    fig.add_trace(go.Scatter(
        x=MONTH_NAMES, y=temp_mean, mode="lines", name="Mean temp (F)",
        line=dict(color=X_SLATE, width=1, dash="dot"), opacity=0.5,
        hovertemplate="%{x}<br>%{y:.0f} F<extra></extra>",
    ), secondary_y=False)

    tidy_dark(fig)
    fig.update_layout(showlegend=True)
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Run distance (km, summed)", secondary_y=False)
    fig.update_yaxes(title_text="MTB rides (count)", secondary_y=True)
    # MTB blackout band Jul-Sep (violet @0.10)
    fig.add_vrect(x0="Jul", x1="Sep", fillcolor="rgba(167,139,250,0.10)",
                  line_width=0, layer="below",
                  annotation_text=f"MTB blackout - {int(mtb_cnt[6])} July rides",
                  annotation_position="top left",
                  annotation_font=dict(family=PLOT_FONT_FAMILY, size=9, color=X_VIOLET))
    return fig, dict(total_run=total_run, total_mtb=total_mtb,
                     sep_km=run_km[8], jul_mtb=mtb_cnt[6], run_km=run_km, mtb_cnt=mtb_cnt)


def chart_x_cadence(rows):
    """V6 - Cadence Is the Gearbox."""
    cad, spd, hr, names = [], [], [], []
    cad_n, spd_n, hr_n, names_n = [], [], [], []  # no-HR group
    for r in _x_runs(rows):
        c = mf(r["average_cadence"]); s = mf(r["average_speed_kmh"])
        if c is None or c <= 0 or s is None:
            continue
        h = mf(r["average_heartrate"])
        if h is None:
            cad_n.append(c); spd_n.append(s); names_n.append(r["name"])
        else:
            cad.append(c); spd.append(s); hr.append(h); names.append(r["name"])
    n = len(cad) + len(cad_n)
    all_cad = np.array(cad + cad_n)
    median_cad = float(np.median(all_cad))

    # OLS computed at build time from data (was hardcoded — stale on refetch)
    all_s = np.array(spd + spd_n)
    slope, intercept, r, p = ols_r_p(all_cad, all_s)
    # cadence-vs-HR correlation over the runs that HAVE hr (the colored trace)
    r_cad_hr = float(np.corrcoef(cad, hr)[0, 1]) if len(cad) > 1 else float("nan")

    # Display y as pace min/mi (REVERSED). speed km/h -> pace = 60/(speed*KM_TO_MI).
    def spd_to_pace_mi(speeds):
        return [60.0 / (s * KM_TO_MI) for s in speeds]
    pace = spd_to_pace_mi(spd)
    pace_n = spd_to_pace_mi(spd_n)

    fig = go.Figure()
    teal_scale = [[0, "rgba(13,148,136,0.15)"], [1, "rgba(45,212,191,1)"]]
    # customdata: [name, "M:SS"] — Plotly can't format M:SS natively.
    cd_main = [[names[i], fmt_pace(pace[i])] for i in range(len(pace))]
    fig.add_trace(go.Scatter(
        x=cad, y=pace, mode="markers", customdata=cd_main,
        marker=dict(color=hr, colorscale=teal_scale, cmin=85, cmax=171, size=7,
                    colorbar=dict(title="Avg HR")),
        showlegend=False,
        hovertemplate="%{customdata[0]}<br>%{x:.1f} spm, %{customdata[1]} /mi<extra></extra>",
    ))
    if cad_n:
        cd_n = [[names_n[i], fmt_pace(pace_n[i])] for i in range(len(pace_n))]
        fig.add_trace(go.Scatter(
            x=cad_n, y=pace_n, mode="markers", customdata=cd_n,
            marker=dict(color=X_SLATE, size=7), showlegend=False,
            hovertemplate="%{customdata[0]}<br>%{x:.1f} spm, %{customdata[1]} /mi (no HR)<extra></extra>",
        ))
    # OLS fit stays in speed space (slope/intercept verified, NOT refit); transform
    # the fitted line into pace space and sample densely -> renders as a smooth curve.
    xline = np.linspace(all_cad.min(), all_cad.max(), 120)
    yline = [60.0 / ((intercept + slope * x) * KM_TO_MI) for x in xline]
    fig.add_trace(go.Scatter(
        x=xline, y=yline, mode="lines",
        line=dict(color=X_SLATE, dash="dash", width=1.5),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_vline(x=median_cad, line=dict(color=X_SLATE, dash="dot", width=1))

    tidy_dark(fig)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title_text="Avg cadence (spm, single-leg)")
    # min/mi pace ticks (M:SS), REVERSED so faster reads up.
    pv, pt = _pace_ticks(pace + pace_n)
    fig.update_yaxes(title_text="Pace (min/mi, faster = up)", autorange="reversed",
                     tickvals=pv, ticktext=pt)
    fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper", xanchor="left",
                       yanchor="top",
                       text=f"r={r:.3f} | p={p:.1e} | cadence-HR only r={r_cad_hr:.2f}",
                       showarrow=False,
                       font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
                       bgcolor=X_ANN_BG)
    fig.add_annotation(x=0.02, y=0.02, xref="paper", yref="paper", xanchor="left",
                       yanchor="bottom", text="MTB excluded (no cadence data)",
                       showarrow=False,
                       font=dict(family=PLOT_FONT_FAMILY, size=9, color=X_SLATE),
                       bgcolor=X_ANN_BG)
    # Moved to the empty bottom band along the median line (was y=0.95, colliding
    # with the top-left stats box). Stays anchored at median_cad x so it still reads
    # as that vertical line's label; y=0.04 (paper) sits in the sparse low-pace region.
    fig.add_annotation(x=median_cad, yref="paper", y=0.04, yanchor="bottom",
                       text=f"median {median_cad:.1f} spm", showarrow=False,
                       font=dict(family=PLOT_FONT_FAMILY, size=9, color=X_SLATE),
                       bgcolor=X_ANN_BG)
    return fig, dict(slope=slope, intercept=intercept, r=r, n=n)


def chart_x_metronome(rows):
    """V7 - The Metronome and Its Tail."""
    run_pace, run_is_trail = [], []
    mtb_speed = []
    for r in rows:
        s = mf(r["average_speed_kmh"])
        if s is None or s == 0:
            continue
        if r["sport_type"] in ("Run", "TrailRun"):
            pace = 60.0 / s
            run_pace.append(pace)
            elev = mf(r["total_elevation_gain_m"]) or 0
            run_is_trail.append(r["sport_type"] == "TrailRun" or elev >= 300)
        elif r["sport_type"] == "MountainBikeRide":
            mtb_speed.append(s)
    run_pace = np.array(run_pace)
    mtb_speed = np.array(mtb_speed)

    # tail rule stays in metric pace space (pace > 6.5 min/km).
    tail_idx = [i for i in range(len(run_pace)) if run_pace[i] > 6.5]
    tail_n = len(tail_idx)
    n_trail = sum(1 for i in tail_idx if run_is_trail[i])
    n_social = tail_n - n_trail

    # Display units: run pace -> min/mi (/ KM_TO_MI), MTB speed -> mph (* KM_TO_MI).
    run_pace_mi = run_pace / KM_TO_MI
    mtb_speed_mph = mtb_speed * KM_TO_MI
    p10, p50, p90 = np.percentile(run_pace_mi, [10, 50, 90])
    mp10, mp50, mp90 = np.percentile(mtb_speed_mph, [10, 50, 90])

    fig = make_subplots(rows=1, cols=2, subplot_titles=["Run pace", "MTB speed"])
    # bin 0.4 min/mi (~the original 0.25 min/km granularity)
    fig.add_trace(go.Histogram(
        x=run_pace_mi, marker_color=X_TEAL, showlegend=False,
        xbins=dict(start=5.0, end=19.5, size=0.4),
    ), row=1, col=1)
    # bin 0.5 mph (~the original 1 km/h)
    fig.add_trace(go.Histogram(
        x=mtb_speed_mph, marker_color=X_AMBER, showlegend=False,
        xbins=dict(start=4.0, end=11.0, size=0.5),
    ), row=1, col=2)

    # central-80% vrect on left, median line (min/mi)
    fig.add_vrect(x0=p10, x1=p90, fillcolor="rgba(45,212,191,0.10)", line_width=0,
                  layer="below", row=1, col=1)
    fig.add_vline(x=p50, line=dict(color=X_TEAL, dash="dash", width=1.5), row=1, col=1)
    # MTB percentile lines (mph)
    for v in (mp10, mp50, mp90):
        fig.add_vline(x=v, line=dict(color=X_AMBER, dash="dash", width=1.5), row=1, col=2)

    tidy_dark(fig)
    # Size-16 subplot titles ("Run pace"/"MTB speed") need headroom; the default
    # t=20 margin from tidy_dark clips their tops against the SVG viewport.
    fig.update_layout(showlegend=False, margin=dict(t=44))
    # min/mi pace ticks (M:SS) on left axis.
    pv, pt = _pace_ticks(run_pace_mi.tolist())
    fig.update_xaxes(title_text="Pace (min/mi)", tickvals=pv, ticktext=pt, row=1, col=1)
    fig.update_xaxes(title_text="Speed (mph)", row=1, col=2)
    fig.update_yaxes(title_text="Runs", row=1, col=1)
    fig.update_yaxes(title_text="Rides", row=1, col=2)
    fig.add_annotation(x=0.0, y=1.0, xref="x domain", yref="y domain", row=1, col=1,
                       text=f"tail: {n_trail} trail (300m+ gain), {n_social} social",
                       showarrow=False, xanchor="left", yanchor="top",
                       font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
                       bgcolor=X_ANN_BG)
    fig.add_annotation(x=1.0, y=1.0, xref="x2 domain", yref="y2 domain", row=1, col=2,
                       text=f"p10={mp10:.1f} p50={mp50:.1f} p90={mp90:.1f} mph",
                       showarrow=False, xanchor="right", yanchor="top",
                       font=dict(family=PLOT_FONT_FAMILY, size=9, color=X_AMBER),
                       bgcolor=X_ANN_BG)
    return fig, dict(p10=p10, p50=p50, p90=p90, tail_n=tail_n,
                     mtb_p50=mp50, n_trail=n_trail, n_social=n_social)


def chart_x_load(rows):
    """V8 - Load, Monotony & the Spike Zone."""
    daily = defaultdict(float)
    for r in rows:
        ss = mf(r["suffer_score"]) or 0
        d = r["start_date_local"][:10]
        daily[d] += ss

    start = datetime(2024, 11, 20)
    end = datetime(2026, 6, 7)
    ndays = (end - start).days + 1  # 565
    dates = [start + timedelta(days=i) for i in range(ndays)]
    series = np.array([daily.get(d.strftime("%Y-%m-%d"), 0.0) for d in dates])
    total_suffer = float(series.sum())

    # 7d rolling SUM, right-aligned, min_periods=1
    roll7 = np.array([series[max(0, i-6):i+1].sum() for i in range(ndays)])
    # ACWR = 7d rolling mean / 28d rolling mean, min_periods=1
    mean7 = np.array([series[max(0, i-6):i+1].mean() for i in range(ndays)])
    mean28 = np.array([series[max(0, i-27):i+1].mean() for i in range(ndays)])
    acwr = np.divide(mean7, mean28, out=np.zeros(ndays), where=mean28 != 0)

    peak_i = int(np.argmax(roll7))
    peak_val = float(roll7[peak_i]); peak_date = dates[peak_i]

    # plot ACWR only from day 28 onward (index >= 27); break before
    acwr_plot = [acwr[i] if i >= 27 else None for i in range(ndays)]
    # day counts/median use all-day evaluation per recipe
    spike_days = int(np.sum(acwr > 1.5))
    median_acwr = float(np.median(acwr))

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # bands on Y2 behind
    bands = [(0.0, 0.8, "rgba(139,148,158,0.06)", "<0.8"),
             (0.8, 1.3, "rgba(45,212,191,0.08)", "0.8-1.3"),
             (1.3, 1.5, "rgba(245,158,11,0.10)", "1.3-1.5"),
             (1.5, 2.2, "rgba(248,113,113,0.14)", ">1.5")]
    for y0, y1, col, lbl in bands:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=col, line_width=0, layer="below",
                      secondary_y=True)
        fig.add_annotation(x=1.0, y=(y0+y1)/2, xref="paper", yref="y2",
                           text=lbl, showarrow=False, xanchor="right",
                           font=dict(family=PLOT_FONT_FAMILY, size=9, color=X_SLATE),
                           bgcolor="rgba(0,0,0,0)")

    fig.add_trace(go.Scatter(
        x=dates, y=roll7, mode="lines", name="7d suffer (sum)",
        line=dict(color=X_VIOLET, width=1.5),
        hovertemplate="%{x|%b %d %Y}<br>%{y:.0f}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=dates, y=acwr_plot, mode="lines", name="ACWR",
        line=dict(color=X_SLATE), connectgaps=False,
        hovertemplate="%{x|%b %d %Y}<br>ACWR %{y:.2f}<extra></extra>",
    ), secondary_y=True)

    tidy_dark(fig)
    fig.update_layout(showlegend=True)
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="7-day suffer score (sum)", secondary_y=False)
    fig.update_yaxes(title_text="ACWR (7d / 28d)", range=[0, 2.2], secondary_y=True)
    fig.add_annotation(x=peak_date, y=peak_val, xref="x", yref="y",
                       text=f"peak {peak_val:.0f} ({peak_date.strftime('%Y-%m-%d')})",
                       showarrow=True, arrowcolor=X_VIOLET, ax=0, ay=-30,
                       font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_VIOLET),
                       bgcolor=X_ANN_BG)
    # Moved out of the plot area (was y=0.97 inside, overlapping the peak suffer
    # line/area). Anchored above the plot on the left to clear the peak label
    # (center) and the right-edge band labels. Top margin bumped to make room.
    fig.update_layout(margin=dict(t=44, b=40, l=50, r=80))
    fig.add_annotation(x=0.0, y=1.07, xref="paper", yref="paper", xanchor="left",
                       yanchor="bottom", text=f"{spike_days} days in spike zone (>1.5)",
                       showarrow=False,
                       font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
                       bgcolor=X_ANN_BG)
    return fig, dict(peak=peak_val, peak_date=peak_date.strftime("%Y-%m-%d"),
                     spike_days=spike_days, median_acwr=median_acwr, days=ndays,
                     total_suffer=total_suffer)


# ─── Stats ────────────────────────────────────────────────────────────────────

def compute_stats(rows):
    run_rows   = [r for r in rows if r["sport_type"] in ("Run", "TrailRun")]
    mtb_rows   = [r for r in rows if r["sport_type"] == "MountainBikeRide"]
    run_dist   = sum((mf(r["distance_km"]) or 0) * KM_TO_MI for r in run_rows)
    mtb_dist   = sum((mf(r["distance_km"]) or 0) * KM_TO_MI for r in mtb_rows)
    total_elev = sum((mf(r["total_elevation_gain_m"]) or 0) * M_TO_FT for r in rows)
    longest    = max(((mf(r["distance_km"]) or 0) * KM_TO_MI for r in run_rows), default=0)
    longest_mtb = max(((mf(r["distance_km"]) or 0) * KM_TO_MI for r in mtb_rows), default=0)
    sport_counts = defaultdict(int)
    for r in rows:
        sport_counts[r["sport_type"]] += 1
    top_sport = max(sport_counts, key=sport_counts.get) if sport_counts else "—"
    return {
        "total_acts":   len(rows),
        "run_dist":     run_dist,
        "mtb_dist":     mtb_dist,
        "total_elev":   total_elev,
        "longest_run":  longest,
        "longest_mtb":  longest_mtb,
        "top_sport":    top_sport,
    }

def stat_card(num, lbl):
    return (
        f'<div class="stat-card">'
        f'<div class="stat-num">{num}</div>'
        f'<div class="stat-label">{lbl}</div>'
        f'</div>'
    )

# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = f"""
:root {{
  --bg-base: {BG_BASE};
  --bg-surface: {BG_SURFACE};
  --bg-elevated: {BG_ELEVATED};
  --bg-glass: {BG_GLASS};
  --topnav-bg: rgba(13, 17, 23, 0.7);
  --border: {BORDER};
  --border-subtle: {BORDER_SUBTLE};
  --text-primary: {TEXT_PRIMARY};
  --text-secondary: {TEXT_SECONDARY};
  --text-tertiary: {TEXT_TERTIARY};
  --grid: {GRID};
  --ann-pill-bg: rgba(13, 17, 23, 0.65);
  --bg-gradient-1: rgba(88, 166, 255, 0.06);
  --bg-gradient-2: rgba(245, 158, 11, 0.04);
  --accent: {ACCENT};
  --accent-glow: {ACCENT_GLOW};
  --accent-dim: {ACCENT_DIM};
  --running: #2dd4bf;
  --mtb: #f59e0b;
  --other: #8b949e;
  --elevation: {ELEVATION_COLOR};
  --faster: {FASTER};
  --slower: {SLOWER};
}}

:root.light {{
  --bg-base: #ffffff;
  --bg-surface: #f3f4f6;
  --bg-elevated: #ffffff;
  --bg-glass: rgba(255, 255, 255, 0.75);
  --topnav-bg: rgba(255, 255, 255, 0.8);
  --border: rgba(140, 149, 159, 0.55);
  --border-subtle: rgba(140, 149, 159, 0.3);
  --text-primary: #11161d;
  --text-secondary: #424a53;
  --text-tertiary: #424a53;
  --grid: rgba(140, 149, 159, 0.35);
  --ann-pill-bg: rgba(255, 255, 255, 0.75);
  --bg-gradient-1: rgba(9, 105, 218, 0.09);
  --bg-gradient-2: rgba(194, 113, 12, 0.07);
  --accent: #0550ae;
  --accent-glow: rgba(5, 80, 174, 0.18);
  --accent-dim: rgba(5, 80, 174, 0.10);
  --running: #0d9488;
  --mtb: #c2710c;
  --other: #475569;
  --elevation: #6d28d9;
  --faster: #0d9488;
  --slower: #c81e1e;
}}

* {{ box-sizing: border-box; }}

html, body {{
  margin: 0; padding: 0;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: 'Geist', system-ui, -apple-system, sans-serif;
  font-size: 14px;
  min-height: 100vh;
  background-image:
    radial-gradient(ellipse 80% 50% at 20% -10%, var(--bg-gradient-1) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 110%, var(--bg-gradient-2) 0%, transparent 60%);
}}

.shell {{ display: flex; flex-direction: column; min-height: 100vh; }}

/* Top nav */
.topnav {{
  position: sticky; top: 0; z-index: 50;
  background: var(--topnav-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-subtle);
}}
.topnav-row {{
  max-width: 1100px; margin: 0 auto;
  padding: 0 32px;
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px;
}}
.topnav-row.row1 {{ height: 48px; }}
.topnav-row.row2 {{ padding-top: 10px; padding-bottom: 11px; flex-wrap: wrap; }}

.wordmark {{ display: flex; align-items: baseline; gap: 10px; }}
.wordmark-name {{
  font-size: 22px; font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}}
.wordmark-meta {{ font-family: 'Geist Mono', monospace; font-size: 13px; color: var(--text-tertiary); }}

.topnav-actions {{ display: inline-flex; align-items: center; gap: 10px; }}

/* Back link to College Running Log */
.back-link {{
  display: inline-flex; align-items: center; gap: 6px;
  font-family: 'Geist', sans-serif;
  font-size: 11px; font-weight: 600;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  padding: 6px 12px; border-radius: 7px;
  cursor: pointer; text-decoration: none;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.back-link:hover {{
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-dim);
}}

/* Theme toggle (3-state: dark / system / light) */
.theme-toggle {{
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px; gap: 0;
}}
.theme-toggle button {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 22px;
  background: transparent; border: none;
  color: var(--text-secondary);
  cursor: pointer; border-radius: 5px;
  padding: 0;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.theme-toggle button:hover {{ color: var(--text-primary); }}
.theme-toggle button.active {{
  background: var(--accent-dim);
  color: var(--accent);
}}
.theme-toggle button svg {{
  width: 13px; height: 13px;
  stroke: currentColor; fill: none;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}}

/* Section nav */
.tabnav {{
  display: flex; gap: 4px; flex-wrap: wrap;
}}
.tab {{
  background: none; border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  padding: 8px 12px;
  cursor: pointer; text-decoration: none;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.tab:hover {{ color: var(--text-primary); }}
.tab.active {{
  color: var(--text-primary);
  border-bottom-color: var(--accent);
}}

/* Page routing */
.view {{ display: none; }}
.view.active {{ display: block; }}

/* Main content */
main {{
  flex: 1;
  max-width: 1100px; width: 100%;
  margin: 0 auto;
  padding: 32px 32px 80px;
}}

.page-header {{ margin-bottom: 24px; }}
.page-header h1 {{
  margin: 0;
  font-size: 26px; font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}}
.page-header .date-range {{
  font-family: 'Geist Mono', monospace;
  font-size: 13px;
  color: var(--text-tertiary);
  margin-top: 6px;
}}

.section-anchor {{
  font-size: 12px; font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin: 28px 0 14px;
}}

@keyframes fadeUp {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}

.card {{
  background: var(--bg-glass);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  animation: fadeUp 240ms cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
  min-width: 0;
}}
.card .plotly-graph-div {{ max-width: 100%; }}
.card-title {{
  font-size: 12px; font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 20px;
}}
.attribution {{ font-size:13.5px; color:var(--text-secondary); line-height:1.65; margin:0; }}
.plot-caption {{ font-size:13.5px; color:var(--text-secondary); line-height:1.65; margin:12px 0 0; }}

/* Activity calendar (hand-built SVG, ported from the College Running Log) */
.hm-grid {{ display: flex; flex-direction: column; gap: 10px; overflow-x: auto; }}
.hm-year-row {{ display: flex; align-items: center; gap: 8px; }}
.hm-year {{
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--text-tertiary);
  width: 36px; flex-shrink: 0;
}}
.hm-year-row svg {{ flex: 1; min-width: 800px; }}
.hm-cell {{ transition: transform 120ms cubic-bezier(0.16, 1, 0.3, 1); transform-origin: center; transform-box: fill-box; }}
.hm-cell:hover {{ transform: scale(1.4); }}
.hm-month {{ fill: var(--text-tertiary); font-size: 9px; font-family: 'Geist Mono', monospace; }}
.hm-dow   {{ fill: var(--text-tertiary); font-size: 9px; font-family: 'Geist Mono', monospace; }}
.hm-legend {{
  margin-top: 4px; margin-bottom: 14px;
  display: flex; gap: 8px; align-items: center;
  font-size: 10px; color: var(--text-tertiary);
  font-family: 'Geist Mono', monospace;
}}
.hm-legend-meta {{ color: var(--text-secondary); }}
.hm-legend-grad {{
  display: inline-block;
  width: 140px; height: 10px; border-radius: 3px;
  background: linear-gradient(
    to right,
    color-mix(in srgb, var(--accent) 10%, transparent),
    var(--accent)
  );
}}

/* Stat cards */
.stat-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}}
.stat-card {{
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 18px 20px;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.stat-num {{
  font-family: 'Geist Mono', monospace;
  font-size: 24px; font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  line-height: 1.1;
}}
.stat-label {{
  margin-top: 6px;
  font-size: 11px; font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-secondary);
}}

@media (max-width: 900px) {{
  .stat-grid {{ grid-template-columns: repeat(3, 1fr); }}
}}
@media (max-width: 560px) {{
  .stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .topnav-row {{ padding: 0 16px; }}
  main {{ padding: 24px 16px 60px; }}
  .page-header h1 {{ font-size: 22px; }}
}}

/* Segment filter pills */
.seg-filter {{
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px; gap: 0;
  margin-bottom: 14px;
}}
.seg-btn {{
  background: transparent; border: none;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif; font-size: 11px;
  padding: 4px 12px; border-radius: 5px;
  cursor: pointer;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.seg-btn:hover {{ color: var(--text-primary); }}
.seg-btn.active {{
  background: var(--accent-dim);
  color: var(--accent);
}}

/* Detail panel */
.detail-backdrop {{
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.45);
  opacity: 0; pointer-events: none;
  transition: opacity 200ms ease;
  z-index: 90;
}}
.detail-backdrop.open {{ opacity: 1; pointer-events: auto; }}
.detail-panel {{
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 420px; max-width: 100vw;
  background: var(--bg-surface);
  border-left: 1px solid var(--border);
  box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
  transform: translateX(100%);
  transition: transform 240ms cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 100;
  display: flex; flex-direction: column;
  overflow: hidden;
}}
.detail-panel.open {{ transform: translateX(0); }}
.detail-header {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}}
.detail-title {{
  font-family: 'Geist', sans-serif;
  font-size: 14px; font-weight: 600;
  color: var(--text-primary);
}}
.detail-close {{
  background: none; border: none;
  color: var(--text-secondary);
  font-size: 22px; line-height: 1;
  cursor: pointer; padding: 4px 12px;
  border-radius: 6px;
  transition: background 150ms, color 150ms;
}}
.detail-close:hover {{ background: var(--bg-elevated); color: var(--text-primary); }}
.detail-body {{ flex: 1; overflow-y: auto; padding: 20px; }}
.d-name {{
  font-size: 15px; font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}}
.d-date {{
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 18px;
}}
.d-stats {{ display: flex; flex-wrap: wrap; gap: 10px; }}
.d-stat {{
  flex: 1 1 100px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px 14px;
  text-align: center;
}}
.d-stat-val {{
  font-family: 'Geist Mono', monospace;
  font-size: 18px; font-weight: 600;
  color: var(--text-primary);
  line-height: 1.1;
}}
.d-stat-lbl {{
  font-size: 10px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-tertiary);
  margin-top: 4px;
}}
.d-hint {{
  font-size: 13px;
  color: var(--text-tertiary);
  text-align: center;
  margin-top: 12px;
  padding: 18px;
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
}}

/* Rangeslider cursor (Plotly) */
.rangeslider-slidebox,
.rangeslider-handle-min,
.rangeslider-handle-max {{ cursor: grab; }}
.rangeslider-slidebox:active,
.rangeslider-handle-min:active,
.rangeslider-handle-max:active {{ cursor: grabbing; }}
"""

# ─── JS ───────────────────────────────────────────────────────────────────────

def build_js(act_json, sync_ids, click_ids):
    return f"""
var ACT_DATA  = {act_json};
var SYNC_IDS  = {json.dumps(sync_ids)};
var CLICK_IDS = {json.dumps(click_ids)};
var syncing   = false;

// ─── Detail panel ───────────────────────────────────────────────────────────
function closeDetail() {{
  document.getElementById('detail-panel').classList.remove('open');
  document.getElementById('detail-backdrop').classList.remove('open');
}}
function showDetail(actId) {{
  var a = ACT_DATA[String(actId)];
  if (!a) return;
  var esc = function(s) {{ return String(s).replace(/</g,'&lt;').replace(/>/g,'&gt;'); }};
  var html = '';
  html += '<div class="d-name">' + esc(a.name) + '</div>';
  html += '<div class="d-date">' + a.date + ' · ' + esc(a.sport) + '</div>';
  html += '<div class="d-stats">';
  html += '<div class="d-stat"><div class="d-stat-val">' + a.dist_mi.toFixed(1) + '</div><div class="d-stat-lbl">mi</div></div>';
  if (a.hr)      html += '<div class="d-stat"><div class="d-stat-val">' + a.hr + '</div><div class="d-stat-lbl">avg bpm</div></div>';
  if (a.elev_ft) html += '<div class="d-stat"><div class="d-stat-val">' + a.elev_ft.toLocaleString() + '</div><div class="d-stat-lbl">elev ft</div></div>';
  html += '<div class="d-stat"><div class="d-stat-val">' + a.elapsed + '</div><div class="d-stat-lbl">time</div></div>';
  if (a.pace)    html += '<div class="d-stat"><div class="d-stat-val">' + esc(a.pace) + '</div><div class="d-stat-lbl">pace/speed</div></div>';
  html += '</div>';
  document.getElementById('detail-body').innerHTML = html;
  document.getElementById('detail-panel').classList.add('open');
  document.getElementById('detail-backdrop').classList.add('open');
}}

// ─── Segment filter (trace 0 = Running, trace 1 = MTB) ─────────────────────
function filterSegs(type, btn) {{
  var el = document.getElementById('chart-segs');
  if (!el) return;
  var vis = type === 'all'  ? [true,  true]  :
            type === 'run'  ? [true,  false] :
                              [false, true];
  Plotly.restyle(el, {{visible: vis}}, [0, 1]);
  document.querySelectorAll('.seg-btn').forEach(function(b) {{
    b.classList.remove('active');
  }});
  if (btn) btn.classList.add('active');
}}

// ─── Cross-chart date sync ─────────────────────────────────────────────────
function syncRange(sourceId, ed) {{
  if (syncing) return;
  var x0   = ed['xaxis.range[0]'];
  var x1   = ed['xaxis.range[1]'];
  var auto = ed['xaxis.autorange'];
  if (x0 === undefined && x1 === undefined && !auto) return;
  syncing = true;
  var promises = [];
  SYNC_IDS.forEach(function(id) {{
    if (id === sourceId) return;
    var el = document.getElementById(id);
    if (!el) return;
    if (auto) {{
      promises.push(Plotly.relayout(el, {{'xaxis.autorange': true}}));
    }} else {{
      var upd = {{}};
      if (x0 !== undefined) upd['xaxis.range[0]'] = x0;
      if (x1 !== undefined) upd['xaxis.range[1]'] = x1;
      promises.push(Plotly.relayout(el, upd));
    }}
  }});
  Promise.all(promises).then(function() {{ syncing = false; }});
}}

// ─── Theme toggle (light / dark / system) ──────────────────────────────────
(function() {{
  var root = document.documentElement;
  var mq = window.matchMedia('(prefers-color-scheme: light)');
  var STORAGE_KEY = 'strava-theme';

  function getStoredMode() {{
    var v = localStorage.getItem(STORAGE_KEY);
    return (v === 'light' || v === 'dark' || v === 'system') ? v : 'system';
  }}
  function effectiveTheme(mode) {{
    if (mode === 'system') return mq.matches ? 'light' : 'dark';
    return mode;
  }}
  function cssVar(name) {{
    return getComputedStyle(root).getPropertyValue(name).trim();
  }}
  // Dark-theme gray text hexes baked into figures by tidy_dark / chart builders.
  // Annotations using THESE are re-colored on theme change to the current
  // secondary text color.
  // Includes the light-theme --text-secondary/--text-tertiary grey (#424a53 ==
  // rgb(66,74,83)) so that once an annotation has been retinted to the light
  // grey, switching back to dark still matches and retints to #8b949e. Without
  // it the light->dark transition was one-way (label stuck at low-contrast light
  // grey on the dark plot).
  var GRAY_TEXT = ['#8b949e', '#e6edf3', '#424a53', 'rgb(66,74,83)'];
  // The translucent dark pill bg baked into Exploratory annotations.
  var DARK_PILL = 'rgba(13,17,23,0.65)';
  // Brand-colored annotation text (teal/amber/violet) is baked with the DARK
  // palette hex by the chart builders, but the dark variants are low-contrast on
  // white (amber 2.15, violet 2.72). Each pair maps both palette variants of a
  // brand color to the CSS var, so the text is retinted to the current theme's
  // variant (keeping brand identity while fixing contrast) and toggling back to
  // dark restores the bright variant automatically.
  var BRAND_TEXT = [
    {{ cssVar: '--running',   variants: ['#2dd4bf', '#0d9488'] }},
    {{ cssVar: '--mtb',       variants: ['#f59e0b', '#c2710c'] }},
    {{ cssVar: '--elevation', variants: ['#a78bfa', '#6d28d9'] }},
  ];
  function normColor(c) {{ return (c == null ? '' : ('' + c)).toLowerCase().replace(/\\s+/g, ''); }}
  function isGrayText(c) {{
    var n = normColor(c);
    for (var i = 0; i < GRAY_TEXT.length; i++) {{ if (n === GRAY_TEXT[i]) return true; }}
    return false;
  }}
  function brandTextVar(c) {{
    var n = normColor(c);
    for (var i = 0; i < BRAND_TEXT.length; i++) {{
      var variants = BRAND_TEXT[i].variants;
      for (var j = 0; j < variants.length; j++) {{
        if (n === normColor(variants[j])) return BRAND_TEXT[i].cssVar;
      }}
    }}
    return null;
  }}
  function applyChartTheme() {{
    var textPrimary   = cssVar('--text-primary');
    var textSecondary = cssVar('--text-secondary');
    var textTertiary  = cssVar('--text-tertiary');
    var grid          = cssVar('--grid');
    var bgElevated    = cssVar('--bg-elevated');
    var border        = cssVar('--border');
    var pillBg        = cssVar('--ann-pill-bg');
    // Current-theme brand variants for retinting brand-colored annotation text.
    var brandColors   = {{}};
    for (var bi = 0; bi < BRAND_TEXT.length; bi++) {{
      brandColors[BRAND_TEXT[bi].cssVar] = cssVar(BRAND_TEXT[bi].cssVar);
    }}
    document.querySelectorAll('.plotly-graph-div').forEach(function(el) {{
      if (!el || !el._fullLayout || !window.Plotly) return;
      var fl  = el._fullLayout;
      var upd = {{
        'font.color': textSecondary,
        'legend.font.color': textSecondary,
        'hoverlabel.font.color': textPrimary,
        'hoverlabel.bgcolor': bgElevated,
        'hoverlabel.bordercolor': border,
        // chart titles are baked #e6edf3 by tidy_dark -> invisible on white.
        'title.font.color': textPrimary,
      }};
      // 1. Every x/y axis (incl. subplot axes xaxis2, yaxis2, ... matched dynamically).
      Object.keys(fl).forEach(function(k) {{
        if (/^[xy]axis\\d*$/.test(k)) {{
          upd[k + '.tickfont.color']    = textTertiary;
          upd[k + '.title.font.color']  = textSecondary;
          upd[k + '.gridcolor']         = grid;
          upd[k + '.zerolinecolor']     = grid;
        }}
      }});
      // 3 & 5. Annotations: recolor gray-text ones to secondary text; retint
      //        brand-colored ones to the current theme's brand variant.
      //        Swap the dark pill bg for the theme-driven pill var.
      if (fl.annotations) {{
        for (var i = 0; i < fl.annotations.length; i++) {{
          var a = fl.annotations[i];
          if (a && a.font && isGrayText(a.font.color)) {{
            upd['annotations[' + i + '].font.color'] = textSecondary;
          }} else if (a && a.font) {{
            var bvar = brandTextVar(a.font.color);
            if (bvar) {{
              upd['annotations[' + i + '].font.color'] = brandColors[bvar];
            }}
          }}
          if (a && normColor(a.bgcolor) === normColor(DARK_PILL)) {{
            upd['annotations[' + i + '].bgcolor'] = pillBg;
          }}
        }}
      }}
      // Weekly Volume rangeslider: retint its bg/border so it reads in light mode.
      if (fl.xaxis && fl.xaxis.rangeslider) {{
        upd['xaxis.rangeslider.bgcolor']     = cssVar('--bg-glass');
        upd['xaxis.rangeslider.bordercolor'] = cssVar('--border-subtle');
      }}
      try {{ Plotly.relayout(el, upd); }} catch (e) {{ /* chart may not be ready */ }}
      // 4. Colorbars (V6 "Avg HR") are baked per-trace via marker.colorbar.
      try {{
        var data = el.data || [];
        var tIdx = [];
        for (var t = 0; t < data.length; t++) {{
          if (data[t] && data[t].marker && data[t].marker.colorbar) tIdx.push(t);
        }}
        if (tIdx.length) {{
          Plotly.restyle(el, {{
            'marker.colorbar.tickfont.color': textTertiary,
            'marker.colorbar.title.font.color': textSecondary,
          }}, tIdx);
        }}
      }} catch (e) {{ /* no colorbar on this chart */ }}
    }});
  }}
  // Reachable from the separate tab-routing IIFE so hidden-tab charts get
  // retinted (not just resized) when their tab is first shown.
  window.__applyChartTheme = applyChartTheme;
  function setActiveButton(mode) {{
    document.querySelectorAll('.theme-toggle button').forEach(function(b) {{
      b.classList.toggle('active', b.dataset.theme === mode);
    }});
  }}
  function applyTheme(mode) {{
    var eff = effectiveTheme(mode);
    root.classList.toggle('light', eff === 'light');
    setActiveButton(mode);
    applyChartTheme();
  }}

  var current = getStoredMode();
  applyTheme(current);

  document.querySelectorAll('.theme-toggle button').forEach(function(b) {{
    b.addEventListener('click', function() {{
      current = b.dataset.theme;
      localStorage.setItem(STORAGE_KEY, current);
      applyTheme(current);
    }});
  }});

  mq.addEventListener('change', function() {{
    if (current === 'system') applyTheme('system');
  }});
}})();

// ─── Wire chart listeners on load ──────────────────────────────────────────
window.addEventListener('load', function() {{
  SYNC_IDS.forEach(function(id) {{
    var el = document.getElementById(id);
    if (!el) return;
    el.on('plotly_relayout', function(ed) {{ syncRange(id, ed); }});
  }});
  CLICK_IDS.forEach(function(id) {{
    var el = document.getElementById(id);
    if (!el) return;
    el.on('plotly_click', function(data) {{
      if (!data.points || !data.points.length) return;
      var pt = data.points[0];
      if (pt.customdata) showDetail(String(pt.customdata));
    }});
  }});

  // Close detail panel on backdrop click or Escape
  var bd = document.getElementById('detail-backdrop');
  if (bd) bd.addEventListener('click', closeDetail);
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeDetail();
  }});

  // ─── Page/tab routing ─────────────────────────────────────────────────
  (function() {{
    var tabs = document.querySelectorAll('.tab[data-view]');
    function activateView(name) {{
      tabs.forEach(function(t) {{
        t.classList.toggle('active', t.dataset.view === name);
      }});
      document.querySelectorAll('.view').forEach(function(v) {{
        var on = v.id === 'view-' + name;
        v.classList.toggle('active', on);
        if (on && window.Plotly) {{
          v.querySelectorAll('.js-plotly-plot').forEach(function(el) {{
            Plotly.Plots.resize(el);
          }});
        }}
      }});
      // Retint chart titles/axes to the current theme (resize alone won't).
      if (window.__applyChartTheme) window.__applyChartTheme();
      history.replaceState(null, '', '#' + name);
    }}
    tabs.forEach(function(t) {{
      t.addEventListener('click', function() {{ activateView(t.dataset.view); }});
    }});
    var hash = (location.hash || '').replace('#', '');
    activateView(document.getElementById('view-' + hash) ? hash : 'overview');
  }})();
}});
"""

# ─── Page assembly ────────────────────────────────────────────────────────────

THEME_TOGGLE_SVGS = {
    "light":  '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
    "dark":   '<svg viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/></svg>',
    "system": '<svg viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 21h8M12 18v3"/></svg>',
}


def build_page(rows, segs):
    stats = compute_stats(rows)

    # Embed activity data for detail panel
    act_by_id = {}
    for r in rows:
        km    = mf(r["distance_km"]) or 0
        hr    = mf(r["average_heartrate"])
        elev  = (mf(r["total_elevation_gain_m"]) or 0) * M_TO_FT
        etime = mf(r["elapsed_time_min"]) or 0
        speed = mf(r["average_speed_kmh"])
        cat   = sport_category(r["sport_type"])
        pace_str = ""
        if speed and speed > 0:
            pace_str = (fmt_pace(60.0 / (speed * KM_TO_MI)) + " /mi") if cat == "Running" else f"{speed * KM_TO_MI:.1f} mph"
        act_by_id[str(r["id"])] = {
            "name":    r["name"],
            "date":    r["start_date_local"][:10],
            "sport":   r["sport_type"],
            "dist_mi": round(km * KM_TO_MI, 2),
            "hr":      round(hr) if hr else None,
            "elev_ft": round(elev),
            "elapsed": fmt_time(etime),
            "pace":    pace_str,
        }
    act_json = json.dumps(act_by_id, ensure_ascii=False)

    print("  calendar...")
    cal, cal_max_mi = chart_calendar(rows)
    print("    calendar data-driven max_mi=%.2f mi" % cal_max_mi)
    print("  volume...")
    vol    = chart_volume(rows)
    print("  heart rate...")
    hr_c   = chart_heartrate(rows)
    print("  pace...")
    pac    = chart_pace(rows)
    print("  elevation...")
    elev_c = chart_elevation(rows)
    print("  segments...")
    segs_c = chart_segment_prs(segs)
    print("  map...")
    mp     = chart_map(rows)

    # ── New scatter plots ──────────────────────────────────────────────────────
    print("  loading segment efforts...")
    seg_efforts = load_segment_efforts()
    act_by_id   = activity_dict(rows)

    print("  run pace vs HR...")
    run_pace_hr   = chart_run_pace_vs_hr(rows)
    print("  run HR vs temp...")
    run_hr_temp   = chart_run_hr_vs_temp(rows)

    print("  computing tortuosity...")
    tort_map = compute_tortuosity_map(seg_efforts, act_by_id)

    print("  building run segment data...")
    run_seg_data = _seg_effort_points(
        seg_efforts, act_by_id, tort_map,
        sport_filter=("Run", "TrailRun"),
    )
    print("  building MTB segment data...")
    mtb_seg_data = _seg_effort_points(
        seg_efforts, act_by_id, tort_map,
        sport_filter=("MountainBikeRide",),
        exclude_sports=("EBikeRide",),
    )

    print("  run seg pace vs tortuosity...")
    run_pace_tort = chart_run_seg_pace_vs_tortuosity(run_seg_data)
    print("  run seg pace vs grade...")
    run_pace_grade = chart_run_seg_pace_vs_grade(run_seg_data)
    print("  run seg HR vs grade...")
    run_hr_grade  = chart_run_seg_hr_vs_grade(run_seg_data)
    print("  MTB seg pace vs tortuosity...")
    mtb_pace_tort = chart_mtb_seg_pace_vs_tortuosity(mtb_seg_data)
    print("  MTB seg pace vs grade...")
    mtb_pace_grade = chart_mtb_seg_pace_vs_grade(mtb_seg_data)
    print("  MTB seg HR vs grade...")
    mtb_hr_grade  = chart_mtb_seg_hr_vs_grade(mtb_seg_data)

    # ── Exploratory tab (V1-V8) ────────────────────────────────────────────────
    print("  exploratory V1 temperature mirage...")
    v1, v1m = chart_x_mirage(rows)
    print("    V1 n=%d bins=%d raw_r=%.3f raw_p=%.3f adj_r=%.3f adj_p=%.3f"
          % (v1m["n"], v1m["bins"], v1m["raw_r"], v1m["raw_p"], v1m["adj_r"], v1m["adj_p"]))
    print("  exploratory V2 archetypes...")
    v2, v2m = chart_x_archetypes(rows)
    print("    V2 n=%d EVR PC1=%.1f%% PC2=%.1f%% scale=%.3f inertia=%.2f sizes=%s"
          % (v2m["n"], v2m["evr1"], v2m["evr2"], v2m["scale"], v2m["inertia"],
             {k: v2m["sizes"][k] for k in sorted(v2m["sizes"])}))
    print("  exploratory V3 cardiac...")
    v3, v3m = chart_x_cardiac(rows)
    print("    V3 welch t=%.3f df=%.2f p=%.3e n_run=%d n_mtb=%d"
          % (v3m["t"], v3m["df"], v3m["p"], v3m["n_run"], v3m["n_mtb"]))
    print("  exploratory V4 heat...")
    v4, v4m = chart_x_heat(rows)
    print("    V4 welch t=%.3f p=%.5f HR=%s n=%d/%d/%d q=%.2f/%.2f"
          % (v4m["t"], v4m["p"], ["%.2f" % h for h in v4m["hr_means"]],
             v4m["n_cool"], v4m["n_mid"], v4m["n_warm"], v4m["q1"], v4m["q2"]))
    print("  exploratory V5 seasonal handoff...")
    v5, v5m = chart_x_seasonal(rows)
    print("    V5 total_run_km=%.1f total_mtb=%d sep_km=%.1f jul_mtb=%d"
          % (v5m["total_run"], v5m["total_mtb"], v5m["sep_km"], v5m["jul_mtb"]))
    print("  exploratory V6 cadence...")
    v6, v6m = chart_x_cadence(rows)
    print("    V6 slope=%.4f intercept=%.4f r=%.4f n=%d"
          % (v6m["slope"], v6m["intercept"], v6m["r"], v6m["n"]))
    print("  exploratory V7 metronome...")
    v7, v7m = chart_x_metronome(rows)
    print("    V7 run p10=%.3f p50=%.3f p90=%.3f tail_n=%d mtb_p50=%.3f"
          % (v7m["p10"], v7m["p50"], v7m["p90"], v7m["tail_n"], v7m["mtb_p50"]))
    print("  exploratory V8 load...")
    v8, v8m = chart_x_load(rows)
    print("    V8 peak=%.0f on %s spike_days=%d median_acwr=%.3f days=%d total_suffer=%.0f"
          % (v8m["peak"], v8m["peak_date"], v8m["spike_days"], v8m["median_acwr"],
             v8m["days"], v8m["total_suffer"]))

    dates = sorted(r["start_date_local"][:10] for r in rows)
    date_range = f"{dates[0]} – {dates[-1]}" if dates else "—"

    stats_html = (
        '<div class="stat-grid">'
        + stat_card(stats["total_acts"], "Total Activities")
        + stat_card(f"{stats['run_dist']:,.0f} mi", "Running")
        + stat_card(f"{stats['mtb_dist']:,.0f} mi", "Mountain Bike")
        + stat_card(f"{stats['total_elev']:,.0f} ft", "Total Elevation")
        + stat_card(f"{stats['longest_run']:.1f} mi", "Longest Run")
        + stat_card(f"{stats['longest_mtb']:.1f} mi", "Longest MTB")
        + "</div>"
    )

    nav_links = "".join(
        f'<button class="tab" data-view="{v}">{l}</button>'
        for v, l in [
            ("overview",  "Overview"),
            ("volume",    "Volume"),
            ("trends",    "Trends"),
            ("segments",  "Segments"),
            ("map",       "Map"),
            ("exploratory", "Exploratory"),
        ]
    )

    theme_buttons = "".join(
        f'<button type="button" data-theme="{mode}" title="{title}" aria-label="{aria}">{svg}</button>'
        for mode, title, aria, svg in [
            ("light",  "Light",  "Light theme",       THEME_TOGGLE_SVGS["light"]),
            ("dark",   "Dark",   "Dark theme",        THEME_TOGGLE_SVGS["dark"]),
            ("system", "System", "Use system theme",  THEME_TOGGLE_SVGS["system"]),
        ]
    )

    SYNC_IDS  = ["chart-volume", "chart-hr", "chart-pace", "chart-elev"]
    CLICK_IDS = ["chart-hr", "chart-pace", "chart-map"]

    js = build_js(act_json, SYNC_IDS, CLICK_IDS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Strava Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;700&family=Geist+Mono:wght@400;600&display=swap" rel="stylesheet">
  {PLOTLY_CDN}
  <style>{CSS}</style>
</head>
<body>

<div class="shell">

<header class="topnav">
  <div class="topnav-row row1">
    <div class="wordmark">
      <span class="wordmark-name">Strava Dashboard</span>
      <span class="wordmark-meta">{date_range}</span>
    </div>
    <div class="topnav-actions">
      <a class="back-link" href="/" title="College Running Log">
        <span>←</span><span>College Running Log</span>
      </a>
      <div class="theme-toggle" role="group" aria-label="Theme">{theme_buttons}</div>
    </div>
  </div>
  <div class="topnav-row row2">
    <nav class="tabnav">{nav_links}</nav>
  </div>
</header>

<main>

<section id="view-overview" class="view active">
  <div class="page-header">
    <h1>Overview</h1>
    <div class="date-range">{date_range}</div>
  </div>
  {stats_html}
  <div class="card">
    <div class="card-title">Activity Calendar</div>
    {cal}
  </div>
</section>

<section id="view-volume" class="view">
  <div class="section-anchor">Volume</div>
  <div class="card">
    <div class="card-title">Weekly Volume</div>
    {fig_html(vol, 440, div_id="chart-volume")}
  </div>
  <div class="card">
    <div class="card-title">Weekly Elevation Gain</div>
    {fig_html(elev_c, 360, div_id="chart-elev")}
  </div>
</section>

<section id="view-trends" class="view">
  <div class="section-anchor">Trends</div>
  <div class="card">
    <div class="card-title">Heart Rate</div>
    {fig_html(hr_c, 420, div_id="chart-hr")}
  </div>
  <div class="card">
    <div class="card-title">Pace / Speed</div>
    {fig_html(pac, 440, div_id="chart-pace")}
  </div>

  <div class="section-anchor" style="margin-top:32px">Running · Activity Trends</div>
  <div class="card">
    <div class="card-title">Pace vs Heart Rate</div>
    {fig_html(run_pace_hr, 420, div_id="chart-run-pace-hr")}
  </div>
  <div class="card">
    <div class="card-title">Heart Rate vs Temperature</div>
    {fig_html(run_hr_temp, 420, div_id="chart-run-hr-temp")}
  </div>

  <div class="section-anchor" style="margin-top:32px">Running · Segment Scatter</div>
  <div class="card">
    <div class="card-title">Pace vs Tortuosity</div>
    {fig_html(run_pace_tort, 420, div_id="chart-run-seg-pace-tort")}
  </div>
  <div class="card">
    <div class="card-title">Pace vs Grade</div>
    {fig_html(run_pace_grade, 420, div_id="chart-run-seg-pace-grade")}
  </div>
  <div class="card">
    <div class="card-title">Heart Rate vs Grade</div>
    {fig_html(run_hr_grade, 420, div_id="chart-run-seg-hr-grade")}
  </div>

  <div class="section-anchor" style="margin-top:32px">MTB · Segment Scatter</div>
  <div class="card">
    <div class="card-title">Speed vs Tortuosity</div>
    {fig_html(mtb_pace_tort, 420, div_id="chart-mtb-seg-pace-tort")}
  </div>
  <div class="card">
    <div class="card-title">Speed vs Grade</div>
    {fig_html(mtb_pace_grade, 420, div_id="chart-mtb-seg-pace-grade")}
  </div>
  <div class="card">
    <div class="card-title">Heart Rate vs Grade</div>
    {fig_html(mtb_hr_grade, 420, div_id="chart-mtb-seg-hr-grade")}
  </div>
</section>

<section id="view-segments" class="view">
  <div class="section-anchor">Segments</div>
  <div class="card">
    <div class="card-title">Top 20 Segments by Effort Count</div>
    <div class="seg-filter">
      <button class="seg-btn active" onclick="filterSegs('all',this)">All</button>
      <button class="seg-btn" onclick="filterSegs('run',this)">🏃‍♀️ Running</button>
      <button class="seg-btn" onclick="filterSegs('mtb',this)">🚵‍♀️ MTB</button>
    </div>
    {fig_html(segs_c, 540, div_id="chart-segs")}
  </div>
</section>

<section id="view-map" class="view">
  <div class="section-anchor">Map</div>
  <div class="card">
    <div class="card-title">Activity Locations</div>
    {fig_html(mp, 520, div_id="chart-map")}
  </div>
</section>

<section id="view-exploratory" class="view">
  <div class="section-anchor">Exploratory</div>
  <div class="card">
    <div class="card-title">About This Section</div>
    <p class="attribution">This section was created entirely by Claude — Anthropic's <strong>Claude Fable 5</strong> model (<code>claude-fable-5</code>) acting as orchestrator, dispatching the strava-data-analyst, strava-creativity, strava-viz-design, strava-developer, and strava-qa subagents.</p>
  </div>
  <div class="card">
    <div class="card-title">The Temperature Mirage</div>
    {fig_html(v1,460,"chart-x-mirage")}
    <p class="plot-caption">When the weather cools down, runners often feel like they're getting fitter — but is that real? This chart tracks aerobic efficiency (pace per heartbeat) over time: the dashed line is the raw trend, the solid line adjusts for temperature using a statistical technique called OLS regression. The annotation in the top-right corner shows two correlation values (r) and their p-values — one before and one after the temperature correction. If the adjusted r is smaller or less significant, some of your apparent fitness gains were weather-driven, not true fitness gains.</p>
  </div>
  <div class="card">
    <div class="card-title">Athlete Archetypes</div>
    {fig_html(v2,520,"chart-x-archetypes")}
    <p class="plot-caption">A technique called PCA compresses 8 workout metrics — distance, elevation, pace, heart rate, calories, and more — into two summary axes, then k-means clustering groups activities into 3 natural archetypes. Think of it as a map where nearby dots are workouts with similar effort profiles. The arrows show which original metrics pull in each direction; longer arrows mean that metric has more influence on the layout. The convex hull outlines and legend show how many activities fall into each cluster.</p>
  </div>
  <div class="card">
    <div class="card-title">Two Cardiac Worlds</div>
    {fig_html(v3,420,"chart-x-cardiac")}
    <p class="plot-caption">These overlapping histograms compare average heart rate across all runs (teal) vs. mountain bike rides (amber). The vertical dashed lines mark the mean heart rate for each sport. The annotation box shows the gap (Δ bpm) between those means plus a Welch t-test result — a statistical check that confirms whether the difference is real or could be random chance (p &lt; 0.05 means it's real). The triangle markers at the top track max heart rate: despite the sustained intensity gap, your cardiovascular ceiling is nearly identical across both sports.</p>
  </div>
  <div class="card">
    <div class="card-title">She Pays Pace, Not Heart, for Heat</div>
    {fig_html(v4,460,"chart-x-heat")}
    <p class="plot-caption">Each violin shape shows the spread of run paces across three temperature bands — cool, mid, and warm. Wider = more spread in that band; the box inside marks the middle 50% of runs. The teal line (right axis) tracks average heart rate across those same bands. The bottom annotation gives the exact average pace for the coolest and warmest conditions, plus two p-values: one confirming pace does change significantly with temperature, and one showing heart rate does not — meaning in the heat you move slower without working cardiovascularly harder.</p>
  </div>
  <div class="card">
    <div class="card-title">The Seasonal Handoff</div>
    {fig_html(v5,440,"chart-x-seasonal")}
    <p class="plot-caption">The teal filled area shows total running distance per month; the amber bars show MTB ride counts; the faint dot-dash line is average temperature. Where one sport rises, the other falls. The shaded "MTB blackout" annotation marks a stretch where ride counts dropped to near zero — the label inside it shows how few MTB rides occurred that month, likely due to trail conditions rather than preference.</p>
  </div>
  <div class="card">
    <div class="card-title">Cadence Is the Gearbox</div>
    {fig_html(v6,460,"chart-x-cadence")}
    <p class="plot-caption">Each dot is a run, colored by heart rate intensity (darker teal = higher HR). The dashed trendline shows the OLS-fitted relationship between cadence and pace. The annotation box in the top-left reports two correlations: cadence→pace (r and p-value) and cadence→heart rate (r and p-value). A strong cadence–pace r with a weak cadence–HR r means cadence functions like a mechanical gear ratio — spinning faster makes you go faster without necessarily driving your heart harder. The vertical dotted line marks the median cadence.</p>
  </div>
  <div class="card">
    <div class="card-title">The Metronome and Its Tail</div>
    {fig_html(v7,420,"chart-x-metronome")}
    <p class="plot-caption">Two side-by-side distributions: run pace in min/mi (left) and mountain bike speed in mph (right). The shaded band on the left covers the middle 80% of runs (p10 to p90 — the 10th and 90th percentiles); the vertical dashed lines on the right mark the same percentile boundaries for MTB. The annotation on the left's slow tail identifies what those outlier runs actually are — trail workouts with heavy elevation gain, or group social runs where pace takes a back seat.</p>
  </div>
  <div class="card">
    <div class="card-title">Load, Monotony &amp; the Spike Zone</div>
    {fig_html(v8,480,"chart-x-load")}
    <p class="plot-caption">The violet line (left axis) is your 7-day rolling suffer score — a Strava-derived measure of cumulative training stress. The gray line (right axis) is the ACWR ratio: your current week's training divided by your 4-week rolling average. A ratio near 1.0 means you're training consistently; the colored bands show risk zones — teal is the sweet spot, amber is elevated risk, and red is the spike zone (&gt;1.5) where injury risk rises sharply. The labeled arrow marks your highest single-week training peak; the counter at the top shows how many days you spent in the spike zone.</p>
  </div>
</section>

</main>

</div>

<!-- Detail panel -->
<div id="detail-backdrop" class="detail-backdrop"></div>
<aside id="detail-panel" class="detail-panel" role="complementary">
  <div class="detail-header">
    <span class="detail-title">Activity Details</span>
    <button class="detail-close" onclick="closeDetail()" aria-label="Close">×</button>
  </div>
  <div class="detail-body" id="detail-body">
    <div class="d-hint">Click any point on the Heart Rate, Pace, or Map charts to see activity details.</div>
  </div>
</aside>

<script>{js}</script>
</body>
</html>"""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    rows = load_activities()
    segs = load_segments()
    print(f"  {len(rows)} activities, {len(segs)} segments")

    print("Building dashboard...")
    html = build_page(rows, segs)

    # Source-controlled copy
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"-> {OUT_HTML}")

    # Netlify publish copy (the Running Log dir is the publish root)
    os.makedirs(os.path.dirname(DEPLOY_HTML), exist_ok=True)
    with open(DEPLOY_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"-> {DEPLOY_HTML}")

    print(f"   {len(html):,} bytes")


if __name__ == "__main__":
    main()
