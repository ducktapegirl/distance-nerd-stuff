#!/usr/bin/env python3
"""Proof sheet for the landing-page tile art — twelve directions from the real data.

    uv run python tools/proof_landing_art.py

Modeled on strava-data/tools/proof_year_art.py: one function per direction, a
CONCEPTS list, one .svg written per direction plus an HTML index. Writes to
Project Docs/Plans/landing-art/proofs/.

This is an exploration tool, not a build step — nothing imports it and no
workflow runs it. Once the two winners are voted on, their bodies move into
landing/art.py and this stays as the record of what was considered.

The brief is Project Docs/Plans/landing-art.md. Three things it gets wrong or
does not say, each of which shapes everything below:

  * **The tile is 4:3, not square.** landing/template.py sets
    `.tile-art-wrap { aspect-ratio: 4 / 3 }` with `preserveAspectRatio="…slice"`,
    so a square 480x480 artwork silently loses 12.5% off the top and the same
    off the bottom. Everything here is authored 640x480 and crops nothing.
  * **strava-data/data/streams/ is NOT gitignored** — all 379 files are tracked,
    so CI, fork PRs and fresh clones all have the geometry. No precomputed
    asset is needed; reading all 378 costs ~1.5 s.
  * **The ~40 KB budget forces subset selection** on any "every activity"
    direction: all 351 routes at step=12 is ~595 KB and all 374 elevation
    profiles is ~192 KB. Every concept prints its measured size against the
    budget, so a direction that only fits after subsetting is visible at vote
    time rather than discovered at wire-up.
"""

import datetime
import html
import math
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from landing.config import ACTIVITIES_CSV, RUNNING_LOG_CSV, TILES  # noqa: E402
from landing.geometry import (  # noqa: E402
    COLOR, FAMILY, altitude, bbox, fit, path, rotate, simplify, thin, track,
)

import csv  # noqa: E402

OUT = os.path.join(ROOT, "Project Docs", "Plans", "landing-art", "proofs")

# The tile's real frame. Authored at 4:3 so `slice` crops nothing.
W, H = 640, 480
BUDGET = 40 * 1024          # the brief's ~40 KB per tile
WEEKS = 53                  # slots in an academic year, Aug 1 anchored

# ─── palette ──────────────────────────────────────────────────────────────────
# name -> (dark, light). The two tile accents come straight from landing/config
# TILES; the five family colors and their light values match art_year.py's
# ART_CSS so the site keeps one vocabulary. Every one of these needs a value in
# both columns — a color defined only in dark is how the light theme ships
# broken.
VARS = {
    "art-bg":      ("#1c2230", "#ffffff"),
    "art-faint":   ("#2b3446", "#e4e7ee"),
    "art-col":     ("#a78bfa", "#7c3aed"),   # college — the tile's violet
    "art-col-dim": ("#6d5bd0", "#c4b5fd"),
    "art-col-hot": ("#f0abfc", "#c026d3"),   # races and accents
    "art-str":     ("#f59e0b", "#b45309"),   # strava — the tile's amber
    "art-str-dim": ("#8a5f14", "#f3c98b"),
    "art-run":     ("#2dd4bf", "#0d9488"),
    "art-mtb":     ("#f59e0b", "#b45309"),
    "art-foot":    ("#a3e635", "#4d7c0f"),
    "art-snow":    ("#60a5fa", "#1d4ed8"),
    "art-other":   ("#f472b6", "#be185d"),
    # Not colors: opacities that have to differ by theme. A trace that reads
    # correctly at 0.3 on #1c2230 is a ghost at 0.3 on white, which is the same
    # trap art_year.py's --art-trace-op exists to avoid.
    "art-op-trace":  ("0.30", "0.50"),
    "art-op-tangle": ("0.72", "0.88"),
}
FAM_VAR = {"run": "art-run", "mtb": "art-mtb", "foot": "art-foot",
           "snow": "art-snow", "other": "art-other"}


def paint(key):
    """var() for the page, literal value for anything that rasterizes.

    Rasterizers do not implement var(), so every call carries the dark literal
    as the fallback — the same paint()/ink() gate art_year.py uses.
    """
    return "var(--%s, %s)" % (key, VARS[key][0])


def _decls(i):
    return "".join("--%s:%s;" % (k, v[i]) for k, v in VARS.items())


# Inside a standalone .svg there is no .light class to hang the theme on, so
# those files follow the OS instead. proofs.html and the real page use the
# class, matching nerd_common/theme_ui.py.
SVG_STYLE = ("<style>svg{%s}@media (prefers-color-scheme:light){svg{%s}}</style>"
             % (_decls(0), _decls(1)))
PAGE_VARS = ":root{%s}\n:root.light{%s}" % (_decls(0), _decls(1))


# ─── data ─────────────────────────────────────────────────────────────────────

