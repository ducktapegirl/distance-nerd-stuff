"""The landing page's CSS.

The `:root` / `:root.light` variable spine, the `html, body` rule with its two
radial gradients, and the glass `.card` treatment are the same design system the
two dashboards use (running-log/dashboard/template.py, strava-data/dashboard/
template.py). Colors come from nerd_common.tokens, never from a literal hex
typed here — the light-theme values below are the one exception, since the
dashboards hardcode them too and nerd_common only carries the dark palette.

This is the third copy of that spine. Folding it into nerd_common is worth doing
the next time one of these needs to change, but the dashboards' copies are
f-strings tangled with their own domain palettes, so unifying them is a separate
change from adding this page.
"""

from nerd_common.theme_ui import THEME_TOGGLE_CSS
from nerd_common.tokens import (
    ACCENT, ACCENT_DIM, ACCENT_GLOW,
    BG_BASE, BG_ELEVATED, BG_GLASS, BG_SURFACE,
    BORDER, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)

CSS = f"""
:root {{
  --bg-base: {BG_BASE};
  --bg-surface: {BG_SURFACE};
  --bg-elevated: {BG_ELEVATED};
  --bg-glass: {BG_GLASS};
  --topnav-bg: rgba(13, 17, 23, 0.7);
  --border: {BORDER};
  --border-subtle: {BORDER_SUBTLE};
  --text-primary: {TEXT_PRIMARY};
  --text-secondary: {TEXT_SECONDARY};
  --text-tertiary: {TEXT_TERTIARY};
  --bg-gradient-1: rgba(88, 166, 255, 0.06);
  --bg-gradient-2: rgba(167, 139, 250, 0.04);
  --accent: {ACCENT};
  --accent-glow: {ACCENT_GLOW};
  --accent-dim: {ACCENT_DIM};
}}

:root.light {{
  --bg-base: #ffffff;
  --bg-surface: #f3f4f6;
  --bg-elevated: #ffffff;
  --bg-glass: rgba(255, 255, 255, 0.75);
  --topnav-bg: rgba(255, 255, 255, 0.8);
  --border: rgba(140, 149, 159, 0.55);
  --border-subtle: rgba(140, 149, 159, 0.3);
  --text-primary: #11161d;
  --text-secondary: #424a53;
  --text-tertiary: #424a53;
  --bg-gradient-1: rgba(9, 105, 218, 0.09);
  --bg-gradient-2: rgba(130, 80, 223, 0.07);
  --accent: #0550ae;
  --accent-glow: rgba(5, 80, 174, 0.18);
  --accent-dim: rgba(5, 80, 174, 0.10);
}}

* {{ box-sizing: border-box; }}

html, body {{
  margin: 0; padding: 0;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: 'Geist', system-ui, -apple-system, sans-serif;
  font-size: 14px;
  min-height: 100vh;
  background-image:
    radial-gradient(ellipse 80% 50% at 20% -10%, var(--bg-gradient-1) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 110%, var(--bg-gradient-2) 0%, transparent 60%);
}}

.shell {{ display: flex; flex-direction: column; min-height: 100vh; }}

/* ─── Topnav ──────────────────────────────────────────────────────────── */

.topnav {{
  position: sticky; top: 0; z-index: 50;
  background: var(--topnav-bg);
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-subtle);
}}
.topnav-row {{
  max-width: 1100px; margin: 0 auto; padding: 0 32px;
  display: flex; align-items: center; justify-content: space-between;
  height: 56px; gap: 16px;
}}
.wordmark-name {{
  font-size: 17px; font-weight: 700; letter-spacing: -0.02em;
  color: var(--text-primary);
}}
{THEME_TOGGLE_CSS}

/* ─── Hero ────────────────────────────────────────────────────────────── */

main {{ flex: 1; max-width: 1100px; margin: 0 auto; padding: 0 32px 64px; width: 100%; }}

.hero {{ padding: 72px 0 40px; max-width: 640px; }}
.hero h1 {{
  margin: 0 0 12px;
  font-size: clamp(30px, 6vw, 46px); font-weight: 700;
  letter-spacing: -0.035em; line-height: 1.05;
}}
.hero p {{
  margin: 0;
  font-size: 15px; line-height: 1.6;
  color: var(--text-secondary);
}}

/* ─── The two tiles ───────────────────────────────────────────────────── */

.tiles {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}}

.tile {{
  display: block;
  text-decoration: none; color: inherit;
  background: var(--bg-glass);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  overflow: hidden;
  min-width: 0;
  animation: fadeUp 240ms cubic-bezier(0.16, 1, 0.3, 1);
  transition: border-color 160ms cubic-bezier(0.16, 1, 0.3, 1),
              transform 160ms cubic-bezier(0.16, 1, 0.3, 1),
              box-shadow 160ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.tile:hover, .tile:focus-visible {{
  border-color: var(--tile-accent, var(--accent));
  transform: translateY(-3px);
  box-shadow: 0 12px 32px -12px var(--tile-accent, var(--accent));
  outline: none;
}}

/* 4:3 rather than square so the whole tile — art, title, stats — lands above
   the fold at 1440x900. The art is authored square and `slice`-cropped to fit,
   so a direction that needs the full square just has to say so here. */
.tile-art-wrap {{
  aspect-ratio: 4 / 3;
  border-bottom: 1px solid var(--border-subtle);
  overflow: hidden;
}}
.tile-art {{ display: block; width: 100%; height: 100%; }}

/* The two blurbs differ in length, so let the shorter tile's blurb absorb the
   slack and both stat rows land on the same baseline. Grid already stretches
   the tiles to equal height; this makes their insides agree. */
.tile {{ display: flex; flex-direction: column; }}
.tile-body {{ padding: 22px 24px 24px; flex: 1; display: flex; flex-direction: column; }}
.tile-blurb {{ flex: 1; }}
.tile-kicker {{
  font-family: 'Geist Mono', monospace;
  font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--tile-accent, var(--accent));
  margin-bottom: 8px;
}}
.tile-title {{
  font-size: 21px; font-weight: 600; letter-spacing: -0.02em;
  margin: 0 0 8px;
}}
.tile-blurb {{
  font-size: 13px; line-height: 1.55;
  color: var(--text-secondary);
  margin: 0 0 16px;
}}
.tile-stats {{
  display: flex; flex-wrap: wrap; gap: 6px 14px;
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  color: var(--text-tertiary);
}}
.tile-stats span + span::before {{
  content: '·'; margin-right: 14px; opacity: 0.5;
}}

@keyframes fadeUp {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}
@media (prefers-reduced-motion: reduce) {{
  .tile {{ animation: none; }}
  .tile:hover, .tile:focus-visible {{ transform: none; }}
}}

/* ─── Footer ──────────────────────────────────────────────────────────── */

.site-footer {{
  border-top: 1px solid var(--border-subtle);
  padding: 24px 32px 32px;
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
}}
.site-footer a {{
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 120ms ease;
}}
.site-footer a:hover {{ border-bottom-color: var(--accent); }}

/* ─── Mobile: one column, running log first (DOM order already is) ────── */

@media (max-width: 720px) {{
  .topnav-row, main, .site-footer {{ padding-left: 20px; padding-right: 20px; }}
  .hero {{ padding: 40px 0 28px; }}
  .tiles {{ grid-template-columns: 1fr; gap: 20px; }}
}}
"""
