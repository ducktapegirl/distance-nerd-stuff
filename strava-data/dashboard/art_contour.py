"""B2 — Contour Field: every day's elevation profile as one ridgeline.

Elevation only. No map, no lat/lng. Each activity's altitude profile is drawn
as a ridge, the ridges are stacked down the canvas and sorted, and each is
filled opaque so the row in front occludes the one behind -- the Joy Division
construction. The cheapest beautiful thing in the set: it reads only the
`altitude_m` column, so it never pays for the cos-lat projection.

Promoted from `tools/proof_landing_art.py:b2_contour`. The proof drew **40** of
the 373 usable profiles at 48 points and integer coordinates, purely to fit a
~40 KB tile budget that separating fill from stroke had already doubled the
cost of. That budget does not exist on a dashboard, so this draws **all** of
them, which is a genuinely different picture: 373 rows sorted by date is a
two-year seismograph rather than a poster.

Every id and class is prefixed `co-`; theme is pure cascade. See
`art_year.py` for the full statement of both rules.
"""

import json

from nerd_common.geometry import altitude, set_streams_dir

from .art_year import prepare
from .config import STREAMS_DIR

set_streams_dir(STREAMS_DIR)

# This is the one piece in the set that is NOT square, and the reason is
# arithmetic rather than taste. The Joy Division construction needs roughly
# four user units of pitch between baselines before the strokes stop touching:
# 373 rows in a 900-unit square gives 1.9 units, and at a 1.2-unit stroke the
# ink alone fills 60% of the band, so the field renders as a solid mesh no
# matter what the amplitude is. Tried at 900x900 with amplitudes from 78 down
# to 26 -- the low half of the stack was a block every time. A tall frame is
# what lets all 373 profiles be drawn, which is the whole point of promoting
# this off the tile.
W, H = 900, 1720
L, R = 66, 862

# The first row's baseline sits at TOP and its amplitude reaches *up* from
# there, so TOP has to sit lower than the tallest amplitude or the biggest day
# runs straight off the top of the frame.
TOP = 120
BOT = 1660
# Peak amplitude for the biggest-relief day. Read this against the row pitch
# (~4.1 units), not in isolation: the proof's 74 units over an 8.8-unit pitch
# meant a ridge overlapped about eight neighbors, and 34 here reproduces that
# ratio.
AMP = 34.0
NPT = 64        # points per profile; the tile budget forced this down to 48

SORTS = [("gain", "Gain"), ("date", "Date"), ("dist", "Distance")]

# name -> (dark, light). Both values, always.
CO_COLORS = {
    "co-bg":   ("#0b0f14", "#ffffff"),   # the occluder -- must match the card
    "co-line": ("#2dd4bf", "#0d9488"),   # the horizon itself
    "co-ink":  ("#64748b", "#64748b"),
}


def _paint(key):
    return "var(--%s, %s)" % (key, CO_COLORS[key][0])


_CO_CSS_BODY = """
#co-svg { display:block; width:100%; max-width:720px; margin:0 auto; }
#co-hi { pointer-events:none; }
.co-bar { display:flex; flex-wrap:wrap; gap:6px; justify-content:center;
          margin:12px 0 0; }
.co-bar button { font:inherit; font-size:12px; line-height:1; cursor:pointer;
  padding:6px 12px; border-radius:999px; color:var(--text-secondary,#94a3b8);
  background:transparent; border:1px solid var(--border,#243044); }
.co-bar button.co-on { color:var(--text-primary,#e2e8f0);
  border-color:var(--accent,#2dd4bf); }
.co-tip { position:fixed; top:0; left:0; z-index:40; pointer-events:none;
  max-width:260px; padding:8px 12px; border-radius:10px;
  background:var(--bg-surface); border:1px solid var(--border,#243044);
  box-shadow:0 10px 30px rgba(0,0,0,0.35);
  font-size:13px; line-height:1.4; color:var(--text-secondary,#94a3b8);
  opacity:0; transition:opacity 120ms ease;
}
.co-tip.co-tip-show { opacity:1; }
.co-tip b { color:var(--text-primary,#e2e8f0); font-weight:600; }
@media (max-width:640px) {
  .co-tip { top:auto !important; left:12px !important; right:12px !important;
    bottom:12px !important; max-width:none !important; width:auto; }
}
"""


def _css():
    dark = "".join("--%s: %s; " % (k, v[0]) for k, v in CO_COLORS.items())
    light = "".join("--%s: %s; " % (k, v[1]) for k, v in CO_COLORS.items())
    return ":root { %s }\n:root.light { %s }\n%s" % (dark, light, _CO_CSS_BODY)


def _profiles(acts):
    """(activity, profile) for every activity with a usable altitude stream."""
    out = []
    for a in acts:
        prof = altitude(a["id"], NPT)
        if prof:
            out.append((a, prof))
    return out


def _feet(m):
    return int(round(m * 3.28084))


