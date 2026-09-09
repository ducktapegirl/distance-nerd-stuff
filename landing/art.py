"""The two tile artworks.

Left tile: **Ring of Seasons** — four concentric ribbons, one per academic year,
thickness = that week's mileage. Right tile: **Route Grid** — a specimen sheet of
48 routes, each normalized to its own cell and colored by sport family.

Chosen from twelve directions rendered by `tools/proof_landing_art.py`; the
proof sheet and the ten that lost are under
`Project Docs/Plans/landing-art/proofs/`, and the brief is
`Project Docs/Plans/landing-art.md`. Pattern against path, circle against grid:
the pair has to be tellable apart at a glance at 240 px, which is the constraint
easiest to lose while polishing either tile alone.

Contract, unchanged except where noted:

1. **Inline SVG only.** Return an `<svg …>…</svg>` string. No `<img>`, no
   canvas, no external asset — the art has to theme-switch, and a raster can't.
2. **Theme-aware via CSS variables with literal fallbacks**, e.g.
   `fill="var(--art-col, #a78bfa)"`. `paint()` below is the gate; rasterizers do
   not implement `var()`, so every call carries the dark literal. `ART_COLORS`
   is the single source of both the fallbacks and the CSS that `template.py`
   emits, so the two cannot drift.
3. **`viewBox` + `preserveAspectRatio`, never fixed px.** The tile is fluid.
   **The frame is 4:3, not square** — `.tile-art-wrap` is `aspect-ratio: 4 / 3`
   and slices, so a square artwork silently loses 12.5% off the top and the same
   off the bottom. `size` is the viewBox *height*; the width follows.
4. **Deterministic.** Same CSV in, same SVG out. No `random()`, no clock, and
   every selection below sorts before it slices — otherwise each deploy produces
   a spurious diff and the page can't be regression-tested.
5. **Under ~40 KB of SVG per tile.** Ring of Seasons is ~6 KB; Route Grid ~24 KB
   after Douglas-Peucker and a hard 46-point cap per route. Drawing all 351
   routes would be ~595 KB, so the grid's subset is a budget requirement, not a
   preference.
6. **Legible at 240px.** Both were checked at that size, in both themes, beside
   each other.

Both take the already-loaded rows, and both fall back to `_placeholder()` when
handed nothing — a fresh clone may have one CSV and not the other.
"""

import math
from collections import defaultdict
from datetime import date

from nerd_common.geometry import COLOR, FAMILY, bbox, fit, path, simplify, thin

from .config import TILES

# name -> (dark, light). The single source of truth for both the literal
# fallbacks in the SVG and the custom properties template.py writes into
# :root / :root.light. The five family values match the Strava dashboard's
# art_year.py ART_CSS block so the site keeps one vocabulary; --art-col is the
# college tile's violet from TILES, darkened for the light theme because
# #a78bfa on white is unreadable.
ART_COLORS = {
    "art-bg":    ("#1c2230", "#ffffff"),
    "art-col":   ("#a78bfa", "#7c3aed"),
    "art-run":   ("#2dd4bf", "#0d9488"),
    "art-mtb":   ("#f59e0b", "#b45309"),
    "art-foot":  ("#a3e635", "#4d7c0f"),
    "art-snow":  ("#60a5fa", "#1d4ed8"),
    "art-other": ("#f472b6", "#be185d"),
}
FAM_VAR = {"run": "art-run", "mtb": "art-mtb", "foot": "art-foot",
           "snow": "art-snow", "other": "art-other"}

WEEKS = 53          # slots in an academic year, anchored on 1 August
ASPECT = 4 / 3      # .tile-art-wrap

_ACCENTS = {t["key"]: t["accent"] for t in TILES}


def paint(key):
    """`var()` for the page, with the dark literal as the rasterizer fallback."""
    return "var(--%s, %s)" % (key, ART_COLORS[key][0])


def art_css(light=False):
    """The custom-property block for one theme. template.py emits both."""
    return "".join("--%s: %s; " % (k, v[1 if light else 0])
                   for k, v in ART_COLORS.items())


def _frame(size):
    """(width, height, scale). Geometry below is tuned in 480-unit space."""
    return round(size * ASPECT), size, size / 480.0


