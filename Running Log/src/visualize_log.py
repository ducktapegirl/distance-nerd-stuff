#!/usr/bin/env python3
"""
visualize_log.py — Build the redesigned running log dashboard from running_log.csv.

Usage:  python src/visualize_log.py  (from the Running Log/ directory)
Input:  running_log.csv  (Running Log/, one level up)
Output: index.html      (Running Log/, one level up)

Design follows Claude Design/design_handoff_running_log/README.md:
dark glass UI, top-tab nav, 6 sections (Overview, Volume, Workout Mix,
Performance, Races, Patterns), Geist + Geist Mono typography. Charts use
Plotly (themed dark); layout, cards, race rows, search, and heatmap are
hand-rolled HTML/SVG.
"""

import csv
import html
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

import plotly.graph_objects as go


# ─── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "running_log.csv")
OUT_PATH = os.path.join(BASE_DIR, "index.html")


# ─── Design tokens (from design_handoff_running_log/README.md) ────────────────

ACCENT          = "#58a6ff"
ACCENT_DIM      = "rgba(88, 166, 255, 0.08)"
ACCENT_GLOW     = "rgba(88, 166, 255, 0.15)"

EASY_COLOR      = "#2dd4bf"   # teal — easy run
TEMPO_COLOR     = "#f59e0b"   # amber — tempo
LONG_COLOR      = "#a78bfa"   # violet — long run
RACE_COLOR      = "#f87171"   # coral — race
WORKOUT_COLOR   = "#60a5fa"   # blue — workout (intervals/fartlek/etc.)

BG_BASE         = "#0d1117"
BG_SURFACE      = "#161b22"
BG_ELEVATED     = "#1c2230"
BG_GLASS        = "rgba(22, 27, 34, 0.7)"
BORDER          = "rgba(48, 54, 61, 0.8)"
BORDER_SUBTLE   = "rgba(48, 54, 61, 0.4)"
TEXT_PRIMARY    = "#e6edf3"
TEXT_SECONDARY  = "#8b949e"
TEXT_TERTIARY   = "#8b949e"

PLOTLY_CDN = (
    '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" '
    'charset="utf-8"></script>'
)

# CSV workout_type → 5 design types
WORKOUT_TYPE_MAP = {
    "run":         "easy",
    "":            "easy",
    "long run":    "long",
    "grass loops": "long",
    "tempo":       "tempo",
    "intervals":   "workout",
    "fartlek":     "workout",
    "hills":       "workout",
    "pre-meet":    "workout",
    "strides":     "workout",
    "bike":        "workout",
    "elliptical":  "workout",
    "pool":        "workout",
    "swim":        "workout",
    "aquajog":     "workout",
    "aqua jog":    "workout",
    "drills":      "workout",
}

TYPE_COLORS = {
    "easy":    EASY_COLOR,
    "long":    LONG_COLOR,
    "tempo":   TEMPO_COLOR,
    "workout": WORKOUT_COLOR,
    "race":    RACE_COLOR,
}

TYPE_LABELS = {
    "easy":    "Easy",
    "long":    "Long",
    "tempo":   "Tempo",
    "workout": "Workout",
    "race":    "Race",
}

DOW_ORDER  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
DOW_SHORT  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
SEASON_ORDER = ["fall", "winter", "spring", "summer"]

# Cycled by index for per-year traces (Monthly Mileage by Year chart)
YEAR_PALETTE = [
    "#58a6ff", "#2dd4bf", "#a78bfa", "#f59e0b", "#f87171",
    "#34d399", "#60a5fa", "#fb7185", "#e879f9", "#fcd34d",
]

# Dark-theme palette for the fine-grained workout types stacked in
# "Miles by Workout Type per Season". Easy/long/tempo/workout/race relatives
# are kept in the same hue family as TYPE_COLORS so the chart reads as a
# refinement of the donut directly above it.
WORKOUT_MIX_COLORS = {
    "run":          "#2dd4bf",   # teal
    "long run":     "#a78bfa",   # violet
    "intervals":    "#3b82f6",   # blue
    "tempo":        "#f59e0b",   # amber
    "fartlek":      "#ec4899",   # pink
    "hills":        "#c084fc",   # lavender
    "pre-meet":     "#84cc16",   # lime
    "aquajog":      "#67e8f9",   # light cyan
    "pool":         "#0891b2",   # dark cyan
    "bike":         "#64748b",   # slate
    "elliptical":   "#d1d5db",   # pale gray
    "grass loops":  "#16a34a",   # forest green
    "swim":         "#7dd3fc",   # pale sky
    "other":        "#475569",   # dark slate
}


# ─── Data helpers ─────────────────────────────────────────────────────────────

def load_rows():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def maybe_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_time_seconds(s):
    """'19:32' → 1172.0, '11:21.5' → 681.5, '5:39' → 339.0. None on failure."""
    if not s:
        return None
    s = s.strip().rstrip("*").rstrip("?")
    s = s.replace(".x", "")
    parts = s.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return None
    return None


def fmt_pace(pace_min):
    total_s = round(pace_min * 60)
    return f"{total_s // 60}:{total_s % 60:02d}"


def fmt_time(secs):
    secs = round(secs, 2)
    whole = int(secs)
    frac  = secs - whole
    m, s  = whole // 60, whole % 60
    if frac >= 0.005:
        return f"{m}:{s:02d}.{int(round(frac*100)):02d}"
    return f"{m}:{s:02d}"


def map_type(workout_type, is_race):
    if is_race:
        return "race"
    key = (workout_type or "").lower().strip()
    return WORKOUT_TYPE_MAP.get(key, "easy")


# ─── Race classification (per user rules) ─────────────────────────────────────
# - Cross country: fall, before Thanksgiving, 5k or 6k (no steeple)
# - Indoor track:  December through late March, 800m through 5k
# - Outdoor track: from spring break onward, includes steeplechase
# - Mud Run (2004-06-06): omitted per user

def classify_race(date_str, distance):
    if not date_str or not distance:
        return None
    y, m, d = (int(p) for p in date_str.split("-"))

    # Omit the one summer Mud Run
    if date_str == "2004-06-06":
        return None

    # Cross country: Sep / Oct / Nov-before-25
    if (m in (9, 10)) or (m == 11 and d < 25):
        return "crossCountry"

    # Indoor track: Dec through ~late March
    if m == 12 or m <= 2:
        return "indoorTrack"
    if m == 3 and d < 28:           # 2006-03-29 / 2007-03-31 are spring-break FL outdoor meets
        return "indoorTrack"

    # Outdoor track: late March / April / May (any distance, includes steeple)
    if (m == 3 and d >= 28) or m in (4, 5):
        return "outdoorTrack"

    return None  # summer / unclassified


# ─── Distance buckets (for PR cards and race-card display) ────────────────────

def normalize_distance(raw):
    """Map raw `race_distance` text to a canonical bucket. Returns None if
    we don't want to track this distance for PRs."""
    if not raw:
        return None
    s = raw.strip().lower()
    if "steeple" in s and "1500" in s:
        return "1500m steeple"   # one-off time trial 2007-04-07
    if "steeple" in s:
        return "3k steeple"
    if "dmr" in s or "leg" in s:
        return None              # relay leg, not standalone
    if s in ("800", "800m"):
        return "800m"
    if s in ("1000",):
        return "1000m"
    if s in ("1500", "1500m"):
        return "1500m"
    if s in ("mile", "1600m"):
        return "Mile"
    if s in ("3k", "3000m"):
        return "3k"
    if s in ("5k", "5000m", "5k (short)"):
        return "5k"
    if s in ("6k", "6k (short 100m)"):
        return "6k"
    if s in ("4k",):
        return "4k"
    if s == "4822m":
        return "4822m"
    return s.upper()


# Display label for a race row's "season + distance" line
def season_label(date_str, category):
    y, m, _ = (int(p) for p in date_str.split("-"))
    if category == "crossCountry":
        return f"Fall {y}"
    if category == "indoorTrack":
        # December stays in the year that follows
        season_year = y + 1 if m == 12 else y
        return f"Indoor {season_year}"
    if category == "outdoorTrack":
        return f"Spring {y}"
    return ""


# ─── Stats ────────────────────────────────────────────────────────────────────

def compute_stats(rows):
    total_miles = 0.0
    active_days = set()
    weekly      = defaultdict(float)
    races_count = 0
    all_dates_with_miles = []

    for r in rows:
        if not r["date"]:
            continue
        m = maybe_float(r["miles"])
        if m and m > 0:
            total_miles += m
            active_days.add(r["date"])
            weekly[(r["year"], r["week_of_year"])] += m
            all_dates_with_miles.append(r["date"])
        if r["is_race"] == "1":
            # Count classified races only (skip the omitted Mud Run)
            cat = classify_race(r["date"], r["race_distance"])
            if cat:
                races_count += 1

    n_weeks = len(weekly) or 1
    avg_per_week = total_miles / n_weeks
    peak_week = max(weekly.values()) if weekly else 0

    # Longest streak of consecutive calendar days with miles > 0
    sorted_dates = sorted(set(all_dates_with_miles))
    longest = cur = 0
    prev = None
    for ds in sorted_dates:
        cd = date.fromisoformat(ds)
        cur = cur + 1 if (prev and (cd - prev).days == 1) else 1
        longest = max(longest, cur)
        prev = cd

    if sorted_dates:
        first = date.fromisoformat(sorted_dates[0])
        last  = date.fromisoformat(sorted_dates[-1])
        span  = (last - first).days + 1
        active_pct = round(100 * len(active_days) / span)
    else:
        active_pct = 0

    return {
        "totalMiles":         int(round(total_miles)),
        "avgMilesPerWeek":    int(round(avg_per_week)),
        "peakWeekMiles":      int(round(peak_week)),
        "totalRaces":         races_count,
        "longestStreak":      longest,
        "activeDayPercentage": active_pct,
    }


# ─── Race extraction (categorized + PR-flagged) ───────────────────────────────

