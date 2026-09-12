#!/usr/bin/env python3
"""Build the e-paper feed → running-log/{feed.xml, epaper.html, epaper-all.html, feed.json}

Plus the second panel: epaper_xiao.html, epaper_xiao-all.html and epaper_xiao/<id>.html
for the 2.9" four-color XIAO display, built from the same bundle by feed/xiao/.

A second, independent output target alongside build_dashboard.py. The dashboard
targets a browser; this targets a reTerminal Sticky ePaper panel (800x480,
4-level grayscale, no JS) driven by SenseCraft HMI's RSS and Web functions.

Everything is written into running-log/ — already the GitHub Pages publish root
— and is gitignored exactly like index.html / strava.html, so generated output
never collides with committed data.
"""

import json
import os
import sys
from datetime import date, datetime, timezone

from feed.cards import FAMILIES, ROTATION, build_cards, card_of_the_day
from feed.config import OUT_CARD_DIR, OUT_JSON, OUT_PAGE, OUT_RSS, OUT_SHEET, SITE
from feed.metrics import load
from feed.page import render_contact_sheet, render_page
from feed.rss import build_rss
from feed.xiao import cards as xiao_cards
from feed.xiao import page as xiao_page
from feed.xiao.config import (OUT_CARD_DIR as XIAO_CARD_DIR, OUT_PAGE as XIAO_PAGE,
                              OUT_SHEET as XIAO_SHEET)


def _write_card_pages(card_dir, cards, render):
    """One static page per card, and drop the pages of cards that no longer
    exist - a retired card must stop being pinnable by URL."""
    os.makedirs(card_dir, exist_ok=True)
    for c in cards:
        with open(os.path.join(card_dir, f"{c.id}.html"), "w", encoding="utf-8") as f:
            f.write(render(c))
    live = {f"{c.id}.html" for c in cards}
    stale = [f for f in os.listdir(card_dir) if f.endswith(".html") and f not in live]
    for f in stale:
        os.remove(os.path.join(card_dir, f))
    return stale


def build_xiao(bundle, today, now):
    """The second panel: the same rotation on the 296x128 four-color XIAO
    display, written beside the Sticky's outputs. Same clocks, same data."""
    cards = xiao_cards.build_cards(bundle, today)
    today_card = xiao_cards.card_of_the_hour(cards, now)
    mockups = xiao_cards.build_mockups(bundle, today)
    outputs = {
        XIAO_PAGE: xiao_page.render_page(today_card),
        XIAO_SHEET: xiao_page.render_sheet(cards, mockups, bundle["asof"],
                                           xiao_cards.ROTATION, today_card),
    }
    for path, body in outputs.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"-> {os.path.basename(path):18s} {len(body):>8,} bytes")
    stale = _write_card_pages(XIAO_CARD_DIR, cards, xiao_page.render_page)
    print(f"-> epaper_xiao/      {len(cards):>4} card pages"
          + (f" ({len(stale)} stale removed)" if stale else ""))
    print(f"   xiao card this hour: {today_card.id} — {today_card.title}")
    return cards, today_card


def main():
    # Card titles carry em dashes; a cp1252 Windows console raises
    # UnicodeEncodeError on the first print without this.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    bundle = load()
    asof = bundle["asof"]
    # Two clocks on purpose. `today` drives the cards' own daily content
    # rotation ("route of the day"); `now` drives which card is published,
    # which steps hourly. Both are UTC so a local build matches the runner.
    now = datetime.now(timezone.utc)
    today = now.date()
    print(f"Loaded {len(bundle['acts'])} activities, data as of {asof}")

    cards = build_cards(bundle, today)
    print(f"Built {len(cards)} cards")

    today_card = card_of_the_day(cards, now)
    xiao, xiao_today = build_xiao(bundle, today, now)
    outputs = {
        OUT_RSS: build_rss(cards, asof, bundle["athlete"]),
        OUT_PAGE: render_page(today_card, asof),
        OUT_SHEET: render_contact_sheet(cards, asof, ROTATION, FAMILIES),
        OUT_JSON: json.dumps({
            "as_of": asof.isoformat(),
            "built": today.isoformat(),
            "card_chosen_at": now.strftime("%Y-%m-%dT%H:00Z"),
            "site": SITE,
            "card_of_the_day": today_card.id,
            "rotation": list(ROTATION),
            "cards": [{"id": c.id, "idea": c.idea, "family": c.family,
                       "title": c.title, "summary": c.summary,
                       "recipe": c.recipe, "in_rotation": c.id in set(ROTATION)}
                      for c in cards],
            # The second panel, keyed on the same hour. Its cards reuse the
            # Sticky's ids, so this is the rotation and which of it shows.
            "xiao": {"card_of_the_hour": xiao_today.id,
                     "rotation": list(xiao_cards.ROTATION),
                     "cards": [c.id for c in xiao]},
        }, indent=2) + "\n",
    }

    os.makedirs(os.path.dirname(OUT_PAGE), exist_ok=True)
    for path, body in outputs.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"-> {os.path.basename(path):18s} {len(body):>8,} bytes")
    # One static page per card, so a single card can be pinned in SenseCraft
    # by URL, or checked locally, without waiting for its turn in the rotation.
    # The panel runs no JavaScript, so a "?card=" query could never work.
    stale = _write_card_pages(OUT_CARD_DIR, cards, lambda c: render_page(c, asof))
    print(f"-> epaper/           {len(cards):>4} card pages"
          + (f" ({len(stale)} stale removed)" if stale else ""))
    print(f"   card this hour: {today_card.id} — {today_card.title}")


if __name__ == "__main__":
    main()
