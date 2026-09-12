"""Render three Low Relief variants from the real module and write a comparison page.

Pinned from the September 2026 Woven Weeks exploration. It imports the
`art_relief` module, which was reverted from the tree; to run it again, first
restore that module beside the others:

    git show cb52a18:running-log/dashboard/art_relief.py > running-log/dashboard/art_relief.py
    uv run python "Project Docs/Plans/running-log/woven update/gen_shine_compare.py"

Writes `shine-compare.html` next to this script. Paths are relative to the
repo root, which is found from this file's own location.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "running-log"))
import dashboard.art_relief as AR  # noqa: E402

rows = list(csv.DictReader(open(
    os.path.join(ROOT, "running-log", "running_log.csv"), encoding="utf-8-sig")))


def svg_only(fragment, prefix):
    """The <svg>...</svg> of a fragment, with every lr- id/class renamed."""
    m = re.search(r"<svg .*?</svg>", fragment, re.S)
    return m.group(0).replace("lr-", prefix + "-")


original_gradient = AR._gradient
original_shadow = AR._SHADOW

# 1. Current build.
v1 = svg_only(AR.art_relief_html(rows), "v1")


# 2. No shine: drop the white crown stop; the body starts at the type color.
def gradient_no_shine(t):
    paint = AR._type_paint(t)
    return (
        '<radialGradient id="lr-g-%s" cx="%.2f" cy="%.2f" r="%.2f">'
        '<stop offset="0" style="stop-color:%s" stop-opacity="0.93"/>'
        '<stop offset="0.78" style="stop-color:%s" stop-opacity="0.78"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0"/>'
        '</radialGradient>' % (t, AR.CROWN_CX, AR.CROWN_CY, AR.CROWN_R, paint, paint)
    )


AR._gradient = gradient_no_shine
v2 = svg_only(AR.art_relief_html(rows), "v2")


# 3. Flat, tapered: a uniform translucent fill, no rim, no shadow.
def gradient_flat(t):
    paint = AR._type_paint(t)
    return (
        '<radialGradient id="lr-g-%s" cx="0.5" cy="0.5" r="0.5">'
        '<stop offset="0" style="stop-color:%s" stop-opacity="0.86"/>'
        '<stop offset="1" style="stop-color:%s" stop-opacity="0.86"/>'
        '</radialGradient>' % (t, paint, paint)
    )


AR._gradient = gradient_flat
AR._SHADOW = ""
v3 = svg_only(AR.art_relief_html(rows), "v3").replace(' filter="url(#v3-sh)"', "")

AR._gradient = original_gradient
AR._SHADOW = original_shadow

LIGHT = {"easy": "#0d9488", "tempo": "#c2710c", "long": "#6d28d9",
         "race": "#c81e1e", "workout": "#1d4ed8"}
DARK = {"easy": AR.EASY_COLOR, "tempo": AR.TEMPO_COLOR, "long": AR.LONG_COLOR,
        "race": AR.RACE_COLOR, "workout": AR.WORKOUT_COLOR}

def vars_block(colors, ground, ink):
    toks = "".join("--%s-ground:%s;--%s-ink:%s;" % (p, ground, p, ink)
                   for p in ("v1", "v2", "v3", "v1l", "v2l", "v3l"))
    return "".join("--%s:%s;" % (k, v) for k, v in colors.items()) + toks

page = """<title>Low Relief Shine Compare</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0f17;--surface:#121826;--ink:#e6ebf4;--ink-soft:#8b96ab;--border:#22293a;--accent:#a78bfa;--accent-tint:#241c3a;}
*{box-sizing:border-box;}
body{background:var(--bg);color:var(--ink);font-family:'Geist',ui-sans-serif,system-ui,sans-serif;padding:36px 20px 64px;}
.wrap{max-width:1100px;margin:0 auto;}
.eyebrow{font-family:'Geist Mono',ui-monospace,monospace;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);margin:0 0 10px;}
h1{font-size:clamp(26px,3.6vw,36px);font-weight:700;letter-spacing:-.01em;margin:0 0 12px;text-wrap:balance;}
.intro{font-size:15px;line-height:1.6;color:var(--ink-soft);max-width:70ch;margin:0 0 30px;}
.intro strong{color:var(--ink);font-weight:600;}
.sample{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:22px;margin-bottom:22px;}
.sample-head{display:flex;align-items:baseline;gap:14px;margin-bottom:6px;}
.sample-num{font-family:'Geist Mono',ui-monospace,monospace;font-size:13px;font-weight:600;color:var(--accent);background:var(--accent-tint);border-radius:6px;padding:3px 8px;}
.sample-title{font-size:18px;font-weight:600;margin:0;}
.sample-sub{font-size:13.5px;color:var(--ink-soft);line-height:1.55;margin:0 0 16px;max-width:80ch;}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
@media (max-width:820px){.pair{grid-template-columns:1fr;}}
.ground{border-radius:10px;padding:10px;}
.ground.dark{background:#0f172a;%s}
.ground.light{background:#ffffff;%s}
.ground svg{display:block;width:100%%;height:auto;}
.view-label{font-family:'Geist Mono',ui-monospace,monospace;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-soft);margin:0 0 6px;}
.note{margin-top:28px;padding:16px 20px;background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:0 10px 10px 0;font-size:14px;line-height:1.65;color:var(--ink-soft);}
.note strong{color:var(--ink);font-weight:600;}
</style>
<div class="wrap">
  <p class="eyebrow">running-log/dashboard/art_relief.py &middot; rendered from the real module, all four years</p>
  <h1>Low Relief: how much shine?</h1>
  <p class="intro">Three renders of the actual piece, straight from <code>art_relief.py</code> with
    only the gradient changed. Same ellipses, same tapered ends, same draw order, same labels.
    Each shown on the dark and the light ground, using the page's own type colors for each theme.</p>
  %s
  <p class="note"><strong>What differs, precisely:</strong> 01 is the committed build. 02 drops
    only the white stop at the gradient's center, so each mound is its own color from crown to rim,
    still darkening at the edge and still casting the shared shadow. 03 also drops the rim darkening
    and the shadow, leaving a uniform translucent fill: the taper is entirely the ellipse's own
    silhouette. Translucency (86%%) is kept in 03 so overlapping runs still deepen.</p>
</div>
"""

def sample(n, title, sub, svg):
    # The light copy gets its own id namespace: a paint server reference
    # resolves document-wide, so a shared id would hand the light render the
    # dark copy's gradient (and the dark theme's colors).
    light = svg.replace("v%d-" % n, "v%dl-" % n)
    return (
        '<div class="sample"><div class="sample-head"><span class="sample-num">0%d</span>'
        '<h2 class="sample-title">%s</h2></div><p class="sample-sub">%s</p>'
        '<div class="pair"><div><p class="view-label">Dark theme</p><div class="ground dark">%s</div></div>'
        '<div><p class="view-label">Light theme</p><div class="ground light">%s</div></div></div></div>'
        % (n, title, sub, svg, light)
    )

samples = (
    sample(1, "Current build", "White crown at the gradient center, rim darkening toward the edge, shared shadow beneath.", v1)
    + sample(2, "No shine", "The white stop is gone. Everything else &mdash; rim shading, shadow, translucency, tapered ends &mdash; is untouched.", v2)
    + sample(3, "Flat, tapered", "No shine, no rim, no shadow. A uniform translucent fill; the taper is the ellipse itself.", v3)
)

html = page % (vars_block(DARK, "#243044", "#64748b"), vars_block(LIGHT, "#dfe4ec", "#64748b"), samples)
out = os.path.join(HERE, "shine-compare.html")
open(out, "w", encoding="utf-8").write(html)
print("wrote", len(html), "bytes;", "v1", len(v1), "v2", len(v2), "v3", len(v3))
