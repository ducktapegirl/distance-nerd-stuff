"""Mt. Whitney — three developments of concept D, with landmarks and a registered map.

Builds on proofs.py (imported, not copied — same folder, same exploration) and adds the three
things concept D was asked to carry:

  1. landmarks along the profile, positioned from this activity's real Strava segment efforts;
  2. the GPS route drawn as the DESCENT ONLY and set below the profile, tied to it;
  3. profile and route at equal weight, the figures demoted to an accent.

    uv run python "Project Docs/Plans/strava-data/whitney/proofs_d.py"
    uv run python "Project Docs/Plans/strava-data/whitney/proofs_d.py" --png --dpi 300

Why the sheet turns portrait in D1 and D2
-----------------------------------------
Stacking the map under the profile fixes the map's height: the descent's bounding box is
5,234 x 3,476 m, so a full-measure map is 0.664 of its own width. At 11x14 landscape the
measure is 1,210 units, which makes the map 805 tall and leaves nothing for a profile. Turned
portrait the measure is 930, the map is 617 tall, and profile + map + type all fit. D3 keeps
the original landscape and pays for it by shrinking the map and giving up the shared measure.

Why the two views are tied by numerals and not by leader lines
--------------------------------------------------------------
A true cross-section — elevation plotted against easting, so a vertical line crosses both views
at the same place on the ground — is impossible for this route, and the track says so twice:

  * the descent backtracks 29% of its easting (the switchbacks fold back on themselves), so
    elevation-against-easting is multivalued and draws a tangle rather than a section;
  * summit to Trail Crest is 1.89 mi and 898 ft of descent inside 57 m of easting — 17.3% of
    the descent's distance in 1.2% of its width. A section would crush a fifth of the day,
    the Needles and Trail Crest included, into a vertical wall.

Leader lines between the two views were the next option and are also out: Trail Crest lies 59 m
WEST of the summit, because the final ridge runs north, so its tie-line crosses the summit's.
What is left, and what these three use, is a numbered mark in both views plus the two named
spans drawn heavier on both — so the correspondence is carried by the line itself.
"""

import argparse
import csv
import datetime as dt
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proofs as P                                          # noqa: E402
from proofs import (BG, INK, SERIF, SANS, HAIR, LIGHT, MED,  # noqa: E402
                    SUMMIT_FT, HIKER_GROUND, HIKER_FOOT,
                    art, art_anchor, art_width, douglas_peucker, esc, frame,
                    line, metres, poly, summit_mark, text, write)

W, H = 1100, 1400
# "Equal importance" is an optical judgement, not an arithmetic one. The profile is a short,
# taut line and the map is a long meander dispersed over twice the area, so at identical
# stroke the map reads lighter. It gets a 20% bump to sit level — the same kind of hand
# correction poster_40for40.py applies with GLYPH_OPTICAL.
PROF, MAPL = 3.0, 3.6
SPAN, MAP_SPAN = 6.0, 6.8   # the two named spans: 2x the line they sit on, in both views
TITLE, DATE = "Mt. Whitney", "OCTOBER 1, 2025"

# Set in place on the profile, a label gets one slot of cw/6 ~ 155 units, so the long names
# are shortened for that use only. The legend and this listing keep them in full.
SHORT = {"Whitney Portal": "WHITNEY PORTAL",
         "Lone Pine Lake Jct": "LONE PINE LAKE",
         "Outpost Camp": "OUTPOST CAMP",
         "Trail Camp": "TRAIL CAMP",
         "Trail Crest / JMT Jct": "TRAIL CREST",
         "Mount Whitney Summit": "WHITNEY SUMMIT"}


# ===================================================================== landmarks

def segment_efforts(act):
    """This activity's Strava segment efforts, located on the track.

    segment_efforts.csv carries no start/end index, but it does carry start_date_local and
    elapsed_time_s, and the stream carries t. That is enough to place every effort exactly.
    """
    start = dt.datetime.fromisoformat(act["start_date_local"])
    out = []
    path = os.path.join(P.DATA, "segment_efforts.csv")
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["activity_id"] != P.ACT_ID:
                continue
            t0 = (dt.datetime.fromisoformat(r["start_date_local"]) - start).total_seconds()
            t1 = t0 + float(r["elapsed_time_s"])
            out.append({"name": r["segment_name"],
                        "i0": nearest_t(act, t0), "i1": nearest_t(act, t1)})
    return out


