"""Composable card layouts.

Fifty-six hand-laid-out cards would drift apart within a week. These eight
layouts carry the shared structure - masthead, rules, footer, and the handful
of arrangements the ideas actually reduce to - so ``cards.py`` is mostly data
binding.

Every layout returns a populated ``svg.Card``. They compose: a card can call a
layout and then ``.add()`` extra marks on top.
"""

import math

from . import svg as S
from .config import BLACK, DARK, H, LIGHT, MIN_TEXT, PAD, W, WHITE

TOP_RULE = 74
BOT_RULE = H - 62
CX = W / 2
BODY_TOP = TOP_RULE + 18
BODY_H = BOT_RULE - TOP_RULE - 36


def base(cid, title, summary, kicker, asof):
    """A card with the masthead and rules, and nothing else."""
    c = S.Card(cid, title, summary)
    # Reserve the right-hand date slot; a long kicker shrinks/ellipsizes
    # rather than running into it.
    ktext, ksize = S.fit_text(kicker.upper(), 26, W - 2 * PAD - 210, ratio=0.68,
                              tracking=3)
    c.add(
        S.text(PAD, 46, ktext, ksize, "bold", tracking=3),
        S.text(W - PAD, 46, asof.strftime("%-d %b %Y").upper(), 26,
               anchor="end", fill=DARK, tracking=2),
        S.line(PAD, TOP_RULE, W - PAD, TOP_RULE, sw=4),
        S.line(PAD, BOT_RULE, W - PAD, BOT_RULE, stroke=LIGHT, sw=3),
    )
    return c


def footer(c, s, size=26):
    if not s:
        return c
    s, size = S.fit_text(s, size, W - 2 * PAD)
    return c.add(S.text(PAD, H - 22, s, size, fill=DARK, tracking=1))


# --- 1. one huge numeral ------------------------------------------------

def hero_number(c, value, unit=None, sub=None, glyph=None, size=150):
    """A single number carrying the whole card. Centred, with an optional
    unit beside it and a caption beneath."""
    y = 236 if sub else 262
    c.add(S.text(CX, y, str(value), size, "bold", anchor="middle"))
    if unit:
        # Sits to the right of the numeral, whose advance width we
        # approximate - there is no text measurement at build time.
        half = len(str(value)) * size * 0.30
        c.add(S.text(CX + half + 16, y, unit.upper(), max(MIN_TEXT, size * 0.30),
                     "bold", fill=DARK))
    if sub:
        st, ss = S.fit_text(sub.upper(), 32, W - 2 * PAD, tracking=4)
        c.add(S.text(CX, y + 66, st, ss, "bold", anchor="middle", tracking=4))
    if glyph:
        c.add(glyph(PAD, 96, 96))
    return c


def stat_trio(c, items):
    """Three numbers across, for 'miles / hours / feet'-shaped payloads."""
    n = len(items)
    for i, (value, label) in enumerate(items):
        x = PAD + (W - 2 * PAD) * (i + 0.5) / n
        vt, vs = S.fit_text(str(value), 84, (W - 2 * PAD) / n - 16)
        lt, ls = S.fit_text(label.upper(), 28, (W - 2 * PAD) / n - 12, tracking=3)
        c.add(S.text(x, 250, vt, vs, "bold", anchor="middle"),
              S.text(x, 296, lt, ls, "bold", anchor="middle", fill=DARK, tracking=3))
        if i:
            c.add(S.line(PAD + (W - 2 * PAD) * i / n, 180,
                         PAD + (W - 2 * PAD) * i / n, 320, stroke=LIGHT, sw=3))
    return c


# --- 2. labelled bars ---------------------------------------------------

def bar_rows(c, rows, label_w=250, value_w=180, note=None):
    """``rows`` are ``(label, value_text, frac)`` with ``frac`` in 0..1.

    Up to five rows fit; beyond that the type has to drop under the 26 px
    floor, so callers must trim rather than relying on this to shrink.
    """
    rows = rows[:4 if note else 5]
    if not rows:
        return c
    top = BODY_TOP + (14 if note else 0)
    pitch = min(62, (BODY_H - (14 if note else 0)) / len(rows))
    bh = min(34, pitch - 22)
    bx = PAD + label_w
    bw = W - PAD - value_w - bx
    for i, (label, value, frac) in enumerate(rows):
        y = top + i * pitch
        lt, ls = S.fit_text(str(label), 28, label_w - 12)
        c.add(S.text(PAD, y + bh - 8, lt, ls, "bold"))
        c.add(S.rect(bx, y, bw, bh, fill=WHITE, stroke=LIGHT, sw=3))
        c.add(S.rect(bx + 3, y + 3, max((bw - 6) * max(0.0, min(1.0, frac)), 0),
                     bh - 6, fill=BLACK))
        vt, vs = S.fit_text(str(value), 28, value_w - 12)
        c.add(S.text(W - PAD, y + bh - 8, vt, vs, "bold", anchor="end", fill=DARK))
    if note:
        c.add(S.text(PAD, BOT_RULE - 8, note.upper(), 26, "bold", fill=DARK, tracking=2))
    return c


# --- 3. a vs b ----------------------------------------------------------

def two_up(c, left, right, delta=None):
    """``left``/``right`` are ``(label, value, sub)``. A delta pill sits between."""
    for i, (label, value, sub) in enumerate((left, right)):
        x = PAD + (W - 2 * PAD) * (0.25 if i == 0 else 0.75)
        lt, ls = S.fit_text(label.upper(), 28, 300, tracking=3)
        vt, vs = S.fit_text(str(value), 88, 320)
        c.add(S.text(x, 168, lt, ls, "bold", anchor="middle", tracking=3),
              S.text(x, 262, vt, vs, "bold", anchor="middle"))
        if sub:
            stx, sts = S.fit_text(str(sub), 28, 320)
            c.add(S.text(x, 306, stx, sts, anchor="middle", fill=DARK))
    c.add(S.line(CX, 140, CX, 330, stroke=LIGHT, sw=3))
    if delta:
        dt, ds = S.fit_text(str(delta).upper(), 28, 240, tracking=2)
        w = len(dt) * ds * 0.62 + 28
        c.add(S.rect(CX - w / 2, 352, w, 42, fill=BLACK),
              S.text(CX, 382, dt, ds, "bold", anchor="middle", fill=WHITE, tracking=2))
    return c


# --- 4. words -----------------------------------------------------------

def text_card(c, headline, body=None, tag=None, headline_size=62):
    """Headline plus wrapped body. Wrapping is by character budget - there is
    no text measurement at build time - and caps at three lines."""
    ht, hs = S.fit_text(str(headline), headline_size, W - 2 * PAD)
    c.add(S.text(PAD, 158, ht, hs, "bold"))
    if body:
        budget = int((W - 2 * PAD) / (30 * 0.55))
        y, lines, cur = 222, 0, ""
        for word in str(body).split():
            trial = f"{cur} {word}".strip()
            if len(trial) > budget:
                c.add(S.text(PAD, y, cur, 30, fill=DARK))
                y += 42
                lines += 1
                cur = word
                if lines == 2:
                    break
            else:
                cur = trial
        if lines < 3 and cur:
            c.add(S.text(PAD, y, cur if lines < 2 else cur[:budget - 1] + "…",
                         30, fill=DARK))
    if tag:
        tt, ts = S.fit_text(str(tag).upper(), 28, W - 2 * PAD, tracking=2)
        c.add(S.text(PAD, BOT_RULE - 18, tt, ts, "bold", tracking=2))
    return c


# --- 5. sparkline -------------------------------------------------------

def spark(c, values, labels=None, headline=None, sub=None):
    """A step line with no axis and a filled dot on the last point."""
    if len(values) < 2:
        return c
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1.0
    x0, x1, y0, y1 = PAD + 10, W - PAD - 10, 250, 356
    pts = [(x0 + (x1 - x0) * i / (len(values) - 1),
            y1 - (y1 - y0) * (v - lo) / rng) for i, v in enumerate(values)]
    c.add(S.line(x0, y1 + 14, x1, y1 + 14, stroke=LIGHT, sw=3))
    c.add(S.polyline(pts, sw=4))
    c.add(S.circle(pts[-1][0], pts[-1][1], 11, fill=BLACK))
    if headline:
        c.add(S.text(PAD, 172, str(headline), 92, "bold"))
    if sub:
        st, ss = S.fit_text(str(sub).upper(), 28, 420, tracking=2)
        c.add(S.text(W - PAD, 172, st, ss, "bold", anchor="end", fill=DARK, tracking=2))
    if labels:
        c.add(S.text(x0, y1 + 48, str(labels[0]).upper(), 26, fill=DARK, tracking=2),
              S.text(x1, y1 + 48, str(labels[-1]).upper(), 26, anchor="end",
                     fill=DARK, tracking=2))
    return c


