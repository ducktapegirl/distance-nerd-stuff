"""Low Relief: four years of training as raised forms on a flat ground.

The same grid as the Woven Weeks piece this replaces -- seven day-of-week
columns against ~193 ISO-week rows -- but each run is a lit mound rather than a
thread. Its width is its mileage, its color its mapped workout type, and it is
brightest at a crown set toward an upper-left light, falls through its true
color into a shaded rim, and fades out with no outline at all. Marks are
translucent, so overlaps deepen rather than cover, and one soft shadow sits
under everything. A heavy week reads as a ridge; a rest week as level ground.

Self-contained per the Art packaging rule: style + svg + controls + script as
one string, the shape `strava-data/dashboard/art_year.py` uses. Every id and
class is prefixed `lr-`, because SVG <defs> ids share one document namespace
with `yc-`, `ac-` and the Plotly charts.

Theme is pure cascade; `applyChartTheme()` must not touch it. The five workout
colors reuse the page's `--easy` / `--long` / `--tempo` / `--workout` / `--race`
custom properties, which template.py defines in both themes. The mound's crown
and rim are built by interpolating toward theme-neutral white and black inside
each gradient, rather than from precomputed lighter/darker hexes, so one
gradient per type serves both themes. Only the two tokens introduced here are
defined below, each with a dark *and* a light value.

**One element per run, deliberately.** Woven Weeks shipped five <path>s, one
per type, because a constant-width stroke can be concatenated. A per-mark
gradient fill cannot, and the draw order here is global -- widest mark first,
so a short run always sits on top of a long one -- which also rules out
grouping by type. The legend filter therefore keys on a `data-t` attribute and
a class on the <svg>, not on a <g> per type. ~1,138 ellipses is well inside
what the page handles.
"""

import datetime
import json

from dashboard.config import (
    EASY_COLOR, LONG_COLOR, RACE_COLOR, TEMPO_COLOR, TYPE_LABELS, WORKOUT_COLOR,
)
from dashboard.data import map_type, maybe_float

# The frame. Square at 900 like the Year Clock and the Strava art clock.
S = 900
# The left margin carries the academic-year labels ("2003–04"); the gap between
# them and the marks is derived below from how far a Monday mark can reach.
L, R, T, B = 118, 858, 74, 858

# Legend order. Easy runs are the ground the rest is read against.
TYPES = ["easy", "long", "tempo", "workout", "race"]
TYPE_VAR = {
    "easy":    ("--easy", EASY_COLOR),
    "long":    ("--long", LONG_COLOR),
    "tempo":   ("--tempo", TEMPO_COLOR),
    "workout": ("--workout", WORKOUT_COLOR),
    "race":    ("--race", RACE_COLOR),
}

# name -> (dark, light). The single source of both the SVG literal fallbacks
# and the custom properties the <style> below writes into :root / :root.light.
LR_COLORS = {
    "lr-ground": ("#243044", "#dfe4ec"),   # the row guides the mounds rest on
    "lr-ink":    ("#64748b", "#64748b"),   # axis labels and the hover ring
}

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# The mound. ry is a fraction of the row pitch; the gradient center sits
# off-center toward the light so the crown reads as lit, not as a bullseye.
RY_FRAC = 0.62
CROWN_CX, CROWN_CY, CROWN_R = 0.42, 0.36, 0.62


def _paint(key):
    """A named token as var() with its dark value as the literal fallback."""
    return "var(--%s, %s)" % (key, LR_COLORS[key][0])


def _type_paint(t):
    """A workout-type color, reusing the page's existing custom property."""
    var, lit = TYPE_VAR[t]
    return "var(%s, %s)" % (var, lit)


