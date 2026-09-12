"""The Sticky rotation, re-drawn for a 296x128 four-color strip.

One function per surviving rotation id, same ids as ``feed.cards`` so the two
panels show the same idea in the same hour. The data layer is shared
unchanged (``metrics``, ``places``, ``journey``, ``geo``); only the drawing is
new, because the drawing is what a panel a tenth the size and with no gray
changes.

Every builder takes ``(bundle, ordinal, palette, **variant)``. The palette is
a table of color *roles* (``config.Palette``); a card never names a hex.
``variant`` keywords are for the proof sheet's mockups - an alternative
layout or an alternative reading of the same data - and are ignored by the
device build.

Audit outcome, for the record (the prose version is in
``Project Docs/Plans/strava-data/epaper-xiao.md``): 15 of the 16 rotation
cards adapt; ``mosaic`` is dropped because its whole point is density, and
survives here only as a 2x6 mockup for the owner to reinstate or not.
"""

from datetime import date, datetime, timezone

from nerd_common.format import mmss

from .. import fmt as F
from .. import geo, journey
from .. import metrics as M
from .. import places as P
from ..cards import ROTATION as STICKY_ROTATION
from . import layouts as L
from . import svg as S
from ..config import KM_TO_MI
from .config import DEFAULT, HEAT, MIN_TEXT, PAD, SPORT, W, WHITE

_REGISTRY = []


def card(idea, family, recipe, rotation=True):
    """Register a builder. ``rotation=False`` keeps it off the device and
    off ``build_cards`` - it exists for the sheet's mockups only."""
    def deco(fn):
        _REGISTRY.append((idea, family, recipe, rotation, fn))
        return fn
    return deco


def _mk(cid, title, summary, kicker, b, pal):
    return L.base(cid, title, summary, kicker, b["asof"], pal)


def _sport_glyph(sport):
    if sport in ("Run", "TrailRun", "Walk", "Hike"):
        return S.glyph_runner
    if sport in ("MountainBikeRide", "Ride", "EBikeRide"):
        return S.glyph_bike
    return None


def _sport_color(sport, pal):
    return pal.bike if M.is_bike({"sport_type": sport}) else pal.run


def _month(label):
    y, m = label.split("-")
    return date(int(y), int(m), 1).strftime("%b %y").upper()


# ══ B · Streaks ══════════════════════════════════════════════════════════════

@card(9, "B", "one cell per day, filled if any activity that day")
def strip(b, o, pal=DEFAULT, variant=None):
    """Two rows of fifteen. Under ``variant="miles"`` the active cells take
    the ramp by that day's mileage instead of plain ink - the heat model's
    reading of the same thirty days."""
    days = M.last_30_strip(b["acts"], b["asof"])
    n = sum(days)
    c = _mk("strip", f"{n} active days in the last 30",
            f"{n} of the last 30 days had an activity.", "last 30 days", b, pal)
    c.add(S.text(PAD, 58, f"{n} / 30", 34, "bold", fill=pal.ink),
          S.text(W - PAD, 58, "ACTIVE DAYS", MIN_TEXT, "bold", anchor="end",
                 fill=pal.ink, tracking=1))
    if variant == "miles":
        by_day = {}
        for r in b["acts"]:
            by_day[r["_date"]] = by_day.get(r["_date"], 0.0) + r["_mi"]
        from datetime import timedelta
        dates = [b["asof"] - timedelta(days=29 - i) for i in range(30)]
        miles = [by_day.get(d, 0.0) for d in dates]
        peak = max(miles) or 1.0
        colors = [None if not m else pal.ramp[1 + min(2, int(m / peak * 3))] for m in miles]
    else:
        colors = [pal.ink if d else pal.wash for d in days]
        colors[-1] = pal.accent if days[-1] else None
    x0, total, _ = L.cells(c, colors, per_row=15, cell=13, gap=4, top=66, pal=pal)
    c.add(S.text(x0, 116, "30 DAYS AGO", MIN_TEXT, fill=pal.ink, tracking=1),
          S.text(x0 + total, 116, "TODAY", MIN_TEXT, anchor="end", fill=pal.ink, tracking=1))
    return c


# ══ C · Volume ════════════════════════════════════════════════════════════════

