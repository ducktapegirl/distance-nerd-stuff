"""A2 — Woven Weeks: four years of training as a bolt of cloth.

A warp of seven day-of-week columns against a weft of ~193 week rows. Each run
is a slub whose length is its mileage and whose color is its mapped workout
type. Nothing is readable as a number, which is the point.

Promoted from the landing-art proof (`tools/proof_landing_art.py:_weave`). The
proof ran at 640x480 under a ~40 KB tile budget, which forced a coarse
two-weeks-to-a-row variant: 193 rows over 440 units is 2.29 units a row, about
1.2 px at the 240 px tile size, which is a moire rather than a textile. At
S=900 a row is ~4.1 units and the fine version is the right one.

Self-contained per the Art packaging rule: this returns style + svg + controls
+ script as one string, the shape `strava-data/dashboard/art_year.py` uses.
The Year Clock's split across three files is what that rule exists to avoid.

Every id and CSS class is prefixed `aw-`. SVG <defs> ids share one document
namespace, so an unprefixed id would silently cross-wire with `yc-` or with a
Plotly chart already on the page.

Theme is pure cascade -- this is not a Plotly figure, so `applyChartTheme()`
must not touch it. The five workout-type colors reuse the page's existing
`--easy` / `--long` / `--tempo` / `--workout` / `--race` custom properties,
which template.py already defines in both `:root` and `:root.light`; each
`var()` carries the dark hex as a literal fallback because a rasterizer does
not implement `var()`. Only the two tokens this piece introduces are defined
here, and both get a dark *and* a light value -- a dark-only value is how the
light theme ships broken.
"""

import datetime
import json

from dashboard.config import (
    EASY_COLOR, LONG_COLOR, RACE_COLOR, TEMPO_COLOR, TYPE_LABELS, WORKOUT_COLOR,
)
from dashboard.data import map_type, maybe_float

# The frame. Square at 900 like the Year Clock and the Strava art clock, not
# the landing tile's 4:3 -- the composition follows the frame.
S = 900
# The left margin carries the academic-year labels ("2003–04"), which are wider
# than they look at this scale -- at 56 they clipped off the edge of the frame.
L, R, T, B = 118, 858, 74, 858

# Paint order, and the order the filter buttons appear in. Easy runs are the
# ground the rest is read against, so they go down first.
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
AW_COLORS = {
    # The weft has to actually be visible where no run crosses it, or the seven
    # day columns read as seven separate barcodes with dark gutters between
    # them. Drawn at #2a3344 it vanished against the card and did exactly that.
    "aw-weft": ("#44536b", "#c2cad8"),   # the continuous cross-thread
    "aw-ink":  ("#64748b", "#64748b"),   # axis labels, legible on either ground
}

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _paint(key):
    """A named token as var() with its dark value as the literal fallback."""
    return "var(--%s, %s)" % (key, AW_COLORS[key][0])


def _type_paint(t):
    """A workout-type color, reusing the page's existing custom property."""
    var, lit = TYPE_VAR[t]
    return "var(%s, %s)" % (var, lit)


_AW_CSS_BODY = """
#aw-svg { display:block; width:100%; max-width:720px; margin:0 auto; }
#aw-svg .aw-grp { transition: opacity .18s ease; }
#aw-svg .aw-grp.aw-off { opacity:.08; }
#aw-hi { pointer-events:none; }
.aw-bar { display:flex; flex-wrap:wrap; gap:6px; justify-content:center;
          margin:12px 0 0; }
.aw-bar button { font:inherit; font-size:12px; line-height:1; cursor:pointer;
  padding:6px 10px; border-radius:999px; color:var(--text-secondary,#94a3b8);
  background:transparent; border:1px solid var(--border,#243044);
  display:inline-flex; align-items:center; gap:6px; }
.aw-bar button[aria-pressed="false"] { opacity:.42; }
.aw-sw { width:9px; height:9px; border-radius:2px; display:inline-block; }
#aw-readout { text-align:center; min-height:2.4em; margin:10px 0 0;
  font-size:13px; color:var(--text-secondary,#94a3b8); }
#aw-readout b { color:var(--text-primary,#e2e8f0); font-weight:600; }
@media (max-width:600px) { .aw-bar button { padding:7px 11px; } }
"""


