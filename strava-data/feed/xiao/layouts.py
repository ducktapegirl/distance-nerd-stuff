"""Composable layouts for the 296x128 panel.

The Sticky's twelve layouts exist so sixty cards cannot drift apart; these
ten exist for the same reason at a quarter of the height. Every one returns
the populated ``svg.Card`` and takes the ``Palette`` explicitly - a layout
never picks a hex, it asks the palette for a role, so the color models on the
proof sheet are the same code with a different table.

Vertical budget, in user units: masthead to y=21, body 27..122. That is
95 px for the whole idea, which is why nothing here has a footer, a
divider, or a second line of anything.
"""

import math

from . import svg as S
from .config import DEFAULT, H, MIN_TEXT, PAD, W, WHITE

TOP_RULE = 21
BODY_TOP = 27
BOT = H - PAD
BODY_H = BOT - BODY_TOP
CX = W / 2


def base(cid, title, summary, kicker, asof, pal=DEFAULT):
    """Masthead and rule, nothing else.

    The date is day-and-month only: "12 SEP" costs 63 px where "12 SEP 2026"
    costs 116, and the difference is whether a twenty-character kicker fits
    at the floor or gets ellipsized.
    """
    c = S.Card(cid, title, summary)
    date = asof.strftime("%d %b").lstrip("0").upper()
    ktext, ksize = S.fit_text(kicker.upper(), MIN_TEXT, W - 2 * PAD - 60, ratio=0.62,
                              tracking=1)
    c.add(
        S.text(PAD, 15, ktext, ksize, "bold", tracking=1, fill=pal.ink),
        S.text(W - PAD, 15, date, MIN_TEXT, anchor="end", fill=pal.ink, tracking=1),
        S.line(PAD, TOP_RULE, W - PAD, TOP_RULE, stroke=pal.ink, sw=2),
    )
    return c


# --- 1. one big numeral, left-aligned -------------------------------------

def hero(c, value, unit=None, sub=None, sub2=None, size=56, x=PAD, y=82, pal=DEFAULT,
         fill=None):
    """A numeral carrying the card, with its captions hanging off its right edge
    or under it. Returns the x where the numeral's advance ends, so a card can
    put a graphic beside it without measuring text."""
    value = str(value)
    c.add(S.text(x, y, value, size, "bold", fill=fill or pal.ink))
    end = x + len(value) * size * 0.60
    if unit:
        c.add(S.text(end + 6, y, unit.upper(), max(MIN_TEXT, int(size * 0.3)), "bold",
                     fill=pal.ink, tracking=1))
        end += 6 + len(unit) * size * 0.3 * 0.68
    if sub:
        st, ss = S.fit_text(sub.upper(), MIN_TEXT, W - 2 * PAD, ratio=0.68, tracking=1)
        c.add(S.text(x, y + 22, st, ss, "bold", fill=pal.ink, tracking=1))
    if sub2:
        st, ss = S.fit_text(sub2.upper(), MIN_TEXT, W - 2 * PAD, ratio=0.68, tracking=1)
        c.add(S.text(x, y + 40, st, ss, fill=pal.ink, tracking=1))
    return end


# --- 2. numbers across ----------------------------------------------------

def stat_row(c, items, y=78, size=28, x0=PAD, x1=W - PAD, pal=DEFAULT, fills=None):
    """``items`` are ``(value, label)``; ``fills`` an optional parallel list of
    colors for the values. No dividers - a 2 px black rule between three
    numbers is heavier than the numbers."""
    n = len(items)
    cw = (x1 - x0) / n
    for i, (value, label) in enumerate(items):
        x = x0 + cw * (i + 0.5)
        vt, vs = S.fit_text(str(value), size, cw - 6)
        lt, ls = S.fit_text(str(label).upper(), MIN_TEXT, cw - 4, ratio=0.62, tracking=1)
        c.add(S.text(x, y, vt, vs, "bold", anchor="middle",
                     fill=(fills[i] if fills and fills[i] else pal.ink)),
              S.text(x, y + 18, lt, ls, anchor="middle", fill=pal.ink, tracking=1))
    return c


