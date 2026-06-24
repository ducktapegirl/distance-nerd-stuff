"""CSS, JS, and theme-toggle SVG string constants for the dashboard HTML shell."""

import json

from .config import (
    ACCENT, ACCENT_DIM, ACCENT_GLOW, BG_BASE, BG_ELEVATED, BG_GLASS, BG_SURFACE,
    BORDER, BORDER_SUBTLE, ELEVATION_COLOR, FASTER, GRID, SLOWER, TEXT_PRIMARY,
    TEXT_SECONDARY, TEXT_TERTIARY,
)

# ─── CSS ──────────────────────────────────────────────────────────────────────

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
  --grid: {GRID};
  --ann-pill-bg: rgba(13, 17, 23, 0.65);
  --bg-gradient-1: rgba(88, 166, 255, 0.06);
  --bg-gradient-2: rgba(245, 158, 11, 0.04);
  --accent: {ACCENT};
  --accent-glow: {ACCENT_GLOW};
  --accent-dim: {ACCENT_DIM};
  --running: #2dd4bf;
  --mtb: #f59e0b;
  --other: #8b949e;
  --elevation: {ELEVATION_COLOR};
  --faster: {FASTER};
  --slower: {SLOWER};
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
  --grid: rgba(140, 149, 159, 0.35);
  --ann-pill-bg: rgba(255, 255, 255, 0.75);
  --bg-gradient-1: rgba(9, 105, 218, 0.09);
  --bg-gradient-2: rgba(194, 113, 12, 0.07);
  --accent: #0550ae;
  --accent-glow: rgba(5, 80, 174, 0.18);
  --accent-dim: rgba(5, 80, 174, 0.10);
  --running: #0d9488;
  --mtb: #c2710c;
  --other: #475569;
  --elevation: #6d28d9;
  --faster: #0d9488;
  --slower: #c81e1e;
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

/* Top nav */
.topnav {{
  position: sticky; top: 0; z-index: 50;
  background: var(--topnav-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-subtle);
}}
.topnav-row {{
  max-width: 1100px; margin: 0 auto;
  padding: 0 32px;
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px;
}}
.topnav-row.row1 {{ height: 48px; }}
.topnav-row.row2 {{ padding-top: 10px; padding-bottom: 11px; flex-wrap: wrap; }}

.wordmark {{ display: flex; align-items: baseline; gap: 10px; }}
.wordmark-name {{
  font-size: clamp(16px, 4.5vw, 22px); font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}}
.wordmark-meta {{ font-family: 'Geist Mono', monospace; font-size: 13px; color: var(--text-tertiary); }}

.topnav-actions {{ display: inline-flex; align-items: center; gap: 10px; }}

/* Back link to College Running Log */
.back-link {{
  display: inline-flex; align-items: center; gap: 6px;
  font-family: 'Geist', sans-serif;
  font-size: 11px; font-weight: 600;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  padding: 6px 12px; border-radius: 7px;
  cursor: pointer; text-decoration: none;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.back-link:hover {{
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-dim);
}}

/* Theme toggle (3-state: dark / system / light) */
.theme-toggle {{
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px; gap: 0;
}}
.theme-toggle button {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 22px;
  background: transparent; border: none;
  color: var(--text-secondary);
  cursor: pointer; border-radius: 5px;
  padding: 0;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.theme-toggle button:hover {{ color: var(--text-primary); }}
.theme-toggle button.active {{
  background: var(--accent-dim);
  color: var(--accent);
}}
.theme-toggle button svg {{
  width: 13px; height: 13px;
  stroke: currentColor; fill: none;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}}

/* Section nav */
.tabnav {{
  display: flex; gap: 4px;
  flex-wrap: nowrap; overflow-x: auto;
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}}
.tabnav::-webkit-scrollbar {{ display: none; }}
.tab {{
  background: none; border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  padding: 8px 12px;
  cursor: pointer; text-decoration: none;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
  scroll-snap-align: start; flex-shrink: 0;
}}
.tab:hover {{ color: var(--text-primary); }}
.tab.active {{
  color: var(--text-primary);
  border-bottom-color: var(--accent);
}}

/* Page routing */
.view {{ display: none; }}
.view.active {{ display: block; }}

/* Main content */
main {{
  flex: 1;
  max-width: 1100px; width: 100%;
  margin: 0 auto;
  padding: 32px 32px 80px;
}}

.page-header {{ margin-bottom: 24px; }}
.page-header h1 {{
  margin: 0;
  font-size: clamp(20px, 4.5vw, 26px); font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}}
.page-header .date-range {{
  font-family: 'Geist Mono', monospace;
  font-size: 13px;
  color: var(--text-tertiary);
  margin-top: 6px;
}}

.section-anchor {{
  font-size: 12px; font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin: 28px 0 14px;
}}

@keyframes fadeUp {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}

.card {{
  background: var(--bg-glass);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  animation: fadeUp 240ms cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
  min-width: 0;
}}
.card .plotly-graph-div {{ max-width: 100%; }}
.card-title {{
  font-size: 12px; font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 20px;
}}
.card-header {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}}
.card-header .card-title {{ margin: 0; }}
.attribution {{ font-size:13.5px; color:var(--text-secondary); line-height:1.65; margin:0; }}
.plot-caption {{ font-size:13.5px; color:var(--text-secondary); line-height:1.65; margin:12px 0 0; }}

/* Activity calendar (hand-built SVG, ported from the College Running Log) */
.hm-grid {{ display: flex; flex-direction: column; gap: 10px; overflow-x: auto; }}
.hm-year-row {{ display: flex; align-items: center; gap: 8px; }}
.hm-year {{
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--text-tertiary);
  width: 36px; flex-shrink: 0;
}}
.hm-year-row svg {{ flex: 1; min-width: 800px; }}
.hm-cell {{ transition: transform 120ms cubic-bezier(0.16, 1, 0.3, 1); transform-origin: center; transform-box: fill-box; }}
.hm-cell[data-date]:hover {{ transform: scale(1.4); }}
.hm-cell[data-date] {{ cursor: pointer; }}
.hm-month {{ fill: var(--text-tertiary); font-size: 9px; font-family: 'Geist Mono', monospace; }}
.hm-dow   {{ fill: var(--text-tertiary); font-size: 9px; font-family: 'Geist Mono', monospace; }}
/* Longest-day marker: fixed (non-theme) colors so it reads on any cell fill —
   accent blue in Mileage mode, or any sport color in Activity Type mode. */
