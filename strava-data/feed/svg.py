"""1-bit / 4-tone SVG primitives, the dither ramp, and the glyph set.

Everything is hand-generated SVG rather than Plotly: the panel has no
JavaScript, no CDN, no hover, and four grey levels. Plotly gives us none of
what we need here and costs a 3 MB runtime to say so.

Cards render as a whole 800x480 ``<svg>``, so layout is exact user units - no
CSS cascade, no font metrics surprise, no scrolling.
"""

from .config import BLACK, DARK, FONT, LIGHT, MIN_STROKE, MIN_TEXT, W, H, WHITE


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# --- dither ramp ---------------------------------------------------------
# The panel's four native tones, extended with three ordered-dither patterns
# for the steps in between, giving a usable 7-step sequential ramp. Every fill
# in the output is one of these, so nothing depends on the device dithering an
# arbitrary colour for us.
DITHER_DEFS = f"""<defs>
  <pattern id="d25" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="4" fill="{WHITE}"/><rect width="2" height="2" fill="{BLACK}"/>
  </pattern>
  <pattern id="d50" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="4" fill="{WHITE}"/>
    <rect width="2" height="2" fill="{BLACK}"/><rect x="2" y="2" width="2" height="2" fill="{BLACK}"/>
  </pattern>
  <pattern id="d75" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="4" fill="{BLACK}"/><rect width="2" height="2" fill="{WHITE}"/>
  </pattern>
</defs>"""

RAMP = [WHITE, "url(#d25)", LIGHT, "url(#d50)", DARK, "url(#d75)", BLACK]


def tone(level):
    """Pick a ramp step from a 0..1 quantity. 0 = white, 1 = black."""
    i = int(round(max(0.0, min(1.0, level)) * (len(RAMP) - 1)))
    return RAMP[i]


# --- primitives ----------------------------------------------------------

def text(x, y, s, size=MIN_TEXT, weight="normal", anchor="start",
         fill=BLACK, tracking=0, family=FONT):
    if size < MIN_TEXT:
        raise ValueError(f"text {size}px is below the {MIN_TEXT}px legibility floor: {s!r}")
    ls = f' letter-spacing="{tracking}"' if tracking else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}"{ls}>{esc(s)}</text>')


def rect(x, y, w, h, fill=BLACK, stroke=None, sw=MIN_STROKE, rx=0):
    st = f' stroke="{stroke}" stroke-width="{max(sw, MIN_STROKE)}"' if stroke else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" '
            f'rx="{rx}" fill="{fill}"{st}/>')


def line(x1, y1, x2, y2, stroke=BLACK, sw=MIN_STROKE, dash=None, cap="butt"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{max(sw, MIN_STROKE)}" '
            f'stroke-linecap="{cap}"{d}/>')


def circle(cx, cy, r, fill=BLACK, stroke=None, sw=MIN_STROKE):
    st = f' stroke="{stroke}" stroke-width="{max(sw, MIN_STROKE)}"' if stroke else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{st}/>'


def polyline(pts, stroke=BLACK, sw=MIN_STROKE, fill="none", dash=None):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polyline points="{d}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{max(sw, MIN_STROKE)}" stroke-linejoin="round" '
            f'stroke-linecap="round"{da}/>')


def polygon(pts, fill=BLACK, stroke=None, sw=MIN_STROKE):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    st = f' stroke="{stroke}" stroke-width="{max(sw, MIN_STROKE)}"' if stroke else ""
    return f'<polygon points="{d}" fill="{fill}"{st}/>'


def arc(cx, cy, r, a0, a1, stroke=BLACK, sw=MIN_STROKE, cap="butt"):
    """Stroked arc between two angles in degrees, 0 = east, growing clockwise."""
    import math
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if abs(a1 - a0) > 180 else 0
    return (f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {large},1 {x1:.1f},{y1:.1f}" '
            f'fill="none" stroke="{stroke}" stroke-width="{max(sw, MIN_STROKE)}" '
            f'stroke-linecap="{cap}"/>')