def nearest_t(act, t):
    tv = act["_t"]
    lo, hi = 0, len(tv) - 1
    while lo < hi:                                  # tv is sorted; bisect by hand
        mid = (lo + hi) // 2
        if tv[mid] < t:
            lo = mid + 1
        else:
            hi = mid
    return max(0, min(lo, len(tv) - 1))


def seg(effs, frag, which=0):
    hits = [e for e in effs if frag.lower() in e["name"].lower()]
    if not hits:
        sys.exit("segment effort not found: " + frag)
    return hits[which]


def descend_to(act, ft):
    """First index on the descent at or below an elevation."""
    tgt = ft / P.M_TO_FT
    for i in range(act["_summit"], len(act["_alt"])):
        if act["_alt"][i] <= tgt:
            return i
    return len(act["_alt"]) - 1


def landmarks(act):
    """The eight landmarks, as (points, spans).

    Positions come from this activity's own segment efforts wherever a segment names the
    landmark, and otherwise from the published elevation found on the descent. Printed
    elevations are the published ones — they are facts about the places, not about the watch —
    and every one of them lands within 132 ft of the track's own reading, which on a profile
    spanning 6,146 ft is under 2% of its height and so invisible.
    """
    e = segment_efforts(act)
    n = len(act["_alt"]) - 1
    switch = seg(e, "99 Switchbacks down")            # the descent's own switchback effort
    crest = seg(e, "Trail Crest to Whitney Summit")   # recorded on the ascent
    camp = seg(e, "summit down to trail camp")
    lake = seg(e, "Lone Pine Lake to Trail head")

    pts = [
        (1, "Whitney Portal", "8,365 FT", n),
        (2, "Lone Pine Lake Jct", "9,960 FT", lake["i0"]),
        (3, "Outpost Camp", "10,360 FT", descend_to(act, 10360)),
        (4, "Trail Camp", "12,039 FT", camp["i1"]),
        (5, "Trail Crest / JMT Jct", "13,700 FT", descend_to(act, act["_alt"][crest["i0"]] * P.M_TO_FT)),
        (6, "Mount Whitney Summit", f"{SUMMIT_FT:,} FT", act["_summit"]),
    ]
    spans = [
        ("A", "The 97 Switchbacks", "12,000-13,400 FT", switch["i1"], switch["i0"]),
        ("B", "The Final Ridge & Needles", "13,700-14,400 FT",
         descend_to(act, act["_alt"][crest["i0"]] * P.M_TO_FT), act["_summit"]),
    ]
    return pts, spans


# ======================================================================== mappers
# One mapper per view, so a landmark and the line it sits on cannot drift apart: the drawn
# polyline and every mark on it come from the same function.

def profile_mapper(act, i0, i1, x, y, w, h):
    alt, d = act["_alt"], act["_dist"]
    seg_a = alt[i0:i1 + 1]
    a0, a1 = min(seg_a), max(seg_a)
    d0, d1 = d[i0], d[i1]
    rng = max(a1 - a0, 1e-9)
    span = max(d1 - d0, 1e-9)

    def at(i):
        return (x + (d[i] - d0) / span * w, y + h - (alt[i] - a0) / rng * h)
    return at


def route_mapper(act, i0, i1, x, y, w, h, fit="contain"):
    """fit="width" makes the map span exactly w, whatever height that costs — which is what
    D2 needs, since a contain-fit map would sit inset from the profile above it and quietly
    break the shared measure the design is built on."""
    m = metres(act["_pts"])
    sub = m[i0:i1 + 1]
    x0, x1 = min(p[0] for p in sub), max(p[0] for p in sub)
    y0, y1 = min(p[1] for p in sub), max(p[1] for p in sub)
    if fit == "width":
        k = w / max(x1 - x0, 1e-9)
    else:
        k = min(w / max(x1 - x0, 1e-9), h / max(y1 - y0, 1e-9))
    ox = x + (w - (x1 - x0) * k) / 2
    oy = y if fit == "width" else y + (h - (y1 - y0) * k) / 2

    def at(i):
        return (ox + (m[i][0] - x0) * k, oy + (y1 - m[i][1]) * k)
    return at, (x1 - x0) * k, (y1 - y0) * k