@card(17, "C", "miles per calendar month, last 13 months")
def sparkline(b, o, pal=DEFAULT):
    months = M.monthly_miles(b["acts"], 13)
    vals = [v for _, v in months]
    c = _mk("sparkline", f"13 months of volume — {vals[-1]:.0f} mi latest",
            f"Monthly mileage over the last 13 months, from {min(vals):.0f} to "
            f"{max(vals):.0f}, finishing at {vals[-1]:.0f}.", "monthly volume", b, pal)
    c.add(S.text(PAD, 56, f"{vals[-1]:.0f} MI", 34, "bold", fill=pal.ink))
    L.spark(c, vals, top=64, bottom=98, pal=pal)
    c.add(S.text(PAD, 118, _month(months[0][0]), MIN_TEXT, fill=pal.ink, tracking=1),
          S.text(L.CX, 118, f"{min(vals):.0f}–{max(vals):.0f} MI", MIN_TEXT,
                 anchor="middle", fill=pal.ink, tracking=1),
          S.text(W - PAD, 118, _month(months[-1][0]), MIN_TEXT, anchor="end",
                 fill=pal.ink, tracking=1))
    return c


@card(18, "C", "sum of total_elevation_gain_m, converted, over 29,032 ft")
def everest(b, o, pal=DEFAULT):
    e = M.everest(b["acts"])
    whole, frac = int(e["multiple"]), e["multiple"] - int(e["multiple"])
    c = _mk("everest", f"{e['ft']:,.0f} ft climbed — {e['multiple']:.1f} × Everest",
            f"All-time elevation gain is {e['ft']:,.0f} feet, or {e['multiple']:.1f} times "
            f"the 29,032-foot height of Everest.", "total elevation", b, pal)
    c.add(S.text(PAD, 50, f"{e['ft']:,.0f} FT", 26, "bold", fill=pal.ink),
          S.text(W - PAD, 50, f"{e['multiple']:.1f}× EVEREST", MIN_TEXT, "bold",
                 anchor="end", fill=pal.ink, tracking=1))
    shown = min(whole, 5)
    gap = 6
    size = min(52, int((W - 2 * PAD - shown * gap) / (shown + 1)))
    total = (shown + 1) * size + shown * gap
    x, y = L.CX - total / 2, 58
    for _ in range(shown):
        c.add(S.glyph_mountain(x, y, size, color=pal.ink, filled=True))
        x += size + gap
    c.add(S.glyph_mountain(x, y, size, color=pal.ink, fill_frac=frac, fill_color=pal.wash))
    return c


