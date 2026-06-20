"""Segment rollups (consistency, fastest, grade-vs-pace overlap), the overall
stats aggregation, and the HTML card builders that render them."""

import math
from collections import defaultdict

import numpy as np
import plotly.graph_objects as go

from .config import KM_TO_MI, MTB_EMOJI, M_TO_FT, PLOT_FONT_FAMILY, RUN_EMOJI
from .charts_exploratory import X_ANN_BG, X_SLATE, _x_rgba
from .charts_production import MTB_COLOR, RUN_COLOR
from .data import fmt_pace, fmt_seg_time, mf
from .geometry_stats import _haversine_m
from .theme import fig_html, tidy_dark

# ─── New Segments-section views ───────────────────────────────────────────────
# Three additions to the Segments tab, built from segment_efforts.csv:
#   (1) pace-consistency box plots (most/least consistent per sport)
#   (2) top-3 fastest segments by average pace (HTML stat cards)
#   (3) grade vs avg pace, run vs MTB, over geographically-overlapping segments,
#       with the grade at which running overtakes mountain biking.
# Conventions reused: Run+TrailRun = Running (teal), MountainBikeRide = MTB
# (amber); running effort shown as pace min/mi (faster = lower), MTB as mph;
# distance in mi, grade in %. Annotations use X_SLATE text + X_ANN_BG pill so
# applyChartTheme() retints them in light mode. ASCII-only on-chart text.