.hm-star {{ fill: #fff; stroke: #0d1117b0; stroke-width: 0.6; pointer-events: none; }}
.hm-legend {{
  margin-top: 4px; margin-bottom: 14px;
  display: flex; gap: 8px; align-items: center;
  font-size: 10px; color: var(--text-tertiary);
  font-family: 'Geist Mono', monospace;
}}
.hm-legend-meta {{ color: var(--text-secondary); }}
.hm-legend-star-note {{ color: var(--text-secondary); font-weight: 600; margin-left: 4px; }}
.hm-legend-grad {{
  display: inline-block;
  width: 140px; height: 10px; border-radius: 3px;
  background: linear-gradient(
    to right,
    color-mix(in srgb, var(--accent) 10%, transparent),
    var(--accent)
  );
}}
.hm-legend[hidden] {{ display: none; }}
.hm-legend-item {{ display: inline-flex; gap: 6px; align-items: center; }}
.hm-legend-item .swatch {{ width: 12px; height: 12px; border-radius: 2px; display: inline-block; }}

/* Stat cards */
.stat-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}}
.stat-card {{
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 18px 20px;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.stat-num {{
  font-family: 'Geist Mono', monospace;
  font-size: clamp(18px, 4.5vw, 24px); font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  line-height: 1.1;
}}
.stat-label {{
  margin-top: 6px;
  font-size: 11px; font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-secondary);
}}

/* Segment consistency cardlets (Section 1) */
.seg-cons-grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}}
.seg-cardlet {{
  background: var(--bg-glass);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 18px 18px 14px;
  min-width: 0;
  animation: fadeUp 240ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.seg-cardlet .plotly-graph-div {{ max-width: 100%; }}
.seg-cardlet-head {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
.seg-emoji {{ font-size: 17px; line-height: 1; }}
.seg-cardlet-tag {{
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--text-secondary);
}}
.seg-cardlet-name {{
  font-size: 15px; font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.seg-cardlet-meta {{
  font-family: 'Geist Mono', monospace;
  font-size: 11px; color: var(--text-tertiary);
  margin-top: 2px;
}}

/* Fastest-segment stat cards (Section 2) */
.fast-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}}
.fast-card {{
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px 18px;
  min-width: 0;
  animation: fadeUp 240ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.fast-rank {{
  font-family: 'Geist Mono', monospace;
  font-size: 12px; font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}}
.fast-name {{
  font-size: 15px; font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 14px;
  line-height: 1.3;
  min-height: 2.6em;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}}
.fast-stats {{ display: flex; gap: 8px; }}
.fast-stat {{ flex: 1 1 0; text-align: center; }}
.fast-val {{
  font-family: 'Geist Mono', monospace;
  font-size: 17px; font-weight: 600;
  color: var(--text-primary);
  line-height: 1.1;
  white-space: nowrap;
}}
.fast-val .u {{
  font-size: 0.62em; color: var(--text-tertiary);
  margin-left: 2px; letter-spacing: 0;
}}
.fast-lbl {{
  margin-top: 4px;
  font-size: 9.5px; letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--text-secondary);
}}
.fast-foot {{
  margin-top: 12px;
  font-family: 'Geist Mono', monospace;
  font-size: 10.5px; color: var(--text-tertiary);
}}

/* Segment filter pills */
.seg-filter {{
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px; gap: 0;
  margin-bottom: 14px;
}}
.seg-btn {{
  background: transparent; border: none;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif; font-size: 11px;
  padding: 4px 12px; border-radius: 5px;
  cursor: pointer;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.seg-btn:hover {{ color: var(--text-primary); }}
.seg-btn.active {{
  background: var(--accent-dim);
  color: var(--accent);
}}

/* Detail panel */
.detail-backdrop {{
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.45);
  opacity: 0; pointer-events: none;
  transition: opacity 200ms ease;
  z-index: 90;
}}
.detail-backdrop.open {{ opacity: 1; pointer-events: auto; }}
.detail-panel {{
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 420px; max-width: 100vw;
  background: var(--bg-surface);
  border-left: 1px solid var(--border);
  box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
  transform: translateX(100%);
  transition: transform 240ms cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 100;
  display: flex; flex-direction: column;
  overflow: hidden;
}}
.detail-panel.open {{ transform: translateX(0); }}
.detail-header {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}}
.detail-title {{
  font-family: 'Geist', sans-serif;
  font-size: 14px; font-weight: 600;
  color: var(--text-primary);
}}
.detail-close {{
  background: none; border: none;
  color: var(--text-secondary);
  font-size: 22px; line-height: 1;
  cursor: pointer; padding: 4px 12px;
  border-radius: 6px;
  transition: background 150ms, color 150ms;
}}
.detail-close:hover {{ background: var(--bg-elevated); color: var(--text-primary); }}
.detail-body {{ flex: 1; overflow-y: auto; padding: 20px; }}
.d-name {{
  font-size: 15px; font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}}
.d-date {{
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 18px;
}}
.d-stats {{ display: flex; flex-wrap: wrap; gap: 10px; }}
.d-desc {{
  margin-top: 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
  white-space: pre-wrap;
}}
.d-sep {{ height: 1px; background: var(--border-subtle); margin: 20px 0; }}
.d-stat {{
  flex: 1 1 100px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px 14px;
  text-align: center;
}}
.d-stat-val {{
  font-family: 'Geist Mono', monospace;
  font-size: 18px; font-weight: 600;
  color: var(--text-primary);
  line-height: 1.1;
}}
.d-stat-lbl {{
  font-size: 10px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-tertiary);
  margin-top: 4px;
}}
.d-hint {{
  font-size: 13px;
  color: var(--text-tertiary);
  text-align: center;
  margin-top: 12px;
  padding: 18px;
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
}}

/* Rangeslider cursor (Plotly) */
.rangeslider-slidebox,
.rangeslider-handle-min,
.rangeslider-handle-max {{ cursor: grab; }}
.rangeslider-slidebox:active,
.rangeslider-handle-min:active,
.rangeslider-handle-max:active {{ cursor: grabbing; }}

/* ── Responsive / mobile (kept last so overrides win by source order) ── */
@media (max-width: 900px) {{
  .stat-grid {{ grid-template-columns: repeat(3, 1fr); }}
}}
@media (max-width: 640px) {{
  .stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .seg-cons-grid {{ grid-template-columns: 1fr; }}
  .fast-grid {{ grid-template-columns: 1fr; }}
  main {{ padding: 20px 14px 60px; }}
  .theme-toggle button {{ width: 36px; height: 36px; }}
  .tab {{ min-height: 44px; padding: 10px 12px; }}
  .seg-btn {{ min-height: 40px; padding: 6px 14px; }}
  .js-plotly-plot {{ max-width: 100%; }}

  /* #1 Topnav: stack title over date, compact switch button */
  .topnav-row {{ padding: 0 14px; }}
  .topnav-row.row1 {{ height: auto; min-height: 48px; padding-top: 8px; padding-bottom: 8px; }}
  .wordmark {{ flex-direction: column; align-items: flex-start; gap: 1px; }}
  .wordmark-name {{ font-size: clamp(15px, 4.2vw, 20px); }}
  .wordmark-meta {{ font-size: 11px; }}
  .back-link {{ white-space: nowrap; font-size: 10px; padding: 5px 9px; }}

  /* #4 Bottom sheet */
  .detail-panel {{
    top: auto; left: 0;
    width: 100%; max-width: none; max-height: 85vh;
    transform: translateY(100%);
    border-left: none;
    border-top: 1px solid var(--border);
    border-radius: 20px 20px 0 0;
    box-shadow: 0 -10px 30px rgba(0,0,0,0.5);
  }}
  .detail-panel.open {{ transform: translateY(0); }}
  .detail-panel::before {{
    content: '';
    display: block;
    width: 36px; height: 4px;
    background: var(--border);
    border-radius: 2px;
    margin: 8px auto 0;
    flex-shrink: 0;
  }}
}}
"""



# ─── JS ───────────────────────────────────────────────────────────────────────

def build_js(act_json, sync_ids, click_ids, heat_air_text, heat_app_text,
             mirage_air_text, mirage_app_text, hr_temp_meta):
    # json.dumps produces safely-escaped JS string literals (handles quotes,
    # backslashes) for the build-time-computed annotation strings/arrays.
    heat_air_js = json.dumps(heat_air_text)
    heat_app_js = json.dumps(heat_app_text)
    mirage_air_js = json.dumps(mirage_air_text)
    mirage_app_js = json.dumps(mirage_app_text)
    hr_temp_js = json.dumps(hr_temp_meta)
    return f"""
var ACT_DATA  = {act_json};
var SYNC_IDS  = {json.dumps(sync_ids)};
var CLICK_IDS = {json.dumps(click_ids)};
var syncing   = false;

// Date (YYYY-MM-DD) → [activity ids], built from ACT_DATA for the calendar.
var DAY_INDEX = {{}};
Object.keys(ACT_DATA).forEach(function(id) {{
  var d = ACT_DATA[id].date;
  (DAY_INDEX[d] = DAY_INDEX[d] || []).push(id);
}});

// ─── Detail panel ───────────────────────────────────────────────────────────
function closeDetail() {{
  document.getElementById('detail-panel').classList.remove('open');
  document.getElementById('detail-backdrop').classList.remove('open');
}}
function renderActivity(a) {{
  var esc = function(s) {{ return String(s).replace(/</g,'&lt;').replace(/>/g,'&gt;'); }};
  var html = '';
  html += '<div class="d-name">' + esc(a.name) + '</div>';
  html += '<div class="d-date">' + a.date + ' · ' + esc(a.sport) + '</div>';
  html += '<div class="d-stats">';
  html += '<div class="d-stat"><div class="d-stat-val">' + a.dist_mi.toFixed(1) + '</div><div class="d-stat-lbl">mi</div></div>';
  if (a.hr)      html += '<div class="d-stat"><div class="d-stat-val">' + a.hr + '</div><div class="d-stat-lbl">avg bpm</div></div>';
  if (a.elev_ft) html += '<div class="d-stat"><div class="d-stat-val">' + a.elev_ft.toLocaleString() + '</div><div class="d-stat-lbl">elev ft</div></div>';
  html += '<div class="d-stat"><div class="d-stat-val">' + a.elapsed + '</div><div class="d-stat-lbl">time</div></div>';
  if (a.pace)    html += '<div class="d-stat"><div class="d-stat-val">' + esc(a.pace) + '</div><div class="d-stat-lbl">pace/speed</div></div>';
  html += '</div>';
  if (a.desc)    html += '<div class="d-desc">' + esc(a.desc) + '</div>';
  return html;
}}
function openPanel(html) {{
  document.getElementById('detail-body').innerHTML = html;
  document.getElementById('detail-panel').classList.add('open');
  document.getElementById('detail-backdrop').classList.add('open');
}}
function showDetail(actId) {{
  var a = ACT_DATA[String(actId)];
  if (!a) return;
  openPanel(renderActivity(a));
}}
function showDay(dateStr) {{
  var ids = DAY_INDEX[dateStr] || [];
  if (!ids.length) return;
  openPanel(ids.map(function(id) {{ return renderActivity(ACT_DATA[id]); }})
               .join('<div class="d-sep"></div>'));
}}

// ─── Calendar heatmap: mileage-intensity ↔ activity-type toggle ────────────
function toggleCalMode(mode, btn) {{
  document.querySelectorAll('.hm-cell[data-date]').forEach(function(c) {{
    c.setAttribute('fill', mode === 'type' ? c.getAttribute('data-type-color') : 'var(--accent)');
  }});
  var intensityLegend = document.querySelector('.hm-legend-intensity');
  var typeLegend = document.querySelector('.hm-legend-type');
  if (intensityLegend) intensityLegend.hidden = (mode === 'type');
  if (typeLegend) typeLegend.hidden = (mode !== 'type');
  var grp = btn ? btn.parentNode : null;
  if (grp) grp.querySelectorAll('.seg-btn').forEach(function(b) {{
    b.classList.remove('active');
  }});
  if (btn) btn.classList.add('active');
}}

// ─── Segment filter (trace 0 = Running, trace 1 = MTB) ─────────────────────
function filterSegs(type, btn) {{
  var el = document.getElementById('chart-segs');
  if (!el) return;
  var vis = type === 'all'  ? [true,  true]  :
            type === 'run'  ? [true,  false] :
                              [false, true];
  Plotly.restyle(el, {{visible: vis}}, [0, 1]);
  // Scope active-state reset to this control's own group — the page now has
  // more than one .seg-filter (heat toggle), so a global reset would clear it.
  var grp = btn ? btn.parentNode : null;
  if (grp) grp.querySelectorAll('.seg-btn').forEach(function(b) {{
    b.classList.remove('active');
  }});
  if (btn) btn.classList.add('active');
}}

// ─── Heat chart: air-temp ↔ apparent-temp toggle ──────────────────────────
// Traces 0-4 = air-temp view, 5-9 = apparent-temp view (5 each: 4 violin + HR
// line). Annotation index 1 = the bottom stat line (index 0 = "teal line" note).
var HEAT_ANN = {{
  air: {heat_air_js},
  app: {heat_app_js}
}};
function toggleHeat(view, btn) {{
  var el = document.getElementById('chart-x-heat');
  if (!el) return;
  var vis = view === 'app'
    ? [false,false,false,false,false, true,true,true,true,true]
    : [true,true,true,true,true, false,false,false,false,false];
  Plotly.restyle(el, {{visible: vis}}, [0,1,2,3,4,5,6,7,8,9]);
  Plotly.relayout(el, {{'annotations[1].text': HEAT_ANN[view]}});
  var grp = btn ? btn.parentNode : null;
  if (grp) grp.querySelectorAll('.seg-btn').forEach(function(b) {{
    b.classList.remove('active');
  }});
  if (btn) btn.classList.add('active');
}}

// ─── Mirage chart: air-temp ↔ apparent-temp toggle ─────────────────────────
// Traces 0-2 = raw (always visible); 3-4 = air-adjusted, 5-6 = apparent-adjusted.
// Only the adjusted pair swaps; annotation index 0 holds the raw/adjusted r/p.
var MIRAGE_ANN = {{
  air: {mirage_air_js},
  app: {mirage_app_js}
}};
function toggleMirage(view, btn) {{
  var el = document.getElementById('chart-x-mirage');
  if (!el) return;
  var vis = view === 'app'
    ? [false, false, true, true]
    : [true, true, false, false];
  Plotly.restyle(el, {{visible: vis}}, [3, 4, 5, 6]);
  Plotly.relayout(el, {{'annotations[0].text': MIRAGE_ANN[view]}});
  var grp = btn ? btn.parentNode : null;
  if (grp) grp.querySelectorAll('.seg-btn').forEach(function(b) {{
    b.classList.remove('active');
  }});
  if (btn) btn.classList.add('active');
}}

// ─── HR vs Temp chart: air-temp ↔ apparent-temp toggle ─────────────────────
// Trace counts can vary, so Python supplies per-view visibility arrays + the
// trace index list. Annotations: index 0 Run R², 1 TrailRun R², 2 caveat.
var HRTEMP = {hr_temp_js};
function toggleHrTemp(view, btn) {{
  var el = document.getElementById('chart-run-hr-temp');
  if (!el) return;
  var vis = view === 'app' ? HRTEMP.app_vis : HRTEMP.air_vis;
  Plotly.restyle(el, {{visible: vis}}, HRTEMP.trace_idx);
  var anns = view === 'app' ? HRTEMP.app_anns : HRTEMP.air_anns;
  var rl = {{}};
  for (var i = 0; i < anns.length; i++) rl['annotations[' + i + '].text'] = anns[i];
  Plotly.relayout(el, rl);
  var grp = btn ? btn.parentNode : null;
  if (grp) grp.querySelectorAll('.seg-btn').forEach(function(b) {{
    b.classList.remove('active');
  }});
  if (btn) btn.classList.add('active');
}}

// ─── Cross-chart date sync ─────────────────────────────────────────────────
function syncRange(sourceId, ed) {{
  if (syncing) return;
  var x0   = ed['xaxis.range[0]'];
  var x1   = ed['xaxis.range[1]'];
  var auto = ed['xaxis.autorange'];
  if (x0 === undefined && x1 === undefined && !auto) return;
  syncing = true;
  var promises = [];
  SYNC_IDS.forEach(function(id) {{
    if (id === sourceId) return;
    var el = document.getElementById(id);
    if (!el) return;
    if (auto) {{
      promises.push(Plotly.relayout(el, {{'xaxis.autorange': true}}));
    }} else {{
      var upd = {{}};
      if (x0 !== undefined) upd['xaxis.range[0]'] = x0;
      if (x1 !== undefined) upd['xaxis.range[1]'] = x1;
      promises.push(Plotly.relayout(el, upd));
    }}
  }});
  Promise.all(promises).then(function() {{ syncing = false; }});
}}

// ─── Theme toggle (light / dark / system) ──────────────────────────────────
(function() {{
  var root = document.documentElement;
  var mq = window.matchMedia('(prefers-color-scheme: light)');
  var STORAGE_KEY = 'strava-theme';

  function getStoredMode() {{
    var v = localStorage.getItem(STORAGE_KEY);
    return (v === 'light' || v === 'dark' || v === 'system') ? v : 'system';
  }}
  function effectiveTheme(mode) {{
    if (mode === 'system') return mq.matches ? 'light' : 'dark';
    return mode;
  }}
  function cssVar(name) {{
    return getComputedStyle(root).getPropertyValue(name).trim();
  }}
  // Dark-theme gray text hexes baked into figures by tidy_dark / chart builders.
  // Annotations using THESE are re-colored on theme change to the current
  // secondary text color.
  // Includes the light-theme --text-secondary/--text-tertiary grey (#424a53 ==
  // rgb(66,74,83)) so that once an annotation has been retinted to the light
  // grey, switching back to dark still matches and retints to #8b949e. Without
  // it the light->dark transition was one-way (label stuck at low-contrast light
  // grey on the dark plot).
  var GRAY_TEXT = ['#8b949e', '#e6edf3', '#424a53', 'rgb(66,74,83)'];
  // The translucent dark pill bg baked into Exploratory annotations.
  var DARK_PILL = 'rgba(13,17,23,0.65)';
  // Brand-colored annotation text (teal/amber/violet) is baked with the DARK
  // palette hex by the chart builders, but the dark variants are low-contrast on
  // white (amber 2.15, violet 2.72). Each pair maps both palette variants of a
  // brand color to the CSS var, so the text is retinted to the current theme's
  // variant (keeping brand identity while fixing contrast) and toggling back to
  // dark restores the bright variant automatically.
  var BRAND_TEXT = [
    {{ cssVar: '--running',   variants: ['#2dd4bf', '#0d9488'] }},
    {{ cssVar: '--mtb',       variants: ['#f59e0b', '#c2710c'] }},
    {{ cssVar: '--elevation', variants: ['#a78bfa', '#6d28d9'] }},
  ];
  function normColor(c) {{ return (c == null ? '' : ('' + c)).toLowerCase().replace(/\\s+/g, ''); }}
  function isGrayText(c) {{
    var n = normColor(c);
    for (var i = 0; i < GRAY_TEXT.length; i++) {{ if (n === GRAY_TEXT[i]) return true; }}
    return false;
  }}
  function brandTextVar(c) {{
    var n = normColor(c);
    for (var i = 0; i < BRAND_TEXT.length; i++) {{
      var variants = BRAND_TEXT[i].variants;
      for (var j = 0; j < variants.length; j++) {{
        if (n === normColor(variants[j])) return BRAND_TEXT[i].cssVar;
      }}
    }}
    return null;
  }}
  function applyChartTheme() {{
    var textPrimary   = cssVar('--text-primary');
    var textSecondary = cssVar('--text-secondary');
    var textTertiary  = cssVar('--text-tertiary');
    var grid          = cssVar('--grid');
    var bgElevated    = cssVar('--bg-elevated');
    var border        = cssVar('--border');
    var pillBg        = cssVar('--ann-pill-bg');
    // Current-theme brand variants for retinting brand-colored annotation text.
    var brandColors   = {{}};
    for (var bi = 0; bi < BRAND_TEXT.length; bi++) {{
      brandColors[BRAND_TEXT[bi].cssVar] = cssVar(BRAND_TEXT[bi].cssVar);
    }}
    document.querySelectorAll('.plotly-graph-div').forEach(function(el) {{
      if (!el || !el._fullLayout || !window.Plotly) return;
      var fl  = el._fullLayout;
      var upd = {{
        'font.color': textSecondary,
        'legend.font.color': textSecondary,
        'hoverlabel.font.color': textPrimary,
        'hoverlabel.bgcolor': bgElevated,
        'hoverlabel.bordercolor': border,
        // chart titles are baked #e6edf3 by tidy_dark -> invisible on white.
        'title.font.color': textPrimary,
      }};
      // 1. Every x/y axis (incl. subplot axes xaxis2, yaxis2, ... matched dynamically).
      Object.keys(fl).forEach(function(k) {{
        if (/^[xy]axis\\d*$/.test(k)) {{
          upd[k + '.tickfont.color']    = textTertiary;
          upd[k + '.title.font.color']  = textSecondary;
          upd[k + '.gridcolor']         = grid;
          upd[k + '.zerolinecolor']     = grid;
        }}
      }});
      // 3 & 5. Annotations: recolor gray-text ones to secondary text; retint
      //        brand-colored ones to the current theme's brand variant.
      //        Swap the dark pill bg for the theme-driven pill var.
      if (fl.annotations) {{
        for (var i = 0; i < fl.annotations.length; i++) {{
          var a = fl.annotations[i];
          if (a && a.font && isGrayText(a.font.color)) {{
            upd['annotations[' + i + '].font.color'] = textSecondary;
          }} else if (a && a.font) {{
            var bvar = brandTextVar(a.font.color);
            if (bvar) {{
              upd['annotations[' + i + '].font.color'] = brandColors[bvar];
            }}
          }}
          if (a && normColor(a.bgcolor) === normColor(DARK_PILL)) {{
            upd['annotations[' + i + '].bgcolor'] = pillBg;
          }}
        }}
      }}
      // Weekly Volume rangeslider: retint its bg/border so it reads in light mode.
      if (fl.xaxis && fl.xaxis.rangeslider) {{
        upd['xaxis.rangeslider.bgcolor']     = cssVar('--bg-glass');
        upd['xaxis.rangeslider.bordercolor'] = cssVar('--border-subtle');
      }}
      try {{ Plotly.relayout(el, upd); }} catch (e) {{ /* chart may not be ready */ }}
      // 4. Colorbars (V6 "Avg HR") are baked per-trace via marker.colorbar.
      try {{
        var data = el.data || [];
        var tIdx = [];
        for (var t = 0; t < data.length; t++) {{
          if (data[t] && data[t].marker && data[t].marker.colorbar) tIdx.push(t);
        }}
        if (tIdx.length) {{
          Plotly.restyle(el, {{
            'marker.colorbar.tickfont.color': textTertiary,
            'marker.colorbar.title.font.color': textSecondary,
          }}, tIdx);
        }}
      }} catch (e) {{ /* no colorbar on this chart */ }}
    }});
  }}
  // Reachable from the separate tab-routing IIFE so hidden-tab charts get
  // retinted (not just resized) when their tab is first shown.
  window.__applyChartTheme = applyChartTheme;
  function setActiveButton(mode) {{
    document.querySelectorAll('.theme-toggle button').forEach(function(b) {{
      b.classList.toggle('active', b.dataset.theme === mode);
    }});
  }}
  function applyTheme(mode) {{
    var eff = effectiveTheme(mode);
    root.classList.toggle('light', eff === 'light');
    setActiveButton(mode);
    applyChartTheme();
  }}

  var current = getStoredMode();
  applyTheme(current);

  document.querySelectorAll('.theme-toggle button').forEach(function(b) {{
    b.addEventListener('click', function() {{
      current = b.dataset.theme;
      localStorage.setItem(STORAGE_KEY, current);
      applyTheme(current);
    }});
  }});

  mq.addEventListener('change', function() {{
    if (current === 'system') applyTheme('system');
  }});
}})();

// ─── Wire chart listeners on load ──────────────────────────────────────────
window.addEventListener('load', function() {{
  SYNC_IDS.forEach(function(id) {{
    var el = document.getElementById(id);
    if (!el) return;
    el.on('plotly_relayout', function(ed) {{ syncRange(id, ed); }});
  }});
  CLICK_IDS.forEach(function(id) {{
    var el = document.getElementById(id);
    if (!el) return;
    el.on('plotly_click', function(data) {{
      if (!data.points || !data.points.length) return;
      var pt = data.points[0];
      if (pt.customdata) showDetail(String(pt.customdata));
    }});
  }});

  // Calendar cells are hand-built SVG (not Plotly) — wire them to the day view.
  document.querySelectorAll('.hm-cell[data-date]').forEach(function(c) {{
    c.addEventListener('click', function() {{ showDay(c.getAttribute('data-date')); }});
  }});

  // Close detail panel on backdrop click or Escape
  var bd = document.getElementById('detail-backdrop');
  if (bd) bd.addEventListener('click', closeDetail);
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeDetail();
  }});

  // ─── Page/tab routing ─────────────────────────────────────────────────
  (function() {{
    var tabs = document.querySelectorAll('.tab[data-view]');
    function activateView(name) {{
      tabs.forEach(function(t) {{
        t.classList.toggle('active', t.dataset.view === name);
      }});
      document.querySelectorAll('.view').forEach(function(v) {{
        v.classList.toggle('active', v.id === 'view-' + name);
      }});
      // Retint chart titles/axes to the current theme (color only; size-safe).
      if (window.__applyChartTheme) window.__applyChartTheme();
      // Charts laid out while their view was display:none render at 0 width, so
      // Plotly leaves the SVG at its ~700px default and it overflows the card
      // (clipped by .card{{overflow:hidden}}). Wait one frame for the now-visible
      // card to lay out, THEN resize each chart to its container. Resizing
      // synchronously here reads a 0 width, leaving the chart too wide. (Don't
      // autorange — several charts set intentional fixed ranges.)
      if (window.Plotly) {{
        requestAnimationFrame(function() {{
          var view = document.getElementById('view-' + name);
          if (view) view.querySelectorAll('.js-plotly-plot').forEach(function(el) {{
            Plotly.Plots.resize(el);
          }});
          // Thin crowded axes now that the view's charts have real width.
          if (window.__thinTicks) window.__thinTicks();
        }});
      }}
      history.replaceState(null, '', '#' + name);
      var at = document.querySelector('.tab[data-view="' + name + '"]');
      if (at) at.scrollIntoView({{behavior: 'smooth', block: 'nearest', inline: 'center'}});
    }}
    tabs.forEach(function(t) {{
      t.addEventListener('click', function() {{ activateView(t.dataset.view); }});
    }});
    var hash = (location.hash || '').replace('#', '');
    activateView(document.getElementById('view-' + hash) ? hash : 'overview');
  }})();

  // ─── Mobile: re-fit charts, thin crowded axes, simplify ──────────────────
  (function() {{
    var mq = window.matchMedia('(max-width:640px)');
    // Dense time/numeric charts: thin ticks to ~1 per 100px (x) / 80px (y).
    // Categorical charts are excluded — nticks can drop their category labels.
    var DENSE = [
      {{id: 'chart-volume', dual: false}},
      {{id: 'chart-elevation', dual: false}},
      {{id: 'chart-hr', dual: false}},
      {{id: 'chart-pace', dual: true}},
      {{id: 'chart-run-pace-hr', dual: false}},
      {{id: 'chart-run-hr-temp', dual: false}}
    ];
    function thinTicks() {{
      if (!window.Plotly) return;
      var mobile = mq.matches;
      DENSE.forEach(function(c) {{
        var el = document.getElementById(c.id);
        if (!el || !el._fullLayout) return;
        var w = el.clientWidth || 0, h = el.clientHeight || 0;
        if (w === 0) return;  // hidden view — recomputed on activation
        var nx = mobile ? Math.max(2, Math.floor(w / 100)) : 0;  // 0 = auto
        var ny = mobile ? Math.max(2, Math.floor(h / 80)) : 0;
        var upd = {{'xaxis.nticks': nx, 'yaxis.nticks': ny}};
        if (c.dual) upd['yaxis2.nticks'] = ny;
        Plotly.relayout(el, upd);
      }});
    }}
    window.__thinTicks = thinTicks;
    function simplify(mobile) {{
      if (!window.Plotly) return;
      var vol = document.getElementById('chart-volume');
      if (vol && vol._fullLayout) Plotly.relayout(vol, {{'xaxis.rangeslider.visible': !mobile}});
      var segs = document.getElementById('chart-segs');
      if (segs && segs._fullLayout) Plotly.relayout(segs, {{'xaxis.tickfont.size': mobile ? 8 : 10}});
      var arch = document.getElementById('chart-x-archetypes');
      if (arch && arch._fullLayout) {{
        var upd = {{}};
        for (var i = 0; i < 8; i++) upd['annotations[' + i + '].visible'] = !mobile;
        Plotly.relayout(arch, upd);
      }}
    }}
    function applyMobile() {{ simplify(mq.matches); thinTicks(); }}
    // Debounced resize → re-fit active charts, then re-thin ticks for new width.
    var t;
    function onResize() {{
      clearTimeout(t);
      t = setTimeout(function() {{
        if (!window.Plotly) return;
        document.querySelectorAll('.view.active .js-plotly-plot').forEach(function(el) {{
          Plotly.Plots.resize(el);
        }});
        thinTicks();
      }}, 150);
    }}
    window.addEventListener('resize', onResize);
    if (window.visualViewport) window.visualViewport.addEventListener('resize', onResize);
    mq.addEventListener('change', applyMobile);
    applyMobile();
  }})();

  // ─── Bottom-sheet swipe-to-dismiss ───────────────────────────────────────
  (function() {{
    var panel = document.getElementById('detail-panel');
    if (!panel) return;
    var sy = 0, drag = false;
    panel.addEventListener('touchstart', function(e) {{
      if (!window.matchMedia('(max-width:640px)').matches) return;
      sy = e.touches[0].clientY; drag = true;
    }}, {{passive: true}});
    panel.addEventListener('touchmove', function(e) {{
      if (!drag) return;
      var dy = e.touches[0].clientY - sy;
      if (dy > 0) panel.style.transform = 'translateY(' + dy + 'px)';
    }}, {{passive: true}});
    panel.addEventListener('touchend', function(e) {{
      if (!drag) return;
      drag = false;
      var dy = e.changedTouches[0].clientY - sy;
      if (dy > 80) {{
        panel.style.transform = 'translateY(100%)';
        setTimeout(function() {{ panel.style.transform = ''; closeDetail(); }}, 240);
      }} else {{
        panel.style.transform = '';
      }}
    }});
  }})();
}});
"""


# ─── Theme toggle SVGs ──────────────────────────────────────────────────────

THEME_TOGGLE_SVGS = {
    "light":  '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
    "dark":   '<svg viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/></svg>',
    "system": '<svg viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 21h8M12 18v3"/></svg>',
}
