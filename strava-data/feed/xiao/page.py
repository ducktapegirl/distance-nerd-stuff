"""Static pages for the XIAO panel: the device page and the review sheet.

``render_page`` is what SenseCraft's Web function fetches - one card, exactly
296x128, no JavaScript, no CDN, no webfonts.

``render_sheet`` is for a person. It carries the audit of the Sticky rotation,
every surviving card at panel size, and the mockup pairs the owner is asked
to decide between. Two things it does that the Sticky's sheet never needed:
a 1x / 2x zoom (1x is close to physical size on a ~100 DPI monitor; 2x is for
reading the pixels), and a "panel preview" toggle that runs every proof
through an SVG discrete-transfer filter. That filter thresholds each channel
at one half, which collapses the browser's anti-aliasing into exactly the
four colors the panel can show - pairwise mixes of black, white, red and
yellow all quantize back into the palette - so what the toggle shows is what
the device will show, jaggies included.
"""

from .. import fmt as F
from ..svg import esc
from .config import BLACK, H, PALETTE, PPI, RED, W, WHITE, YELLOW

_CSS = f"""html,body{{margin:0;padding:0;background:{WHITE};
  width:{W}px;height:{H}px;overflow:hidden}}
svg{{display:block}}"""


def render_page(card):
    """The device page: exactly one card, exactly 296x128."""
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
        f'<meta name="viewport" content="width={W},height={H}">\n'
        f"<title>{esc(card.title)}</title>\n<style>{_CSS}</style></head>\n"
        f"<body>{card.svg()}</body></html>\n"
    )


# ── the audit, as data ──────────────────────────────────────────────────────
# One row per Sticky rotation card, in rotation order. The sheet renders it;
# the prose lives in Project Docs/Plans/strava-data/epaper-xiao.md.

AUDIT = [
    ("strip", 9, "adapt", "2 rows of 15 cells at 13 px (3 mm) still read. Headline above; rest days take the wash."),
    ("sparkline", 17, "adapt", "The archetypal small graphic. Headline number, 13-month line, end dot as the accent."),
    ("everest", 18, "adapt", "Up to six summits across the bottom; the partial one fills with the wash."),
    ("journey-run", 19, "adapt · mockup", "Numbers over the milepost strip. The CONUS map is a mockup below."),
    ("journey-bike", 19, "adapt · mockup", "Same treatment."),
    ("split", 20, "adapt", "Bar rows trimmed five to four; the track is a wash band, no outline."),
    ("hours", 21, "adapt", "Numeral left, one tally mark per 24 hours along the bottom; the partial day is the accent."),
    ("mosaic", 37, "drop · mockup", "32 routes would be 25 px squiggles; the idea is density. A 2×6 is mocked up below."),
    ("latest", 3, "adapt", "Route left, six of the eight stats in a 3×2 grid; the name moves into the masthead."),
    ("segment-month", 57, "adapt", "Name, best / latest / trend, spark of the last 24 efforts. The grade caption goes."),
    ("hall-of-fame", 58, "adapt · mockup", "Three of the weekly five, one line each, distance instead of date. A one-name version is mocked up."),
    ("uv-week", 59, "adapt", "The strongest color card: a yellow sun, red past half a scorcher; the week's cells on the ramp."),
    ("wildlife", 52, "adapt", "Ten bar rows become a four-up scoreboard of silhouettes; the latest sighting is the accent."),
    ("week-2004", 60, "adapt", "The then / now band keeps both headline numbers and the average paces; the day lists go."),
    ("anniversary", 61, "adapt", "When-line (red on the day), distance · time, race name, date. The comments go."),
    ("haiku", 62, "adapt", "Three lines at 18 px shrinking to 14, full width, no glyph. Never ellipsized - checked."),
]

