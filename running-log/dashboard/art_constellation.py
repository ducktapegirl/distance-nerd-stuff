"""A4 — Constellation: four years of running overlaid on one calendar year.

A dot per run at (day of year, miles), sized by miles, with faint threads
between runs a few days apart. All four academic years land on the same
calendar, so the piece is really about the **voids** -- summers at home, taper
weeks, the injuries -- rather than about the marks.

**Why y is miles and not minutes.** The landing-art proof placed dots at
(day of year, minutes) and, in doing so, silently dropped 340 of the 1,138
runs: only 798 recorded a duration. On a dashboard that is a chart quietly
lying about the record. Miles are on every single run, so every run appears.
The spec calls this the most important decision in the piece; it is recorded
here so a later session does not "fix" it back.

Promoted from `tools/proof_landing_art.py:a4_constellation`, re-derived rather
than lifted: dropping the duration filter changes the distribution, so the
thread gate and the dot sizing are tuned against miles, not reused.

Hover reveals that run's `comments` -- the log's best and least-exploited
asset, real writing from the day it happened. A constellation whose dots
reveal the actual sentence is a better piece than one that reveals a mileage.

Every id and class is prefixed `ac-`; theme is pure cascade and
`applyChartTheme()` must not touch it. See `art_weave.py` for the full
statement of both rules.
"""

import datetime
import json

from dashboard.config import EASY_COLOR, RACE_COLOR
from dashboard.data import maybe_float

S = 900
L, R, T, B = 66, 858, 60, 812

# Five dot sizes. Marks ship as <use> of five <symbol>s rather than 1,138
# <circle> elements -- that was ~57 KB in the proof, and even without a byte
# budget a small DOM is what keeps the page responsive.
NSIZE = 5

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# name -> (dark, light). Both values always; a dark-only value is how the
# light theme ships broken.
AC_COLORS = {
    # A run and a race take the page's own easy/race hues, so the piece reads
    # as part of the dashboard rather than as a separate palette.
    "ac-dot":    (EASY_COLOR, "#0d9488"),
    "ac-race":   (RACE_COLOR, "#c81e1e"),
    "ac-thread": ("#3f6f78", "#9ccec7"),   # the link between near runs
    "ac-ink":    ("#64748b", "#64748b"),   # axis chrome, legible either way
    "ac-grid":   ("#1e2836", "#e2e8f0"),
}


def _paint(key):
    return "var(--%s, %s)" % (key, AC_COLORS[key][0])


_AC_CSS_BODY = """
#ac-svg { display:block; width:100%; max-width:720px; margin:0 auto; }
#ac-hi { pointer-events:none; }
#ac-readout { margin:12px auto 0; max-width:56em; min-height:4.5em;
  font-size:13px; line-height:1.5; text-align:center;
  color:var(--text-secondary,#94a3b8); }
#ac-readout b { color:var(--text-primary,#e2e8f0); font-weight:600; }
#ac-readout .ac-note { display:block; margin-top:4px; font-style:italic; }
"""


def _css():
    dark = "".join("--%s: %s; " % (k, v[0]) for k, v in AC_COLORS.items())
    light = "".join("--%s: %s; " % (k, v[1]) for k, v in AC_COLORS.items())
    return ":root { %s }\n:root.light { %s }\n%s" % (dark, light, _AC_CSS_BODY)


def _runs(rows):
    out = []
    for r in rows:
        mi = maybe_float(r.get("miles"))
        if not r.get("date") or not mi or mi <= 0:
            continue
        try:
            d = datetime.date.fromisoformat(r["date"])
        except ValueError:
            continue
        note = " ".join((r.get("comments") or "").split())
        out.append({"d": d, "mi": mi, "doy": d.timetuple().tm_yday,
                    "race": r.get("is_race") == "1", "note": note})
    out.sort(key=lambda r: r["d"])
    return out