def build_race_records(rows):
    """Returns dict of {crossCountry, indoorTrack, outdoorTrack} → list of races,
    each with: date, season, race, distance, distance_bucket, time, time_seconds,
    pr (bool — best of distance bucket within its category), surface_distance_key
    (for separating XC 5k from track 5k in PR computation)."""

    cats = {"crossCountry": [], "indoorTrack": [], "outdoorTrack": []}

    for r in rows:
        if r["is_race"] != "1":
            continue
        cat = classify_race(r["date"], r["race_distance"])
        if cat is None:
            continue

        bucket = normalize_distance(r["race_distance"])
        secs   = parse_time_seconds(r["race_time"])
        is_relay = (r["race_time"] or "").strip().endswith("*")

        cats[cat].append({
            "date":       r["date"],
            "season":     season_label(r["date"], cat),
            "race":       r["race_name"] or "Race",
            "distance":   r["race_distance"],
            "bucket":     bucket,
            "time":       (r["race_time"] or "").rstrip("*"),
            "time_seconds": secs,
            "is_relay":   is_relay,
            "category":   cat,
        })

    # Sort each category chronologically
    for cat_list in cats.values():
        cat_list.sort(key=lambda x: x["date"])

    # PR flagging — min time per (category, bucket), excluding relays + invalid
    # times. Only flag buckets that have a corresponding PR card; this keeps the
    # per-race PR badge consistent with the Performance tab.
    pr_eligible = {(cat, b) for _, buckets, cats_, _ in PR_CARD_SPECS
                   for cat in cats_ for b in buckets}
    for cat, items in cats.items():
        best_per_bucket = {}
        for item in items:
            if item["is_relay"] or item["bucket"] is None or item["time_seconds"] is None:
                continue
            if (cat, item["bucket"]) not in pr_eligible:
                continue
            b = item["bucket"]
            if b not in best_per_bucket or item["time_seconds"] < best_per_bucket[b]["time_seconds"]:
                best_per_bucket[b] = item
        for item in items:
            item["pr"] = item is best_per_bucket.get(item["bucket"])

    return cats


# ─── PR cards (Performance section) ───────────────────────────────────────────
# 7 cards: 800m, Mile, 1500m, 3k Steeple, 5k (track), 5k XC, 6k XC.

PR_CARD_SPECS = [
    # (label,     buckets,           categories,                              color)
    ("800m",      ["800m"],          ("indoorTrack", "outdoorTrack"),         WORKOUT_COLOR),
    ("Mile",      ["Mile"],          ("indoorTrack", "outdoorTrack"),         EASY_COLOR),
    ("1500m",     ["1500m"],         ("indoorTrack", "outdoorTrack"),         TEMPO_COLOR),
    ("3k Steeple",["3k steeple"],    ("outdoorTrack",),                       LONG_COLOR),
    ("5k Track",  ["5k"],            ("indoorTrack", "outdoorTrack"),         RACE_COLOR),
    ("5k XC",     ["5k"],            ("crossCountry",),                       EASY_COLOR),
    ("6k XC",     ["6k"],            ("crossCountry",),                       LONG_COLOR),
]


def compute_pr_cards(races_by_cat):
    cards = []
    for label, buckets, cats, color in PR_CARD_SPECS:
        best = None
        for cat in cats:
            for race in races_by_cat[cat]:
                if race["is_relay"] or race["bucket"] not in buckets or race["time_seconds"] is None:
                    continue
                if best is None or race["time_seconds"] < best["time_seconds"]:
                    best = race
        if best:
            cards.append({
                "label":  label,
                "time":   best["time"],
                "season": best["season"],
                "color":  color,
            })
        else:
            cards.append({"label": label, "time": "—", "season": "no data", "color": color})
    return cards


# ─── Plotly: dark theme helper ────────────────────────────────────────────────

PLOT_FONT_FAMILY = "'Geist Mono', 'Fira Code', monospace"

def tidy_dark(fig, *, title=None):
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
            bgcolor=BG_ELEVATED, bordercolor=BORDER, font=dict(family=PLOT_FONT_FAMILY, color=TEXT_PRIMARY, size=11),
        ),
    )
    if title:
        fig.update_layout(title=dict(
            text=title, font=dict(color=TEXT_PRIMARY, size=12, family="'Geist', sans-serif"),
            x=0, xanchor="left",
        ))
    fig.update_xaxes(
        gridcolor=BORDER_SUBTLE, zerolinecolor=BORDER_SUBTLE,
        linecolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT_TERTIARY, size=10),
        title_font=dict(color=TEXT_SECONDARY, size=11),
    )
    fig.update_yaxes(
        gridcolor=BORDER_SUBTLE, zerolinecolor=BORDER_SUBTLE,
        linecolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT_TERTIARY, size=10),
        title_font=dict(color=TEXT_SECONDARY, size=11),
    )
    return fig


def fig_html(fig, height=320, div_id=None):
    kwargs = dict(
        full_html=False,
        include_plotlyjs=False,
        default_height=f"{height}px",
        config={"displayModeBar": False, "responsive": True},
    )
    if div_id:
        kwargs["div_id"] = div_id
    return fig.to_html(**kwargs)


# ─── Plotly chart builders ────────────────────────────────────────────────────

def chart_weekly(rows):
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


def chart_easy_pace(rows):
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
        return tidy_dark(go.Figure())

    # 30-run rolling mean
    paces  = [p[1] for p in pts]
    smooth = [sum(paces[max(0,i-29):i+1]) / len(paces[max(0,i-29):i+1]) for i in range(len(paces))]

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

    # MM:SS y-axis ticks from 5:30 to 9:30 (skip the endpoints — no grid line
    # renders there because they sit on the axis bounds)
    tickvals = [5.5 + i * 0.5 for i in range(9)]  # 5.5, 6.0, ..., 9.5
    ticktext = [f"{int(v)}:{int(round((v - int(v)) * 60)):02d}" for v in tickvals]

    fig.update_layout(
        xaxis=dict(tickformat="%Y", showgrid=False,
                   range=[first.isoformat(), last.isoformat()]),
        yaxis=dict(title="min/mile",
                   range=[10, 5],
                   tickvals=tickvals, ticktext=ticktext),
    )
    return tidy_dark(fig)


PR_PROGRESSION_SPECS = [
    # (label,        buckets,            categories,                       color)
    ("800m",         ["800m"],           ("indoorTrack", "outdoorTrack"),  WORKOUT_COLOR),
    ("Mile",         ["Mile"],           ("indoorTrack", "outdoorTrack"),  EASY_COLOR),
    ("3k Steeple",   ["3k steeple"],     ("outdoorTrack",),                LONG_COLOR),
    ("5k Track",     ["5k"],             ("indoorTrack", "outdoorTrack"),  RACE_COLOR),
    ("5k XC",        ["5k"],             ("crossCountry",),                EASY_COLOR),
]


