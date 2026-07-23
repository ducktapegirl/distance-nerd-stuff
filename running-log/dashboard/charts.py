"""The 14 Plotly chart builders for the running-log dashboard."""

from collections import defaultdict
from datetime import date, timedelta

import plotly.graph_objects as go

from dashboard.config import (
    ACCENT, ACCENT_DIM, ACCENT_GLOW, BG_BASE, BG_ELEVATED, BORDER, DOW_ORDER,
    DOW_SHORT, EASY_COLOR, EVENT_GROUP_COLOR_BY_PR_LABEL,
    EVENT_GROUPS, LONG_COLOR, MONTH_ABBR, PLOT_FONT_FAMILY, RACE_COLOR,
    SEASON_ORDER, TEXT_PRIMARY, TEXT_SECONDARY, TYPE_COLORS,
    TYPE_LABELS, WORKOUT_COLOR, WORKOUT_MIX_COLORS, YEAR_PALETTE,
)
from dashboard.data import fmt_pace, fmt_time, map_type, maybe_float
from dashboard.stats import PR_CARD_SPECS
from dashboard.theme import fig_html, tidy_dark


def _weekly_series(rows):
    # Bucket by the Monday of the week so every bar sits on a uniform 7-day grid
    # (otherwise consecutive bars anchored at "first run date" of the week can
    # overlap when weeks start on different weekdays).
    weekly = defaultdict(float)
    for r in rows:
        m = maybe_float(r["miles"])
        if not m or not r["date"]:
            continue
        try:
            d = date.fromisoformat(r["date"])
        except ValueError:
            continue
        monday = d - timedelta(days=d.weekday())
        weekly[monday.isoformat()] += m

    sorted_weeks = sorted(weekly.items())
    xs   = [d for d, _ in sorted_weeks]
    ys   = [round(m, 1) for _, m in sorted_weeks]
    text = [f"Week of {d}<br>{m:.1f} mi" for d, m in sorted_weeks]

    rolling = [sum(ys[max(0,i-3):i+1]) / len(ys[max(0,i-3):i+1]) for i in range(len(ys))]
    return xs, ys, text, rolling


def chart_weekly(rows):
    xs, ys, text, rolling = _weekly_series(rows)

    seven_days_ms = 7 * 24 * 60 * 60 * 1000
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=xs, y=ys,
        width=[seven_days_ms] * len(xs),
        marker=dict(color=ACCENT, opacity=0.85, line=dict(width=0)),
        hovertext=text, hoverinfo="text", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=[round(v, 2) for v in rolling],
        mode="lines",
        line=dict(color=TEXT_SECONDARY, width=1.5, dash="dot"),
        name="4-wk avg", hoverinfo="skip",
    ))
    fig.update_layout(
        xaxis=dict(tickformat="%b %Y", showgrid=False),
        yaxis=dict(title="Miles"),
        bargap=0,
    )
    return tidy_dark(fig)


def chart_cumulative(rows):
    pts = []
    cum = 0.0
    for r in sorted(rows, key=lambda x: x["date"] or ""):
        m = maybe_float(r["miles"])
        if not r["date"] or not m:
            continue
        cum += m
        pts.append((r["date"], cum))

    fig = go.Figure()
    if pts:
        fig.add_trace(go.Scatter(
            x=[p[0] for p in pts], y=[round(p[1], 1) for p in pts],
            mode="lines",
            line=dict(color=ACCENT, width=2),
            fill="tozeroy",
            fillcolor=ACCENT_GLOW,
            hovertemplate="%{x}<br>%{y:,.0f} mi<extra></extra>",
            showlegend=False,
        ))
    fig.update_layout(
        xaxis=dict(tickformat="%Y", showgrid=False),
        yaxis=dict(title="Cumulative miles"),
    )
    return tidy_dark(fig)


def chart_workout_donut(rows, races_by_cat):
    counts = defaultdict(int)
    for r in rows:
        if r["is_race"] == "1":
            continue
        if maybe_float(r["miles"]):
            counts[map_type(r["workout_type"], False)] += 1
    counts["race"] = sum(len(races_by_cat[c]) for c in races_by_cat)

    order  = ["easy", "long", "tempo", "workout", "race"]
    labels = [TYPE_LABELS[k] for k in order]
    values = [counts.get(k, 0) for k in order]
    colors = [TYPE_COLORS[k]  for k in order]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color=BG_BASE, width=2)),
        textinfo="percent", textfont=dict(family=PLOT_FONT_FAMILY, size=11, color=BG_BASE),
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
        sort=False,
    ))
    return tidy_dark(fig)


