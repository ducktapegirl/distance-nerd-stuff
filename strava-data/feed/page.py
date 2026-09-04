"""Static pages: the device page, and the proof sheet.

``render_page`` is what the panel loads - no JavaScript, no CDN, no webfonts,
no scrolling, sized in exact user units so nothing depends on the CSS cascade.

``render_contact_sheet`` is the opposite: a browsing surface for a person, on
a real screen, showing every card in the catalogue at once.
"""

from collections import OrderedDict

from . import fmt as F
from .config import H, W, WHITE
from .svg import esc

_CSS = f"""html,body{{margin:0;padding:0;background:{WHITE};
  width:{W}px;height:{H}px;overflow:hidden}}
svg{{display:block}}"""


def render_page(card, asof):
    """The device page: exactly one card, exactly 800x480."""
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
        f'<meta name="viewport" content="width={W},height={H}">\n'
        f"<title>{esc(card.title)}</title>\n<style>{_CSS}</style></head>\n"
        f"<body>{card.svg()}</body></html>\n"
    )


# ── proof sheet ───────────────────────────────────────────────────────────
# A darkroom contact sheet: each card is a proof, numbered by its catalogue
# frame and grouped into rolls. The page's neutral scale is the panel's own
# four tones, extended - the one detail that could only come from this subject.