def chart_pr_progression(races_by_cat, label, buckets, cats, color):
    """All race times for the given distance(s) plotted as faded scatter, with
    cumulative-best (PR) points marked with stars and connected by a step line."""
    items = []
    for cat in cats:
        for race in races_by_cat[cat]:
            if race["bucket"] not in buckets or race["is_relay"] or race["time_seconds"] is None:
                continue
            items.append(race)
    items.sort(key=lambda r: r["date"])

    # Cumulative-best (PR over time)
    pr_items = []
    best = float("inf")
    for r in items:
        if r["time_seconds"] < best:
            best = r["time_seconds"]
            pr_items.append(r)

    fig = go.Figure()
    if items:
        fig.add_trace(go.Scatter(
            x=[r["date"] for r in items],
            y=[r["time_seconds"] for r in items],
            mode="markers",
            marker=dict(color=color, size=8, opacity=0.35, line=dict(width=0)),
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
        if len(pr_items) >= 2:
            epoch = date.fromisoformat(pr_items[0]["date"])
            ns = [(date.fromisoformat(r["date"]) - epoch).days for r in pr_items]
            ys = [r["time_seconds"] for r in pr_items]
            n_mean = sum(ns) / len(ns)
            y_mean = sum(ys) / len(ys)
            denom  = sum((n - n_mean) ** 2 for n in ns)
            if denom > 0:
                slope = sum((n - n_mean) * (y - y_mean) for n, y in zip(ns, ys)) / denom
                intercept = y_mean - slope * n_mean
                fit_y = [round(intercept + slope * ns[0], 1),
                         round(intercept + slope * ns[-1], 1)]
                fig.add_trace(go.Scatter(
                    x=[pr_items[0]["date"], pr_items[-1]["date"]],
                    y=fit_y, mode="lines",
                    line=dict(color=color, width=2, dash="dot"),
                    hoverinfo="skip", showlegend=False,
                ))

    if items:
        all_y = [r["time_seconds"] for r in items]
        span = max(all_y) - min(all_y)
        step = 5 if span <= 60 else (10 if span <= 120 else (30 if span <= 600 else 60))
        lo = (int(min(all_y)) // step) * step
        hi = (int(max(all_y)) // step + 1) * step
        ticks = list(range(lo, hi + step, step))
        # Drop boundary ticks so axis labels don't sit on the chart edge
        inner = ticks[1:-1] if len(ticks) > 2 else ticks
        fig.update_yaxes(
            tickmode="array", tickvals=inner,
            ticktext=[fmt_time(s) for s in inner],
            title="Time", autorange="reversed",
        )
    fig.update_layout(xaxis=dict(tickformat="%b %Y", showgrid=False))
    return tidy_dark(fig)


def chart_pace_timeline(races_by_cat):
    """All races plotted as pace (min/mile) over time, color-coded by distance bucket."""
    fig = go.Figure()
    bucket_colors = {
        "800m":       WORKOUT_COLOR,
        "Mile":       EASY_COLOR,
        "1500m":      TEMPO_COLOR,
        "3k":         "#a78bfa",
        "3k steeple": LONG_COLOR,
        "5k":         RACE_COLOR,
        "6k":         "#f59e0b",
    }
    miles_lookup = {
        "800m":       0.4971,
        "Mile":       1.0,
        "1500m":      0.9321,
        "3k":         1.86411,
        "3k steeple": 1.86411,
        "5k":         3.10686,
        "6k":         3.72823,
    }
    by_bucket = defaultdict(lambda: {"x":[],"y":[],"text":[],"pr":[],"relay":[],"season":[]})
    for cat, races in races_by_cat.items():
        for race in races:
            b = race["bucket"]
            if b not in miles_lookup or race["time_seconds"] is None:
                continue
            pace = (race["time_seconds"] / 60) / miles_lookup[b]
            if pace < 4 or pace > 12:
                continue
            d = by_bucket[b]
            d["x"].append(race["date"])
            d["y"].append(pace)
            d["pr"].append(bool(race.get("pr")))
            d["relay"].append(bool(race.get("is_relay")))
            d["season"].append(race.get("season") or "")
            tags = []
            if race.get("pr"):       tags.append("PR")
            if race.get("is_relay"): tags.append("relay split")
            tag = (" · " + " · ".join(tags)) if tags else ""
            d["text"].append(
                f"{race['date']}<br>{race['race']}<br>{race['distance']} — {race['time']}{tag}<br>{fmt_pace(pace)}/mi"
            )

    def _symbol(is_pr, is_relay):
        if is_relay: return "diamond"
        if is_pr:    return "star"
        return "circle"
    def _size(is_pr, is_relay):
        if is_pr:    return 14
        if is_relay: return 11
        return 9

    for bucket, color in bucket_colors.items():
        d = by_bucket.get(bucket)
        if not d or not d["x"]:
            continue
        symbols = [_symbol(pr, rl) for pr, rl in zip(d["pr"], d["relay"])]
        sizes   = [_size(pr, rl)   for pr, rl in zip(d["pr"], d["relay"])]
        fig.add_trace(go.Scatter(
            x=d["x"], y=[round(v,3) for v in d["y"]],
            mode="markers",
            name=bucket,
            marker=dict(color=color, size=sizes, symbol=symbols,
                        line=dict(color=BG_BASE, width=1)),
            hovertext=d["text"], hoverinfo="text",
        ))

        # Season-best trendline (one dotted line per bucket connecting the
        # fastest race in each season).
        season_best = {}
        for x, y, sn, rl in zip(d["x"], d["y"], d["season"], d["relay"]):
            if rl or not sn:
                continue
            cur = season_best.get(sn)
            if cur is None or y < cur[1]:
                season_best[sn] = (x, y)
        if len(season_best) >= 2:
            pts = sorted(season_best.values(), key=lambda p: p[0])
            fig.add_trace(go.Scatter(
                x=[p[0] for p in pts],
                y=[round(p[1], 3) for p in pts],
                mode="lines",
                name=f"{bucket} season best",
                line=dict(color=color, width=1.5, dash="dot"),
                hoverinfo="skip",
                showlegend=False,
            ))

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
    fig.update_layout(xaxis=dict(tickformat="%b %Y", showgrid=False))
    return tidy_dark(fig)


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


def chart_workout_mix_by_season(rows):
    KEEP = ["run","long run","intervals","tempo","fartlek","pre-meet",
            "hills","aquajog","pool","bike","elliptical","grass loops"]

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
        wtype = raw if raw in KEEP else "other"
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

    all_types = KEEP + ["other"]
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


# ─── Hand-rolled HTML components ──────────────────────────────────────────────

def stat_card_html(label, value):
    return f"""
    <div class="stat-card">
      <div class="stat-num">{value}</div>
      <div class="stat-label">{label}</div>
    </div>"""


def pr_card_html(card):
    return f"""
    <div class="pr-card" style="--pr-color: {card['color']}">
      <div class="pr-label">{card['label']}</div>
      <div class="pr-time">{html.escape(card['time'])}</div>
      <div class="pr-season">{html.escape(card['season'])}</div>
    </div>"""


def race_card_html(race):
    type_color = LONG_COLOR if race["category"] == "crossCountry" else (
        WORKOUT_COLOR if race["category"] == "indoorTrack" else TEMPO_COLOR
    )
    type_label = {"crossCountry":"XC", "indoorTrack":"Indoor", "outdoorTrack":"Outdoor"}[race["category"]]
    pr_badge = '<span class="pr-badge">PR</span>' if race.get("pr") else ""
    relay = '<span class="relay-tag">relay</span>' if race["is_relay"] else ""
    return f"""
    <div class="race-card" data-date="{race['date']}" tabindex="0" role="button">
      <span class="race-type-badge" style="--badge-color: {type_color}">{type_label}</span>
      <div class="race-meta">
        <div class="race-name">{html.escape(race['race'])}</div>
        <div class="race-sub">{html.escape(race['season'])} · {html.escape(race['distance'])}</div>
      </div>
      <div class="race-time">{html.escape(race['time'])}{relay}</div>
      {pr_badge}
    </div>"""


def heatmap_html(rows):
    """Hand-rolled SVG calendar heatmap, year-rows × (weeks × 7 days), with two
    color modes (Workout Type / Miles Intensity). Mode toggle is a JS click."""

    # Bucket miles + type per date
    by_date = {}
    for r in rows:
        if not r["date"]:
            continue
        miles = maybe_float(r["miles"]) or 0
        if miles <= 0 and r["is_race"] != "1":
            continue
        t = map_type(r["workout_type"], r["is_race"] == "1")
        prev = by_date.get(r["date"])
        if prev is None or miles > prev["miles"]:
            by_date[r["date"]] = {"miles": miles, "type": t}

    if not by_date:
        return "<div class='heatmap-empty'>No data</div>"

    years = sorted({int(d.split("-")[0]) for d in by_date})

    cell    = 11
    gap     = 2
    label_w = 28
    week_w  = cell + gap

    # Map a date to its column-day index, where 0 = Sunday … 6 = Saturday.
    def sun_dow(d):
        return (d.weekday() + 1) % 7

    rows_html = []
    for year in years:
        # All Sundays from the year's first week to year's last
        start = date(year, 1, 1)
        # Roll back to the Sunday on/before Jan 1
        start -= timedelta(days=sun_dow(start))
        end   = date(year, 12, 31)
        end   += timedelta(days=(6 - sun_dow(end)))   # roll forward to Saturday

        n_weeks = ((end - start).days + 1) // 7
        svg_w = label_w + n_weeks * week_w + 8
        svg_h = 7 * (cell + gap) + 22  # +22 for month labels

        cells = []
        month_labels = []
        last_month_label_x = -100
        for w in range(n_weeks):
            for dow in range(7):
                cur = start + timedelta(weeks=w, days=dow)
                if cur.year != year:
                    continue
                ds = cur.isoformat()
                rec = by_date.get(ds)
                x = label_w + w * week_w
                y = 14 + dow * (cell + gap)
                if rec:
                    miles = rec["miles"]
                    type_color = TYPE_COLORS[rec["type"]]
                    type_op    = min(1.0, 0.30 + (miles / 14) * 0.70)
                    # Discrete intensity bins (GitHub-style) for stronger contrast
                    if   miles >= 12: intens_op = 1.00
                    elif miles >=  8: intens_op = 0.78
                    elif miles >=  4: intens_op = 0.55
                    else:             intens_op = 0.32
                    title = f"{ds}: {miles:.1f} mi · {TYPE_LABELS[rec['type']]}"
                    cells.append(
                        f'<rect class="hm-cell" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                        f'data-date="{ds}" '
                        f'data-type-color="{type_color}" data-type-op="{type_op:.2f}" '
                        f'data-int-op="{intens_op:.2f}" '
                        f'fill="{ACCENT}" fill-opacity="{intens_op:.2f}">'
                        f'<title>{title}</title></rect>'
                    )
                else:
                    cells.append(
                        f'<rect class="hm-cell hm-rest" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                        f'fill="{TEXT_TERTIARY}" fill-opacity="0.10"></rect>'
                    )
            # Month label: print when crossing into a new month
            mid_date = start + timedelta(weeks=w, days=3)
            if mid_date.year == year and mid_date.day <= 7:
                if x - last_month_label_x > 30:
                    month_labels.append(
                        f'<text x="{x}" y="10" class="hm-month">{MONTH_ABBR[mid_date.month-1]}</text>'
                    )
                    last_month_label_x = x

        dow_labels = []
        for i, lbl in enumerate(("S","M","T","W","T","F","S")):
            dow_labels.append(
                f'<text x="0" y="{14 + i*(cell+gap) + 9}" class="hm-dow">{lbl}</text>'
            )

        rows_html.append(f"""
          <div class="hm-year-row">
            <div class="hm-year">{year}</div>
            <svg viewBox="0 0 {svg_w} {svg_h}" width="100%" preserveAspectRatio="xMinYMid meet">
              {"".join(month_labels)}
              {"".join(dow_labels)}
              {"".join(cells)}
            </svg>
          </div>""")

    legend_type = " ".join(
        f'<span class="hm-legend-item"><span class="swatch" style="background:{TYPE_COLORS[k]}"></span>{TYPE_LABELS[k]}</span>'
        for k in ("easy","long","tempo","workout","race")
    )
    legend_intensity = (
        '<span class="hm-legend-meta">0 mi</span>'
        '<span class="hm-legend-grad" title="Miles per day"></span>'
        '<span class="hm-legend-meta">12+ mi</span>'
    )

    return f"""
    <div class="card heatmap-card">
      <div class="card-header">
        <div class="card-title">Training Calendar</div>
        <div class="hm-mode-toggle">
          <button class="hm-toggle" data-mode="type">Workout Type</button>
          <button class="hm-toggle active" data-mode="intensity">Miles Intensity</button>
        </div>
      </div>
      <div class="hm-legend hm-legend-type" data-mode="type" hidden>{legend_type}</div>
      <div class="hm-legend hm-legend-intensity" data-mode="intensity">{legend_intensity}</div>
      <div class="hm-grid">{"".join(rows_html)}</div>
    </div>"""


def build_day_index(rows):
    """Per-date map of all log entries, used by the click-to-detail panel."""
    idx = defaultdict(list)
    for r in rows:
        if not r["date"]:
            continue
        is_race = r["is_race"] == "1"
        idx[r["date"]].append({
            "type":      map_type(r["workout_type"], is_race),
            "type_raw":  r["workout_type"] or "",
            "miles":     maybe_float(r["miles"]),
            "minutes":   maybe_float(r["minutes"]),
            "pace":      r["pace_min_per_mile"] or "",
            "comments":  r["comments"] or "",
            "extras":    r["extras"] or "",
            "is_race":   is_race,
            "race":      r["race_name"] or "",
            "race_dist": r["race_distance"] or "",
            "race_time": r["race_time"] or "",
        })
    return dict(idx)


def notes_search_html(rows):
    """Renders the search input + filter pills + scrollable note list. JS does
    the live filtering on the client."""

    notes = []
    for r in rows:
        c = (r["comments"] or "").strip()
        if not c:
            continue
        t = map_type(r["workout_type"], r["is_race"] == "1")
        notes.append({
            "date":  r["date"],
            "miles": maybe_float(r["miles"]) or 0,
            "type":  t,
            "note":  c,
            "race":  r["is_race"] == "1",
            "race_name": r["race_name"] or "",
        })
    notes.sort(key=lambda n: n["date"], reverse=True)

    rows_json = json.dumps(notes)

    pills = "".join(
        f'<button class="filter-pill" data-type="{k}" style="--pill-color: {TYPE_COLORS[k]}">{TYPE_LABELS[k]}</button>'
        for k in ("easy","long","tempo","workout","race")
    )

    return f"""
    <div class="card notes-card">
      <div class="card-header">
        <div class="card-title">Training Notes</div>
        <div class="notes-count" id="notes-count"></div>
      </div>
      <div class="notes-search">
        <input type="text" id="notes-query" placeholder="Search notes…" autocomplete="off"/>
        <button id="notes-clear" hidden>×</button>
      </div>
      <div class="filter-pills">
        <button class="filter-pill active" data-type="all">All</button>
        {pills}
      </div>
      <div class="notes-list" id="notes-list"></div>
      <script id="notes-data" type="application/json">{rows_json}</script>
    </div>"""


# ─── Section assemblers ───────────────────────────────────────────────────────

def section_overview(rows, stats):
    cards = [
        stat_card_html("Total Miles", f"{stats['totalMiles']:,}"),
        stat_card_html("Avg Mi/Week", stats["avgMilesPerWeek"]),
        stat_card_html("Peak Week", stats["peakWeekMiles"]),
        stat_card_html("Races", stats["totalRaces"]),
        stat_card_html("Longest Streak", f"{stats['longestStreak']}d"),
        stat_card_html("Active Days", f"{stats['activeDayPercentage']}%"),
    ]
    return f"""
    <section id="view-overview" class="view active">
      <div class="page-header">
        <div class="eyebrow">DASHBOARD</div>
        <h1>Overview</h1>
      </div>
      <div class="stat-grid">{"".join(cards)}</div>
      {notes_search_html(rows)}
      {heatmap_html(rows)}
      <div class="card">
        <div class="card-title">Cumulative Mileage</div>
        {fig_html(chart_cumulative(rows), height=280, div_id="chart-cumulative")}
      </div>
    </section>"""


def section_volume(rows):
    sparks = chart_seasonal_sparklines(rows)
    spark_cards = ""
    for season in ["fall", "winter", "spring", "summer"]:
        avg, html_div = sparks[season]
        spark_cards += f"""
        <div class="spark-card">
          <div class="spark-label">{season.capitalize()}</div>
          <div class="spark-stat">
            <span class="spark-num">{avg}</span>
            <span class="spark-sub">avg mi/wk</span>
          </div>
          <div class="spark-chart">{html_div}</div>
        </div>"""
    return f"""
    <section id="view-volume" class="view">
      <div class="page-header">
        <div class="eyebrow">TRAINING</div>
        <h1>Volume</h1>
      </div>
      <div class="card">
        <div class="card-title">Weekly Mileage</div>
        {fig_html(chart_weekly(rows), height=320, div_id="chart-weekly")}
      </div>
      <div class="card">
        <div class="card-title">Average Weekly Mileage by Season</div>
        <div class="spark-grid">{spark_cards}</div>
      </div>
      <div class="card">
        <div class="card-title">Monthly Mileage by Year</div>
        {fig_html(chart_monthly_mileage_by_year(rows), height=340, div_id="chart-monthly-by-year")}
      </div>
    </section>"""


def section_workout_mix(rows, races_by_cat):
    counts = defaultdict(int)
    for r in rows:
        if r["is_race"] == "1":
            continue
        if maybe_float(r["miles"]):
            counts[map_type(r["workout_type"], False)] += 1
    # Use the same race tally as the Races tab so the two views agree
    counts["race"] = sum(len(races_by_cat[c]) for c in races_by_cat)

    type_cards = "".join(f"""
        <div class="type-stat-card" style="--ts-color: {TYPE_COLORS[k]}">
          <div class="type-swatch"></div>
          <div class="type-num">{counts.get(k, 0)}</div>
          <div class="type-label">{TYPE_LABELS[k]}{'s' if k == 'race' else ' runs'}</div>
        </div>""" for k in ("easy", "long", "tempo", "workout", "race"))

    return f"""
    <section id="view-mix" class="view">
      <div class="page-header">
        <div class="eyebrow">TRAINING</div>
        <h1>Workout Mix</h1>
      </div>
      <div class="card">
        <div class="card-title">Distribution by Type</div>
        {fig_html(chart_workout_donut(rows, races_by_cat), height=300, div_id="chart-donut")}
      </div>
      <div class="type-stat-grid">{type_cards}</div>
      {(lambda res: f'''<div class="card">
        <div class="card-title-row">
          <div class="card-title">Miles by Workout Type per Season</div>
          <div class="chart-toggle" data-toggle-target="chart-mix-by-season"
               data-miles='{json.dumps(res[1])}'
               data-pct='{json.dumps(res[2])}'>
            <button class="active" data-mode="miles">Miles</button>
            <button data-mode="pct">% of Total</button>
          </div>
        </div>
        {fig_html(res[0], height=440, div_id="chart-mix-by-season")}
      </div>''')(chart_workout_mix_by_season(rows))}
      <div class="card">
        <div class="card-title">Easy Run Pace Over Time</div>
        {fig_html(chart_easy_pace(rows), height=300, div_id="chart-easy-pace")}
      </div>
    </section>"""


def section_performance(rows, races_by_cat):
    pr_cards = compute_pr_cards(races_by_cat)
    pr_html  = "".join(pr_card_html(c) for c in pr_cards)

    prog_cards = ""
    for i, (label, buckets, cats, color) in enumerate(PR_PROGRESSION_SPECS):
        slug = label.lower().replace(" ", "-")
        prog_cards += f"""
        <div class="card">
          <div class="card-title">{label} — PR Progression</div>
          {fig_html(chart_pr_progression(races_by_cat, label, buckets, cats, color),
                    height=260, div_id=f"chart-pr-{slug}")}
        </div>"""

    return f"""
    <section id="view-performance" class="view">
      <div class="page-header">
        <div class="eyebrow">RACING</div>
        <h1>Performance</h1>
      </div>
      <div class="pr-grid">{pr_html}</div>
      <div class="card">
        <div class="card-title">Race Pace Over Time</div>
        <div class="chart-caption">★ all-time PR &nbsp;·&nbsp; ◆ relay split &nbsp;·&nbsp; dotted line = season-best trend</div>
        {fig_html(chart_pace_timeline(races_by_cat), height=360, div_id="chart-pace-timeline")}
      </div>
      {prog_cards}
    </section>"""


def section_races(races_by_cat):
    cat_labels  = {"crossCountry": "XC", "indoorTrack": "Indoor", "outdoorTrack": "Outdoor"}
    cat_colors  = {"crossCountry": LONG_COLOR, "indoorTrack": WORKOUT_COLOR, "outdoorTrack": TEMPO_COLOR}

    # Flatten all races into a single JSON blob (rendered client-side)
    all_races = []
    for cat, races in races_by_cat.items():
        for r in races:
            all_races.append({
                "date":      r["date"],
                "race":      r["race"],
                "distance":  r["distance"],
                "bucket":    r["bucket"] or "",
                "time":      r["time"],
                "time_seconds": r["time_seconds"],
                "season":    r["season"],
                "is_relay":  bool(r.get("is_relay")),
                "pr":        bool(r.get("pr")),
                "category":  cat,
                "type_label": cat_labels[cat],
                "type_color": cat_colors[cat],
            })
    races_json = json.dumps(all_races).replace("</", "<\\/")

    # Distinct buckets (ordered) for the distance filter
    bucket_order = ["800m", "Mile", "1500m", "3k", "3k steeple", "5k", "6k"]
    seen_buckets = {r["bucket"] for r in all_races if r["bucket"]}
    bucket_opts  = "".join(
        f'<option value="{b}">{b}</option>' for b in bucket_order if b in seen_buckets
    )

    xc_n = len(races_by_cat["crossCountry"])
    in_n = len(races_by_cat["indoorTrack"])
    ou_n = len(races_by_cat["outdoorTrack"])
    total_n = xc_n + in_n + ou_n

    return f"""
    <section id="view-races" class="view">
      <div class="page-header">
        <div class="eyebrow">RACING</div>
        <h1>Races</h1>
      </div>
      <div class="race-tabs" role="tablist">
        <button class="race-tab active" data-tab="all">All <span class="tab-count">{total_n}</span></button>
        <button class="race-tab"        data-tab="crossCountry">Cross Country <span class="tab-count">{xc_n}</span></button>
        <button class="race-tab"        data-tab="indoorTrack">Indoor Track <span class="tab-count">{in_n}</span></button>
        <button class="race-tab"        data-tab="outdoorTrack">Outdoor Track <span class="tab-count">{ou_n}</span></button>
      </div>
      <div class="race-controls">
        <div class="race-search">
          <input type="text" id="race-query" placeholder="Search by race or distance…" autocomplete="off"/>
          <button id="race-clear" hidden>×</button>
        </div>
        <label class="race-control-group">
          <span class="race-control-label">Sort</span>
          <select id="race-sort">
            <option value="date-desc">Date (newest)</option>
            <option value="date-asc">Date (oldest)</option>
            <option value="time-asc">Time (fastest)</option>
            <option value="distance">Distance</option>
            <option value="pr">PRs first</option>
          </select>
        </label>
        <label class="race-control-group">
          <span class="race-control-label">Distance</span>
          <select id="race-distance">
            <option value="">All</option>{bucket_opts}
          </select>
        </label>
        <label class="race-control-group race-pr-toggle">
          <input type="checkbox" id="race-pr-only"/>
          <span>PRs only</span>
        </label>
      </div>
      <div class="race-list" id="race-list"></div>
      <div class="race-summary" id="race-summary"></div>
      <script id="races-data" type="application/json">{races_json}</script>
    </section>"""


def section_patterns(rows, stats):
    return f"""
    <section id="view-patterns" class="view">
      <div class="page-header">
        <div class="eyebrow">TRAINING</div>
        <h1>Patterns</h1>
      </div>
      <div class="patterns-grid">
        <div class="card">
          <div class="card-title">Avg Miles by Day of Week</div>
          {fig_html(chart_dow(rows), height=260, div_id="chart-dow")}
        </div>
        <div class="card">
          <div class="card-title">Avg Weekly Miles by Month</div>
          {fig_html(chart_monthly_avg(rows), height=260, div_id="chart-month")}
        </div>
      </div>
      <div class="card streak-card">
        <div class="card-title">Streak Analysis</div>
        <div class="streak-grid">
          <div class="streak-item">
            <div class="streak-num">{stats['longestStreak']}</div>
            <div class="streak-label">Longest streak (days)</div>
          </div>
          <div class="streak-item">
            <div class="streak-num">{stats['activeDayPercentage']}%</div>
            <div class="streak-label">Active days</div>
          </div>
          <div class="streak-item">
            <div class="streak-num">{stats['totalMiles']:,}</div>
            <div class="streak-label">Total miles</div>
          </div>
        </div>
      </div>
    </section>"""


# ─── CSS + JS blocks ──────────────────────────────────────────────────────────

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
  --grid: rgba(48, 54, 61, 0.4);
  --bg-gradient-1: rgba(88, 166, 255, 0.06);
  --bg-gradient-2: rgba(167, 139, 250, 0.04);
  --accent: {ACCENT};
  --accent-glow: {ACCENT_GLOW};
  --accent-dim: {ACCENT_DIM};
  --easy: {EASY_COLOR};
  --tempo: {TEMPO_COLOR};
  --long: {LONG_COLOR};
  --race: {RACE_COLOR};
  --workout: {WORKOUT_COLOR};
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
  --bg-gradient-1: rgba(9, 105, 218, 0.09);
  --bg-gradient-2: rgba(130, 80, 223, 0.07);
  --accent: #0550ae;
  --accent-glow: rgba(5, 80, 174, 0.18);
  --accent-dim: rgba(5, 80, 174, 0.10);
  --easy: #0d9488;
  --tempo: #c2710c;
  --long: #6d28d9;
  --race: #c81e1e;
  --workout: #1d4ed8;
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

.dash-footer {{
  text-align: center;
  padding: 28px 24px 36px;
  margin-top: 24px;
  font-size: 13px;
  color: var(--text-secondary);
  border-top: 1px solid var(--border);
}}
.dash-footer a {{
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.15s ease;
}}
.dash-footer a:hover {{ border-bottom-color: var(--accent); }}

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
}}
.topnav-row.row1 {{ height: 48px; }}
.topnav-row.row2 {{ padding-top: 10px; padding-bottom: 11px; }}

.wordmark {{ display: flex; align-items: center; gap: 10px; }}
.wordmark-name {{
  font-size: 34px; font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}}
.wordmark-meta {{ font-family: 'Geist Mono', monospace; font-size: 16px; color: var(--text-tertiary); }}

.strava-btn {{
  display: inline-flex; align-items: center; gap: 6px;
  font-family: 'Geist', sans-serif;
  font-size: 11px; font-weight: 600;
  background: rgba(252, 76, 2, 0.08);
  border: 1px solid rgba(252, 76, 2, 0.25);
  color: #fc4c02;
  padding: 6px 10px; border-radius: 7px;
  cursor: pointer; text-decoration: none;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.strava-btn:hover {{
  background: rgba(252, 76, 2, 0.16);
  border-color: rgba(252, 76, 2, 0.45);
}}
.strava-btn svg {{ width: 12px; height: 12px; fill: #fc4c02; }}

/* Theme toggle */
.theme-toggle {{
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px;
  gap: 0;
}}
.theme-toggle button {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 22px;
  background: transparent; border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 5px;
  padding: 0;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.theme-toggle button:hover {{ color: var(--text-primary); }}
.theme-toggle button.active {{
  background: var(--accent-dim);
  color: var(--accent);
}}
.theme-toggle button svg {{ width: 13px; height: 13px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
.topnav-actions {{ display: inline-flex; align-items: center; gap: 10px; }}

/* Chart toggle (theme-aware, used by Workout Mix per Season) */
.card-title-row {{
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 8px; flex-wrap: wrap;
}}
.card-title-row .card-title {{ margin-bottom: 0; }}
.chart-toggle {{
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px;
  gap: 0;
}}
.chart-toggle button {{
  background: transparent; border: none;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif; font-size: 11px;
  padding: 4px 10px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.chart-toggle button:hover {{ color: var(--text-primary); }}
.chart-toggle button.active {{
  background: var(--accent-dim);
  color: var(--accent);
}}

/* Tab nav */
.tabnav {{
  display: flex; gap: 4px;
  margin-bottom: -1px;
}}
.tab {{
  background: none; border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  padding: 10px 14px;
  cursor: pointer;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
  display: inline-flex; align-items: center; gap: 6px;
}}
.tab:hover {{ color: var(--text-primary); }}
.tab.active {{
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}}

/* Main content */
main {{
  flex: 1;
  max-width: 1100px; width: 100%;
  margin: 0 auto;
  padding: 32px 32px 80px;
}}

.page-header {{
  margin-bottom: 24px;
}}
.eyebrow {{
  font-family: 'Geist Mono', monospace;
  font-size: 10px; font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}}
.page-header h1 {{
  margin: 0;
  font-size: 26px; font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}}

.view {{ display: none; animation: fadeUp 240ms cubic-bezier(0.16, 1, 0.3, 1); }}
.view.active {{ display: block; }}

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
.card-header {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}}
.card-header .card-title {{ margin: 0; }}
.chart-caption {{
  margin-top: -12px; margin-bottom: 8px;
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: 'Geist Mono', monospace;
}}

/* Stat cards */
.stat-grid {{
  display: grid;
  grid-template-columns: repeat(6, 1fr);
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
  font-size: 26px; font-weight: 600;
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
}}

/* Notes search */
.notes-card .card-header {{ margin-bottom: 14px; }}
.notes-count {{
  font-family: 'Geist Mono', monospace;
  font-size: 11px; color: var(--text-tertiary);
}}
.notes-search {{
  position: relative;
  margin-bottom: 12px;
}}
.notes-search input {{
  width: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 36px 10px 14px;
  color: var(--text-primary);
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  outline: none;
  transition: border-color 120ms;
}}
.notes-search input:focus {{ border-color: var(--accent); }}
.notes-search input::placeholder {{ color: var(--text-tertiary); }}
.notes-search #notes-clear {{
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: var(--text-secondary);
  font-size: 18px; cursor: pointer; padding: 0 6px;
}}
.filter-pills {{
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-bottom: 12px;
}}
.filter-pill {{
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 11px; font-weight: 500;
  padding: 5px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.filter-pill:hover {{ color: var(--text-primary); }}
.filter-pill.active {{
  background: color-mix(in srgb, var(--pill-color, var(--accent)) 12%, transparent);
  border-color: color-mix(in srgb, var(--pill-color, var(--accent)) 30%, transparent);
  color: var(--pill-color, var(--accent));
}}
.filter-pill[data-type="all"].active {{
  background: var(--accent-dim);
  border-color: color-mix(in srgb, var(--accent) 30%, transparent);
  color: var(--accent);
}}

.notes-list {{
  max-height: 218px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 6px;
  padding-right: 4px;
}}
.notes-list::-webkit-scrollbar {{ width: 8px; }}
.notes-list::-webkit-scrollbar-thumb {{ background: var(--border-subtle); border-radius: 4px; }}
.note-row {{
  background: var(--bg-elevated);
  border-radius: 8px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: 72px 92px 64px 1fr 14px;
  gap: 12px; align-items: center;
  cursor: pointer;
  transition: background 120ms;
  text-align: left;
}}
.note-row > .type-badge {{ justify-self: start; }}
.note-row > .note-date,
.note-row > .note-miles {{ text-align: left; }}
.note-row:hover {{ background: color-mix(in srgb, var(--bg-elevated) 70%, var(--bg-surface)); }}
.note-row.expanded .note-text {{ -webkit-line-clamp: unset; display: block; white-space: pre-wrap; }}
.note-row.expanded .chev {{ transform: rotate(180deg); }}
.note-date {{
  font-family: 'Geist Mono', monospace; font-size: 11px;
  color: var(--text-tertiary); white-space: nowrap;
}}
.note-miles {{
  font-family: 'Geist Mono', monospace; font-size: 11px;
  color: var(--text-secondary); white-space: nowrap;
}}
.note-text {{
  color: var(--text-primary);
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.note-text mark {{
  background: color-mix(in srgb, var(--accent) 35%, transparent);
  color: var(--text-primary);
  border-radius: 2px;
}}
.chev {{
  color: var(--text-tertiary); font-size: 10px;
  transition: transform 240ms cubic-bezier(0.16, 1, 0.3, 1);
}}

/* Type badge */
.type-badge {{
  display: inline-block;
  font-size: 9px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 2px 7px; border-radius: 4px;
  background: color-mix(in srgb, var(--badge-color) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--badge-color) 30%, transparent);
  color: var(--badge-color);
}}

/* Heatmap */
.heatmap-card {{ overflow-x: auto; }}
.hm-mode-toggle {{
  display: inline-flex; gap: 2px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 2px;
}}
.hm-toggle {{
  background: none; border: none;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 11px;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 120ms;
}}
.hm-toggle:hover {{ color: var(--text-primary); }}
.hm-toggle.active {{
  background: var(--bg-glass);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}}

.hm-grid {{ display: flex; flex-direction: column; gap: 10px; }}
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
.hm-cell.hm-flash {{ animation: hm-flash-pulse 1.4s ease-out; transform-origin: center; transform-box: fill-box; }}
@keyframes hm-flash-pulse {{
  0%   {{ stroke: var(--accent); stroke-width: 0; transform: scale(1); }}
  20%  {{ stroke: var(--accent); stroke-width: 3; transform: scale(2.2); }}
  100% {{ stroke: var(--accent); stroke-width: 0; transform: scale(1); }}
}}
.hm-month {{ fill: var(--text-tertiary); font-size: 9px; font-family: 'Geist Mono', monospace; }}
.hm-dow   {{ fill: var(--text-tertiary); font-size: 9px; font-family: 'Geist Mono', monospace; }}

.hm-legend {{
  margin-top: 4px; margin-bottom: 14px;
  display: flex; gap: 14px; align-items: center;
  font-size: 10px; color: var(--text-tertiary);
  font-family: 'Geist Mono', monospace;
}}
.hm-legend-intensity {{ gap: 8px; }}
.hm-legend-item {{ display: inline-flex; gap: 6px; align-items: center; }}
.hm-legend-item .swatch {{ width: 12px; height: 12px; border-radius: 2px; }}
.hm-legend-grad {{
  display: inline-block;
  width: 140px; height: 10px; border-radius: 3px;
  background: linear-gradient(
    to right,
    color-mix(in srgb, var(--accent) 10%, transparent),
    var(--accent)
  );
}}
.hm-legend-meta {{ color: var(--text-secondary); }}
.hm-legend[hidden] {{ display: none; }}

/* Detail panel (click-to-detail side panel) */
.detail-backdrop {{
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45);
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
  box-shadow: -10px 0 30px rgba(0,0,0,0.5);
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
.detail-date {{
  font-family: 'Geist Mono', monospace;
  font-size: 14px;
  color: var(--text-primary);
}}
.detail-close {{
  background: none; border: none;
  color: var(--text-secondary);
  font-size: 24px; line-height: 1;
  cursor: pointer; padding: 4px 12px;
  border-radius: 6px;
  transition: background 150ms, color 150ms;
}}
.detail-close:hover {{ background: var(--bg-elevated); color: var(--text-primary); }}
.detail-body {{ flex: 1; overflow-y: auto; padding: 20px; }}
.detail-entry {{
  padding: 16px 0;
  border-bottom: 1px solid var(--border-subtle);
}}
.detail-entry:last-child {{ border-bottom: none; padding-bottom: 0; }}
.detail-entry:first-child {{ padding-top: 0; }}
.detail-entry-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
.detail-type-badge {{
  display: inline-block;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background: var(--badge-color, var(--accent));
  color: var(--bg-base);
}}
.detail-stats {{
  display: flex; gap: 18px; flex-wrap: wrap;
  font-family: 'Geist Mono', monospace;
  font-size: 13px;
  color: var(--text-secondary);
}}
.detail-stat-val {{ color: var(--text-primary); font-weight: 600; }}
.detail-race-info {{
  margin: 12px 0 0;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--race) 12%, transparent);
  border-left: 3px solid var(--race);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
}}
.detail-race-info strong {{ color: var(--text-primary); font-weight: 600; }}
.detail-comments {{
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}}
.detail-extras {{
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
}}
.detail-empty {{
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  padding: 60px 20px;
}}
.race-card[data-date] {{ cursor: pointer; transition: border-color 150ms, background 150ms; }}
.race-card[data-date]:hover {{ border-color: var(--accent); background: var(--accent-dim); }}
.race-card[data-date]:focus {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.hm-cell[data-date] {{ cursor: pointer; }}
@media (max-width: 900px) {{ .pr-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 600px) {{ .detail-panel {{ width: 100vw; }} }}

/* PR cards */
.pr-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}}
.pr-card {{
  position: relative;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 18px 20px;
  overflow: hidden;
}}
.pr-card::after {{
  content: '';
  position: absolute; top: 0; right: 0; bottom: 0;
  width: 4px; background: var(--pr-color);
}}
.pr-label {{
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 8px;
}}
.pr-time {{
  font-family: 'Geist Mono', monospace;
  font-size: 30px; font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--text-primary);
  line-height: 1;
}}
.pr-season {{
  margin-top: 6px;
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--text-tertiary);
}}


/* Race tabs + cards */
.race-tabs {{
  display: inline-flex; gap: 2px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 3px;
  margin-bottom: 16px;
}}
.race-tab {{
  background: none; border: none;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 12px; font-weight: 500;
  padding: 7px 14px;
  border-radius: 7px;
  cursor: pointer;
  transition: all 120ms;
  display: inline-flex; align-items: center; gap: 8px;
}}
.race-tab:hover {{ color: var(--text-primary); }}
.race-tab.active {{
  background: var(--bg-glass);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.25);
}}
.tab-count {{
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  background: var(--bg-elevated);
  padding: 2px 6px; border-radius: 4px;
  color: var(--text-tertiary);
}}
.race-tab.active .tab-count {{ background: var(--bg-base); color: var(--text-secondary); }}

.race-list {{ display: flex; flex-direction: column; gap: 8px; }}

/* Race controls (search / sort / filter) */
.race-controls {{
  display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  margin-bottom: 14px;
}}
.race-search {{
  position: relative;
  flex: 1 1 240px; min-width: 200px;
}}
.race-search input {{
  width: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  padding: 8px 30px 8px 12px;
  transition: border-color 120ms;
}}
.race-search input:focus {{ outline: none; border-color: var(--accent); }}
.race-search button {{
  position: absolute; top: 50%; right: 6px; transform: translateY(-50%);
  background: none; border: none;
  color: var(--text-tertiary);
  font-size: 16px; line-height: 1;
  cursor: pointer; padding: 4px 6px;
}}
.race-control-group {{
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--text-secondary);
}}
.race-control-label {{
  text-transform: uppercase; letter-spacing: 0.06em;
  font-weight: 600;
}}
.race-controls select {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: 'Geist', sans-serif;
  font-size: 12px;
  padding: 6px 10px;
  cursor: pointer;
}}
.race-controls select:focus {{ outline: none; border-color: var(--accent); }}
.race-pr-toggle {{
  cursor: pointer;
  user-select: none;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
}}
.race-pr-toggle input {{ accent-color: var(--accent); margin: 0; }}
.race-empty {{
  padding: 30px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  background: var(--bg-elevated);
  border: 1px dashed var(--border-subtle);
  border-radius: 10px;
}}
.race-card {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 14px 18px;
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: 14px; align-items: center;
  transition: border-color 120ms;
}}
.race-card:hover {{ border-color: var(--border); }}
.race-type-badge {{
  font-size: 9px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 3px 8px; border-radius: 4px;
  background: color-mix(in srgb, var(--badge-color) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--badge-color) 30%, transparent);
  color: var(--badge-color);
}}
.race-name {{
  font-size: 13px; font-weight: 500;
  color: var(--text-primary);
  line-height: 1.3;
}}
.race-sub {{
  margin-top: 3px;
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--text-tertiary);
}}
.race-time {{
  font-family: 'Geist Mono', monospace;
  font-size: 16px; font-weight: 600;
  color: var(--text-primary);
}}
.relay-tag {{
  font-family: 'Geist', sans-serif;
  font-size: 9px; font-weight: 500;
  color: var(--text-tertiary);
  margin-left: 6px;
  text-transform: lowercase;
}}
.pr-badge {{
  background: color-mix(in srgb, var(--race) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--race) 30%, transparent);
  color: var(--race);
  font-size: 9px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 2px 7px; border-radius: 4px;
}}
.race-summary {{
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--accent-dim);
  border: 1px solid color-mix(in srgb, var(--accent) 20%, transparent);
  border-radius: 8px;
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--text-secondary);
}}

