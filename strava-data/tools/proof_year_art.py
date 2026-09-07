"""Exploration proofs for the calendar-year art piece.

Four directions that were tried before the composition was chosen: a calendar
grid, the year clock, the bloom, and a time-of-day tapestry. The piece that won
(the year clock standing on the bloom) is NOT duplicated here -- it lives in
`strava-data/dashboard/art_year.py`, because the dashboard's Art tab renders it,
and this tool imports it from there.

Writes an HTML proof sheet plus one SVG per direction under
Project Docs/Plans/strava-data/year-art/.
"""
import calendar, math, os, sys
from collections import defaultdict
from datetime import date

# dashboard/ is a sibling package under strava-data/; this file is in tools/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.art_year import (  # noqa: E402
    ART_BG, COLOR, FAM_LABEL, UNMAPPED, art_fragment, by_year, fmt_day, load,
    load_tracks, ndays, path, scale_of, static_svg,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "Project Docs", "Plans", "strava-data", "year-art")
YEAR = 2025
BG = ART_BG


# ---------------------------------------------------------------- concept A
def concept_grid(acts, tracks):
    """12 rows x 31 columns. One cell per day; route drawn at true relative
    scale within the month so a long day visibly dwarfs a short one."""
    CW, CH, GAP = 34, 34, 3
    W = 31 * (CW + GAP) + 90
    H = 12 * (CH + GAP) + 60
    by_day = defaultdict(list)
    for a in acts:
        by_day[a["dt"].date()].append(a)
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG)]
    for m in range(1, 13):
        y0 = 34 + (m - 1) * (CH + GAP)
        out.append('<text x="8" y="%.1f" fill="#64748b" font-family="system-ui" '
                   'font-size="11">%s</text>' % (y0 + CH / 2 + 4, calendar.month_abbr[m]))
        span = 1.0  # common scale for the month: the biggest day sets it
        for d in range(1, 32):
            try:
                dd = date(YEAR, m, d)
            except ValueError:
                continue
            for a in by_day.get(dd, []):
                t = tracks.get(a["id"])
                if t:
                    span = max(span,
                               max(p[0] for p in t) - min(p[0] for p in t),
                               max(p[1] for p in t) - min(p[1] for p in t))
        for d in range(1, 32):
            try:
                dd = date(YEAR, m, d)
            except ValueError:
                continue
            x0 = 60 + (d - 1) * (CW + GAP)
            out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="#12181f" '
                       'stroke="#1c2530" stroke-width="0.7"/>' % (x0, y0, CW, CH))
            for a in by_day.get(dd, []):
                t = tracks.get(a["id"])
                c = COLOR[a["fam"]]
                if not t:  # no GPS: a ring sized by duration
                    r = 2 + min(a["min"], 120) / 40
                    out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" '
                               'stroke="%s" stroke-width="1.4"/>'
                               % (x0 + CW / 2, y0 + CH / 2, r, c))
                    continue
                s = (CW * 0.84) / span
                cx = sum(p[0] for p in t) / len(t)
                cy = sum(p[1] for p in t) / len(t)
                pp = [((x - cx) * s + x0 + CW / 2, (y - cy) * s + y0 + CH / 2) for x, y in t]
                out.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.9" '
                           'stroke-linejoin="round" opacity="0.95"/>' % (path(pp), c))
    for d in range(1, 32):
        out.append('<text x="%.1f" y="24" fill="#475569" text-anchor="middle" '
                   'font-family="system-ui" font-size="9">%d</text>'
                   % (60 + (d - 1) * (CW + GAP) + CW / 2, d))
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- concept B
def concept_spiral(acts, tracks):
    """A year-clock: 365 days around a ring, each activity a radial bar whose
    length is distance and whose width is duration. Sport by color."""
    S = 820
    C = S / 2
    R0, R1 = 150, 380
    mx = max(a["km"] for a in acts) or 1
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (S, S),
           '<rect width="%d" height="%d" fill="%s"/>' % (S, S, BG)]
    for m in range(12):
        deg = (date(YEAR, m + 1, 1).timetuple().tm_yday - 1) / 365 * 360 - 90
        a = math.radians(deg)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#1e293b" '
                   'stroke-width="1"/>' % (C + R0 * math.cos(a), C + R0 * math.sin(a),
                                           C + (R1 + 16) * math.cos(a),
                                           C + (R1 + 16) * math.sin(a)))
        am = math.radians(deg + 15)
        out.append('<text x="%.1f" y="%.1f" fill="#475569" font-family="system-ui" '
                   'font-size="13" text-anchor="middle">%s</text>'
                   % (C + (R1 + 34) * math.cos(am), C + (R1 + 34) * math.sin(am),
                      calendar.month_abbr[m + 1]))
    out.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="none" stroke="#1e293b"/>' % (C, C, R0))
    for a in acts:
        ang = math.radians((a["dt"].timetuple().tm_yday - 1) / 365 * 360 - 90)
        ln = R0 + (R1 - R0) * math.sqrt(a["km"] / mx)
        w = 1.2 + min(a["min"], 240) / 60
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="%.1f" stroke-linecap="round" opacity="0.85"/>'
                   % (C + R0 * math.cos(ang), C + R0 * math.sin(ang),
                      C + ln * math.cos(ang), C + ln * math.sin(ang), COLOR[a["fam"]], w))
    tot = sum(a["km"] for a in acts) * 0.621371
    out.append('<text x="%.1f" y="%.1f" fill="#e2e8f0" font-family="system-ui" '
               'font-size="44" text-anchor="middle">%d</text>' % (C, C - 6, YEAR))
    out.append('<text x="%.1f" y="%.1f" fill="#64748b" font-family="system-ui" '
               'font-size="15" text-anchor="middle">%d activities &#183; %s mi</text>'
               % (C, C + 26, len(acts), format(int(round(tot)), ",")))
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- concept C
def concept_bloom(acts, tracks):
    """Every route of the year overlaid from a common origin, rotated by its
    day-of-year. The year becomes one organism rather than 194 pictures."""
    S = 860
    C = S / 2
    keep = [(a, tracks[a["id"]]) for a in acts if tracks.get(a["id"])]
    ext = max(max(max(abs(x), abs(y)) for x, y in t) for _, t in keep)
    s = (S * 0.46) / ext
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (S, S),
           '<rect width="%d" height="%d" fill="%s"/>' % (S, S, BG)]
    for a, t in keep:
        th = (a["dt"].timetuple().tm_yday - 1) / 365 * 2 * math.pi
        ct, st = math.cos(th), math.sin(th)
        pp = [(C + (x * ct - y * st) * s, C + (x * st + y * ct) * s) for x, y in t]
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.8" '
                   'opacity="0.5" stroke-linejoin="round"/>' % (path(pp), COLOR[a["fam"]]))
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- concept D
def concept_clock(acts, tracks):
    """Time-of-day tapestry: x = day of year, y = clock time. Each activity is
    a bar at the hour it actually happened, thickness = distance."""
    W, H = 1100, 460
    L, T = 46, 24
    pw, ph = W - L - 16, H - T - 30
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG)]
    for hr in range(0, 25, 3):
        y = T + hr / 24 * ph
        out.append('<line x1="%d" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#1a222c"/>'
                   % (L, y, L + pw, y))
        out.append('<text x="%d" y="%.1f" fill="#475569" text-anchor="end" '
                   'font-family="system-ui" font-size="10">%02d:00</text>' % (L - 8, y + 4, hr))
    for m in range(1, 13):
        x = L + (date(YEAR, m, 1).timetuple().tm_yday - 1) / 365 * pw
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%.1f" stroke="#1a222c"/>'
                   % (x, T, x, T + ph))
        out.append('<text x="%.1f" y="%d" fill="#475569" font-family="system-ui" '
                   'font-size="10">%s</text>' % (x + 4, H - 10, calendar.month_abbr[m]))
    for a in acts:
        x = L + (a["dt"].timetuple().tm_yday - 1) / 365 * pw
        y0 = T + (a["dt"].hour + a["dt"].minute / 60) / 24 * ph
        y1 = y0 + max(a["min"], 8) / 60 / 24 * ph
        w = 1.4 + min(a["km"], 25) / 6
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="%.1f" stroke-linecap="round" opacity="0.8"/>'
                   % (x, y0, x, y1, COLOR[a["fam"]], w))
    out.append("</svg>")
    return "\n".join(out)