def _css():
    """The :root pair plus the static rules. Both themes, always."""
    dark = "".join("--%s: %s; " % (k, v[0]) for k, v in AW_COLORS.items())
    light = "".join("--%s: %s; " % (k, v[1]) for k, v in AW_COLORS.items())
    return ":root { %s }\n:root.light { %s }\n%s" % (dark, light, _AW_CSS_BODY)


def _rows(rows):
    """Runs with mileage, as (date, miles, mapped type, raw type label)."""
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
    out.sort(key=lambda t: t[0])
    return out


def art_weave_html(rows):
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

    # The weft has to be a real, continuous thread, not a hairline. Drawn
    # thinner than this the seven day columns read as seven separate barcodes
    # with visible gutters between them -- the exact opposite of cloth.
    weft = "".join("M%d %.2fH%d" % (L, T + (i + 0.5) * rh, R) for i in range(nrow))
    parts = ['<path d="%s" stroke="%s" stroke-width="%.2f" fill="none" opacity="0.6"/>'
             % (weft, _paint("aw-weft"), min(rh * 0.34, 1.2))]

    # Warp guides, one per day column, behind everything.
    warp = "".join("M%.1f %dV%d" % (L + (c + 0.5) * colw, T, B) for c in range(7))
    parts.append('<path d="%s" stroke="%s" stroke-width="0.6" fill="none" '
                 'opacity="0.35"/>' % (warp, _paint("aw-weft")))

    # One <path> per workout type rather than ~1,138 elements. Stroke width is
    # constant here, so grouping by type costs nothing over grouping by width
    # and buys both the coloring and the filter for free.
    segs = {t: [] for t in TYPES}
    marks = []
    for d, mi, t in runs:
        i = (d - start).days // 7
        # A run deliberately overruns its column and bleeds into the days
        # either side of it. That overlap is what stops the seven columns from
        # reading as seven separate charts -- without it the piece is a bar
        # chart lying on its side.
        #
        # The proof's curve (0.15*colw floor, exponent 0.75) only overran for
        # the very longest runs, so at dashboard size the gutters were still
        # visible. A higher floor and a flatter exponent put a *typical* run at
        # roughly one column width, which is where the cloth closes up.
        ln = 0.34 * colw + 0.95 * colw * (mi / mx) ** 0.6
        x = L + d.weekday() * colw + (colw - ln) / 2
        y = T + (i + 0.5) * rh
        segs[t].append("M%.1f %.2fh%.1f" % (x, y, ln))
        marks.append([round(x + ln / 2, 1), round(y, 1), d.isoformat(),
                      round(mi, 2), t])

    sw = min(rh * 0.8, 3.6)
    for t in TYPES:
        if not segs[t]:
            continue
        parts.append('<g class="aw-grp" data-type="%s"><path d="%s" stroke="%s" '
                     'stroke-width="%.2f" fill="none" stroke-linecap="round" '
                     'opacity="0.92"/></g>'
                     % (t, "".join(segs[t]), _type_paint(t), sw))

    # Day-of-week headers and a year tick down the left edge. Chrome only --
    # kept off the cloth itself so the weave stays uninterrupted. Drawn after
    # the threads so labels always sit on top, but that only decides who wins
    # an overlap; the gap below is what removes it.
    #
    # How far past L a Monday slub can reach: half its overrun past the column
    # plus half the stroke and its round cap. Deriving the label gap from this
    # means re-tuning the length curve above can never push a thread back over
    # the year labels -- at the old fixed L - 12 a long Monday run crossed
    # "2005–06".
    max_ln = 0.34 * colw + 0.95 * colw
    bleed = max(0.0, (max_ln - colw) / 2) + sw / 2
    label_x = L - bleed - 10
    lab = []
    for c, name in enumerate(DOW):
        lab.append('<text x="%.1f" y="%d" text-anchor="middle" font-size="15" '
                   'fill="%s" letter-spacing="1.5">%s</text>'
                   % (L + (c + 0.5) * colw, T - 22, _paint("aw-ink"), name.upper()))
    seen = set()
    for d, _mi, _t in runs:
        ay = d.year if d.month >= 8 else d.year - 1        # academic year, Aug 1
        if ay in seen:
            continue
        seen.add(ay)
        i = (d - start).days // 7
        lab.append('<text x="%.1f" y="%.1f" text-anchor="end" font-size="14" '
                   'fill="%s">%s</text>'
                   % (label_x, T + (i + 0.5) * rh + 5, _paint("aw-ink"),
                      "%d–%02d" % (ay, (ay + 1) % 100)))
    parts.append("".join(lab))

    # Hover highlight, drawn last so it sits over the cloth.
    parts.append('<circle id="aw-hi" r="%.1f" fill="none" stroke="%s" '
                 'stroke-width="2" opacity="0"/>'
                 % (max(sw * 2.2, 9), _paint("aw-ink")))

    legend = "".join(
        '<button type="button" data-type="%s" aria-pressed="true">'
        '<span class="aw-sw" style="background:%s"></span>%s</button>'
        % (t, _type_paint(t), TYPE_LABELS.get(t, t.title())) for t in TYPES)

    data = {"marks": marks, "labels": {t: TYPE_LABELS.get(t, t.title()) for t in TYPES}}
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

    return (
        "<style>%s</style>" % _css()
        + '<svg id="aw-svg" viewBox="0 0 %d %d" role="img" '
          'aria-label="Every run of four years woven as cloth: seven day-of-week '
          'columns crossed by %d week rows, each run a slub whose length is its '
          'mileage.">%s</svg>' % (S, S, nrow, "".join(parts))
        + '<div class="aw-bar" id="aw-legend">%s</div>' % legend
        + '<p id="aw-readout"></p>'
        + '<script id="aw-data" type="application/json">%s</script>' % blob
        + "<script>%s</script>" % AW_JS
    )


