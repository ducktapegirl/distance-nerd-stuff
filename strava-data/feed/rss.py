"""RSS 2.0 writer for the SenseCraft HMI RSS function.

Deliberately plain: no HTML in descriptions, no enclosures, no CDATA. The
panel's feed reader shows a title and an excerpt, so every item has to be a
self-contained sentence.
"""

from datetime import datetime, time, timezone
from xml.sax.saxutils import escape

from .config import SITE

FEED_URL = f"{SITE}/feed.xml"
PAGE_URL = f"{SITE}/epaper.html"


def _rfc822(d):
    return datetime.combine(d, time(12, 0), tzinfo=timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000")


def build_rss(cards, asof, athlete):
    """One item per card, newest-dated first."""
    who = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip() or "athlete"
    bio = (athlete.get("bio") or "").strip()
    built = _rfc822(asof)

    items = []
    for c in cards:
        # GUIDs stay stable per card per data date, so the reader treats a
        # refreshed number as a new item but a re-publish of the same data as
        # the one it already has.
        guid = f"{SITE}/feed/{c.id}/{asof.isoformat()}"
        items.append(
            "    <item>\n"
            f"      <title>{escape(c.title)}</title>\n"
            f"      <description>{escape(c.summary)}</description>\n"
            f"      <link>{PAGE_URL}#{escape(c.id)}</link>\n"
            f'      <guid isPermaLink="false">{escape(guid)}</guid>\n'
            f"      <pubDate>{built}</pubDate>\n"
            "    </item>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{escape(who)} — distance nerd stuff</title>\n"
        f"    <link>{PAGE_URL}</link>\n"
        f"    <description>{escape(bio or 'Strava numbers, one fact at a time.')}</description>\n"
        "    <language>en-us</language>\n"
        f"    <lastBuildDate>{built}</lastBuildDate>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )
