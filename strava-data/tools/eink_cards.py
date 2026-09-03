"""eink_cards.py -- prototype contact sheet of Strava "cards" for a reTerminal E1005
e-paper display (800x650, 4-level greyscale) driven by SenseCraft HMI.

This is a PROTOTYPE / idea-picker, not a build step: it renders ~17 candidate views
from the real data in strava-data/data/ (and running-log/running_log.csv), snaps every
pixel to the panel's four grey levels, and tiles them into one contact sheet so the
owner can pick favourites before a real feed builder is written.

Run from the repo root:
    uv run python strava-data/tools/eink_cards.py [--out DIR]

Output (default: "Project Docs/Plans/strava-data/eink-cards/"):
    contact-sheet.png       all cards, 3-across at 50%, captioned
    cards/<nn>-<id>.png     one 800x650 mode-L PNG per card

Needs Pillow (dev dependency). Imports the strava dashboard package only for its
data loaders and a few pure helpers (RDP, away-trip clustering).
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_STRAVA = os.path.normpath(os.path.join(_HERE, ".."))
_ROOT = os.path.normpath(os.path.join(_STRAVA, ".."))
for p in (_ROOT, _STRAVA):
    if p not in sys.path:
        sys.path.insert(0, p)

from dashboard.config import DATA_DIR, KM_TO_MI  # noqa: E402
from dashboard.data import load_activities, load_segments, load_segment_efforts  # noqa: E402
from dashboard.charts_places import _rdp, _passport_data  # noqa: E402

RUNLOG_CSV = os.path.join(_ROOT, "running-log", "running_log.csv")
DEFAULT_OUT = os.path.join(_ROOT, "Project Docs", "Plans", "strava-data", "eink-cards")

# ---------------------------------------------------------------- panel spec
W, H = 800, 650
BLACK, DARK, LIGHT, WHITE = 0, 85, 170, 255
LEVELS = (BLACK, DARK, LIGHT, WHITE)
M = 28  # outer margin

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
_FONT_FILES = {
    ("sans", False): "DejaVuSans.ttf",
    ("sans", True): "DejaVuSans-Bold.ttf",
    ("mono", False): "DejaVuSansMono.ttf",
    ("mono", True): "DejaVuSansMono-Bold.ttf",
}
_font_cache = {}


def font(size, bold=True, mono=False):
    key = (size, bold, mono)
    if key not in _font_cache:
        fn = os.path.join(FONT_DIR, _FONT_FILES[("mono" if mono else "sans", bold)])
        try:
            _font_cache[key] = ImageFont.truetype(fn, size)
        except OSError:
            print(f"warn: font {fn} missing; using Pillow default", file=sys.stderr)
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


M_TO_FT = 3.28084


def mf(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def f_to_c(c):
    return c * 9 / 5 + 32


def pace_str(kmh):
    """min/mi as M:SS from km/h."""
    if not kmh:
        return "--"
    mpm = 60.0 / (kmh * KM_TO_MI)
    m = int(mpm)
    s = int(round((mpm - m) * 60))
    if s == 60:
        m, s = m + 1, 0
    return f"{m}:{s:02d}"


def hms(minutes):
    s = int(round(minutes * 60))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def secs_str(s):
    s = int(s)
    m, r = divmod(s, 60)
    return f"{m}:{r:02d}" if m else f"{r}s"


def pdate(s):
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


RUN_TYPES = ("Run", "TrailRun")
BIKE_TYPES = ("MountainBikeRide", "Ride", "EBikeRide")

# ---------------------------------------------------------------- drawing kit


def new_card():
    img = Image.new("L", (W, H), WHITE)
    return img, ImageDraw.Draw(img)


def quantize(img):
    """Snap every pixel to the nearest of the four panel levels."""
    lut = []
    for v in range(256):
        lut.append(min(LEVELS, key=lambda l: abs(l - v)))
    return img.point(lut)


def tw(d, s, f):
    return d.textlength(s, font=f)


def fit(d, s, f, maxw, ell="..."):
    """Truncate s with an ellipsis so it fits maxw."""
    if tw(d, s, f) <= maxw:
        return s
    while s and tw(d, s + ell, f) > maxw:
        s = s[:-1]
    return s.rstrip() + ell


def text(d, xy, s, size=24, fill=BLACK, bold=True, mono=False, anchor="la", maxw=None):
    f = font(size, bold, mono)
    if maxw:
        s = fit(d, s, f, maxw)
    d.text(xy, s, font=f, fill=fill, anchor=anchor)
    return tw(d, s, f)


def wrap(d, s, f, maxw, max_lines=3):
    words = s.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tw(d, t, f) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(lines)) < len(s):
        lines[-1] = fit(d, lines[-1] + " " + " ".join(words[len(" ".join(lines).split()):]), f, maxw)
    return lines


def header(d, title, kicker=None, right=None):
    """Top band: black bar with white title; optional grey kicker above."""
    y = M
    if kicker:
        text(d, (M, y), kicker.upper(), 18, DARK, bold=True)
        y += 26
    d.rectangle([M, y, W - M, y + 56], fill=BLACK)
    text(d, (M + 14, y + 28), title, 30, WHITE, anchor="lm", maxw=W - 2 * M - 28 - (200 if right else 0))
    if right:
        text(d, (W - M - 14, y + 28), right, 22, WHITE, anchor="rm")
    return y + 56


def footer(d, s, y=None):
    y = H - M - 12 if y is None else y
    d.line([M, y - 18, W - M, y - 18], fill=LIGHT, width=2)
    text(d, (M, y), s, 19, DARK, bold=False, anchor="lm", maxw=W - 2 * M)


def hero(d, cx, y, number, label, size=120, unit=None):
    f = font(size, True)
    numw = tw(d, number, f)
    unitw = tw(d, unit, font(40, True)) + 12 if unit else 0
    x0 = cx - (numw + unitw) / 2
    d.text((x0, y), number, font=f, fill=BLACK, anchor="la")
    if unit:
        d.text((x0 + numw + 12, y + size - 40), unit, font=font(40, True), fill=DARK, anchor="la")
    text(d, (cx, y + size + 14), label, 24, DARK, bold=False, anchor="ma")
    return y + size + 44


def hatch(d, box, step=8, fill=DARK, width=2):
    x0, y0, x1, y1 = box
    for k in range(int(x0 - (y1 - y0)), int(x1), step):
        d.line([k, y1, k + (y1 - y0), y0], fill=fill, width=width)


def hatched_rect(img, box, step=8, fill=DARK):
    """Hatch clipped to box, via a temp mask."""
    x0, y0, x1, y1 = [int(v) for v in box]
    if x1 <= x0 or y1 <= y0:
        return
    tmp = Image.new("L", (x1 - x0, y1 - y0), WHITE)
    hatch(ImageDraw.Draw(tmp), (0, 0, x1 - x0, y1 - y0), step, fill)
    img.paste(tmp, (x0, y0))


def progress_bar(d, box, frac, outline=BLACK, fill=BLACK, track=LIGHT):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=track, outline=outline, width=3)
    fx = x0 + (x1 - x0) * max(0.0, min(1.0, frac))
    if fx > x0 + 3:
        d.rectangle([x0, y0, fx, y1], fill=fill)
    return fx


def stat_tile(d, box, num, label, icon=None):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=WHITE, outline=BLACK, width=3)
    if icon:
        icon(d, x0 + 34, y0 + 34, 44, BLACK)
    text(d, (x0 + 18, y1 - 16), label, 19, DARK, bold=False, anchor="ld", maxw=x1 - x0 - 36)
    text(d, (x1 - 18, y0 + (y1 - y0) / 2 - 4), num, 44, BLACK, anchor="rm", maxw=x1 - x0 - 36)


def sparkline(d, box, vals, lo=None, hi=None, invert=False, width=3):
    x0, y0, x1, y1 = box
    if len(vals) < 2:
        return
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    rng = (hi - lo) or 1.0
    pts = []
    for i, v in enumerate(vals):
        x = x0 + (x1 - x0) * i / (len(vals) - 1)
        t = (v - lo) / rng
        y = y0 + (y1 - y0) * (t if invert else (1 - t))
        pts.append((x, y))
    d.line(pts, fill=BLACK, width=width, joint="curve")
    for p in pts:
        d.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=WHITE, outline=BLACK, width=2)
    lx, ly = pts[-1]
    d.ellipse([lx - 7, ly - 7, lx + 7, ly + 7], fill=BLACK)


def gauge(d, cx, cy, r, frac, bands, label_lo="", label_hi=""):
    """Half-dial gauge. bands: [(f0,f1,fill)] fractions 0..1 across 180deg."""
    for f0, f1, fillv in bands:
        a0 = 180 + 180 * f0
        a1 = 180 + 180 * f1
        d.pieslice([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=fillv)
    d.pieslice([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62], 180, 360, fill=WHITE)
    d.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=BLACK, width=3)
    d.arc([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62], 180, 360, fill=BLACK, width=3)
    ang = math.radians(180 + 180 * max(0, min(1, frac)))
    nx, ny = cx + math.cos(ang) * r * 0.92, cy + math.sin(ang) * r * 0.92
    px, py = math.cos(ang + math.pi / 2) * 7, math.sin(ang + math.pi / 2) * 7
    d.polygon([(cx + px, cy + py), (cx - px, cy - py), (nx, ny)], fill=BLACK)
    d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=BLACK)
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=WHITE)
    if label_lo:
        text(d, (cx - r, cy + 10), label_lo, 18, DARK, bold=False, anchor="la")
    if label_hi:
        text(d, (cx + r, cy + 10), label_hi, 18, DARK, bold=False, anchor="ra")


def stamp(d, cx, cy, r, title, sub=None, sub2=None, dashed=True):
    """Circular passport-stamp frame with dotted border."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=4)
    if dashed:
        n = int(2 * math.pi * (r - 12) / 14)
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = cx + math.cos(a) * (r - 12), cy + math.sin(a) * (r - 12)
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=BLACK)
    lines = wrap(d, title, font(22, True), 2 * r - 50, 2)
    y = cy - 12 * len(lines) - (12 if sub else 0)
    for ln in lines:
        text(d, (cx, y), ln, 22, BLACK, anchor="ma")
        y += 26
    if sub:
        text(d, (cx, y + 2), sub, 17, DARK, bold=False, anchor="ma", maxw=2 * r - 50)
        y += 22
    if sub2:
        text(d, (cx, y + 2), sub2, 17, DARK, bold=False, anchor="ma", maxw=2 * r - 50)


# ---------------------------------------------------------------- icons
# All icons: (d, cx, cy, size, fill) -- geometric silhouettes sized to `size` px.


def _sc(cx, cy, s, pts):
    """Scale unit-square points (0..1) to a size-s box centred on cx,cy."""
    return [(cx + (px - 0.5) * s, cy + (py - 0.5) * s) for px, py in pts]


def ic_run(d, cx, cy, s, fill=BLACK):
    w = max(3, int(s * 0.12))
    d.ellipse(_sc(cx, cy, s, [(0.62, 0.05), (0.82, 0.25)]), fill=fill)          # head
    d.line(_sc(cx, cy, s, [(0.68, 0.28), (0.45, 0.58)]), fill=fill, width=w)      # torso
    d.line(_sc(cx, cy, s, [(0.68, 0.32), (0.90, 0.48)]), fill=fill, width=w)      # arm back
    d.line(_sc(cx, cy, s, [(0.66, 0.36), (0.42, 0.30), (0.30, 0.44)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.45, 0.58), (0.20, 0.72), (0.10, 0.95)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.45, 0.58), (0.70, 0.70), (0.66, 0.95)]), fill=fill, width=w, joint="curve")


def ic_bike(d, cx, cy, s, fill=BLACK):
    w = max(3, int(s * 0.09))
    r = s * 0.22
    for wx in (0.24, 0.76):
        x, y = cx + (wx - 0.5) * s, cy + 0.2 * s
        d.ellipse([x - r, y - r, x + r, y + r], outline=fill, width=w)
        for k in range(0, 360, 45):
            a = math.radians(k)
            d.line([x, y, x + math.cos(a) * (r - w), y + math.sin(a) * (r - w)], fill=fill, width=2)
    p = _sc(cx, cy, s, [(0.24, 0.70), (0.45, 0.35), (0.70, 0.35), (0.76, 0.70), (0.52, 0.70), (0.45, 0.35)])
    d.line(p, fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.70, 0.35), (0.62, 0.15), (0.78, 0.13)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.45, 0.35), (0.38, 0.22), (0.52, 0.20)]), fill=fill, width=w)


def ic_hike(d, cx, cy, s, fill=BLACK):
    w = max(3, int(s * 0.12))
    d.ellipse(_sc(cx, cy, s, [(0.40, 0.04), (0.60, 0.24)]), fill=fill)
    d.line(_sc(cx, cy, s, [(0.50, 0.26), (0.48, 0.58)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.48, 0.58), (0.30, 0.78), (0.28, 0.96)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.48, 0.58), (0.66, 0.74), (0.72, 0.96)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.50, 0.34), (0.74, 0.40), (0.80, 0.96)]), fill=fill, width=max(2, w - 1))
    d.rectangle(_sc(cx, cy, s, [(0.30, 0.30), (0.46, 0.50)]), fill=fill)


def ic_climb(d, cx, cy, s, fill=BLACK):
    w = max(3, int(s * 0.11))
    d.polygon(_sc(cx, cy, s, [(0.0, 1.0), (0.55, 0.0), (0.75, 0.0), (0.75, 1.0)]), fill=LIGHT)
    d.ellipse(_sc(cx, cy, s, [(0.36, 0.28), (0.54, 0.46)]), fill=fill)
    d.line(_sc(cx, cy, s, [(0.45, 0.48), (0.42, 0.72)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.45, 0.52), (0.62, 0.30), (0.66, 0.12)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.45, 0.56), (0.26, 0.60)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.42, 0.72), (0.28, 0.84), (0.30, 0.98)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.42, 0.72), (0.60, 0.80)]), fill=fill, width=w)


def ic_paddle(d, cx, cy, s, fill=BLACK):
    d.ellipse(_sc(cx, cy, s, [(0.25, 0.05), (0.75, 0.60)]), fill=fill)
    d.line(_sc(cx, cy, s, [(0.50, 0.58), (0.50, 0.95)]), fill=fill, width=max(4, int(s * 0.16)))
    d.ellipse(_sc(cx, cy, s, [(0.78, 0.62), (0.98, 0.82)]), outline=fill, width=3)


def ic_weights(d, cx, cy, s, fill=BLACK):
    d.line(_sc(cx, cy, s, [(0.15, 0.5), (0.85, 0.5)]), fill=fill, width=max(4, int(s * 0.12)))
    for x in (0.12, 0.24, 0.76, 0.88):
        d.rectangle(_sc(cx, cy, s, [(x - 0.06, 0.28), (x + 0.06, 0.72)]), fill=fill)


def ic_ski(d, cx, cy, s, fill=BLACK):
    w = max(3, int(s * 0.11))
    d.ellipse(_sc(cx, cy, s, [(0.44, 0.06), (0.62, 0.24)]), fill=fill)
    d.line(_sc(cx, cy, s, [(0.52, 0.26), (0.42, 0.52), (0.52, 0.72)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.52, 0.72), (0.34, 0.80)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.05, 0.95), (0.95, 0.72)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.30, 0.42), (0.12, 0.80)]), fill=fill, width=max(2, w - 2))
    d.line(_sc(cx, cy, s, [(0.62, 0.40), (0.86, 0.60)]), fill=fill, width=max(2, w - 2))


def ic_star(d, cx, cy, s, fill=BLACK):
    pts = []
    for i in range(10):
        r = s * (0.5 if i % 2 == 0 else 0.22)
        a = math.radians(-90 + i * 36)
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.polygon(pts, fill=fill)


def ic_walk(d, cx, cy, s, fill=BLACK):
    w = max(3, int(s * 0.12))
    d.ellipse(_sc(cx, cy, s, [(0.42, 0.04), (0.60, 0.22)]), fill=fill)
    d.line(_sc(cx, cy, s, [(0.51, 0.24), (0.50, 0.56)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.50, 0.56), (0.36, 0.76), (0.38, 0.96)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.50, 0.56), (0.64, 0.74), (0.70, 0.96)]), fill=fill, width=w, joint="curve")
    d.line(_sc(cx, cy, s, [(0.51, 0.30), (0.34, 0.48)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.51, 0.30), (0.68, 0.46)]), fill=fill, width=w)


SPORT_ICON = {
    "Run": ic_run, "TrailRun": ic_run, "MountainBikeRide": ic_bike, "Ride": ic_bike,
    "EBikeRide": ic_bike, "Hike": ic_hike, "Walk": ic_walk, "RockClimbing": ic_climb,
    "Pickleball": ic_paddle, "WeightTraining": ic_weights, "AlpineSki": ic_ski,
    "NordicSki": ic_ski, "Snowboard": ic_ski,
}


def sport_icon(sport):
    return SPORT_ICON.get(sport, ic_star)


def ic_heart(d, cx, cy, s, fill=BLACK):
    r = s * 0.26
    d.ellipse([cx - s * 0.5, cy - s * 0.42, cx - s * 0.5 + 2 * r, cy - s * 0.42 + 2 * r], fill=fill)
    d.ellipse([cx + s * 0.5 - 2 * r, cy - s * 0.42, cx + s * 0.5, cy - s * 0.42 + 2 * r], fill=fill)
    d.polygon([(cx - s * 0.49, cy - s * 0.10), (cx + s * 0.49, cy - s * 0.10), (cx, cy + s * 0.5)], fill=fill)


def _teardrop(cx, cy, s, top, bot, halfw):
    """Flame-ish outline: pointed top, round bottom."""
    pts = [(cx, cy + (top - 0.5) * s)]
    for i in range(1, 12):
        t = i / 12
        yy = top + (bot - top) * t
        ww = halfw * math.sin(t * math.pi * 0.85) * s
        pts.append((cx + ww, cy + (yy - 0.5) * s))
    pts.append((cx, cy + (bot - 0.5) * s))
    for i in range(11, 0, -1):
        t = i / 12
        yy = top + (bot - top) * t
        ww = halfw * math.sin(t * math.pi * 0.85) * s
        pts.append((cx - ww, cy + (yy - 0.5) * s))
    return pts


def ic_flame(d, cx, cy, s, fill=BLACK):
    d.polygon(_teardrop(cx, cy, s, 0.0, 1.0, 0.44), fill=fill)
    # side lick
    d.polygon(_teardrop(cx + s * 0.22, cy + s * 0.12, s * 0.6, 0.0, 1.0, 0.44), fill=fill)
    d.polygon(_teardrop(cx, cy + s * 0.12, s * 0.5, 0.0, 1.0, 0.40), fill=WHITE)


def ic_mountain(d, cx, cy, s, fill=BLACK):
    d.polygon(_sc(cx, cy, s, [(0.0, 0.95), (0.35, 0.25), (0.55, 0.55), (0.68, 0.40), (1.0, 0.95)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.35, 0.25), (0.28, 0.40), (0.35, 0.36), (0.42, 0.42), (0.47, 0.43)]), fill=WHITE)


def ic_trophy(d, cx, cy, s, fill=BLACK):
    d.polygon(_sc(cx, cy, s, [(0.22, 0.05), (0.78, 0.05), (0.72, 0.50), (0.5, 0.65), (0.28, 0.50)]), fill=fill)
    d.arc(_sc(cx, cy, s, [(0.02, 0.05), (0.32, 0.45)]), 60, 270, fill=fill, width=4)
    d.arc(_sc(cx, cy, s, [(0.68, 0.05), (0.98, 0.45)]), 270, 120, fill=fill, width=4)
    d.rectangle(_sc(cx, cy, s, [(0.45, 0.62), (0.55, 0.80)]), fill=fill)
    d.rectangle(_sc(cx, cy, s, [(0.28, 0.80), (0.72, 0.95)]), fill=fill)


def ic_shoe(d, cx, cy, s, fill=BLACK):
    # heel-collar at left, toe box at right, sole underneath
    d.polygon(_sc(cx, cy, s, [(0.04, 0.30), (0.26, 0.28), (0.34, 0.44), (0.52, 0.50), (0.74, 0.56),
                              (0.98, 0.68), (0.98, 0.78), (0.04, 0.78)]), fill=fill)
    d.rectangle(_sc(cx, cy, s, [(0.04, 0.78), (0.98, 0.92)]), fill=DARK)
    for k in range(5):
        x = 0.10 + k * 0.18
        d.rectangle(_sc(cx, cy, s, [(x, 0.80), (x + 0.08, 0.92)]), fill=fill)
    d.line(_sc(cx, cy, s, [(0.34, 0.40), (0.48, 0.58)]), fill=WHITE, width=3)
    d.line(_sc(cx, cy, s, [(0.44, 0.36), (0.58, 0.54)]), fill=WHITE, width=3)
    d.line(_sc(cx, cy, s, [(0.54, 0.40), (0.66, 0.56)]), fill=WHITE, width=3)


def ic_pin(d, cx, cy, s, fill=BLACK):
    d.ellipse(_sc(cx, cy, s, [(0.18, 0.0), (0.82, 0.64)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.22, 0.45), (0.78, 0.45), (0.5, 1.0)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.37, 0.19), (0.63, 0.45)]), fill=WHITE)


def ic_medal(d, cx, cy, s, fill=BLACK):
    d.polygon(_sc(cx, cy, s, [(0.30, 0.0), (0.50, 0.42), (0.70, 0.0), (0.84, 0.0), (0.58, 0.50), (0.42, 0.50), (0.16, 0.0)]), fill=DARK)
    d.ellipse(_sc(cx, cy, s, [(0.22, 0.42), (0.78, 0.98)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.32, 0.52), (0.68, 0.88)]), outline=WHITE, width=3)