def _easy_pace_series(rows):
    pts = []
    for r in rows:
        wt   = (r["workout_type"] or "").lower().strip()
        if wt not in ("run", "long run", "fartlek", "grass loops"):
            continue
        pace = maybe_float(r["pace_min_per_mile"])
        if not pace or pace < 5.5 or pace > 12:
            continue
        if not r["date"]:
            continue
        pts.append((r["date"], pace))

    pts.sort()
    if not pts:
        return pts, [], [], []

    # 30-run rolling mean
    paces  = [p[1] for p in pts]
    smooth = [sum(paces[max(0,i-29):i+1]) / len(paces[max(0,i-29):i+1]) for i in range(len(paces))]

    # MM:SS y-axis ticks from 5:30 to 9:30 (skip the endpoints — no grid line
    # renders there because they sit on the axis bounds)
    tickvals = [5.5 + i * 0.5 for i in range(9)]  # 5.5, 6.0, ..., 9.5
    ticktext = [f"{int(v)}:{int(round((v - int(v)) * 60)):02d}" for v in tickvals]

    return pts, smooth, tickvals, ticktext


def chart_easy_pace(rows):
    pts, smooth, tickvals, ticktext = _easy_pace_series(rows)
    if not pts:
        return tidy_dark(go.Figure())

    fig = go.Figure()
    def _mmss(p):
        m = int(p); s = int(round((p - m) * 60))
        if s == 60: m, s = m + 1, 0
        return f"{m}:{s:02d}"

    fig.add_trace(go.Scatter(
        x=[p[0] for p in pts], y=[round(p[1], 2) for p in pts],
        mode="markers",
        marker=dict(color=EASY_COLOR, size=4, opacity=0.35, line=dict(width=0)),
        name="run",
        customdata=[_mmss(p[1]) for p in pts],
        hovertemplate="%{x}<br>%{customdata} /mi<extra></extra>",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[p[0] for p in pts], y=[round(v, 3) for v in smooth],
        mode="lines",
        line=dict(color=ACCENT, width=2),
        name="30-run avg", hoverinfo="skip",
    ))
    # Pad x-range so the data doesn't crowd the chart edges
    first = date.fromisoformat(pts[0][0]) - timedelta(days=30)
    last  = date.fromisoformat(pts[-1][0]) + timedelta(days=30)

    fig.update_layout(
        xaxis=dict(tickformat="%Y", showgrid=False,
                   range=[first.isoformat(), last.isoformat()]),
        yaxis=dict(title="min/mile",
                   range=[10, 5],
                   tickvals=tickvals, ticktext=ticktext),
    )
    return tidy_dark(fig)


PR_PROGRESSION_SPECS = [
    # (label,        buckets,            categories,                       color,         axis_group)
    ("800m",         ["800m"],           ("indoorTrack", "outdoorTrack"),  WORKOUT_COLOR, None),
    ("Mile",         ["Mile"],           ("indoorTrack", "outdoorTrack"),  EASY_COLOR,    None),
    ("3k Steeple",   ["3k steeple"],     ("outdoorTrack",),                LONG_COLOR,    None),
    # 5k Track and 5k XC share an axis_group so chart_pr_progression can be
    # given an identical y-range/step for both — see
    # compute_pr_progression_axis_overrides().
    ("5k Track",     ["5k"],             ("indoorTrack", "outdoorTrack"),  RACE_COLOR,    "5k"),
    ("5k XC",        ["5k"],             ("crossCountry",),                EASY_COLOR,    "5k"),
]

# Unified x-window for all 5 per-distance PR-progression charts (small
# multiples read as a set only if they share the same time axis).
_PR_X_RANGE = ["2003-07-01", "2007-07-31"]

# Candidate y-axis tick steps (seconds) for chart_pr_progression's
# rounded-range / ~5-tick policy.
_PR_AXIS_STEPS = (5, 10, 15, 20, 30, 60)