def trace(at, i0, i1, tol=1.1, step=1):
    pts = [at(i) for i in range(i0, i1 + 1, step)]
    return douglas_peucker(pts, tol)


# ==================================================================== annotation

def numeral(p, s, dx, dy, size=16, r=5.2):
    return (text(p[0] + dx, p[1] + dy, s, size, "middle", SANS, 0.5, 600)
            + f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{r}" fill="{BG}" '
              f'stroke="{INK}" stroke-width="2.4"/>')


def fanned_labels(items, x, cw, top, drop=34, size=11):
    """Landmark labels on evenly spaced slots, each tied back to its point by a leader.

    Three of the six landmarks fall within 50 units of a neighbour on the descent's measure
    (Outpost Camp and Lone Pine Lake are half a mile apart), so labels set directly under
    their own x collide however they are staggered. Even slots plus a two-segment leader is
    the standard fix and it keeps the correspondence explicit.

    items: [(px, name, elevation)] in left-to-right order.
    """
    out = []
    slot = cw / len(items)
    for k, (px, name, ft) in enumerate(items):
        sx = x + (k + 0.5) * slot
        out.append(line(px, top, px, top + drop, HAIR))
        out.append(line(px, top + drop, sx, top + drop + 16, HAIR))
        out.append(text(sx, top + drop + 34, name, size, "middle", SANS, 1.5))
        out.append(text(sx, top + drop + 50, ft, size, "middle", SANS, 1.5))
    return "".join(out)


def legend_rows(pts, spans, x, y, lead, size=14, gap=250):
    """Numbered list: key, name, elevation. Two columns if gap is given a second x."""
    out = []
    for k, (num, name, ft, _) in enumerate(pts):
        out.append(text(x, y + k * lead, str(num), size, "start", SANS, 0.5, 600))
        out.append(text(x + 22, y + k * lead, name, size, "start", SANS, 1.2))
        out.append(text(x + gap, y + k * lead, ft, size, "end", SANS, 1.2))
    for k, (key, name, ft, _, _) in enumerate(spans):
        yy = y + (len(pts) + k) * lead
        out.append(text(x, yy, key, size, "start", SANS, 0.5, 600))
        out.append(text(x + 22, yy, name, size, "start", SANS, 1.2))
        out.append(text(x + gap, yy, ft, size, "end", SANS, 1.2))
    return "".join(out)