# --- 3. labeled bars -------------------------------------------------------

def bars(c, rows, label_w=104, value_w=40, top=BODY_TOP, pal=DEFAULT, fills=None):
    """``rows`` are ``(label, value_text, frac)``, at most four.

    The track is a wash-filled band and the value is ink on top of it - one
    fewer outline than the Sticky draws, because a 2 px outline around a 12 px
    bar would be a quarter of the bar.
    """
    rows = rows[:4]
    if not rows:
        return c
    pitch = min(24, BODY_H / len(rows))
    bh = 12
    bx = PAD + label_w
    bw = W - PAD - value_w - bx
    for i, (label, value, frac) in enumerate(rows):
        y = top + i * pitch + (pitch - bh) / 2
        lt, ls = S.fit_text(str(label), MIN_TEXT, label_w - 6)
        c.add(S.text(PAD, y + bh - 1, lt, ls, "bold", fill=pal.ink))
        c.add(S.rect(bx, y, bw, bh, fill=pal.wash))
        c.add(S.rect(bx, y, max(bw * max(0.0, min(1.0, frac)), 0), bh,
                     fill=(fills[i] if fills and fills[i] else pal.ink)))
        vt, vs = S.fit_text(str(value), MIN_TEXT, value_w - 4)
        c.add(S.text(W - PAD, y + bh - 1, vt, vs, "bold", anchor="end", fill=pal.ink))
    return c


# --- 4. sparkline ----------------------------------------------------------

def spark(c, values, x0=PAD + 4, x1=W - PAD - 4, top=64, bottom=104, labels=None,
          pal=DEFAULT, dot=True):
    """A line with no axis, a baseline rule, and the last point marked.

    The end dot is the accent: on a card about a series, "where it is now"
    is the one thing to look at.
    """
    if len(values) < 2:
        return c
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1.0
    pts = [(x0 + (x1 - x0) * i / (len(values) - 1),
            bottom - (bottom - top) * (v - lo) / rng) for i, v in enumerate(values)]
    c.add(S.line(x0 - 4, bottom + 6, x1 + 4, bottom + 6, stroke=pal.ink, sw=2))
    c.add(S.polyline(pts, stroke=pal.ink, sw=2))
    if dot:
        c.add(S.circle(pts[-1][0], pts[-1][1], 4, fill=pal.accent))
    if labels:
        c.add(S.text(x0 - 4, bottom + 20, str(labels[0]).upper(), MIN_TEXT,
                     fill=pal.ink, tracking=1),
              S.text(x1 + 4, bottom + 20, str(labels[-1]).upper(), MIN_TEXT,
                     anchor="end", fill=pal.ink, tracking=1))
    return c


# --- 5. cell grid ----------------------------------------------------------

def cells(c, colors, per_row, cell, gap, x0=None, top=BODY_TOP, pal=DEFAULT):
    """One rect per entry. ``colors`` are resolved fills; ``None`` draws an
    empty cell as a 2 px ink outline. Returns ``(x0, total_w, rows)`` so the
    caller can hang labels off the grid."""
    total = per_row * cell + (per_row - 1) * gap
    x0 = CX - total / 2 if x0 is None else x0
    rows = math.ceil(len(colors) / per_row)
    for i, col in enumerate(colors):
        row, k = divmod(i, per_row)
        x, y = x0 + k * (cell + gap), top + row * (cell + gap)
        if col is None:
            c.add(S.rect(x + 1, y + 1, cell - 2, cell - 2, fill=WHITE, stroke=pal.ink, sw=2))
        else:
            c.add(S.rect(x, y, cell, cell, fill=col))
    return x0, total, rows


# --- 6. route --------------------------------------------------------------

def route(c, path, pw, ph, region, pal=DEFAULT, sw=3, stroke=None, start=True):
    """Fit a normalized path to ``region`` preserving aspect. The start is
    an accent dot with an ink ring: at this size a bare dot merges with the
    line it sits on."""
    rx, ry, rw, rh = region
    k = min(rw / (pw or 1e-9), rh / (ph or 1e-9))
    ox, oy = rx + (rw - pw * k) / 2, ry + (rh - ph * k) / 2
    pts = [(ox + x * k, oy + y * k) for x, y in path]
    c.add(S.polyline(pts, stroke=stroke or pal.ink, sw=sw))
    if start:
        c.add(S.circle(pts[0][0], pts[0][1], 4.5, fill=pal.accent, stroke=pal.ink, sw=2))
    return pts