def concept_year(acts, tracks):
    """The chosen piece, drawn by the dashboard module so there is one copy."""
    scale = scale_of(acts, {a["id"]: tracks[a["id"]] for a in acts if tracks.get(a["id"])})
    return static_svg(acts, tracks, acts[0]["yr"], scale)


CONCEPTS = [
    ("year", "The piece &#183; year clock on the bloom",
     "B standing on C: every 2025 track from a shared origin, rotated by day of "
     "year, held back as ground; the year clock as figure. Bar length = distance, "
     "thickness = duration, color = sport family.", concept_year),
    ("grid", "A &#183; Calendar grid",
     "12&#215;31 cells, one route per day at true relative scale within its month. "
     "Rest days are the negative space.", concept_grid),
    ("spiral", "B &#183; Year clock",
     "365 days around a ring; bar length = distance, thickness = duration. "
     "Reads as a single object at any size.", concept_spiral),
    ("bloom", "C &#183; Bloom",
     "Every GPS track overlaid from a shared origin, rotated by day of year. "
     "The shape of a year&#8217;s movement, not a map.", concept_bloom),
    ("clock", "D &#183; Time-of-day tapestry",
     "x = day of year, y = wall clock. Shows when you move, and how the season "
     "pushes it around.", concept_clock),
]