def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def load_college():
    """running_log.csv enriched with the handful of derived fields the art wants.

    The academic year is anchored on 1 August, which is what puts 2003-08-31 —
    the very first entry — in the first year rather than stranded in a fifth.
    """
    rows = []
    with open(RUNNING_LOG_CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if not r.get("date"):
                continue
            d = datetime.date.fromisoformat(r["date"])
            ay = d.year if d.month >= 8 else d.year - 1
            cm = " ".join((r.get("comments") or "").split())
            rows.append({
                "d": d, "ay": ay,
                "wk": min((d - datetime.date(ay, 8, 1)).days // 7, WEEKS - 1),
                "doy": d.timetuple().tm_yday,
                "mi": _f(r.get("miles")), "mins": _f(r.get("minutes")),
                "pace": _f(r.get("pace_min_per_mile")),
                "race": r.get("is_race") == "1", "comment": cm,
            })
    rows.sort(key=lambda r: r["d"])
    return rows


def load_strava():
    acts = []
    with open(ACTIVITIES_CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            acts.append({
                "id": r["id"], "name": r.get("name", ""),
                "dt": datetime.datetime.strptime(r["start_date_local"],
                                                 "%Y-%m-%d %H:%M:%S"),
                "sport": r.get("sport_type", ""),
                "fam": FAMILY.get(r.get("sport_type", ""), "other"),
                "km": _f(r.get("distance_km")),
                "gain": _f(r.get("total_elevation_gain_m")),
            })
    acts.sort(key=lambda a: a["dt"])
    return acts


def spread(seq, n):
    """n items evenly spaced through seq, ends included. Deterministic."""
    seq = list(seq)
    if n < 1 or not seq:
        return []
    if len(seq) <= n:
        return seq
    if n == 1:
        return [seq[0]]
    return [seq[round(i * (len(seq) - 1) / (n - 1))] for i in range(n)]


# ─── college: abstract / rhythmic (no GPS exists for 2003-2007) ───────────────

def a1_ring(D):
    """A1 — Ring of Seasons.

    Four concentric ribbons, one per academic year, thickness = that week's
    mileage. Deliberately coarser than running-log/dashboard/year_clock.py and
    stripped of every label, so the tile is not a small copy of a chart the
    dashboard already has. The gaps are the point: the inner ring opens at the
    top where the log starts in week 4, and the outer one stops dead at week 40
    — May 2007, graduation.
    """
    rows = [r for r in D["college"] if r["mi"] > 0]
    if not rows:
        return ""
    wk = defaultdict(float)
    for r in rows:
        wk[(r["ay"], r["wk"])] += r["mi"]
    ays = sorted({k[0] for k in wk})
    mx = max(wk.values())
    cx, cy = W / 2, H / 2
    out = []
    for i, ay in enumerate(ays):
        # Thin rings, widely spaced. Thick ones (the first cut used 62 + 46i at
        # a half-thickness of 20) merge visually into a single spiral swoosh
        # rather than four separate years — the one thing this direction cannot
        # afford, since "four concentric years" is the whole idea.
        rc = 85 + i * 42
        outer, inner = [], []
        for w in range(WEEKS):
            a = math.radians(-90 + w / WEEKS * 360)
            t = 15.0 * min(wk.get((ay, w), 0.0) / mx, 1.0)
            ca, sa = math.cos(a), math.sin(a)
            outer.append((cx + (rc + t) * ca, cy + (rc + t) * sa))
            inner.append((cx + (rc - t) * ca, cy + (rc - t) * sa))
        d = (path(outer) + "L"
             + "L".join("%.1f %.1f" % p for p in reversed(inner)) + "Z")
        out.append('<path d="%s" fill="%s" opacity="%.2f"/>'
                   % (d, paint("art-col"), 0.5 + 0.5 * i / max(len(ays) - 1, 1)))
    return "\n".join(out)


def _weave(D, per):
    rows = [r for r in D["college"] if r["mi"] > 0]
    if not rows:
        return ""
    d0 = min(r["d"] for r in rows)
    start = d0 - datetime.timedelta(days=d0.weekday())
    nrow = ((max(r["d"] for r in rows) - start).days // 7) // per + 1
    L, R, T, B = 38, 602, 20, 460
    rh = (B - T) / nrow
    colw = (R - L) / 7
    mx = max(r["mi"] for r in rows)

    # The weft has to be a real, continuous thread, not a hairline. The first
    # cut drew it at 0.4 units against 1.6-unit slubs, which made the seven day
    # columns read as seven separate barcodes with gutters between them —
    # the opposite of cloth.
    weft = "".join("M%d %.2fH%d" % (L, T + (i + 0.5) * rh, R) for i in range(nrow))
    out = ['<path d="%s" stroke="%s" stroke-width="%.2f" fill="none" opacity="0.5"/>'
           % (weft, paint("art-col-dim"), min(rh * 0.34, 1.2))]
    segs = []
    for r in rows:
        i = ((r["d"] - start).days // 7) // per
        # A big week deliberately overruns its column and merges with the days
        # either side of it: that overlap is what stops the seven columns from
        # reading as seven charts.
        ln = 12 + (colw + 12) * (r["mi"] / mx) ** 0.75
        segs.append("M%.1f %.2fh%.1f"
                    % (L + r["d"].weekday() * colw + (colw - ln) / 2,
                       T + (i + 0.5) * rh, ln))
    out.append('<path d="%s" stroke="%s" stroke-width="%.2f" fill="none" '
               'stroke-linecap="round" opacity="0.9"/>'
               % ("".join(segs), paint("art-col"), min(rh * 0.8, 3.6)))
    return "\n".join(out)


def a2_weave(D):
    """A2 — Woven Weeks.

    Warp of seven day-columns, weft of ~192 week-rows, each run a slub whose
    length is its mileage. At 2.3 units a row this is either a textile or a
    moire at the 240 px size — which is exactly what the proof is for.
    """
    return _weave(D, 1)


def a2b_weave(D):
    """A2b — Woven Weeks, two weeks to a row.

    The same cloth at half the thread count: ~96 rows at 4.5 units. Coarser and
    safer at 240 px, at the cost of some of the fineness that makes A2 read as
    fabric rather than as a bar chart lying on its side.
    """
    return _weave(D, 2)


def a3_ribbon(D):
    """A3 — Pace Ribbon.

    One sweep across four years: height is that week's mileage-weighted pace
    (faster is higher), thickness is time on feet. Binned by week rather than
    drawn per run — 1,138 marks over 568 units is noise, and the weekly ribbon
    is the honest shape of a training block. SVG cannot vary stroke width along
    a path, so this is a filled envelope, not a stroke.

    The brief's own warning applies: of the six, this is the one most likely to
    read as a chart.
    """
    rows = [r for r in D["college"]
            if r["mi"] > 0 and r["mins"] > 0 and 5.0 <= r["pace"] <= 11.0]
    if not rows:
        return ""
    d0 = min(r["d"] for r in rows)
    start = d0 - datetime.timedelta(days=d0.weekday())
    bins = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        b = bins[(r["d"] - start).days // 7]
        b[0] += r["mi"]
        b[1] += r["mins"]
    n = max(bins) + 1
    raw = {i: v[1] / v[0] for i, v in bins.items()}
    # A three-week centered mean over whatever neighbours exist. Unsmoothed,
    # week-to-week pace swings further than the whole plotted range, so the
    # ribbon shreds into vertical spikes and reads as noise rather than as a
    # training block. Smoothing is the difference between a ribbon and a graph
    # of the difference between consecutive weeks.
    sm = {}
    for i in raw:
        near = [raw[j] for j in (i - 1, i, i + 1) if j in raw]
        sm[i] = sum(near) / len(near)
    vals = sorted(sm.values())
    lo = vals[0] - 0.3
    hi = vals[-1] + 0.3
    mxm = max(v[1] for v in bins.values())

    L, R, T, B = 34, 606, 44, 436
    subs, block = [], []
    for i in range(n + 1):
        v = bins.get(i)
        if v:
            x = L + i / max(n - 1, 1) * (R - L)
            # y inverted: a faster pace sits higher, the way the dashboards do it
            y = B - (sm[i] - lo) / (hi - lo) * (B - T)
            block.append((x, y, 3.0 + 17.0 * (v[1] / mxm)))
        elif block:
            subs.append(block)
            block = []
    if block:
        subs.append(block)

    out = []
    for blk in subs:
        # A lone week is a spike, not a ribbon — it has no direction to travel in
        if len(blk) < 3:
            continue
        top = [(x, y - t) for x, y, t in blk]
        bot = [(x, y + t) for x, y, t in reversed(blk)]
        out.append('<path d="%sL%sZ" fill="%s" opacity="0.9"/>'
                   % (path(top), "L".join("%.1f %.1f" % p for p in bot),
                      paint("art-col")))
    return "\n".join(out)


def a4_constellation(D):
    """A4 — Constellation.

    A dot per run at (day of year, minutes), sized by miles, with a faint thread
    between runs within three days of each other. Four years overlaid on one
    calendar, so the voids — summers, the taper into finals, the injuries —
    are the subject rather than the marks.

    Only the 798 runs that recorded a duration can be placed; the other 340 have
    miles but no minutes. Dots ship as <use> of five symbols: 1,138 <circle>
    elements would be ~57 KB on their own, which is the whole budget.
    """
    pts = [r for r in D["college"] if r["mi"] > 0 and r["mins"] > 0]
    if not pts:
        return ""
    L, R, T, B = 38, 602, 34, 446
    mx = max(r["mi"] for r in pts)

    def xy(r):
        return (L + (r["doy"] - 1) / 365.0 * (R - L),
                B - min(r["mins"], 120.0) / 120.0 * (B - T))

    # A link only when the two runs are near in both axes. Linking on date
    # alone drops a near-vertical stem from every dot whose neighbour ran a very
    # different duration, and the field stops reading as a constellation and
    # starts reading as a barcode with drips.
    thread = []
    prev = None
    for r in pts:
        x, y = xy(r)
        if (prev and (r["d"] - prev[0]).days <= 3
                and abs(x - prev[1]) < 14 and abs(y - prev[2]) < 34):
            thread.append("L%.0f %.0f" % (x, y))
        else:
            thread.append("M%.0f %.0f" % (x, y))
        prev = (r["d"], x, y)

    defs = "".join('<circle id="art-a4-d%d" r="%.2f"/>' % (i, 1.1 + i * 0.85)
                   for i in range(5))
    uses = defaultdict(list)
    for r in pts:
        x, y = xy(r)
        k = min(int(r["mi"] / mx * 5), 4)
        uses[k].append('<use href="#art-a4-d%d" x="%.0f" y="%.0f"/>' % (k, x, y))

    out = ['<defs>%s</defs>' % defs,
           '<path d="%s" fill="none" stroke="%s" stroke-width="0.5" opacity="0.45"/>'
           % ("".join(thread), paint("art-col-dim"))]
    for k in sorted(uses):
        out.append('<g fill="%s" opacity="%.2f">%s</g>'
                   % (paint("art-col"), 0.55 + k * 0.11, "".join(uses[k])))
    return "\n".join(out)


def a5_strata(D):
    """A5 — Ink Strata.

    One full-bleed band per month, ruled at a density set by that month's
    volume. Sedimentary rather than statistical: no axis, no scale, nothing to
    read a number off, and the month boundaries do the work of bedding planes.

    Two things had to go to get here. The rules run horizontally, ALONG each
    band: a band is only H/46 = 10.4 units tall, so hatching near the vertical
    draws a 10-unit stub and stops, and since every band carries its own
    pattern the stubs do not line up across the boundary — the tile renders as
    a field of falling dashes rather than as strata. And the rules are all at
    exactly 90 degrees; tilting them a few degrees per academic year, to make
    the four years legible as separate beds, put a huge moire fan across every
    tilted band and swamped the density differences that are the actual subject.

    Cheapest of the six by a wide margin — seven <pattern> defs and 46 <rect>s.
    """
    rows = [r for r in D["college"] if r["mi"] > 0]
    if not rows:
        return ""
    vol = defaultdict(float)
    for r in rows:
        vol[(r["d"].year, r["d"].month)] += r["mi"]
    months = sorted(vol)
    mx = max(vol.values())

    bh = H / len(months)
    used, rects = set(), []
    for i, m in enumerate(months):
        lv = min(int(vol[m] / mx * 6.99), 6)
        used.add(lv)
        rects.append('<rect x="0" y="%.2f" width="%d" height="%.2f" fill="url(#art-a5-%d)"/>'
                     % (i * bh, W, bh + 0.4, lv))
        if i:
            rects.append('<line x1="0" y1="%.2f" x2="%d" y2="%.2f" stroke="%s" '
                         'stroke-width="0.5" opacity="0.6"/>'
                         % (i * bh, W, i * bh, paint("art-bg")))
    # Spacing is the gap BETWEEN rules, so it has to fit several into a
    # 10.4-unit band: 5.6 down to 1.9 gives roughly two rules in the quietest
    # month and six in the heaviest, which is the tonal range the density is
    # supposed to carry.
    defs = []
    for lv in sorted(used):
        sp = 5.6 - 0.62 * lv
        # The rule overruns its tile. Drawn exactly 0..sp it meets the next tile
        # on an antialiased cap, and the seam shows as a break in the line.
        defs.append('<pattern id="art-a5-%d" width="%.2f" height="%.2f" '
                    'patternUnits="userSpaceOnUse" patternTransform="rotate(90)">'
                    '<line x1="0" y1="-1" x2="0" y2="%.2f" stroke="%s" stroke-width="%.2f"/>'
                    '</pattern>'
                    % (lv, sp, sp, sp + 1, paint("art-col"), 0.4 + 0.13 * lv))
    return "<defs>%s</defs>\n%s" % ("".join(defs), "\n".join(rects))


def a6_type(D):
    """A6 — Typographic mass.

    The log's own comments, set at 3.6 units and stacked until they fill the
    tile, so the words that were actually written become the texture. Line
    opacity follows that day's mileage, which gives the block tonal bands
    without adding a single mark that isn't the log.

    Illegible at tile size is the point; it still has to be deliberately so.
    SVG has no text wrapping, so lines are truncated to the measured monospace
    column rather than flowed.
    """
    cms = [r for r in D["college"] if r["comment"]]
    if not cms:
        return ""
    nl = 104
    fs, lh = 3.6, (H - 14) / 104.0
    cols = int((W - 24) / (fs * 0.6))
    mx = max(r["mi"] for r in cms) or 1.0
    out = ['<g font-family="\'Geist Mono\', ui-monospace, monospace" '
           'font-size="%.2f" fill="%s">' % (fs, paint("art-col"))]
    for i, r in enumerate(spread(cms, nl)):
        out.append('<text x="12" y="%.2f" opacity="%.2f">%s</text>'
                   % (12 + i * lh, 0.22 + 0.68 * min(r["mi"] / mx, 1.0),
                      html.escape(r["comment"][:cols])))
    out.append("</g>")
    return "\n".join(out)


# ─── strava: literal / linear (378 activities, 352 with GPS) ──────────────────

def b1_bloom(D):
    """B1 — Route Bloom.

    Every route recentered on its own start and rotated to its day of year, so
    a year of movement opens as one radial flower.

    Deliberately NOT art_year.py's bloom, which already sits under the Year
    Clock on the Strava dashboard's Art tab: that one keeps true compass
    orientation and colors by sport family. This rotates and holds a single
    hue, so the two cannot be mistaken for crops of each other.

    All 351 routes would be ~595 KB, so this is a 110-route spread across the
    whole record, Douglas-Peucker'd and then hard-capped at 30 points each.
    """
    keep = [a for a in D["acts"] if D["tracks"].get(a["id"])]
    if not keep:
        return ""
    picked = spread(keep, 110)
    exts = sorted(max(max(abs(x), abs(y)) for x, y in D["tracks"][a["id"]])
                  for a in picked)
    ext = exts[int(len(exts) * 0.85)] or 1.0
    s = (min(W, H) * 0.46) / ext
    cx, cy = W / 2, H / 2
    out = ['<g fill="none" stroke="%s" stroke-width="0.95" stroke-linejoin="round" '
           'opacity="%s">' % (paint("art-str"), paint("art-op-trace"))]
    for a in picked:
        th = (a["dt"].timetuple().tm_yday - 1) / 366.0 * 2 * math.pi
        pp = [(cx + x * s, cy + y * s)
              for x, y in rotate(D["tracks"][a["id"]], th)]
        out.append('<path d="%s"/>' % path(thin(simplify(pp, 1.4), 30), 0))
    out.append("</g>")
    return "\n".join(out)


def b2_contour(D):
    """B2 — Contour Field.

    Elevation streams only, stacked as ridgelines and sorted by total gain, each
    filled opaque so the row in front occludes the one behind. Pure geography,
    zero map, and the cheapest of the six — it reads altitude_m and never
    touches lat/lng or the projection.

    Amplitude follows sqrt(relief), not relief: a linear scale against the
    2,058 m day flattens the median 84 m one to four percent of the frame and
    the field turns into 40 straight lines.
    """
    have = [a for a in D["acts"] if D["alts"].get(a["id"])]
    if not have:
        return ""
    # 40 ridges at 48 points, drawn to integer coordinates. Separating the fill
    # from the stroke doubles the path data, which is what pays for the honest
    # horizon — so the resolution has to come down to stay inside 40 KB.
    picked = spread(sorted(have, key=lambda a: a["gain"], reverse=True), 40)
    reliefs = [max(D["alts"][a["id"]]) - min(D["alts"][a["id"]]) for a in picked]
    mxr = max(reliefs) or 1.0

    # T leaves room for the tallest ridge's peak: the first row's baseline sits
    # at T and its amplitude reaches up from there, so T below the max amplitude
    # runs the biggest day straight off the top of the tile.
    L, R, T = 40, 600, 88
    dy = (H - T - 40) / max(len(picked) - 1, 1)
    out = []
    for i, a in enumerate(picked):
        prof = D["alts"][a["id"]]
        base = T + i * dy
        lo, span = min(prof), (max(prof) - min(prof)) or 1.0
        amp = 74.0 * (reliefs[i] / mxr) ** 0.4
        pts = [(L + j / (len(prof) - 1) * (R - L), base - (v - lo) / span * amp)
               for j, v in enumerate(prof)]
        d = path(pts, 0)
        # Fill and stroke MUST be two elements. Stroking the closed occluder
        # draws its baseline and both vertical sides too, so every ridge comes
        # out boxed and the stack reads as 44 rectangles instead of a horizon.
        out.append('<path d="%sL%d %.0fL%d %.0fZ" fill="%s"/>'
                   % (d, R, base, L, base, paint("art-bg")))
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.2" '
                   'stroke-linejoin="round"/>' % (d, paint("art-str")))
    return "\n".join(out)


def b3_grid(D):
    """B3 — Route Grid.

    A specimen sheet, one route to a cell, each normalized to its own square and
    colored by sport family — a miniature of tools/poster_40for40.py, which is
    the family resemblance the brief asks for.

    8x6 rather than the brief's 6x6: in a 640x480 frame that is 48 exactly
    square cells, where 6x6 would be 100x73 and quietly distort every route that
    filled one. Picks are a proportional quota per family, then the largest
    routes within each family, so a sheet of 48 is not 48 identical
    neighbourhood loops.
    """
    keep = [a for a in D["acts"] if D["tracks"].get(a["id"])]
    if not keep:
        return ""
    cols, rowsn = 8, 6
    n = cols * rowsn
    byfam = defaultdict(list)
    for a in keep:
        byfam[a["fam"]].append(a)
    # Rank on shape before size. Sorting by distance alone fills the sheet with
    # the longest rides, which are point-to-point and draw as near-straight
    # diagonals — 48 cells of the same line. Squarish bounding boxes are the
    # loops, and loops are what a specimen sheet is for.
    def squarish(a):
        x0, y0, x1, y1 = bbox(D["tracks"][a["id"]])
        w_, h_ = x1 - x0, y1 - y0
        return min(w_, h_) / max(w_, h_, 1e-9) >= 0.38

    quota = {f: max(1, round(len(v) / len(keep) * n)) for f, v in byfam.items()}
    picked = []
    for f in sorted(byfam):
        ranked = sorted(byfam[f], key=lambda a: (not squarish(a), -a["km"], a["id"]))
        picked += ranked[:quota[f]]
    picked = sorted(picked, key=lambda a: a["dt"])[:n]

    cw, ch = W / cols, H / rowsn
    out = []
    for i, a in enumerate(picked):
        pp = fit(thin(simplify(D["tracks"][a["id"]], 6.0), 46),
                 (i % cols) * cw, (i // cols) * ch, cw, ch, pad=11)
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.3" '
                   'stroke-linejoin="round" stroke-linecap="round" opacity="0.92"/>'
                   % (path(pp, 0), paint(FAM_VAR[a["fam"]])))
    return "\n".join(out)


def _signature(D):
    """The most-repeated loop, and everything that matches it.

    Grid-cell Jaccard on the recentered track, the same test poster_40for40.py
    uses to keep two laps of one loop off the wall — here inverted, to find the
    loop that was run the most times. Recentering on the start point is what
    makes two runs of the same loop compare equal even when the watch caught a
    different driveway.
    """
    cand = [a for a in D["acts"] if D["tracks"].get(a["id"]) and 1.0 < a["km"] < 13.0]
    sig = {a["id"]: frozenset((round(x / 100.0), round(y / 100.0))
                              for x, y in D["tracks"][a["id"]]) for a in cand}
    ids = sorted(sig)
    hits = defaultdict(list)
    for i, p in enumerate(ids):
        for q in ids[i + 1:]:
            u = len(sig[p] | sig[q])
            if u and len(sig[p] & sig[q]) / u > 0.5:
                hits[p].append(q)
                hits[q].append(p)
    if not hits:
        return None, []
    best = max(sorted(hits), key=lambda k: len(hits[k]))
    return best, sorted(hits[best])


def b4_signature(D):
    """B4 — Signature Route.

    One line: the 4.4-mile loop out the front door, run more times than any
    other shape in the record. Everything else omitted. The boldest simplicity
    play of the six, ~2 KB, and the only direction that is unambiguously legible
    at 240 px.
    """
    best, _ = _signature(D)
    if not best:
        return ""
    pp = fit(simplify(D["tracks"][best], 4.0), 0, 0, W, H, pad=58)
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="3.4" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
            % (path(pp), paint("art-str")))


def b4b_signature(D):
    """B4b — Signature Route, every repeat.

    The same loop with all of its siblings behind it: every run that matches it
    on the grid-cell test, drawn faint on a common scale, with the signature
    itself solid on top. The GPS wander between repeats becomes the texture —
    "the loop I ran twenty-one times" rather than "a loop".
    """
    best, sibs = _signature(D)
    if not best:
        return ""
    # One scale shared by the whole cluster — fitting each repeat to its own
    # bounds would align them on the frame rather than on each other, and the
    # GPS wander between runs, which is the entire subject here, would vanish.
    allpts = []
    for aid in [best] + sibs:
        allpts += D["tracks"][aid]
    minx = min(p[0] for p in allpts)
    maxx = max(p[0] for p in allpts)
    miny = min(p[1] for p in allpts)
    maxy = max(p[1] for p in allpts)
    s = min((W - 116) / max(maxx - minx, 1e-9), (H - 116) / max(maxy - miny, 1e-9))
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2

    def place(pts):
        return [(W / 2 + (x - cx) * s, H / 2 + (y - cy) * s) for x, y in pts]

    out = ['<g fill="none" stroke="%s" stroke-width="1.5" stroke-linejoin="round" '
           'opacity="0.22">' % paint("art-str")]
    for aid in sibs:
        out.append('<path d="%s"/>' % path(thin(simplify(place(D["tracks"][aid]), 1.2), 90)))
    out.append("</g>")
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.6" '
               'stroke-linejoin="round" stroke-linecap="round"/>'
               % (path(simplify(place(D["tracks"][best]), 1.2)), paint("art-str")))
    return "\n".join(out)


def b5_tangle(D):
    """B5 — Tangle.

    Every route laid head to tail as one unbroken line. Because each is
    recentered on its own start and most of them are loops, the line keeps
    returning to where it began instead of wandering off — so 150 activities
    knot into one dense scribble around a common centre.

    One <path> rather than 150, which is what buys the point budget: no
    per-element overhead, integer coordinates, ~24 points an activity.
    """
    keep = [a for a in D["acts"] if D["tracks"].get(a["id"])]
    if not keep:
        return ""
    cur = (0.0, 0.0)
    pts = [cur]
    for a in spread(keep, 150):
        t = thin(simplify(D["tracks"][a["id"]], 22.0), 24)
        for x, y in t[1:]:
            pts.append((cur[0] + x, cur[1] + y))
        cur = pts[-1]
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="0.95" '
            'stroke-linejoin="round" opacity="%s"/>'
            % (path(fit(pts, 0, 0, W, H, pad=26), 0), paint("art-str"),
               paint("art-op-tangle")))


def b6_bands(D):
    """B6 — Sport Palette Bands.

    Vertical bands whose widths are the five families' shares of the record,
    each filled with a fragment of a real route from that sport, clipped to its
    band. Literal material, abstract arrangement — and the only one of the six
    that still renders with no streams at all, since the widths come from
    activities.csv alone.

    "other" (climbing, pickleball, the gym) has no route worth showing, so it
    gets a dot field rather than a borrowed line.
    """
    acts = D["acts"]
    if not acts:
        return ""
    cnt = Counter(a["fam"] for a in acts)
    order = [f for f in ("run", "mtb", "foot", "snow", "other") if cnt.get(f)]
    tot = sum(cnt[f] for f in order)
    defs, out = [], []
    x = 0.0
    for k, f in enumerate(order):
        bw = W * cnt[f] / tot if k < len(order) - 1 else W - x
        defs.append('<clipPath id="art-b6-c%d"><rect x="%.2f" y="0" width="%.2f" '
                    'height="%d"/></clipPath>' % (k, x, bw, H))
        out.append('<rect x="%.2f" y="0" width="%.2f" height="%d" fill="%s" '
                   'opacity="0.14"/>' % (x, bw, H, paint(FAM_VAR[f])))
        # A loop, not the longest activity. Picking by distance gets a
        # point-to-point ride, and a straight line scaled across a band is a
        # diagonal stripe rather than a recognizable piece of a route.
        cand = [a for a in acts if a["fam"] == f and D["tracks"].get(a["id"])]

        def loopiness(a):
            x0, y0, x1, y1 = bbox(D["tracks"][a["id"]])
            w_, h_ = x1 - x0, y1 - y0
            return (min(w_, h_) / max(w_, h_, 1e-9) >= 0.45, a["km"], a["id"])

        best = max(cand, key=loopiness, default=None)
        if best:
            # Square-ish frame keyed to the band's own width, so a wide band
            # shows most of a route and a narrow one shows a true vertical
            # slice of it — in both cases a fragment at a legible scale.
            side = max(bw * 1.5, H * 1.05)
            pp = fit(thin(simplify(D["tracks"][best["id"]], 4.0), 190),
                     x + bw / 2 - side / 2, H / 2 - side / 2, side, side, pad=6)
            out.append('<g clip-path="url(#art-b6-c%d)"><path d="%s" fill="none" '
                       'stroke="%s" stroke-width="2.4" stroke-linejoin="round" '
                       'stroke-linecap="round"/></g>'
                       % (k, path(pp), paint(FAM_VAR[f])))
        else:
            defs.append('<pattern id="art-b6-p%d" width="9" height="9" '
                        'patternUnits="userSpaceOnUse"><circle cx="4.5" cy="4.5" '
                        'r="1.3" fill="%s"/></pattern>' % (k, paint(FAM_VAR[f])))
            out.append('<rect x="%.2f" y="0" width="%.2f" height="%d" '
                       'fill="url(#art-b6-p%d)" opacity="0.75"/>' % (x, bw, H, k))
        out.append('<line x1="%.2f" y1="0" x2="%.2f" y2="%d" stroke="%s" '
                   'stroke-width="1"/>' % (x, x, H, paint("art-bg")))
        x += bw
    return "<defs>%s</defs>\n%s" % ("".join(defs), "\n".join(out))


# ─── the sheet ────────────────────────────────────────────────────────────────

CONCEPTS = [
    ("college", "a1", "A1 &middot; Ring of Seasons",
     "Four concentric ribbons, one per academic year; thickness is that week&rsquo;s "
     "mileage. Tree rings. The inner ring opens where the log starts in week 4 and "
     "the outer one stops dead at graduation.", a1_ring),
    ("college", "a2", "A2 &middot; Woven Weeks",
     "Seven day-columns warped against ~192 week-rows, each run a slub whose length "
     "is its mileage. Four years as a bolt of cloth.", a2_weave),
    ("college", "a2b", "A2b &middot; Woven Weeks, two weeks a row",
     "The same cloth at half the thread count &mdash; coarser, and safer at 240 px.",
     a2b_weave),
    ("college", "a3", "A3 &middot; Pace Ribbon",
     "One sweep: height is weekly mileage-weighted pace (faster is higher), thickness "
     "is time on feet. A filled envelope, since SVG cannot taper a stroke.", a3_ribbon),
    ("college", "a4", "A4 &middot; Constellation",
     "A dot per run at (day of year, minutes), sized by miles, threaded between runs "
     "three days apart. The voids &mdash; summers, injuries &mdash; are the subject.",
     a4_constellation),
    ("college", "a5", "A5 &middot; Ink Strata",
     "A full-bleed band per month, hatched at a density set by that month&rsquo;s "
     "volume, the angle stepping once per academic year. Sedimentary, not "
     "statistical.", a5_strata),
    ("college", "a6", "A6 &middot; Typographic mass",
     "The log&rsquo;s own comments at 3.6 units, line opacity following that "
     "day&rsquo;s mileage. The words that were actually written, as texture.", a6_type),

    ("strava", "b1", "B1 &middot; Route Bloom",
     "110 routes recentered on their own starts and rotated to their day of year. "
     "Rotated and single-hue precisely so it cannot be mistaken for the Year "
     "Clock&rsquo;s bloom, which is neither.", b1_bloom),
    ("strava", "b2", "B2 &middot; Contour Field",
     "44 elevation profiles stacked and sorted by total gain, each opaque so the row "
     "in front occludes the one behind. Pure geography, zero map.", b2_contour),
    ("strava", "b3", "B3 &middot; Route Grid",
     "A specimen sheet, 8&times;6 square cells, one route each, colored by sport "
     "family. The poster at thumbnail scale.", b3_grid),
    ("strava", "b4", "B4 &middot; Signature Route",
     "The 4.4-mile loop out the front door, run more times than any other shape in "
     "the record. Everything else omitted.", b4_signature),
    ("strava", "b4b", "B4b &middot; Signature Route, every repeat",
     "The same loop with all of its siblings behind it on a common scale. The GPS "
     "wander between repeats becomes the texture.", b4b_signature),
    ("strava", "b5", "B5 &middot; Tangle",
     "150 routes laid head to tail as one unbroken line. Because most are loops, it "
     "knots around a centre instead of wandering off.", b5_tangle),
    ("strava", "b6", "B6 &middot; Sport Palette Bands",
     "Band widths are the five families&rsquo; shares; each is filled with a fragment "
     "of a real route from that sport. Works with no streams at all.", b6_bands),
]

# The 6x6 pairing matrix, primaries only — variants would make it 7x7 and the
# point of the matrix is constraint #4, not completeness.
PAIR_A = ["a1", "a2", "a3", "a4", "a5", "a6"]
PAIR_B = ["b1", "b2", "b3", "b4", "b5", "b6"]


def content(body):
    return ('<rect width="%d" height="%d" fill="%s"/>\n%s'
            % (W, H, paint("art-bg"), body))


def standalone(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'preserveAspectRatio="xMidYMid slice">%s%s</svg>'
            % (W, H, SVG_STYLE, content(body)))


PAGE_CSS = """
%s
*{box-sizing:border-box}
body{background:var(--art-bg);color:#c9d2de;margin:0;padding:40px 32px 90px;
  font:14px/1.6 'Geist',system-ui,sans-serif}
:root.light body{color:#39424f}
h1{font-size:27px;font-weight:700;letter-spacing:-.03em;margin:0 0 6px}
h2{font-size:13px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;
  margin:56px 0 18px;opacity:.6}
h3{font-size:16px;font-weight:600;margin:0 0 4px}
p.lede{max-width:76ch;opacity:.72;margin:0 0 4px}
.wrap{max-width:1180px;margin:0 auto}
.card{border:1px solid rgba(128,140,160,.28);border-radius:12px;padding:18px;
  margin:0 0 22px}
.blurb{opacity:.68;max-width:74ch;margin:0 0 14px;font-size:13px}
.pair{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}
.f640{width:640px;max-width:100%%}
.f240{width:240px;flex:none}
.cap{font:11px/1.5 'Geist Mono',ui-monospace,monospace;opacity:.5;
  letter-spacing:.06em;margin-top:6px}
svg.tile{display:block;width:100%%;height:auto;border-radius:8px;
  border:1px solid rgba(128,140,160,.22)}
.budget{font:11px/1.5 'Geist Mono',ui-monospace,monospace;letter-spacing:.04em}
.over{color:#f87171;font-weight:600}
.ok{opacity:.5}
.matrix{border-collapse:separate;border-spacing:10px;margin-top:8px}
.matrix th{font:11px/1.4 'Geist Mono',ui-monospace,monospace;font-weight:600;
  opacity:.6;letter-spacing:.08em;text-align:left;vertical-align:bottom}
.matrix td{padding:0}
.mcell{display:flex;gap:5px;width:238px}
.mcell svg{width:116px;border-radius:5px}
.scroll{overflow-x:auto;padding-bottom:8px}
.bar{position:fixed;right:22px;bottom:22px;display:flex;gap:8px;z-index:9}
.bar button{background:var(--art-bg);color:inherit;font:inherit;font-size:13px;
  border:1px solid rgba(128,140,160,.4);border-radius:999px;padding:8px 16px;
  cursor:pointer;box-shadow:0 6px 20px -8px rgba(0,0,0,.6)}
""" % PAGE_VARS


def build_page(rendered, sizes):
    """The sheet. Each artwork is inlined once as a <symbol> and instantiated by
    <use> everywhere it appears — otherwise the 6x6 matrix would carry 72 more
    copies of the artwork and the file would be several megabytes. CSS custom
    properties inherit through <use>, so the theme still reaches every instance.
    """
    syms = "".join('<symbol id="sym-%s" viewBox="0 0 %d %d">%s</symbol>'
                   % (slug, W, H, content(rendered[slug]))
                   for _, slug, _, _, _ in CONCEPTS)

    def tile(slug, cls):
        return ('<svg class="tile %s" viewBox="0 0 %d %d"><use href="#sym-%s"/></svg>'
                % (cls, W, H, slug))

    def card(side, slug, title, blurb):
        n = sizes[slug]
        over = n > BUDGET
        return """<div class="card">
  <h3>%s</h3>
  <p class="blurb">%s</p>
  <div class="pair">
    <div class="f640">%s<div class="cap">640 &times; 480 &mdash; the tile at desktop width</div></div>
    <div class="f240">%s<div class="cap">240 px &mdash; mobile</div></div>
  </div>
  <p class="budget %s">%s &nbsp;%s of 40 KB budget</p>
</div>""" % (title, blurb, tile(slug, "f"), tile(slug, "f"),
             "over" if over else "ok",
             "OVER BUDGET" if over else "within budget",
             "%.1f KB" % (n / 1024.0))

    def section(side, label):
        return "<h2>%s</h2>\n%s" % (label, "\n".join(
            card(s, slug, title, blurb)
            for s, slug, title, blurb, _ in CONCEPTS if s == side))

    head = ("<tr><th></th>"
            + "".join("<th>%s</th>" % s.upper() for s in PAIR_B) + "</tr>")
    body = "".join(
        "<tr><th>%s</th>%s</tr>"
        % (a.upper(), "".join('<td><div class="mcell">%s%s</div></td>'
                              % (tile(a, "m"), tile(b, "m")) for b in PAIR_B))
        for a in PAIR_A)

    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>landing tile art &mdash; twelve proofs</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;700&family=Geist+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>%s</style></head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">%s</svg>
<div class="wrap">
  <h1>Landing tile art &mdash; twelve directions</h1>
  <p class="lede">Every tile is authored 640&times;480, which is the real shape of
  <code>.tile-art-wrap</code> (4:3, <code>slice</code>) &mdash; a square artwork would lose
  12.5%% off the top and bottom. Judge the 240 px column as hard as the 640, and use the
  toggle: a color defined only in dark is how the light theme ships broken.</p>
  <p class="lede">The pairing matrix at the bottom is the one that actually matters.
  Constraint&nbsp;#4 is that the two tiles are distinguishable at a glance, and that is a
  property of the pair, not of either tile alone.</p>
%s
%s
  <h2>Pairings &mdash; college &times; strava at 116 px</h2>
  <div class="scroll"><table class="matrix">%s%s</table></div>
</div>
<div class="bar">
  <button type="button" id="t">Light / dark</button>
</div>
<script>
document.getElementById('t').addEventListener('click', function(){
  document.documentElement.classList.toggle('light');
});
</script>
</body></html>
""" % (PAGE_CSS, syms, section("college", "College Running Log &mdash; abstract / rhythmic"),
       section("strava", "Strava &mdash; literal / linear"), head, body)


def main():
    os.makedirs(OUT, exist_ok=True)
    print("loading...")
    college = load_college()
    acts = load_strava()
    tracks = {}
    for a in acts:
        t = track(a["id"], step=6)
        if t:
            tracks[a["id"]] = t
    alts = {}
    for a in acts:
        v = altitude(a["id"], 48)
        if v:
            alts[a["id"]] = v
    D = {"college": college, "acts": acts, "tracks": tracks, "alts": alts}
    print("  %d college rows (%d with miles), %d activities, %d tracks, %d profiles"
          % (len(college), sum(1 for r in college if r["mi"] > 0),
             len(acts), len(tracks), len(alts)))

    rendered, sizes = {}, {}
    for side, slug, title, _, fn in CONCEPTS:
        body = fn(D)
        svg = standalone(body)
        n = len(svg.encode("utf-8"))
        rendered[slug] = body
        sizes[slug] = n
        # newline="\n": Python's text mode would write CRLF on Windows, where
        # this is developed, and every regeneration would then churn the
        # committed proofs against git's LF normalization.
        with open(os.path.join(OUT, slug + ".svg"), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(svg)
        print("  %-4s %-8s %7.1f KB  %s"
              % (slug, side, n / 1024.0, "OVER BUDGET" if n > BUDGET else "ok"))

    p = os.path.join(OUT, "proofs.html")
    page = build_page(rendered, sizes)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print("wrote %s (%.0f KB)" % (p, len(page.encode("utf-8")) / 1024.0))


if __name__ == "__main__":
    main()