/* Workout mix */
.type-stat-grid {{
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
  margin-bottom: 20px;
}}
@media (max-width: 800px) {{ .type-stat-grid {{ grid-template-columns: repeat(3, 1fr); }} }}
@media (max-width: 500px) {{ .type-stat-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
.type-stat-card {{
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px 18px;
  position: relative;
}}
.type-swatch {{
  width: 8px; height: 8px; border-radius: 2px;
  background: var(--ts-color);
  display: inline-block; margin-bottom: 8px;
}}
.type-num {{
  font-family: 'Geist Mono', monospace;
  font-size: 24px; font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.03em;
}}
.type-label {{
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 4px;
}}

/* Sparklines — vertically stacked rows */
.spark-grid {{
  display: flex; flex-direction: column;
  gap: 10px;
}}
.spark-card {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 12px 16px;
  display: grid;
  grid-template-columns: 80px 110px 1fr;
  align-items: center;
  gap: 16px;
}}
.spark-label {{
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
}}
.spark-stat {{ display: flex; align-items: baseline; gap: 6px; }}
.spark-num {{
  font-family: 'Geist Mono', monospace;
  font-size: 22px; font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  line-height: 1;
}}
.spark-sub {{
  font-size: 10px;
  color: var(--text-tertiary);
  white-space: nowrap;
}}
.spark-chart {{ min-width: 0; }}
.spark-chart .plotly-graph-div {{ width: 100% !important; }}

@media (max-width: 700px) {{
  .spark-card {{ grid-template-columns: 70px 1fr; row-gap: 6px; }}
  .spark-card .spark-chart {{ grid-column: 1 / -1; }}
}}

/* Patterns */
.patterns-grid {{
  display: flex; flex-direction: column; gap: 20px;
  margin-bottom: 20px;
}}
.patterns-grid .card {{ margin-bottom: 0; }}
.patterns-grid .plotly-graph-div {{ width: 100% !important; }}

.streak-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;
  text-align: left;
}}
.streak-num {{
  font-family: 'Geist Mono', monospace;
  font-size: 32px; font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--text-primary);
  line-height: 1;
}}
.streak-label {{
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.04em;
}}
"""


JS = r"""
// ─── Tab nav ────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.view;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + target).classList.add('active');
    history.replaceState(null, '', '#' + target);
    // Trigger Plotly redraw on visible charts (in case sizes were 0)
    document.querySelectorAll('#view-' + target + ' .js-plotly-plot').forEach(el => {
      window.Plotly && window.Plotly.Plots.resize(el);
    });
  });
});
const initialHash = (location.hash || '#overview').slice(1);
const initialTab = document.querySelector('[data-view="' + initialHash + '"]') ||
                   document.querySelector('[data-view="overview"]');