# --- 6. cell grid -------------------------------------------------------

def cell_grid(c, levels, per_row=15, cell=40, gap=8, headline=None, labels=None,
              top=232):
    """``levels`` are 0..1 quantities; 0 draws a hollow cell, anything else
    fills from the tone ramp. Used for day strips and route mosaics alike."""
    total = per_row * cell + (per_row - 1) * gap
    x0 = CX - total / 2
    rows = math.ceil(len(levels) / per_row)
    for i, lv in enumerate(levels):
        row, col = divmod(i, per_row)
        x, y = x0 + col * (cell + gap), top + row * (cell + gap)
        if lv <= 0:
            c.add(S.rect(x, y, cell, cell, fill=WHITE, stroke=LIGHT, sw=3))
        else:
            c.add(S.rect(x, y, cell, cell, fill=S.tone(lv)))
    if headline:
        c.add(S.text(CX, top - 42, str(headline), 92, "bold", anchor="middle"))
    if labels:
        y = top + rows * cell + (rows - 1) * gap + 40
        c.add(S.text(x0, y, str(labels[0]).upper(), 26, fill=DARK, tracking=2),
              S.text(x0 + total, y, str(labels[-1]).upper(), 26, anchor="end",
                     fill=DARK, tracking=2))
    return c


# --- 7. banded dial -----------------------------------------------------

def dial(c, value, vmax, bands, readout, band_label, ticks=()):
    """A half-circle gauge. ``bands`` are ``(lo, hi, tone_level)``; more ink
    means more concern, which reads as a gradient with no colour key."""
    cx, cy, r = CX, 298, 142

    def ang(v):
        return 180 + 180 * max(0.0, min(vmax, v)) / vmax

    for lo, hi, level in bands:
        c.add(S.arc(cx, cy, r, ang(lo), ang(hi), stroke=S.tone(level), sw=34))
    c.add(S.arc(cx, cy, r, 180, 360, stroke=BLACK, sw=3))
    for t in ticks:
        rad = math.radians(ang(t))
        c.add(S.line(cx + (r - 17) * math.cos(rad), cy + (r - 17) * math.sin(rad),
                     cx + (r + 17) * math.cos(rad), cy + (r + 17) * math.sin(rad),
                     stroke=BLACK, sw=3))
        c.add(S.text(cx + (r + 46) * math.cos(rad), cy + (r + 46) * math.sin(rad) + 9,
                     f"{t:g}", 26, fill=DARK, anchor="middle"))
    # The needle stops well short of the rim so it never crosses the readout.
    th = math.radians(ang(value))
    c.add(
        S.line(cx, cy, cx + (r * 0.60) * math.cos(th), cy + (r * 0.60) * math.sin(th),
               sw=9, cap="round"),
        S.circle(cx, cy, 14, fill=BLACK),
        S.text(cx, cy + 72, str(readout), 84, "bold", anchor="middle"),
    )
    if band_label:
        c.add(S.text(cx, cy + 108, str(band_label).upper(), 28, "bold",
                     anchor="middle", tracking=5))
    return c


# --- 8. route -----------------------------------------------------------

def route_card(c, path, pw, ph, lines=(), region=None):
    """Fit a normalised path to a rectangle, preserving aspect. Letterboxing a
    wide, flat route into a square wastes most of the card."""
    rx, ry, rw, rh = region or (372, BODY_TOP, W - PAD - 372, BODY_H)
    k = min(rw / (pw or 1e-9), rh / (ph or 1e-9))
    ox, oy = rx + (rw - pw * k) / 2, ry + (rh - ph * k) / 2
    pts = [(ox + x * k, oy + y * k) for x, y in path]
    c.add(S.polyline(pts, sw=4))
    c.add(S.circle(pts[0][0], pts[0][1], 9, fill=WHITE, stroke=BLACK, sw=4))
    y = TOP_RULE + 74
    for text, size, weight, fill in lines:
        t, s = S.fit_text(str(text), size, rx - PAD - 20)
        c.add(S.text(PAD, y, t, s, weight, fill=fill))
        y += size + 16
    return c