def art_contour_html(rows):
    """The whole self-contained fragment: style + svg + controls + script."""
    acts = prepare(rows)
    have = _profiles(acts)
    if not have:
        return ""

    reliefs = {a["id"]: (max(p) - min(p)) for a, p in have}
    mxr = max(reliefs.values()) or 1.0
    dy = (BOT - TOP) / max(len(have) - 1, 1)

    # Each ridge is drawn ONCE, with its baseline at y=0, and placed by a
    # transform. Sorting then moves 373 transforms and re-appends 373 groups
    # rather than re-emitting the geometry: rendering all three orders
    # server-side worked, but tripled the profile data and put 1.7 MB on the
    # page for what is a three-button control.
    rows_out, marks = [], []
    for idx, (a, prof) in enumerate(have):
        lo = min(prof)
        span = (max(prof) - lo) or 1.0
        # Amplitude follows relief ** 0.4, not relief. A linear scale against
        # the 2,058 m day flattens the median 84 m one to four percent of the
        # frame and the whole field becomes straight lines; even sqrt (0.5) is
        # dull. This is the number that makes the piece exist.
        amp = AMP * (reliefs[a["id"]] / mxr) ** 0.4
        pts = [(L + j / (len(prof) - 1) * (R - L), -(v - lo) / span * amp)
               for j, v in enumerate(prof)]
        d = "M" + "L".join("%.0f %.1f" % p for p in pts)
        # Fill and stroke MUST be two elements. Stroking the closed occluder
        # polygon draws its baseline *and both vertical sides*, so every ridge
        # comes out boxed and the stack reads as 373 rectangles instead of a
        # horizon. This is the highest-value finding in the whole set -- do not
        # merge these back into one element.
        rows_out.append(
            '<g class="co-row">'
            '<path d="%sL%d 0L%d 0Z" fill="%s"/>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="1.0" '
            'stroke-linejoin="round"/></g>'
            % (d, R, L, _paint("co-bg"), d, _paint("co-line")))
        marks.append([a["name"], a["dt"].strftime("%d %b %Y"),
                      _feet(reliefs[a["id"]]), round(a["km"] * 0.621371, 1),
                      a["sport_type"]])

    # Ties break on index so every ordering is deterministic build to build.
    idxs = range(len(have))
    orders = {
        "gain": sorted(idxs, key=lambda i: (-reliefs[have[i][0]["id"]], i)),
        "date": sorted(idxs, key=lambda i: (have[i][0]["dt"], i)),
        "dist": sorted(idxs, key=lambda i: (-have[i][0]["km"], i)),
    }

    layers = ['<g id="co-rows">%s</g>' % "".join(rows_out)]
    hi = ('<path id="co-hi" d="" fill="none" stroke="%s" stroke-width="2.4" '
          'opacity="0"/>' % _paint("co-ink"))

    buttons = "".join(
        '<button type="button" data-sort="%s" class="%s">%s</button>'
        % (k, "co-on" if k == "gain" else "", lab) for k, lab in SORTS)

    blob = json.dumps({"marks": marks, "orders": orders,
                       "top": TOP, "dy": round(dy, 4)},
                      separators=(",", ":")).replace("</", "<\\/")

    return (
        "<style>%s</style>" % _css()
        + '<svg id="co-svg" viewBox="0 0 %d %d" role="img" '
          'aria-label="The elevation profile of every one of %d recorded '
          'activities, stacked as ridgelines with the nearer row hiding the '
          'one behind.">%s%s</svg>'
          % (W, H, len(have), "".join(layers), hi)
        + '<div class="co-bar" id="co-sort">%s</div>' % buttons
        + '<script id="co-data" type="application/json">%s</script>' % blob
        + "<script>%s</script>" % CO_JS
    )


