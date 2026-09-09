"""Assemble running-log/index.html — the two-door landing page."""

import html

from nerd_common.theme_ui import THEME_INIT_JS, THEME_TOGGLE_HTML, THEME_TOGGLE_JS

from .art import college_art, strava_art
from .config import REPO_URL, SITE_BLURB, SITE_TITLE, TILES
from .data import load_college, load_strava
from .template import CSS

# One art generator per tile key, each taking the whole payload so a tile can
# ask for more than `rows` — the Route Grid needs the GPS tracks as well.
# Adding a third dashboard means adding a TILES entry and a generator here;
# nothing else in this module is tile-specific.
_ART = {
    "college": lambda p: college_art(p["rows"]),
    "strava":  lambda p: strava_art(p["rows"], tracks=p.get("tracks")),
}


def _explainer_html():
    """The "What are these graphics?" panel that sits under the two tiles.

    A native <details>, so it costs no JavaScript — the theme toggle is still
    the only script on the page — and it gets keyboard support, the disclosure
    role and find-in-page expansion for free.

    Deliberately explains the two things about each drawing that are not
    guessable: that the college rings pinch to nothing where the log stops, and
    that every route in the grid is scaled to its own cell, so a cell shows
    shape and not distance. It adds no outbound links; the page still has three.
    """
    return """      <details class="explainer">
        <summary>What are these graphics?</summary>
        <div class="explainer-body">
          <section>
            <h3>College &mdash; Ring of Seasons</h3>
            <p>Four rings, one per academic year: innermost is 2003&ndash;04, outermost
            2006&ndash;07. Each ring is a single year read clockwise from the top, starting
            in August, and its thickness at any point is the miles run that week.</p>
            <p>Where nothing was logged the ring pinches to nothing. That is why the inner
            ring opens at the top &mdash; the log begins a few weeks into freshman fall &mdash;
            and why the outer one stops three&#8209;quarters of the way round, at graduation in
            May 2007. There is no GPS in this era at all; it was a paper log, so the drawing
            is built from dates and mileage alone.</p>
          </section>
          <section>
            <h3>Strava &mdash; Route Grid</h3>
            <p>Forty&#8209;eight real GPS tracks, one to a cell, drawn from every activity that
            recorded a route. Each is scaled to fill its own square, so a cell shows a
            route's <em>shape</em>, not its size &mdash; a two&#8209;mile loop and a
            twenty&#8209;mile ride are drawn just as large.</p>
            <p>The picks are spread across sports in proportion to how often each one
            appears, and favor routes that fill a square rather than running off in a
            line. A few near&#8209;straight cells survive that: those are genuine
            out&#8209;and&#8209;backs.</p>
            <ul class="legend">
              <li><i style="background: var(--art-run, #2dd4bf)"></i>run</li>
              <li><i style="background: var(--art-mtb, #f59e0b)"></i>bike</li>
              <li><i style="background: var(--art-foot, #a3e635)"></i>hike / walk</li>
              <li><i style="background: var(--art-snow, #60a5fa)"></i>snow</li>
              <li><i style="background: var(--art-other, #f472b6)"></i>everything else</li>
            </ul>
          </section>
        </div>
      </details>"""


def _tile_html(meta, payload):
    art = _ART[meta["key"]](payload)
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
{_explainer_html()}
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
