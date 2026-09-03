#!/usr/bin/env python3
"""Build the e-paper feed → running-log/{feed.xml, epaper.html, epaper-all.html, feed.json}

A second, independent output target alongside build_dashboard.py. The dashboard
targets a browser; this targets a reTerminal Sticky ePaper panel (800x480,
4-level grayscale, no JS) driven by SenseCraft HMI's RSS and Web functions.

Everything is written into running-log/ — already the GitHub Pages publish root
— and is gitignored exactly like index.html / strava.html, so generated output
never collides with committed data.
"""

import json
import os
from datetime import date

from feed.cards import FAMILIES, ROTATION, build_cards, card_of_the_day
from feed.config import OUT_JSON, OUT_PAGE, OUT_RSS, OUT_SHEET, SITE
from feed.metrics import load
from feed.page import render_contact_sheet, render_page
from feed.rss import build_rss


def main():
    bundle = load()
    asof = bundle["asof"]
    today = date.today()
    print(f"Loaded {len(bundle['acts'])} activities, data as of {asof}")

    cards = build_cards(bundle, today)
    print(f"Built {len(cards)} cards")

    today_card = card_of_the_day(cards, today)
    outputs = {
        OUT_RSS: build_rss(cards, asof, bundle["athlete"]),
        OUT_PAGE: render_page(today_card, asof),
        OUT_SHEET: render_contact_sheet(cards, asof, ROTATION, FAMILIES),
        OUT_JSON: json.dumps({
            "as_of": asof.isoformat(),
            "built": today.isoformat(),
            "site": SITE,
            "card_of_the_day": today_card.id,
            "rotation": list(ROTATION),
            "cards": [{"id": c.id, "idea": c.idea, "family": c.family,
                       "title": c.title, "summary": c.summary,
                       "recipe": c.recipe, "in_rotation": c.id in set(ROTATION)}
                      for c in cards],
        }, indent=2) + "\n",
    }

    os.makedirs(os.path.dirname(OUT_PAGE), exist_ok=True)
    for path, body in outputs.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"-> {os.path.basename(path):18s} {len(body):>8,} bytes")
    print(f"   card of the day: {today_card.id} — {today_card.title}")


if __name__ == "__main__":
    main()
