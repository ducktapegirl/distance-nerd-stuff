"""Composable card layouts.

Fifty-six hand-laid-out cards would drift apart within a week. These eight
layouts carry the shared structure - masthead, rules, footer, and the handful
of arrangements the ideas actually reduce to - so ``cards.py`` is mostly data
binding.

Every layout returns a populated ``svg.Card``. They compose: a card can call a
layout and then ``.add()`` extra marks on top.
"""

import math

from . import fmt as F
from . import svg as S
from .config import BLACK, DARK, H, LIGHT, MIN_TEXT, PAD, W, WHITE

TOP_RULE = 74
# Was H - 62, with a rule drawn on it and a line of footer text underneath.
# The footers are gone, so this is now just the bottom bound of the body and
# nothing is drawn on it - a rule with nothing under it reads as a mistake.
BOT_RULE = H - PAD
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
        S.text(W - PAD, 46, F.day(asof).upper(), 26,
               anchor="end", fill=DARK, tracking=2),
        S.line(PAD, TOP_RULE, W - PAD, TOP_RULE, sw=4),
    )
    return c


# --- 1. one huge numeral ------------------------------------------------

def hero_number(c, value, unit=None, sub=None, glyph=None, size=150):
    """A single number carrying the whole card. Centred, with an optional
    unit beside it and a caption beneath."""
    # Centred on the body, which now runs to BOT_RULE rather than stopping
    # where the footer band began.
    y = 280 if sub else 300
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


def stat_trio(c, items, baseline=269, size=84):
    """Three numbers across, for 'miles / hours / feet'-shaped payloads.

    ``baseline`` lifts or drops the whole row, so a card that also carries a
    sparkline can put the two in different bands instead of on top of each
    other.
    """
    n = len(items)
    for i, (value, label) in enumerate(items):
        x = PAD + (W - 2 * PAD) * (i + 0.5) / n
        vt, vs = S.fit_text(str(value), size, (W - 2 * PAD) / n - 16)
        lt, ls = S.fit_text(label.upper(), 28, (W - 2 * PAD) / n - 12, tracking=3)
        c.add(S.text(x, baseline, vt, vs, "bold", anchor="middle"),
              S.text(x, baseline + 46, lt, ls, "bold", anchor="middle",
                     fill=DARK, tracking=3))
        if i:
            c.add(S.line(PAD + (W - 2 * PAD) * i / n, baseline - 70,
                         PAD + (W - 2 * PAD) * i / n, baseline + 70,
                         stroke=LIGHT, sw=3))
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
    # The cap tracks BODY_H: five rows should reach the bottom of the body
    # rather than stopping where the old footer band used to begin.
    pitch = min(68, (BODY_H - (14 if note else 0)) / len(rows))
    bh = min(38, pitch - 24)
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