if (initialTab) initialTab.click();

// ─── Races: search / sort / filter ─────────────────────────────────────────
(function() {
  const dataEl = document.getElementById('races-data');
  if (!dataEl) return;
  const races  = JSON.parse(dataEl.textContent);
  const list   = document.getElementById('race-list');
  const summary= document.getElementById('race-summary');
  const queryEl   = document.getElementById('race-query');
  const clearEl   = document.getElementById('race-clear');
  const sortEl    = document.getElementById('race-sort');
  const distEl    = document.getElementById('race-distance');
  const prOnlyEl  = document.getElementById('race-pr-only');
  const tabs      = document.querySelectorAll('.race-tab');

  let activeCat = 'all';

  const BUCKET_ORDER = {"800m":1, "Mile":2, "1500m":3, "3k":4, "3k steeple":5, "5k":6, "6k":7};

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function highlight(s, q) {
    if (!q) return esc(s);
    const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    return esc(s).replace(re, m => '<mark>' + m + '</mark>');
  }

  function renderCard(r, q) {
    const relay = r.is_relay ? '<span class="relay-tag">relay</span>' : '';
    const pr    = r.pr ? '<span class="pr-badge">PR</span>' : '';
    return `<div class="race-card" data-date="${esc(r.date)}" tabindex="0" role="button">
      <span class="race-type-badge" style="--badge-color: ${r.type_color}">${esc(r.type_label)}</span>
      <div class="race-meta">
        <div class="race-name">${highlight(r.race, q)}</div>
        <div class="race-sub">${esc(r.season)} · ${highlight(r.distance, q)}</div>
      </div>
      <div class="race-time">${esc(r.time)}${relay}</div>
      ${pr}
    </div>`;
  }

  function render() {
    const q = queryEl.value.trim();
    const ql = q.toLowerCase();
    const dist = distEl.value;
    const prOnly = prOnlyEl.checked;
    const sort = sortEl.value;

    let filtered = races.filter(r => {
      if (activeCat !== 'all' && r.category !== activeCat) return false;
      if (dist && r.bucket !== dist) return false;
      if (prOnly && !r.pr) return false;
      if (ql) {
        const hay = (r.race + ' ' + r.distance).toLowerCase();
        if (!hay.includes(ql)) return false;
      }
      return true;
    });

    filtered.sort((a, b) => {
      switch (sort) {
        case 'date-asc':  return a.date.localeCompare(b.date);
        case 'date-desc': return b.date.localeCompare(a.date);
        case 'time-asc':
          if (a.time_seconds == null) return 1;
          if (b.time_seconds == null) return -1;
          return a.time_seconds - b.time_seconds;
        case 'distance': {
          const ao = BUCKET_ORDER[a.bucket] || 99;
          const bo = BUCKET_ORDER[b.bucket] || 99;
          return ao - bo || a.date.localeCompare(b.date);
        }
        case 'pr':
          return (b.pr - a.pr) || b.date.localeCompare(a.date);
        default: return 0;
      }
    });

    list.innerHTML = filtered.map(r => renderCard(r, q)).join('') ||
                     '<div class="race-empty">No races match the current filters.</div>';
    const prCount = filtered.reduce((n, r) => n + (r.pr ? 1 : 0), 0);
    summary.textContent = filtered.length === 0
      ? ''
      : `${prCount} PR${prCount === 1 ? '' : 's'} across ${filtered.length} race${filtered.length === 1 ? '' : 's'}`;
    clearEl.hidden = !q;

    // Wire up the click-to-detail handler on the newly rendered cards
    list.querySelectorAll('.race-card[data-date]').forEach(card => {
      card.addEventListener('click', () => window.__openRaceDetail && window.__openRaceDetail(card.dataset.date));
      card.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          window.__openRaceDetail && window.__openRaceDetail(card.dataset.date);
        }
      });
    });
  }

  tabs.forEach(tab => tab.addEventListener('click', () => {
    activeCat = tab.dataset.tab;
    tabs.forEach(t => t.classList.toggle('active', t === tab));
    render();
  }));
  queryEl.addEventListener('input', render);
  clearEl.addEventListener('click', () => { queryEl.value = ''; render(); queryEl.focus(); });
  sortEl.addEventListener('change', render);
  distEl.addEventListener('change', render);
  prOnlyEl.addEventListener('change', render);

  render();
})();