def _journey(b, group, pal, variant=None):
    """Numbers plus the milepost strip by default; ``variant="map"`` swaps
    the strip for the CONUS orientation map the Sticky draws."""
    if group == "run":
        total = M.totals(b["acts"], M.is_run)["mi"]
        verb, color = "run", pal.run
    else:
        total = M.totals(b["acts"], M.is_bike)["mi"]
        verb, color = "ridden", pal.bike
    j = journey.position(total, group)
    cor = j["corridor"]
    label, dest = cor["label"], cor["destination"]
    ahead = j["ahead"]["name"]
    behind = j["behind"]["name"] if j["behind"] else "home"
    short = ahead.split(",")[0]
    if j["lapped"]:
        title = f"{label.title()} · {total:,.0f} mi — {j['laps']:.1f}× the road to {dest}"
        summary = (f"{total:,.0f} miles {verb} is {j['laps']:.1f} times the "
                   f"{cor['total_mi']:,.0f}-mile interstate route from 92129 to {dest}.")
        second = f"{j['laps']:.1f}× THE ROAD TO {dest.upper()}"
    else:
        title = f"{label.title()} · {total:,.0f} mi — {j['remaining_mi']:,.0f} mi to {short}"
        summary = (f"Measured along {cor['road']} out of 92129, {total:,.0f} miles {verb} puts "
                   f"you past {behind} with {j['remaining_mi']:,.0f} miles to {ahead} — "
                   f"{j['route_frac'] * 100:.0f}% of the {cor['total_mi']:,.0f}-mile road to "
                   f"{dest}.")
        second = f"{j['remaining_mi']:,.0f} MI TO {short.upper()}"
    c = _mk(f"journey-{group}", title, summary, f"{label} · to {dest}", b, pal)

    if variant == "map":
        c.add(S.text(PAD, 54, f"{total:,.0f}", 30, "bold", fill=color),
              S.text(PAD, 70, f"MILES {verb.upper()}", MIN_TEXT, "bold", fill=pal.ink,
                     tracking=1))
        first, _, rest = second.partition(" TO ") if " TO " in second else \
            second.partition(" THE ")
        c.add(S.text(PAD, 96, first, 20, "bold", fill=pal.ink))
        rt, rs = S.fit_text(("TO " if " TO " in second else "THE ") + rest, MIN_TEXT, 130,
                            ratio=0.62, tracking=1)
        c.add(S.text(PAD, 114, rt, rs, fill=pal.ink, tracking=1))
        path = [tuple(q) for q in cor["path"]]
        mx, mw = 146, W - PAD - 146
        frame = geo.Frame(*geo.CONUS, mx, L.BODY_TOP, mw, L.BODY_H, pad=0.02)
        # Clipped to its box: draw_basemap allows 40 px of slack past the
        # frame, which on the Sticky is a margin and here is a third of the map.
        c.add(f'<clipPath id="jmap"><rect x="{mx}" y="{L.BODY_TOP}" width="{mw}" '
              f'height="{L.BODY_H}"/></clipPath><g clip-path="url(#jmap)">')
        # Coast only: at 144 px wide the state lines are noise, not orientation.
        geo.draw_basemap(c, frame, _InkOnly(pal), layers=("coast",))
        done = geo.project(frame, path[:j["split"] + 1])
        todo = geo.project(frame, path[j["split"]:])
        if len(todo) > 1:
            c.add(S.polyline(todo, stroke=pal.ink, sw=2, dash="3 3"))
        if len(done) > 1:
            c.add(S.polyline(done, stroke=color, sw=3))
        hx, hy = frame.xy(*j["here"])
        c.add(S.circle(hx, hy, 5, fill=pal.accent, stroke=pal.ink, sw=2), "</g>")
        return c

    end = L.hero(c, f"{total:,.0f}", size=36, y=56, pal=pal, fill=color)
    c.add(S.text(end + 6, 56, f"MI {verb.upper()}", MIN_TEXT, "bold", fill=pal.ink, tracking=1))
    st, ss = S.fit_text(second, 16, W - 2 * PAD, ratio=0.62, tracking=1)
    c.add(S.text(PAD, 80, st, ss, "bold", fill=pal.ink, tracking=1))
    x0, x1, y = PAD + 4, W - PAD - 4, 100
    mx = x0 + (x1 - x0) * j["route_frac"]
    c.add(S.line(x0, y, x1, y, stroke=pal.wash, sw=4),
          S.line(x0, y, mx, y, stroke=color, sw=4))
    for post in cor["mileposts"]:
        px = x0 + (x1 - x0) * post["mi"] / cor["total_mi"]
        passed = post["mi"] <= total
        c.add(S.circle(px, y, 3.5, fill=pal.ink if passed else WHITE,
                       stroke=pal.ink, sw=2))
    c.add(S.circle(mx, y, 7, fill=pal.accent, stroke=pal.ink, sw=2))
    c.add(S.text(x0, 120, "SAN DIEGO", MIN_TEXT, fill=pal.ink, tracking=1),
          S.text(x1, 120, f"{dest.upper()} {cor['total_mi']:,.0f}", MIN_TEXT,
                 anchor="end", fill=pal.ink, tracking=1))
    return c


class _InkOnly:
    """The ``S``-shaped object ``geo.draw_basemap`` draws with, forcing every
    basemap stroke to ink at the floor: it asks for the Sticky's grays."""

    def __init__(self, pal):
        self.pal = pal

    def polyline(self, pts, stroke=None, sw=2):
        return S.polyline(pts, stroke=self.pal.ink, sw=2)


@card(19, "C", "cumulative running miles on the road-distance ladder from 92129")
def journey_run(b, o, pal=DEFAULT, variant=None):
    return _journey(b, "run", pal, variant)


