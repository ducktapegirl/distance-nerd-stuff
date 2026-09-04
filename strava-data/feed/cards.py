"""One function per catalogued idea, all 63 of them.

A card is a whole 800x480 screen carrying *one* idea - the Sticky is a fridge
magnet glanced at in passing, not a dashboard you sit in front of. The RSS
title and summary live on the same object so the two transports cannot drift.

Layout lives in ``layouts.py``; these functions are mostly data binding. Each
is registered with its catalogue number, family and a one-line recipe, which
the contact sheet reads.

Numbering matches Project Docs/Plans/strava-data/epaper-feed-brainstorm.md.
"""

import math
from datetime import date, datetime, timezone

from nerd_common.format import mmss

from . import fmt as F
from . import layouts as L
from . import metrics as M
from . import places as P
from . import stats as St
from . import svg as S
from .config import BLACK, DARK, H, KM_TO_MI, LIGHT, PAD, W, WHITE
from . import geo
from . import journey

FAMILIES = {
    "A": "Right now", "B": "Streaks & consistency", "C": "Volume & progress",
    "D": "The racing self", "E": "Gear", "F": "Places",
    "G": "Weather & environment", "H": "Records", "I": "Memory",
    "J": "Voice & whimsy", "K": "Meta",
}

CXD = W / 2

_REGISTRY = []


def card(idea, family, recipe):
    """Register a card builder with its catalogue metadata."""
    def deco(fn):
        _REGISTRY.append((idea, family, recipe, fn))
        return fn
    return deco


def _mk(cid, title, summary, kicker, b, idea, family, recipe):
    c = L.base(cid, title, summary, kicker, b["asof"])
    c.idea, c.family, c.recipe = idea, family, recipe
    return c


def _sport_glyph(sport):
    if sport in ("Run", "TrailRun", "Walk", "Hike"):
        return S.glyph_runner
    if sport in ("MountainBikeRide", "Ride", "EBikeRide"):
        return S.glyph_bike
    return None


# ══ A · Right now ═══════════════════════════════════════════════════════

@card(1, "A", "ACWR: 7-day mean daily suffer score / 28-day mean")
def c01_load(b, o):
    a = M.acwr(b["acts"], b["asof"])
    r = a["ratio"]
    c = _mk("load", f"Training load {r:.2f} — {a['band']}" if r else "Training load — no data",
            (f"Acute:chronic workload ratio is {r:.2f} ({a['band']}): the last 7 days of suffer "
             f"score against the 28-day average." if r else
             "Not enough recent suffer-score data to compute a load ratio."),
            "training load", b, 1, "A", "ACWR: 7-day mean daily suffer score / 28-day mean")
    if r is None:
        return L.hero_number(c, "—", sub="no data")
    L.dial(c, r, 2.0,
           [(0.0, 0.8, 0.25), (0.8, 1.3, 0.45), (1.3, 1.5, 0.7), (1.5, 2.0, 1.0)],
           f"{r:.2f}", a["band"], ticks=(0.8, 1.3, 1.5))
    return c


@card(2, "A", "asof date minus the last active date")
def c02_days_since(b, o):
    st = M.streaks(b["acts"], b["asof"])
    n = st["days_since"]
    c = _mk("days-since", f"{n} days since the last activity",
            f"The last recorded activity was {n} day{'s' if n != 1 else ''} ago.",
            "days since", b, 2, "A", "asof date minus the last active date")
    L.hero_number(c, n, sub="days since an activity" if n != 1 else "day since an activity")
    return c


@card(3, "A", "the newest row of activities.csv, unit-converted")
def c03_last_activity(b, o):
    a = b["acts"][-1]
    c = _mk("last", f"Last out — {a['name']}",
            f"{a['_mi']:.1f} mi of {F.sport_activity(a['sport_type'])} with {a['_ft']:.0f} ft of climbing on "
            f"{F.day(a['_date'])}.",
            "last activity", b, 3, "A", "the newest row of activities.csv, unit-converted")
    L.text_card(c, a["name"], a.get("description") or None,
                tag=f"{a['_mi']:.1f} mi · {a['_ft']:.0f} ft · {F.sport(a['sport_type'])}")
    g = _sport_glyph(a["sport_type"])
    if g:
        c.add(g(W - PAD - 92, 92, 92))
    return c


@card(4, "A", "sum over the 7-day window ending at the last data day")
def c04_week_totals(b, o):
    t = M.totals(M.window(b["acts"], b["asof"], 7))
    c = _mk("week", f"Last 7 days: {t['mi']:.0f} mi, {t['ft']:,.0f} ft",
            f"{t['n']} activities in the last seven days: {t['mi']:.1f} miles, "
            f"{t['hours']:.1f} moving hours and {t['ft']:,.0f} feet of climbing.",
            "last 7 days", b, 4, "A", "sum over the 7-day window ending at the last data day")
    L.stat_trio(c, [(f"{t['mi']:.0f}", "miles"), (f"{t['hours']:.1f}", "hours"),
                    (f"{t['ft']:,.0f}", "feet")])
    return c


@card(5, "A", "ACWR band crossed with days-since; a word, not a number")
def c05_fresh(b, o):
    a = M.acwr(b["acts"], b["asof"])
    st = M.streaks(b["acts"], b["asof"])
    since, r = st["days_since"], a["ratio"] or 1.0
    if since >= 5:
        word, note = "RUSTY", f"{since} days off"
    elif r > 1.5:
        word, note = "COOKED", f"load {r:.2f}"
    elif r > 1.3:
        word, note = "SPICY", f"load {r:.2f}"
    elif r < 0.8:
        word, note = "FRESH", f"load {r:.2f}"
    else:
        word, note = "READY", f"load {r:.2f}"
    c = _mk("fresh", f"Current state: {word.lower()}",
            f"With a load ratio of {r:.2f} and {since} day{'s' if since != 1 else ''} since the "
            f"last activity, the verdict is {word.lower()}.",
            "state of the athlete", b, 5, "A",
            "ACWR band crossed with days-since; a word, not a number")
    L.hero_number(c, word, sub=note, size=140)
    return c


@card(6, "A", "GPS stream of the most recent activity, cosine-corrected")
def c06_last_route(b, o):
    for a in reversed(b["acts"]):
        r = M.route_for(a)
        if r:
            break
    else:
        return None
    c = _mk("last-route", f"Last route — {a['name']}",
            f"The most recent GPS track: {a['_mi']:.1f} mi on "
            f"{F.day(a['_date'])}.",
            "last route", b, 6, "A",
            "GPS stream of the most recent activity, cosine-corrected")
    L.route_card(c, r["path"], r["w"], r["h"], [
        (a["name"], 38, "bold", BLACK), (f"{a['_mi']:.1f} mi", 54, "bold", BLACK),
        (f"{a['_ft']:.0f} ft climbed", 28, "normal", DARK),
    ])
    return c


# ══ B · Streaks & consistency ═══════════════════════════════════════════

@card(7, "B", "consecutive days back from the last data day with an activity")
def c07_streak(b, o):
    st = M.streaks(b["acts"], b["asof"])
    c = _mk("streak", f"{st['current']}-day streak (best ever {st['longest']})",
            f"Currently {st['current']} consecutive active day"
            f"{'s' if st['current'] != 1 else ''}; the longest run ever is {st['longest']}.",
            "active streak", b, 7, "B",
            "consecutive days back from the last data day with an activity")
    L.hero_number(c, st["current"], sub="day active streak")
    return c


@card(8, "B", "gaps between consecutive active days")
def c08_rest(b, o):
    r = M.rest_days(b["acts"], b["asof"])
    c = _mk("rest", f"{r['rest_days']} rest days, longest gap {r['longest_gap']}",
            f"{r['rest_days']} rest days across the whole log, and the longest unbroken "
            f"break was {r['longest_gap']} days.",
            "rest days", b, 8, "B", "gaps between consecutive active days")
    L.stat_trio(c, [(r["rest_days"], "rest days"), (r["longest_gap"], "longest gap"),
                    (r["since_rest"], "since a rest")])
    return c


@card(9, "B", "one cell per day, filled if any activity that day")
def c09_strip(b, o):
    days = M.last_30_strip(b["acts"], b["asof"])
    n = sum(days)
    st = M.streaks(b["acts"], b["asof"])
    c = _mk("strip", f"{n} active days in the last 30",
            f"{n} of the last 30 days had an activity. Longest streak ever: {st['longest']} "
            f"days; {st['active_days']} active days out of {st['span_days']}.",
            "last 30 days", b, 9, "B", "one cell per day, filled if any activity that day")
    # Two rows of 15, not one of 30: a single row forces 20px cells (~2 mm on
    # this panel) that vanish at arm's length.
    L.cell_grid(c, [1.0 if d else 0.0 for d in days], per_row=15,
                headline=f"{n} / 30", labels=("30 days ago", "today"))
    return c


@card(10, "B", "this week's miles per weekday vs the 8-week median")
def c10_week_shape(b, o):
    rows = M.week_shape(b["acts"], b["asof"])
    peak = max([max(cur, med) for _, cur, med in rows] + [1.0])
    c = _mk("week-shape", f"This week's shape — {sum(r[1] for r in rows):.0f} mi so far",
            "Miles by weekday this week, against the median of the last eight weeks.",
            "this week vs usual", b, 10, "B",
            "this week's miles per weekday vs the 8-week median")
    n = len(rows)
    bw = (W - 2 * PAD) / n
    base = 372
    for i, (name, cur, med) in enumerate(rows):
        x = PAD + i * bw
        c.add(S.rect(x + 8, base - 190 * med / peak, bw - 16, 190 * med / peak,
                     fill=WHITE, stroke=LIGHT, sw=3))
        c.add(S.rect(x + 8, base - 190 * cur / peak, bw - 16, 190 * cur / peak, fill=BLACK))
        c.add(S.text(x + bw / 2, base + 34, name.upper(), 26, "bold",
                     anchor="middle", fill=DARK, tracking=1))
    c.add(S.line(PAD, base, W - PAD, base, sw=3))
    return c