// ─── Heatmap mode toggle ────────────────────────────────────────────────────
function accentColor() {
  return getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#58a6ff';
}
document.querySelectorAll('.hm-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.mode;
    document.querySelectorAll('.hm-toggle').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const accent = accentColor();
    document.querySelectorAll('.hm-cell').forEach(cell => {
      if (cell.classList.contains('hm-rest')) return;
      const tcol = cell.dataset.typeColor;
      const top  = cell.dataset.typeOp;
      const iop  = cell.dataset.intOp;
      if (mode === 'type') {
        cell.setAttribute('fill', tcol);
        cell.setAttribute('fill-opacity', top);
      } else {
        cell.setAttribute('fill', accent);
        cell.setAttribute('fill-opacity', iop);
      }
    });
    document.querySelectorAll('.hm-legend').forEach(l => {
      l.hidden = (l.dataset.mode !== mode);
    });
  });
});

// ─── Note row → highlight calendar cell ─────────────────────────────────────
function flashHeatmapCell(dateStr) {
  if (!dateStr) return;
  const cell = document.querySelector('.hm-cell[data-date="' + dateStr + '"]');
  if (!cell) return;
  // Scroll the heatmap card so the cell is visible
  const card = cell.closest('.heatmap-card');
  if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  cell.classList.remove('hm-flash');
  void cell.getBoundingClientRect();  // force reflow so the animation can replay
  cell.classList.add('hm-flash');
  setTimeout(() => cell.classList.remove('hm-flash'), 1600);
}