@card(19, "C", "cumulative riding miles on the road-distance ladder from 92129")
def journey_bike(b, o, pal=DEFAULT, variant=None):
    return _journey(b, "bike", pal, variant)


@card(20, "C", "activity counts by sport over the trailing 365 days")
def split(b, o, pal=DEFAULT):
    rows = M.sport_split(b["acts"], b["asof"])[:4]
    c = _mk("split", f"Last year: {F.sport(rows[0][0])} {rows[0][1]} vs "
                     f"{F.sport(rows[1][0])} {rows[1][1]}",
            "Activity counts by sport over the last 365 days.", "sport split", b, pal)
    L.bars(c, [(F.sport(name), f"{n}", n / rows[0][1]) for name, n in rows],
           label_w=112, value_w=36, pal=pal,
           fills=[_sport_color(name, pal) for name, _ in rows])
    return c


@card(21, "C", "sum of moving_time_min across the whole log, as 24-hour days")
def hours(b, o, pal=DEFAULT):
    t = M.totals(b["acts"])
    days = t["hours"] / 24.0
    c = _mk("hours", f"{t['hours']:.0f} hours in motion",
            f"{t['hours']:.0f} moving hours across {t['n']} activities — "
            f"{days:.1f} full days.", "time in motion", b, pal)
    end = L.hero(c, f"{t['hours']:.0f}", size=48, y=70, pal=pal)
    c.add(S.text(end + 8, 56, "MOVING HOURS", MIN_TEXT, "bold", fill=pal.ink, tracking=1),
          S.text(end + 8, 74, f"= {days:.1f} FULL DAYS", MIN_TEXT, fill=pal.ink, tracking=1))
    L.tally(c, int(days), partial=days - int(days), x=PAD + 2, top=88, mark_h=28, pal=pal)
    return c


# ══ A · Right now ════════════════════════════════════════════════════════════

@card(3, "A", "newest activity: its GPS stream over its own numbers")
def latest(b, o, pal=DEFAULT, demo=False):
    """``demo`` is for the sheet only: when the newest activity has no GPS
    stream yet the card is absent, and a mockup pair of two empty proofs
    decides nothing, so the sheet falls back to the newest activity that has
    one and says so in its label."""
    a = b["acts"][-1]
    r = M.route_for(a)
    if not r and demo:
        for a in reversed(b["acts"]):
            r = M.route_for(a)
            if r:
                break
    if not r:
        return None
    mi, ft = a["_mi"], a["_ft"]
    moving = M.mf(a["moving_time_min"]) or 0.0
    hr = M.mf(a["average_heartrate"])
    temp_c = M.mf(a["average_temp_c"])
    speed_kmh = M.mf(a["average_speed_kmh"]) or 0.0
    if M.is_bike(a):
        pace = f"{speed_kmh * KM_TO_MI:.1f}", "mph"
    else:
        pace = (mmss(60 / (speed_kmh * KM_TO_MI) * 60) if speed_kmh else "—"), "/mi"
    # The name rides in the masthead: on the Sticky the title carried it, and
    # here there is no other line to spare.
    c = _mk("latest", f"Last out — {a['name']}",
            f"{mi:.1f} mi of {F.sport_activity(a['sport_type'])} in "
            f"{int(moving // 60)}h {int(moving % 60):02d}m with {ft:,.0f} ft of climbing, "
            f"on {F.day(a['_date'])}.", a["name"], b, pal)
    L.route(c, r["path"], r["w"], r["h"], (PAD, L.BODY_TOP, 92, L.BODY_H), pal=pal,
            stroke=_sport_color(a["sport_type"], pal))
    stats = [(f"{mi:.1f}", "miles"),
             (f"{int(moving // 60)}:{int(moving % 60):02d}", "time"),
             (pace[0], pace[1]),
             (f"{ft:,.0f}", "ft up"),
             (f"{hr:.0f}" if hr else "—", "bpm"),
             (f"{temp_c * 9 / 5 + 32:.0f}°" if temp_c is not None else "—", "deg f")]
    L.stat_row(c, stats[:3], y=54, size=22, x0=106, pal=pal)
    L.stat_row(c, stats[3:], y=96, size=22, x0=106, pal=pal)
    return c


# ══ D · Segments ═════════════════════════════════════════════════════════════