def _filtered_races(races_by_cat, buckets, cats):
    """Non-relay races with a valid time for the given bucket(s) across the
    given categories, sorted chronologically. Shared by chart_pr_progression,
    compute_pr_progression_axis_overrides, and chart_pr_timeline."""
    items = []
    for cat in cats:
        for race in races_by_cat[cat]:
            if race["bucket"] not in buckets or race["is_relay"] or race["time_seconds"] is None:
                continue
            items.append(race)
    items.sort(key=lambda r: r["date"])
    return items


def _cumulative_pr_items(items):
    """Items (already chronological) whose time beat every prior time —
    i.e. the running PR at the moment each race happened."""
    pr_items = []
    best = float("inf")
    for r in items:
        if r["time_seconds"] < best:
            best = r["time_seconds"]
            pr_items.append(r)
    return pr_items


def _pr_axis_range(all_y):
    """Pick a step from {5,10,15,20,30,60}s that rounds [min(all_y),max(all_y)]
    outward to step multiples and yields 4-6 ticks (inclusive of both
    boundaries). Returns (lo, hi, step)."""
    lo_raw, hi_raw = min(all_y), max(all_y)
    candidates = []
    for step in _PR_AXIS_STEPS:
        lo = (int(lo_raw) // step) * step
        hi = (int(hi_raw) // step + 1) * step
        n_ticks = (hi - lo) // step + 1
        candidates.append((step, lo, hi, n_ticks))
        if 4 <= n_ticks <= 6:
            return lo, hi, step
    # No fixed step landed in [4, 6] ticks (unusually small/large range) —
    # fall back to whichever candidate's tick count is closest to 5.
    step, lo, hi, _ = min(candidates, key=lambda c: abs(c[3] - 5))
    return lo, hi, step


def compute_pr_progression_axis_overrides(races_by_cat, specs=PR_PROGRESSION_SPECS):
    """For specs that share a non-None axis_group (today: "5k Track" +
    "5k XC"), compute one shared (lo, hi, step) from the union of their race
    times, so the paired small-multiples render identical y-ranges/ticks.
    Returns {label: (lo, hi, step)} — only for specs that belong to a group."""
    groups = defaultdict(list)
    for label, buckets, cats, color, axis_group in specs:
        if axis_group is None:
            continue
        items = _filtered_races(races_by_cat, buckets, cats)
        groups[axis_group].append((label, items))

    overrides = {}
    for axis_group, entries in groups.items():
        all_y = [r["time_seconds"] for _, items in entries for r in items]
        if not all_y:
            continue
        lo, hi, step = _pr_axis_range(all_y)
        for label, _ in entries:
            overrides[label] = (lo, hi, step)
    return overrides


def _regress_pr_line(pr_items):
    """Linear regression best-fit through cumulative-PR points. Returns
    (x0, x1, y0, y1) or None if there aren't enough points to fit."""
    if len(pr_items) < 2:
        return None
    epoch = date.fromisoformat(pr_items[0]["date"])
    ns = [(date.fromisoformat(r["date"]) - epoch).days for r in pr_items]
    ys = [r["time_seconds"] for r in pr_items]
    n_mean = sum(ns) / len(ns)
    y_mean = sum(ys) / len(ys)
    denom  = sum((n - n_mean) ** 2 for n in ns)
    if denom <= 0:
        return None
    slope = sum((n - n_mean) * (y - y_mean) for n, y in zip(ns, ys)) / denom
    intercept = y_mean - slope * n_mean
    fit_y = [round(intercept + slope * ns[0], 1),
             round(intercept + slope * ns[-1], 1)]
    return pr_items[0]["date"], pr_items[-1]["date"], fit_y[0], fit_y[1]


def chart_pr_progression(races_by_cat, label, buckets, cats, color, y_override=None):
    """All race times for the given distance(s) plotted as faded scatter, with
    cumulative-best (PR) points marked with stars and connected by a step line.

    y_override, if given, is an explicit (lo, hi, step) tuple — used to give
    paired small-multiples (5k Track / 5k XC) an identical y-range/step; see
    compute_pr_progression_axis_overrides(). Other callers omit it and get a
    range/step computed from their own data."""
    items = _filtered_races(races_by_cat, buckets, cats)
    pr_items = _cumulative_pr_items(items)

    fig = go.Figure()
    if items:
        fig.add_trace(go.Scatter(
            x=[r["date"] for r in items],
            y=[r["time_seconds"] for r in items],
            mode="markers",
            marker=dict(color=color, size=8, opacity=0.55, line=dict(width=0)),
            hovertext=[f"{r['date']}<br>{r['race']}<br>{r['time']}" for r in items],
            hoverinfo="text", showlegend=False,
        ))
    if pr_items:
        fig.add_trace(go.Scatter(
            x=[r["date"] for r in pr_items],
            y=[r["time_seconds"] for r in pr_items],
            mode="markers",
            marker=dict(color=color, size=14, symbol="star",
                        line=dict(color=BG_BASE, width=1)),
            hovertext=[f"<b>NEW PR</b><br>{r['date']}<br>{r['race']}<br>{r['time']}"
                       for r in pr_items],
            hoverinfo="text", showlegend=False,
        ))
        # Linear regression best-fit through the PR points
        fit = _regress_pr_line(pr_items)
        if fit:
            x0, x1, y0, y1 = fit
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1], mode="lines",
                line=dict(color=color, width=2, dash="dot"),
                hoverinfo="skip", showlegend=False,
            ))

    tidy_dark(fig)

    if items:
        if y_override:
            lo, hi, step = y_override
        else:
            lo, hi, step = _pr_axis_range([r["time_seconds"] for r in items])
        # Rounded-range / ~5-tick policy: keep ALL ticks including the
        # boundaries (they're clean M:SS values now, not adaptive-step noise).
        ticks = list(range(lo, hi + step, step))
        fig.update_yaxes(
            tickmode="array", tickvals=ticks,
            ticktext=[fmt_time(s) for s in ticks],
            title="Time", range=[hi, lo],
        )
    fig.update_layout(xaxis=dict(
        tickformat="%b %Y", showgrid=False,
        range=_PR_X_RANGE, dtick="M6",
    ))
    return fig