# Rows are ~2 units apart, so pointing at one is a y-coordinate lookup rather
# than a hit test on geometry: find the nearest baseline in the active order.
# That also makes the whole field usable by dragging a finger down it.
CO_JS = r"""
(function () {
  var svg = document.getElementById('co-svg');
  var dataEl = document.getElementById('co-data');
  var host = document.getElementById('co-rows');
  if (!svg || !dataEl || !host) return;
  var D = JSON.parse(dataEl.textContent);
  var hi = document.getElementById('co-hi');
  var rows = [].slice.call(host.children);   // in build order, index = mark id
  var sort = 'gain';
  var placed = [];                           // [baselineY, markIndex] per slot

  // Portal: appended to <body>, not left nested in the card, because the
  // card has both overflow:hidden and backdrop-filter -- backdrop-filter
  // creates a containing block for position:fixed descendants, so a tooltip
  // left inside the card would be clipped by the card's overflow:hidden.
  var tip = document.createElement('div');
  tip.className = 'co-tip';
  tip.setAttribute('role', 'status');
  tip.setAttribute('aria-live', 'polite');
  document.body.appendChild(tip);
  function isMobile() { return window.matchMedia('(max-width:640px)').matches; }

  function positionTip(clientX, clientY) {
    if (isMobile()) return;      // mobile CSS pins it; skip inline positioning
    var margin = 12;
    var vw = window.innerWidth, vh = window.innerHeight;
    var r = svg.getBoundingClientRect();
    var mid = r.left + r.width / 2;

    // Fixed width, not shrink-to-fit -- a *constant* tw is what makes the
    // viewport clamp below safe. Measuring the box's own width from content
    // (tip.offsetWidth) meant the clamped edge held steady while the other
    // edge -- the one next to the cursor -- crept sideways by however much
    // a row's text width changed between hovers, whenever the clamp engaged
    // (narrow desktop widths). Capping *width* to the gutter instead (a
    // second attempt) fixed the drift but then either clipped off-screen
    // (when the true gutter was narrower than the floor) or force-wrapped
    // the text into an unreadably narrow column. A constant width sidesteps
    // both: it can't drift (nothing about it depends on content), and it's
    // never narrower than comfortable.
    var tw = 260;
    tip.style.width = tw + 'px';

    var left = (clientX < mid) ? (r.left - tw - margin) : (r.right + margin);
    // Clamp against the viewport, not the SVG's own gutter -- when the
    // space beside the plot is too narrow for the tooltip, letting it slide
    // to overlap the plot/card edge (pointer-events:none, so this is
    // harmless) beats clipping it off-screen.
    left = Math.max(margin, Math.min(left, vw - tw - margin));
    tip.style.left = left.toFixed(0) + 'px';
    tip.style.right = 'auto';

    var th = tip.offsetHeight;
    var top = clientY - th / 2;
    top = Math.max(margin, Math.min(top, vh - th - margin));
    tip.style.top = top.toFixed(0) + 'px';
  }

  function apply(key) {
    var order = D.orders[key];
    var frag = document.createDocumentFragment();
    placed = [];
    for (var i = 0; i < order.length; i++) {
      var idx = order[i], y = D.top + i * D.dy;
      var g = rows[idx];
      g.setAttribute('transform', 'translate(0 ' + y.toFixed(1) + ')');
      // Re-appending in sort order is what preserves the occlusion: the row in
      // front has to be painted after the one it hides.
      frag.appendChild(g);
      placed.push([y, idx]);
    }
    host.appendChild(frag);
    sort = key;
  }

  function toUser(ev) {
    var r = svg.getBoundingClientRect();
    var t = ev.touches && ev.touches[0] ? ev.touches[0] : ev;
    var vb = svg.viewBox.baseVal;
    return [(t.clientX - r.left) / r.width * vb.width,
            (t.clientY - r.top) / r.height * vb.height];
  }

  function show(slot, clientX, clientY) {
    if (slot == null) {
      hi.setAttribute('opacity', '0');
      tip.classList.remove('co-tip-show');
      return;
    }
    var y = placed[slot][0], m = D.marks[placed[slot][1]];
    // Reuse the row's own stroke geometry for the highlight rather than
    // recomputing it; child 1 of the group is the open profile path.
    var stroke = rows[placed[slot][1]].children[1];
    hi.setAttribute('d', stroke.getAttribute('d'));
    hi.setAttribute('transform', 'translate(0 ' + y.toFixed(1) + ')');
    hi.setAttribute('opacity', '0.95');
    tip.innerHTML = '<b>' + m[0] + '</b> · ' + m[1] + ' · ' +
                    m[2].toLocaleString() + ' ft climbed · ' +
                    m[3].toFixed(1) + ' mi · ' + m[4];
    tip.classList.add('co-tip-show');
    positionTip(clientX, clientY);
  }

  function at(ev) {
    var p = toUser(ev);
    var t = ev.touches && ev.touches[0] ? ev.touches[0] : ev;
    var slot = Math.round((p[1] - D.top) / D.dy);
    if (slot < 0 || slot >= placed.length) { show(null); return; }
    show(Math.abs(p[1] - placed[slot][0]) < 14 ? slot : null, t.clientX, t.clientY);
  }

  svg.addEventListener('mousemove', at);
  svg.addEventListener('mouseleave', function () { show(null); });
  svg.addEventListener('touchstart', function (e) { at(e); e.preventDefault(); },
                       { passive: false });
  svg.addEventListener('touchmove', function (e) { at(e); e.preventDefault(); },
                       { passive: false });

  var bar = document.getElementById('co-sort');
  if (bar) {
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-sort]');
      if (!b) return;
      [].forEach.call(bar.children, function (c) {
        c.classList.toggle('co-on', c === b);
      });
      apply(b.dataset.sort);
      show(null);
    });
  }

  apply('gain');

  // The tooltip lives on <body>, not inside this view's own shown/hidden
  // section, so it won't auto-hide via the page's router when switching
  // tabs. Hide it whenever the SVG itself stops intersecting the viewport
  // -- covers a tab switch without coupling to the router's JS at all.
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      if (!entries[0].isIntersecting) { show(null); }
    }, { threshold: 0 }).observe(svg);
  }
})();
"""