@card(57, "D", "segment with the most efforts in the last 30 days")
def segment_month(b, o, pal=DEFAULT):
    s = M.segment_of_month(b["efforts"], b["segs"], b["asof"])
    if not s or len(s["times"]) < 2:
        return None
    trend = s["trend"]
    arrow = "down" if trend is not None and trend < -1 else \
            "up" if trend is not None and trend > 1 else "flat"
    c = _mk("segment-month", f"Segment of the month — {s['name']}",
            f"{s['n30']} efforts on \"{s['name']}\" in the last 30 days: best "
            f"{mmss(s['best_s'])}, latest {mmss(s['latest_s'])}, {s['trend_word']}.",
            f"segment · {s['n30']}× in 30 days" if s["n30"] < 10 else
            f"{s['n30']}× in 30 days", b, pal)
    nt, ns = S.fit_text(s["name"], 18, W - 2 * PAD)
    c.add(S.text(PAD, 45, nt, ns, "bold", fill=pal.ink))
    word = s["trend_word"].split()[0]
    slower = trend is not None and trend > 1
    L.stat_row(c, [(mmss(s["best_s"]), "best"), (mmss(s["latest_s"]), "last"),
                   (f"{trend:+.0f}%" if trend is not None else "—", word)],
               y=80, size=22, x0=PAD, x1=200, pal=pal,
               fills=[None, None, pal.accent if slower else None])
    if trend is not None:
        # Geometry, not a glyph, for the Sticky's reasons. Beside the label.
        cx = PAD + (200 - PAD) * (2 + 0.5) / 3
        c.add(S.triangle(min(cx + len(word) * 4.9 + 10, 206), 93, 10, arrow,
                         fill=pal.accent if slower else pal.ink))
    # Negated seconds so a rising line means faster, as on the Sticky.
    L.spark(c, [-t for t in s["times"][-24:]], x0=216, x1=W - PAD - 4, top=56, bottom=98,
            pal=pal)
    c.add(S.text(W - PAD - 4, 118, "LAST 24 · UP = FASTER", MIN_TEXT, anchor="end",
                 fill=pal.ink, tracking=1))
    return c


# ══ J · Voice ════════════════════════════════════════════════════════════════

@card(58, "J", "best-scoring activity names, a window of three per ISO week")
def hall_of_fame(b, o, pal=DEFAULT, variant=None):
    """The first three of the Sticky's five, same weekly window. Distance
    instead of date on the right: the name needs the width, and a distance
    is six characters where a date is eleven. ``variant="one"`` is the
    mockup that gives the whole card to a single name."""
    ranked = M.named_activities(b["acts"])
    if len(ranked) < 5:
        return None
    year, week, _ = b["asof"].isocalendar()
    seed = (year * 53 + week) % 7
    picks = ranked[seed:seed + 5]
    c = _mk("hall-of-fame", f"Hall of fame — \"{picks[0]['name']}\"",
            f"Three of the {len(ranked)} activities that got a real name, this week's "
            f"window of the rotation.", "name hall of fame", b, pal)

    def stat(r):
        mi = r["_mi"]
        return f"{mi:.1f} mi" if mi > 0.05 else f"{M.mf(r['moving_time_min']) or 0:.0f} min"

    if variant == "one":
        r = picks[0]
        g = _sport_glyph(r["sport_type"])
        if g:
            c.add(g(PAD, 32, 44, _sport_color(r["sport_type"], pal)))
        lines = S.wrap_text(r["name"], 18, W - PAD - 58, max_lines=3)
        for i, line in enumerate(lines):
            c.add(S.text(58, 48 + i * 21, line, 18, "bold", fill=pal.ink))
        c.add(S.text(58, 112, f"{F.day(r['_date']).upper()} · {stat(r).upper()}", MIN_TEXT,
                     fill=pal.ink, tracking=1))
        return c

    for i, r in enumerate(picks[:3]):
        y = 28 + i * 32
        g = _sport_glyph(r["sport_type"])
        if g:
            c.add(g(PAD, y, 30, _sport_color(r["sport_type"], pal)))
        # Two lines of 14 rather than one of 16: the names are the card, and
        # a joke cut off at "Somerville Road Runners…" is not a joke.
        for k, line in enumerate(S.wrap_text(r["name"], MIN_TEXT, W - PAD - 44 - 52)):
            c.add(S.text(PAD + 38, y + 13 + k * 15, line, MIN_TEXT, "bold", fill=pal.ink))
        c.add(S.text(W - PAD, y + 13, stat(r), MIN_TEXT, anchor="end", fill=pal.ink))
    return c


