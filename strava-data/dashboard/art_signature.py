"""B4b — Signature Route: one loop, and every time it was run.

The most-repeated loop in the record drawn solid, with all of its
near-identical siblings ghosted behind it on a shared scale. The subject is not
the route -- it is the **GPS wander between repeats**, the fuzz of twenty runs
of the same four miles.

Promoted from `tools/proof_landing_art.py:_signature` / `b4b_signature`. Two
things change on a dashboard. There is more than one signature route here (five
~4.5 mi loops each repeated 19-21 times), so hardcoding a single pick throws
most of the finding away: this builds a **picker** over the top clusters.
And each ghost can carry its own pace, which turns the piece into "did I get
faster on this loop over two years?" -- a question the dashboard cannot
otherwise answer.

**Cluster detection is a grid-cell Jaccard on the recentered track** (100 m
cells, overlap > 0.5). It is `poster_40for40.py`'s duplicate test inverted:
there it keeps two laps of one loop off the wall, here it finds them on
purpose. Recentering on the start point is what makes it work -- two runs of
the same loop compare equal even when the watch caught a different driveway.

The comparison is O(n^2) over the ~300 candidates left after the distance
filter. That is fine at build time; as the record grows, the cut is a cheap
prefilter on distance and start point before the pairwise pass, not a smarter
Jaccard.

Every id and class is prefixed `sg-`; theme is pure cascade.
"""

import json
from collections import defaultdict

from nerd_common.geometry import path, set_streams_dir, simplify, thin, track

from .art_year import prepare
from .config import STREAMS_DIR

set_streams_dir(STREAMS_DIR)

S = 900
PAD = 116

CELL_M = 100.0        # grid cell for the Jaccard signature
OVERLAP = 0.5         # two tracks are the same loop above this
KM_LO, KM_HI = 1.0, 13.0
NCLUSTER = 5          # how many signature loops the picker offers
MIN_REPEATS = 4

SG_COLORS = {
    "sg-line":  ("#2dd4bf", "#0d9488"),   # the signature itself
    "sg-ghost": ("#2dd4bf", "#0d9488"),   # the repeats, drawn faint
    "sg-fast":  ("#f59e0b", "#b45309"),   # the quickest repeat
    "sg-ink":   ("#64748b", "#64748b"),
}


def _paint(key):
    return "var(--%s, %s)" % (key, SG_COLORS[key][0])


_SG_CSS_BODY = """
#sg-svg { display:block; width:100%; max-width:720px; margin:0 auto; }
.sg-bar { display:flex; flex-wrap:wrap; gap:6px; justify-content:center;
          margin:12px 0 0; }
.sg-bar button { font:inherit; font-size:12px; line-height:1; cursor:pointer;
  padding:6px 12px; border-radius:999px; color:var(--text-secondary,#94a3b8);
  background:transparent; border:1px solid var(--border,#243044); }
.sg-bar button.sg-on { color:var(--text-primary,#e2e8f0);
  border-color:var(--accent,#2dd4bf); }
#sg-readout { text-align:center; min-height:2.4em; margin:10px 0 0;
  font-size:13px; color:var(--text-secondary,#94a3b8); }
#sg-readout b { color:var(--text-primary,#e2e8f0); font-weight:600; }
"""


def _css():
    dark = "".join("--%s: %s; " % (k, v[0]) for k, v in SG_COLORS.items())
    light = "".join("--%s: %s; " % (k, v[1]) for k, v in SG_COLORS.items())
    return ":root { %s }\n:root.light { %s }\n%s" % (dark, light, _SG_CSS_BODY)


def _clusters(acts, tracks):
    """The top signature loops, each as (anchor id, [member ids]).

    Members are the transitive-free neighbor set of the anchor, matching the
    proof: a run is in the cluster when it matches the anchor directly, not
    when it matches something that matches the anchor.
    """
    cand = [a for a in acts
            if tracks.get(a["id"]) and KM_LO < a["km"] < KM_HI]
    sig = {a["id"]: frozenset((round(x / CELL_M), round(y / CELL_M))
                              for x, y in tracks[a["id"]]) for a in cand}
    ids = sorted(sig)
    hits = defaultdict(list)
    for i, p in enumerate(ids):
        for q in ids[i + 1:]:
            u = len(sig[p] | sig[q])
            if u and len(sig[p] & sig[q]) / u > OVERLAP:
                hits[p].append(q)
                hits[q].append(p)
    if not hits:
        return []

    # Pick anchors greedily by repeat count, skipping any whose members are
    # already spoken for -- otherwise the five entries in the picker are five
    # views of the same loop.
    used = set()
    out = []
    for anchor in sorted(hits, key=lambda k: (-len(hits[k]), k)):
        if anchor in used or len(hits[anchor]) < MIN_REPEATS:
            continue
        members = sorted(hits[anchor])
        if sum(1 for m in members if m in used) > len(members) / 2:
            continue
        used.add(anchor)
        used.update(members)
        out.append((anchor, members))
        if len(out) >= NCLUSTER:
            break
    return out


def _pace_min_mi(a):
    mi = a["km"] * 0.621371
    return (a["min"] / mi) if (mi > 0 and a["min"] > 0) else None