_SHEET_CSS = """
:root{
  --board:#c9cbcf; --board-2:#d4d6da; --proof:#ffffff;
  --ink:#101114; --muted:#5c6068; --rule:#a8abb1; --rule-soft:#bcbfc5;
  --mark:#8a1c1c; --shadow:rgba(16,17,20,.28);
  --tone-0:#ffffff; --tone-1:#aaaaaa; --tone-2:#555555; --tone-3:#000000;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --board:#17181b; --board-2:#1e2024; --proof:#ffffff;
    --ink:#e9eaec; --muted:#9aa0a8; --rule:#33363c; --rule-soft:#2a2d32;
    --mark:#d4614a; --shadow:rgba(0,0,0,.55);
  }
}
:root[data-theme="dark"]{
  --board:#17181b; --board-2:#1e2024; --proof:#ffffff;
  --ink:#e9eaec; --muted:#9aa0a8; --rule:#33363c; --rule-soft:#2a2d32;
  --mark:#d4614a; --shadow:rgba(0,0,0,.55);
}
*{box-sizing:border-box}
/* figure sets display:flex below, which outranks the UA's
   [hidden]{display:none} - without this the filter sets the attribute
   and every proof stays on screen. */
[hidden]{display:none!important}
body{margin:0;background:var(--board);color:var(--ink);
  font-family:Archivo,"Helvetica Neue",Arial,sans-serif;
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:36px 28px 96px}

/* masthead */
.head{border-bottom:3px solid var(--ink);padding-bottom:22px;margin-bottom:8px}
.eyebrow{font-family:"DM Mono",ui-monospace,Menlo,monospace;font-size:12px;
  letter-spacing:.22em;text-transform:uppercase;color:var(--mark);margin:0 0 12px}
h1{font-size:clamp(34px,6vw,60px);line-height:.98;margin:0;font-weight:700;
  letter-spacing:-.025em;text-wrap:balance}
.standfirst{font-family:Newsreader,Georgia,serif;font-size:19px;line-height:1.5;
  max-width:60ch;color:var(--muted);margin:16px 0 0}
.spec{display:flex;flex-wrap:wrap;gap:0;margin:22px 0 0;
  border-top:1px solid var(--rule)}
.spec div{flex:1 1 120px;padding:12px 16px 4px 0;border-right:1px solid var(--rule-soft)}
.spec div:last-child{border-right:0}
.spec dt{font-family:"DM Mono",ui-monospace,monospace;font-size:11px;
  letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin:0 0 4px}
.spec dd{margin:0;font-size:17px;font-weight:600}

/* tone ramp - the panel's actual four levels */
.ramp{display:flex;height:10px;margin-top:20px;border:1px solid var(--rule)}
.ramp span{flex:1}

/* roll header */
.roll{position:sticky;top:0;z-index:2;background:var(--board);
  display:flex;align-items:baseline;gap:14px;
  padding:30px 0 10px;margin:34px 0 18px;border-bottom:2px solid var(--ink)}
.roll b{font-size:24px;font-weight:700;letter-spacing:-.01em}
.roll .letter{font-family:"DM Mono",ui-monospace,monospace;font-size:13px;
  color:var(--proof);background:var(--ink);padding:3px 8px;letter-spacing:.1em}
.roll .count{margin-left:auto;font-family:"DM Mono",ui-monospace,monospace;
  font-size:12px;color:var(--muted);letter-spacing:.1em}

/* proofs */
.sheet{display:grid;gap:26px;grid-template-columns:repeat(auto-fill,minmax(360px,1fr))}
figure{margin:0;display:flex;flex-direction:column}
.frame{display:flex;align-items:center;gap:9px;padding:0 0 7px;
  font-family:"DM Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted)}
.frame .no{color:var(--mark);font-weight:500}
.frame .tick{flex:1;height:1px;background:var(--rule)}
.rot{border:1px solid var(--mark);color:var(--mark);padding:1px 6px;
  letter-spacing:.12em;white-space:nowrap}
.proof{background:var(--proof);box-shadow:0 1px 3px var(--shadow);
  border:1px solid var(--rule-soft);overflow:hidden}
.proof svg{display:block;width:100%;height:auto}
figcaption{padding:11px 2px 0}
figcaption h3{margin:0;font-size:17px;font-weight:600;line-height:1.3;
  letter-spacing:-.01em;text-wrap:balance}
figcaption .rss{font-family:Newsreader,Georgia,serif;font-size:15px;
  line-height:1.45;color:var(--muted);margin:6px 0 0}
figcaption .recipe{font-family:"DM Mono",ui-monospace,monospace;font-size:11px;
  line-height:1.5;color:var(--muted);margin:9px 0 0;padding-top:8px;
  border-top:1px dashed var(--rule);word-break:break-word}
figcaption .recipe::before{content:"↳ ";color:var(--mark)}

/* filter - sticky under the masthead, same mono/letterspaced register as
   the frame numbers so it reads as part of the contact-sheet apparatus */
.filter{position:sticky;top:0;z-index:3;display:flex;align-items:center;
  gap:10px;flex-wrap:wrap;background:var(--board);
  padding:14px 0 12px;border-bottom:1px solid var(--rule)}
.filter-label,.filter-note{font-family:"DM Mono",ui-monospace,monospace;
  font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.filter button{font:inherit;font-family:"DM Mono",ui-monospace,monospace;
  font-size:12px;letter-spacing:.1em;text-transform:uppercase;
  display:inline-flex;align-items:center;gap:7px;
  padding:6px 12px;cursor:pointer;color:var(--ink);
  background:transparent;border:1px solid var(--rule)}
.filter button b{font-weight:500;color:var(--muted);font-variant-numeric:tabular-nums}
.filter button:hover{border-color:var(--ink)}
.filter button[aria-pressed="true"]{background:var(--ink);color:var(--proof);
  border-color:var(--ink)}
.filter button[aria-pressed="true"] b{color:var(--proof);opacity:.65}
.filter button:focus-visible{outline:2px solid var(--mark);outline-offset:2px}
/* the roll headers stick too; keep them below the filter bar */
.roll{top:49px}

.foot{margin-top:56px;padding-top:20px;border-top:1px solid var(--rule);
  font-family:"DM Mono",ui-monospace,monospace;font-size:12px;line-height:1.7;
  color:var(--muted)}
.foot code{background:var(--board-2);padding:1px 5px}
@media (max-width:520px){.wrap{padding:24px 16px 64px}
  .sheet{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


# Progressive enhancement: with JavaScript off the page is exactly what it
# always was, every proof visible. The proof sheet is a browsing surface for a
# person on a real screen - the no-JavaScript rule applies to the cards and to
# epaper.html, which the panel loads, not to this page.
_SHEET_JS = """
(function () {
  var buttons = document.querySelectorAll('.filter button');
  var note = document.querySelector('.filter-note');
  var KEY = 'stickyProofFilter';

  function apply(mode, persist) {
    document.querySelectorAll('figure').forEach(function (fig) {
      fig.hidden = mode === 'rot' && fig.dataset.rot !== '1';
    });
    document.querySelectorAll('.roll-group').forEach(function (group) {
      var shown = mode === 'rot' ? +group.dataset.rotCount
                                 : group.querySelectorAll('figure').length;
      // A family with nothing in the rotation drops out entirely, header and
      // all, rather than leaving a heading over an empty grid.
      group.hidden = shown === 0;
      var count = group.querySelector('.count');
      count.textContent = shown + (shown === 1 ? ' card' : ' cards');
    });
    buttons.forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.mode === mode));
    });
    if (note) note.hidden = mode !== 'rot';
    if (persist !== false) {
      try { localStorage.setItem(KEY, mode); } catch (e) { /* private window */ }
    }
  }

  buttons.forEach(function (b) {
    b.addEventListener('click', function () { apply(b.dataset.mode); });
  });

  var start = 'all';
  try { start = localStorage.getItem(KEY) || 'all'; } catch (e) { /* ignore */ }
  // A deep link to a specific proof wins over a remembered filter that would
  // hide it - landing on #haiku and seeing nothing would just look broken.
  var target = location.hash && document.querySelector(location.hash);
  var forced = target && target.dataset && target.dataset.rot !== '1';
  if (forced) start = 'all';
  // A deep link overrides the filter for this visit only. Persisting it would
  // let one link to one proof quietly throw away the preference.
  apply(start, !forced);
  if (target) target.scrollIntoView();
})();
"""


def render_contact_sheet(cards, asof, rotation=(), families=None):
    """Every card as a proof, grouped into rolls by catalogue family."""
    families = families or {}
    rot = set(rotation)

    rolls = OrderedDict()
    for c in cards:
        rolls.setdefault(c.family or "?", []).append(c)

    n_rot = sum(1 for c in cards if c.id in rot)
    body = []
    # Each roll is a <section> wrapping its header and its grid, so the filter
    # can hide a whole family in one go rather than reasoning about siblings.
    for letter, group in rolls.items():
        in_roll = sum(1 for c in group if c.id in rot)
        body.append(
            f'<section class="roll-group" data-rot-count="{in_roll}">'
            f'<div class="roll"><span class="letter">{esc(letter)}</span>'
            f"<b>{esc(families.get(letter, 'Other'))}</b>"
            f'<span class="count" data-all="{len(group)}">'
            f'{len(group)} card{"s" if len(group) != 1 else ""}</span>'
            "</div><div class=\"sheet\">"
        )
        for c in group:
            is_rot = c.id in rot
            badge = ('<span class="rot">in rotation</span>' if is_rot else "")
            body.append(
                f'<figure id="{esc(c.id)}"{' data-rot="1"' if is_rot else ""}>'
                f'<div class="frame"><span class="no">{c.idea:02d}</span>'
                f"<span>{esc(c.id)}</span><span class=\"tick\"></span>{badge}</div>"
                f'<div class="proof">{c.svg()}</div>'
                f"<figcaption><h3>{esc(c.title)}</h3>"
                f'<p class="rss">{esc(c.summary)}</p>'
                f'<p class="recipe">{esc(c.recipe or "")}</p></figcaption>'
                "</figure>"
            )
        body.append("</div></section>")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sticky Proof Sheet</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=DM+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">
<style>{_SHEET_CSS}</style></head>
<body><div class="wrap">
<header class="head">
  <p class="eyebrow">reTerminal Sticky · 800 × 480 · 4-level grayscale</p>
  <h1>Every card, at panel size</h1>
  <p class="standfirst">The whole Strava e-paper catalogue drawn under the real
  constraints: nothing smaller than 26&nbsp;px, no stroke under 3&nbsp;px, four
  tones and three dither patterns, no colour and no JavaScript. Each proof below
  is the actual file the panel would render — not a mockup of one.</p>
  <dl class="spec">
    <div><dt>Cards</dt><dd>{len(cards)}</dd></div>
    <div><dt>In rotation</dt><dd>{n_rot}</dd></div>
    <div><dt>Panel</dt><dd>3.97″ · 235 PPI</dd></div>
    <div><dt>Physical size</dt><dd>3.4″ × 2.0″</dd></div>
    <div><dt>Data as of</dt><dd>{F.day(asof)}</dd></div>
  </dl>
  <div class="ramp"><span style="background:var(--tone-3)"></span>
    <span style="background:var(--tone-2)"></span>
    <span style="background:var(--tone-1)"></span>
    <span style="background:var(--tone-0)"></span></div>
</header>
<div class="filter" role="group" aria-label="Filter proofs">
  <span class="filter-label">Show</span>
  <button type="button" data-mode="all" aria-pressed="true">Every card
    <b>{len(cards)}</b></button>
  <button type="button" data-mode="rot" aria-pressed="false">In rotation
    <b>{n_rot}</b></button>
  <span class="filter-note" hidden>the {n_rot} cards the device cycles daily</span>
</div>
{''.join(body)}
<p class="foot">
Built by <code>strava-data/build_feed.py</code> from the live Strava export.
Proofs render white because the panel does — on a dark screen they sit as a
lightbox, not inverted.<br>
<b>In rotation</b> marks the cards the device actually cycles through daily;
the rest stay in the catalogue. Numbers are catalogue frames from
<code>Project&nbsp;Docs/Plans/strava-data/epaper-feed-brainstorm.md</code>.
</p>
</div>
<script>{_SHEET_JS}</script>
</body></html>
"""
