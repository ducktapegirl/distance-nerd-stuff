"""The "Year Clock" -- a radial year-clock of running-only daily mileage,
modeled on the Strava dashboard's art_year.py but without the GPS bloom: no
tracks, no sport families. Lives on the Art tab.

Its Workout Type / Miles Intensity mode toggle uses the same TYPE_COLORS
palette as the Overview heatmap (for dashboard-wide visual consistency) but
its own `.yc-toggle` buttons and its own legend -- clicking one view's toggle
does not affect the other, and each carries its own legend rather than
sharing the heatmap's.

Markup only: the CSS (`.yc-*` rules) and JS (year picker, click-to-highlight,
hover readout, mode toggle) live in template.py's CSS/JS constants, matching
the heatmap's split (SVG built here, styling/behavior centralized there)
rather than art_year.py's self-contained inline <style>/<script> style.
"""

import json
import math
from datetime import date

from dashboard.config import MONTH_ABBR, TYPE_COLORS, TYPE_LABELS
from dashboard.data import map_type, maybe_float

# Workout types that are cross-training, not running -- excluded even on the
# handful of days where they carry a nonzero miles value.
CROSS_TRAINING_TYPES = {
    "bike", "elliptical", "pool", "swim", "aquajog", "aqua jog", "aqua-jog",
    "swim/aqua jog",
}

S = 900              # viewBox, square -- same proportions as the Strava art clock
C = S / 2
R0, R1 = 168, 402    # inner ring, outer reach of the longest spoke


def _daily_running_miles(rows):
    """{date: {"miles": float, "runs": int, "type": str}} for running-only
    entries. "miles" is summed per day (not maxed like heatmap_html -- a
    two-a-day should add up here); "type" is the design-type (easy/long/
    tempo/workout/race) of that day's single biggest entry, the same
    tie-break heatmap_html uses, so the two views agree on a day's color."""
    by_date = {}
    best_miles = {}
    for r in rows:
        d = r["date"]
        if not d:
            continue
        wt = (r["workout_type"] or "").strip().lower()
        if wt in CROSS_TRAINING_TYPES:
            continue
        miles = maybe_float(r["miles"]) or 0
        if miles <= 0 and r["is_race"] != "1":
            continue
        rec = by_date.setdefault(d, {"miles": 0.0, "runs": 0, "type": "easy"})
        rec["miles"] += miles
        rec["runs"] += 1
        if miles >= best_miles.get(d, -1):
            best_miles[d] = miles
            rec["type"] = map_type(r["workout_type"], r["is_race"] == "1")
    return by_date


def _by_year(by_date):
    out = {}
    for d, rec in by_date.items():
        out.setdefault(int(d[:4]), {})[d] = rec
    return out


def _fmt_day(d):
    return "%d %s" % (d.day, MONTH_ABBR[d.month - 1])


def _summary_lines(year, day_recs):
    """The center subtitle. A partial year must say so -- an unqualified "51
    runs" next to another year's 194 reads as a collapse in training rather
    than a short window of data (2003 starts 31 Aug, 2007 ends 12 May)."""
    dates = sorted(day_recs)
    total_miles = sum(rec["miles"] for rec in day_recs.values())
    total_runs = sum(rec["runs"] for rec in day_recs.values())
    first, last = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
    lines = ["%d runs · %s mi" % (total_runs, format(int(round(total_miles)), ","))]
    if first > date(year, 1, 7) or last < date(year, 12, 24):
        lines.append("%s – %s · partial year" % (_fmt_day(first), _fmt_day(last)))
    return lines


def _ndays(year):
    return 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365