def _mmss(p):
    m = int(p)
    return "%d:%02d" % (m, int(round((p - m) * 60)))


def art_signature_html(rows):
    """The whole self-contained fragment: style + svg + picker + script."""
    acts = prepare(rows)
    tracks = {}
    for a in acts:
        t = track(a["id"])
        if t:
            tracks[a["id"]] = t
    if not tracks:
        return ""

    clusters = _clusters(acts, tracks)
    if not clusters:
        return ""

    by_id = {a["id"]: a for a in acts}
    layers, meta, buttons = [], [], []

    for ci, (anchor, members) in enumerate(clusters):
        ids = [anchor] + members

        # ONE scale shared across the whole cluster. Fitting each repeat to its
        # own bounds aligns them on the *frame* instead of on *each other*, and
        # the wander -- the entire subject of the piece -- vanishes. So the
        # bounds are computed over the union and every track goes through the
        # same transform.
        allpts = [p for aid in ids for p in tracks[aid]]
        minx = min(p[0] for p in allpts)
        maxx = max(p[0] for p in allpts)
        miny = min(p[1] for p in allpts)
        maxy = max(p[1] for p in allpts)
        s = min((S - PAD) / max(maxx - minx, 1e-9),
                (S - PAD) / max(maxy - miny, 1e-9))
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2

        def place(pts, s=s, cx=cx, cy=cy):
            return [(S / 2 + (x - cx) * s, S / 2 + (y - cy) * s) for x, y in pts]

        paces = {aid: _pace_min_mi(by_id[aid]) for aid in ids}
        timed = [p for p in paces.values() if p]
        fastest = min(timed) if timed else None

        ghosts = []
        for aid in sorted(members, key=lambda i: by_id[i]["dt"]):
            pp = thin(simplify(place(tracks[aid]), 1.2), 120)
            quick = paces[aid] is not None and paces[aid] == fastest
            ghosts.append('<path d="%s" stroke="%s" opacity="%.2f"/>'
                          % (path(pp), _paint("sg-fast" if quick else "sg-ghost"),
                             0.55 if quick else 0.2))

        sig_pts = simplify(place(tracks[anchor]), 1.2)
        body = ('<g fill="none" stroke-width="1.5" stroke-linejoin="round">%s</g>'
                '<path d="%s" fill="none" stroke="%s" stroke-width="2.8" '
                'stroke-linejoin="round" stroke-linecap="round"/>'
                % ("".join(ghosts), path(sig_pts), _paint("sg-line")))
        layers.append('<g class="sg-layer" data-c="%d"%s>%s</g>'
                      % (ci, "" if ci == 0 else ' style="display:none"', body))

        a = by_id[anchor]
        mi = a["km"] * 0.621371
        dts = sorted(by_id[i]["dt"] for i in ids)
        meta.append({
            "n": len(ids),
            "mi": round(mi, 1),
            "from": dts[0].strftime("%b %Y"),
            "to": dts[-1].strftime("%b %Y"),
            "fast": _mmss(fastest) if fastest else None,
            "slow": _mmss(max(timed)) if timed else None,
        })
        buttons.append('<button type="button" data-c="%d" class="%s">'
                       '%.1f mi &middot; %d&times;</button>'
                       % (ci, "sg-on" if ci == 0 else "", round(mi, 1), len(ids)))

    blob = json.dumps({"meta": meta}, separators=(",", ":")).replace("</", "<\\/")

    return (
        "<style>%s</style>" % _css()
        + '<svg id="sg-svg" viewBox="0 0 %d %d" role="img" '
          'aria-label="The most-repeated loop in the record drawn solid, with '
          'every other run of the same loop ghosted behind it on a shared '
          'scale.">%s</svg>' % (S, S, "".join(layers))
        + '<div class="sg-bar" id="sg-pick">%s</div>' % "".join(buttons)
        + '<p id="sg-readout"></p>'
        + '<script id="sg-data" type="application/json">%s</script>' % blob
        + "<script>%s</script>" % SG_JS
    )


SG_JS = r"""
(function () {
  var svg = document.getElementById('sg-svg');
  var dataEl = document.getElementById('sg-data');
  if (!svg || !dataEl) return;
  var meta = JSON.parse(dataEl.textContent).meta;
  var out = document.getElementById('sg-readout');
  var bar = document.getElementById('sg-pick');

  function describe(i) {
    var m = meta[i];
    var s = '<b>' + m.n + ' runs</b> of the same ' + m.mi.toFixed(1) +
            '-mile loop, ' + m.from + ' to ' + m.to + '.';
    if (m.fast && m.slow) {
      s += ' Fastest ' + m.fast + '/mi, slowest ' + m.slow +
           '/mi — the quickest one is picked out in amber.';
    }
    out.innerHTML = s;
  }

  if (bar) {
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-c]');
      if (!b) return;
      var i = +b.dataset.c;
      [].forEach.call(bar.children, function (c) {
        c.classList.toggle('sg-on', c === b);
      });
      [].forEach.call(svg.querySelectorAll('.sg-layer'), function (g) {
        g.style.display = +g.dataset.c === i ? '' : 'none';
      });
      describe(i);
    });
  }
  describe(0);
})();
"""