# ══ G · Weather ══════════════════════════════════════════════════════════════

@card(59, "G", "sum of uv_index x moving hours over the ISO week of the last data day")
def uv_week(b, o, pal=DEFAULT, demo=False):
    u = M.uv_week(b["acts"], b["asof"])
    if not u["n"] and demo:
        # Sheet only: the most recent ISO week that carried any UV data.
        from datetime import timedelta
        probe = b["asof"]
        while not u["n"] and probe > b["acts"][0]["_date"]:
            probe -= timedelta(days=7)
            u = M.uv_week(b["acts"], probe)
    if not u["n"]:
        return None
    total = u["total"]
    frac = min(1.0, total / 20.0)
    c = _mk("uv-week", f"{total:.0f} UV-hours this week",
            f"UV dose for ISO week {u['week']}: {total:.1f} UV-hours across {u['n']} "
            f"activities, peaking at UV {u['peak_uv']:.0f}.", "uv dose this week", b, pal)
    end = L.hero(c, f"{total:.0f}", size=48, y=70, pal=pal)
    c.add(S.text(end + 8, 56, "UV-HOURS", MIN_TEXT, "bold", fill=pal.ink, tracking=1),
          S.text(end + 8, 74, f"WEEK {u['week']}", MIN_TEXT, fill=pal.ink, tracking=1))
    # The disc carries the dose in the only way four colors can: a yellow sun
    # for an ordinary week, the accent past half of a twenty-UV-hour scorcher.
    c.add(S.glyph_sun(W - PAD - 46, L.BODY_TOP - 2, 46, color=pal.ink,
                      disc=pal.accent if frac >= 0.5 else pal.wash))
    peak = max(u["days"]) or 1.0
    colors = [None if d <= 0 else pal.ramp[1 + min(2, int(d / peak * 3))] for d in u["days"]]
    x0, total_w, _ = L.cells(c, colors, per_row=7, cell=18, gap=4, x0=PAD, top=96, pal=pal)
    c.add(S.text(x0 + total_w + 10, 110, "MON – SUN", MIN_TEXT, fill=pal.ink, tracking=1))
    return c


@card(52, "J", "whole-word animal names in activity titles and descriptions")
def wildlife(b, o, pal=DEFAULT):
    z = M.animal_sightings(b["acts"])
    if not z["counts"]:
        return None
    top = z["counts"][:4]
    latest = max(z["last_seen"].values(), key=lambda r: r["_dt"])
    recent = M.animal_hits(latest)
    c = _mk("wildlife", f"{z['total']} wildlife sightings, {len(z['counts'])} species",
            f"Animals named in activity titles and descriptions: {z['total']} mentions "
            f"across {z['n']} outings, led by {top[0][0].lower()} at {top[0][1]}.",
            f"{z['total']} wildlife sightings", b, pal)
    # The most recently seen species takes the accent: the one to look at.
    L.glyph_row(c, [(S.ANIMAL_GLYPHS.get(label), n, label,
                     pal.accent if label in recent else pal.ink) for label, n in top],
                pal=pal)
    return c


# ══ I · Memory ═══════════════════════════════════════════════════════════════

@card(60, "I", "the same ISO week in the 2003-07 paper log, against this one")
def week_2004(b, o, pal=DEFAULT):
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
    c = _mk("week-2004", f"Week {week}: {then_mi:.0f} mi in {then_year}, {now_mi:.0f} mi now",
            f"The same ISO week, {year - then_year} years apart: {then_mi:.1f} run miles in "
            f"{then_year} against {now_mi:.1f} now.", f"week {week} · then and now", b, pal)
    L.then_now(c,
               (then_year, f"{then_mi:.0f} MI",
                f"avg {mmss(then_pace * 60)}/mi" if then_pace else f"{len(then)} days logged"),
               (year, f"{now_mi:.0f} MI",
                f"avg {mmss(now_pace * 60)}/mi" if now_pace else "no runs yet"),
               pal=pal)
    return c