def ic_arrow(d, cx, cy, s, direction, fill=BLACK):
    """direction: 'up', 'down', 'flat'."""
    w = max(3, int(s * 0.14))
    if direction == "flat":
        d.line([cx - s * 0.45, cy, cx + s * 0.45, cy], fill=fill, width=w)
        d.polygon([(cx + s * 0.5, cy), (cx + s * 0.2, cy - s * 0.25), (cx + s * 0.2, cy + s * 0.25)], fill=fill)
        return
    sgn = -1 if direction == "up" else 1
    d.line([cx, cy - sgn * s * 0.45, cx, cy + sgn * s * 0.45], fill=fill, width=w)
    d.polygon([(cx, cy + sgn * s * 0.5), (cx - s * 0.3, cy + sgn * s * 0.15), (cx + s * 0.3, cy + sgn * s * 0.15)], fill=fill)


def ic_thermo(d, cx, cy, s, fill=BLACK):
    d.rounded_rectangle(_sc(cx, cy, s, [(0.38, 0.02), (0.62, 0.66)]), radius=int(s * 0.12), outline=fill, width=3)
    d.ellipse(_sc(cx, cy, s, [(0.25, 0.58), (0.75, 1.0)]), fill=fill)
    d.rectangle(_sc(cx, cy, s, [(0.45, 0.30), (0.55, 0.70)]), fill=fill)


def ic_kudos(d, cx, cy, s, fill=BLACK):
    d.rectangle(_sc(cx, cy, s, [(0.05, 0.45), (0.25, 0.95)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.28, 0.45), (0.50, 0.40), (0.42, 0.08), (0.55, 0.05), (0.72, 0.38),
                              (0.95, 0.42), (0.90, 0.95), (0.28, 0.95)]), fill=fill)


# animal silhouettes -------------------------------------------------------
def ic_coyote(d, cx, cy, s, fill=BLACK):
    p = _sc(cx, cy, s, [(0.02, 0.62), (0.10, 0.45), (0.30, 0.42), (0.62, 0.40), (0.70, 0.22), (0.76, 0.34),
                        (0.88, 0.18), (0.92, 0.40), (0.98, 0.50), (0.90, 0.56), (0.72, 0.60), (0.70, 0.82),
                        (0.64, 0.82), (0.60, 0.62), (0.40, 0.62), (0.34, 0.82), (0.28, 0.82), (0.26, 0.62),
                        (0.14, 0.64), (0.06, 0.80), (0.0, 0.76)])
    d.polygon(p, fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.86, 0.40), (0.90, 0.44)]), fill=WHITE)


def ic_deer(d, cx, cy, s, fill=BLACK):
    p = _sc(cx, cy, s, [(0.12, 0.50), (0.30, 0.44), (0.62, 0.44), (0.72, 0.28), (0.82, 0.30), (0.90, 0.40),
                        (0.88, 0.50), (0.74, 0.54), (0.72, 0.90), (0.66, 0.90), (0.64, 0.62), (0.40, 0.62),
                        (0.36, 0.90), (0.30, 0.90), (0.28, 0.62), (0.16, 0.66), (0.08, 0.60)])
    d.polygon(p, fill=fill)
    w = max(2, int(s * 0.05))
    d.line(_sc(cx, cy, s, [(0.74, 0.28), (0.66, 0.06), (0.60, 0.16)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.74, 0.28), (0.80, 0.06), (0.86, 0.14)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.70, 0.14), (0.74, 0.10)]), fill=fill, width=w)


def ic_snake(d, cx, cy, s, fill=BLACK):
    pts = []
    for i in range(41):
        t = i / 40
        pts.append((cx + (t - 0.5) * s * 0.96, cy + math.sin(t * 2 * math.pi * 1.5) * s * 0.28))
    d.line(pts, fill=fill, width=max(4, int(s * 0.16)), joint="curve")
    hx, hy = pts[-1]
    d.ellipse([hx - s * 0.10, hy - s * 0.10, hx + s * 0.10, hy + s * 0.10], fill=fill)
    d.ellipse([hx + s * 0.02, hy - s * 0.05, hx + s * 0.06, hy - s * 0.01], fill=WHITE)


def ic_owl(d, cx, cy, s, fill=BLACK):
    d.ellipse(_sc(cx, cy, s, [(0.18, 0.18), (0.82, 0.98)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.22, 0.30), (0.20, 0.02), (0.40, 0.22)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.78, 0.30), (0.80, 0.02), (0.60, 0.22)]), fill=fill)
    for ex in (0.36, 0.64):
        d.ellipse(_sc(cx, cy, s, [(ex - 0.13, 0.28), (ex + 0.13, 0.54)]), fill=WHITE)
        d.ellipse(_sc(cx, cy, s, [(ex - 0.06, 0.35), (ex + 0.06, 0.47)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.44, 0.54), (0.56, 0.54), (0.50, 0.66)]), fill=WHITE)


def ic_quail(d, cx, cy, s, fill=BLACK):
    d.ellipse(_sc(cx, cy, s, [(0.14, 0.34), (0.84, 0.94)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.56, 0.22), (0.84, 0.50)]), fill=fill)
    d.line(_sc(cx, cy, s, [(0.72, 0.26), (0.66, 0.06)]), fill=fill, width=max(2, int(s * 0.05)))
    d.ellipse(_sc(cx, cy, s, [(0.60, 0.03), (0.72, 0.13)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.84, 0.36), (0.96, 0.40), (0.84, 0.44)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.72, 0.32), (0.76, 0.36)]), fill=WHITE)


def ic_lizard(d, cx, cy, s, fill=BLACK):
    d.ellipse(_sc(cx, cy, s, [(0.28, 0.36), (0.68, 0.64)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.62, 0.38), (0.86, 0.60)]), fill=fill)
    w = max(3, int(s * 0.08))
    d.line(_sc(cx, cy, s, [(0.30, 0.50), (0.12, 0.44), (0.02, 0.30)]), fill=fill, width=w, joint="curve")
    for x, y0 in ((0.38, 0.40), (0.60, 0.40)):
        d.line(_sc(cx, cy, s, [(x, y0), (x - 0.10, 0.22)]), fill=fill, width=w)
        d.line(_sc(cx, cy, s, [(x, 1 - y0), (x - 0.10, 0.78)]), fill=fill, width=w)
    d.ellipse(_sc(cx, cy, s, [(0.76, 0.44), (0.80, 0.48)]), fill=WHITE)


def ic_hawk(d, cx, cy, s, fill=BLACK):
    d.polygon(_sc(cx, cy, s, [(0.0, 0.30), (0.20, 0.36), (0.40, 0.48), (0.50, 0.40), (0.60, 0.48), (0.80, 0.36),
                              (1.0, 0.30), (0.78, 0.52), (0.62, 0.62), (0.56, 0.88), (0.44, 0.88), (0.38, 0.62),
                              (0.22, 0.52)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.42, 0.24), (0.58, 0.42)]), fill=fill)


def ic_bobcat(d, cx, cy, s, fill=BLACK):
    d.polygon(_sc(cx, cy, s, [(0.06, 0.52), (0.14, 0.42), (0.60, 0.40), (0.68, 0.26), (0.74, 0.34), (0.86, 0.26),
                              (0.88, 0.40), (0.96, 0.48), (0.86, 0.56), (0.70, 0.60), (0.68, 0.88), (0.60, 0.88),
                              (0.58, 0.62), (0.34, 0.62), (0.30, 0.88), (0.22, 0.88), (0.20, 0.60), (0.06, 0.60)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.84, 0.40), (0.88, 0.44)]), fill=WHITE)


def ic_roadrunner(d, cx, cy, s, fill=BLACK):
    d.ellipse(_sc(cx, cy, s, [(0.30, 0.40), (0.70, 0.74)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.32, 0.56), (0.0, 0.34), (0.06, 0.28), (0.36, 0.48)]), fill=fill)
    d.line(_sc(cx, cy, s, [(0.62, 0.48), (0.72, 0.28)]), fill=fill, width=max(3, int(s * 0.10)))
    d.ellipse(_sc(cx, cy, s, [(0.64, 0.14), (0.84, 0.34)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.82, 0.22), (1.0, 0.26), (0.82, 0.30)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.70, 0.16), (0.60, 0.02), (0.76, 0.12)]), fill=fill)
    w = max(2, int(s * 0.06))
    d.line(_sc(cx, cy, s, [(0.44, 0.72), (0.40, 0.92), (0.30, 0.92)]), fill=fill, width=w)
    d.line(_sc(cx, cy, s, [(0.56, 0.72), (0.62, 0.92), (0.72, 0.92)]), fill=fill, width=w)
    d.ellipse(_sc(cx, cy, s, [(0.74, 0.20), (0.78, 0.24)]), fill=WHITE)


def ic_turkey(d, cx, cy, s, fill=BLACK):
    for k in range(-3, 4):
        a = math.radians(-90 + k * 22)
        x, y = cx + math.cos(a) * s * 0.44, cy + 0.12 * s + math.sin(a) * s * 0.44
        d.line([cx, cy + 0.14 * s, x, y], fill=fill, width=max(5, int(s * 0.14)))
    d.ellipse(_sc(cx, cy, s, [(0.26, 0.40), (0.74, 0.90)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.60, 0.26), (0.82, 0.50)]), fill=fill)
    d.polygon(_sc(cx, cy, s, [(0.80, 0.36), (0.96, 0.40), (0.80, 0.44)]), fill=fill)
    d.ellipse(_sc(cx, cy, s, [(0.70, 0.34), (0.74, 0.38)]), fill=WHITE)


ANIMALS = [  # (keyword regex, label, icon)
    (r"coyote", "Coyote", ic_coyote), (r"snake|rattler", "Snake", ic_snake), (r"owl", "Owl", ic_owl),
    (r"deer", "Deer", ic_deer), (r"quail", "Quail", ic_quail), (r"lizard", "Lizard", ic_lizard),
    (r"hawk", "Hawk", ic_hawk), (r"bobcat", "Bobcat", ic_bobcat), (r"roadrunner", "Roadrunner", ic_roadrunner),
    (r"turkey", "Turkey", ic_turkey), (r"rabbit|bunny", "Rabbit", ic_star),
]


def animal_hits(r):
    blob = ((r.get("description") or "") + " " + (r.get("name") or "")).lower()
    return [(lbl, ic) for rx, lbl, ic in ANIMALS if re.search(rf"\b{rx}s?\b", blob)]


# ---------------------------------------------------------------- data prep


def is_run(r):
    return r["sport_type"] in RUN_TYPES


def is_bike(r):
    return r["sport_type"] in BIKE_TYPES


def latest_with_gps(rows):
    for r in sorted(rows, key=lambda r: r["start_date_local"], reverse=True):
        if os.path.exists(os.path.join(DATA_DIR, "streams", f"{r['id']}.csv")):
            return r
    return rows[-1]


def load_stream(aid):
    fn = os.path.join(DATA_DIR, "streams", f"{aid}.csv")
    with open(fn, encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f)]


def iso_week(r):
    return pdate(r["start_date_local"]).isocalendar()[:2]


# ---------------------------------------------------------------- cards
# Each card: fn(ctx) -> (img, caption). ctx holds preloaded data.


