"""Static 800x480 pages for the SenseCraft HMI Web function.

No JavaScript, no CDN, no webfonts, no scrolling: whatever renderer the panel
uses, plain markup and an inline SVG work. The card is sized in exact user
units so nothing depends on the CSS cascade or on font metrics.
"""

from .config import H, W, WHITE
from .svg import esc

_CSS = f"""html,body{{margin:0;padding:0;background:{WHITE};
  width:{W}px;height:{H}px;overflow:hidden}}
svg{{display:block}}"""


def render_page(card, asof):
    """The device page: exactly one card, exactly 800x480."""
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
        f'<meta name="viewport" content="width={W},height={H}">\n'
        f"<title>{esc(card.title)}</title>\n<style>{_CSS}</style></head>\n"
        f"<body>{card.svg()}</body></html>\n"
    )


_SHEET_CSS = """body{margin:0;padding:24px;background:#e9e9e9;
  font-family:Helvetica,Arial,sans-serif}
figure{margin:0 0 28px;width:800px}
figcaption{font-size:13px;color:#333;padding:6px 2px}
svg{display:block;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.3)}
b{font-family:ui-monospace,Menlo,monospace}"""


def render_contact_sheet(cards, asof):
    """Every card stacked, for previewing the whole rotation in one scroll.

    A build convenience, not something the panel ever loads.
    """
    figs = []
    for i, c in enumerate(cards):
        figs.append(
            f"<figure id=\"{esc(c.id)}\">{c.svg()}"
            f"<figcaption><b>{esc(c.id)}</b> · day {i} of the rotation · "
            f"{esc(c.title)}</figcaption></figure>"
        )
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
        f"<title>e-paper cards — {asof.isoformat()}</title>\n"
        f"<style>{_SHEET_CSS}</style></head>\n<body>"
        + "".join(figs) + "</body></html>\n"
    )
