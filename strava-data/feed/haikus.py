"""Every activity's haiku on one page → running-log/haiku.html

Not a card: the ``haiku`` card shows only the newest activity's poem, and this
page is the history behind it. Nothing is logged to build it. ``metrics.haiku``
seeds on the activity id, so the same activity always writes the same poem and
the whole back catalog can be regenerated from the data on every build.

The price of regenerating: the page reflects the *current* templates. Edit a
word bank in ``metrics.py`` and older poems change with it, so this is the list
each activity would get today, not a frozen record of what the panel showed.

Unlike the cards, this is a page for a person in a browser: it follows the
site's light/dark control (``nerd_common.theme_ui``, the shared ``dns-theme``
key) and uses system fonts, so it still loads with no CDN at all.
"""

from nerd_common.theme_ui import (THEME_INIT_JS, THEME_TOGGLE_CSS, THEME_TOGGLE_HTML,
                                  THEME_TOGGLE_JS)
from nerd_common.tokens import (ACCENT, ACCENT_DIM, BG_BASE, BG_GLASS, BORDER_SUBTLE,
                                TEXT_PRIMARY, TEXT_SECONDARY)

from . import fmt as F
from . import metrics as M
from .svg import esc


def history(acts):
    """``(activity, haiku)`` for every activity, newest first.

    Built exactly as the card builds its one poem - same ``sightings`` map,
    same ``metrics.haiku`` - so the page and the card cannot disagree. Ties on
    a date break on the start time and then the id, so the order is stable.
    """
    sightings = {str(r["id"]): M.animal_hits(r) for r in acts if M.animal_hits(r)}
    out = []
    for a in acts:
        h = M.haiku(a, sightings)
        if h:
            out.append((a, h))
    out.sort(key=lambda p: (p[0]["_dt"], str(p[0]["id"])), reverse=True)
    return out


def _meta(a):
    parts = [esc(a["name"]), F.day(a["_date"], "%d %b %Y")]
    if a["_mi"] >= 0.5:
        parts.append(f"{a['_mi']:.1f} mi")
    parts.append(esc(F.sport(a["sport_type"])))
    return " · ".join(parts)


_CSS = f"""
:root {{
  --bg: {BG_BASE};
  --glass: {BG_GLASS};
  --rule: {BORDER_SUBTLE};
  --ink: {TEXT_PRIMARY};
  --muted: {TEXT_SECONDARY};
  --accent: {ACCENT};
  --accent-dim: {ACCENT_DIM};
  /* theme_ui's toggle reads these names */
  --bg-glass: {BG_GLASS};
  --border-subtle: {BORDER_SUBTLE};
  --text-primary: {TEXT_PRIMARY};
  --text-secondary: {TEXT_SECONDARY};
}}
:root.light {{
  --bg: #ffffff;
  --glass: rgba(255, 255, 255, 0.75);
  --rule: rgba(140, 149, 159, 0.3);
  --ink: #11161d;
  --muted: #424a53;
  --accent: #0550ae;
  --accent-dim: rgba(5, 80, 174, 0.10);
  --bg-glass: rgba(255, 255, 255, 0.75);
  --border-subtle: rgba(140, 149, 159, 0.3);
  --text-primary: #11161d;
  --text-secondary: #424a53;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
}}
main {{ max-width: 640px; margin: 0 auto; padding: 32px 16px 64px; }}
header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }}
@media (max-width: 640px) {{
  /* Beside the title the toggle squeezes the lede into half the width. */
  header {{ flex-direction: column-reverse; gap: 8px; }}
  header .theme-toggle {{ align-self: flex-end; }}
}}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
.lede {{ color: var(--muted); margin: 0 0 8px; }}
h2 {{
  font-size: 13px; letter-spacing: 0.12em; color: var(--muted);
  border-bottom: 1px solid var(--rule); padding-bottom: 6px; margin: 40px 0 0;
}}
article {{ padding: 20px 0; border-bottom: 1px solid var(--rule); }}
.poem {{ font: 20px/1.45 Georgia, "Times New Roman", serif; margin: 0; }}
.poem span {{ display: block; }}
.poem .mid {{ color: var(--muted); }}
.meta {{ color: var(--muted); font-size: 13px; margin-top: 8px; }}
.now {{
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
  color: var(--accent); background: var(--accent-dim); border-radius: 4px;
  padding: 1px 6px; margin-bottom: 8px;
}}
{THEME_TOGGLE_CSS}
"""


def render(acts, asof):
    """The page, as one self-contained HTML string."""
    rows = history(acts)
    body, year = [], None
    for i, (a, h) in enumerate(rows):
        if a["_date"].year != year:
            year = a["_date"].year
            body.append(f"<h2>{year}</h2>")
        l1, l2, l3 = (esc(s) for s in h["lines"])
        now = '<div class="now">ON THE PANEL NOW</div>' if i == 0 else ""
        body.append(
            f'<article>{now}<p class="poem"><span>{l1}</span><span class="mid">{l2}</span>'
            f'<span>{l3}</span></p><div class="meta">{_meta(a)}</div></article>')
    n = len(rows)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Every haiku so far</title>
{THEME_INIT_JS}
<style>{_CSS}</style>
</head>
<body>
<main>
<header>
  <div>
    <h1>Every haiku so far</h1>
    <p class="lede">{n} poems, one per activity, newest first. Each is a
    five-seven-five assembled from that activity's own numbers. The newest is the
    one on the e-paper panel right now. Data as of {F.day(asof, "%d %B %Y")}.</p>
  </div>
  {THEME_TOGGLE_HTML}
</header>
{"".join(body)}
</main>
<script>{THEME_TOGGLE_JS}</script>
</body>
</html>
"""