def mile_ticks(act, i0, i1, at, base, every=5):
    """Distance ticks on the profile baseline — distance stays readable without hanging a
    mileage off every landmark, where published and recorded figures disagree."""
    out = []
    d0, d1 = act["_dist"][i0] * 0.000621371, act["_dist"][i1] * 0.000621371
    lo, hi = min(d0, d1), max(d0, d1)
    m = int(lo // every) * every
    while m <= hi:
        if lo <= m <= hi:
            j = min(range(min(i0, i1), max(i0, i1) + 1),
                    key=lambda k: abs(act["_dist"][k] * 0.000621371 - m))
            px = at(j)[0]
            out.append(line(px, base, px, base + 9, HAIR))
            out.append(text(px, base + 27, f"{m:.0f}", 12, "middle", SANS, 1.5))
        m += every
    return "".join(out)


# ======================================================================= designs

def design_d1(act):
    """D1 · SECTION — the whole day as a triangle, the descent limb annotated, map below."""
    side, cw = 85, W - 170
    n = len(act["_alt"]) - 1
    si = act["_summit"]
    pts, spans = landmarks(act)
    body = []

    base, ph = 470.0, 290.0
    pf = profile_mapper(act, 0, n, side, base - ph, cw, ph)
    body.append(poly(trace(pf, 0, n, 0.4, 2), PROF))
    body.append(line(side, base, side + cw, base, HAIR))
    body.append(mile_ticks(act, 0, n, pf, base))
    for key, _, _, ia, ib in spans:                       # the named spans, heavier
        body.append(poly(trace(pf, min(ia, ib), max(ia, ib), 0.3), SPAN))

    rt, rw, rh = route_mapper(act, si, n, side, 540.0, cw, 590.0)
    body.append(poly(trace(rt, si, n, 0.7), MAPL))
    for key, _, _, ia, ib in spans:
        body.append(poly(trace(rt, min(ia, ib), max(ia, ib), 0.4), MAP_SPAN))

    # every landmark marked in both views, and only in the descent limb of the profile —
    # the limb the map below actually draws
    for num, name, ft, i in pts:
        body.append(numeral(pf(i), str(num), 0, -17))
        body.append(numeral(rt(i), str(num), 17, 5, 14, 4.8))
    for key, _, _, ia, ib in spans:
        mid = (min(ia, ib) + max(ia, ib)) // 2
        body.append(numeral(pf(mid), key, 0, -18))
        body.append(numeral(rt(mid), key, -18, 5, 14, 4.8))

    hk = art("hikers_simple2.svg", HIKER_GROUND)
    fx = side + cw * 0.20
    fy = pf(min(range(0, si), key=lambda k: abs(pf(k)[0] - fx)))[1]
    body.append(art_anchor(hk, 118.0 / hk["h"], HIKER_FOOT, (fx, fy), LIGHT))

    body.append(text(side, 108, TITLE, 62, "start", SERIF, -1))
    body.append(text(side, 148, DATE, 18, "start", SANS, 5))
    body.append(text(side + cw, 148, "MILES ALONG THE TRAIL", 13, "end", SANS, 3))
    body.append(legend_rows(pts, spans, side, 1188, 24, 13, 360))
    body.append(text(side + cw, 1188, f"{act['_mi']:.1f} MILES", 13, "end", SANS, 2))
    body.append(text(side + cw, 1212, f"{act['_ft']:,.0f} FT GAINED", 13, "end", SANS, 2))
    body.append(text(side + cw, 1236, "14 H 58 M", 13, "end", SANS, 2))
    body.append(text(side + cw, 1284, "MAP: DESCENT ONLY", 12, "end", SANS, 3))
    return frame("".join(body), W, H), "full profile, descent map, 6.0x"


def design_d2(act):
    """D2 · DESCENT — profile and map both the descent, one measure, direct registration."""
    side, cw = 85, W - 170
    n = len(act["_alt"]) - 1
    si = act["_summit"]
    pts, spans = landmarks(act)
    body = []

    base, ph = 460.0, 270.0
    pf = profile_mapper(act, si, n, side, base - ph, cw, ph)
    body.append(poly(trace(pf, si, n, 0.4), PROF))
    body.append(line(side, base, side + cw, base, HAIR))
    body.append(mile_ticks(act, si, n, pf, base))
    for key, _, _, ia, ib in spans:
        body.append(poly(trace(pf, min(ia, ib), max(ia, ib), 0.3), SPAN))

    # Both views on the descent's own measure, so a landmark sits at nearly the same place
    # across in each and is named in place rather than in a legend.
    for num, name, ft, i in pts:
        body.append(numeral(pf(i), str(num), 0, -17))
    for key, _, _, ia, ib in spans:
        body.append(numeral(pf((min(ia, ib) + max(ia, ib)) // 2), key, 0, -18))
    body.append(fanned_labels([(pf(i)[0], SHORT[name], ft) for num, name, ft, i
                               in sorted(pts, key=lambda r: pf(r[3])[0])],
                              side, cw, base + 14))

    rt, rw, rh = route_mapper(act, si, n, side, 588.0, cw, 0, "width")
    body.append(poly(trace(rt, si, n, 0.7), MAPL))
    for key, _, _, ia, ib in spans:
        body.append(poly(trace(rt, min(ia, ib), max(ia, ib), 0.4), MAP_SPAN))
    for num, name, ft, i in pts:
        body.append(numeral(rt(i), str(num), 17, 5, 14, 4.8))
    for key, _, _, ia, ib in spans:
        body.append(numeral(rt((min(ia, ib) + max(ia, ib)) // 2), key, -18, 5, 14, 4.8))

    body.append(text(side, 108, TITLE, 62, "start", SERIF, -1))
    body.append(text(side, 148, DATE, 18, "start", SANS, 5))
    body.append(text(side + cw, 148, "THE DESCENT · 10.9 MILES", 13, "end", SANS, 3))
    for k, (key, name, ft, _, _) in enumerate(spans):
        body.append(text(side, 1252 + k * 24, key, 13, "start", SANS, 0.5, 600))
        body.append(text(side + 20, 1252 + k * 24, f"{name}  ·  {ft}", 13, "start", SANS, 1.4))
    body.append(text(side + cw, 1252, f"{act['_mi']:.1f} MI ROUND TRIP", 13, "end", SANS, 2))
    body.append(text(side + cw, 1276, f"{act['_ft']:,.0f} FT GAINED", 13, "end", SANS, 2))

    # the figures demoted to an accent, in the empty ground above the falling profile
    hk = art("hikers_simple2.svg", HIKER_GROUND)
    body.append(art_anchor(hk, 104.0 / hk["h"], HIKER_FOOT, (side + cw * 0.60, 268.0), LIGHT))
    return frame("".join(body), W, H), "descent profile + descent map, one measure"


def design_d3(act):
    """D3 · FIELD NOTE — the original landscape sheet, map inset, landmarks in a column."""
    w, h = 1400, 1100
    side, cw = 95, 1400 - 190
    n = len(act["_alt"]) - 1
    si = act["_summit"]
    pts, spans = landmarks(act)
    body = []

    base, ph = 530.0, 270.0
    pf = profile_mapper(act, 0, n, side, base - ph, cw, ph)
    body.append(poly(trace(pf, 0, n, 0.4, 2), PROF))
    body.append(line(side, base, side + cw, base, HAIR))
    body.append(mile_ticks(act, 0, n, pf, base))
    for key, _, _, ia, ib in spans:
        body.append(poly(trace(pf, min(ia, ib), max(ia, ib), 0.3), SPAN))
    for num, name, ft, i in pts:
        body.append(numeral(pf(i), str(num), 0, -16))
    for key, _, _, ia, ib in spans:
        body.append(numeral(pf((min(ia, ib) + max(ia, ib)) // 2), key, 0, -17))

    mw = 700.0
    rt, rw, rh = route_mapper(act, si, n, side, 600.0, mw, 466.0)
    body.append(poly(trace(rt, si, n, 0.7), MAPL))
    for key, _, _, ia, ib in spans:
        body.append(poly(trace(rt, min(ia, ib), max(ia, ib), 0.4), MAP_SPAN))
    for num, name, ft, i in pts:
        body.append(numeral(rt(i), str(num), 15, 5, 13))
    for key, _, _, ia, ib in spans:
        body.append(numeral(rt((min(ia, ib) + max(ia, ib)) // 2), key, -16, 5, 13))

    body.append(text(side, 150, TITLE, 68, "start", SERIF, -1))
    body.append(text(side, 194, DATE, 18, "start", SANS, 5))
    body.append(text(side + cw, 194, "MILES ALONG THE TRAIL", 13, "end", SANS, 3))
    lx = side + mw + 90
    body.append(text(lx, 626, "ALONG THE WAY", 13, "start", SANS, 3.5))
    body.append(line(lx, 640, side + cw, 640, HAIR))
    body.append(legend_rows(pts, spans, lx, 672, 30, 14, side + cw - lx))
    body.append(text(lx, 916, f"{act['_mi']:.1f} MILES  ·  {act['_ft']:,.0f} FT GAINED",
                     14, "start", SANS, 1.6))
    body.append(text(lx, 942, "14 H 58 M  ·  MAP IS THE DESCENT", 14, "start", SANS, 1.6))

    hk = art("hikers_simple2.svg")
    body.append(art_width(hk, lx, 972, 100, LIGHT)[0])
    return frame("".join(body), w, h), "landscape kept, map inset, 5.6x"


DESIGNS = [
    ("D1", "Section", design_d1, W, H,
     "The whole day kept as its triangle, with the descent limb carrying the landmarks and the "
     "descent map directly beneath it. Closest to the original D, and the only one of the three "
     "where the ascent and descent are both visible — but the six landmarks are squeezed into "
     "the right half of the profile, so they need the legend at the foot to be readable."),
    ("D2", "Descent", design_d2, W, H,
     "Profile and map are both the descent and span one measure, so the landmarks land in the "
     "same neighbourhood across both views — within 1.2 in at worst, at Trail Camp, where the "
     "switchbacks pack trail distance into very little easting. Close enough to scan between, "
     "not registration: the numerals still do the tying. Named in place, so no legend, which "
     "makes it the most legible of the three and the truest to “equal importance” — at the "
     "cost of the triangle, since the day now reads as one long drop rather than an "
     "out-and-back."),
    ("D3", "Field note", design_d3, 1400, 1100,
     "The original 14x11 landscape sheet kept, which forces the map down to 700 units and off "
     "the profile's measure — so the numerals do all the tying and the landmarks move into a "
     "column at the right. Roomiest for type; weakest registration of the three."),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--png", action="store_true")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()

    act = P.load()
    pts, spans = landmarks(act)
    print(f"{act['name']}  ·  {len(segment_efforts(act))} segment efforts on file",
          file=sys.stderr)
    for num, name, ft, i in pts:
        print(f"  {num}  {name:24s} {ft:>10s}   {act['_dist'][i] * 0.000621371:6.2f} mi   "
              f"track {act['_alt'][i] * P.M_TO_FT:,.0f} ft", file=sys.stderr)
    for key, name, ft, ia, ib in spans:
        print(f"  {key}  {name:24s} {ft:>10s}   "
              f"{act['_dist'][min(ia, ib)] * 0.000621371:6.2f} - "
              f"{act['_dist'][max(ia, ib)] * 0.000621371:.2f} mi", file=sys.stderr)

    # How far a landmark moves between the two views in D2, where both span one measure.
    # Reported rather than assumed: the design's claim is only as good as this number.
    si, n = act["_summit"], len(act["_alt"]) - 1
    pf = profile_mapper(act, si, n, 85, 190, 930, 270)
    rt, _, _ = route_mapper(act, si, n, 85, 588, 930, 0, "width")
    worst = max((abs(pf(i)[0] - rt(i)[0]), name) for _, name, _, i in pts)
    print(f"  D2 profile-to-map divergence: worst {worst[0]:.0f} units "
          f"({worst[0] / 100:.2f} in) at {worst[1]}", file=sys.stderr)

    cards = []
    for key, name, fn, w, h, blurb in DESIGNS:
        svg, note = fn(act)
        path = os.path.join(args.out, f"proof_{key}.svg")
        write(path, svg)
        print(f"  {key} · {name:10s} {w}x{h}  {note}", file=sys.stderr)
        if args.png:
            P.rasterise(path, os.path.join(args.out, f"proof_{key}.png"), w, h, args.dpi)
        cards.append(f'<figure><div class="p">{svg}</div><figcaption><b>{key} · {name}</b> '
                     f'<span class=n>{esc(note)}</span><br>{esc(blurb)}</figcaption></figure>')

    html = ("<!doctype html><meta charset=utf-8><title>Whitney — concept D developed</title>"
            "<style>body{margin:0;padding:28px;background:#e9e4da;"
            "font:15px/1.5 -apple-system,Segoe UI,Helvetica,sans-serif;color:#33312e}"
            "h1{font-weight:500;margin:0 0 4px;font-size:22px}p.sub{margin:0 0 22px;color:#6d675e}"
            ".g{display:grid;grid-template-columns:repeat(2,1fr);gap:30px}figure{margin:0}"
            ".p svg{width:100%;height:auto;display:block;box-shadow:0 8px 30px rgba(0,0,0,.25)}"
            "figcaption{margin-top:10px;max-width:64ch}.n{color:#6d675e;font-size:13px}</style>"
            "<h1>Mt. Whitney · concept D developed — landmarks, and the descent map</h1>"
            "<p class=sub>Landmarks positioned from this activity's own Strava segment efforts "
            "&middot; map is the descent only &middot; the two named spans are drawn heavier in "
            "both views</p><div class=g>" + "".join(cards) + "</div>")
    write(os.path.join(args.out, "proofs_d.html"), html)
    print("wrote " + os.path.join(args.out, "proofs_d.html"), file=sys.stderr)


if __name__ == "__main__":
    main()