_LR_CSS_BODY = """
#lr-svg { display:block; width:100%; max-width:720px; margin:0 auto; }
#lr-svg ellipse[data-t] { transition: opacity .18s ease; }
#lr-hi { pointer-events:none; }
.lr-bar { display:flex; flex-wrap:wrap; gap:6px; justify-content:center;
          margin:12px 0 0; }
.lr-bar button { font:inherit; font-size:12px; line-height:1; cursor:pointer;
  padding:6px 10px; border-radius:999px; color:var(--text-secondary,#94a3b8);
  background:transparent; border:1px solid var(--border,#243044);
  display:inline-flex; align-items:center; gap:6px; }
.lr-bar button[aria-pressed="false"] { opacity:.42; }
.lr-sw { width:9px; height:9px; border-radius:2px; display:inline-block; }
#lr-readout { text-align:center; min-height:2.4em; margin:10px 0 0;
  font-size:13px; color:var(--text-secondary,#94a3b8); }
#lr-readout b { color:var(--text-primary,#e2e8f0); font-weight:600; }
@media (max-width:600px) { .lr-bar button { padding:7px 11px; } }
"""


def _css():
    """The :root pair, the per-type filter rules, and the static rules."""
    dark = "".join("--%s: %s; " % (k, v[0]) for k, v in LR_COLORS.items())
    light = "".join("--%s: %s; " % (k, v[1]) for k, v in LR_COLORS.items())
    # The legend filter: a class on the <svg> fades every mark of that type.
    # Marks carry data-t rather than living in a <g> per type because the
    # draw order is global (widest first), not grouped.
    off = "".join('#lr-svg.lr-off-%s ellipse[data-t="%s"] { opacity:.08; }\n'
                  % (t, t) for t in TYPES)
    return ":root { %s }\n:root.light { %s }\n%s%s" % (dark, light, off, _LR_CSS_BODY)


def _rows(rows):
    """Runs with mileage, as (date, miles, mapped type), in a stable order."""
    out = []
    for r in rows:
        mi = maybe_float(r.get("miles"))
        if not r.get("date") or not mi or mi <= 0:
            continue
        try:
            d = datetime.date.fromisoformat(r["date"])
        except ValueError:
            continue
        out.append((d, mi, map_type(r.get("workout_type"), r.get("is_race") == "1")))
    # Two runs on one date keep a fixed order regardless of CSV order: the
    # build has to be byte-identical from the same data.
    out.sort(key=lambda t: (t[0], t[2], t[1]))
    return out


def _gradient(t):
    """The mound fill for one type.

    objectBoundingBox units, so one def scales to every ellipse of that type.
    The crown interpolates from white and the rim toward black, both at
    stop-opacity, so the same gradient is right in both themes; only the two
    middle stops carry the type color, and they carry it as the page's own
    custom property.
    """
    paint = _type_paint(t)
    return (
        '<radialGradient id="lr-g-%s" cx="%.2f" cy="%.2f" r="%.2f">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0.96"/>'
        '<stop offset="0.3" style="stop-color:%s" stop-opacity="0.93"/>'
        '<stop offset="0.78" style="stop-color:%s" stop-opacity="0.78"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0"/>'
        '</radialGradient>' % (t, CROWN_CX, CROWN_CY, CROWN_R, paint, paint)
    )


# One shadow for every mark, as a single filter on their group: blur, offset
# toward the lower right, flatten to black at low alpha, then the marks on top.
# The classic chain rather than feDropShadow, for the widest support.
_SHADOW = (
    '<filter id="lr-sh" x="-2%" y="-2%" width="104%" height="104%">'
    '<feGaussianBlur in="SourceAlpha" stdDeviation="0.9"/>'
    '<feOffset dx="0.6" dy="1"/>'
    '<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.28 0"/>'
    '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>'
    '</filter>'
)