def spark(c, values, labels=None, headline=None, sub=None, top=250, bottom=356):
    """A step line with no axis and a filled dot on the last point.

    ``top``/``bottom`` bound the plot band; the default is the band every
    sparkline-only card uses. A card that stacks the spark under something
    else passes its own.
    """
    if len(values) < 2:
        return c
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1.0
    x0, x1, y0, y1 = PAD + 10, W - PAD - 10, top, bottom
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
        c.add(S.text(x0, y1 + 42, str(labels[0]).upper(), 26, fill=DARK, tracking=2),
              S.text(x1, y1 + 42, str(labels[-1]).upper(), 26, anchor="end",
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


# --- 9. route over a stat grid ------------------------------------------

def route_stats(c, path, pw, ph, stats):
    """A route across the top, a 4x2 grid of numbers under it.

    The one card that earns two ideas at once: the shape of the ride and what
    it cost. ``stats`` are ``(value, label)`` pairs, up to eight.

    The route gets whatever the grid does not need, rather than a fixed height:
    two rows of numbers plus their labels have to clear ``BOT_RULE``, or the
    second row's labels land on top of the footer.
    """
    stats = list(stats)[:8]
    rows = 1 if len(stats) <= 4 else 2
    row_h = 74
    grid_top = BOT_RULE - rows * row_h
    ry, rh = TOP_RULE + 12, grid_top - (TOP_RULE + 12) - 14

    k = min((W - 2 * PAD) / (pw or 1e-9), rh / (ph or 1e-9))
    ox, oy = CX - pw * k / 2, ry + (rh - ph * k) / 2
    pts = [(ox + x * k, oy + y * k) for x, y in path]
    c.add(S.polyline(pts, sw=5))
    c.add(S.circle(pts[0][0], pts[0][1], 10, fill=WHITE, stroke=BLACK, sw=4))
    c.add(S.rect(pts[-1][0] - 8, pts[-1][1] - 8, 16, 16, fill=BLACK))

    cols = 4
    cw = (W - 2 * PAD) / cols
    for i, (value, label) in enumerate(stats):
        row, col = divmod(i, cols)
        x = PAD + cw * (col + 0.5)
        y = grid_top + row * row_h
        vt, vs = S.fit_text(str(value), 44, cw - 14)
        lt, ls = S.fit_text(str(label).upper(), 26, cw - 10, tracking=2)
        c.add(S.text(x, y + 42, vt, vs, "bold", anchor="middle"),
              S.text(x, y + 68, lt, ls, anchor="middle", fill=DARK, tracking=2))
    for col in range(1, cols):
        x = PAD + cw * col
        c.add(S.line(x, grid_top + 4, x, BOT_RULE - 6, stroke=LIGHT, sw=3))
    return c


# --- 10. two-column bar rows --------------------------------------------

def bar_grid(c, rows, cols=2, glyphs=None):
    """``bar_rows`` folded into two columns, so ten short rows fit where five
    long ones did. ``rows`` are ``(label, value_text, frac)``; ``glyphs`` is an
    optional parallel list of ``fn(x, y, size)`` drawn at the row's left."""
    if not rows:
        return c
    per_col = math.ceil(len(rows) / cols)
    cw = (W - 2 * PAD) / cols
    pitch = min(66, BODY_H / per_col)
    gw = 56 if glyphs else 0
    for i, (label, value, frac) in enumerate(rows):
        col, row = divmod(i, per_col)
        x0 = PAD + cw * col
        y = BODY_TOP + row * pitch
        if glyphs and glyphs[i]:
            c.add(glyphs[i](x0, y - 4, 52))
        lt, ls = S.fit_text(str(label), 28, cw - gw - 90)
        c.add(S.text(x0 + gw, y + 22, lt, ls, "bold"))
        vt, vs = S.fit_text(str(value), 28, 80)
        c.add(S.text(x0 + cw - 24, y + 22, vt, vs, "bold", anchor="end", fill=DARK))
        bw = cw - gw - 40
        c.add(S.rect(x0 + gw, y + 30, bw, 14, fill=WHITE, stroke=LIGHT, sw=3))
        c.add(S.rect(x0 + gw + 3, y + 33, max((bw - 6) * max(0.0, min(1.0, frac)), 0),
                     8, fill=BLACK))
    return c


# --- 12. tally ------------------------------------------------------------

def tally(c, full, partial=0.0, top=246, mark_h=104, per_group=5):
    """Gate-five tally marks: four uprights and a diagonal, one per unit.

    A count you read the way you'd read it scratched on a wall - the groups do
    the arithmetic, so nobody counts eleven separate strokes. ``partial`` draws
    a final short mark rising from the baseline, which is how a fraction of a
    unit reads without a legend.
    """
    sp, sw, gap = 26, 9, 46
    groups = []
    left = int(full)
    while left > 0:
        groups.append(min(per_group, left))
        left -= min(per_group, left)

    def width(k):
        return (k - 1) * sp if k > 1 else 0

    total = sum(width(k) for k in groups) + gap * max(0, len(groups) - 1)
    if partial > 0:
        total += gap
    x = CX - total / 2
    for k in groups:
        for i in range(k):
            xx = x + i * sp
            c.add(S.line(xx, top, xx, top + mark_h, sw=sw, cap="round"))
        if k == per_group:
            # The diagonal overhangs both ends so the group reads as struck
            # through rather than as a fifth upright leaning over.
            c.add(S.line(x - 9, top + mark_h - 14, x + width(k) + 9, top + 14,
                         sw=sw, cap="round"))
        x += width(k) + gap
    if partial > 0:
        h = mark_h * max(0.12, min(1.0, partial))
        c.add(S.line(x, top + mark_h - h, x, top + mark_h, sw=sw, stroke=DARK,
                     cap="round"))
    return c


# --- 11. then & now -----------------------------------------------------

def then_now(c, top, bottom):
    """A shaded band of the past over an unshaded present.

    ``top``/``bottom`` are ``(era, headline, sub, lines)``. The band is the
    whole argument of the card: the old log is literally in the background.

    The two halves are sized from ``BOT_RULE`` rather than from a fixed band
    height, because the lower half has the same four rows to fit and no shaded
    box to hide in - laid out by eye it runs its subtitle through the footer.
    """
    gap = 18
    avail = BOT_RULE - (TOP_RULE + 8) - gap
    band_h = int(avail * 0.53)
    tops = (TOP_RULE + 8, TOP_RULE + 8 + band_h + gap)
    heights = (band_h, avail - band_h)
    c.add(S.rect(PAD, tops[0], W - 2 * PAD, band_h, fill=LIGHT))
    for i, (era, headline, sub, lines) in enumerate((top, bottom)):
        y0, bh = tops[i], heights[i]
        c.add(S.text(PAD + 16, y0 + 34, str(era).upper(), 28, "bold", tracking=3))
        ht, hs = S.fit_text(str(headline), 58, 330)
        c.add(S.text(PAD + 16, y0 + 92, ht, hs, "bold"))
        if sub:
            st, ss = S.fit_text(str(sub), 28, 330)
            c.add(S.text(PAD + 16, y0 + 124, st, ss, fill=DARK))
        # However many 36 px rows are left after the era heading.
        room = max(0, int((bh - 40) // 36))
        y = y0 + 34
        for text in list(lines)[:room]:
            lt, ls = S.fit_text(str(text), 28, W - PAD - 420)
            c.add(S.text(PAD + 400, y, lt, ls))
            y += 36
    return c
