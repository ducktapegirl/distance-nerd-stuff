"""Four-color SVG primitives for the 296x128 panel.

The same shapes as ``feed.svg``, at this panel's floors, with one rule the
Sticky never needed: **every color is validated against the four the panel
can show.** There is no gray here and no dither ramp, so a ``#555`` that
slipped through would be quantized by the device into whichever of black,
red or white its algorithm liked - the card would look different on the
panel than on the proof sheet, which is the one thing a proof sheet must not
do. ``_col`` raises instead.

The glyph builders (runner, bike, shoe, mountain, the animals) are imported
from ``feed.svg`` unchanged: they are drawn in a 100-unit box and scaled, so
they carry no panel size, and their default colors are plain black and white.
Only the sun is redrawn, because the Sticky's darkens its disc with the tone
ramp and this panel has none.
"""

import math

from ..svg import (ANIMAL_GLYPHS, esc, glyph_bike, glyph_mountain,  # noqa: F401
                   glyph_runner, glyph_shoe)
from .config import BLACK, FONT, H, MIN_STROKE, MIN_TEXT, PALETTE, W, WHITE

_ALLOWED = set(PALETTE) | {"none"}


def _col(c):
    """A color the panel can show, or a ValueError now rather than a surprise later."""
    if c is None:
        return "none"
    if c not in _ALLOWED:
        raise ValueError(f"{c!r} is not one of the panel's four colors {PALETTE}")
    return c


def _sw(sw):
    return max(sw, MIN_STROKE)


# --- primitives ----------------------------------------------------------

def text(x, y, s, size=MIN_TEXT, weight="normal", anchor="start",
         fill=BLACK, tracking=0, family=FONT):
    if size < MIN_TEXT:
        raise ValueError(f"text {size}px is below the {MIN_TEXT}px legibility floor: {s!r}")
    ls = f' letter-spacing="{tracking}"' if tracking else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{_col(fill)}"{ls}>'
            f'{esc(s)}</text>')


def rect(x, y, w, h, fill=BLACK, stroke=None, sw=MIN_STROKE, rx=0):
    st = f' stroke="{_col(stroke)}" stroke-width="{_sw(sw)}"' if stroke else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" '
            f'rx="{rx}" fill="{_col(fill)}"{st}/>')


def line(x1, y1, x2, y2, stroke=BLACK, sw=MIN_STROKE, dash=None, cap="butt"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{_col(stroke)}" stroke-width="{_sw(sw)}" stroke-linecap="{cap}"{d}/>')


def circle(cx, cy, r, fill=BLACK, stroke=None, sw=MIN_STROKE):
    st = f' stroke="{_col(stroke)}" stroke-width="{_sw(sw)}"' if stroke else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{_col(fill)}"{st}/>'


def polyline(pts, stroke=BLACK, sw=MIN_STROKE, fill="none", dash=None):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polyline points="{d}" fill="{_col(fill)}" stroke="{_col(stroke)}" '
            f'stroke-width="{_sw(sw)}" stroke-linejoin="round" stroke-linecap="round"{da}/>')


def polygon(pts, fill=BLACK, stroke=None, sw=MIN_STROKE):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    st = f' stroke="{_col(stroke)}" stroke-width="{_sw(sw)}"' if stroke else ""
    return f'<polygon points="{d}" fill="{_col(fill)}"{st}/>'


def arc(cx, cy, r, a0, a1, stroke=BLACK, sw=MIN_STROKE, cap="butt"):
    """Stroked arc between two angles in degrees, 0 = east, growing clockwise."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if abs(a1 - a0) > 180 else 0
    return (f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {large},1 {x1:.1f},{y1:.1f}" '
            f'fill="none" stroke="{_col(stroke)}" stroke-width="{_sw(sw)}" '
            f'stroke-linecap="{cap}"/>')


def fit_text(s, size, max_w, min_size=MIN_TEXT, ratio=0.55, tracking=0):
    """Shrink ``size`` until ``s`` fits ``max_w``, then ellipsize if it still won't.

    Same width approximation as the Sticky's (``ratio`` x font size per
    glyph, plus tracking) and for the same reason: there is no text
    measurement at build time.
    """
    def width(txt, sz):
        return len(txt) * (sz * ratio + tracking)

    while size > min_size and width(s, size) > max_w:
        size -= 1
    per = size * ratio + tracking
    budget = int(max_w / per) if per else len(s)
    if len(s) > budget:
        s = s[: max(1, budget - 1)].rstrip() + "…"
    return s, size


def wrap_text(s, size, max_w, max_lines=2, ratio=0.55):
    """Greedy word wrap by character budget, capped at ``max_lines``."""
    budget = max(1, int(max_w / (size * ratio)))
    lines, cur = [], ""
    for word in str(s).split():
        trial = f"{cur} {word}".strip()
        if len(trial) <= budget:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = word
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if not lines:
        return [""]
    if len(" ".join(lines)) < len(" ".join(str(s).split())):
        lines[-1] = lines[-1][: max(1, budget - 1)].rstrip() + "…"
    return lines


def triangle(cx, cy, size, direction="up", fill=BLACK):
    """A trend arrowhead as geometry - the same reasoning as the Sticky's."""
    h = size / 2.0
    if direction == "up":
        pts = [(cx, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
    elif direction == "down":
        pts = [(cx, cy + h), (cx + h, cy - h), (cx - h, cy - h)]
    else:
        return rect(cx - h, cy - size * 0.16, size, size * 0.32, fill=fill)
    return polygon(pts, fill=fill)


def glyph_sun(x, y, size, color=BLACK, disc=WHITE, rays=8):
    """A rayed sun with a solid disc.

    The Sticky's darkens its disc along the tone ramp; here the disc is one of
    the four colors, chosen by the caller - a yellow sun for an ordinary
    week, red for a scorcher. Rays are 7 units in the 100-box, so at 44 px
    they land at 3 px, above the floor.
    """
    r = 27.0
    body = [f'<circle cx="50" cy="50" r="{r}" fill="{_col(disc)}" '
            f'stroke="{_col(color)}" stroke-width="6"/>']
    for i in range(rays):
        th = math.radians(i * 360.0 / rays - 90)
        x0, y0 = 50 + (r + 9) * math.cos(th), 50 + (r + 9) * math.sin(th)
        x1, y1 = 50 + (r + 21) * math.cos(th), 50 + (r + 21) * math.sin(th)
        body.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
                    f'stroke="{_col(color)}" stroke-width="7" stroke-linecap="round"/>')
    s = size / 100.0
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.4f})" '
            f'fill="none">{"".join(body)}</g>')


# --- canvas --------------------------------------------------------------

class Card:
    """One 296x128 four-color screen."""

    def __init__(self, cid, title, summary, idea=None, family=None, recipe=None):
        self.id = cid
        self.title = title
        self.summary = summary
        self.idea = idea
        self.family = family
        self.recipe = recipe
        self.parts = []

    def add(self, *markup):
        self.parts.extend(markup)
        return self

    def svg(self, standalone=False):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}">' if standalone else
                f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
        return head + rect(0, 0, W, H, fill=WHITE) + "".join(self.parts) + "</svg>"