def _svg(body, label, size):
    w, h, _ = _frame(size)
    return """<svg class="tile-art" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid slice"
     role="img" aria-label="%s" focusable="false">
  <rect width="%d" height="%d" fill="%s"/>
%s
</svg>""" % (w, h, label, w, h, paint("art-bg"), body)


def _placeholder(key, label, size):
    """A calm stand-in for when the data isn't there.

    Reached on a fresh clone or a fork PR that has one CSV and not the other.
    Intentionally quiet and intentionally not a chart — it should read as a
    deliberate blank rather than a broken image.
    """
    accent = _ACCENTS.get(key, "#58a6ff")
    w, h, _ = _frame(size)
    gid = "artph-%s" % key
    return """<svg class="tile-art" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid slice"
     role="img" aria-label="%s — artwork placeholder" focusable="false">
  <defs>
    <radialGradient id="%s" cx="32%%" cy="28%%" r="78%%">
      <stop offset="0%%"   stop-color="%s" stop-opacity="0.42"/>
      <stop offset="55%%"  stop-color="%s" stop-opacity="0.10"/>
      <stop offset="100%%" stop-color="%s" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="%d" height="%d" fill="%s"/>
  <rect width="%d" height="%d" fill="url(#%s)"/>
  <text x="%.0f" y="%.0f" text-anchor="middle" dominant-baseline="middle"
        font-family="'Geist Mono', monospace" font-size="%.0f"
        letter-spacing="%.1f"
        fill="var(--text-tertiary, #8b949e)" opacity="0.75">%s</text>
</svg>""" % (w, h, label, gid, accent, accent, accent, w, h, paint("art-bg"),
             w, h, gid, w / 2, h / 2, h * 0.045, h * 0.012, label)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def college_art(rows, *, size=480):
    """Ring of Seasons — the College Running Log tile.

    `rows` is running_log.csv as dicts (date, miles, minutes, workout_type, …).
    No GPS exists for 2003-2007, so the art is built from time and quantity:
    four concentric ribbons, one per academic year, each week's arc as thick as
    that week's mileage.

    Deliberately coarser than `running-log/dashboard/year_clock.py` and stripped
    of every label — otherwise the tile is a small copy of a chart the dashboard
    already has. The gaps are the subject: the inner ring opens at the top,
    where the log starts four weeks into freshman fall, and the outer one stops
    dead three-quarters of the way round, at graduation in May 2007.

    The rings are thin and widely spaced on purpose. Thicker ones merge into a
    single spiral swoosh and the four years stop being four years.
    """
    runs = []
    for r in rows:
        mi = _num(r.get("miles"))
        if mi <= 0 or not r.get("date"):
            continue
        d = date.fromisoformat(r["date"])
        # August anchors the academic year, which is what keeps 2003-08-31 —
        # the very first entry — out of a fifth, one-day-long year.
        ay = d.year if d.month >= 8 else d.year - 1
        runs.append((ay, min((d - date(ay, 8, 1)).days // 7, WEEKS - 1), mi))
    if not runs:
        return _placeholder("college", "COLLEGE", size)

    weeks = defaultdict(float)
    for ay, wk, mi in runs:
        weeks[(ay, wk)] += mi
    years = sorted({k[0] for k in weeks})
    mx = max(weeks.values())

    w, h, k = _frame(size)
    cx, cy = w / 2, h / 2
    out = []
    for i, ay in enumerate(years):
        rc = (85 + i * 42) * k
        outer, inner = [], []
        for wk in range(WEEKS):
            a = math.radians(-90 + wk / WEEKS * 360)
            # A week with no miles pinches the ribbon to nothing, which is how
            # the breaks and the end of the log draw themselves.
            t = 15.0 * k * min(weeks.get((ay, wk), 0.0) / mx, 1.0)
            ca, sa = math.cos(a), math.sin(a)
            outer.append((cx + (rc + t) * ca, cy + (rc + t) * sa))
            inner.append((cx + (rc - t) * ca, cy + (rc - t) * sa))
        d = (path(outer) + "L"
             + "L".join("%.1f %.1f" % p for p in reversed(inner)) + "Z")
        out.append('  <path d="%s" fill="%s" opacity="%.2f"/>'
                   % (d, paint("art-col"),
                      0.5 + 0.5 * i / max(len(years) - 1, 1)))
    return _svg("\n".join(out), "Four years of weekly mileage as concentric rings",
                size)


def strava_art(rows, *, tracks=None, size=480):
    """Route Grid — the Strava tile.

    `rows` is activities.csv as dicts and `tracks` is `{id: [(x, y), …]}` from
    `data.load_tracks()`, projected and recentered. A specimen sheet: 48 routes,
    each normalized to its own square cell, one color per sport family — the
    poster (`strava-data/tools/poster_40for40.py`) at thumbnail scale, which is
    a family resemblance worth having.

    8x6 rather than a square 6x6: in a 640x480 frame that is 48 exactly square
    cells, where 6x6 would be 100x73 and quietly distort every route that filled
    one.

    Two selection rules, both of which the proofs earned. Routes are ranked on
    **shape before size** — sorting by distance alone fills the sheet with the
    longest rides, which are point-to-point and draw as near-identical
    diagonals. And the per-family quota is proportional, so a sheet of 48 is not
    48 neighbourhood running loops.

    **Known and accepted: about 11 of the 48 still draw as near-straight.** The
    quota is not what causes it — all 48 clear the 0.38 bar with room to spare,
    and the pool has slack (185 of 216 running routes qualify for 30 slots), so
    raising the threshold changes nothing. Bounding-box squarishness simply
    cannot see a straight line: an out-and-back that drifts sideways has a
    square box and one stroke ("Silver Strand 12k" scores 0.71). The metric that
    does catch it is tortuosity — path length over box diagonal, where ~1.4 means
    out-and-back — but ranking by it selects for lapping a small area, and the
    sheet fills with the same neighbourhood loop three times and the same track
    oval three times. Fixing it properly means tortuosity *plus* a duplicate
    test, i.e. poster_40for40.py's 100 m grid-cell Jaccard comparison applied in
    reverse. Weighed against a handful of honest point-to-point cells, that was
    not judged worth the build time. Don't "fix" the threshold; it isn't the
    lever.
    """
    tracks = tracks or {}
    keep = [r for r in rows if tracks.get(r.get("id"))]
    if not keep:
        return _placeholder("strava", "STRAVA", size)

    cols, rowsn = 8, 6
    n = cols * rowsn
    byfam = defaultdict(list)
    for r in keep:
        byfam[FAMILY.get(r.get("sport_type", ""), "other")].append(r)

    def squarish(r):
        x0, y0, x1, y1 = bbox(tracks[r["id"]])
        bw, bh = x1 - x0, y1 - y0
        return min(bw, bh) / max(bw, bh, 1e-9) >= 0.38

    quota = {f: max(1, round(len(v) / len(keep) * n)) for f, v in byfam.items()}
    picked = []
    for f in sorted(byfam):
        # `not squarish` first so loops sort ahead of straight lines; id last so
        # a tie never depends on dict order.
        ranked = sorted(byfam[f],
                        key=lambda r: (not squarish(r),
                                       -_num(r.get("distance_km")), r["id"]))
        picked += ranked[:quota[f]]
    picked = sorted(picked, key=lambda r: r.get("start_date_local", ""))[:n]

    w, h, k = _frame(size)
    cw, ch = w / cols, h / rowsn
    out = []
    for i, r in enumerate(picked):
        fam = FAMILY.get(r.get("sport_type", ""), "other")
        pp = fit(thin(simplify(tracks[r["id"]], 6.0), 46),
                 (i % cols) * cw, (i // cols) * ch, cw, ch, pad=11 * k)
        out.append('  <path d="%s" fill="none" stroke="%s" stroke-width="%.2f" '
                   'stroke-linejoin="round" stroke-linecap="round" opacity="0.92"/>'
                   % (path(pp, 0), paint(FAM_VAR[fam]), 1.3 * k))
    return _svg("\n".join(out), "Forty-eight GPS routes, one per cell, "
                               "colored by sport", size)