def card_latest(ctx):
    rows = ctx["rows"]
    r = latest_with_gps(rows)
    img, d = new_card()
    dt = pdate(r["start_date_local"])
    y = header(d, r["name"], kicker="Latest activity", right=dt.strftime("%a %b %-d"))
    # route thumbnail
    box = (M, y + 14, W - M, y + 14 + 300)
    d.rectangle(box, fill=WHITE, outline=LIGHT, width=2)
    pts = [(float(s["lng"]), float(s["lat"])) for s in load_stream(r["id"]) if s["lat"] and s["lng"]]
    pts = _rdp(pts, 0.00004)
    if pts:
        lat0 = sum(p[1] for p in pts) / len(pts)
        k = math.cos(math.radians(lat0))
        xs = [p[0] * k for p in pts]
        ys = [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        pad = 24
        bw, bh = box[2] - box[0] - 2 * pad, box[3] - box[1] - 2 * pad
        sc = min(bw / ((x1 - x0) or 1e-9), bh / ((y1 - y0) or 1e-9))
        ox = box[0] + pad + (bw - (x1 - x0) * sc) / 2
        oy = box[1] + pad + (bh - (y1 - y0) * sc) / 2
        poly = [(ox + (x - x0) * sc, oy + (y1 - y) * sc) for x, y in zip(xs, ys)]
        d.line(poly, fill=LIGHT, width=9, joint="curve")
        d.line(poly, fill=BLACK, width=4, joint="curve")
        sx, sy = poly[0]
        ex, ey = poly[-1]
        d.ellipse([sx - 9, sy - 9, sx + 9, sy + 9], fill=WHITE, outline=BLACK, width=3)
        d.rectangle([ex - 8, ey - 8, ex + 8, ey + 8], fill=BLACK)
        # scale bar: 1 km in degrees-lng*k ~ 1/111.32
        km_px = sc / 111.32
        bx = box[2] - pad - km_px
        d.line([bx, box[3] - 18, bx + km_px, box[3] - 18], fill=BLACK, width=3)
        text(d, (bx + km_px / 2, box[3] - 24), "1 km", 16, DARK, bold=False, anchor="md")
        text(d, (box[0] + 12, box[1] + 8), "N", 18, DARK, anchor="la")
        ic_arrow(d, box[0] + 40, box[1] + 18, 18, "up", DARK)
    sport_icon(r["sport_type"])(d, box[2] - 40, box[1] + 36, 48, BLACK)
    # stats strip: 4 x 2
    dist_mi = (mf(r["distance_km"]) or 0) * KM_TO_MI
    if is_bike(r):
        speed = f"{(mf(r['average_speed_kmh']) or 0) * KM_TO_MI:.1f} mph"
    else:
        speed = f"{pace_str(mf(r['average_speed_kmh']))} /mi"
    tc = mf(r["average_temp_c"])
    stats = [
        (f"{dist_mi:.1f} mi", "distance"), (hms(mf(r["moving_time_min"]) or 0), "moving"),
        (speed, "avg speed" if is_bike(r) else "avg pace"),
        (f"{(mf(r['total_elevation_gain_m']) or 0) * M_TO_FT:,.0f} ft", "climb"),
        (f"{(mf(r['average_heartrate']) or 0):.0f} bpm", "avg HR"),
        (f"{f_to_c(tc):.0f} F" if tc is not None else "--", "temp"),
        (f"{int(mf(r['suffer_score']) or 0)}", "suffer"), (f"{int(r['kudos_count'] or 0)}", "kudos"),
    ]
    sy = box[3] + 14
    cw = (W - 2 * M) / 4
    for i, (num, lbl) in enumerate(stats):
        cx = M + cw * (i % 4) + cw / 2
        yy = sy + (i // 4) * 68
        text(d, (cx, yy), num, 30, BLACK, anchor="ma")
        text(d, (cx, yy + 36), lbl, 17, DARK, bold=False, anchor="ma")
    footer(d, fit(d, (r.get("description") or "").strip() or "no description", font(19, False), W - 2 * M))
    return img, "#1 Latest activity + route  [Map + stats]"


def card_week(ctx):
    rows = ctx["rows"]
    last = max(rows, key=lambda r: r["start_date_local"])
    wk = iso_week(last)
    monday = date.fromisocalendar(wk[0], wk[1], 1)
    prev_wk = (monday - timedelta(days=7)).isocalendar()[:2]
    this = [r for r in rows if iso_week(r) == wk]
    prev = [r for r in rows if iso_week(r) == prev_wk]

    def tot(rs):
        return {
            "run": sum((mf(r["distance_km"]) or 0) * KM_TO_MI for r in rs if is_run(r)),
            "bike": sum((mf(r["distance_km"]) or 0) * KM_TO_MI for r in rs if is_bike(r)),
            "elev": sum((mf(r["total_elevation_gain_m"]) or 0) * M_TO_FT for r in rs),
            "hours": sum((mf(r["moving_time_min"]) or 0) for r in rs) / 60,
            "n": len(rs),
        }
    t, p = tot(this), tot(prev)
    img, d = new_card()
    y = header(d, f"Week of {monday.strftime('%b %-d')}", kicker="Week in review",
               right=f"{t['n']} activities")
    # day boxes
    y += 16
    bw = (W - 2 * M - 6 * 8) / 7
    by_day = defaultdict(list)
    for r in this:
        by_day[pdate(r["start_date_local"]).weekday()].append(r)
    for i in range(7):
        x0 = M + i * (bw + 8)
        day = monday + timedelta(days=i)
        acts = by_day.get(i, [])
        d.rectangle([x0, y, x0 + bw, y + 200], fill=LIGHT if acts else WHITE, outline=BLACK, width=3)
        text(d, (x0 + bw / 2, y + 12), day.strftime("%a"), 20, BLACK, anchor="ma")
        text(d, (x0 + bw / 2, y + 36), day.strftime("%-d"), 18, DARK, bold=False, anchor="ma")
        yy = y + 70
        for r in acts[:2]:
            sport_icon(r["sport_type"])(d, x0 + bw / 2, yy + 22, 40, BLACK)
            mi = (mf(r["distance_km"]) or 0) * KM_TO_MI
            lbl = f"{mi:.1f} mi" if mi > 0 else hms(mf(r["moving_time_min"]) or 0)
            text(d, (x0 + bw / 2, yy + 48), lbl, 16, BLACK, bold=False, anchor="ma")
            yy += 66
        if not acts:
            text(d, (x0 + bw / 2, y + 110), "rest", 17, DARK, bold=False, anchor="mm")
    y += 224

    def delta(a, b):
        if b == 0:
            return "new"
        return f"{(a - b) / b * 100:+.0f}% vs last wk"
    tiles = [(f"{t['run']:.1f} mi", "running", delta(t['run'], p['run']), ic_run),
             (f"{t['bike']:.1f} mi", "biking", delta(t['bike'], p['bike']), ic_bike),
             (f"{t['elev']:,.0f} ft", "climbed", delta(t['elev'], p['elev']), ic_mountain),
             (f"{t['hours']:.1f} h", "moving", delta(t['hours'], p['hours']), ic_flame)]
    tw_ = (W - 2 * M - 3 * 12) / 4
    for i, (num, lbl, dl, ic) in enumerate(tiles):
        x0 = M + i * (tw_ + 12)
        d.rectangle([x0, y, x0 + tw_, y + 128], outline=BLACK, width=3)
        ic(d, x0 + 30, y + 30, 36, BLACK)
        text(d, (x0 + tw_ - 12, y + 34), lbl, 18, DARK, bold=False, anchor="rm")
        text(d, (x0 + tw_ / 2, y + 66), num, 34, BLACK, anchor="mm", maxw=tw_ - 16)
        text(d, (x0 + tw_ / 2, y + 108), dl, 16, DARK, bold=False, anchor="mm", maxw=tw_ - 12)
    footer(d, f"Last week: {p['run']:.1f} mi run, {p['bike']:.1f} mi bike, {p['n']} activities")
    return img, "#11 Week in review  [Card grid]"


def load_series(rows):
    daily = defaultdict(float)
    for r in rows:
        daily[r["start_date_local"][:10]] += mf(r["suffer_score"]) or 0
    d0 = min(daily)
    d1 = max(daily)
    start = datetime.strptime(d0, "%Y-%m-%d")
    end = datetime.strptime(d1, "%Y-%m-%d")
    n = (end - start).days + 1
    series = [daily.get((start + timedelta(days=i)).strftime("%Y-%m-%d"), 0.0) for i in range(n)]
    roll7 = [sum(series[max(0, i - 6):i + 1]) for i in range(n)]
    mean7 = [sum(series[max(0, i - 6):i + 1]) / len(series[max(0, i - 6):i + 1]) for i in range(n)]
    mean28 = [sum(series[max(0, i - 27):i + 1]) / len(series[max(0, i - 27):i + 1]) for i in range(n)]
    acwr = [m7 / m28 if m28 else 0.0 for m7, m28 in zip(mean7, mean28)]
    return roll7, acwr, end


def run_week_streak(rows):
    weeks = sorted({iso_week(r) for r in rows if is_run(r)}, reverse=True)
    if not weeks:
        return 0, 0
    # current streak counted back from the latest run week
    streak, best, cur = 1, 1, 1
    for a, b in zip(weeks, weeks[1:]):
        da = date.fromisocalendar(a[0], a[1], 1)
        db = date.fromisocalendar(b[0], b[1], 1)
        if (da - db).days == 7:
            cur += 1
        else:
            best = max(best, cur)
            cur = 1
    best = max(best, cur)
    # streak ending at latest week
    streak = 1
    for a, b in zip(weeks, weeks[1:]):
        if (date.fromisocalendar(a[0], a[1], 1) - date.fromisocalendar(b[0], b[1], 1)).days == 7:
            streak += 1
        else:
            break
    return streak, best


def card_streak_load(ctx):
    rows = ctx["rows"]
    roll7, acwr, end = load_series(rows)
    streak, best = run_week_streak(rows)
    img, d = new_card()
    y = header(d, "Streak & training load", kicker="Consistency", right=end.strftime("%b %-d"))
    # left: streak hero
    ic_flame(d, 150, y + 90, 90, BLACK)
    hero(d, 150, y + 150, str(streak), "weeks running in a row", size=110)
    text(d, (150, y + 330), f"best ever: {best} weeks", 20, DARK, bold=False, anchor="ma")
    d.line([W / 2, y + 30, W / 2, H - 90], fill=LIGHT, width=3)
    # right: ACWR gauge
    a = acwr[-1]
    frac = min(a, 2.2) / 2.2
    bands = [(0, 0.8 / 2.2, LIGHT), (0.8 / 2.2, 1.3 / 2.2, WHITE), (1.3 / 2.2, 1.5 / 2.2, LIGHT), (1.5 / 2.2, 1.0, DARK)]
    gauge(d, 600, y + 210, 150, frac, bands, "0", "2.2")
    text(d, (600, y + 226), f"{a:.2f}", 56, BLACK, anchor="ma")
    text(d, (600, y + 292), "acute : chronic load", 20, DARK, bold=False, anchor="ma")
    zone = "under-training" if a < 0.8 else "sweet spot" if a < 1.3 else "caution" if a < 1.5 else "SPIKE ZONE"
    d.rectangle([505, y + 330, 695, y + 368], fill=BLACK if a >= 1.5 else WHITE, outline=BLACK, width=3)
    text(d, (600, y + 349), zone, 22, WHITE if a >= 1.5 else BLACK, anchor="mm")
    footer(d, f"7-day suffer score {int(roll7[-1])}  |  28-day avg {sum(roll7[-28:]) / 28 / 7:.0f}/day  |  data through {end:%Y-%m-%d}")
    return img, "#19+#20 Streak + load gauge  [Hero]"


def card_pr_board(ctx):
    rows = ctx["rows"]
    runs = [r for r in rows if is_run(r)]
    bikes = [r for r in rows if r["sport_type"] == "MountainBikeRide"]
    lr = max(runs, key=lambda r: mf(r["distance_km"]) or 0)
    lb = max(bikes, key=lambda r: mf(r["distance_km"]) or 0)
    climb = max(rows, key=lambda r: mf(r["total_elevation_gain_m"]) or 0)
    fast = max((r for r in runs if (mf(r["distance_km"]) or 0) >= 4.5), key=lambda r: mf(r["average_speed_kmh"]) or 0)
    hr = max((r for r in rows if mf(r["max_heartrate"])), key=lambda r: mf(r["max_heartrate"]))
    spd = max(bikes, key=lambda r: mf(r["max_speed_kmh"]) or 0)
    temps = [r for r in rows if mf(r["average_temp_c"]) is not None]
    hot = max(temps, key=lambda r: mf(r["average_temp_c"]))
    cold = min(temps, key=lambda r: mf(r["average_temp_c"]))
    items = [
        (ic_run, "Longest run", f"{mf(lr['distance_km']) * KM_TO_MI:.1f} mi", lr),
        (ic_bike, "Longest MTB", f"{mf(lb['distance_km']) * KM_TO_MI:.1f} mi", lb),
        (ic_mountain, "Biggest climb", f"{mf(climb['total_elevation_gain_m']) * M_TO_FT:,.0f} ft", climb),
        (ic_flame, "Fastest 5k+ run", f"{pace_str(mf(fast['average_speed_kmh']))} /mi", fast),
        (ic_heart, "Max heart rate", f"{mf(hr['max_heartrate']):.0f} bpm", hr),
        (ic_bike, "MTB top speed", f"{mf(spd['max_speed_kmh']) * KM_TO_MI:.1f} mph", spd),
        (ic_thermo, "Hottest / coldest", f"{f_to_c(mf(hot['average_temp_c'])):.0f} F / {f_to_c(mf(cold['average_temp_c'])):.0f} F", hot),
    ]
    img, d = new_card()
    y = header(d, "Personal records", kicker="All time", right=f"{len(rows)} activities")
    y += 12
    rh = 66
    for i, (ic, lbl, val, r) in enumerate(items):
        yy = y + i * rh
        if i % 2 == 0:
            d.rectangle([M, yy, W - M, yy + rh], fill=LIGHT)
        ic(d, M + 32, yy + rh / 2, 40, BLACK)
        text(d, (M + 70, yy + rh / 2 - 12), lbl, 22, BLACK, anchor="lm")
        text(d, (M + 70, yy + rh / 2 + 14), f"{r['name']}  -  {r['start_date_local'][:10]}", 16, DARK, bold=False, anchor="lm", maxw=380)
        text(d, (W - M - 14, yy + rh / 2), val, 30, BLACK, anchor="rm")
    footer(d, f"{sum(int(r['pr_count'] or 0) for r in rows)} segment PRs  |  {sum(int(r['achievement_count'] or 0) for r in rows)} achievements  |  {sum(int(r['kudos_count'] or 0) for r in rows):,} kudos")
    return img, "#25 PR board  [List]"


def card_segment_week(ctx):
    rows, segs, eff = ctx["rows"], ctx["segs"], ctx["efforts"]
    last = max(r["start_date_local"] for r in rows)
    cutoff = (pdate(last) - timedelta(days=30)).strftime("%Y-%m-%d")
    recent = Counter(e["segment_id"] for e in eff if e["start_date_local"] >= cutoff)
    sid, n30 = recent.most_common(1)[0]
    s = next(x for x in segs if x["segment_id"] == sid)
    efforts = sorted((e for e in eff if e["segment_id"] == sid), key=lambda e: e["start_date_local"])
    times = [float(e["elapsed_time_s"]) for e in efforts]
    img, d = new_card()
    y = header(d, s["segment_name"], kicker="Segment of the month", right=f"{n30}x in 30d")
    sport_icon(efforts[-1]["sport_type"])(d, M + 40, y + 60, 64, BLACK)
    text(d, (M + 90, y + 40), f"{float(s['segment_distance_m']) / 1000 * KM_TO_MI:.2f} mi  |  {float(s['segment_avg_grade']):+.1f}% grade  |  {s['effort_count']} efforts total", 20, DARK, bold=False, anchor="lm")
    text(d, (M + 90, y + 72), f"{s['segment_city']}, {s['segment_state']}", 20, DARK, bold=False, anchor="lm")
    # three numbers
    trend = float(s["recent_trend"] or 0)
    cols = [("best", secs_str(min(times)), s["pr_date"][:10]), ("latest", secs_str(times[-1]), efforts[-1]["start_date_local"][:10]),
            ("trend", f"{trend:+.1f}%", "recent vs earlier")]
    cw = (W - 2 * M) / 3
    for i, (lbl, val, sub) in enumerate(cols):
        cx = M + cw * i + cw / 2
        text(d, (cx, y + 120), lbl, 18, DARK, bold=False, anchor="ma")
        if lbl == "trend":
            vw = text(d, (cx - 22, y + 150), val, 48, BLACK, anchor="ma")
            ic_arrow(d, cx - 22 + vw / 2 + 26, y + 178, 34, "down" if trend < -1 else "up" if trend > 1 else "flat", BLACK)
            sub = "slower lately" if trend > 1 else "faster lately" if trend < -1 else "holding steady"
        else:
            text(d, (cx, y + 146), val, 56, BLACK, anchor="ma")
        text(d, (cx, y + 212), sub, 16, DARK, bold=False, anchor="ma")
    # sparkline of effort times (lower = faster => invert so faster is up)
    box = (M + 10, y + 260, W - M - 10, y + 390)
    text(d, (M + 10, y + 244), "effort time, oldest -> newest (up = faster)", 16, DARK, bold=False, anchor="la")
    d.rectangle(box, outline=LIGHT, width=2)
    sparkline(d, (box[0] + 16, box[1] + 16, box[2] - 16, box[3] - 16), times[-24:], invert=True)
    footer(d, f"HR on this segment avg {float(s['avg_heartrate'] or 0):.0f} bpm  |  worst {secs_str(max(times))}  |  first effort {s['first_effort'][:10]}")
    return img, "#26 Segment of the month  [Hero + sparkline]"


ROUTE_LADDER = [  # (destination, road miles from 92129, [(waypoint, cum miles)...])
    ("Oceanside", 30, []), ("Tijuana", 35, []), ("Temecula", 45, []), ("San Clemente", 55, []),
    ("Los Angeles", 125, [("San Clemente", 55), ("Irvine", 80), ("Anaheim", 100)]),
    ("Palm Springs", 130, [("Temecula", 45), ("Beaumont", 100)]),
    ("Santa Barbara", 220, [("Los Angeles", 125), ("Ventura", 190)]),
    ("Las Vegas", 340, [("Temecula", 45), ("Victorville", 150), ("Barstow", 185), ("Baker", 245), ("Primm", 300)]),
    ("Phoenix", 355, [("El Centro", 120), ("Yuma", 175), ("Gila Bend", 290)]),
    ("Yosemite", 420, [("Los Angeles", 125), ("Bakersfield", 240), ("Fresno", 350)]),
    ("San Francisco", 500, [("Los Angeles", 125), ("Bakersfield", 240), ("Fresno", 350), ("Modesto", 440)]),
    ("Sacramento", 530, [("Los Angeles", 125), ("Bakersfield", 240), ("Fresno", 350), ("Stockton", 480)]),
    ("Reno", 620, [("Los Angeles", 125), ("Bakersfield", 240), ("Fresno", 350), ("Sacramento", 530), ("Truckee", 600)]),
    ("Salt Lake City", 750, [("Las Vegas", 340), ("St. George", 460), ("Cedar City", 510), ("Provo", 700)]),
    ("Portland", 1080, [("Los Angeles", 125), ("Bakersfield", 240), ("Fresno", 350), ("Sacramento", 530), ("Redding", 690), ("Medford", 830), ("Eugene", 990)]),
    ("Denver", 1090, [("Las Vegas", 340), ("St. George", 460), ("Grand Junction", 830), ("Vail", 970)]),
    ("Seattle", 1250, [("Sacramento", 530), ("Redding", 690), ("Medford", 830), ("Portland", 1080), ("Olympia", 1190)]),
    ("Austin", 1300, [("Phoenix", 355), ("Tucson", 470), ("Las Cruces", 750), ("El Paso", 800), ("Fort Stockton", 1040)]),
    ("Dallas", 1380, [("Phoenix", 355), ("Tucson", 470), ("El Paso", 800), ("Abilene", 1230)]),
    ("Mexico City", 1600, [("Tijuana", 35), ("Hermosillo", 600), ("Mazatlan", 1100), ("Guadalajara", 1350)]),
    ("Kansas City", 1650, [("Las Vegas", 340), ("Denver", 1090), ("Hays", 1400), ("Topeka", 1590)]),
    ("Nashville", 2050, [("El Paso", 800), ("Dallas", 1380), ("Little Rock", 1700), ("Memphis", 1840)]),
    ("Chicago", 2090, [("Denver", 1090), ("Kansas City", 1650), ("St. Louis", 1900)]),
    ("Atlanta", 2150, [("Dallas", 1380), ("Shreveport", 1570), ("Jackson", 1800), ("Birmingham", 2000)]),
    ("Washington DC", 2680, [("Dallas", 1380), ("Nashville", 2050), ("Knoxville", 2230), ("Roanoke", 2480)]),
    ("Miami", 2720, [("Dallas", 1380), ("Atlanta", 2150), ("Jacksonville", 2500), ("Orlando", 2640)]),
    ("New York City", 2780, [("Kansas City", 1650), ("Chicago", 2090), ("Cleveland", 2430), ("Pittsburgh", 2560)]),
    ("Lexington, MA", 3000, [("Chicago", 2090), ("Cleveland", 2430), ("New York City", 2780), ("Hartford", 2890)]),
    ("Anchorage", 3600, [("Portland", 1080), ("Seattle", 1250), ("Vancouver", 1390), ("Prince George", 1900), ("Whitehorse", 2900)]),
    ("Panama City", 4200, [("Mexico City", 1600), ("Guatemala City", 2300), ("San Jose, CR", 3800)]),
    ("Ushuaia", 9500, [("Panama City", 4200), ("Bogota", 5000), ("Lima", 6300), ("Santiago", 8000)]),
]


def route_card(ctx, sport):
    rows = ctx["rows"]
    if sport == "run":
        sel = [r for r in rows if is_run(r)]
        icon, title, verb = ic_run, "Running", "run"
    else:
        sel = [r for r in rows if is_bike(r)]
        icon, title, verb = ic_bike, "Biking", "ridden"
    total = sum((mf(r["distance_km"]) or 0) * KM_TO_MI for r in sel)
    ytd = sum((mf(r["distance_km"]) or 0) * KM_TO_MI for r in sel if r["start_date_local"].startswith(str(pdate(max(x["start_date_local"] for x in rows)).year)))
    rung = next((x for x in ROUTE_LADDER if x[1] > total), ROUTE_LADDER[-1])
    dest, dist, wps = rung
    passed = [w for w in wps if w[1] <= total]
    ahead = [w for w in wps if w[1] > total]
    reached = [x[0] for x in ROUTE_LADDER if x[1] <= total]

    img, d = new_card()
    y = header(d, f"92129 -> {dest}", kicker=f"{title}: how far along the route?", right=f"{total:,.0f} of {dist:,} mi")
    icon(d, M + 44, y + 70, 72, BLACK)
    hero(d, W / 2 + 40, y + 10, f"{total:,.0f}", f"lifetime miles {verb}  |  {dist - total:,.0f} to go", size=96)
    # road
    ry = y + 262
    x0, x1 = M + 20, W - M - 20
    d.rectangle([x0, ry - 22, x1, ry + 22], fill=DARK)
    for k in range(int(x0), int(x1), 40):
        d.line([k + 6, ry, min(k + 26, x1), ry], fill=WHITE, width=4)
    fx = x0 + (x1 - x0) * min(1, total / dist)
    d.rectangle([x0, ry - 22, fx, ry + 22], fill=BLACK)
    for k in range(int(x0), int(fx), 40):
        d.line([k + 6, ry, min(k + 26, fx), ry], fill=LIGHT, width=4)
    # waypoints
    for i, (wn, wm) in enumerate([("92129", 0)] + wps + [(dest, dist)]):
        wx = x0 + (x1 - x0) * wm / dist
        done = wm <= total
        d.ellipse([wx - 8, ry - 8, wx + 8, ry + 8], fill=WHITE if done else DARK, outline=WHITE, width=3)
        row = 34 if i % 2 == 0 else 78
        text(d, (wx, ry + row), wn, 17, BLACK if done else DARK, bold=done, anchor="ma")
        text(d, (wx, ry + row + 20), f"{wm:,} mi", 14, DARK, bold=False, anchor="ma")
        if i % 2 == 1:
            d.line([wx, ry + 24, wx, ry + 74], fill=LIGHT, width=2)
    # marker
    d.polygon([(fx, ry - 26), (fx - 14, ry - 52), (fx + 14, ry - 52)], fill=BLACK)
    icon(d, fx, ry - 84, 56, BLACK)
    # legs
    yy = ry + 126
    last_passed = passed[-1][0] if passed else "92129"
    nxt = ahead[0] if ahead else (dest, dist)
    text(d, (M, yy), f"passed {last_passed}", 26, BLACK, anchor="la")
    text(d, (M, yy + 34), f"next: {nxt[0]} in {nxt[1] - total:,.0f} mi", 22, DARK, bold=False, anchor="la")
    text(d, (W - M, yy), f"YTD {ytd:,.0f} mi", 26, BLACK, anchor="ra")
    text(d, (W - M, yy + 34), f"arrived so far: {len(reached)} cities", 22, DARK, bold=False, anchor="ra")
    footer(d, "already reached: " + (", ".join(reached[-6:]) if reached else "nowhere yet") + ("..." if len(reached) > 6 else ""))
    return img, f"#38 Route progress - {title.lower()}  [Map + stats]"


def card_route_run(ctx):
    return route_card(ctx, "run")


def card_route_bike(ctx):
    return route_card(ctx, "bike")


def card_passport(ctx):
    rows = ctx["rows"]
    featured, brief, pc, n_states, n_prov = _passport_data(rows)
    img, d = new_card()
    y = header(d, "Passport", kicker="Places", right=f"{n_states} states  {n_prov} provinces")
    picks = featured[:6]
    cols, r = 3, 105
    for i, ft in enumerate(picks):
        cx = M + (W - 2 * M) / cols * (i % cols) + (W - 2 * M) / cols / 2
        cy = y + 30 + r + (i // cols) * (2 * r + 22)
        title = ft["region"] or ft["caption"]
        stamp(d, cx, cy, r, title, ft["dates"], ft["tags"] if isinstance(ft["tags"], str) else " ".join(ft["tags"]))
        if ft.get("badge"):
            ic_star(d, cx + r - 22, cy - r + 22, 30, BLACK)
    more = len(featured) - len(picks)
    footer(d, f"{len(featured)} trips, {len(brief)} brief stops" + (f"  |  +{more} more trips" if more > 0 else ""))
    return img, "#33 Passport  [Badge wall]"


def card_hearts(ctx):
    rows = ctx["rows"]
    runs = [mf(r["average_heartrate"]) for r in rows if is_run(r) and mf(r["average_heartrate"])]
    mtb = [mf(r["average_heartrate"]) for r in rows if r["sport_type"] == "MountainBikeRide" and mf(r["average_heartrate"])]
    rmax = [mf(r["max_heartrate"]) for r in rows if is_run(r) and mf(r["max_heartrate"])]
    mmax = [mf(r["max_heartrate"]) for r in rows if r["sport_type"] == "MountainBikeRide" and mf(r["max_heartrate"])]
    ra, ma = sum(runs) / len(runs), sum(mtb) / len(mtb)
    img, d = new_card()
    y = header(d, "Two cardiac worlds", kicker="Physiology", right="avg HR per activity")
    for cx, val, lbl, n, ic, size in ((220, ra, "running", len(runs), ic_run, 230), (580, ma, "mountain bike", len(mtb), ic_bike, 230 * ma / ra)):
        ic_heart(d, cx, y + 150, size, LIGHT)
        ic_heart(d, cx, y + 150, size * 0.86, WHITE)
        ic(d, cx, y + 40, 48, BLACK)
        text(d, (cx, y + 150), f"{val:.0f}", 72, BLACK, anchor="mm")
        text(d, (cx, y + 200), "bpm", 22, DARK, bold=False, anchor="ma")
        text(d, (cx, y + 300), lbl, 26, BLACK, anchor="ma")
        text(d, (cx, y + 332), f"n = {n}", 18, DARK, bold=False, anchor="ma")
    text(d, (W / 2, y + 150), f"{ra - ma:.0f}", 44, BLACK, anchor="mm")
    text(d, (W / 2, y + 180), "bpm gap", 18, DARK, bold=False, anchor="ma")
    footer(d, f"same redline: max HR averages {sum(rmax) / len(rmax):.0f} (run) vs {sum(mmax) / len(mmax):.0f} (MTB)")
    return img, "#43 Two cardiac worlds  [Hero pair]"


def card_shoes(ctx):
    gear = ctx["gear"]
    rows = ctx["rows"]
    last_use = {}
    for r in sorted(rows, key=lambda r: r["start_date_local"]):
        if r["gear_id"]:
            last_use[r["gear_id"]] = r["start_date_local"][:10]
    items = sorted(gear.values(), key=lambda g: (g["retired"], -g["converted_distance"]))
    img, d = new_card()
    y = header(d, "Gear odometer", kicker="Shoes & bike", right=f"{len(items)} items")
    y += 10
    rh = 96
    for i, g in enumerate(items[:5]):
        yy = y + i * rh
        is_bike_g = g["id"].startswith("b")
        (ic_bike if is_bike_g else ic_shoe)(d, M + 34, yy + 40, 52, DARK if g["retired"] else BLACK)
        name = g["name"] + ("  (retired)" if g["retired"] else "")
        text(d, (M + 80, yy + 22), name, 22, DARK if g["retired"] else BLACK, anchor="lm", maxw=W - M - 80 - 150)
        mi = g["converted_distance"]
        nd = g.get("notification_distance") or 0
        # Strava's API documents this in metres, but the values here (400, 450)
        # are clearly the miles typed into the alert box -- treat small as miles.
        limit = 0 if is_bike_g else (nd if 0 < nd < 2000 else nd / 1000 * KM_TO_MI if nd else 0)
        limit = limit if limit > 0 else (400 if not is_bike_g else 0)
        text(d, (W - M, yy + 22), f"{mi:,.0f} mi", 28, BLACK, anchor="rm")
        if limit:
            frac = mi / limit
            fx = progress_bar(d, (M + 80, yy + 44, W - M, yy + 72), frac, fill=BLACK if frac < 0.9 else DARK)
            for k in range(1, 4):
                tx = M + 80 + (W - M - M - 80) * k / 4
                d.line([tx, yy + 44, tx, yy + 72], fill=WHITE, width=2)
            lbl = f"{frac * 100:.0f}% of {limit:.0f} mi" + ("  -  RETIRE SOON" if frac >= 0.9 else "")
            text(d, (M + 80, yy + 84), lbl, 15, DARK, bold=frac >= 0.9, anchor="lm")
        else:
            text(d, (M + 80, yy + 58), f"{g['brand_name']} {g['model_name']}  |  last ride {last_use.get(g['id'], '--')}", 17, DARK, bold=False, anchor="lm")
    footer(d, "bar = miles vs Strava's replacement alert (400 mi default when unset)")
    return img, "#48 Shoe odometer  [Card grid]"


def card_2004(ctx):
    rows, log = ctx["rows"], ctx["runlog"]
    last = max(rows, key=lambda r: r["start_date_local"])
    wk = iso_week(last)
    then_year = 2004 if any(l["year"] == "2004" and int(l["week_of_year"]) == wk[1] for l in log) else "2003"
    then = [l for l in log if l["year"] == str(then_year) and int(l["week_of_year"]) == wk[1]]
    now = [r for r in rows if iso_week(r) == wk and is_run(r)]
    then_mi = sum(mf(l["miles"]) or 0 for l in then)
    now_mi = sum((mf(r["distance_km"]) or 0) * KM_TO_MI for r in now)
    then_p = [mf(l["pace_min_per_mile"]) for l in then if mf(l["pace_min_per_mile"])]
    now_p = [60 / (mf(r["average_speed_kmh"]) * KM_TO_MI) for r in now if mf(r["average_speed_kmh"])]
    img, d = new_card()
    y = header(d, f"This week in {then_year}", kicker="Then & now", right=f"ISO week {wk[1]}")
    # top band (then)
    d.rectangle([M, y + 12, W - M, y + 262], fill=LIGHT)
    text(d, (M + 16, y + 30), str(then_year), 24, BLACK, mono=True, anchor="la")
    text(d, (M + 16, y + 62), f"{then_mi:.1f} mi", 60, BLACK, mono=True, anchor="la")
    if then_p:
        text(d, (M + 16, y + 132), f"avg pace {int(sum(then_p) / len(then_p))}:{int(round((sum(then_p) / len(then_p) % 1) * 60)):02d} /mi", 20, DARK, bold=False, mono=True, anchor="la")
    yy = y + 164
    for l in [t for t in then if (mf(t["miles"]) or 0) > 0][:4]:
        line = f"{l['day_of_week'][:3]}  {l['workout_type']:<11} {mf(l['miles']) or 0:4.1f} mi"
        if l["is_race"] == "1":
            line += f"  RACE: {l['race_name']}"
        text(d, (M + 16, yy), line, 18, BLACK, bold=False, mono=True, anchor="la", maxw=W - 2 * M - 32)
        yy += 24
    text(d, (W - M - 16, y + 30), fit(d, (then[0]["comments"] if then and then[0]["comments"] else ""), font(17, False), 300), 17, DARK, bold=False, anchor="ra")
    # bottom (now)
    ny = y + 280
    text(d, (M + 16, ny + 6), str(wk[0]), 24, BLACK, anchor="la")
    text(d, (M + 16, ny + 38), f"{now_mi:.1f} mi", 60, BLACK, anchor="la")
    if now_p:
        ap = sum(now_p) / len(now_p)
        text(d, (M + 16, ny + 108), f"avg pace {int(ap)}:{int(round((ap % 1) * 60)):02d} /mi", 20, DARK, bold=False, anchor="la")
    yy = ny + 140
    if not now:
        lr = max((r for r in rows if is_run(r)), key=lambda r: r["start_date_local"])
        text(d, (M + 16, ny + 108), "no runs this week", 20, DARK, bold=False, anchor="la")
        text(d, (M + 16, yy), f"last run: {lr['name']}  {mf(lr['distance_km']) * KM_TO_MI:.1f} mi on {lr['start_date_local'][:10]}", 18, BLACK, bold=False, anchor="la", maxw=W - 2 * M - 140)
    for r in sorted(now, key=lambda r: r["start_date_local"])[:3]:
        text(d, (M + 16, yy), f"{pdate(r['start_date_local']).strftime('%a')}  {r['name']}  {mf(r['distance_km']) * KM_TO_MI:.1f} mi", 18, BLACK, bold=False, anchor="la", maxw=W - 2 * M - 32)
        yy += 24
    ic_run(d, W - M - 60, ny + 60, 90, BLACK)
    delta = now_mi - then_mi
    footer(d, f"{abs(delta):.1f} mi {'more' if delta >= 0 else 'less'} than the same week in {then_year}  |  2003-era log has {len(log):,} days")
    return img, f"#51 This week in {then_year}  [Then & now]"


def card_wildlife(ctx):
    rows = ctx["rows"]
    tally = Counter()
    last_seen = {}
    for r in sorted(rows, key=lambda r: r["start_date_local"]):
        for lbl, ic in animal_hits(r):
            tally[lbl] += 1
            last_seen[lbl] = r
    icons = {lbl: ic for _, lbl, ic in ANIMALS}
    img, d = new_card()
    latest = max(last_seen.values(), key=lambda r: r["start_date_local"])
    y = header(d, "Wildlife scoreboard", kicker="Trail sightings", right=f"{sum(tally.values())} total")
    y += 10
    top = tally.most_common(10)
    cols = 2
    rh = 96
    cw = (W - 2 * M) / cols
    mx = max(tally.values())
    for i, (lbl, n) in enumerate(top):
        cx0 = M + cw * (i % cols)
        yy = y + (i // cols) * rh
        icons[lbl](d, cx0 + 40, yy + 38, 60, BLACK)
        text(d, (cx0 + 86, yy + 22), lbl, 24, BLACK, anchor="lm")
        progress_bar(d, (cx0 + 86, yy + 40, cx0 + cw - 90, yy + 62), n / mx)
        text(d, (cx0 + cw - 16, yy + 40), str(n), 40, BLACK, anchor="rm")
    footer(d, f"last: {[l for l, _ in animal_hits(latest)][0]} on {latest['start_date_local'][:10]}  -  \"{latest['name']}\"")
    return img, "#56 Wildlife scoreboard  [List]"


FUNNY_WORDS = re.compile(r"crap|pants|butt|hell|suck|oops|jackalope|death|nope|ugh|lol|omg|wtf|whee|yikes|puke|"
                         r"barf|nemesis|evil|dumb|stupid|crazy|fart|poop|booty|damn|burn|scream|misery|regret|"
                         r"brutal|ouch|monster|dragon|killer|customers|widow", re.I)


def is_funny_name(n):
    return bool(FUNNY_WORDS.search(n)) or len(n) >= 38 or bool(re.search(r"[,!?]", n))


def funny_score(n):
    return (3 * len(FUNNY_WORDS.findall(n)) + 2 * len(re.findall(r"[,!?]", n))
            + (2 if len(n) >= 38 else 0) + min(len(n), 60) / 30)


def funny_segments(segs):
    cands = [s for s in segs if int(s["effort_count"]) >= 3]
    return sorted(cands, key=lambda s: funny_score(s["segment_name"]), reverse=True)


def card_funny_segment(ctx):
    segs, eff = ctx["segs"], ctx["efforts"]
    scored = funny_segments(segs)
    top = ([s for s in scored if is_funny_name(s["segment_name"])] or scored)[:6]
    seed = int(hashlib.md5(ctx["asof"].encode()).hexdigest(), 16)
    s = top[seed % len(top)]
    my = sorted((e for e in eff if e["segment_id"] == s["segment_id"]), key=lambda e: e["start_date_local"])
    times = [float(e["elapsed_time_s"]) for e in my]
    img, d = new_card()
    y = header(d, "Segment name of the day", kicker="Strava poetry", right=f"{s['effort_count']}x")
    quote = f'"{s["segment_name"]}"'
    for fs in (40, 34, 30, 26):  # shrink until the whole name fits in 3 lines
        lines = wrap(d, quote, font(fs, True), W - 2 * M - 20, 3)
        if " ".join(lines).rstrip(".") == quote or fs == 26:
            break
    yy = y + 40
    for ln in lines:
        text(d, (W / 2, yy), ln, fs, BLACK, anchor="ma")
        yy += fs + 10
    text(d, (W / 2, yy + 8), f"{s['segment_city']}, {s['segment_state']}  |  {float(s['segment_distance_m']) / 1000 * KM_TO_MI:.2f} mi at {float(s['segment_avg_grade']):+.1f}%", 20, DARK, bold=False, anchor="ma", maxw=W - 2 * M)
    sy0 = yy + 44
    sy1 = H - 216
    if sy1 - sy0 > 70 and len(times) >= 2:
        text(d, (M + 10, sy0), "your attempts, oldest -> newest (up = faster)", 15, DARK, bold=False, anchor="la")
        d.rectangle([M + 10, sy0 + 20, W - M - 10, sy1], outline=LIGHT, width=2)
        sparkline(d, (M + 26, sy0 + 36, W - M - 26, sy1 - 16), times[-24:], invert=True)
    trend = float(s["recent_trend"] or 0)
    pr = datetime.strptime(s["pr_date"][:10], "%Y-%m-%d")
    tiles = [(secs_str(min(times)), "your best"), (secs_str(times[-1]), "latest"),
             (pr.strftime("%-m/%-d/%y"), "PR date"), (f"{trend:+.1f}%", "recent trend")]
    tw_ = (W - 2 * M - 3 * 12) / 4
    ty = H - 200
    for i, (num, lbl) in enumerate(tiles):
        x0 = M + i * (tw_ + 12)
        d.rectangle([x0, ty, x0 + tw_, ty + 100], fill=LIGHT if i == 0 else WHITE, outline=BLACK, width=3)
        text(d, (x0 + tw_ / 2, ty + 42), num, 30, BLACK, anchor="mm", maxw=tw_ - 12)
        text(d, (x0 + tw_ / 2, ty + 78), lbl, 17, DARK, bold=False, anchor="mm")
    footer(d, f"rotates daily through the {len(top)} best-scored names of {len(scored)} segments with 3+ efforts")
    return img, "#30 Funny segment name of the day  [Hero]"


DEFAULT_NAME = re.compile(r"^(Morning|Afternoon|Lunch|Evening|Night)\s+(Run|Ride|Mountain Bike Ride|Pickleball|Weight Training|Rock Climb|Hike|Walk|Workout|.*Ski|Ice Skate|Snowboard|Pilates)$")


def card_hall_of_fame(ctx):
    rows = ctx["rows"]
    named = [r for r in rows if not DEFAULT_NAME.match(r["name"].strip()) and r["name"].strip() not in ("Warm Up",)]
    def score(r):
        n = r["name"]
        return (len(re.findall(r"[!?,'\"]", n)) * 3 + min(len(n), 40) / 8 + int(r["kudos_count"] or 0) * 0.5
                + (2 if re.search(r"[^\x00-\x7f]", n) else 0))
    ranked = sorted(named, key=score, reverse=True)
    wk = iso_week(max(rows, key=lambda r: r["start_date_local"]))
    seed = (wk[0] * 53 + wk[1]) % 7
    picks = ranked[seed:seed + 5] if len(ranked) >= seed + 5 else ranked[:5]
    img, d = new_card()
    y = header(d, "Activity-name hall of fame", kicker="Rotates weekly", right=f"{len(named)} named")
    y += 12
    rh = 92
    for i, r in enumerate(picks):
        yy = y + i * rh
        if i % 2 == 0:
            d.rectangle([M, yy, W - M, yy + rh], fill=LIGHT)
        sport_icon(r["sport_type"])(d, M + 36, yy + rh / 2, 48, BLACK)
        f = font(26, True)
        lines = wrap(d, r["name"], f, W - 2 * M - 90 - 160, 2)
        ty = yy + rh / 2 - 15 * len(lines)
        for ln in lines:
            text(d, (M + 78, ty), ln, 26, BLACK, anchor="la")
            ty += 30
        mi = (mf(r["distance_km"]) or 0) * KM_TO_MI
        stat = f"{mi:.1f} mi" if mi > 0 else hms(mf(r["moving_time_min"]) or 0)
        text(d, (W - M - 12, yy + rh / 2 - 12), r["start_date_local"][:10], 17, DARK, bold=False, anchor="rm")
        text(d, (W - M - 12, yy + rh / 2 + 14), f"{stat}  |  {r['kudos_count']} kudos", 17, DARK, bold=False, anchor="rm")
    footer(d, f"{len(rows) - len(named)} activities kept Strava's default name (Morning Run etc.)")
    return img, "#32 Activity-name hall of fame  [List]"


def detect_badges(rows, latest):
    """Firsts/records the latest activity set vs everything before it."""
    hist = [r for r in rows if r["start_date_local"] < latest["start_date_local"]]
    same = [r for r in hist if r["sport_type"] == latest["sport_type"]]
    badges, near = [], []

    def rec(key, label, fmt, higher=True, pool=None, pad=1.0):
        pool = same if pool is None else pool
        v = mf(latest.get(key))
        if v is None:
            return
        prev = [mf(r.get(key)) for r in pool if mf(r.get(key)) is not None]
        if not prev:
            badges.append((label, "first ever", ic_star))
            return
        best = max(prev) if higher else min(prev)
        if (v > best) if higher else (v < best):
            badges.append((label, fmt(v), ic_trophy))
        elif abs(v - best) <= abs(best) * 0.05 * pad:
            near.append(f"{label}: {fmt(v)} vs best {fmt(best)}")
    rec("distance_km", "Longest " + latest["sport_type"], lambda v: f"{v * KM_TO_MI:.1f} mi")
    rec("total_elevation_gain_m", "Biggest climb", lambda v: f"{v * M_TO_FT:,.0f} ft")
    rec("max_heartrate", "New max HR", lambda v: f"{v:.0f} bpm", pool=hist)
    rec("max_speed_kmh", "Top speed", lambda v: f"{v * KM_TO_MI:.1f} mph")
    rec("suffer_score", "Hardest effort", lambda v: f"{v:.0f} suffer")
    rec("average_temp_c", "Hottest ever", lambda v: f"{f_to_c(v):.0f} F", pool=hist)
    rec("average_temp_c", "Coldest ever", lambda v: f"{f_to_c(v):.0f} F", higher=False, pool=hist)
    n = len(same) + 1
    if n % 25 == 0 or n in (1, 10, 50, 100):
        badges.append((f"{latest['sport_type']} #{n}", "milestone", ic_medal))
    prs = int(latest["pr_count"] or 0)
    if prs:
        badges.append((f"{prs} segment PR{'s' if prs > 1 else ''}", "in one go", ic_trophy))
    ach = int(latest["achievement_count"] or 0)
    if ach >= 5:
        badges.append((f"{ach} trophies", "Strava achievements", ic_medal))
    mon = latest["start_date_local"][5:7]
    if not any(r["start_date_local"][5:7] == mon for r in same):
        badges.append((f"First {latest['sport_type']}", f"ever in month {mon}", ic_star))
    for lbl, _ in animal_hits(latest):
        badges.append((f"{lbl} sighting", "wildlife", ic_star))
    return badges, near


def card_achievements(ctx):
    rows = ctx["rows"]
    latest = max(rows, key=lambda r: r["start_date_local"])
    badges, near = detect_badges(rows, latest)
    img, d = new_card()
    y = header(d, "Achievement unlocked" if badges else "No new badges", kicker=f"After: {latest['name']}", right=latest["start_date_local"][:10])
    if badges:
        r = 100
        nrows = math.ceil(min(len(badges), 6) / 3)
        avail = (H - 90) - y
        top = y + (avail - (nrows * 2 * r + (nrows - 1) * 24)) / 2
        for i, (title, sub, ic) in enumerate(badges[:6]):
            cx = M + (W - 2 * M) / 3 * (i % 3) + (W - 2 * M) / 6
            cy = top + r + (i // 3) * (2 * r + 24)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=LIGHT, outline=BLACK, width=4)
            ic(d, cx, cy - 40, 60, BLACK)
            lines = wrap(d, title, font(21, True), 2 * r - 44, 2)
            ty = cy + 12
            for ln in lines:
                text(d, (cx, ty), ln, 21, BLACK, anchor="ma", maxw=2 * r - 44)
                ty += 24
            text(d, (cx, ty + 2), sub, 16, DARK, bold=False, anchor="ma", maxw=2 * r - 44)
        extra = len(badges) - 6
        footer(d, f"{len(badges)} badges" + (f" (+{extra} not shown)" if extra > 0 else "") + (f"  |  near-miss: {near[0]}" if near else ""))
    else:
        text(d, (W / 2, y + 60), "near misses", 26, DARK, anchor="ma")
        yy = y + 110
        for n in near[:4] or ["nothing close this time"]:
            text(d, (M + 20, yy), "- " + n, 22, BLACK, bold=False, anchor="la", maxw=W - 2 * M - 40)
            yy += 40
        footer(d, "badges: records, milestones, segment PRs, first-of-month, wildlife")
    return img, "#60 Achievement unlocked  [Badge wall]"


def card_joggernaut(ctx):
    rows, ath = ctx["rows"], ctx["athlete"]
    roll7, acwr, end = load_series(rows)
    streak, best = run_week_streak(rows)
    cutoff = (end - timedelta(days=30)).strftime("%Y-%m-%d")
    recent = [r for r in rows if r["start_date_local"] >= cutoff]
    novelty = len({r["sport_type"] for r in recent})
    kud = sum(int(r["kudos_count"] or 0) for r in recent)
    parts = [("streak", min(streak / 12, 1.0), f"{streak} wk"), ("load", 1 - min(abs(acwr[-1] - 1.05) / 1.0, 1.0), f"ACWR {acwr[-1]:.2f}"),
             ("variety", min(novelty / 5, 1.0), f"{novelty} sports"), ("kudos", min(kud / 60, 1.0), f"{kud} in 30d")]
    score = int(round(100 * sum(p[1] for p in parts) / len(parts)))
    img, d = new_card()
    y = header(d, "The Joggernaut Index", kicker=f"{ath.get('firstname', '')} {ath.get('lastname', '')}".strip() or "athlete", right="unscientific")
    bio = (ath.get("bio") or "").strip()
    if bio:
        text(d, (W / 2, y + 14), f'"{bio}"', 20, DARK, bold=False, anchor="ma", maxw=W - 2 * M)
    gauge(d, W / 2, y + 230, 190, score / 100, [(0, 0.33, LIGHT), (0.33, 0.66, WHITE), (0.66, 1.0, DARK)], "0", "100")
    text(d, (W / 2, y + 246), str(score), 84, BLACK, anchor="ma")
    verdict = "hibernating" if score < 30 else "jogging along" if score < 55 else "joggernaut" if score < 80 else "UNSTOPPABLE"
    text(d, (W / 2, y + 336), verdict, 30, BLACK, anchor="ma")
    yy = y + 390
    cw = (W - 2 * M) / 4
    for i, (lbl, v, sub) in enumerate(parts):
        cx = M + cw * i + cw / 2
        progress_bar(d, (cx - 70, yy, cx + 70, yy + 22), v)
        text(d, (cx, yy + 32), lbl, 18, BLACK, anchor="ma")
        text(d, (cx, yy + 54), sub, 16, DARK, bold=False, anchor="ma")
    footer(d, "streak x load-sanity x variety x kudos, equally weighted, as of " + end.strftime("%Y-%m-%d"))
    return img, "#62 Joggernaut index  [Hero]"


def card_sighting(ctx):
    rows = ctx["rows"]
    hit = None
    for r in sorted(rows, key=lambda r: r["start_date_local"], reverse=True):
        h = animal_hits(r)
        if h:
            hit = (r, h[0])
            break
    r, (lbl, ic) = hit
    n = sum(1 for x in rows if x["start_date_local"] <= r["start_date_local"] and any(l == lbl for l, _ in animal_hits(x)))
    img, d = new_card()
    y = header(d, "Trail wildlife", kicker="Latest sighting", right=r["start_date_local"][:10])
    ic(d, 200, y + 190, 260, BLACK)
    text(d, (470, y + 110), lbl, 64, BLACK, anchor="la")
    text(d, (470, y + 190), f"#{n}", 96, BLACK, anchor="la")
    text(d, (470, y + 300), "lifetime sightings", 20, DARK, bold=False, anchor="la")
    sport_icon(r["sport_type"])(d, W - M - 30, y + 30, 44, DARK)
    desc = (r.get("description") or "").strip()
    lines = wrap(d, f'"{desc}"', font(22, False), W - 2 * M - 10, 3)
    yy = y + 372
    for ln in lines:
        text(d, (M, yy), ln, 22, BLACK, bold=False, anchor="la")
        yy += 30
    footer(d, f"during \"{r['name']}\"  -  {(mf(r['distance_km']) or 0) * KM_TO_MI:.1f} mi")
    return img, "#8 Latest wildlife sighting  [Hero]"


CARDS = [
    ("latest", card_latest), ("week", card_week), ("streak-load", card_streak_load),
    ("pr-board", card_pr_board), ("segment-month", card_segment_week), ("route-run", card_route_run),
    ("route-bike", card_route_bike), ("passport", card_passport), ("hearts", card_hearts),
    ("shoes", card_shoes), ("week-2004", card_2004), ("wildlife", card_wildlife),
    ("funny-segment", card_funny_segment), ("hall-of-fame", card_hall_of_fame),
    ("achievements", card_achievements), ("joggernaut", card_joggernaut), ("sighting", card_sighting),
]


# ---------------------------------------------------------------- assembly


def load_ctx():
    rows = load_activities()
    with open(os.path.join(DATA_DIR, "gear.json"), encoding="utf-8") as f:
        gear = json.load(f)
    with open(os.path.join(DATA_DIR, "athlete.json"), encoding="utf-8") as f:
        athlete = json.load(f)
    with open(RUNLOG_CSV, encoding="utf-8-sig") as f:
        runlog = list(csv.DictReader(f))
    asof = max(r["start_date_local"] for r in rows)[:10]
    return {"rows": rows, "segs": load_segments(), "efforts": load_segment_efforts(),
            "gear": gear, "athlete": athlete, "runlog": runlog, "asof": asof}


def verify(img):
    assert img.mode == "L" and img.size == (W, H), (img.mode, img.size)
    bad = set(img.tobytes()) - set(LEVELS)
    assert not bad, f"non-palette levels: {sorted(bad)[:8]}"


def contact_sheet(cards, out):
    cols, scale, cap = 3, 0.5, 44
    cw, ch = int(W * scale), int(H * scale)
    gap = 24
    rows_n = math.ceil(len(cards) / cols)
    sheet = Image.new("L", (cols * cw + (cols + 1) * gap, rows_n * (ch + cap + gap) + gap), WHITE)
    d = ImageDraw.Draw(sheet)
    for i, (idx, cid, img, caption) in enumerate(cards):
        x = gap + (i % cols) * (cw + gap)
        y = gap + (i // cols) * (ch + cap + gap)
        sheet.paste(img.resize((cw, ch), Image.LANCZOS), (x, y))
        d.rectangle([x, y, x + cw, y + ch], outline=BLACK, width=2)
        text(d, (x, y + ch + 8), f"{idx:02d}  {caption}", 15, BLACK, anchor="la", maxw=cw)
        text(d, (x, y + ch + 26), f"cards/{idx:02d}-{cid}.png", 13, DARK, bold=False, anchor="la")
    quantize(sheet).save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--only", help="comma-separated card ids to render")
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "cards"), exist_ok=True)
    ctx = load_ctx()
    only = set(args.only.split(",")) if args.only else None
    done = []
    for i, (cid, fn) in enumerate(CARDS, 1):
        if only and cid not in only:
            continue
        img, caption = fn(ctx)
        img = quantize(img)
        verify(img)
        path = os.path.join(args.out, "cards", f"{i:02d}-{cid}.png")
        img.save(path)
        done.append((i, cid, img, caption))
        print(f"ok  {i:02d} {cid:14s} {caption}")
    if not only:
        contact_sheet(done, os.path.join(args.out, "contact-sheet.png"))
        print(f"wrote {os.path.join(args.out, 'contact-sheet.png')}")


if __name__ == "__main__":
    main()