_SHEET_CSS = """
:root{
  --board:#c9cbcf; --board-2:#d4d6da; --proof:#ffffff;
  --ink:#101114; --muted:#5c6068; --rule:#a8abb1; --rule-soft:#bcbfc5;
  --mark:#8a1c1c; --shadow:rgba(16,17,20,.28);
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
[hidden]{display:none!important}
body{margin:0;background:var(--board);color:var(--ink);
  font-family:Archivo,"Helvetica Neue",Arial,sans-serif;
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:36px 28px 96px}
.head{border-bottom:3px solid var(--ink);padding-bottom:22px;margin-bottom:8px}
.eyebrow{font-family:"DM Mono",ui-monospace,Menlo,monospace;font-size:12px;
  letter-spacing:.22em;text-transform:uppercase;color:var(--mark);margin:0 0 12px}
h1{font-size:clamp(34px,6vw,60px);line-height:.98;margin:0;font-weight:700;
  letter-spacing:-.025em;text-wrap:balance}
h2{font-size:24px;margin:0;font-weight:700;letter-spacing:-.01em}
.standfirst{font-family:Newsreader,Georgia,serif;font-size:19px;line-height:1.5;
  max-width:62ch;color:var(--muted);margin:16px 0 0}
.spec{display:flex;flex-wrap:wrap;gap:0;margin:22px 0 0;border-top:1px solid var(--rule)}
.spec div{flex:1 1 120px;padding:12px 16px 4px 0;border-right:1px solid var(--rule-soft)}
.spec div:last-child{border-right:0}
.spec dt{font-family:"DM Mono",ui-monospace,monospace;font-size:11px;
  letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin:0 0 4px}
.spec dd{margin:0;font-size:17px;font-weight:600}
.ramp{display:flex;height:14px;margin-top:20px;border:1px solid var(--rule)}
.ramp span{flex:1}

.roll{position:sticky;top:49px;z-index:2;background:var(--board);
  display:flex;align-items:baseline;gap:14px;
  padding:30px 0 10px;margin:34px 0 18px;border-bottom:2px solid var(--ink)}
.roll .letter{font-family:"DM Mono",ui-monospace,monospace;font-size:13px;
  color:var(--proof);background:var(--ink);padding:3px 8px;letter-spacing:.1em}
.roll .count{margin-left:auto;font-family:"DM Mono",ui-monospace,monospace;
  font-size:12px;color:var(--muted);letter-spacing:.1em}
.lede{font-family:Newsreader,Georgia,serif;font-size:17px;line-height:1.5;
  max-width:70ch;color:var(--muted);margin:0 0 18px}

/* audit table */
table{border-collapse:collapse;width:100%;font-size:14px;margin:0 0 8px}
th,td{text-align:left;padding:8px 10px 8px 0;border-bottom:1px solid var(--rule-soft);
  vertical-align:top}
th{font-family:"DM Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted);font-weight:500}
td.id{font-family:"DM Mono",ui-monospace,monospace;font-size:12px;white-space:nowrap}
td.no{font-family:"DM Mono",ui-monospace,monospace;font-size:12px;color:var(--mark)}
.v{font-family:"DM Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;white-space:nowrap;padding:2px 7px;border:1px solid var(--rule)}
.v-drop{border-color:var(--mark);color:var(--mark)}

/* proofs */
.sheet{display:grid;gap:26px 30px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}
.sheet.pairs{grid-template-columns:repeat(auto-fill,minmax(640px,1fr))}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:16px;
  border:1px solid var(--rule);background:var(--board-2)}
figure{margin:0;display:flex;flex-direction:column;align-items:flex-start}
.frame{display:flex;align-items:center;gap:9px;padding:0 0 7px;width:100%;
  font-family:"DM Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted)}
.frame .no{color:var(--mark);font-weight:500}
.frame .tick{flex:1;height:1px;background:var(--rule)}
.proof{background:var(--proof);box-shadow:0 1px 3px var(--shadow);
  border:1px solid var(--rule-soft);overflow:hidden;width:296px;height:128px}
.proof.empty{display:flex;align-items:center;justify-content:center;
  font-family:"DM Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:#999;background:repeating-linear-gradient(
  45deg,#f4f4f4 0 8px,#fff 8px 16px)}
.proof svg{display:block;width:296px;height:128px}
body.zoom2 .proof{width:592px;height:256px}
body.zoom2 .proof svg{width:592px;height:256px}
body.zoom2 .sheet{grid-template-columns:repeat(auto-fill,minmax(620px,1fr))}
body.zoom2 .sheet.pairs{grid-template-columns:1fr}
body.quant .proof svg{filter:url(#quant)}
figcaption{padding:11px 2px 0;max-width:296px}
body.zoom2 figcaption{max-width:592px}
figcaption h3{margin:0;font-size:15px;font-weight:600;line-height:1.3;letter-spacing:-.01em}
figcaption .rss{font-family:Newsreader,Georgia,serif;font-size:14px;
  line-height:1.45;color:var(--muted);margin:6px 0 0}
figcaption .recipe{font-family:"DM Mono",ui-monospace,monospace;font-size:11px;
  line-height:1.5;color:var(--muted);margin:9px 0 0;padding-top:8px;
  border-top:1px dashed var(--rule);word-break:break-word}
figcaption .recipe::before{content:"↳ ";color:var(--mark)}
figcaption .note{font-family:Newsreader,Georgia,serif;font-size:14px;line-height:1.45;
  color:var(--ink);margin:6px 0 0}

/* controls */
.filter{position:sticky;top:0;z-index:3;display:flex;align-items:center;
  gap:10px;flex-wrap:wrap;background:var(--board);
  padding:14px 0 12px;border-bottom:1px solid var(--rule)}
.filter-label{font-family:"DM Mono",ui-monospace,monospace;
  font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.filter button{font:inherit;font-family:"DM Mono",ui-monospace,monospace;
  font-size:12px;letter-spacing:.1em;text-transform:uppercase;
  padding:6px 12px;cursor:pointer;color:var(--ink);
  background:transparent;border:1px solid var(--rule)}
.filter button:hover{border-color:var(--ink)}
.filter button[aria-pressed="true"]{background:var(--ink);color:var(--board);border-color:var(--ink)}
.filter button:focus-visible{outline:2px solid var(--mark);outline-offset:2px}
.filter .gap{width:18px}

.foot{margin-top:56px;padding-top:20px;border-top:1px solid var(--rule);
  font-family:"DM Mono",ui-monospace,monospace;font-size:12px;line-height:1.7;
  color:var(--muted)}
.foot code{background:var(--board-2);padding:1px 5px}
@media (max-width:700px){.wrap{padding:24px 16px 64px}
  .sheet,.sheet.pairs{grid-template-columns:1fr}.pair{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

_SHEET_JS = """
(function () {
  var KEY = 'xiaoProofView';
  var state = {zoom: '1', quant: '0'};
  try { var s = JSON.parse(localStorage.getItem(KEY) || '{}');
        if (s.zoom) state.zoom = s.zoom; if (s.quant) state.quant = s.quant; } catch (e) {}
  function apply() {
    document.body.classList.toggle('zoom2', state.zoom === '2');
    document.body.classList.toggle('quant', state.quant === '1');
    document.querySelectorAll('.filter button').forEach(function (b) {
      var k = b.dataset.key, v = b.dataset.val;
      b.setAttribute('aria-pressed', String(state[k] === v));
    });
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }
  document.querySelectorAll('.filter button').forEach(function (b) {
    b.addEventListener('click', function () { state[b.dataset.key] = b.dataset.val; apply(); });
  });
  apply();
})();
"""

# Thresholds every channel at one half. Black, white, red and yellow are all
# corners of the RGB cube, and any two of them mix along an edge, so every
# anti-aliased pixel snaps back to one of the four.
_QUANT_FILTER = """<svg width="0" height="0" style="position:absolute" aria-hidden="true">
<filter id="quant" color-interpolation-filters="sRGB">
  <feComponentTransfer>
    <feFuncR type="discrete" tableValues="0 1"/>
    <feFuncG type="discrete" tableValues="0 1"/>
    <feFuncB type="discrete" tableValues="0 1"/>
  </feComponentTransfer>