_PACE_MILES_LOOKUP = {
    "800m":       0.4971,
    "Mile":       1.0,
    "1500m":      0.9321,
    "3k":         1.86411,
    "3k steeple": 1.86411,
    "5k":         3.10686,
    "6k":         3.72823,
}


def _group_races_by_bucket(races_by_cat):
    """All races plotted as pace (min/mile) over time, grouped by distance
    bucket, with hover text and PR/relay flags attached."""
    by_bucket = defaultdict(lambda: {"x":[],"y":[],"text":[],"pr":[],"relay":[]})
    for cat, races in races_by_cat.items():
        for race in races:
            b = race["bucket"]
            if b not in _PACE_MILES_LOOKUP or race["time_seconds"] is None:
                continue
            pace = (race["time_seconds"] / 60) / _PACE_MILES_LOOKUP[b]
            if pace < 4 or pace > 12:
                continue
            d = by_bucket[b]
            d["x"].append(race["date"])
            d["y"].append(pace)
            d["pr"].append(bool(race.get("pr")))
            d["relay"].append(bool(race.get("is_relay")))
            tags = []
            if race.get("pr"):       tags.append("PR")
            if race.get("is_relay"): tags.append("relay split")
            tag = (" · " + " · ".join(tags)) if tags else ""
            d["text"].append(
                f"{race['date']}<br>{race['race']}<br>{race['distance']} — {race['time']}{tag}<br>{fmt_pace(pace)}/mi"
            )
    return by_bucket


def _spread_right_labels(seeds, min_gap):
    """De-collide right-edge direct labels: nudge overlapping 'y' data
    coordinates apart to at least min_gap (data units), preserving order, so
    labels for lines that end at similar values don't overprint each other.
    Adjusts upward from the lowest label into whatever vertical space is
    available. Mutates and returns the seed dicts."""
    ordered = sorted(seeds, key=lambda s: s["y"])
    prev = None
    for s in ordered:
        if prev is not None and s["y"] - prev < min_gap:
            s["y"] = prev + min_gap
        prev = s["y"]
    return ordered