def fit_text(s, size, max_w, min_size=MIN_TEXT, ratio=0.55, tracking=0):
    """Shrink ``size`` until ``s`` fits ``max_w``, then ellipsize if it still won't.

    ``ratio`` is an average glyph-width-to-font-size factor for a humanist
    sans - close enough to keep long names inside a card without measuring
    text, which we cannot do at build time. ``tracking`` must be passed
    whenever the caller sets letter-spacing: at 26 px with tracking 4 it adds
    a sixth to every advance, which is the difference between fitting and
    running off the edge.
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
    """Greedy word wrap by character budget, capped at ``max_lines``.

    Same approximation as ``fit_text`` and for the same reason - there is no
    text measurement at build time. The last line is ellipsized only if the
    text genuinely does not fit in ``max_lines``.
    """
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
    # Anything that did not fit gets an ellipsis on the final line.
    if len(" ".join(lines)) < len(" ".join(str(s).split())):
        lines[-1] = lines[-1][: max(1, budget - 1)].rstrip() + "…"
    return lines


def triangle(cx, cy, size, direction="up", fill=BLACK):
    """A trend arrowhead drawn as geometry, not as a font glyph.

    "▲" is roughly a full em wide where the fallback font has it at all, so
    fit_text's width estimate is badly wrong for it and it can render as a box
    on a panel with no webfonts. A polygon is neither.
    """
    h = size / 2.0
    if direction == "up":
        pts = [(cx, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
    elif direction == "down":
        pts = [(cx, cy + h), (cx + h, cy - h), (cx - h, cy - h)]
    else:                                   # flat: a bar, not an arrowhead
        return rect(cx - h, cy - size * 0.16, size, size * 0.32, fill=fill)
    return polygon(pts, fill=fill)


# --- glyphs --------------------------------------------------------------
# Solid silhouettes in a 100x100 box. Interior detail below ~3 px vanishes on
# e-ink, so these are deliberately chunky: strokes, not outlines.

def _g(body, x, y, size, colour=BLACK):
    s = size / 100.0
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.4f})" '
            f'stroke="{colour}" fill="none" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</g>')


def glyph_runner(x, y, size, colour=BLACK):
    body = (
        f'<circle cx="52" cy="13" r="10" fill="{colour}" stroke="none"/>'
        '<path d="M52 26 L43 50" stroke-width="9"/>'
        '<path d="M45 33 L68 27" stroke-width="8"/>'
        '<path d="M45 36 L26 48" stroke-width="8"/>'
        '<path d="M43 50 L62 62 L69 85" stroke-width="9"/>'
        '<path d="M43 50 L27 68 L12 66" stroke-width="9"/>'
    )
    return _g(body, x, y, size, colour)


def glyph_bike(x, y, size, colour=BLACK):
    body = (
        '<circle cx="21" cy="68" r="19" stroke-width="7"/>'
        '<circle cx="79" cy="68" r="19" stroke-width="7"/>'
        '<path d="M21 68 L45 68 L60 38 L79 68" stroke-width="7"/>'
        '<path d="M45 68 L60 38" stroke-width="7"/>'
        '<path d="M45 68 L38 42 L52 42" stroke-width="7"/>'
        '<path d="M60 38 L72 34" stroke-width="7"/>'
    )
    return _g(body, x, y, size, colour)


def glyph_shoe(x, y, size, colour=BLACK, fill_frac=None, fill_colour=DARK):
    """A shoe outline; with ``fill_frac`` the sole fills like a fuel gauge.

    The fill is a lighter tone than the outline on purpose - filled solid
    black, a full shoe loses its silhouette and reads as a blob.
    """
    outline = ("M8 74 L8 60 C8 44 22 39 36 39 L48 39 L64 25 L76 25 "
               "C87 25 93 34 93 46 L93 66 C93 72 89 74 82 74 Z")
    parts = []
    if fill_frac is not None:
        clip_id = f"shoefill{abs(hash((x, y, size))) % 100000}"
        top = 74 - 49 * max(0.0, min(1.0, fill_frac))
        parts.append(f'<clipPath id="{clip_id}"><path d="{outline}"/></clipPath>')
        parts.append(f'<rect x="0" y="{top:.1f}" width="100" height="{74 - top:.1f}" '
                     f'fill="{fill_colour}" stroke="none" clip-path="url(#{clip_id})"/>')
    parts.append(f'<path d="{outline}" stroke-width="6"/>')
    return _g("".join(parts), x, y, size, colour)


MOUNTAIN_PTS = "4,86 38,24 56,52 68,36 96,86"


def glyph_mountain(x, y, size, colour=BLACK, filled=True, fill_frac=None,
                   fill_colour=None):
    """A peak silhouette. ``fill_frac`` fills it from the base like a gauge,
    clipped to the outline so a partial summit never spills past the slopes."""
    if fill_frac is not None:
        clip_id = f"mtn{abs(hash((x, y, size))) % 100000}"
        top = 86 - 62 * max(0.0, min(1.0, fill_frac))
        body = (f'<clipPath id="{clip_id}"><polygon points="{MOUNTAIN_PTS}"/></clipPath>'
                f'<rect x="0" y="{top:.1f}" width="100" height="{86 - top:.1f}" '
                f'fill="{fill_colour or DARK}" stroke="none" clip-path="url(#{clip_id})"/>'
                f'<polygon points="{MOUNTAIN_PTS}" fill="none" stroke="{colour}" '
                f'stroke-width="6"/>')
        return _g(body, x, y, size, colour)
    fill = colour if filled else "none"
    body = (f'<polygon points="{MOUNTAIN_PTS}" fill="{fill}" '
            f'stroke="{colour}" stroke-width="6"/>')
    return _g(body, x, y, size, colour)


GLYPHS = {"run": glyph_runner, "bike": glyph_bike,
          "shoe": glyph_shoe, "mountain": glyph_mountain}


# --- canvas --------------------------------------------------------------

class Card:
    """One 800x480 e-paper screen."""

    def __init__(self, cid, title, summary, idea=None, family=None, recipe=None):
        self.id = cid
        self.title = title        # RSS <title> - the fact itself
        self.summary = summary    # RSS <description> - one sentence of context
        self.idea = idea          # catalogue number, for the contact sheet
        self.family = family      # catalogue family letter
        self.recipe = recipe      # one line on where the numbers come from
        self.parts = []

    def add(self, *markup):
        self.parts.extend(markup)
        return self

    def svg(self, standalone=False):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}">' if standalone else
                f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
        return (head + DITHER_DEFS + rect(0, 0, W, H, fill=WHITE)
                + "".join(self.parts) + "</svg>")


# --- animal glyphs -------------------------------------------------------
# Ported from the Pillow prototype's polygon silhouettes (uoiv93,
# strava-data/tools/eink_cards.py L506-604), which were drawn in a 0..1 box;
# these are the same shapes at 100x scale. Solid fills, not outlines: at the
# 52 px the wildlife scoreboard draws them, an outlined animal is a smudge.
# Strokes are specified in the 100-box, so a stroke of 8 at size 52 lands at
# 4.2 effective px - above the 3 px floor with room to spare.

def _fill(pts, colour):
    d = " ".join(f"{x * 100:.1f},{y * 100:.1f}" for x, y in pts)
    return f'<polygon points="{d}" fill="{colour}" stroke="none"/>'


def _ell(x0, y0, x1, y1, colour):
    return (f'<ellipse cx="{(x0 + x1) * 50:.1f}" cy="{(y0 + y1) * 50:.1f}" '
            f'rx="{(x1 - x0) * 50:.1f}" ry="{(y1 - y0) * 50:.1f}" '
            f'fill="{colour}" stroke="none"/>')


def _stroke(pts, colour, w=8):
    d = " ".join(f"{x * 100:.1f},{y * 100:.1f}" for x, y in pts)
    return (f'<polyline points="{d}" fill="none" stroke="{colour}" '
            f'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def _eye(x, y, colour=WHITE, r=2.6):
    return (f'<circle cx="{x * 100:.1f}" cy="{y * 100:.1f}" r="{r}" '
            f'fill="{colour}" stroke="none"/>')


def _animal(body_fn):
    """Wrap a body builder into the standard ``glyph_*(x, y, size)`` shape."""
    def glyph(x, y, size, colour=BLACK):
        return _g(body_fn(colour), x, y, size, colour)
    return glyph


def _coyote(c):
    return _fill([(0.02, 0.62), (0.10, 0.45), (0.30, 0.42), (0.62, 0.40), (0.70, 0.22),
                  (0.76, 0.34), (0.88, 0.18), (0.92, 0.40), (0.98, 0.50), (0.90, 0.56),
                  (0.72, 0.60), (0.70, 0.82), (0.64, 0.82), (0.60, 0.62), (0.40, 0.62),
                  (0.34, 0.82), (0.28, 0.82), (0.26, 0.62), (0.14, 0.64), (0.06, 0.80),
                  (0.0, 0.76)], c) + _eye(0.88, 0.42)


def _deer(c):
    return (_fill([(0.12, 0.50), (0.30, 0.44), (0.62, 0.44), (0.72, 0.28), (0.82, 0.30),
                   (0.90, 0.40), (0.88, 0.50), (0.74, 0.54), (0.72, 0.90), (0.66, 0.90),
                   (0.64, 0.62), (0.40, 0.62), (0.36, 0.90), (0.30, 0.90), (0.28, 0.62),
                   (0.16, 0.66), (0.08, 0.60)], c)
            + _stroke([(0.74, 0.28), (0.66, 0.06), (0.60, 0.16)], c, 7)
            + _stroke([(0.74, 0.28), (0.80, 0.06), (0.86, 0.14)], c, 7))


def _snake(c):
    import math as _m
    pts = [(0.02 + 0.96 * (i / 40), 0.5 + _m.sin(i / 40 * 2 * _m.pi * 1.5) * 0.28)
           for i in range(41)]
    hx, hy = pts[-1]
    return (_stroke(pts, c, 15)
            + _ell(hx - 0.10, hy - 0.10, hx + 0.10, hy + 0.10, c)
            + _eye(hx + 0.04, hy - 0.03))


def _owl(c):
    body = _ell(0.18, 0.18, 0.82, 0.98, c)
    ears = (_fill([(0.22, 0.30), (0.20, 0.02), (0.40, 0.22)], c)
            + _fill([(0.78, 0.30), (0.80, 0.02), (0.60, 0.22)], c))
    eyes = "".join(_ell(ex - 0.13, 0.28, ex + 0.13, 0.54, WHITE)
                   + _ell(ex - 0.06, 0.35, ex + 0.06, 0.47, c) for ex in (0.36, 0.64))
    beak = _fill([(0.44, 0.54), (0.56, 0.54), (0.50, 0.66)], WHITE)
    return body + ears + eyes + beak


def _quail(c):
    return (_ell(0.14, 0.34, 0.84, 0.94, c) + _ell(0.56, 0.22, 0.84, 0.50, c)
            + _stroke([(0.72, 0.26), (0.66, 0.06)], c, 6)
            + _ell(0.60, 0.03, 0.72, 0.13, c)
            + _fill([(0.84, 0.36), (0.96, 0.40), (0.84, 0.44)], c) + _eye(0.74, 0.34))


def _lizard(c):
    legs = "".join(_stroke([(x, y0), (x - 0.10, y1)], c, 8)
                   for x, y0, y1 in ((0.38, 0.40, 0.22), (0.60, 0.40, 0.22),
                                     (0.38, 0.60, 0.78), (0.60, 0.60, 0.78)))
    return (_ell(0.28, 0.36, 0.68, 0.64, c) + _ell(0.62, 0.38, 0.86, 0.60, c)
            + _stroke([(0.30, 0.50), (0.12, 0.44), (0.02, 0.30)], c, 8)
            + legs + _eye(0.78, 0.46))


def _hawk(c):
    return (_fill([(0.0, 0.30), (0.20, 0.36), (0.40, 0.48), (0.50, 0.40), (0.60, 0.48),
                   (0.80, 0.36), (1.0, 0.30), (0.78, 0.52), (0.62, 0.62), (0.56, 0.88),
                   (0.44, 0.88), (0.38, 0.62), (0.22, 0.52)], c)
            + _ell(0.42, 0.24, 0.58, 0.42, c))


def _bobcat(c):
    return (_fill([(0.06, 0.52), (0.14, 0.42), (0.60, 0.40), (0.68, 0.26), (0.74, 0.34),
                   (0.86, 0.26), (0.88, 0.40), (0.96, 0.48), (0.86, 0.56), (0.70, 0.60),
                   (0.68, 0.88), (0.60, 0.88), (0.58, 0.62), (0.34, 0.62), (0.30, 0.88),
                   (0.22, 0.88), (0.20, 0.60), (0.06, 0.60)], c) + _eye(0.86, 0.42))


def _roadrunner(c):
    return (_ell(0.30, 0.40, 0.70, 0.74, c)
            + _fill([(0.32, 0.56), (0.0, 0.34), (0.06, 0.28), (0.36, 0.48)], c)
            + _stroke([(0.62, 0.48), (0.72, 0.28)], c, 10)
            + _ell(0.64, 0.14, 0.84, 0.34, c)
            + _fill([(0.82, 0.22), (1.0, 0.26), (0.82, 0.30)], c)
            + _fill([(0.70, 0.16), (0.60, 0.02), (0.76, 0.12)], c)
            + _stroke([(0.44, 0.72), (0.40, 0.92), (0.30, 0.92)], c, 6)
            + _stroke([(0.56, 0.72), (0.62, 0.92), (0.72, 0.92)], c, 6)
            + _eye(0.76, 0.22))


def _turkey(c):
    import math as _m
    fan = "".join(
        _stroke([(0.5, 0.64), (0.5 + _m.cos(_m.radians(-90 + k * 22)) * 0.44,
                               0.62 + _m.sin(_m.radians(-90 + k * 22)) * 0.44)], c, 13)
        for k in range(-3, 4))
    return (fan + _ell(0.26, 0.40, 0.74, 0.90, c) + _ell(0.60, 0.26, 0.82, 0.50, c)
            + _fill([(0.80, 0.36), (0.96, 0.40), (0.80, 0.44)], c) + _eye(0.72, 0.36))


def _rabbit(c):
    return (_ell(0.24, 0.46, 0.74, 0.92, c) + _ell(0.58, 0.32, 0.84, 0.58, c)
            + _stroke([(0.66, 0.34), (0.60, 0.06)], c, 9)
            + _stroke([(0.76, 0.34), (0.80, 0.06)], c, 9)
            + _ell(0.16, 0.60, 0.32, 0.76, c) + _eye(0.76, 0.44))


def _tarantula(c):
    legs = "".join(_stroke([(0.5 - s * 0.06, 0.52), (0.5 - s * 0.34, 0.5 + dy),
                            (0.5 - s * 0.46, 0.5 + dy * 2)], c, 7)
                   for s in (1, -1) for dy in (-0.22, -0.06, 0.10, 0.26))
    return legs + _ell(0.34, 0.40, 0.66, 0.78, c) + _ell(0.40, 0.26, 0.60, 0.44, c)


def _skunk(c):
    return (_fill([(0.10, 0.62), (0.18, 0.50), (0.60, 0.48), (0.70, 0.40), (0.82, 0.44),
                   (0.84, 0.56), (0.70, 0.62), (0.66, 0.86), (0.58, 0.86), (0.56, 0.66),
                   (0.30, 0.66), (0.26, 0.86), (0.18, 0.86), (0.16, 0.66)], c)
            + _stroke([(0.16, 0.60), (0.06, 0.36), (0.14, 0.10), (0.30, 0.06)], c, 13)
            + _stroke([(0.34, 0.52), (0.34, 0.66)], WHITE, 6) + _eye(0.78, 0.46))


def _heron(c):
    return (_ell(0.28, 0.44, 0.66, 0.68, c)
            + _stroke([(0.58, 0.52), (0.70, 0.32), (0.66, 0.14)], c, 8)
            + _ell(0.58, 0.06, 0.76, 0.20, c)
            + _fill([(0.74, 0.10), (0.98, 0.14), (0.74, 0.18)], c)
            + _stroke([(0.40, 0.66), (0.38, 0.94), (0.28, 0.94)], c, 7)
            + _stroke([(0.54, 0.66), (0.56, 0.94), (0.66, 0.94)], c, 7)
            + _stroke([(0.30, 0.56), (0.06, 0.48)], c, 8) + _eye(0.70, 0.12))


def _seal(c):
    return (_fill([(0.06, 0.72), (0.14, 0.56), (0.44, 0.48), (0.68, 0.46), (0.84, 0.34),
                   (0.94, 0.36), (0.96, 0.48), (0.84, 0.56), (0.70, 0.66), (0.40, 0.76),
                   (0.20, 0.80)], c)
            + _fill([(0.06, 0.72), (0.0, 0.52), (0.10, 0.54)], c)
            + _stroke([(0.44, 0.70), (0.34, 0.88)], c, 9) + _eye(0.86, 0.42))


def _dolphin(c):
    return (_fill([(0.04, 0.44), (0.26, 0.34), (0.52, 0.34), (0.74, 0.44), (0.92, 0.60),
                   (0.98, 0.74), (0.82, 0.68), (0.60, 0.68), (0.34, 0.62), (0.14, 0.56)], c)
            + _fill([(0.40, 0.34), (0.50, 0.12), (0.58, 0.34)], c)
            + _fill([(0.04, 0.44), (0.0, 0.24), (0.14, 0.34)], c) + _eye(0.84, 0.60))


def _whale(c):
    return (_fill([(0.06, 0.56), (0.22, 0.42), (0.52, 0.40), (0.76, 0.48), (0.88, 0.62),
                   (0.72, 0.72), (0.44, 0.76), (0.18, 0.72)], c)
            + _fill([(0.88, 0.62), (1.0, 0.40), (0.98, 0.66), (1.0, 0.86)], c)
            + _stroke([(0.30, 0.42), (0.28, 0.20)], c, 8)
            + _stroke([(0.30, 0.24), (0.20, 0.10)], c, 6)
            + _stroke([(0.30, 0.24), (0.40, 0.10)], c, 6) + _eye(0.18, 0.58))


def _fox(c):
    return (_fill([(0.10, 0.62), (0.20, 0.48), (0.60, 0.46), (0.66, 0.28), (0.74, 0.38),
                   (0.86, 0.28), (0.90, 0.44), (0.96, 0.52), (0.86, 0.58), (0.68, 0.62),
                   (0.66, 0.86), (0.58, 0.86), (0.56, 0.64), (0.32, 0.64), (0.28, 0.86),
                   (0.20, 0.86), (0.18, 0.64)], c)
            + _stroke([(0.16, 0.60), (0.04, 0.42), (0.08, 0.22)], c, 14) + _eye(0.86, 0.44))


ANIMAL_GLYPHS = {
    "Coyote": _animal(_coyote), "Deer": _animal(_deer), "Snake": _animal(_snake),
    "Owl": _animal(_owl), "Quail": _animal(_quail), "Lizard": _animal(_lizard),
    "Hawk": _animal(_hawk), "Bobcat": _animal(_bobcat),
    "Roadrunner": _animal(_roadrunner), "Turkey": _animal(_turkey),
    "Rabbit": _animal(_rabbit), "Tarantula": _animal(_tarantula),
    "Skunk": _animal(_skunk), "Heron": _animal(_heron), "Seal": _animal(_seal),
    "Dolphin": _animal(_dolphin), "Whale": _animal(_whale), "Fox": _animal(_fox),
}


def glyph_sun(x, y, size, colour=BLACK, level=0.0, rays=8):
    """A rayed sun whose disc darkens with ``level`` (0..1).

    Replaces a sunscreen tube that nobody could identify - at this size a tube
    reads as a jar or a battery, whereas a sun needs no caption and matches
    the peak-UV card next door, which also draws one. Dose is carried by tone
    rather than by a fill line: on four grey levels a darkening disc is a
    clearer quantity than a partial fill inside a circle, and it keeps the
    silhouette intact.
    """
    import math as _m
    r = 27.0
    body = [f'<circle cx="50" cy="50" r="{r}" fill="{tone(level)}" '
            f'stroke="{colour}" stroke-width="6"/>']
    for i in range(rays):
        th = _m.radians(i * 360.0 / rays - 90)
        x0, y0 = 50 + (r + 9) * _m.cos(th), 50 + (r + 9) * _m.sin(th)
        x1, y1 = 50 + (r + 21) * _m.cos(th), 50 + (r + 21) * _m.sin(th)
        body.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
                    f'stroke="{colour}" stroke-width="7" stroke-linecap="round"/>')
    return _g("".join(body), x, y, size, colour)