def art_relief_html(rows):
    """The whole self-contained fragment: style + svg + controls + script."""
    runs = _rows(rows)
    if not runs:
        return ""

    d0 = runs[0][0]
    start = d0 - datetime.timedelta(days=d0.weekday())     # Monday of week one
    nrow = (runs[-1][0] - start).days // 7 + 1
    rh = (B - T) / nrow
    colw = (R - L) / 7
    mx = max(r[1] for r in runs)
    ry = rh * RY_FRAC

    parts = ["<defs>" + "".join(_gradient(t) for t in TYPES) + _SHADOW + "</defs>"]

    # The ground: one faint guide per week row, so the mounds have a surface
    # to rest on and the week rhythm survives where no run falls.
    ground = "".join("M%d %.2fH%d" % (L, T + (i + 0.5) * rh, R) for i in range(nrow))
    parts.append('<path d="%s" stroke="%s" stroke-width="0.5" fill="none" '
                 'opacity="0.55"/>' % (ground, _paint("lr-ground")))

    # Place every run, then draw widest first so a short run is never buried
    # under a long one in the same week.
    placed = []
    for d, mi, t in runs:
        i = (d - start).days // 7
        # The same length curve Woven Weeks tuned: a typical run is about one
        # column wide, and a long one overruns into the days either side.
        ln = 0.34 * colw + 0.95 * colw * (mi / mx) ** 0.6
        cx = L + d.weekday() * colw + colw / 2
        cy = T + (i + 0.5) * rh
        placed.append((ln, d, t, mi, cx, cy))
    placed.sort(key=lambda p: (-p[0], p[1], p[2]))

    marks = []
    ell = []
    for ln, d, t, mi, cx, cy in placed:
        ell.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" '
                   'fill="url(#lr-g-%s)" data-t="%s"/>'
                   % (cx, cy, ln / 2, ry, t, t))
        marks.append([round(cx, 1), round(cy, 1), round(ln / 2, 1),
                      d.isoformat(), round(mi, 2), t])
    parts.append('<g filter="url(#lr-sh)">%s</g>' % "".join(ell))
    # Hover reads the marks in date order; the draw order above is a display
    # concern and must not leak into the readout's tie-breaking.
    marks.sort(key=lambda m: (m[3], m[5], m[4]))

    # Day-of-week headers and a year tick down the left edge. The gap between
    # the year labels and the marks is derived from how far a Monday mark can
    # reach past the column edge (its overrun plus the shadow's throw), so a
    # later re-tune of the length curve can never push a mark back over them.
    max_ln = 0.34 * colw + 0.95 * colw
    bleed = max(0.0, (max_ln - colw) / 2) + 2.0
    label_x = L - bleed - 10
    lab = []
    for c, name in enumerate(DOW):
        lab.append('<text x="%.1f" y="%d" text-anchor="middle" font-size="15" '
                   'fill="%s" letter-spacing="1.5">%s</text>'
                   % (L + (c + 0.5) * colw, T - 30, _paint("lr-ink"), name.upper()))
    seen = set()
    for d, _mi, _t in runs:
        ay = d.year if d.month >= 8 else d.year - 1        # academic year, Aug 1
        if ay in seen:
            continue
        seen.add(ay)
        i = (d - start).days // 7
        lab.append('<text x="%.1f" y="%.1f" text-anchor="end" font-size="14" '
                   'fill="%s">%s</text>'
                   % (label_x, T + (i + 0.5) * rh + 5, _paint("lr-ink"),
                      "%d–%02d" % (ay, (ay + 1) % 100)))
    parts.append("".join(lab))

    # Hover highlight: an outline sized to the hovered mound, drawn last.
    parts.append('<ellipse id="lr-hi" rx="1" ry="%.1f" fill="none" stroke="%s" '
                 'stroke-width="1.2" opacity="0"/>' % (ry + 1.2, _paint("lr-ink")))

    legend = "".join(
        '<button type="button" data-type="%s" aria-pressed="true">'
        '<span class="lr-sw" style="background:%s"></span>%s</button>'
        % (t, _type_paint(t), TYPE_LABELS.get(t, t.title())) for t in TYPES)

    data = {"marks": marks, "labels": {t: TYPE_LABELS.get(t, t.title()) for t in TYPES}}
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

    return (
        "<style>%s</style>" % _css()
        + '<svg id="lr-svg" viewBox="0 0 %d %d" role="img" '
          'aria-label="Every run of four years as a raised, lit mound: seven '
          'day-of-week columns crossed by %d week rows, each mound as wide as '
          'its mileage.">%s</svg>' % (S, S, nrow, "".join(parts))
        + '<div class="lr-bar" id="lr-legend">%s</div>' % legend
        + '<p id="lr-readout"></p>'
        + '<script id="lr-data" type="application/json">%s</script>' % blob
        + "<script>%s</script>" % LR_JS
    )