def chart_pace_timeline(races_by_cat):
    """All race paces over time, grouped into 3 event-group colors (rather
    than 7 per-bucket colors) with direct labels instead of a legend. Marker
    shape still distinguishes relay splits (diamond) and all-time PRs (star)
    from ordinary races (circle); non-PR/relay markers are semi-transparent
    so the PR "spine" of each event group stands out."""
    fig = go.Figure()
    by_bucket = _group_races_by_bucket(races_by_cat)

    def _symbol(is_pr, is_relay):
        if is_relay: return "diamond"
        if is_pr:    return "star"
        return "circle"
    def _size(is_pr, is_relay):
        if is_pr:    return 14
        if is_relay: return 11
        return 9
    def _opacity(is_pr, is_relay):
        return 1.0 if (is_pr or is_relay) else 0.55

    label_seeds = []
    for group_name, buckets, color in EVENT_GROUPS:
        xs, ys, texts, symbols, sizes, opacities = [], [], [], [], [], []
        for bucket in buckets:
            d = by_bucket.get(bucket)
            if not d:
                continue
            for x, y, text, pr, relay in zip(d["x"], d["y"], d["text"], d["pr"], d["relay"]):
                xs.append(x)
                ys.append(round(y, 3))
                texts.append(text)
                symbols.append(_symbol(pr, relay))
                sizes.append(_size(pr, relay))
                opacities.append(_opacity(pr, relay))
        if not xs:
            continue

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers", name=group_name,
            marker=dict(color=color, size=sizes, symbol=symbols, opacity=opacities,
                        line=dict(color=BG_BASE, width=1)),
            hovertext=texts, hoverinfo="text", showlegend=False,
        ))

        # Seed a direct label for this group at its chronologically-last
        # point; all group labels are pinned to the right edge and de-collided
        # below (replaces the old 7-item legend).
        last_i = max(range(len(xs)), key=lambda i: xs[i])
        label_seeds.append({"text": group_name, "color": color,
                            "x": xs[last_i], "y": ys[last_i]})

    tidy_dark(fig)

    # Pace ticks at every 30s
    if any(by_bucket[b]["y"] for b in by_bucket):
        all_y = [v for b in by_bucket.values() for v in b["y"]]
        lo = max(4, int(min(all_y)))
        hi = min(12, int(max(all_y)) + 1)
        ticks = []
        v = lo
        while v <= hi + 0.01:
            ticks.append(round(v, 3))
            v += 0.5
        fig.update_yaxes(
            tickmode="array", tickvals=ticks,
            ticktext=[fmt_pace(t) for t in ticks],
            title="Pace (min/mile)",
        )
    # Pin all group labels to the right edge and de-collide them vertically so
    # the two mid-pace groups (3k/steeple and 5k/6k) don't overprint.
    annotations = []
    if label_seeds:
        x_right = max(s["x"] for s in label_seeds)
        for s in _spread_right_labels(label_seeds, min_gap=0.14):
            annotations.append(dict(
                x=x_right, y=s["y"], xref="x", yref="y",
                text=s["text"], showarrow=False,
                xanchor="left", yanchor="middle", xshift=8,
                font=dict(color=s["color"], size=11, family=PLOT_FONT_FAMILY),
            ))
    fig.update_layout(
        xaxis=dict(tickformat="%b %Y", showgrid=False, range=_PR_X_RANGE),
        annotations=annotations,
        margin=dict(r=110),
    )
    return fig


def chart_pr_timeline(races_by_cat):
    """One categorical row per PR-card distance (PR_CARD_SPECS order, 7
    rows); a star marks every race that set a new all-time cumulative PR.
    Reveals whether breakthroughs clustered in particular seasons or landed
    steadily throughout."""
    row_labels = [label for label, _, _, _ in PR_CARD_SPECS]

    fig = go.Figure()
    for label, buckets, cats, _color in PR_CARD_SPECS:
        items = _filtered_races(races_by_cat, buckets, cats)
        pr_items = _cumulative_pr_items(items)
        if not pr_items:
            continue
        color = EVENT_GROUP_COLOR_BY_PR_LABEL.get(label, TEXT_SECONDARY)
        fig.add_trace(go.Scatter(
            x=[r["date"] for r in pr_items],
            y=[label] * len(pr_items),
            mode="markers", name=label,
            marker=dict(color=color, size=13, symbol="star",
                        line=dict(color=BG_BASE, width=1)),
            hovertext=[f"{r['date']}<br>{r['time']}<br>{r['race']}" for r in pr_items],
            hoverinfo="text", showlegend=False,
        ))

    tidy_dark(fig)
    fig.update_layout(
        xaxis=dict(tickformat="%b %Y", showgrid=False,
                   range=_PR_X_RANGE, dtick="M6"),
        yaxis=dict(type="category", categoryorder="array",
                   categoryarray=list(reversed(row_labels)), showgrid=True),
    )
    return fig