// ─── Notes search ───────────────────────────────────────────────────────────
(function() {
  const dataEl = document.getElementById('notes-data');
  if (!dataEl) return;
  const notes = JSON.parse(dataEl.textContent);
  const list  = document.getElementById('notes-list');
  const count = document.getElementById('notes-count');
  const input = document.getElementById('notes-query');
  const clear = document.getElementById('notes-clear');
  let activeFilter = 'all';
  const TYPE_LABELS = {easy:'Easy', long:'Long', tempo:'Tempo', workout:'Workout', race:'Race'};
  const TYPE_COLORS = {easy:'#2dd4bf', long:'#a78bfa', tempo:'#f59e0b', workout:'#60a5fa', race:'#f87171'};

  function escape(s) { return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function highlight(s, q) {
    if (!q) return escape(s);
    const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    return escape(s).replace(re, m => '<mark>' + m + '</mark>');
  }

  function render() {
    const q = input.value.trim();
    const ql = q.toLowerCase();
    const filtered = notes.filter(n =>
      (activeFilter === 'all' || n.type === activeFilter) &&
      (!ql || n.note.toLowerCase().includes(ql) || (n.race_name || '').toLowerCase().includes(ql))
    );
    count.textContent = filtered.length + (filtered.length === 1 ? ' note' : ' notes');
    list.innerHTML = filtered.map((n, i) => {
      const milesText = n.miles ? n.miles.toFixed(1) + ' mi' : (n.race ? 'race' : '—');
      const typeColor = TYPE_COLORS[n.type] || '#58a6ff';
      return `<div class="note-row" data-i="${i}">
        <span class="type-badge" style="--badge-color:${typeColor}">${TYPE_LABELS[n.type]}</span>
        <span class="note-date">${n.date}</span>
        <span class="note-miles">${milesText}</span>
        <span class="note-text">${highlight(n.note, q)}</span>
        <span class="chev">▾</span>
      </div>`;
    }).join('');
    list.querySelectorAll('.note-row').forEach(row => {
      row.addEventListener('click', () => {
        row.classList.toggle('expanded');
        const dateEl = row.querySelector('.note-date');
        if (dateEl) flashHeatmapCell(dateEl.textContent.trim());
      });
    });
    clear.hidden = !q;
  }

  input.addEventListener('input', render);
  clear.addEventListener('click', () => { input.value = ''; render(); input.focus(); });
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      activeFilter = pill.dataset.type;
      render();
    });
  });
  render();
})();

// ─── Cross-chart date sync ──────────────────────────────────────────────────
var DATE_CHART_IDS = ["chart-cumulative","chart-weekly","chart-easy-pace","chart-pace-timeline","chart-pr-800m","chart-pr-mile","chart-pr-3k-steeple","chart-pr-5k-track","chart-pr-5k-xc"];
var syncing = false;
function syncDateRange(sourceId, eventdata) {
  if (syncing) return;
  var x0 = eventdata['xaxis.range[0]'];
  var x1 = eventdata['xaxis.range[1]'];
  var autorange = eventdata['xaxis.autorange'];
  if (x0 === undefined && x1 === undefined && !autorange) return;
  syncing = true;
  var promises = DATE_CHART_IDS.filter(id => id !== sourceId).map(id => {
    var el = document.getElementById(id);
    if (!el || !el._fullLayout) return Promise.resolve();
    if (autorange) return Plotly.relayout(el, {'xaxis.autorange': true});
    var upd = {};
    if (x0 !== undefined) upd['xaxis.range[0]'] = x0;
    if (x1 !== undefined) upd['xaxis.range[1]'] = x1;
    return Plotly.relayout(el, upd);
  });
  Promise.all(promises).finally(() => { syncing = false; });
}
DATE_CHART_IDS.forEach(id => {
  var el = document.getElementById(id);
  if (el && el.on) el.on('plotly_relayout', ev => syncDateRange(id, ev));
});