# --- 7. then & now ---------------------------------------------------------

def then_now(c, left, right, pal=DEFAULT):
    """Two halves; the left one sits on a wash band - the old log is
    literally in the background. Each half is ``(era, headline, sub)``."""
    half = (W - 2 * PAD - 6) / 2
    c.add(S.rect(PAD, BODY_TOP, half, BODY_H, fill=pal.wash))
    for i, (era, headline, sub) in enumerate((left, right)):
        x = PAD + 8 + i * (half + 6)
        c.add(S.text(x, BODY_TOP + 17, str(era).upper(), MIN_TEXT, "bold",
                     fill=pal.ink, tracking=1))
        ht, hs = S.fit_text(str(headline), 30, half - 16)
        c.add(S.text(x, BODY_TOP + 56, ht, hs, "bold", fill=pal.ink))
        if sub:
            st, ss = S.fit_text(str(sub).upper(), MIN_TEXT, half - 16, ratio=0.62, tracking=1)
            c.add(S.text(x, BODY_TOP + 80, st, ss, fill=pal.ink, tracking=1))
    return c


# --- 8. tally --------------------------------------------------------------

def tally(c, full, partial=0.0, x=None, top=44, mark_h=34, per_group=5, pal=DEFAULT,
          x1=W - PAD):
    """Gate-five tally marks, right-aligned by default so a numeral can own
    the left. The partial mark is the accent: the day in progress."""
    sp, sw, gap = 7, 3, 11
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
    x = (x1 - total) if x is None else x
    for k in groups:
        for i in range(k):
            xx = x + i * sp
            c.add(S.line(xx, top, xx, top + mark_h, stroke=pal.ink, sw=sw, cap="round"))
        if k == per_group:
            c.add(S.line(x - 3, top + mark_h - 5, x + width(k) + 3, top + 5,
                         stroke=pal.ink, sw=sw, cap="round"))
        x += width(k) + gap
    if partial > 0:
        h = mark_h * max(0.15, min(1.0, partial))
        c.add(S.line(x, top + mark_h - h, x, top + mark_h, stroke=pal.accent, sw=sw,
                     cap="round"))
    return c


# --- 9. glyph scoreboard ---------------------------------------------------

def glyph_row(c, items, pal=DEFAULT, glyph_size=36, top=BODY_TOP + 2):
    """``items`` are ``(glyph_fn, count, label, color)``, up to five across:
    a silhouette over its count over its name. The scoreboard reduced to
    what a glance can take in."""
    n = len(items)
    cw = (W - 2 * PAD) / n
    for i, (glyph, count, label, color) in enumerate(items):
        cx = PAD + cw * (i + 0.5)
        if glyph:
            c.add(glyph(cx - glyph_size / 2, top, glyph_size, color or pal.ink))
        c.add(S.text(cx, top + glyph_size + 26, str(count), 24, "bold", anchor="middle",
                     fill=pal.ink))
        lt, ls = S.fit_text(str(label).upper(), MIN_TEXT, cw - 4, ratio=0.68, tracking=1)
        c.add(S.text(cx, top + glyph_size + 44, lt, ls, anchor="middle",
                     fill=pal.ink, tracking=1))
    return c


# --- 10. stacked text lines -------------------------------------------------

def lines(c, rows, x=PAD, max_w=W - 2 * PAD, pal=DEFAULT):
    """``rows`` are ``(y, text, size, weight, fill)``; each is shrunk to fit
    but never ellipsized past its floor without the caller knowing - the
    returned list says what actually printed."""
    out = []
    for y, text, size, weight, fill in rows:
        t, s = S.fit_text(str(text), size, max_w)
        c.add(S.text(x, y, t, s, weight, fill=fill or pal.ink))
        out.append(t)
    return out