def chart_dow(rows):
    miles_by_dow = defaultdict(list)
    for r in rows:
        m = maybe_float(r["miles"])
        if m and r["day_of_week"]:
            miles_by_dow[r["day_of_week"]].append(m)
    avgs = [round(sum(miles_by_dow[d]) / len(miles_by_dow[d]), 2) if miles_by_dow[d] else 0
            for d in DOW_ORDER]
    max_v = max(avgs) or 1
    opacities = [0.45 + (v / max_v) * 0.55 for v in avgs]

    fig = go.Figure(go.Bar(
        x=DOW_SHORT, y=avgs,
        marker=dict(color=ACCENT, opacity=1, line=dict(width=0)),
        marker_color=[ACCENT] * 7,
        marker_line_width=0,
        hovertemplate="%{x}: %{y:.1f} mi avg<extra></extra>",
    ))
    fig.update_traces(marker=dict(color=[f"rgba(88,166,255,{o:.2f})" for o in opacities]))
    fig.update_layout(yaxis=dict(title="Avg miles"))
    return tidy_dark(fig)


def chart_monthly_avg(rows):
    weekly_by_month = defaultdict(lambda: defaultdict(float))
    for r in rows:
        m = maybe_float(r["miles"])
        if m and r["month"] and r["year"] and r["week_of_year"]:
            weekly_by_month[int(r["month"])][(r["year"], r["week_of_year"])] += m

    avgs = []
    for mo in range(1, 13):
        weeks = list(weekly_by_month[mo].values())
        avgs.append(round(sum(weeks) / len(weeks), 2) if weeks else 0)

    max_v = max(avgs) or 1
    opacities = [0.45 + (v / max_v) * 0.55 for v in avgs]

    fig = go.Figure(go.Bar(
        x=MONTH_ABBR, y=avgs,
        marker=dict(color=[f"rgba(88,166,255,{o:.2f})" for o in opacities], line=dict(width=0)),
        hovertemplate="%{x}: %{y:.1f} mi/wk<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(title="Avg miles per week"))
    return tidy_dark(fig)


def chart_monthly_mileage_by_year(rows):
    monthly = defaultdict(float)
    for r in rows:
        m = maybe_float(r["miles"])
        if m and r["year"] and r["month"]:
            monthly[(r["year"], int(r["month"]))] += m

    years = sorted({r["year"] for r in rows if r["year"]})
    fig = go.Figure()
    for i, year in enumerate(years):
        y_vals = [round(monthly[(year, m)], 1) if monthly[(year, m)] > 0 else None
                  for m in range(1, 13)]
        fig.add_trace(go.Bar(
            x=MONTH_ABBR, y=y_vals, name=year,
            marker=dict(color=YEAR_PALETTE[i % len(YEAR_PALETTE)], line=dict(width=0)),
            hovertemplate=f"%{{x}} {year}: %{{y:.1f}} mi<extra></extra>",
        ))

    fig.update_layout(
        barmode="group",
        xaxis=dict(title="Month"),
        yaxis=dict(title="Miles"),
        bargap=0.15, bargroupgap=0.05,
    )
    return tidy_dark(fig)


_WORKOUT_MIX_KEEP = ["run","long run","intervals","tempo","fartlek","pre-meet",
                      "hills","aquajog","pool","bike","elliptical","grass loops"]


def _aggregate_workout_mix_by_season(rows):
    """Buckets miles by (season-year label) × workout type, then derives both
    absolute-miles and percent-of-total traces per type. Returns
    (x_labels, miles_traces, pct_traces), where each trace is (wtype, y_values)."""
    bucket_miles = defaultdict(lambda: defaultdict(float))
    bucket_order = []
    seen = set()
    for r in rows:
        miles = maybe_float(r["miles"])
        if not miles or not r["workout_type"] or not r["season"] or not r["year"]:
            continue
        raw = r["workout_type"]
        if raw == "hill repeats":
            raw = "hills"
        wtype = raw if raw in _WORKOUT_MIX_KEEP else "other"
        season = r["season"]
        year = r["year"]
        label = f"{season.capitalize()} '{year[2:]}"
        sk = (year, SEASON_ORDER.index(season) if season in SEASON_ORDER else 99)
        if label not in seen:
            bucket_order.append((sk, label))
            seen.add(label)
        bucket_miles[label][wtype] += miles

    bucket_order.sort()
    x_labels = [lbl for _, lbl in bucket_order]

    all_types = _WORKOUT_MIX_KEEP + ["other"]
    miles_traces = []
    pct_traces = []
    for wtype in all_types:
        y_abs = [bucket_miles[lbl].get(wtype, 0) for lbl in x_labels]
        if sum(y_abs) == 0:
            continue
        totals = [sum(bucket_miles[lbl].values()) for lbl in x_labels]
        y_pct = [round(100 * a / tot, 1) if tot > 0 else 0 for a, tot in zip(y_abs, totals)]
        miles_traces.append((wtype, [round(v, 1) for v in y_abs]))
        pct_traces.append((wtype, y_pct))

    return x_labels, miles_traces, pct_traces


def chart_workout_mix_by_season(rows):
    x_labels, miles_traces, pct_traces = _aggregate_workout_mix_by_season(rows)

    fig = go.Figure()
    for wtype, y_vals in miles_traces:
        fig.add_trace(go.Bar(
            name=wtype.capitalize(),
            x=x_labels, y=y_vals,
            marker=dict(color=WORKOUT_MIX_COLORS.get(wtype, "#475569"), line=dict(width=0)),
            hovertemplate=f"{wtype.capitalize()} — %{{x}}: %{{y}}<extra></extra>",
        ))

    miles_y_list = [tr[1] for tr in miles_traces]
    pct_y_list   = [tr[1] for tr in pct_traces]

    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Season", tickangle=-40),
        yaxis=dict(title="Miles"),
    )
    fig = tidy_dark(fig)
    # Override after tidy_dark — push legend below rotated season labels.
    fig.update_layout(
        margin=dict(t=20, b=130, l=50, r=20),
        legend=dict(
            orientation="h", yanchor="top", y=-0.38, x=0.5, xanchor="center",
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_SECONDARY, size=10, family=PLOT_FONT_FAMILY),
        ),
    )
    return fig, miles_y_list, pct_y_list