# Hit testing is done in JS against the mark array rather than by attaching a
# handler per slub: the marks ship as five <path>s, so there is nothing
# per-run in the DOM to hover. That is also what makes this work on a phone --
# at 375 px a slub is ~1.7 px of row height, far under a tap target, so the
# same nearest-mark search backs a drag-scrub over the canvas.
AW_JS = r"""
(function () {
  var svg = document.getElementById('aw-svg');
  var dataEl = document.getElementById('aw-data');
  if (!svg || !dataEl) return;
  var D = JSON.parse(dataEl.textContent);
  var marks = D.marks, hi = document.getElementById('aw-hi');
  var out = document.getElementById('aw-readout');
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
      if (off[m[4]]) continue;
      // x is weighted down: rows are ~4 units apart and columns ~114, so an
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
    hi.setAttribute('opacity', '0.9');
    out.innerHTML = '<b>' + fmtDate(m[2]) + '</b> · ' +
                    m[3].toFixed(1) + ' mi · ' + (D.labels[m[4]] || m[4]);
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

  var bar = document.getElementById('aw-legend');
  if (bar) {
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-type]');
      if (!b) return;
      var t = b.dataset.type;
      off[t] = !off[t];
      b.setAttribute('aria-pressed', off[t] ? 'false' : 'true');
      var g = svg.querySelector('.aw-grp[data-type="' + t + '"]');
      if (g) g.classList.toggle('aw-off', !!off[t]);
      show(null);
    });
  }
})();
"""
