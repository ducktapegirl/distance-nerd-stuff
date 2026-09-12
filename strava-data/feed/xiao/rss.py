"""A one-item RSS feed carrying the card of the hour, image included.

SenseCraft's RSS widget is the one source its docs say the cloud re-fetches
on every scheduled refresh ("refresh with the latest headlines automatically,
without manually updating content"). The Image widget takes "an image URL or
Base64 content". Put the two together and the card can travel *inside* the
feed: this item carries the fact as title and description for text widgets,
and the rendered PNG three ways for an Image widget to bind to, whichever
its parser exposes -

- ``<enclosure url=… type="image/png">``  the standard RSS way to attach an image
- ``<dns:png>``                            the PNG as bare base64
- ``<dns:pngDataUri>``                     the same as a ``data:`` URI

One item, not sixty: the widget shows "the latest", and with one item it
cannot pick the wrong one. ``pubDate`` is the build hour so a newest-first
reader agrees. The Sticky's ``feed.xml`` is untouched - it is text for a
reader, this is a transport for a picture.
"""

from datetime import datetime, timezone
from xml.sax.saxutils import escape

from ..config import SITE

FEED_URL = f"{SITE}/feed_xiao.xml"
NS = "https://ducktapegirl.github.io/distance-nerd-stuff/ns/xiao"


def build_rss(card, png_b64, now, athlete):
    who = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip() or "athlete"
    hour = now.replace(minute=0, second=0, microsecond=0)
    stamp = hour.strftime("%a, %d %b %Y %H:%M:%S +0000")
    guid = f"{SITE}/feed_xiao/{card.id}/{hour.strftime('%Y-%m-%dT%HZ')}"
    png_url = f"{SITE}/epaper_xiao.png"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<rss version="2.0" xmlns:dns="{NS}">\n'
        "  <channel>\n"
        f"    <title>{escape(who)} — this hour on the XIAO panel</title>\n"
        f"    <link>{SITE}/epaper_xiao.html</link>\n"
        "    <description>One item: the card the 2.9-inch panel shows this hour, "
        "as text and as a four-color PNG.</description>\n"
        "    <language>en-us</language>\n"
        f"    <lastBuildDate>{stamp}</lastBuildDate>\n"
        "    <item>\n"
        f"      <title>{escape(card.title)}</title>\n"
        f"      <description>{escape(card.summary)}</description>\n"
        f"      <link>{SITE}/epaper_xiao/{escape(card.id)}.html</link>\n"
        f'      <guid isPermaLink="false">{escape(guid)}</guid>\n'
        f"      <pubDate>{stamp}</pubDate>\n"
        f'      <enclosure url="{png_url}" type="image/png" length="0"/>\n'
        f"      <dns:card>{escape(card.id)}</dns:card>\n"
        f"      <dns:png>{png_b64}</dns:png>\n"
        f"      <dns:pngDataUri>data:image/png;base64,{png_b64}</dns:pngDataUri>\n"
        "    </item>\n"
        "  </channel>\n"
        "</rss>\n"
    )
