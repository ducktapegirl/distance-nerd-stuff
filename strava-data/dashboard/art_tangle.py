"""B5 — Tangle: two years of GPS as one unbroken line.

Every route is laid head to tail into a single polyline. Because each track is
recentered on its own start and most of them are loops, the line keeps
returning to where it began instead of wandering off, so the activities knot
around a common center. Rooted in every activity, and it reads as pure gesture.

Promoted from `tools/proof_landing_art.py:b5_tangle`, which drew 150 of the
351 usable tracks at ~24 points each to stay under a ~40 KB tile budget. This
draws **all** of them at a far higher point count.

**Point-to-point activities translate the entire remainder of the line.** A
loop returns to its origin and costs nothing; a one-way ride shifts everything
drawn after it, and a handful of travel days visibly drag the composition off
center. The decision taken here is to **exclude non-loops** -- a track whose
end is further from its start than a fraction of its own extent is dropped --
because the piece is explicitly about the knot, and a few airport transfers
otherwise stretch the whole tangle into a diagonal smear. `LOOP_TOL` is the
knob; raising it past 1.0 admits everything and restores the proof's behavior.

Every id and class is prefixed `tg-`; theme is pure cascade. The draw-on
animation respects `prefers-reduced-motion`.
"""

import math

from nerd_common.geometry import fit, path, set_streams_dir, simplify, track

from .art_year import prepare
from .config import STREAMS_DIR

set_streams_dir(STREAMS_DIR)

S = 900
PAD = 34

# Per-route simplification tolerance, in meters, applied BEFORE concatenation.
# Simplifying the finished polyline instead would cut corners across the joins
# between activities, straightening away the very returns that make the knot.
EPS_M = 14.0

# A track counts as a loop when its start and end are within this fraction of
# its own bounding-box diagonal. 0.28 keeps genuine out-and-backs and drops
# one-way travel days.
LOOP_TOL = 0.28

TG_COLORS = {
    "tg-line": ("#2dd4bf", "#0d9488"),
}


def _paint(key):
    return "var(--%s, %s)" % (key, TG_COLORS[key][0])


_TG_CSS_BODY = """
#tg-svg { display:block; width:100%; max-width:720px; margin:0 auto; }
#tg-path { stroke-dasharray: var(--tg-len); stroke-dashoffset: var(--tg-len); }
@media (prefers-reduced-motion: reduce) {
  #tg-path { stroke-dasharray: none; stroke-dashoffset: 0; }
}
.tg-bar { display:flex; justify-content:center; margin:12px 0 0; }
.tg-bar button { font:inherit; font-size:12px; line-height:1; cursor:pointer;
  padding:6px 14px; border-radius:999px; color:var(--text-secondary,#94a3b8);
  background:transparent; border:1px solid var(--border,#243044); }
"""


def _css():
    dark = "".join("--%s: %s; " % (k, v[0]) for k, v in TG_COLORS.items())
    light = "".join("--%s: %s; " % (k, v[1]) for k, v in TG_COLORS.items())
    return ":root { %s }\n:root.light { %s }\n%s" % (dark, light, _TG_CSS_BODY)


def _is_loop(t):
    xs = [p[0] for p in t]
    ys = [p[1] for p in t]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    return math.hypot(t[-1][0] - t[0][0], t[-1][1] - t[0][1]) / diag <= LOOP_TOL


def art_tangle_html(rows):
    """The whole self-contained fragment: style + svg + control + script."""
    acts = prepare(rows)

    kept, skipped = [], 0
    for a in acts:
        t = track(a["id"])
        if not t:
            continue
        if not _is_loop(t):
            skipped += 1
            continue
        kept.append(simplify(t, EPS_M))
    if not kept:
        return ""

    # Head to tail. Each track is already recentered on its own start, so
    # appending one continues the line from wherever the last one ended.
    cur = (0.0, 0.0)
    pts = [cur]
    for t in kept:
        for x, y in t[1:]:
            pts.append((cur[0] + x, cur[1] + y))
        cur = pts[-1]

    # fit() runs once, on the finished polyline, for the same reason simplify
    # runs per route: the shared transform is what keeps every activity on one
    # scale.
    placed = fit(pts, 0, 0, S, S, pad=PAD)
    d = path(placed, 1)

    # The dash animation needs the path length, and the browser can measure it
    # itself far more accurately than a polyline sum -- but only after layout.
    # Seed a close approximation server-side so the first frame is already
    # blanked, then let the script correct it.
    approx = sum(math.dist(placed[i - 1], placed[i])
                 for i in range(1, len(placed)))

    return (
        "<style>%s</style>" % _css()
        + '<svg id="tg-svg" viewBox="0 0 %d %d" style="--tg-len:%.0f" '
          'role="img" aria-label="Every one of %d looped GPS routes drawn as a '
          'single unbroken line, each starting where the last one ended.">'
          '<path id="tg-path" d="%s" fill="none" stroke="%s" '
          'stroke-width="0.9" stroke-linejoin="round" stroke-linecap="round" '
          'opacity="0.72"/></svg>'
          % (S, S, approx, len(kept), d, _paint("tg-line"))
        + '<div class="tg-bar"><button type="button" id="tg-replay">'
          'Draw it again</button></div>'
        + '<script>%s</script>' % TG_JS
    )


TG_JS = r"""
(function () {
  var svg = document.getElementById('tg-svg');
  var p = document.getElementById('tg-path');
  if (!svg || !p) return;
  var len = 0;
  var reduceMotion = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function measure() {
    try {
      var n = p.getTotalLength();
      if (n > 0) { len = n; svg.style.setProperty('--tg-len', n.toFixed(0)); }
    } catch (e) { /* getTotalLength can throw while the tab is hidden */ }
  }

  // Driven by the Web Animations API rather than a CSS @keyframes animation
  // restarted via a style="none"-then-reflow trick, so "Draw it again" is a
  // fresh, cancellable Animation object each time -- not dependent on the
  // browser re-triggering a `forwards`-filled CSS animation from a same-tick
  // property toggle.
  function draw() {
    if (reduceMotion || !len) return;
    p.getAnimations().forEach(function (a) { a.cancel(); });
    p.animate(
      [{ strokeDashoffset: len }, { strokeDashoffset: 0 }],
      { duration: 14000, easing: 'ease-out', fill: 'forwards' }
    );
  }

  // The Art view starts display:none behind the router, so the path has no
  // layout until the tab is first shown and getTotalLength() is meaningless
  // before then. Measure (and draw) on reveal, not on load.
  if (svg.getBoundingClientRect().width > 0) { measure(); draw(); }
  else if (window.IntersectionObserver) {
    var io = new IntersectionObserver(function (es) {
      if (es.some(function (e) { return e.isIntersecting; })) {
        measure(); draw(); io.disconnect();
      }
    });
    io.observe(svg);
  }

  var btn = document.getElementById('tg-replay');
  if (btn) {
    btn.addEventListener('click', function () {
      measure();
      draw();
    });
  }
})();
"""
