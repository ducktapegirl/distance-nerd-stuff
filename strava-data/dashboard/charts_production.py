"""Chart builders wired into the production dashboard: the Overview/Volume/
Trends/Map charts plus the running & MTB segment scatter plots."""

from collections import defaultdict
from datetime import datetime

import plotly.graph_objects as go

from .config import (
    BG_ELEVATED, BG_GLASS, BORDER, BORDER_SUBTLE, FASTER, GRID, KM_TO_MI,
    MAP_CENTER_LAT, MAP_CENTER_LON, M_TO_FT, NEUTRAL, PLOT_FONT_FAMILY,
    SLOWER, SPORT_COLORS, SPORT_DISPLAY, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_TERTIARY, TITLE_FONT_FAMILY, TRAIL_RUN_COLOR,
)
from .data import fmt_pace, fmt_seg_time, mf, sport_category, week_start
from .geometry_stats import _add_regression_line, _pace_ticks, _r2_annotations, _remove_outliers
from .theme import tidy_dark

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
                if rec:
                    ds, mi, cnt = rec
                    op = min(1.0, max(0.08, mi / max_mi)) if max_mi else 0.08
                    title = (f"{ds} · {mi:.1f} mi "
                             f"({cnt} {'activity' if cnt == 1 else 'activities'})")
                    cells.append(
                        f'<rect class="hm-cell" data-date="{ds}" x="{x}" y="{y}" '
                        f'width="{cell}" height="{cell}" rx="2" fill="var(--accent)" '
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
    """Avg HR vs temperature, with an Air temp ↔ Apparent temp toggle.

    Both views are built into one figure (air-temp traces visible, apparent-temp
    hidden); a page-level toggle swaps trace visibility and the R²/caveat
    annotation text. Trace counts can vary if a sport is empty, so the per-view
    visibility arrays are computed here and applied verbatim by the JS (no
    hard-coded indices). 3 annotations (fixed slots): Run R² (0), TrailRun R² (1),
    sample-size caveat (2)."""
    colors = {"Run": RUN_COLOR, "TrailRun": TRAIL_COLOR}
    labels = {"Run": "Running", "TrailRun": "Trail Running"}

    def collect(metric):
        by = {"Run": {"x": [], "y": [], "text": []},
              "TrailRun": {"x": [], "y": [], "text": []}}
        tlabel = "Apparent temp" if metric == "apparent_temp_c" else "Temp"
        for r in rows:
            st = r.get("sport_type", "")
            if st not in ("Run", "TrailRun"):
                continue
            km = mf(r["distance_km"]) or 0
            if km < 1.5:
                continue
            hr = mf(r["average_heartrate"])
            tc = mf(r[metric])
            if not hr or tc is None or hr <= 0:
                continue
            tf = tc * 9 / 5 + 32          # °C → °F
            ds = r["start_date_local"][:10]
            by[st]["x"].append(round(tf, 1))
            by[st]["y"].append(hr)
            by[st]["text"].append(
                f"{r['name']}<br>{ds}<br>{st}<br>"
                f"{tlabel}: {tf:.0f}°F<br>HR: {hr:.0f} bpm"
            )
        return by

    fig = go.Figure()

    def add_view(by, visible):
        """Add scatter + regression per sport. Returns (n_traces, {sport: r2},
        n_points, all_x, all_y)."""
        nt, r2s, npts, axx, ayy = 0, {"Run": None, "TrailRun": None}, 0, [], []
        for st in ("Run", "TrailRun"):
            d = by[st]
            if not d["x"]:
                continue
            xs, ys, ts = _remove_outliers(d["x"], d["y"], d["text"])
            if not xs:
                continue
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="markers", name=labels[st],
                marker=dict(color=colors[st], size=7, opacity=0.75, line=dict(width=0)),
                hovertext=ts, hoverinfo="text", visible=visible,
            ))
            nt += 1
            before = len(fig.data)
            r2 = _add_regression_line(fig, xs, ys, colors[st])
            if len(fig.data) > before:        # regression trace was actually added
                fig.data[-1].visible = visible
                nt += 1
            r2s[st] = r2
            npts += len(xs)
            axx += list(xs); ayy += list(ys)
        return nt, r2s, npts, axx, ayy

    air_by, app_by = collect("average_temp_c"), collect("apparent_temp_c")
    n_air, r2_air, npts_air, ax_air, ay_air = add_view(air_by, True)
    n_app, r2_app, npts_app, ax_app, ay_app = add_view(app_by, False)

    # Per-view visibility arrays over the full (air + apparent) trace list.
    air_vis = [True] * n_air + [False] * n_app
    app_vis = [False] * n_air + [True] * n_app

    def rng(vals, frac=0.05):
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * frac or 1
        return [lo - pad, hi + pad]

    all_x, all_y = ax_air + ax_app, ay_air + ay_app

    def r2txt(v):
        return f"R²={v:.2f}" if v is not None else ""

    caveat = ""
    if npts_air:
        pct = round((npts_air - npts_app) / npts_air * 100)
        caveat = f"apparent temp: ~{pct}% fewer runs than air temp"

    # Annotation order is fixed (Run R², TrailRun R², caveat) so the JS can swap
    # by index. Default text = air-temp view; caveat is blank for air.
    DARK_PILL = "rgba(13,17,23,0.65)"  # themed via --ann-pill-bg by applyChartTheme
    annotations = [
        dict(x=0.98, y=0.95, xref="paper", yref="paper", text=r2txt(r2_air["Run"]),
             showarrow=False, xanchor="right", yanchor="top", bgcolor="rgba(0,0,0,0)",
             font=dict(color=colors["Run"], size=10, family=PLOT_FONT_FAMILY)),
        dict(x=0.98, y=0.85, xref="paper", yref="paper", text=r2txt(r2_air["TrailRun"]),
             showarrow=False, xanchor="right", yanchor="top", bgcolor="rgba(0,0,0,0)",
             font=dict(color=colors["TrailRun"], size=10, family=PLOT_FONT_FAMILY)),
        dict(x=0.5, y=-0.20, xref="paper", yref="paper", text="",
             showarrow=False, xanchor="center", yanchor="top", bgcolor=DARK_PILL,
             font=dict(color=TEXT_SECONDARY, size=10, family=PLOT_FONT_FAMILY)),
    ]

    tidy_dark(fig)
    fig.update_layout(
        title=dict(text="Heart Rate vs Temperature · Running Activities",
                   font=dict(color=TEXT_PRIMARY, size=12, family=TITLE_FONT_FAMILY),
                   x=0, xanchor="left"),
        # Shared/union axis ranges so air ↔ apparent reads as a 1:1 comparison.
        xaxis=dict(title="Temperature (°F)", range=rng(all_x)),
        yaxis=dict(title="Avg Heart Rate (bpm)", range=rng(all_y)),
        annotations=annotations,
        margin=dict(t=50, b=80, l=60, r=20),
    )
    meta = dict(
        air_vis=air_vis, app_vis=app_vis, trace_idx=list(range(n_air + n_app)),
        air_anns=[r2txt(r2_air["Run"]), r2txt(r2_air["TrailRun"]), ""],
        app_anns=[r2txt(r2_app["Run"]), r2txt(r2_app["TrailRun"]), caveat],
    )
    return fig, meta


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