# Legend text only -- the family keys and the fam-* classes are separate.
def main():
    os.makedirs(OUT, exist_ok=True)
    all_acts = load()
    tracks = load_tracks(all_acts)
    years = by_year(all_acts)
    scale = scale_of(all_acts, tracks)
    for y in sorted(years):
        n = len(years[y])
        print("%d: %3d activities, %3d with GPS"
              % (y, n, sum(1 for a in years[y] if tracks.get(a["id"]))))
    print("shared scale: longest %.1f mi, bloom extent %.0f m"
          % (scale["mx"] * 0.621371, scale["ext"]))
    nodist = sum(1 for a in all_acts if a["km"] <= 0)
    print("%d activities have no distance -> inner-ring ticks" % nodist)
    if UNMAPPED:
        print("NOTE: sport types not in FAMILY, drawn as 'other': %s"
              % ", ".join(sorted(UNMAPPED)))

    # the proof sheet stays single-year -- it is the record of the four
    # directions, not the deliverable
    acts = years[YEAR]
    cards = []
    for slug, title, blurb, fn in CONCEPTS:
        svg = fn(acts, tracks)
        with open(os.path.join(OUT, slug + ".svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        cards.append('<section><h2>%s</h2><p>%s</p><div class="art">%s</div></section>'
                     % (title, blurb, svg))
        print("wrote", slug + ".svg")

    legend = " ".join('<span><i style="background:%s"></i>%s</span>' % (c, k)
                      for k, c in COLOR.items())
    html = """<!doctype html><meta charset="utf-8"><title>%d year-art proofs</title>
<style>
body{background:#070a0e;color:#cbd5e1;font:15px/1.6 system-ui,sans-serif;margin:0;padding:40px}
h1{font-weight:600;font-size:26px;margin:0 0 4px}
h2{font-size:17px;font-weight:600;color:#e2e8f0;margin:0 0 4px}
p{margin:0 0 14px;color:#64748b;max-width:70ch}
section{max-width:1180px;margin:0 auto 56px}
.art{background:%s;border:1px solid #1c2530;border-radius:10px;padding:10px}
.art svg{width:100%%;height:auto;display:block}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:0 auto 40px;max-width:1180px;color:#94a3b8;font-size:13px}
.legend span{display:flex;align-items:center;gap:6px}
.legend i{width:11px;height:11px;border-radius:2px;display:block}
</style>
<section><h1>%d in motion &#8212; proofs</h1>
<p>%d activities, %d with GPS. Four directions for a calendar-year piece.</p></section>
<div class="legend">%s</div>
%s
""" % (YEAR, BG, YEAR, len(acts), sum(1 for a in acts if tracks.get(a["id"])),
       legend, "".join(cards))
    p = os.path.join(OUT, "proofs.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", p)

    # the interactive piece, exactly as the dashboard's Art tab renders it
    p = os.path.join(OUT, "year.html")
    page = ('<!doctype html><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Years in motion</title>'
            '<style>:root{--border:#334155;--border-subtle:#1e293b;'
            '--text-primary:#e2e8f0;--text-secondary:#94a3b8}'
            'body{background:%s;margin:0;padding:24px;'
            'font:15px/1.5 system-ui,sans-serif;color:var(--text-secondary)}'
            '#art-svg{max-width:min(94vw,82vh)}</style>' % BG
            + art_fragment(load()))
    with open(p, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote", p, "(%.1f MB)" % (os.path.getsize(p) / 1e6))


if __name__ == "__main__":
    main()
