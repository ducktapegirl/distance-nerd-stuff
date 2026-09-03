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