@card(11, "B", "distinct active days / calendar days spanned")
def c11_consistency(b, o):
    st = M.streaks(b["acts"], b["asof"])
    pct = st["active_days"] / st["span_days"] * 100 if st["span_days"] else 0
    c = _mk("consistency", f"Out {pct:.0f}% of all days",
            f"{st['active_days']} active days across {st['span_days']} calendar days — "
            f"{pct:.0f}% of every day since the log began.",
            "consistency", b, 11, "B", "distinct active days / calendar days spanned")
    # A split disc: the filled wedge is the active share.
    cx, cy, r = CXD, 268, 108
    c.add(S.circle(cx, cy, r, fill=WHITE, stroke=BLACK, sw=4))
    th = 2 * math.pi * pct / 100
    steps = max(2, int(60 * pct / 100))
    pts = [(cx, cy)] + [(cx + r * math.sin(th * i / steps),
                         cy - r * math.cos(th * i / steps)) for i in range(steps + 1)]
    c.add(S.polygon(pts, fill=S.tone(0.75)))
    c.add(S.circle(cx, cy, r, fill="none", stroke=BLACK, sw=4))
    c.add(S.text(W - PAD, cy - 8, f"{pct:.0f}%", 92, "bold", anchor="end"),
          S.text(W - PAD, cy + 36, "OF ALL DAYS", 28, "bold", anchor="end",
                 fill=DARK, tracking=3))
    return c


@card(12, "B", "activity count grouped by weekday over the whole log")
def c12_weekday(b, o):
    rows = M.by_weekday(b["acts"])
    peak = max(n for _, n, _ in rows) or 1
    top = max(rows, key=lambda r: r[1])
    low = min(rows, key=lambda r: r[1])
    c = _mk("weekday", f"{top[0]} is the big day ({top[1]} activities)",
            f"Across the whole log {top[0]} carries {top[1]} activities and {low[0]} "
            f"the fewest at {low[1]} — the weekend is not the busy end.",
            "day-of-week fingerprint", b, 12, "B",
            "activity count grouped by weekday over the whole log")
    n = len(rows)
    bw = (W - 2 * PAD) / n
    base = 372
    for i, (name, cnt, _mi) in enumerate(rows):
        x = PAD + i * bw
        h = 200 * cnt / peak
        c.add(S.rect(x + 8, base - h, bw - 16, h, fill=BLACK if cnt == top[1] else S.tone(0.6)))
        c.add(S.text(x + bw / 2, base - h - 12, str(cnt), 28, "bold", anchor="middle"),
              S.text(x + bw / 2, base + 34, name[:3].upper(), 26, "bold",
                     anchor="middle", fill=DARK, tracking=1))
    c.add(S.line(PAD, base, W - PAD, base, sw=3))
    return c


@card(13, "B", "current streak against the all-time longest")
def c13_streak_race(b, o):
    st = M.streaks(b["acts"], b["asof"])
    c = _mk("streak-race", f"Streak {st['current']} vs record {st['longest']}",
            f"The current {st['current']}-day streak against the {st['longest']}-day record.",
            "streak vs record", b, 13, "B", "current streak against the all-time longest")
    L.two_up(c, ("now", st["current"], "days"), ("record", st["longest"], "days"),
             delta=f"{st['longest'] - st['current']} to beat"
             if st["longest"] > st["current"] else "record equalled")
    return c


# ══ C · Volume & progress ═══════════════════════════════════════════════

@card(14, "C", "miles this year to date vs the same calendar date last year")
def c14_ytd(b, o):
    y = M.ytd_compare(b["acts"], b["asof"])
    d = y["this"] - y["last"]
    c = _mk("ytd", f"{y['this']:.0f} mi YTD vs {y['last']:.0f} last year",
            f"{y['this']:.0f} miles so far in {y['year']}, against {y['last']:.0f} by the same "
            f"date in {y['year'] - 1} — {abs(d):.0f} miles {'ahead' if d >= 0 else 'behind'}.",
            "year to date", b, 14, "C",
            "miles this year to date vs the same calendar date last year")
    L.two_up(c, (str(y["year"]), f"{y['this']:.0f}", "miles"),
             (str(y["year"] - 1), f"{y['last']:.0f}", "by this date"),
             delta=f"{'+' if d >= 0 else '−'}{abs(d):.0f} mi")
    return c


