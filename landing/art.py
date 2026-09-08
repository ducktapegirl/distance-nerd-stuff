"""The two tile artworks — currently placeholders.

>>> THE REAL ART IS NOT BUILT YET. <<<
Directions, precedents, inputs and the decisions still to make are catalogued in
`Project Docs/Plans/landing-art.md`. Replace the two function *bodies* below and
nothing else — `page.py` only ever calls these two names, and the contract in
this docstring is the whole seam.

Contract every implementation must honor:

1. **Inline SVG only.** Return an `<svg …>…</svg>` string. No `<img>`, no
   canvas, no external asset — the art has to theme-switch, and a raster can't.
2. **Theme-aware via CSS variables with literal fallbacks**, e.g.
   `fill="var(--art-run, #2dd4bf)"`. `strava-data/dashboard/art_year.py`'s
   `paint()` / `ink()` gate is the working precedent: the variable path for the
   interactive page, a literal hex for anything that rasterizes.
3. **`viewBox` + `preserveAspectRatio`, never fixed px.** The tile is fluid and
   renders at roughly half size on mobile.
4. **Deterministic.** Same CSV in, same SVG out. Seed any randomness from the
   data (an activity id, a date) — never `random()` and never the clock, or
   every deploy produces a spurious diff and the page can't be regression-tested.
5. **Under ~40 KB of SVG per tile.** `art_year.py` down-samples GPS with
   `track(aid, step=6)`; this wants to be far coarser still.
6. **Legible at 240px.** Anything that depends on reading individual strokes
   fails at the mobile size.

Both functions take the already-loaded rows so no implementation re-reads a CSV,
and both must return *something* renderable when handed an empty list — a fork
PR or a fresh clone may not have the data.
"""

from .config import TILES

# One id per tile, so a real implementation can namespace its gradients and
# filters (SVG defs share one document-wide namespace once both tiles are
# inlined into the same page — colliding ids silently cross-wire the artwork).
_ACCENTS = {t["key"]: t["accent"] for t in TILES}

_PLACEHOLDER_NOTE = (
    "<!-- placeholder art: see Project Docs/Plans/landing-art.md for the "
    "twelve directions and the decisions the art session has to make -->"
)


def _placeholder(key, label, size):
    """A calm stand-in: an off-center radial wash in the tile's accent hue.

    Intentionally quiet and intentionally not a chart — it should read as a
    deliberate blank rather than a broken image, so the page can ship and be
    reviewed on its layout alone. Follows the same contract the real art must:
    inline, fluid viewBox, theme-aware, deterministic.
    """
    accent = _ACCENTS.get(key, "#58a6ff")
    gid = f"artph-{key}"
    return f"""{_PLACEHOLDER_NOTE}
<svg class="tile-art" viewBox="0 0 {size} {size}" preserveAspectRatio="xMidYMid slice"
     role="img" aria-label="{label} — artwork placeholder" focusable="false">
  <defs>
    <radialGradient id="{gid}" cx="32%" cy="28%" r="78%">
      <stop offset="0%"   stop-color="{accent}" stop-opacity="0.42"/>
      <stop offset="55%"  stop-color="{accent}" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{size}" height="{size}" fill="var(--bg-elevated, #1c2230)"/>
  <rect width="{size}" height="{size}" fill="url(#{gid})"/>
  <text x="{size / 2:.0f}" y="{size / 2:.0f}" text-anchor="middle" dominant-baseline="middle"
        font-family="'Geist Mono', monospace" font-size="{size * 0.045:.0f}"
        letter-spacing="{size * 0.012:.1f}"
        fill="var(--text-tertiary, #8b949e)" opacity="0.75">{label}</text>
</svg>"""


def college_art(rows, *, size=480):
    """Artwork for the College Running Log tile.

    `rows` is running_log.csv as dicts (date, miles, minutes, workout_type, …).
    No GPS exists for this era, so the real art must be abstract and rhythmic —
    built from time and quantity, not geography.
    """
    return _placeholder("college", "COLLEGE", size)


def strava_art(rows, *, size=480):
    """Artwork for the Strava tile.

    `rows` is activities.csv as dicts. Note `strava-data/data/streams/` is
    gitignored, so any direction needing per-activity GPS must either precompute
    its geometry into a committed asset under `strava-data/assets/` (the repo's
    established pattern — see journey_routes.json, poster_glyphs.json) or fall
    back to this placeholder when the streams aren't present.
    """
    return _placeholder("strava", "STRAVA", size)