// ─── Click-to-detail panel ──────────────────────────────────────────────────
(function() {
  var dataEl = document.getElementById('day-index');
  var DAY_INDEX = dataEl ? JSON.parse(dataEl.textContent) : {};
  var TYPE_COLORS_D = {easy:'#2dd4bf', long:'#a78bfa', tempo:'#f59e0b', workout:'#60a5fa', race:'#f87171'};
  var TYPE_LABELS_D = {easy:'Easy', long:'Long', tempo:'Tempo', workout:'Workout', race:'Race'};

  var panel = document.getElementById('detail-panel');
  var backdrop = document.getElementById('detail-backdrop');
  var dateEl = document.getElementById('detail-date');
  var body = document.getElementById('detail-body');
  if (!panel) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function fmtPace(p) {
    var f = parseFloat(p);
    if (!f || isNaN(f)) return '';
    var m = Math.floor(f);
    var s = Math.round((f - m) * 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
  }
  function fmtLongDate(ds) {
    var d = new Date(ds + 'T00:00:00');
    if (isNaN(d.getTime())) return ds;
    return d.toLocaleDateString('en-US', {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'});
  }
  function renderEntry(e) {
    var color = TYPE_COLORS_D[e.type] || '#58a6ff';
    var label = TYPE_LABELS_D[e.type] || (e.type_raw || 'Workout');
    var statsBits = [];
    if (e.miles)   statsBits.push('<span><span class="detail-stat-val">' + e.miles.toFixed(1) + '</span> mi</span>');
    if (e.pace)    statsBits.push('<span><span class="detail-stat-val">' + fmtPace(e.pace) + '</span> /mi</span>');
    if (e.minutes) statsBits.push('<span><span class="detail-stat-val">' + Math.round(e.minutes) + '</span> min</span>');
    var stats = statsBits.length ? '<div class="detail-stats">' + statsBits.join('') + '</div>' : '';
    var race = '';
    if (e.is_race) {
      var parts = [];
      if (e.race)      parts.push('<strong>' + esc(e.race) + '</strong>');
      if (e.race_dist) parts.push(esc(e.race_dist));
      if (e.race_time) parts.push(esc(e.race_time));
      race = '<div class="detail-race-info">' + parts.join(' · ') + '</div>';
    }
    var typeRawDiff = e.type_raw && e.type_raw.toLowerCase() !== label.toLowerCase()
      ? '<span style="color:var(--text-tertiary);font-size:12px;font-family:\'Geist Mono\',monospace">' + esc(e.type_raw) + '</span>'
      : '';
    return (
      '<div class="detail-entry">' +
        '<div class="detail-entry-head">' +
          '<span class="detail-type-badge" style="--badge-color:' + color + '">' + esc(label) + '</span>' +
          typeRawDiff +
        '</div>' +
        stats + race +
        (e.comments ? '<div class="detail-comments">' + esc(e.comments) + '</div>' : '') +
        (e.extras ? '<div class="detail-extras">Extras: ' + esc(e.extras) + '</div>' : '') +
      '</div>'
    );
  }
  function openDetail(dateStr) {
    if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return;
    var entries = DAY_INDEX[dateStr] || [];
    dateEl.textContent = fmtLongDate(dateStr);
    body.innerHTML = entries.length
      ? entries.map(renderEntry).join('')
      : '<div class="detail-empty">No entry recorded for this day.</div>';
    panel.classList.add('open');
    panel.setAttribute('aria-hidden', 'false');
    backdrop.classList.add('open');
  }
  function closeDetail() {
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden', 'true');
    backdrop.classList.remove('open');
  }

  document.getElementById('detail-close').addEventListener('click', closeDetail);
  backdrop.addEventListener('click', closeDetail);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

  // Plotly chart points → detail panel
  ['chart-cumulative','chart-easy-pace','chart-pace-timeline','chart-pr-800m','chart-pr-mile','chart-pr-3k-steeple','chart-pr-5k-track','chart-pr-5k-xc'].forEach(id => {
    var el = document.getElementById(id);
    if (el && el.on) {
      el.on('plotly_click', ev => {
        if (!ev.points || !ev.points.length) return;
        var pt = ev.points[0];
        var x = typeof pt.x === 'string' ? pt.x : null;
        if (x && /^\d{4}-\d{2}-\d{2}$/.test(x)) openDetail(x);
      });
    }
  });

  // Heatmap cells (rest days are excluded by [data-date] selector)
  document.querySelectorAll('.hm-cell[data-date]').forEach(cell => {
    cell.addEventListener('click', () => openDetail(cell.dataset.date));
  });

  // Race cards are rendered client-side; expose openDetail so the Races
  // module can wire each card after each re-render.
  window.__openRaceDetail = openDetail;
})();

// ─── Chart toggle (per-chart y-data switcher) ──────────────────────────────
(function() {
  function applyToggle(toggle, mode) {
    var target = toggle.dataset.toggleTarget;
    var gd = document.getElementById(target);
    if (!gd || !window.Plotly) return;
    var key = mode === 'pct' ? 'pct' : 'miles';
    var ys = JSON.parse(toggle.dataset[key]);
    Plotly.restyle(gd, { y: ys });
    Plotly.relayout(gd, {
      'yaxis.title.text': key === 'pct' ? '% of Season Miles' : 'Miles',
    });
    toggle.querySelectorAll('button').forEach(function(b) {
      b.classList.toggle('active', b.dataset.mode === key);
    });
  }
  document.querySelectorAll('.chart-toggle').forEach(function(toggle) {
    toggle.querySelectorAll('button').forEach(function(b) {
      b.addEventListener('click', function() { applyToggle(toggle, b.dataset.mode); });
    });
  });
})();

// ─── Theme toggle (light / dark / system) ───────────────────────────────────
(function() {
  var root = document.documentElement;
  var mq = window.matchMedia('(prefers-color-scheme: light)');
  var STORAGE_KEY = 'theme';

  function getStoredMode() {
    var v = localStorage.getItem(STORAGE_KEY);
    return (v === 'light' || v === 'dark' || v === 'system') ? v : 'system';
  }
  function effectiveTheme(mode) {
    if (mode === 'system') return mq.matches ? 'light' : 'dark';
    return mode;
  }
  function cssVar(name) {
    return getComputedStyle(root).getPropertyValue(name).trim();
  }
  function applyChartTheme() {
    var textPrimary   = cssVar('--text-primary');
    var textSecondary = cssVar('--text-secondary');
    var textTertiary  = cssVar('--text-tertiary');
    var grid          = cssVar('--grid');
    var bgElevated    = cssVar('--bg-elevated');
    var border        = cssVar('--border');
    var upd = {
      'xaxis.tickfont.color': textTertiary,
      'yaxis.tickfont.color': textTertiary,
      'xaxis.title.font.color': textSecondary,
      'yaxis.title.font.color': textSecondary,
      'xaxis.gridcolor': grid,
      'yaxis.gridcolor': grid,
      'xaxis.zerolinecolor': grid,
      'yaxis.zerolinecolor': grid,
      'font.color': textSecondary,
      'legend.font.color': textSecondary,
      'hoverlabel.font.color': textPrimary,
      'hoverlabel.bgcolor': bgElevated,
      'hoverlabel.bordercolor': border,
    };
    document.querySelectorAll('.plotly-graph-div').forEach(function(el) {
      if (el && el._fullLayout && window.Plotly) {
        try { Plotly.relayout(el, upd); } catch (e) { /* chart may not be ready */ }
      }
    });
  }
  function setActiveButton(mode) {
    document.querySelectorAll('.theme-toggle button').forEach(function(b) {
      b.classList.toggle('active', b.dataset.theme === mode);
    });
  }
  function applyTheme(mode) {
    var eff = effectiveTheme(mode);
    root.classList.toggle('light', eff === 'light');
    setActiveButton(mode);
    applyChartTheme();
  }

  var current = getStoredMode();
  applyTheme(current);

  document.querySelectorAll('.theme-toggle button').forEach(function(b) {
    b.addEventListener('click', function() {
      current = b.dataset.theme;
      localStorage.setItem(STORAGE_KEY, current);
      applyTheme(current);
    });
  });

  mq.addEventListener('change', function() {
    if (current === 'system') applyTheme('system');
  });
})();
"""


# ─── HTML assembler ───────────────────────────────────────────────────────────

def build_html(rows):
    stats = compute_stats(rows)
    races_by_cat = build_race_records(rows)
    day_index_json = json.dumps(build_day_index(rows)).replace("</", "<\\/")

    # Date range for wordmark
    dates_sorted = sorted(r["date"] for r in rows if r["date"])
    first_year = dates_sorted[0][:4] if dates_sorted else ""
    last_year  = dates_sorted[-1][:4] if dates_sorted else ""
    date_range = f"{first_year}–{last_year}"

    strava_chevron = (
        '<svg viewBox="0 0 24 24"><path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172'
        'h-3.066m-7.008-5.599l2.836 5.599h4.172L10.463 0l-7 13.828h4.169"/></svg>'
    )

    sections = (
        section_overview(rows, stats)
        + section_volume(rows)
        + section_workout_mix(rows, races_by_cat)
        + section_performance(rows, races_by_cat)
        + section_races(races_by_cat)
        + section_patterns(rows, stats)
    )

    tabs = """
      <button class="tab" data-view="overview">Overview</button>
      <button class="tab" data-view="volume">Volume</button>
      <button class="tab" data-view="mix">Workout Mix</button>
      <button class="tab" data-view="performance">Performance</button>
      <button class="tab" data-view="races">Races</button>
      <button class="tab" data-view="patterns">Patterns</button>
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>College Running Log — Strava Before Strava</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  {PLOTLY_CDN}
  <style>{CSS}</style>
  <script data-goatcounter="https://ducktapegirl.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</head>
<body>
  <div class="shell">
    <nav class="topnav">
      <div class="topnav-row row1">
        <div class="wordmark">
          <span class="wordmark-name">College Running Log</span>
          <span class="wordmark-meta">{date_range}</span>
        </div>
        <div class="topnav-actions">
          <div class="theme-toggle" role="group" aria-label="Theme">
            <button type="button" data-theme="light" title="Light" aria-label="Light theme">
              <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
            </button>
            <button type="button" data-theme="dark" title="Dark" aria-label="Dark theme">
              <svg viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/></svg>
            </button>
            <button type="button" data-theme="system" title="System" aria-label="Use system theme">
              <svg viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 21h8M12 18v3"/></svg>
            </button>
          </div>
          <a class="strava-btn" href="strava.html">
            {strava_chevron}<span>My Strava Dashboard</span>
          </a>
        </div>
      </div>
      <div class="topnav-row row2">
        <div class="tabnav">{tabs}</div>
      </div>
    </nav>
    <main>
      {sections}
    </main>
    <footer class="dash-footer">
      This dashboard was created using Claude Code. <a href="running_log_story.html">See how I did it.</a>
    </footer>
  </div>
  <aside class="detail-panel" id="detail-panel" aria-hidden="true" role="complementary">
    <div class="detail-header">
      <div class="detail-date" id="detail-date"></div>
      <button class="detail-close" id="detail-close" aria-label="Close detail panel">×</button>
    </div>
    <div class="detail-body" id="detail-body"></div>
  </aside>
  <div class="detail-backdrop" id="detail-backdrop"></div>
  <script id="day-index" type="application/json">{day_index_json}</script>
  <script>{JS}</script>
</body>
</html>
"""


def main():
    rows = load_rows()
    html_out = build_html(rows)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)
    races = build_race_records(rows)
    print(f"Wrote {OUT_PATH}")
    print(f"  rows: {len(rows)}")
    print(f"  races: XC={len(races['crossCountry'])}, "
          f"Indoor={len(races['indoorTrack'])}, "
          f"Outdoor={len(races['outdoorTrack'])}, "
          f"total={sum(len(v) for v in races.values())}")


if __name__ == "__main__":
    main()
