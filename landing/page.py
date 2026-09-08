"""Assemble running-log/index.html — the two-door landing page."""

import html

from nerd_common.theme_ui import THEME_INIT_JS, THEME_TOGGLE_HTML, THEME_TOGGLE_JS

from .art import college_art, strava_art
from .config import REPO_URL, SITE_BLURB, SITE_TITLE, TILES
from .data import load_college, load_strava
from .template import CSS

# One art generator per tile key. Adding a third dashboard means adding a TILES
# entry and a generator here; nothing else in this module is tile-specific.
_ART = {
    "college": college_art,
    "strava":  strava_art,
}


def _tile_html(meta, payload):
    art = _ART[meta["key"]](payload["rows"])
    # Data-derived date range wins over the config default — the Strava log's
    # start date moves as history is backfilled, and a stale hardcoded year on
    # the front door is exactly the kind of thing nobody notices for a year.
    kicker = payload.get("kicker") or meta["kicker"]
    stats = "".join(f"<span>{html.escape(s)}</span>" for s in payload["stats"])
    return f"""      <a class="tile" href="{meta['href']}" style="--tile-accent: {meta['accent']}">
        <div class="tile-art-wrap">{art}</div>
        <div class="tile-body">
          <div class="tile-kicker">{html.escape(kicker)}</div>
          <h2 class="tile-title">{html.escape(meta['title'])}</h2>
          <p class="tile-blurb">{html.escape(meta['blurb'])}</p>
          <div class="tile-stats">{stats}</div>
        </div>
      </a>"""


def build_html():
    payloads = {"college": load_college(), "strava": load_strava()}
    # TILES order is the page order, and running log is first — which is also
    # what makes it land on top when the grid collapses to one column.
    tiles = "\n".join(_tile_html(m, payloads[m["key"]]) for m in TILES)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(SITE_TITLE)}</title>
  <meta name="description" content="{html.escape(SITE_BLURB)}"/>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;700&family=Geist+Mono:wght@400;600&display=swap" rel="stylesheet">
  {THEME_INIT_JS}
  <style>{CSS}</style>
  <script data-goatcounter="https://ducktapegirl.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</head>
<body>
  <div class="shell">
    <nav class="topnav">
      <div class="topnav-row">
        <span class="wordmark-name">{html.escape(SITE_TITLE)}</span>
        {THEME_TOGGLE_HTML}
      </div>
    </nav>
    <main>
      <div class="hero">
        <h1>{html.escape(SITE_TITLE)}</h1>
        <p>{html.escape(SITE_BLURB)}</p>
      </div>
      <div class="tiles">
{tiles}
      </div>
    </main>
    <footer class="site-footer">
      Report problems using the provided
      <a href="{REPO_URL}" target="_blank" rel="noopener noreferrer">GitHub issue templates</a>.
    </footer>
  </div>
  <script>{THEME_TOGGLE_JS}</script>
</body>
</html>
"""