# Hit testing is a nearest-mark search in JS against the mark array rather
# than a handler per ellipse: at 375 px a mound is ~1.7 px of row height, far
# under a tap target, so the same search backs a drag-scrub over the canvas.
# Marks are [cx, cy, rx, iso date, miles, type].
LR_JS = r"""
(function () {
  var svg = document.getElementById('lr-svg');
  var dataEl = document.getElementById('lr-data');
  if (!svg || !dataEl) return;
  var D = JSON.parse(dataEl.textContent);
  var marks = D.marks, hi = document.getElementById('lr-hi');
  var out = document.getElementById('lr-readout');
  var off = {};

  function fmtDate(iso) {
    var p = iso.split('-');
    var M = ['Jan','Feb','Mar','Apr','May','Jun',
             'Jul','Aug','Sep','Oct','Nov','Dec'];
    return (+p[2]) + ' ' + M[+p[1] - 1] + ' ' + p[0];
  }

  function toUser(ev) {
    var r = svg.getBoundingClientRect();
    var t = ev.touches && ev.touches[0] ? ev.touches[0] : ev;
    var vb = svg.viewBox.baseVal;
    return [(t.clientX - r.left) / r.width * vb.width,
            (t.clientY - r.top) / r.height * vb.height];
  }

  function nearest(x, y) {
    var best = null, bd = 1e9;
    for (var i = 0; i < marks.length; i++) {
      var m = marks[i];
      if (off[m[5]]) continue;
      // x is weighted down: rows are ~4 units apart and columns ~106, so an
      // unweighted distance would snap to the wrong week long before it
      // snapped to the wrong day.
      var dx = (x - m[0]) * 0.35, dy = y - m[1];
      var d = dx * dx + dy * dy;
      if (d < bd) { bd = d; best = m; }
    }
    return bd < 900 ? best : null;
  }

  function show(m) {
    if (!m) {
      hi.setAttribute('opacity', '0');
      out.innerHTML = '';
      return;
    }
    hi.setAttribute('cx', m[0]);
    hi.setAttribute('cy', m[1]);
    hi.setAttribute('rx', m[2] + 1.2);
    hi.setAttribute('opacity', '0.9');
    out.innerHTML = '<b>' + fmtDate(m[3]) + '</b> · ' +
                    m[4].toFixed(1) + ' mi · ' + (D.labels[m[5]] || m[5]);
  }

  function at(ev) {
    var p = toUser(ev);
    show(nearest(p[0], p[1]));
  }

  svg.addEventListener('mousemove', at);
  svg.addEventListener('mouseleave', function () { show(null); });
  svg.addEventListener('touchstart', function (e) { at(e); e.preventDefault(); },
                       { passive: false });
  svg.addEventListener('touchmove', function (e) { at(e); e.preventDefault(); },
                       { passive: false });

  var bar = document.getElementById('lr-legend');
  if (bar) {
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-type]');
      if (!b) return;
      var t = b.dataset.type;
      off[t] = !off[t];
      b.setAttribute('aria-pressed', off[t] ? 'false' : 'true');
      svg.classList.toggle('lr-off-' + t, !!off[t]);
      show(null);
    });
  }
})();
"""