@card(61, "I", "a race from the 2003-07 log falling near TODAY's calendar date")
def anniversary(b, o, pal=DEFAULT):
    """Keyed to the build date like the Sticky's - an anniversary that
    arrived while the fetch cron was asleep is still an anniversary."""
    today = date.fromordinal(o)
    a = M.race_anniversary(b["runlog"], today)
    if not a:
        return None
    r = a["race"]
    head = " · ".join(x for x in (a["distance"].upper(), a["time"]) if x) or a["name"]
    c = _mk("anniversary", f"{a['when'].capitalize()} — {a['name']}",
            f"{a['name']}, {F.day(r['_date'])}"
            + (f": {a['distance']} in {a['time']}." if a["time"] else "."),
            "race anniversary", b, pal)
    when = a["when"].upper()
    c.add(S.text(PAD, 42, S.fit_text(when, MIN_TEXT, W - 2 * PAD, ratio=0.68, tracking=1)[0],
                 MIN_TEXT, "bold", tracking=1,
                 fill=pal.accent if "TODAY" in when else pal.ink))
    L.lines(c, [(74, head, 26, "bold", pal.ink), (98, a["name"], 16, "bold", pal.ink),
                (116, F.day(r["_date"], "%d %B %Y").upper(), MIN_TEXT, "normal", pal.ink)],
            pal=pal)
    return c


@card(62, "J", "5-7-5 assembled from the newest activity's own numbers")
def haiku(b, o, pal=DEFAULT):
    a = b["acts"][-1]
    sightings = {str(r["id"]): M.animal_hits(r) for r in b["acts"] if M.animal_hits(r)}
    h = M.haiku(a, sightings)
    if not h:
        return None
    c = _mk("haiku", " / ".join(h["lines"]),
            f"Today's five-seven-five, built from \"{a['name']}\" — "
            f"{a['_mi']:.1f} mi on {F.day(a['_date'])}.", "activity haiku", b, pal)
    # Full width, no glyph: the seven-syllable middle line needs every pixel,
    # and a truncated haiku is not a haiku. Checked on the sheet.
    L.lines(c, [(52 + i * 30, line, 18, "normal" if i == 1 else "bold", pal.ink)
                for i, line in enumerate(h["lines"])], pal=pal)
    return c


# ══ mockup only ══════════════════════════════════════════════════════════════

@card(37, "F", "every GPS track, simplified to 64 points, twelve tiled", rotation=False)
def mosaic(b, o, pal=DEFAULT):
    """Dropped from the rotation: at 296x128 the Sticky's 32 thumbnails would
    be 25 px squiggles. Twelve at 42 px is the most this panel can carry, and
    whether that is still a mosaic is the owner's call - it is on the sheet."""
    tracks = P.all_tracks()
    if not tracks:
        return None
    cols, rows = 6, 2
    picks = [tracks[(o + i * 7) % len(tracks)] for i in range(cols * rows)]
    c = _mk("mosaic", f"{len(tracks)} routes, 12 of them",
            "Every GPS track in the log reduced to 64 points each; 12 shown, rotating daily.",
            f"{len(tracks)} routes · 12 today", b, pal)
    cw = (W - 2 * PAD) / cols
    ch = L.BODY_H / rows
    side = min(cw, ch) - 6
    for i, (_name, t) in enumerate(picks):
        r, col = divmod(i, cols)
        k = side / max(t["w"], t["h"], 1e-9)
        ox = PAD + col * cw + (cw - t["w"] * k) / 2
        oy = L.BODY_TOP + r * ch + (ch - t["h"] * k) / 2
        c.add(S.polyline([(ox + x * k, oy + y * k) for x, y in t["path"]],
                         stroke=pal.ink, sw=2))
    return c


# ══ assembly ═════════════════════════════════════════════════════════════════

# The Sticky's hand-picked rotation minus what the audit dropped, in the
# Sticky's order. Both panels key the hour the same way, so they show the
# same idea at the same time except in the hours the Sticky shows the mosaic.
DROPPED = ("mosaic",)
ROTATION = [cid for cid in STICKY_ROTATION if cid not in DROPPED]