def _esc(s):
    """Minimal HTML-text escape for segment names injected into card markup."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def compute_seg_rollups(seg_efforts, act_by_id):
    """Per-segment rollup keyed by segment_id. Groups Run+TrailRun -> 'Running',
    MountainBikeRide -> 'MTB'; everything else ignored. `metric` holds the
    per-effort DISPLAY value (pace min/mi for Running, speed mph for MTB)."""
    roll = {}
    for e in seg_efforts:
        a  = act_by_id.get(str(e.get("activity_id", "")), {})
        st = a.get("sport_type", "")
        g  = ("Running" if st in ("Run", "TrailRun")
              else "MTB" if st == "MountainBikeRide" else None)
        if g is None:
            continue
        dist = mf(e.get("segment_distance_m")) or 0
        el   = mf(e.get("elapsed_time_s")) or 0
        if dist <= 0 or el <= 0:
            continue
        sid = e.get("segment_id", "")
        s = roll.get(sid)
        if s is None:
            s = roll[sid] = dict(
                group=g, name=e.get("segment_name", ""), dist_m=dist,
                grade=mf(e.get("segment_avg_grade")),
                lat=mf(e.get("segment_start_lat")), lng=mf(e.get("segment_start_lng")),
                times=[], metric=[])
        if s["group"] != g:          # Strava segments are sport-specific; guard anyway
            continue
        s["times"].append(el)
        if g == "MTB":
            s["metric"].append((dist / el) * 3.6 * KM_TO_MI)        # mph
        else:
            s["metric"].append((el / dist) * (1000 / 60) / KM_TO_MI)  # min/mi
    return roll


def _cv(vals):
    """Coefficient of variation (population std / mean) of a value list."""
    a = np.array(vals, dtype=float)
    m = a.mean()
    return float(a.std(ddof=0) / m) if m else float("inf")


def _mi_pace_ticks(vals, target=6):
    """Adaptive M:SS tick vals/text for a min/mi axis spanning min(vals)..max(vals).
    Picks a 'nice' step so tight and very wide distributions both read cleanly."""
    if not vals:
        return [], []
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        hi = lo + 0.5
    raw = (hi - lo) / max(1, target)
    step = 60.0
    for cand in (0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60):
        if cand >= raw:
            step = cand
            break
    start = math.floor(lo / step) * step
    out, v = [], start
    while v <= hi + step * 0.5:
        if v >= lo - step * 0.5:
            out.append(round(v, 4))
        v += step
    return out, [fmt_pace(x) for x in out]


# ── 1. Pace consistency ──────────────────────────────────────────────────────

def seg_consistency_picks(roll, group, min_eff=3):
    """(most, least) consistent segments for a group, each (cv, sid, seg), using
    the coefficient of variation of the per-effort display metric. Segments need
    >= min_eff efforts. Returns (None, None) if none qualify."""
    scored = sorted(
        ((_cv(s["metric"]), sid, s) for sid, s in roll.items()
         if s["group"] == group and len(s["metric"]) >= min_eff),
        key=lambda x: x[0])
    if not scored:
        return None, None
    return scored[0], scored[-1]


def chart_consistency_box(s, group):
    """Horizontal box (with all efforts shown) of one segment's pace/speed spread.
    Running: min/mi, x REVERSED so faster reads to the right. MTB: mph (faster is
    naturally to the right)."""
    vals  = s["metric"]
    color = RUN_COLOR if group == "Running" else MTB_COLOR
    if group == "Running":
        labels = [f"{fmt_pace(v)} /mi" for v in vals]
    else:
        labels = [f"{v:.1f} mph" for v in vals]

    fig = go.Figure()
    fig.add_trace(go.Box(
        x=vals, orientation="h", name="",
        boxpoints="all", jitter=0.6, pointpos=0, whiskerwidth=0.4,
        marker=dict(color=color, size=7, opacity=0.75, line=dict(width=0)),
        line=dict(color=color, width=1.5),
        fillcolor=_x_rgba(color, 0.18),
        text=labels, hoverinfo="text",
    ))
    tidy_dark(fig)
    fig.update_layout(showlegend=False, margin=dict(t=12, b=46, l=14, r=18))
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    if group == "Running":
        tv, tt = _mi_pace_ticks(vals)
        fig.update_xaxes(title_text="Pace (min/mi, faster ->)", autorange="reversed",
                         tickvals=tv, ticktext=tt)
    else:
        fig.update_xaxes(title_text="Speed (mph, faster ->)")
    return fig


def _cons_card_html(scored, group, label, div_id):
    """One consistency card: emoji + tag, segment name, the box plot, a stat line."""
    if scored is None:
        return ""
    cv, _sid, s = scored
    emoji = RUN_EMOJI if group == "Running" else MTB_EMOJI
    n  = len(s["metric"])
    lo, hi = min(s["metric"]), max(s["metric"])
    rng = (f"{fmt_pace(lo)}–{fmt_pace(hi)} /mi" if group == "Running"
           else f"{lo:.1f}–{hi:.1f} mph")
    fig = chart_consistency_box(s, group)
    return (
        '<div class="seg-cardlet">'
        f'<div class="seg-cardlet-head"><span class="seg-emoji">{emoji}</span>'
        f'<span class="seg-cardlet-tag">{label} consistent &middot; {group}</span></div>'
        f'<div class="seg-cardlet-name">{_esc(s["name"])}</div>'
        f'{fig_html(fig, 200, div_id)}'
        f'<div class="seg-cardlet-meta">{n} efforts &middot; {rng} &middot; CV {cv*100:.1f}%</div>'
        '</div>')


# ── 2. Fastest segments by average pace ──────────────────────────────────────

def seg_fastest_picks(roll, group, top=3):
    """Top-N segments by average display metric (lowest min/mi for Running,
    highest mph for MTB). Returns list of (avg, sid, seg)."""
    rows = [(float(np.mean(s["metric"])), sid, s)
            for sid, s in roll.items() if s["group"] == group]
    rows.sort(key=lambda x: -x[0] if group == "MTB" else x[0])
    return rows[:top]


def _grade_txt(g):
    if g is None:
        return "n/a"
    t = f"{g:+.1f}%"
    return "0.0%" if t in ("+0.0%", "-0.0%") else t


def fast_seg_card(rank, group, avg, s):
    """One 'fastest segment' stat card: name + avg pace, distance (mi), grade."""
    emoji = RUN_EMOJI if group == "Running" else MTB_EMOJI
    if group == "Running":
        pace = f"{fmt_pace(avg)}<span class='u'>/mi</span>"
    else:
        pace = f"{avg:.1f}<span class='u'>mph</span>"
    dist_mi = s["dist_m"] * KM_TO_MI / 1000
    n = len(s["metric"])
    return (
        '<div class="fast-card">'
        f'<div class="fast-rank">{emoji} #{rank}</div>'
        f'<div class="fast-name">{_esc(s["name"])}</div>'
        '<div class="fast-stats">'
        f'<div class="fast-stat"><div class="fast-val">{pace}</div>'
        '<div class="fast-lbl">avg pace</div></div>'
        f'<div class="fast-stat"><div class="fast-val">{dist_mi:.2f}<span class="u">mi</span></div>'
        '<div class="fast-lbl">distance</div></div>'
        f'<div class="fast-stat"><div class="fast-val">{_grade_txt(s["grade"])}</div>'
        '<div class="fast-lbl">grade</div></div>'
        '</div>'
        f'<div class="fast-foot">avg of {n} effort{"s" if n != 1 else ""}</div>'
        '</div>')


# ── 3. Grade vs pace: where running overtakes mountain biking ─────────────────

def seg_overlap_pairs(roll, max_start_m=60.0, ratio_lo=1 / 1.10, ratio_hi=1.10):
    """Geographically-overlapping run/MTB segment pairs: start points within
    `max_start_m` AND segment distances within [ratio_lo, ratio_hi] (so the two
    cover essentially the same ground -> 'subsegments are ok'). Returns list of
    (start_dist_m, run_seg, mtb_seg)."""
    runs = [s for s in roll.values()
            if s["group"] == "Running" and s["lat"] and s["lng"] and s["grade"] is not None]
    mtbs = [s for s in roll.values()
            if s["group"] == "MTB" and s["lat"] and s["lng"] and s["grade"] is not None]
    pairs = []
    for rs in runs:
        for ms in mtbs:
            d = _haversine_m(rs["lat"], rs["lng"], ms["lat"], ms["lng"])
            if d > max_start_m:
                continue
            if ratio_lo <= rs["dist_m"] / ms["dist_m"] <= ratio_hi:
                pairs.append((d, rs, ms))
    return pairs


def _seg_avg_pace_mi(s):
    """Average completion time normalized to pace (min/mi) so segments of
    different lengths compare fairly on a shared run-vs-MTB axis."""
    avg_t = float(np.mean(s["times"]))
    return (avg_t / s["dist_m"]) * (1000 / 60) / KM_TO_MI


def chart_seg_grade_vs_time(pairs):
    """Scatter: segment grade (x) vs average pace per mile (y, REVERSED), Running
    vs MTB as separate datasets drawn from the overlapping segments. Linear fit
    per sport; the crossover grade (where running's pace overtakes MTB's) is
    marked. Returns (fig_or_None, info, ok)."""
    run_u = {id(rs): rs for _d, rs, _ms in pairs}
    mtb_u = {id(ms): ms for _d, _rs, ms in pairs}
    run = list(run_u.values())
    mtb = list(mtb_u.values())
    info = dict(n_run=len(run), n_mtb=len(mtb), cross=None)
    if len(run) < 2 or len(mtb) < 2:
        return None, info, False

    def pts(segs):
        xs = [s["grade"] for s in segs]
        ys = [_seg_avg_pace_mi(s) for s in segs]
        return xs, ys

    rx, ry = pts(run)
    mx, my = pts(mtb)
    rb, ra = np.polyfit(rx, ry, 1)      # pace = ra + rb*grade
    mb, ma = np.polyfit(mx, my, 1)
    cross = (ma - ra) / (rb - mb) if abs(rb - mb) > 1e-9 else None
    info.update(cross=cross, run_slope=rb, mtb_slope=mb)

    fig = go.Figure()
    # Shade the "running faster" half-plane (grade > crossover) faint teal.
    gmin = min(min(rx), min(mx))
    gmax = max(max(rx), max(mx))
    pad  = max(1.0, (gmax - gmin) * 0.06)
    x0, x1 = gmin - pad, gmax + pad
    if cross is not None and x0 < cross < x1 and rb < mb:
        fig.add_vrect(x0=cross, x1=x1, fillcolor=_x_rgba(RUN_COLOR, 0.07),
                      line_width=0, layer="below")

    def cd(segs):
        out = []
        for s in segs:
            p = _seg_avg_pace_mi(s)
            mph = s["dist_m"] / 1000 * KM_TO_MI / (float(np.mean(s["times"])) / 3600)
            out.append([_esc(s["name"]), _grade_txt(s["grade"]), fmt_pace(p),
                        f"{mph:.1f}", fmt_seg_time(float(np.mean(s["times"])))])
        return out

    fig.add_trace(go.Scatter(
        x=rx, y=ry, mode="markers", name="Running",
        marker=dict(color=RUN_COLOR, size=9, opacity=0.8, symbol="circle",
                    line=dict(width=0)),
        customdata=cd(run),
        hovertemplate=("%{customdata[0]}<br>grade %{customdata[1]}<br>"
                       "%{customdata[2]} /mi<br>avg %{customdata[4]}<extra></extra>"),
    ))
    fig.add_trace(go.Scatter(
        x=mx, y=my, mode="markers", name="MTB",
        marker=dict(color=MTB_COLOR, size=9, opacity=0.8, symbol="diamond",
                    line=dict(width=0)),
        customdata=cd(mtb),
        hovertemplate=("%{customdata[0]}<br>grade %{customdata[1]}<br>"
                       "%{customdata[2]} /mi (%{customdata[3]} mph)<br>"
                       "avg %{customdata[4]}<extra></extra>"),
    ))
    # Fit lines across each sport's own grade span.
    for xs, b, a, col in ((rx, rb, ra, RUN_COLOR), (mx, mb, ma, MTB_COLOR)):
        xa, xb = min(xs), max(xs)
        fig.add_trace(go.Scatter(
            x=[xa, xb], y=[a + b * xa, a + b * xb], mode="lines",
            line=dict(color=col, width=1.5, dash="dash"),
            showlegend=False, hoverinfo="skip"))

    tidy_dark(fig)
    fig.update_layout(showlegend=True, margin=dict(t=20, b=44, l=64, r=20))
    fig.update_xaxes(title_text="Segment grade (%)", range=[x0, x1], zeroline=True)
    allp = ry + my
    tv, tt = _mi_pace_ticks(allp)
    fig.update_yaxes(title_text="Avg pace (min/mi, faster = up)", autorange="reversed",
                     tickvals=tv, ticktext=tt)
    if cross is not None and x0 < cross < x1:
        fig.add_vline(x=cross, line=dict(color=X_SLATE, dash="dot", width=1.5))
        fig.add_annotation(
            x=cross, y=1.0, yref="paper", yanchor="bottom", xanchor="center",
            text=f"running overtakes MTB at ~{cross:.1f}% grade", showarrow=False,
            font=dict(family=PLOT_FONT_FAMILY, size=10, color=X_SLATE),
            bgcolor=X_ANN_BG)
    return fig, info, True


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