def art_constellation_html(rows):
    """The whole self-contained fragment: style + svg + script."""
    runs = _runs(rows)
    if not runs:
        return ""

    mx = max(r["mi"] for r in runs)
    # A soft ceiling rather than the raw max: a handful of very long runs would
    # otherwise push the median run into the bottom fifth of the frame and
    # flatten the field. Runs above it clamp to the top edge.
    ceil = 16.0

    def xy(r):
        return (L + (r["doy"] - 1) / 365.0 * (R - L),
                B - min(r["mi"], ceil) / ceil * (B - T))

    parts = []

    # Month gridlines and labels, behind everything.
    grid, labs = [], []
    for m in range(12):
        doy = datetime.date(2005, m + 1, 1).timetuple().tm_yday
        x = L + (doy - 1) / 365.0 * (R - L)
        grid.append("M%.1f %dV%d" % (x, T, B))
        labs.append('<text x="%.1f" y="%d" text-anchor="middle" font-size="15" '
                    'fill="%s" letter-spacing="1">%s</text>'
                    % (x + (R - L) / 24.0, B + 30, _paint("ac-ink"), MONTHS[m].upper()))
    parts.append('<path d="%s" stroke="%s" stroke-width="0.8" fill="none"/>'
                 % ("".join(grid), _paint("ac-grid")))

    # Mileage gridlines on the y axis, so the vertical reads as a quantity.
    for mi in (4, 8, 12, 16):
        y = B - mi / ceil * (B - T)
        parts.append('<path d="M%d %.1fH%d" stroke="%s" stroke-width="0.8" '
                     'fill="none"/>' % (L, y, R, _paint("ac-grid")))
        labs.append('<text x="%d" y="%.1f" text-anchor="end" font-size="14" '
                    'fill="%s">%s</text>'
                    % (L - 10, y + 5, _paint("ac-ink"),
                       "%d+ mi" % mi if mi == 16 else "%d mi" % mi))
    parts.append("".join(labs))

    # Threads. The gate is on BOTH axes, not on date proximity alone: linking
    # any two runs within three days hangs a near-vertical stem off every dot
    # whose neighbour ran a very different distance, and the field reads as a
    # barcode with drips instead of a constellation. The y tolerance is in user
    # units and had to be re-derived for the miles axis. The proof's 34 units
    # was ~10 minutes on a 120-minute axis; 34 units here is only ~0.7 mi,
    # which almost no consecutive pair clears, so at that gate no thread draws
    # at all. Opened to 62 (~1.3 mi) the threads came back as exactly the
    # failure the proof describes -- long near-vertical drips, because a
    # three-day span is under 7 units wide so every link is nearly vertical by
    # construction. 44 units (~0.94 mi) is where they read as connective
    # texture between runs of a similar length instead.
    thread, prev = [], None
    for r in runs:
        x, y = xy(r)
        if (prev and (r["d"] - prev[0]).days <= 3
                and abs(x - prev[1]) < 16 and abs(y - prev[2]) < 44):
            thread.append("L%.0f %.0f" % (x, y))
        else:
            thread.append("M%.0f %.0f" % (x, y))
        prev = (r["d"], x, y)
    parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.7" '
                 'opacity="0.38"/>' % ("".join(thread), _paint("ac-thread")))

    defs = "".join('<circle id="ac-d%d" r="%.2f"/>' % (i, 2.0 + i * 1.5)
                   for i in range(NSIZE))
    parts.insert(0, "<defs>%s</defs>" % defs)

    # Runs, bucketed by size so each bucket is one <g> with one opacity.
    buckets = {i: [] for i in range(NSIZE)}
    races, marks = [], []
    for r in runs:
        x, y = xy(r)
        k = min(int(r["mi"] / mx * NSIZE), NSIZE - 1)
        buckets[k].append('<use href="#ac-d%d" x="%.0f" y="%.0f"/>' % (k, x, y))
        if r["race"]:
            races.append('<circle cx="%.0f" cy="%.0f" r="%.1f" fill="none" '
                         'stroke="%s" stroke-width="1.6" opacity="0.85"/>'
                         % (x, y, 4.5 + k * 1.5, _paint("ac-race")))
        marks.append([round(x, 1), round(y, 1), r["d"].isoformat(),
                      round(r["mi"], 2), 1 if r["race"] else 0, r["note"]])

    for k in sorted(buckets):
        if buckets[k]:
            parts.append('<g fill="%s" opacity="%.2f">%s</g>'
                         % (_paint("ac-dot"), 0.5 + k * 0.11, "".join(buckets[k])))
    if races:
        parts.append("<g>%s</g>" % "".join(races))

    parts.append('<circle id="ac-hi" r="11" fill="none" stroke="%s" '
                 'stroke-width="2" opacity="0"/>' % _paint("ac-ink"))

    n_note = sum(1 for r in runs if r["note"])
    blob = json.dumps({"marks": marks}, separators=(",", ":")).replace("</", "<\\/")

    return (
        "<style>%s</style>" % _css()
        + '<svg id="ac-svg" viewBox="0 0 %d %d" role="img" '
          'aria-label="All %d runs of four years plotted on one calendar year: '
          'horizontal is day of year, vertical is distance. A ring around a '
          'dot marks a race. The gaps are the subject.">%s</svg>'
          % (S, S, len(runs), "".join(parts))
        + '<p id="ac-readout">Drag a finger across the field for that day’s '
          'log entry. %d of %d runs left a note.</p>' % (n_note, len(runs))
        + '<script id="ac-data" type="application/json">%s</script>' % blob
        + "<script>%s</script>" % AC_JS
    )