def chart_seasonal_sparklines(rows):
    """Returns dict of {season: (avg_mi_wk, sparkline_html_div)} — 4 mini Plotly
    charts. Each sparkline plots weekly mileage across all years (chronological),
    so trends over time within a season are visible at a glance."""
    by_season = defaultdict(lambda: defaultdict(float))
    for r in rows:
        m = maybe_float(r["miles"])
        if m and r["season"]:
            by_season[r["season"]][(r["year"], r["week_of_year"])] += m

    out = {}
    for season in ["fall", "winter", "spring", "summer"]:
        weeks = sorted(by_season[season].items(), key=lambda kv: (kv[0][0], int(kv[0][1])))
        ys     = [round(w[1], 1) for w in weeks]
        labels = [f"{kv[0][0]} · wk {int(kv[0][1])}" for kv in weeks]
        avg = round(sum(ys) / len(ys), 1) if ys else 0

        fig = go.Figure(go.Scatter(
            x=list(range(len(ys))), y=ys, mode="lines",
            line=dict(color=ACCENT, width=1.5),
            fill="tozeroy", fillcolor=ACCENT_DIM,
            text=labels,
            hovertemplate="%{text}<br>%{y:.1f} mi<extra></extra>",
        ))
        fig.update_layout(
            margin=dict(t=4, b=4, l=4, r=4),
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            hoverlabel=dict(bgcolor=BG_ELEVATED, bordercolor=BORDER,
                            font=dict(family=PLOT_FONT_FAMILY, color=TEXT_PRIMARY, size=11)),
        )
        out[season] = (avg, fig_html(fig, height=60, div_id=f"spark-{season}"))
    return out