@card(15, "C", "this calendar month vs the median of the last 12")
def c15_month(b, o):
    months = M.monthly_miles(b["acts"], 13)
    cur = months[-1][1]
    hist = sorted(v for _, v in months[:-1])
    med = hist[len(hist) // 2] if hist else 0.0
    c = _mk("month", f"{cur:.0f} mi this month (median {med:.0f})",
            f"{cur:.0f} miles in {months[-1][0]}, against a {med:.0f}-mile median over the "
            f"previous twelve months.",
            "this month", b, 15, "C", "this calendar month vs the median of the last 12")
    # A thermometer that fills against the median mark.
    x, y, w, h = PAD + 40, 200, W - 2 * PAD - 80, 74
    peak = max(cur, med) * 1.25 or 1.0
    c.add(S.rect(x, y, w, h, fill=WHITE, stroke=BLACK, sw=4))
    c.add(S.rect(x + 4, y + 4, (w - 8) * cur / peak, h - 8, fill=BLACK))
    mx = x + w * med / peak
    c.add(S.line(mx, y - 22, mx, y + h + 22, stroke=DARK, sw=4, dash="8 8"),
          S.text(mx, y - 32, "MEDIAN", 26, "bold", anchor="middle", fill=DARK, tracking=2))
    c.add(S.text(PAD, 372, f"{cur:.0f} MI", 76, "bold"),
          S.text(W - PAD, 372, months[-1][0], 30, "bold", anchor="end", fill=DARK))
    return c


@card(16, "C", "sum of miles over the trailing 365 days")
def c16_odometer(b, o):
    yr = M.totals(M.window(b["acts"], b["asof"], 365))
    digits = f"{yr['mi']:,.0f}"
    c = _mk("odometer", f"{digits} mi in the last 12 months",
            f"{yr['mi']:,.0f} miles, {yr['ft']:,.0f} feet of climbing and {yr['hours']:.0f} "
            f"moving hours across {yr['n']} activities in the last 365 days.",
            "rolling 12 months", b, 16, "C", "sum of miles over the trailing 365 days")
    box_w, box_h, gap = 84, 130, 10
    chars = list(digits)
    total = sum(box_w if ch.isdigit() else 34 for ch in chars) + gap * (len(chars) - 1)
    x, y = CXD - total / 2, 150
    for ch in chars:
        w = box_w if ch.isdigit() else 34
        if ch.isdigit():
            c.add(S.rect(x, y, w, box_h, fill=WHITE, stroke=BLACK, sw=4),
                  S.text(x + w / 2, y + 100, ch, 96, "bold", anchor="middle"))
        else:
            c.add(S.text(x + w / 2, y + 100, ch, 96, "bold", anchor="middle", fill=DARK))
        x += w + gap
    c.add(S.text(CXD, y + box_h + 52, "MILES · LAST 365 DAYS", 30, "bold",
                 anchor="middle", tracking=4))
    return c


@card(17, "C", "miles per calendar month, last 13 months")
def c17_sparkline(b, o):
    months = M.monthly_miles(b["acts"], 13)
    vals = [v for _, v in months]
    c = _mk("sparkline", f"13 months of volume — {vals[-1]:.0f} mi latest",
            f"Monthly mileage over the last 13 months, from {min(vals):.0f} to {max(vals):.0f}, "
            f"finishing at {vals[-1]:.0f}.",
            "monthly volume", b, 17, "C", "miles per calendar month, last 13 months")
    L.spark(c, vals, labels=(months[0][0], months[-1][0]),
            headline=f"{vals[-1]:.0f} mi", sub=f"range {min(vals):.0f}–{max(vals):.0f} mi")
    return c


@card(18, "C", "sum of total_elevation_gain_m, converted, over 29,032 ft")
def c18_everest(b, o):
    e = M.everest(b["acts"])
    whole, frac = int(e["multiple"]), e["multiple"] - int(e["multiple"])
    c = _mk("everest", f"{e['ft']:,.0f} ft climbed — {e['multiple']:.1f} × Everest",
            f"All-time elevation gain is {e['ft']:,.0f} feet, or {e['multiple']:.1f} times the "
            f"29,032-foot height of Everest.",
            "total elevation", b, 18, "C",
            "sum of total_elevation_gain_m, converted, over 29,032 ft")
    size, gap = 138, 10
    shown = min(whole, 5)
    total = (shown + 1) * size + shown * gap
    x, y = CXD - total / 2, 196
    for _ in range(shown):
        c.add(S.glyph_mountain(x, y, size, filled=True))
        x += size + gap
    c.add(S.glyph_mountain(x, y, size, fill_frac=frac, fill_colour=S.tone(0.45)))
    c.add(S.text(PAD, 160, f"{e['ft']:,.0f} FT", 76, "bold"),
          S.text(W - PAD, 160, f"{e['multiple']:.1f}× EVEREST", 34, "bold",
                 anchor="end", tracking=2))
    return c


def _journey(b, group):
    """The map + milepost hybrid: an orientation map above, precise strip below.

    The route is real interstate geometry, shortest-pathed offline by
    tools/gen_journey.py; the mileages are measured along that road.
    """
    if group == "run":
        total = M.totals(b["acts"], M.is_run)["mi"]
        glyph, verb = S.glyph_runner, "run"
    else:
        total = M.totals(b["acts"], M.is_bike)["mi"]
        glyph, verb = S.glyph_bike, "ridden"

    j = journey.position(total, group)
    cor = j["corridor"]
    label, dest = cor["label"], cor["destination"]
    ahead = j["ahead"]["name"]
    behind = j["behind"]["name"] if j["behind"] else "home"
    short = ahead.split(",")[0]

    if j["lapped"]:
        title = (f"{label.title()} · {total:,.0f} mi — {j['laps']:.1f}× the road to {dest}")
        summary = (f"{total:,.0f} miles {verb} is {j['laps']:.1f} times the "
                   f"{cor['total_mi']:,.0f}-mile interstate route from 92129 to {dest}.")
    else:
        title = (f"{label.title()} · {total:,.0f} mi — {j['remaining_mi']:,.0f} mi "
                 f"to {short}")
        summary = (f"Measured along {cor['road']} out of 92129, {total:,.0f} miles {verb} puts "
                   f"you past {behind} with {j['remaining_mi']:,.0f} miles to {ahead} — "
                   f"{j['route_frac'] * 100:.0f}% of the {cor['total_mi']:,.0f}-mile road to "
                   f"{dest}.")

    c = _mk(f"journey-{group}", title, summary, f"{label} · road to {dest}", b, 19, "C",
            "cumulative miles placed on a real interstate route, shortest-pathed offline")

    # ── the numbers, left column ──────────────────────────────────────────
    c.add(S.text(PAD, 158, f"{total:,.0f}", 80, "bold"),
          S.text(PAD, 194, f"MILES {verb.upper()}", 26, "bold", fill=DARK, tracking=3))
    if j["lapped"]:
        c.add(S.text(PAD, 248, f"{j['laps']:.1f}×", 44, "bold"),
              S.text(PAD, 282, f"THE ROAD TO {dest.upper()}", 26, "bold",
                     fill=DARK, tracking=2))
    else:
        lbl, lsz = S.fit_text(f"TO {short.upper()}", 26, 280, tracking=2)
        c.add(S.text(PAD, 248, f"{j['remaining_mi']:,.0f} MI", 44, "bold"),
              S.text(PAD, 282, lbl, lsz, "bold", fill=DARK, tracking=2))

    # ── orientation map, top right ────────────────────────────────────────
    path = [tuple(q) for q in cor["path"]]
    frame = geo.Frame(*geo.CONUS, 330, 92, W - PAD - 330, 198, pad=0.02)
    geo.draw_basemap(c, frame, S)
    done = geo.project(frame, path[:j["split"] + 1])
    todo = geo.project(frame, path[j["split"]:])
    if len(todo) > 1:
        c.add(S.polyline(todo, stroke=DARK, sw=4, dash="7 6"))
    if len(done) > 1:
        c.add(S.polyline(done, sw=6))
    hx, hy = frame.xy(*j["here"])
    c.add(S.circle(hx, hy, 13, fill=WHITE, stroke=BLACK, sw=5),
          S.circle(hx, hy, 5, fill=BLACK))

    # ── milepost strip, full width ────────────────────────────────────────
    x0, x1, y = PAD, W - PAD, 356
    mx = x0 + (x1 - x0) * j["route_frac"]
    c.add(S.line(x0, y, x1, y, stroke=LIGHT, sw=6),
          S.line(x0, y, mx, y, sw=6))
    for post in cor["mileposts"]:
        px = x0 + (x1 - x0) * post["mi"] / cor["total_mi"]
        passed = post["mi"] <= total
        c.add(S.circle(px, y, 9, fill=BLACK if passed else WHITE,
                       stroke=None if passed else BLACK, sw=4))
    c.add(S.circle(mx, y, 24, fill=WHITE, stroke=BLACK, sw=5),
          glyph(mx - 17, y - 18, 35))
    c.add(S.text(x0, y + 40, "SAN DIEGO", 26, "bold", fill=DARK, tracking=2),
          S.text(x1, y + 40, f"{dest.upper()} {cor['total_mi']:,.0f}", 26, "bold",
                 anchor="end", fill=DARK, tracking=2))

    return _footer_or(c, j, behind, cor)


def _footer_or(c, j, behind, cor):
    if j["lapped"]:
        return c
    return c


@card(19, "C", "cumulative running miles on the road-distance ladder from 92129")
def c19a_journey_run(b, o):
    return _journey(b, "run")


@card(19, "C", "cumulative riding miles on the road-distance ladder from 92129")
def c19b_journey_bike(b, o):
    return _journey(b, "bike")


@card(20, "C", "activity counts by sport over the trailing 365 days")
def c20_split(b, o):
    split = M.sport_split(b["acts"], b["asof"])[:5]
    total = sum(n for _, n in split) or 1
    c = _mk("split", f"Last year: {F.sport(split[0][0])} {split[0][1]} vs "
                     f"{F.sport(split[1][0])} {split[1][1]}",
            "Activity counts by sport over the last 365 days — running and mountain biking "
            "are almost exactly level.",
            "sport split", b, 20, "C",
            "activity counts by sport over the trailing 365 days")
    L.bar_rows(c, [(F.sport(name), f"{n}", n / split[0][1]) for name, n in split],
               label_w=330, value_w=100)
    return c


@card(21, "C", "sum of moving_time_min across the whole log, as 24-hour days")
def c21_hours(b, o):
    t = M.totals(b["acts"])
    days = t["hours"] / 24.0
    c = _mk("hours", f"{t['hours']:.0f} hours in motion",
            f"{t['hours']:.0f} moving hours across {t['n']} activities — "
            f"{days:.1f} full days.",
            "time in motion", b, 21, "C",
            "sum of moving_time_min across the whole log, as 24-hour days")
    # A tally, not a clock face. The clock showed hours modulo twelve, so 286
    # hours pointed at ten and read as a time of day; the quantity worth
    # showing is how many whole days of the log were spent moving.
    c.add(S.text(PAD, 176, f"{t['hours']:.0f}", 110, "bold"),
          S.text(PAD + len(f"{t['hours']:.0f}") * 110 * 0.62 + 20, 148,
                 "MOVING HOURS", 30, "bold", fill=DARK, tracking=3),
          S.text(PAD + len(f"{t['hours']:.0f}") * 110 * 0.62 + 20, 184,
                 f"{t['n']} ACTIVITIES", 26, fill=DARK, tracking=3))
    L.tally(c, int(days), partial=days - int(days))
    dt, ds = S.fit_text(f"{days:.1f} FULL DAYS · ONE MARK PER 24 HOURS", 28,
                        W - 2 * PAD, tracking=3)
    c.add(S.text(CXD, 402, dt, ds, "bold", anchor="middle", fill=DARK, tracking=3))
    return c


@card(22, "D", "most recent pr_date in segments_summary.csv")
def c22_pr(b, o):
    pr = M.latest_pr(b["segs"], b["asof"])
    if pr is None:
        return None
    c = _mk("pr", f"PR — {pr['name']} in {mmss(pr['best_s'])}",
            f"Latest segment PR: {pr['name']}, {mmss(pr['best_s'])} on effort {pr['efforts']}. "
            f"That is {pr['counts'][30]} PRs in 30 days and {pr['counts'][365]} in the last year.",
            "latest segment pr", b, 22, "D", "most recent pr_date in segments_summary.csv")
    name, size = S.fit_text(pr["name"], 44, W - 2 * PAD)
    c.add(S.text(PAD, 138, name, size, "bold"),
          S.text(PAD, 234, mmss(pr["best_s"]), 92, "bold"),
          S.text(PAD + 250, 234, f"on effort {pr['efforts']}", 30, fill=DARK),
          S.text(PAD + 250, 196, F.day(pr["date"]).upper(), 26,
                 fill=DARK, tracking=2))
    # Five-bar gates, capped so a 36x segment does not run off the card.
    x, y = PAD, 300
    for i in range(min(pr["efforts"], 40)):
        gate, within = divmod(i, 5)
        gx = x + gate * 46
        if within < 4:
            c.add(S.line(gx + within * 9, y, gx + within * 9, y + 46, sw=4))
        else:
            c.add(S.line(gx - 4, y + 40, gx + 32, y + 6, sw=4))
    c.add(S.text(PAD, 388, f"{pr['efforts']} EFFORTS", 26, "bold", tracking=2))
    return c


@card(23, "D", "count of pr_date values inside trailing windows")
def c23_pr_pace(b, o):
    pr = M.latest_pr(b["segs"], b["asof"])
    if pr is None:
        return None
    k = pr["counts"]
    c = _mk("pr-pace", f"{k[30]} PRs in 30 days, {k[365]} in a year",
            f"Segment personal records are landing at {k[30]} per month: {k[90]} in 90 days "
            f"and {k[365]} over the last year.",
            "pr pace", b, 23, "D", "count of pr_date values inside trailing windows")
    L.stat_trio(c, [(k[30], "in 30 days"), (k[90], "in 90 days"), (k[365], "in a year")])
    return c


@card(24, "D", "top segments by effort_count, with best_time_s")
def c24_leaderboard(b, o):
    rows = M.segment_leaderboard(b["segs"], 5)
    if not rows:
        return None
    top = rows[0]["n"]
    c = _mk("leaderboard", f"Most-ridden: {rows[0]['name']} ×{rows[0]['n']}",
            f"The five most-repeated segments, led by {rows[0]['name']} at {rows[0]['n']} "
            f"efforts and a best of {mmss(rows[0]['best_s'])}.",
            "home leaderboard", b, 24, "D", "top segments by effort_count, with best_time_s")
    L.bar_rows(c, [(r["name"], f"{r['n']}× · {mmss(r['best_s'])}", r["n"] / top)
                   for r in rows], label_w=330, value_w=190)
    return c


@card(25, "D", "most negative recent_trend among segments with 5+ efforts")
def c25_improving(b, o):
    t = M.segment_trends(b["segs"])
    if not t:
        return None
    s = t[0]
    c = _mk("improving", f"Most improved: {s['name']} {s['trend']:.1f}%",
            f"{s['name']} has come down {abs(s['trend']):.1f}% over {s['n']} efforts — the "
            f"biggest improvement on any segment ridden at least five times.",
            "most improved segment", b, 25, "D",
            "most negative recent_trend among segments with 5+ efforts")
    L.text_card(c, s["name"], f"Down {abs(s['trend']):.1f}% across {s['n']} efforts.",
                tag=f"{s['trend']:.1f}% · {s['n']} EFFORTS", headline_size=54)
    c.add(S.text(W - PAD, 300, f"{s['trend']:.1f}%", 84, "bold", anchor="end"))
    return c


@card(26, "D", "most positive recent_trend among segments with 5+ efforts")
def c26_declining(b, o):
    t = M.segment_trends(b["segs"])
    if not t:
        return None
    s = t[-1]
    c = _mk("declining", f"Going backwards: {s['name']} +{s['trend']:.1f}%",
            f"{s['name']} has slipped {s['trend']:.1f}% over {s['n']} efforts. Segments are "
            f"short; one bad day skews a trend.",
            "the honest one", b, 26, "D",
            "most positive recent_trend among segments with 5+ efforts")
    L.text_card(c, s["name"], "Segments are short and one bad day skews a trend. "
                              "Posting it anyway.",
                tag=f"+{s['trend']:.1f}% · {s['n']} EFFORTS", headline_size=54)
    c.add(S.text(W - PAD, 300, f"+{s['trend']:.1f}%", 84, "bold", anchor="end"))
    return c


@card(27, "D", "coefficient of variation of effort times per segment")
def c27_consistency(b, o):
    from collections import defaultdict
    times = defaultdict(list)
    names = {}
    for e in b["efforts"]:
        t = M.mf(e["elapsed_time_s"])
        if t:
            times[e["segment_id"]].append(t)
            names[e["segment_id"]] = e["segment_name"]
    scored = [(St.cv(v), names[k], v) for k, v in times.items() if len(v) >= 5]
    scored = [s for s in scored if s[0] is not None]
    if not scored:
        return None
    scored.sort()
    best, worst = scored[0], scored[-1]
    c = _mk("consistency-seg", f"Metronome: {best[1]} at {best[0] * 100:.0f}% variation",
            f"Of segments ridden five or more times, {best[1]} is the most repeatable "
            f"({best[0] * 100:.1f}% coefficient of variation) and {worst[1]} the least "
            f"({worst[0] * 100:.0f}%).",
            "segment consistency", b, 27, "D",
            "coefficient of variation of effort times per segment")
    lo, hi = min(best[2]), max(best[2])
    span = (hi - lo) or 1
    x0, x1, y = PAD + 20, W - PAD - 20, 300
    c.add(S.line(x0, y, x1, y, stroke=LIGHT, sw=3))
    for t in best[2]:
        c.add(S.circle(x0 + (x1 - x0) * (t - lo) / span, y, 12, fill=S.tone(0.7)))
    nm, ns = S.fit_text(best[1], 44, W - 2 * PAD)
    c.add(S.text(PAD, 176, nm, ns, "bold"),
          S.text(PAD, 236, f"CV {best[0] * 100:.1f}% · {len(best[2])} EFFORTS", 28,
                 "bold", fill=DARK, tracking=2),
          S.text(x0, y + 46, mmss(lo), 26, fill=DARK),
          S.text(x1, y + 46, mmss(hi), 26, anchor="end", fill=DARK))
    return c


@card(28, "D", "effort_count of the single most-repeated segment, as tallies")
def c28_repeat(b, o):
    rows = M.segment_leaderboard(b["segs"], 1)
    if not rows:
        return None
    s = rows[0]
    c = _mk("repeat", f"{s['name']} — ridden {s['n']} times",
            f"{s['name']} has been ridden {s['n']} times, more than any other segment. "
            f"Best: {mmss(s['best_s'])}.",
            "repeat offender", b, 28, "D",
            "effort_count of the single most-repeated segment, as tallies")
    nm, ns = S.fit_text(s["name"], 46, W - 2 * PAD)
    c.add(S.text(PAD, 150, nm, ns, "bold"))
    x, y = PAD, 220
    for i in range(min(s["n"], 40)):
        gate, within = divmod(i, 5)
        row, col = divmod(gate, 8)
        gx, gy = x + col * 92, y + row * 90
        if within < 4:
            c.add(S.line(gx + within * 16, gy, gx + within * 16, gy + 62, sw=5))
        else:
            c.add(S.line(gx - 8, gy + 54, gx + 56, gy + 8, sw=5))
    c.add(S.text(W - PAD, 150, f"{s['n']}×", 76, "bold", anchor="end"))
    return c


@card(29, "D", "OLS of segment pace vs grade, run and bike, and their crossover")
def c29_crossover(b, o):
    g = M.segment_pace_by_grade(b["efforts"], M.activity_by_id(b["acts"]))
    fit_r, fit_b = St.ols(*g.get("run", ([], []))), St.ols(*g.get("bike", ([], [])))
    if not fit_r or not fit_b:
        return None
    x = St.crossover(fit_r, fit_b)
    lo, hi = -12.0, 12.0
    in_range = x is not None and lo <= x <= hi
    headline = (f"Running overtakes riding at {x:.1f}% grade" if in_range
                else "Riding wins at every grade she actually rides")
    c = _mk("crossover", headline,
            (f"Fitting segment pace against grade for both sports, the lines cross at "
             f"{x:.1f}% — steeper than that and running is faster." if in_range else
             f"Fitting segment pace against grade for both sports, the lines do not cross "
             f"anywhere between {lo:.0f}% and {hi:.0f}% grade: riding stays faster throughout."),
            "running vs riding", b, 29, "D",
            "OLS of segment pace vs grade, run and bike, and their crossover")
    px0, px1, py0, py1 = PAD + 30, W - PAD - 30, 190, 350
    ys = [fit_r[0] * v + fit_r[1] for v in (lo, hi)] + \
         [fit_b[0] * v + fit_b[1] for v in (lo, hi)]
    ymin, ymax = min(ys), max(ys)
    rng = (ymax - ymin) or 1

    def pt(gr, pace):
        return (px0 + (px1 - px0) * (gr - lo) / (hi - lo),
                py1 - (py1 - py0) * (pace - ymin) / rng)

    c.add(S.line(px0, py1 + 16, px1, py1 + 16, stroke=LIGHT, sw=3))
    # Label at a quarter along and pushed clear of the line: the two fits
    # converge at the right-hand end, so labels there collide.
    for fit, dash, label, dy in ((fit_r, None, "RUNNING", 34), (fit_b, "12 8", "RIDING", -16)):
        a, bb = pt(lo, fit[0] * lo + fit[1]), pt(hi, fit[0] * hi + fit[1])
        c.add(S.line(a[0], a[1], bb[0], bb[1], sw=5, dash=dash))
        lx = a[0] + (bb[0] - a[0]) * 0.18
        ly = a[1] + (bb[1] - a[1]) * 0.18 + dy
        c.add(S.text(lx, ly, label, 26, "bold", tracking=2))
    if in_range:
        cx = px0 + (px1 - px0) * (x - lo) / (hi - lo)
        c.add(S.line(cx, py0 - 20, cx, py1 + 16, stroke=DARK, sw=3, dash="6 8"))
    c.add(S.text(px0, py1 + 52, f"{lo:.0f}% GRADE", 26, fill=DARK, tracking=2),
          S.text(px1, py1 + 52, f"+{hi:.0f}%", 26, anchor="end", fill=DARK, tracking=2),
          S.text(PAD, 156, "SLOWER ↑ · PACE BY GRADE", 28, "bold", fill=DARK, tracking=2))
    return c


# ══ E · Gear ════════════════════════════════════════════════════════════

@card(30, "E", "gear.json converted_distance against notification_distance")
def c30_shoes(b, o):
    sh = M.shoes(b["gear"], b["acts"])
    if not sh:
        return None
    over = [s for s in sh if s["over"]]
    c = _mk("shoes",
            (f"Retire the {over[0]['name']} — {over[0]['mi']:.0f} mi" if over
             else f"Shoes: {sh[0]['name']} at {sh[0]['mi']:.0f} mi"),
            (f"{over[0]['name']} is at {over[0]['mi']:.0f} miles against a "
             f"{over[0]['limit_mi']:.0f}-mile replacement threshold." if over else
             f"No shoe is past its replacement threshold; {sh[0]['name']} leads at "
             f"{sh[0]['mi']:.0f} of {sh[0]['limit_mi']:.0f} miles."),
            "shoe mileage", b, 30, "E",
            "gear.json converted_distance against notification_distance")
    y = 118
    for s in sh[:3]:
        c.add(S.glyph_shoe(PAD, y - 6, 78, fill_frac=min(s["frac"], 1.0)))
        name, size = S.fit_text(s["name"], 32, 440)
        c.add(S.text(PAD + 96, y + 26, name, size, "bold"))
        bx, bw, by, bh = PAD + 96, W - PAD - (PAD + 96), y + 42, 38
        c.add(S.rect(bx, by, bw, bh, fill=WHITE, stroke=BLACK, sw=3),
              S.rect(bx + 3, by + 3, (bw - 6) * min(s["frac"], 1.0), bh - 6,
                     fill=BLACK if s["over"] else S.tone(0.7)),
              S.text(W - PAD, y + 26, f"{s['mi']:.0f} / {s['limit_mi']:.0f} mi", 28,
                     "bold", anchor="end", fill=DARK))
        if s["over"]:
            # Reversed out of the full black bar, so the alert needs no extra
            # row height and cannot collide with the shoe below it.
            c.add(S.text(bx + 16, by + 29, "RETIRE ME", 26, "bold", fill=WHITE, tracking=3))
        y += 108
    return c


@card(31, "E", "the first shoe past its threshold; absent when none is")
def c31_retire(b, o):
    over = [s for s in M.shoes(b["gear"], b["acts"]) if s["over"]]
    if not over:
        return None
    s = over[0]
    c = _mk("retire", f"Retire the {s['name']}",
            f"{s['name']} is {s['mi'] - s['limit_mi']:.0f} miles past its "
            f"{s['limit_mi']:.0f}-mile replacement threshold, over {s['runs']} activities.",
            "buy new shoes", b, 31, "E",
            "the first shoe past its threshold; absent when none is")
    c.add(S.glyph_shoe(CXD - 90, 108, 180, fill_frac=1.0))
    nm, ns = S.fit_text(s["name"], 40, W - 2 * PAD)
    c.add(S.text(CXD, 344, nm, ns, "bold", anchor="middle"))
    tag = f"{s['mi'] - s['limit_mi']:.0f} MI PAST {s['limit_mi']:.0f}"
    w = len(tag) * 28 * 0.62 + 28
    c.add(S.rect(CXD - w / 2, 366, w, 42, fill=BLACK),
          S.text(CXD, 396, tag, 28, "bold", anchor="middle", fill=WHITE, tracking=2))
    return c


@card(32, "E", "gear.json converted_distance for non-retired bikes")
def c32_bike(b, o):
    bk = M.bikes(b["gear"])
    if not bk:
        return None
    g = bk[0]
    mi = g.get("converted_distance") or 0.0
    c = _mk("bike-odo", f"{g['name']} — {mi:,.0f} mi",
            f"{g.get('brand_name', '')} {g.get('model_name', '')}".strip()
            + f", {mi:,.0f} miles on the odometer.",
            "the bike", b, 32, "E", "gear.json converted_distance for non-retired bikes")
    c.add(S.glyph_bike(CXD - 100, 108, 200))
    L.hero_number(c, f"{mi:,.0f}", unit="mi", sub=g["name"], size=96)
    return c


@card(33, "E", "gear.json entries with retired=true, and their descriptions")
def c33_graveyard(b, o):
    dead = M.retired_gear(b["gear"])
    if not dead:
        return None
    g = dead[0]
    desc = (g.get("description") or "").strip()
    c = _mk("graveyard", f"Retired: {g['name']} at "
                         f"{g.get('converted_distance') or 0:.0f} mi",
            desc or f"{g['name']} retired at {g.get('converted_distance') or 0:.0f} miles.",
            "gear graveyard", b, 33, "E",
            "gear.json entries with retired=true, and their descriptions")
    L.text_card(c, g["name"], desc or None,
                tag=f"RETIRED AT {g.get('converted_distance') or 0:.0f} MI",
                headline_size=52)
    return c


# ══ F · Places ══════════════════════════════════════════════════════════

@card(34, "F", "start points clustered at a 6 mi radius; box table for states")
def c34_passport(b, o):
    pts = P.start_points(b["acts"])
    regions = P.count_regions(pts)
    states, unc = P.count_states(pts)
    c = _mk("passport", f"{regions} regions, {len(states)} states and provinces",
            f"Activities cluster into {regions} distinct regions across {len(states)} states "
            f"and provinces: {', '.join(states)}.",
            "passport", b, 34, "F",
            "start points clustered at a 6 mi radius; box table for states")
    L.stat_trio(c, [(len(pts), "located"), (regions, "regions"), (len(states), "states")])
    c.add(S.text(CXD, 356, " · ".join(states), 30, "bold", anchor="middle", tracking=3))
    return c


@card(35, "F", "miles inside the San Diego and Boston bounding boxes")
def c35_homes(b, o):
    h = P.home_stats(b["acts"])
    c = _mk("homes", f"San Diego {h['sd']['mi']:.0f} mi · Boston {h['bos']['mi']:.0f} mi",
            f"Two home cities: {h['sd']['mi']:.0f} miles inside the San Diego box over "
            f"{h['sd']['n']} activities, {h['bos']['mi']:.0f} miles over {h['bos']['n']} "
            f"around Boston.",
            "two homes", b, 35, "F",
            "miles inside the San Diego and Boston bounding boxes")
    L.two_up(c, ("San Diego", f"{h['sd']['mi']:.0f}", f"{h['sd']['n']} activities"),
             ("Boston", f"{h['bos']['mi']:.0f}", f"{h['bos']['n']} activities"),
             delta="miles, by home")
    return c


@card(36, "F", "one GPS stream chosen by date ordinal, aspect-fitted")
def c36_route(b, o):
    r = M.route_of_day(b["acts"], o)
    if r is None:
        return None
    a = r["act"]
    c = _mk("route", f"Route of the day — {a['name']}",
            f"{a['_mi']:.1f} mi, {a['_ft']:.0f} ft of climbing, "
            f"{F.day(a['_date'])}.",
            "route of the day", b, 36, "F",
            "one GPS stream chosen by date ordinal, aspect-fitted")
    L.route_card(c, r["path"], r["w"], r["h"], [
        (a["name"], 38, "bold", BLACK), (f"{a['_mi']:.1f} mi", 54, "bold", BLACK),
        (f"{a['_ft']:.0f} ft climbed", 28, "normal", DARK),
        (F.sport(a["sport_type"]), 28, "normal", DARK),
    ])
    return c


@card(37, "F", "every GPS track, simplified to 64 points, tiled")
def c37_mosaic(b, o):
    tracks = P.all_tracks()
    if not tracks:
        return None
    cols, rows = 8, 4
    picks = [tracks[(o + i * 7) % len(tracks)] for i in range(cols * rows)]
    c = _mk("mosaic", f"{len(tracks)} routes, 32 of them",
            f"Every GPS track in the log reduced to 64 points each; 32 shown, rotating daily.",
            "route mosaic", b, 37, "F",
            "every GPS track, simplified to 64 points, tiled")
    cw = (W - 2 * PAD) / cols
    ch = (L.BOT_RULE - L.BODY_TOP) / rows
    side = min(cw, ch) - 8
    for i, (_name, t) in enumerate(picks):
        r, col = divmod(i, cols)
        k = side / max(t["w"], t["h"], 1e-9)
        ox = PAD + col * cw + (cw - t["w"] * k) / 2
        oy = L.BODY_TOP + r * ch + (ch - t["h"] * k) / 2
        c.add(S.polyline([(ox + x * k, oy + y * k) for x, y in t["path"]], sw=3))
    return c


@card(39, "F", "hand-curated superlatives mirroring the dashboard's record book")
def c39_compass(b, o):
    rows = P.PEAKS[:4]
    c = _mk("compass", f"{rows[0][1]} — {rows[0][2]}",
            "; ".join(f"{k.lower()} {v}" for k, v, _ in rows) + ".",
            "the extremes", b, 39, "F",
            "hand-curated superlatives mirroring the dashboard's record book")
    y = L.BODY_TOP + 24
    for kicker, value, place in rows:
        c.add(S.text(PAD, y, kicker, 26, "bold", fill=DARK, tracking=2),
              S.text(W - PAD, y, value, 40, "bold", anchor="end"))
        pt, ps = S.fit_text(place, 28, W - 2 * PAD - 200)
        c.add(S.text(PAD, y + 34, pt, ps, fill=DARK))
        c.add(S.line(PAD, y + 50, W - PAD, y + 50, stroke=LIGHT, sw=3))
        y += 78
    return c


# ══ G · Weather & environment ═══════════════════════════════════════════

@card(40, "G", "min and max average_temp_c across the log, in Fahrenheit")
def c40_temp(b, o):
    t = M.temps(b["acts"])
    if not t:
        return None
    c = _mk("temp", f"Trained from {t['min_f']:.0f}°F to {t['max_f']:.0f}°F",
            f"The coldest logged activity averaged {t['min_f']:.0f}°F "
            f"(\"{t['min_act']['name']}\") and the warmest {t['max_f']:.0f}°F "
            f"(\"{t['max_act']['name']}\") — an {t['max_f'] - t['min_f']:.0f}-degree range.",
            "temperature range", b, 40, "G",
            "min and max average_temp_c across the log, in Fahrenheit")
    x, y, w, h = PAD + 40, 210, W - 2 * PAD - 80, 62
    c.add(S.rect(x, y, w, h, fill=WHITE, stroke=BLACK, sw=4))
    for i in range(7):
        c.add(S.rect(x + 4 + (w - 8) * i / 7, y + 4, (w - 8) / 7, h - 8, fill=S.tone(i / 6)))
    c.add(S.text(x, y - 22, f"{t['min_f']:.0f}°F", 34, "bold"),
          S.text(x + w, y - 22, f"{t['max_f']:.0f}°F", 34, "bold", anchor="end"))
    lo, ls = S.fit_text(t["min_act"]["name"], 28, w / 2 - 12)
    hi, hs = S.fit_text(t["max_act"]["name"], 28, w / 2 - 12)
    c.add(S.text(x, y + h + 40, lo, ls, fill=DARK),
          S.text(x + w, y + h + 40, hi, hs, anchor="end", fill=DARK))
    c.add(S.text(CXD, y + h + 92, f"{t['max_f'] - t['min_f']:.0f}° RANGE", 32, "bold",
                 anchor="middle", tracking=4))
    return c


@card(41, "G", "pace and heart rate against temperature band, runs only")
def c41_heat_verdict(b, o):
    runs = [r for r in b["acts"] if M.is_run(r) and M.mf(r["average_temp_c"]) is not None
            and M.mf(r["average_speed_kmh"]) and M.mf(r["average_heartrate"])]
    if len(runs) < 20:
        return None
    bands = [("COOL", -99, 8.9), ("MILD", 8.9, 16.7), ("WARM", 16.7, 23.9), ("HOT", 23.9, 99)]
    rows = []
    for name, lo, hi in bands:
        sel = [r for r in runs if lo <= M.mf(r["average_temp_c"]) < hi]
        if not sel:
            continue
        pace = sum(60 / (M.mf(r["average_speed_kmh"]) * 0.621371) for r in sel) / len(sel)
        hr = sum(M.mf(r["average_heartrate"]) for r in sel) / len(sel)
        rows.append((name, pace, hr, len(sel)))
    if len(rows) < 2:
        return None
    cool, hot = rows[0], rows[-1]
    dp = (hot[1] - cool[1]) * 60
    c = _mk("heat-verdict",
            f"Heat costs {abs(dp):.0f}s/mi, not heartbeats",
            f"From {cool[0].lower()} to {hot[0].lower()} runs, pace moves "
            f"{abs(dp):.0f} seconds per mile while average heart rate shifts only "
            f"{abs(hot[2] - cool[2]):.0f} bpm.",
            "the heat verdict", b, 41, "G",
            "pace and heart rate against temperature band, runs only")
    L.bar_rows(c, [(f"{name}  {mmss(p * 60)}/mi", f"{hr:.0f} bpm · n={n}",
                    (p - min(r[1] for r in rows)) /
                    ((max(r[1] for r in rows) - min(r[1] for r in rows)) or 1) * 0.9 + 0.1)
                   for name, p, hr, n in rows], label_w=330, value_w=210)
    return c


@card(42, "G", "max uv_index across the log; the value is time-of-day resolved")
def c42_uv(b, o):
    u = M.uv_max(b["acts"])
    if not u:
        return None
    c = _mk("uv", f"Peak UV {u['uv']:.1f} — {u['act']['name']}",
            f"The highest UV index recorded on any activity is {u['uv']:.1f}, on "
            f"\"{u['act']['name']}\". UV is resolved to the hour, not a daily maximum.",
            "sun exposure", b, 42, "G",
            "max uv_index across the log; the value is time-of-day resolved")
    cx, cy, r = CXD, 240, 56
    c.add(S.circle(cx, cy, r, fill=S.tone(0.55), stroke=BLACK, sw=4))
    for i in range(int(round(u["uv"]))):
        th = math.radians(i * 360 / max(1, int(round(u["uv"]))) - 90)
        c.add(S.line(cx + (r + 16) * math.cos(th), cy + (r + 16) * math.sin(th),
                     cx + (r + 52) * math.cos(th), cy + (r + 52) * math.sin(th),
                     sw=7, cap="round"))
    c.add(S.text(cx, cy + 18, f"{u['uv']:.1f}", 52, "bold", anchor="middle", fill=WHITE))
    nm, ns = S.fit_text(u["act"]["name"], 34, W - 2 * PAD)
    c.add(S.text(CXD, 380, nm, ns, "bold", anchor="middle"))
    return c


@card(43, "G", "start-hour histogram; count of pre-8am starts")
def c43_dark(b, o):
    hours = M.hour_histogram(b["acts"])
    early = sum(n for h, n in hours if h < 8)
    first = min(r["_dt"].time() for r in b["acts"])
    peak = max(n for _, n in hours) or 1
    c = _mk("dark", f"{early} starts before 8am, earliest {F.hm(first)}",
            f"{early} activities began before 8am; the earliest start on record is "
            f"{F.hm(first)}.",
            "when she goes out", b, 43, "G",
            "start-hour histogram; count of pre-8am starts")
    bw = (W - 2 * PAD) / 24
    base = 356
    for h, n in hours:
        x = PAD + h * bw
        ht = 150 * n / peak
        c.add(S.rect(x + 2, base - ht, bw - 4, ht, fill=BLACK if h < 8 else S.tone(0.45)))
    c.add(S.line(PAD, base, W - PAD, base, sw=3))
    for h in (0, 6, 12, 18):
        c.add(S.text(PAD + h * bw + 2, base + 34, f"{h:02d}", 26, fill=DARK))
    c.add(S.text(PAD, 172, f"{early}", 84, "bold"),
          S.text(PAD + 130, 172, "BEFORE 8AM", 30, "bold", fill=DARK, tracking=3))
    return c


# ══ H · Records ═════════════════════════════════════════════════════════

@card(44, "H", "one pinned record-book row per rotation day")
def c44_record_book(b, o):
    kicker, value, place = P.PEAKS[o % len(P.PEAKS)]
    c = _mk("record-book", f"{kicker.title()} — {value}",
            f"{kicker.title()}: {value}, {place}.",
            "the record book", b, 44, "H", "one pinned record-book row per rotation day")
    # The kicker rides in text_card's tag slot. Drawn as its own line above,
    # it lands inside a 110 px headline's cap height and prints straight
    # through it - which is what it did until the overlap check caught it.
    L.text_card(c, value, place, tag=kicker, headline_size=110)
    return c


@card(45, "H", "max distance by sport group, and max single-activity elevation")
def c45_longest(b, o):
    lr = M.longest(b["acts"], M.is_run)
    lb = M.longest(b["acts"], M.is_bike)
    le = M.longest(b["acts"], lambda r: True, key="_ft")
    rows = [(f"Longest run · {lr['name']}", f"{lr['_mi']:.1f} mi", 1.0),
            (f"Longest ride · {lb['name']}", f"{lb['_mi']:.1f} mi",
             lb["_mi"] / max(lr["_mi"], lb["_mi"])),
            (f"Biggest climb · {le['name']}", f"{le['_ft']:,.0f} ft", 0.8)]
    c = _mk("longest", f"Longest run {lr['_mi']:.1f} mi, longest ride {lb['_mi']:.1f} mi",
            f"Records: {lr['_mi']:.1f} miles running (\"{lr['name']}\"), {lb['_mi']:.1f} "
            f"riding (\"{lb['name']}\"), and {le['_ft']:,.0f} feet climbed in one day.",
            "longest ever", b, 45, "H",
            "max distance by sport group, and max single-activity elevation")
    L.bar_rows(c, rows, label_w=420, value_w=170)
    return c


@card(46, "H", "max kudos_count in activities.csv")
def c46_kudos(b, o):
    a = M.top_kudos(b["acts"])
    if not a:
        return None
    c = _mk("kudos", f"Most kudos: “{a['name']}” ({a['kudos_count']})",
            f"\"{a['name']}\" drew {a['kudos_count']} kudos, more than any other activity.",
            "peak kudos", b, 46, "H", "max kudos_count in activities.csv")
    L.text_card(c, a["name"], a.get("description") or None,
                tag=f"{a['kudos_count']} KUDOS · {a['_mi']:.1f} MI · "
                    f"{F.sport(a['sport_type']).upper()}")
    return c


# ══ I · Memory ══════════════════════════════════════════════════════════

@card(47, "I", "same month and day in prior years; degrades when empty")
def c47_this_day(b, o):
    hits = M.on_this_day(b["acts"], b["asof"])
    if hits:
        a = hits[0]
        c = _mk("this-day", f"On this day {a['_dt'].year} — {a['name']}",
                f"{a['_mi']:.1f} mi of {F.sport_activity(a['sport_type'])} on this date "
                f"in {a['_dt'].year}.",
                "on this day", b, 47, "I",
                "same month and day in prior years; degrades when empty")
        L.text_card(c, a["name"], a.get("description") or None,
                    tag=f"{a['_dt'].year} · {a['_mi']:.1f} MI · "
                        f"{F.sport(a['sport_type']).upper()}")
        return c
    # The log only spans 2024-2026, so most calendar days have no prior hit.
    # Say so rather than showing an empty card.
    c = _mk("this-day", "Nothing on this day in a previous year",
            "The log only spans two years, so most calendar dates have no earlier "
            "activity to recall.",
            "on this day", b, 47, "I",
            "same month and day in prior years; degrades when empty")
    L.hero_number(c, "—", sub="nothing on this date, any year", size=120)
    return c


@card(48, "I", "a +/- 3 day window centred 365 days back")
def c48_year_ago(b, o):
    hits = M.year_ago_week(b["acts"], b["asof"])
    if not hits:
        return None
    mi = sum(r["_mi"] for r in hits)
    a = max(hits, key=lambda r: r["_mi"])
    c = _mk("year-ago", f"A year ago this week: {mi:.1f} mi over {len(hits)} activities",
            f"In the same week last year there were {len(hits)} activities totalling "
            f"{mi:.1f} miles, the biggest being \"{a['name']}\" at {a['_mi']:.1f} mi.",
            "a year ago this week", b, 48, "I",
            "a +/- 3 day window centred 365 days back")
    L.stat_trio(c, [(len(hits), "activities"), (f"{mi:.0f}", "miles"),
                    (f"{sum(r['_ft'] for r in hits):,.0f}", "feet")])
    nm, ns = S.fit_text(f"biggest: {a['name']}", 30, W - 2 * PAD)
    c.add(S.text(CXD, 356, nm, ns, "bold", anchor="middle", fill=DARK))
    return c


@card(49, "I", "the oldest row in activities.csv")
def c49_first(b, o):
    a = b["acts"][0]
    c = _mk("first", f"It started with “{a['name']}”",
            f"The first activity in the log: {a['_mi']:.1f} mi of "
            f"{F.sport_activity(a['sport_type'])} on "
            f"{F.day(a['_date'], '%d %B %Y')}.",
            "where it began", b, 49, "I", "the oldest row in activities.csv")
    L.text_card(c, a["name"], a.get("description") or None,
                tag=f"{F.day(a['_date'], '%d %B %Y').upper()} · {a['_mi']:.1f} MI")
    days = (b["asof"] - a["_date"]).days
    c.add(S.text(W - PAD, 158, f"{days}", 76, "bold", anchor="end"),
          S.text(W - PAD, 196, "DAYS AGO", 26, "bold", anchor="end", fill=DARK, tracking=3))
    return c


# ══ J · Voice & whimsy ══════════════════════════════════════════════════

@card(50, "J", "athlete.json bio, verbatim")
def c50_byline(b, o):
    bio = (b["athlete"].get("bio") or "").strip()
    if not bio:
        return None
    t = M.totals(b["acts"])
    c = _mk("byline", bio, f"{t['n']} activities, {t['mi']:,.0f} miles, "
                           f"{t['ft']:,.0f} feet. That is the whole pitch.",
            "the masthead", b, 50, "J", "athlete.json bio, verbatim")
    bt, bs = S.fit_text(bio, 76, W - 2 * PAD)
    c.add(S.text(CXD, 240, bt, bs, "bold", anchor="middle"))
    c.add(S.text(CXD, 316, f"{t['n']} ACTIVITIES · {t['mi']:,.0f} MI · {t['ft']:,.0f} FT",
                 28, "bold", anchor="middle", fill=DARK, tracking=3))
    return c


@card(51, "J", "an activity with a description, picked by date ordinal")
def c51_logbook(b, o):
    a = M.title_of_day(b["acts"], o)
    if a is None:
        return None
    desc = (a.get("description") or "").strip()
    c = _mk("title", f"“{a['name']}”",
            desc or f"{a['_mi']:.1f} mi of {F.sport_activity(a['sport_type'])} on "
                    f"{F.day(a['_date'])}.",
            "from the logbook", b, 51, "J",
            "an activity with a description, picked by date ordinal")
    L.text_card(c, a["name"], desc,
                tag=f"{a['_mi']:.1f} MI · {F.sport(a['sport_type']).upper()}")
    return c


@card(53, "J", "activity names composed entirely of non-ASCII symbols")
def c53_emoji(b, o):
    rows = M.emoji_titles(b["acts"])
    if not rows:
        return None
    c = _mk("emoji", f"{len(rows)} activities named only in emoji",
            f"{len(rows)} activity titles contain no letters at all: "
            f"{' '.join(r['name'] for r in rows[:6])}.",
            "emoji census", b, 53, "J",
            "activity names composed entirely of non-ASCII symbols")
    L.hero_number(c, len(rows), sub="titles with no letters at all")
    names = "   ".join(r["name"] for r in rows[:6])
    nt, ns = S.fit_text(names, 54, W - 2 * PAD, ratio=1.1)
    # Clears hero_number's caption, which sits at its y + 66.
    c.add(S.text(CXD, 412, nt, ns, anchor="middle"))
    return c


# ══ K · Meta ════════════════════════════════════════════════════════════

@card(54, "K", "row counts and on-disk size of the fetched data")
def c54_dataset(b, o):
    d = M.dataset_stats(b["acts"])
    c = _mk("dataset", f"{d['acts']} activities, {d['streams']} GPS streams, "
                       f"{d['mb']:.0f} MB",
            f"The log behind these cards: {d['acts']} activities, {d['streams']} per-second "
            f"GPS stream files totalling {d['mb']:.0f} MB, plus segment efforts and laps.",
            "the dataset itself", b, 54, "K",
            "row counts and on-disk size of the fetched data")
    L.stat_trio(c, [(d["acts"], "activities"), (d["streams"], "gps streams"),
                    (f"{d['mb']:.0f}", "megabytes")])
    return c


@card(55, "K", "device_name counts across the log")
def c55_devices(b, o):
    dv = M.devices(b["acts"])
    top = dv[0][1]
    c = _mk("devices", f"{dv[0][0]} recorded {dv[0][1]} of {len(b['acts'])}",
            "Every activity in the log, by the device that recorded it.",
            "recorded by", b, 55, "K", "device_name counts across the log")
    L.bar_rows(c, [(name, str(n), n / top) for name, n in dv[:4]],
               label_w=400, value_w=100)
    return c


@card(56, "K", "laps/{id}.csv for the newest activity with more than one lap")
def c56_laps(b, o):
    a = M.last_with_laps(b["acts"])
    if not a:
        return None
    laps = M.laps_for(a)
    rows = []
    for lap in laps[:5]:
        km = M.mf(lap["distance_km"]) or 0
        secs = M.mf(lap["moving_time_s"]) or 0
        mi = km * 0.621371
        pace = secs / 60 / mi if mi > 0.05 else None
        rows.append((lap["name"], f"{mi:.2f} mi · {mmss(secs)}", secs))
    peak = max(r[2] for r in rows) or 1
    c = _mk("laps", f"Lap splits — {a['name']}",
            f"{len(laps)} laps on \"{a['name']}\", "
            f"{F.day(a['_date'])}.",
            "lap splits", b, 56, "K",
            "laps/{id}.csv for the newest activity with more than one lap")
    L.bar_rows(c, [(n, v, s / peak) for n, v, s in rows], label_w=200, value_w=250,
               note=f"{len(laps)} laps · bar length is elapsed time")
    return c


# ══ merged-in cards (57-62) ═════════════════════════════════════════════
# Ported or newly built when this branch merged the other e-paper plan. They
# sit at the end of the registry rather than beside their family's other
# cards, so the catalogue numbers stay stable and the proof sheet still groups
# them by family.

@card(3, "A", "newest activity: its GPS stream over its own numbers")
def c57_latest(b, o):
    """Idea 3, combined. `last` (the words) and `last-route` (the shape) both
    stay in the catalogue; this is the one that rotates, because on a fridge
    magnet the map and the numbers want to arrive together."""
    a = b["acts"][-1]
    r = M.route_for(a)
    if not r:
        return None
    mi, ft = a["_mi"], a["_ft"]
    moving = M.mf(a["moving_time_min"]) or 0.0
    hr = M.mf(a["average_heartrate"])
    temp_c = M.mf(a["average_temp_c"])
    suffer = M.mf(a["suffer_score"])
    bike = M.is_bike(a)
    speed_kmh = M.mf(a["average_speed_kmh"]) or 0.0
    if bike:
        pace = f"{speed_kmh * KM_TO_MI:.1f}", "mph"
    else:
        pace = (mmss(60 / (speed_kmh * KM_TO_MI) * 60) if speed_kmh else "—"), "/mi"

    c = _mk("latest", f"Last out — {a['name']}",
            f"{mi:.1f} mi of {F.sport_activity(a['sport_type'])} in "
            f"{int(moving // 60)}h {int(moving % 60):02d}m "
            f"with {ft:,.0f} ft of climbing, on {F.day(a['_date'])}.",
            "latest activity", b, 3, "A",
            "newest activity: its GPS stream over its own numbers")
    L.route_stats(c, r["path"], r["w"], r["h"], [
        (f"{mi:.1f}", "miles"),
        (f"{int(moving // 60)}:{int(moving % 60):02d}", "moving"),
        (pace[0], pace[1]),
        (f"{ft:,.0f}", "feet up"),
        (f"{hr:.0f}" if hr else "—", "avg bpm"),
        (f"{temp_c * 9 / 5 + 32:.0f}°" if temp_c is not None else "—", "degrees f"),
        (f"{suffer:.0f}" if suffer else "—", "suffer"),
        (a["kudos_count"] or "0", "kudos"),
    ])
    g = _sport_glyph(a["sport_type"])
    if g:
        c.add(g(W - PAD - 76, L.TOP_RULE + 8, 76))
    return c


@card(57, "D", "segment with the most efforts in the last 30 days")
def c58_segment_month(b, o):
    s = M.segment_of_month(b["efforts"], b["segs"], b["asof"])
    if not s or len(s["times"]) < 2:
        return None
    arrow = ("down" if s["trend"] is not None and s["trend"] < -1 else
             "up" if s["trend"] is not None and s["trend"] > 1 else "flat")
    c = _mk("segment-month", f"Segment of the month — {s['name']}",
            f"{s['n30']} efforts on \"{s['name']}\" in the last 30 days: best {mmss(s['best_s'])}, "
            f"latest {mmss(s['latest_s'])}, {s['trend_word']}.",
            "segment of the month", b, 57, "D",
            "segment with the most efforts in the last 30 days")
    nt, ns = S.fit_text(s["name"], 30, W - 2 * PAD - 240)
    c.add(S.text(PAD, 116, nt, ns, "bold"),
          S.text(W - PAD, 116, f"{s['n30']}× IN 30 DAYS", 26, "bold",
                 anchor="end", fill=DARK, tracking=2))
    L.stat_trio(c, [(mmss(s["best_s"]), "best"), (mmss(s["latest_s"]), "latest"),
                    (f"{s['trend']:+.0f}%" if s["trend"] is not None else "—",
                     # One word: the full phrase reaches the column divider.
                     s["trend_word"].split()[0])],
                baseline=202, size=64)
    if s["trend"] is not None:
        # Geometry, not the "▲" character, whose width fit_text cannot
        # estimate and which may not exist in the panel's font at all. It sits
        # on the label row rather than beside the numeral: at 64 px "+10%" is
        # 165 px wide and leaves no room next to it.
        c.add(S.triangle(W - PAD - 22, 240, 26, arrow))
    # Plotted as negated seconds: effort time falls as you get faster, and on
    # a card a rising line has to mean improvement.
    L.spark(c, [-t for t in s["times"][-24:]],
            labels=(s["first"][:4], "now"), top=308, bottom=368)
    c.add(S.text(PAD, 296, f"{s['mi']:.2f} MI AT {s['grade']:+.1f}%  ·  "
                           f"LAST 24 EFFORTS, UP = FASTER", 26, fill=DARK,
                 tracking=1))
    hr = f"avg {s['avg_hr']:.0f} bpm · " if s["avg_hr"] else ""
    return c


@card(58, "J", "best-scoring activity names, a window of five per ISO week")
def c59_hall_of_fame(b, o):
    ranked = M.named_activities(b["acts"])
    if len(ranked) < 5:
        return None
    year, week, _ = b["asof"].isocalendar()
    seed = (year * 53 + week) % 7
    picks = ranked[seed:seed + 5]
    default = len(b["acts"]) - len(ranked)

    c = _mk("hall-of-fame", f"Hall of fame — \"{picks[0]['name']}\"",
            f"Five of the {len(ranked)} activities that got a real name, this week's window "
            f"of the rotation. {default} kept Strava's default.",
            "name hall of fame", b, 58, "J",
            "best-scoring activity names, a window of five per ISO week")
    pitch = (L.BOT_RULE - L.BODY_TOP) / 5
    for i, r in enumerate(picks):
        y = L.BODY_TOP + i * pitch
        g = _sport_glyph(r["sport_type"])
        if g:
            c.add(g(PAD, y + 2, 44))
        # The names are the whole card, so they wrap to two lines rather than
        # ellipsizing; the date and distance drop to a second right-hand line
        # to give them the width.
        lines = S.wrap_text(r["name"], 28, W - PAD - 190 - (PAD + 58), max_lines=2)
        for j, line in enumerate(lines):
            c.add(S.text(PAD + 58, y + 22 + j * 28, line, 28, "bold"))
        mi = r["_mi"]
        stat = f"{mi:.1f} mi" if mi > 0.05 else f"{M.mf(r['moving_time_min']) or 0:.0f} min"
        c.add(S.text(W - PAD, y + 22, F.day(r["_date"]), 26, anchor="end", fill=DARK),
              S.text(W - PAD, y + 50, stat, 26, anchor="end", fill=DARK))
        if i < len(picks) - 1:
            c.add(S.line(PAD, y + pitch - 3, W - PAD, y + pitch - 3,
                         stroke=LIGHT, sw=3))
    return c


@card(59, "G", "sum of uv_index x moving hours over the ISO week of the last data day")
def c60_uv_week(b, o):
    u = M.uv_week(b["acts"], b["asof"])
    if not u["n"]:
        return None
    total = u["total"]
    # 20 UV-hours in a week is the point where the tube reads full: a fortnight
    # of ordinary San Diego mornings, not a medical threshold.
    # Floor at a visible tone so a near-zero week still reads as a sun rather
    # than an empty outline.
    frac = max(0.15, min(1.0, total / 20.0))
    c = _mk("uv-week", f"{total:.0f} UV-hours this week",
            f"UV dose for ISO week {u['week']}: {total:.1f} UV-hours across {u['n']} "
            f"activities, peaking at UV {u['peak_uv']:.0f}.",
            "uv dose this week", b, 59, "G",
            "sum of uv_index x moving hours over the ISO week of the last data day")
    peak_day = max(u["days"]) or 1.0
    L.cell_grid(c, [d / peak_day for d in u["days"]], per_row=7, cell=56, gap=14,
                labels=("mon", "sun"), top=270)
    # The label follows the numeral rather than sitting at a fixed x: "4" and
    # "128" are very different widths and there is no text measurement here.
    num = f"{total:.0f}"
    lx = PAD + len(num) * 120 * 0.62 + 20
    c.add(S.text(PAD, 202, num, 120, "bold"),
          S.text(lx, 176, "UV-HOURS", 30, "bold", fill=DARK, tracking=3),
          S.text(lx, 212, f"WEEK {u['week']}", 26, fill=DARK, tracking=3))
    # Tone carries the dose: a light sun is a quiet week, a black one a
    # scorcher. 20 UV-hours reads as full - a fortnight of ordinary San Diego
    # mornings, not a medical threshold.
    c.add(S.glyph_sun(W - PAD - 140, 104, 140, level=frac))
    peak = u["peak_act"]
    return c


@card(52, "J", "whole-word animal names in activity titles and descriptions")
def c61_wildlife(b, o):
    z = M.animal_sightings(b["acts"])
    if not z["counts"]:
        return None
    top = z["counts"][:10]
    peak = top[0][1]
    latest = max(z["last_seen"].values(), key=lambda r: r["_dt"])
    latest_species = M.animal_hits(latest)

    c = _mk("wildlife", f"{z['total']} wildlife sightings, {len(z['counts'])} species",
            f"Animals named in activity titles and descriptions: {z['total']} mentions across "
            f"{z['n']} outings, led by {top[0][0].lower()} at {top[0][1]}.",
            "wildlife scoreboard", b, 52, "J",
            "whole-word animal names in activity titles and descriptions")
    L.bar_grid(c, [(label, str(n), n / peak) for label, n in top], cols=2,
               glyphs=[S.ANIMAL_GLYPHS.get(label) for label, _ in top])
    return c


@card(60, "I", "the same ISO week in the 2003-07 paper log, against this one")
def c62_week_2004(b, o):
    year, week, _ = b["asof"].isocalendar()
    then_year = next((y for y in (2004, 2003, 2005, 2006, 2007)
                      if M.runlog_week(b["runlog"], (y, week))), None)
    if then_year is None:
        return None
    then = M.runlog_week(b["runlog"], (then_year, week))
    then_mi = sum(r["_mi"] for r in then)
    then_paces = [r["_pace"] for r in then if r["_pace"]]
    then_pace = sum(then_paces) / len(then_paces) if then_paces else None

    now = [r for r in b["acts"]
           if r["_date"].isocalendar()[:2] == (year, week) and M.is_run(r)]
    now_mi = sum(r["_mi"] for r in now)
    now_paces = [60 / (M.mf(r["average_speed_kmh"]) * KM_TO_MI)
                 for r in now if M.mf(r["average_speed_kmh"])]
    now_pace = sum(now_paces) / len(now_paces) if now_paces else None

    then_lines = []
    for r in [t for t in then if t["_mi"] > 0][:4]:
        line = f"{r['day_of_week'][:3]}  {r['workout_type'] or 'run':<12} {r['_mi']:.1f} mi"
        if r["_race"]:
            line += f"  · RACE: {r['race_name']}"
        then_lines.append(line)

    if now:
        now_lines = [f"{r['_date'].strftime('%a')}  {r['name']}  {r['_mi']:.1f} mi"
                     for r in sorted(now, key=lambda r: r["_dt"])[:4]]
    else:
        lr = M.longest([r for r in b["acts"] if M.is_run(r)], lambda r: True, "_dt")
        now_lines = ["no runs this ISO week"]
        if lr:
            now_lines.append(f"last run: {lr['name']}")
            now_lines.append(f"{lr['_mi']:.1f} mi on {F.day(lr['_date'])}")

    delta = now_mi - then_mi
    c = _mk("week-2004", f"Week {week}: {then_mi:.0f} mi in {then_year}, "
                         f"{now_mi:.0f} mi now",
            f"The same ISO week, {year - then_year} years apart: {then_mi:.1f} run miles in "
            f"{then_year} against {now_mi:.1f} now.",
            f"this week in {then_year}", b, 60, "I",
            "the same ISO week in the 2003-07 paper log, against this one")
    L.then_now(c,
               (str(then_year), f"{then_mi:.0f} mi",
                f"avg {mmss(then_pace * 60)}/mi" if then_pace else f"{len(then)} days logged",
                then_lines),
               (str(year), f"{now_mi:.0f} mi",
                f"avg {mmss(now_pace * 60)}/mi" if now_pace else "no run pace this week",
                now_lines))
    return c


@card(61, "I", "a race from the 2003-07 log falling near TODAY's calendar date")
def c63_anniversary(b, o):
    """The one card keyed to the wall clock rather than to the last day with
    data. Everything else on the panel says "as of the last activity"; an
    anniversary that arrived while the fetch cron was asleep is still an
    anniversary, so this one uses the build date."""
    today = date.fromordinal(o)
    a = M.race_anniversary(b["runlog"], today)
    if not a:
        return None
    r = a["race"]
    head = " · ".join(x for x in (a["distance"].upper(), a["time"]) if x) or a["name"]
    c = _mk("anniversary", f"{a['when'].capitalize()} — {a['name']}",
            f"{a['name']}, {F.day(r['_date'])}"
            + (f": {a['distance']} in {a['time']}." if a["time"] else "."),
            "race anniversary", b, 61, "I",
            "a race from the 2003-07 log falling near TODAY's calendar date")
    L.text_card(c, head, a["comments"] or None,
                tag=f"{a['name'].upper()} · {F.day(r['_date']).upper()}",
                headline_size=62)
    # text_card's headline baseline is fixed at 158, so the "when" line has to
    # clear a 62 px cap height above it as well as the top rule below.
    wt, ws = S.fit_text(a["when"].upper(), 30, W - 2 * PAD, tracking=3)
    c.add(S.text(PAD, 104, wt, ws, "bold", fill=DARK, tracking=3))
    return c


@card(62, "J", "5-7-5 assembled from the newest activity's own numbers")
def c64_haiku(b, o):
    a = b["acts"][-1]
    sightings = {str(r["id"]): M.animal_hits(r) for r in b["acts"] if M.animal_hits(r)}
    h = M.haiku(a, sightings)
    if not h:
        return None
    c = _mk("haiku", " / ".join(h["lines"]),
            f"Today's five-seven-five, built from \"{a['name']}\" — "
            f"{a['_mi']:.1f} mi on {F.day(a['_date'])}.",
            "activity haiku", b, 62, "J",
            "5-7-5 assembled from the newest activity's own numbers")
    y = 168
    for i, line in enumerate(h["lines"]):
        # Only the first line yields room to the sport glyph. The middle line
        # is the seven-syllable one and so always the longest; giving it the
        # same reserve ellipsizes it, and a truncated haiku is not a haiku.
        avail = W - 2 * PAD - (100 if i == 0 else 0)
        lt, ls = S.fit_text(line, 48, avail)
        c.add(S.text(PAD, y, lt, ls, "bold" if i != 1 else "normal",
                     fill=BLACK if i != 1 else DARK))
        y += 76
    g = _sport_glyph(a["sport_type"])
    if g:
        c.add(g(W - PAD - 84, 128, 84))
    nt, ns = S.fit_text(a["name"], 26, 420)
    return c


# ══ assembly ════════════════════════════════════════════════════════════

# The seventeen cards the device actually cycles, hand-picked rather than
# curated by family. Every other card still builds, still ships in feed.xml and
# still appears on the proof sheet - promoting one is a one-line edit here.
# Seventeen ids means the rotation repeats every seventeen days.
#
# card_of_the_day falls back to the whole catalogue if an id here goes missing,
# so a typo degrades rather than crashes.
ROTATION = [
    "strip",          # 9  - last 30 days as two rows of cells
    "sparkline",      # 17 - 13 months of volume
    "everest",        # 18 - all-time elevation as stacked Everests
    "journey-run",    # 19 - east on I-8 -> I-10 -> I-40 toward Boston
    "journey-bike",   # 19 - southeast on I-8 -> I-10 toward Austin
    "split",          # 20 - last 365 days by sport
    "hours",          # 21 - hours in motion, on a clock face
    "mosaic",         # 37 - 32 route thumbnails
    "latest",         # 3  - newest activity: route over its own numbers
    "segment-month",  # 57 - most-repeated segment of the last 30 days
    "hall-of-fame",   # 58 - five well-named activities, rotating weekly
    "uv-week",        # 59 - this week's UV dose
    "wildlife",       # 52 - wildlife scoreboard
    "week-2004",      # 60 - the same ISO week in the paper log
    "anniversary",    # 61 - a race from the paper log near today's date
    "haiku",          # 62 - 5-7-5 from the newest activity
]

def build_cards(bundle, today=None):
    """Every card, in catalogue order. Cards that lack data drop out silently."""
    today = today or date.today()
    o = today.toordinal()
    out = []
    for idea, family, recipe, fn in _REGISTRY:
        c = fn(bundle, o)
        if c is None:
            continue
        c.idea, c.family, c.recipe = idea, family, recipe
        out.append(c)
    return out


def card_of_the_day(cards, now=None):
    """Deterministic rotation over the curated list, stepping once an hour.

    Keyed on hours since the epoch in **UTC**, not on a local date. The card is
    chosen at build time - the panel runs no JavaScript and cannot choose - so
    the rotation can only advance as often as the site is rebuilt. deploy.yml
    rebuilds hourly to match; at a daily rebuild this simply steps once a day.
    UTC because the build runs on a UTC runner, so a local key would step at a
    different moment depending on where the build happened.

    Falls back to the whole catalogue if a rotation id ever goes missing, so a
    typo in ROTATION degrades rather than crashes.
    """
    now = now or datetime.now(timezone.utc)
    by_id = {c.id: c for c in cards}
    pool = [by_id[i] for i in ROTATION if i in by_id] or cards
    return pool[int(now.timestamp() // 3600) % len(pool)]