# Same nearest-mark search as the weave, and for the same reason: the dots ship
# as <use> inside five groups, so there is nothing per-run to attach a handler
# to, and at 375 px a dot is well under a tap target. Touch drags the readout.
# Desktop mouse hover is deliberately not wired up (removed as a UX decision --
# a static field of dots read better without a hover readout on desktop); the
# nearest-mark search stays because touch drag-scrub still depends on it.
AC_JS = r"""
(function () {
  var svg = document.getElementById('ac-svg');
  var dataEl = document.getElementById('ac-data');
  if (!svg || !dataEl) return;
  var marks = JSON.parse(dataEl.textContent).marks;
  var hi = document.getElementById('ac-hi');
  var out = document.getElementById('ac-readout');
  var idle = out.innerHTML;

  function fmtDate(iso) {
    var p = iso.split('-');
    var M = ['Jan','Feb','Mar','Apr','May','Jun',
             'Jul','Aug','Sep','Oct','Nov','Dec'];
    return (+p[2]) + ' ' + M[+p[1] - 1] + ' ' + p[0];
  }

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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
      var dx = x - marks[i][0], dy = y - marks[i][1];
      var d = dx * dx + dy * dy;
      if (d < bd) { bd = d; best = marks[i]; }
    }
    return bd < 400 ? best : null;
  }

  function show(m) {
    if (!m) {
      hi.setAttribute('opacity', '0');
      out.innerHTML = idle;
      return;
    }
    hi.setAttribute('cx', m[0]);
    hi.setAttribute('cy', m[1]);
    hi.setAttribute('opacity', '0.9');
    var head = '<b>' + fmtDate(m[2]) + '</b> · ' + m[3].toFixed(1) + ' mi' +
               (m[4] ? ' · race' : '');
    out.innerHTML = head + (m[5] ? '<span class="ac-note">' + esc(m[5]) +
                                   '</span>' : '');
  }

  function at(ev) { var p = toUser(ev); show(nearest(p[0], p[1])); }

  svg.addEventListener('touchstart', function (e) { at(e); e.preventDefault(); },
                       { passive: false });
  svg.addEventListener('touchmove', function (e) { at(e); e.preventDefault(); },
                       { passive: false });
})();
"""
