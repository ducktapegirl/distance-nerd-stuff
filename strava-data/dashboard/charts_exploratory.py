"""The 8 'V1-V8' exploratory charts (Exploratory tab). Each returns
(go.Figure, metrics_dict) — the metrics feed the build-time print summaries."""

import math
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import ELEVATION_COLOR, KM_TO_MI, PLOT_FONT_FAMILY, SLOWER, SPORT_COLORS, TEXT_SECONDARY
from .charts_production import MONTH_NAMES
from .data import fmt_pace, mf
from .geometry_stats import _pace_ticks, kmeans_best, ols_r_p, pca_svd, standardize, welch_ttest
from .theme import tidy_dark

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


def _heat_view(rows, metric):
    """Bin runs into the fixed Cool/Mild/Warm/Hot bands by `metric`
    (`average_temp_c` or `apparent_temp_c`) and compute per-band pace (min/mi),
    HR means, and the Cool-vs-Hot Welch stats. The 48/62/75°F edges are shared
    across metrics (not recomputed per metric) so the bands are identical."""
    temps, paces, hrs = [], [], []
    for r in _x_runs(rows):
        sp = mf(r["average_speed_kmh"]); tp = mf(r[metric])
        if sp is None or tp is None or sp == 0:
            continue
        temps.append(tp); paces.append(60.0 / sp); hrs.append(mf(r["average_heartrate"]))
    temps = np.array(temps); paces = np.array(paces)
    # Fixed °F band edges (48/62/75), converted to °C for filtering — data files
    # stay metric, display is °F-only per policy. Bands: cool/mild/warm/hot.
    def f_to_c(f):
        return (f - 32) * 5 / 9
    t48, t62, t75 = f_to_c(48), f_to_c(62), f_to_c(75)
    cool = temps < t48
    mild = (temps >= t48) & (temps < t62)
    warm = (temps >= t62) & (temps < t75)
    hot = temps >= t75

    pace_cool, pace_mild, pace_warm, pace_hot = paces[cool], paces[mild], paces[warm], paces[hot]

    def hr_mean(mask):
        vals = [hrs[i] for i in np.where(mask)[0] if hrs[i] is not None]
        return float(np.mean(vals)) if vals else None
    hr_means = [hr_mean(cool), hr_mean(mild), hr_mean(warm), hr_mean(hot)]

    t, df, p = welch_ttest(pace_cool, pace_hot)
    # HR cool vs hot Welch
    hc = np.array([hrs[i] for i in np.where(cool)[0] if hrs[i] is not None])
    hh = np.array([hrs[i] for i in np.where(hot)[0] if hrs[i] is not None])
    hrt, hrdf, hrp = welch_ttest(hc, hh)

    # Display in min/mi (= min/km / KM_TO_MI). Stats (Welch) stay in metric space
    # — the t/p are scale-invariant under the constant divisor, so no re-test.
    def to_mi(arr):
        return np.asarray(arr) / KM_TO_MI
    paces_mi = [to_mi(pace_cool), to_mi(pace_mild), to_mi(pace_warm), to_mi(pace_hot)]
    n = [int(cool.sum()), int(mild.sum()), int(warm.sum()), int(hot.sum())]
    return dict(paces_mi=paces_mi, hr_means=hr_means, t=t, p=p,
                hrt=hrt, hrp=hrp, n=n, n_total=sum(n))


def chart_x_heat(rows):
    """V4 - She Pays Pace, Not Heart, for Heat.

    Two precomputed views in one figure (10 traces): air-temp (visible) and
    apparent-temp / heat index (hidden). A page-level toggle swaps which 5-trace
    group is visible and swaps the bottom stat annotation via relayout."""
    air = _heat_view(rows, "average_temp_c")
    app = _heat_view(rows, "apparent_temp_c")
    cats = ["Cool (<48F)", "Mild (48-62F)", "Warm (62-75F)", "Hot (>=75F)"]
    colors = [X_SLATE, "rgba(245,158,11,0.4)", X_AMBER, SLOWER]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    def add_view(view, visible):
        for cat, col, data in zip(cats, colors, view["paces_mi"]):
            # customdata carries M:SS pace strings since Plotly can't format min:sec natively.
            cd = [fmt_pace(v) for v in data]
            fig.add_trace(go.Violin(
                x=[cat]*len(data), y=data, name=cat, fillcolor=_x_rgba(col, 0.4),
                line_color=col, opacity=0.7, box_visible=True, meanline_visible=True,
                points=False, showlegend=False, customdata=cd, visible=visible,
                hovertemplate="%{x}<br>%{customdata} /mi<extra></extra>",
            ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=cats, y=view["hr_means"], mode="lines+markers", line=dict(color=X_TEAL),
            marker=dict(color=X_TEAL), showlegend=False, visible=visible,
            hovertemplate="%{x}<br>mean HR %{y:.1f}<extra></extra>",
        ), secondary_y=True)

    # Traces 0-4 = air-temp view (default visible); 5-9 = apparent-temp (hidden).
    add_view(air, True)
    add_view(app, False)

    tidy_dark(fig)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title_text="Temperature band")
    # min/mi pace ticks (M:SS) from the UNION of both views' pace arrays, so the
    # axis is identical in both toggle states. Axis REVERSED so faster reads up.
    union = np.concatenate(air["paces_mi"] + app["paces_mi"]).tolist()
    pv, pt = _pace_ticks(union)
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
    # Bottom stat annotation. Default shows the air-temp view; the page toggle
    # swaps the text via relayout. Sits fully BELOW the plot area (y=-0.16 clears
    # the "Temperature band" axis title while staying inside the b=96 margin).
    # Default (air-temp) annotation. Formatted to match the spec's exact air
    # string so the initial render equals the JS toggle's `air` text (no value
    # flicker on click): p to 3 sig figs, HR-flat p to 2 dp.
    air_cool = fmt_pace(float(air["paces_mi"][0].mean()))
    air_hot = fmt_pace(float(air["paces_mi"][3].mean()))
    air_text = (f"Cool {air_cool} vs Hot {air_hot} /mi | "
                f"t={air['t']:.2f} | p={air['p']:.3f} | "
                f"HR flat (t={air['hrt']:.2f}, p={air['hrp']:.2f}) | n={air['n_total']}")
    # Apparent-temp annotation, built the same way as air. Appends the
    # sample-size caveat with a self-updating percentage (apparent temp drops
    # rows lacking humidity/wind, so its n is smaller than air's).
    app_cool = fmt_pace(float(app["paces_mi"][0].mean()))
    app_hot = fmt_pace(float(app["paces_mi"][3].mean()))
    app_text = (f"Cool {app_cool} vs Hot {app_hot} /mi | "
                f"t={app['t']:.2f} | p={app['p']:.3f} | "
                f"HR flat (t={app['hrt']:.2f}, p={app['hrp']:.2f}) | n={app['n_total']}")
    if air["n_total"]:
        _pct = round((air["n_total"] - app["n_total"]) / air["n_total"] * 100)
        app_text += f" (~{_pct}% fewer than air temp)"
    fig.add_annotation(
        x=0.5, y=-0.16, xref="paper", yref="paper", xanchor="center", yanchor="top",
        text=air_text,
        showarrow=False, font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
        bgcolor=X_ANN_BG)
    return fig, dict(air=air, app=app, air_text=air_text, app_text=app_text)


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