def _year_layer(year, day_recs, mx, visible):
    nd = _ndays(year)
    out = ['<g class="yc-year" data-year="%d"%s>'
           % (year, "" if visible else ' style="display:none"')]

    for m in range(12):
        deg = (date(year, m + 1, 1).timetuple().tm_yday - 1) / nd * 360 - 90
        a = math.radians(deg)
        out.append(
            '<line class="yc-tick" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
            % (C + R0 * math.cos(a), C + R0 * math.sin(a),
               C + (R1 + 16) * math.cos(a), C + (R1 + 16) * math.sin(a)))
        am = math.radians(deg + 15)
        out.append(
            '<text class="yc-month" x="%.1f" y="%.1f" text-anchor="middle" '
            'letter-spacing="1.5">%s</text>'
            % (C + (R1 + 36) * math.cos(am), C + (R1 + 36) * math.sin(am),
               MONTH_ABBR[m].upper()))

    out.append('<circle class="yc-ring" cx="%.1f" cy="%.1f" r="%d" fill="none"/>' % (C, C, R0))

    spokes, hits = [], []
    for d in sorted(day_recs):
        miles = day_recs[d]["miles"]
        doy = date.fromisoformat(d).timetuple().tm_yday - 1
        ang = math.radians(doy / nd * 360 - 90)
        if miles <= 0:
            # No distance recorded (a race with a blank miles field). A spoke
            # would be exactly zero units long, though it still counts toward
            # the subtitle -- so it gets a tick inside the ring instead.
            r0, r1 = R0 - 13, R0 - 4
        else:
            ln = R0 + (R1 - R0) * math.sqrt(min(miles / mx, 1.0)) if mx else R0
            r0, r1 = R0, max(ln, R0 + 4)
        type_color = TYPE_COLORS[day_recs[d]["type"]]
        spokes.append(
            '<line class="yc-spoke" data-date="%s" data-type-color="%s" '
            'x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
            % (d, type_color, C + r0 * math.cos(ang), C + r0 * math.sin(ang),
               C + r1 * math.cos(ang), C + r1 * math.sin(ang)))
        hr0 = R0 - 15
        hits.append(
            '<line class="yc-hit" data-date="%s" data-miles="%.2f" data-type="%s" '
            'x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
            % (d, miles, day_recs[d]["type"],
               C + hr0 * math.cos(ang), C + hr0 * math.sin(ang),
               C + (R1 + 8) * math.cos(ang), C + (R1 + 8) * math.sin(ang)))
    out.append('<g class="yc-spokes">' + "".join(spokes) + "</g>")
    # hit targets last so they sit on top and are as easy to reach as a real spoke
    out.append('<g class="yc-hits">' + "".join(hits) + "</g>")

    out.append('<text class="yc-num" x="%.1f" y="%.1f" text-anchor="middle" '
               'letter-spacing="4">%d</text>' % (C, C - 4, year))
    for i, line in enumerate(_summary_lines(year, day_recs)):
        out.append('<text class="yc-sub" x="%.1f" y="%.1f" text-anchor="middle" '
                   'letter-spacing="1">%s</text>' % (C, C + 28 + i * 21, line))

    out.append("</g>")
    return "\n".join(out)


def year_clock_html(rows):
    """The whole Year Clock card: SVG + year-picker bar + a small JSON data
    blob for the JS (years list + which one starts visible). Returns "" if
    there's no running data to draw (nothing to build a clock from)."""
    by_date = _daily_running_miles(rows)
    if not by_date:
        return ""

    years_map = _by_year(by_date)
    years = sorted(years_map)
    mx = max(rec["miles"] for recs in years_map.values() for rec in recs.values())
    start = max(years, key=lambda y: len(years_map[y]))   # the fullest year lands first

    picker = []
    for y in years:
        dates = sorted(years_map[y])
        first, last = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
        partial = first > date(y, 1, 7) or last < date(y, 12, 24)
        attrs = (' class="partial" title="partial year: %s – %s"'
                 % (_fmt_day(first), _fmt_day(last))) if partial else ""
        picker.append('<button type="button" data-year="%d" aria-pressed="false"%s>%d</button>'
                      % (y, attrs, y))

    layers = "\n".join(_year_layer(y, years_map[y], mx, visible=(y == start)) for y in years)

    labels = {t: TYPE_LABELS.get(t, t.title())
              for t in ("easy", "long", "tempo", "workout", "race")}
    data_json = json.dumps(
        {"years": years, "start": str(start), "labels": labels}
    ).replace("</", "<\\/")

    legend_type = "".join(
        '<span class="hm-legend-item"><span class="swatch" '
        'style="background:%s"></span>%s</span>' % (TYPE_COLORS[t], labels[t])
        for t in ("easy", "long", "tempo", "workout", "race"))

    return f"""
    <div class="card yc-card">
      <div class="card-header">
        <div class="card-title">Year Clock</div>
        <div class="hm-mode-toggle">
          <button class="yc-toggle" data-mode="type">Workout Type</button>
          <button class="yc-toggle active" data-mode="intensity">Miles Intensity</button>
        </div>
      </div>
      <svg id="yc-svg" viewBox="0 0 {S} {S}">
        {layers}
      </svg>
      <div class="yc-legend yc-legend-type" data-mode="type" hidden>{legend_type}</div>
      <div class="yc-legend yc-legend-intensity" data-mode="intensity">Spoke length is mileage.</div>
      <p id="yc-readout"></p>
      <div class="yc-bar" id="yc-years">{"".join(picker)}</div>
      <script id="yc-data" type="application/json">{data_json}</script>
    </div>"""