def build_cards(bundle, today=None, pal=DEFAULT):
    """Every rotation card, in registry order. Cards that lack data drop out."""
    today = today or date.today()
    o = today.toordinal()
    out = []
    for idea, family, recipe, rotation, fn in _REGISTRY:
        if not rotation:
            continue
        c = fn(bundle, o, pal)
        if c is None:
            continue
        c.idea, c.family, c.recipe = idea, family, recipe
        out.append(c)
    return out


def card_of_the_hour(cards, now=None):
    """Same clock as ``feed.cards.card_of_the_day``: hours since the epoch in
    UTC, modulo the rotation, chosen at build time."""
    now = now or datetime.now(timezone.utc)
    by_id = {c.id: c for c in cards}
    pool = [by_id[i] for i in ROTATION if i in by_id] or cards
    return pool[int(now.timestamp() // 3600) % len(pool)]


def build_mockups(bundle, today=None):
    """The alternatives the proof sheet puts in front of the owner.

    Returns ``(group, pairs)`` where each pair is two ``(label, note, card)``
    tuples drawn side by side: the shipping version on the left, the
    alternative on the right. Layout questions first, then the color models.
    """
    today = today or date.today()
    o = today.toordinal()

    meta = {fn: (idea, family, recipe) for idea, family, recipe, _rot, fn in _REGISTRY}

    def mk(fn, pal=DEFAULT, **kw):
        c = fn(bundle, o, pal, **kw)
        if c is not None:
            c.idea, c.family, c.recipe = meta[fn]
        return c

    layout = [
        (("journey-run · strip (ships)", "Numbers over the milepost strip - the precise half of the Sticky card.",
          mk(journey_run)),
         ("journey-run · map", "The CONUS coast at 144 px wide with the route on it. Orientation, at the cost of a very busy 2 px coastline.",
          mk(journey_run, variant="map"))),
        (("journey-bike · strip (ships)", "", mk(journey_bike)),
         ("journey-bike · map", "", mk(journey_bike, variant="map"))),
        (("mosaic · dropped", "Not built for the device. The Sticky's 32 thumbnails would be 25 px here.",
          None),
         ("mosaic · 2×6 at 42 px", "Twelve routes, rotating daily. Reinstate, or is this no longer a mosaic?",
          mk(mosaic))),
        (("hall-of-fame · 3 names (ships)", "The first three of the Sticky's weekly five, single line each.",
          mk(hall_of_fame)),
         ("hall-of-fame · one name", "The whole card to one name, wrapped. Reads as a quote card - closer to the logbook card than to a hall of fame.",
          mk(hall_of_fame, variant="one"))),
    ]
    color = [
        (("strip · A semantic (ships)", "Active = ink, rest = yellow wash, today = red.",
          mk(strip)),
         ("strip · B heat", "No reserved accent. Active cells take the ramp by that day's miles: yellow, red, black.",
          mk(strip, HEAT, variant="miles"))),
        (("uv-week · A semantic (ships)", "The sun turns red past half of a twenty-UV-hour week. (Demo: the latest week with UV data when this week has none.)",
          mk(uv_week, demo=True)),
         ("uv-week · B heat", "Same cells; the sun can only go black, so the disc reads as ink rather than as alarm.",
          mk(uv_week, HEAT, demo=True))),
        (("split · A semantic (ships)", "Every bar is ink; the sport is the label.",
          mk(split)),
         ("split · C sport", "Bike rows red, run rows black - the dashboard's teal / amber re-tabled.",
          mk(split, SPORT))),
        (("journey-bike · A semantic (ships)", "Red is 'you are here' and nothing else.",
          mk(journey_bike)),
         ("journey-bike · C sport", "The ridden road and the total go red for the bike card; the here-dot now shares its color.",
          mk(journey_bike, SPORT))),
        (("latest · A semantic (ships)", "Route in ink, start dot red. (Demo: the newest activity with a GPS stream.)",
          mk(latest, demo=True)),
         ("latest · C sport", "Route colored by sport family.", mk(latest, SPORT, demo=True))),
    ]
    return [("Layout alternatives", layout), ("Color models", color)]