</filter></svg>"""


def _figure(card, label=None, note=None, badge=""):
    if card is None:
        return (f'<figure><div class="frame"><span>{esc(label or "")}</span>'
                f'<span class="tick"></span></div>'
                f'<div class="proof empty">not built</div>'
                f'<figcaption><p class="note">{esc(note or "")}</p></figcaption></figure>')
    head = (f'<div class="frame"><span class="no">{card.idea:02d}</span>'
            f"<span>{esc(label or card.id)}</span><span class=\"tick\"></span>{badge}</div>")
    cap = f"<figcaption><h3>{esc(card.title)}</h3>"
    if note:
        cap += f'<p class="note">{esc(note)}</p>'
    else:
        cap += (f'<p class="rss">{esc(card.summary)}</p>'
                f'<p class="recipe">{esc(card.recipe or "")}</p>')
    cap += "</figcaption>"
    return f'<figure id="{esc(label or card.id)}">{head}<div class="proof">{card.svg()}</div>{cap}</figure>'


def render_sheet(cards, mockups, asof, rotation, today_card):
    """Audit table, the rotation at panel size, then the mockup pairs.

    ``cards`` can be fewer than ``rotation``: a card with no data this fetch
    (no GPS stream on the newest activity, no UV this week) drops out here
    exactly as it does on the Sticky, and the spec row says so."""
    rot = set(rotation)
    verdict_cls = {"adapt": "", "adapt · mockup": "", "drop · mockup": " v-drop"}
    audit_rows = "".join(
        f'<tr><td class="no">{idea:02d}</td><td class="id">{esc(cid)}</td>'
        f'<td><span class="v{verdict_cls.get(v, "")}">{esc(v)}</span></td>'
        f"<td>{esc(why)}</td></tr>"
        for cid, idea, v, why in AUDIT)

    proofs = "".join(_figure(c, badge='<span class="v">in rotation</span>' if c.id in rot else "")
                     for c in cards)

    mock_sections = []
    for group, pairs in mockups:
        body = "".join(
            '<div class="pair">' + _figure(a[2], a[0], a[1]) + _figure(b[2], b[0], b[1]) + "</div>"
            for a, b in pairs)
        mock_sections.append(
            f'<section><div class="roll"><span class="letter">?</span><h2>{esc(group)}</h2>'
            f'<span class="count">{len(pairs)} pairs</span></div>'
            f'<div class="sheet pairs">{body}</div></section>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>XIAO Proof Sheet</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=DM+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">
<style>{_SHEET_CSS}</style></head>
<body>{_QUANT_FILTER}<div class="wrap">
<header class="head">
  <p class="eyebrow">XIAO ePaper · 2.9″ quadruple color · 296 × 128</p>
  <h1>The Sticky rotation, on a strip a tenth the size</h1>
  <p class="standfirst">The same rotation as the reTerminal Sticky, redrawn for Seeed's 2.9″
  four-color panel: 296 × 128 at 112 PPI, black / white / red / yellow, no gray, no anti-aliasing,
  a 25-second refresh. Floors are the Sticky's translated through the pixel density and rounded
  up for a panel that cannot soften an edge: nothing under 14&nbsp;px, no stroke under 2&nbsp;px,
  and every fill one of the four colors — the build raises on anything else. Each proof is the
  file the panel would fetch, shown at 1× (close to physical size on an ordinary monitor).</p>
  <dl class="spec">
    <div><dt>Rotation</dt><dd>{len(rotation)} of the Sticky's {len(AUDIT)}</dd></div>
    <div><dt>Built this fetch</dt><dd>{len(cards)}</dd></div>
    <div><dt>Panel</dt><dd>2.9″ · {PPI} PPI</dd></div>
    <div><dt>Physical size</dt><dd>66.9 × 29.1 mm</dd></div>
    <div><dt>Colors</dt><dd>4, no gray</dd></div>
    <div><dt>This hour</dt><dd>{esc(today_card.id)}</dd></div>
    <div><dt>Data as of</dt><dd>{F.day(asof)}</dd></div>
  </dl>
  <div class="ramp"><span style="background:{BLACK}"></span>
    <span style="background:{RED}"></span>
    <span style="background:{YELLOW}"></span>
    <span style="background:{WHITE}"></span></div>
</header>
<div class="filter" role="group" aria-label="View">
  <span class="filter-label">Zoom</span>
  <button type="button" data-key="zoom" data-val="1" aria-pressed="true">1×</button>
  <button type="button" data-key="zoom" data-val="2" aria-pressed="false">2×</button>
  <span class="gap"></span>
  <span class="filter-label">Render</span>
  <button type="button" data-key="quant" data-val="0" aria-pressed="true">Browser</button>
  <button type="button" data-key="quant" data-val="1" aria-pressed="false">As the panel sees it</button>
</div>

<section><div class="roll"><span class="letter">1</span><h2>Audit of the Sticky rotation</h2>
<span class="count">{len(AUDIT)} cards</span></div>
<p class="lede">The test is whether the card's <em>idea</em> survives at ≥ 14 px text, ≥ 2 px
strokes and four colors in a 2.3 : 1 strip. "Adapt" keeps the fact and the graphic with less of
it; "drop" means the card's whole point is density this panel does not have.</p>
<table><thead><tr><th>#</th><th>Card</th><th>Verdict</th><th>What changes</th></tr></thead>
<tbody>{audit_rows}</tbody></table></section>

<section><div class="roll"><span class="letter">2</span><h2>The rotation, at panel size</h2>
<span class="count">{len(cards)} cards</span></div>
<p class="lede">Color model A, the one that ships: black is ink, <b>red is the one thing to look
at</b> — now, here, today, an alert — and <b>yellow is the light tone</b>: a wash for reference,
the past, rest. Categories are still carried by shape; quantity by the four-step ramp
white → yellow → red → black where a card needs one.</p>
<div class="sheet">{proofs}</div></section>

{''.join(mock_sections)}

<p class="foot">
Built by <code>strava-data/build_feed.py</code> from the same data as the Sticky feed.
Point SenseCraft's Web function at <code>epaper_xiao.html</code> for the rotation, or at
<code>epaper_xiao/&lt;id&gt;.html</code> to pin one card. The rotation advances hourly with the
site rebuild, exactly as the Sticky's does.<br>
Palette: {' · '.join(PALETTE)}. "As the panel sees it" thresholds every channel at one half —
the same collapse the device's quantizer makes, give or take its dithering, which Seeed does not
document.
</p>
</div>
<script>{_SHEET_JS}</script>
</body></html>
"""
