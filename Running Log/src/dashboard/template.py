"""The CSS f-string (themed via dashboard.config color tokens) and the JS
raw-string that drive the dashboard's client-side interactivity."""

from dashboard.config import (
    ACCENT, ACCENT_DIM, ACCENT_GLOW, BG_BASE, BG_ELEVATED, BG_GLASS, BG_SURFACE,
    BORDER, BORDER_SUBTLE, EASY_COLOR, LONG_COLOR, RACE_COLOR, TEMPO_COLOR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, WORKOUT_COLOR,
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
  --grid: rgba(48, 54, 61, 0.4);
  --bg-gradient-1: rgba(88, 166, 255, 0.06);
  --bg-gradient-2: rgba(167, 139, 250, 0.04);
  --accent: {ACCENT};
  --accent-glow: {ACCENT_GLOW};
  --accent-dim: {ACCENT_DIM};
  --easy: {EASY_COLOR};
  --tempo: {TEMPO_COLOR};
  --long: {LONG_COLOR};
  --race: {RACE_COLOR};
  --workout: {WORKOUT_COLOR};
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
  --bg-gradient-1: rgba(9, 105, 218, 0.09);
  --bg-gradient-2: rgba(130, 80, 223, 0.07);
  --accent: #0550ae;
  --accent-glow: rgba(5, 80, 174, 0.18);
  --accent-dim: rgba(5, 80, 174, 0.10);
  --easy: #0d9488;
  --tempo: #c2710c;
  --long: #6d28d9;
  --race: #c81e1e;
  --workout: #1d4ed8;
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

.dash-footer {{
  text-align: center;
  padding: 28px 24px 36px;
  margin-top: 24px;
  font-size: 13px;
  color: var(--text-secondary);
  border-top: 1px solid var(--border);
}}
.dash-footer a {{
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.15s ease;
}}
.dash-footer a:hover {{ border-bottom-color: var(--accent); }}

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
}}
.topnav-row.row1 {{ height: 48px; }}
.topnav-row.row2 {{ padding-top: 10px; padding-bottom: 11px; }}

.wordmark {{ display: flex; align-items: center; gap: 10px; }}
.wordmark-name {{
  font-size: clamp(22px, 6vw, 34px); font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}}
.wordmark-meta {{ font-family: 'Geist Mono', monospace; font-size: 16px; color: var(--text-tertiary); }}

.strava-btn {{
  display: inline-flex; align-items: center; gap: 6px;
  font-family: 'Geist', sans-serif;
  font-size: 11px; font-weight: 600;
  background: rgba(252, 76, 2, 0.08);
  border: 1px solid rgba(252, 76, 2, 0.25);
  color: #fc4c02;
  padding: 6px 10px; border-radius: 7px;
  cursor: pointer; text-decoration: none;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.strava-btn:hover {{
  background: rgba(252, 76, 2, 0.16);
  border-color: rgba(252, 76, 2, 0.45);
}}
.strava-btn svg {{ width: 12px; height: 12px; fill: #fc4c02; }}

/* Theme toggle */
.theme-toggle {{
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px;
  gap: 0;
}}
.theme-toggle button {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 22px;
  background: transparent; border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 5px;
  padding: 0;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.theme-toggle button:hover {{ color: var(--text-primary); }}
.theme-toggle button.active {{
  background: var(--accent-dim);
  color: var(--accent);
}}
.theme-toggle button svg {{ width: 13px; height: 13px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
.topnav-actions {{ display: inline-flex; align-items: center; gap: 10px; }}

/* Chart toggle (theme-aware, used by Workout Mix per Season) */
.card-title-row {{
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 8px; flex-wrap: wrap;
}}
.card-title-row .card-title {{ margin-bottom: 0; }}
.chart-toggle {{
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px;
  gap: 0;
}}
.chart-toggle button {{
  background: transparent; border: none;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif; font-size: 11px;
  padding: 4px 10px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.chart-toggle button:hover {{ color: var(--text-primary); }}
.chart-toggle button.active {{
  background: var(--accent-dim);
  color: var(--accent);
}}

/* Tab nav */
.tabnav {{
  display: flex; gap: 4px;
  margin-bottom: -1px;
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
  padding: 10px 14px;
  cursor: pointer;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
  display: inline-flex; align-items: center; gap: 6px;
  scroll-snap-align: start; flex-shrink: 0;
}}
.tab:hover {{ color: var(--text-primary); }}
.tab.active {{
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}}

/* Main content */
main {{
  flex: 1;
  max-width: 1100px; width: 100%;
  margin: 0 auto;
  padding: 32px 32px 80px;
}}

.page-header {{
  margin-bottom: 24px;
}}
.eyebrow {{
  font-family: 'Geist Mono', monospace;
  font-size: 10px; font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}}
.page-header h1 {{
  margin: 0;
  font-size: clamp(20px, 4.5vw, 26px); font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}}

.view {{ display: none; animation: fadeUp 240ms cubic-bezier(0.16, 1, 0.3, 1); }}
.view.active {{ display: block; }}

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
.chart-caption {{
  margin-top: -12px; margin-bottom: 8px;
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: 'Geist Mono', monospace;
}}

/* Stat cards */
.stat-grid {{
  display: grid;
  grid-template-columns: repeat(6, 1fr);
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
  font-size: clamp(18px, 4.5vw, 26px); font-weight: 600;
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

/* Notes search */
.notes-card .card-header {{ margin-bottom: 14px; }}
.notes-count {{
  font-family: 'Geist Mono', monospace;
  font-size: 11px; color: var(--text-tertiary);
}}
.notes-search {{
  position: relative;
  margin-bottom: 12px;
}}
.notes-search input {{
  width: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 36px 10px 14px;
  color: var(--text-primary);
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  outline: none;
  transition: border-color 120ms;
}}
.notes-search input:focus {{ border-color: var(--accent); }}
.notes-search input::placeholder {{ color: var(--text-tertiary); }}
.notes-search #notes-clear {{
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: var(--text-secondary);
  font-size: 18px; cursor: pointer; padding: 0 6px;
}}
.filter-pills {{
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-bottom: 12px;
}}
.filter-pill {{
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 11px; font-weight: 500;
  padding: 5px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}}
.filter-pill:hover {{ color: var(--text-primary); }}
.filter-pill.active {{
  background: color-mix(in srgb, var(--pill-color, var(--accent)) 12%, transparent);
  border-color: color-mix(in srgb, var(--pill-color, var(--accent)) 30%, transparent);
  color: var(--pill-color, var(--accent));
}}
.filter-pill[data-type="all"].active {{
  background: var(--accent-dim);
  border-color: color-mix(in srgb, var(--accent) 30%, transparent);
  color: var(--accent);
}}

.notes-list {{
  max-height: 218px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 6px;
  padding-right: 4px;
}}
.notes-list::-webkit-scrollbar {{ width: 8px; }}
.notes-list::-webkit-scrollbar-thumb {{ background: var(--border-subtle); border-radius: 4px; }}
.note-row {{
  background: var(--bg-elevated);
  border-radius: 8px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: 72px 92px 64px 1fr 14px;
  gap: 12px; align-items: center;
  cursor: pointer;
  transition: background 120ms;
  text-align: left;
}}
.note-row > .type-badge {{ justify-self: start; }}
.note-row > .note-date,
.note-row > .note-miles {{ text-align: left; }}
.note-row:hover {{ background: color-mix(in srgb, var(--bg-elevated) 70%, var(--bg-surface)); }}
.note-row.expanded .note-text {{ -webkit-line-clamp: unset; display: block; white-space: pre-wrap; }}
.note-row.expanded .chev {{ transform: rotate(180deg); }}
.note-date {{
  font-family: 'Geist Mono', monospace; font-size: 11px;
  color: var(--text-tertiary); white-space: nowrap;
}}
.note-miles {{
  font-family: 'Geist Mono', monospace; font-size: 11px;
  color: var(--text-secondary); white-space: nowrap;
}}
.note-text {{
  color: var(--text-primary);
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.note-text mark {{
  background: color-mix(in srgb, var(--accent) 35%, transparent);
  color: var(--text-primary);
  border-radius: 2px;
}}
.chev {{
  color: var(--text-tertiary); font-size: 10px;
  transition: transform 240ms cubic-bezier(0.16, 1, 0.3, 1);
}}

/* Type badge */
.type-badge {{
  display: inline-block;
  font-size: 9px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 2px 7px; border-radius: 4px;
  background: color-mix(in srgb, var(--badge-color) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--badge-color) 30%, transparent);
  color: var(--badge-color);
}}

/* Heatmap */
.heatmap-card {{ overflow-x: auto; }}
.hm-mode-toggle {{
  display: inline-flex; gap: 2px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 2px;
}}
.hm-toggle {{
  background: none; border: none;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 11px;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 120ms;
}}
.hm-toggle:hover {{ color: var(--text-primary); }}
.hm-toggle.active {{
  background: var(--bg-glass);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}}

.hm-grid {{ display: flex; flex-direction: column; gap: 10px; }}
.hm-year-row {{ display: flex; align-items: center; gap: 8px; }}
.hm-year {{
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--text-tertiary);
  width: 36px; flex-shrink: 0;
}}
.hm-year-row svg {{ flex: 1; min-width: 800px; }}
.hm-cell {{ transition: transform 120ms cubic-bezier(0.16, 1, 0.3, 1); transform-origin: center; transform-box: fill-box; }}
.hm-cell:hover {{ transform: scale(1.4); }}
.hm-cell.hm-flash {{ animation: hm-flash-pulse 1.4s ease-out; transform-origin: center; transform-box: fill-box; }}
@keyframes hm-flash-pulse {{
  0%   {{ stroke: var(--accent); stroke-width: 0; transform: scale(1); }}
  20%  {{ stroke: var(--accent); stroke-width: 3; transform: scale(2.2); }}
  100% {{ stroke: var(--accent); stroke-width: 0; transform: scale(1); }}
}}
.hm-month {{ fill: var(--text-tertiary); font-size: 9px; font-family: 'Geist Mono', monospace; }}
.hm-dow   {{ fill: var(--text-tertiary); font-size: 9px; font-family: 'Geist Mono', monospace; }}

.hm-legend {{
  margin-top: 4px; margin-bottom: 14px;
  display: flex; gap: 14px; align-items: center;
  font-size: 10px; color: var(--text-tertiary);
  font-family: 'Geist Mono', monospace;
}}
.hm-legend-intensity {{ gap: 8px; }}
.hm-legend-item {{ display: inline-flex; gap: 6px; align-items: center; }}
.hm-legend-item .swatch {{ width: 12px; height: 12px; border-radius: 2px; }}
.hm-legend-grad {{
  display: inline-block;
  width: 140px; height: 10px; border-radius: 3px;
  background: linear-gradient(
    to right,
    color-mix(in srgb, var(--accent) 10%, transparent),
    var(--accent)
  );
}}
.hm-legend-meta {{ color: var(--text-secondary); }}
.hm-legend[hidden] {{ display: none; }}

/* Detail panel (click-to-detail side panel) */
.detail-backdrop {{
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45);
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
  box-shadow: -10px 0 30px rgba(0,0,0,0.5);
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
.detail-date {{
  font-family: 'Geist Mono', monospace;
  font-size: 14px;
  color: var(--text-primary);
}}
.detail-close {{
  background: none; border: none;
  color: var(--text-secondary);
  font-size: 24px; line-height: 1;
  cursor: pointer; padding: 4px 12px;
  border-radius: 6px;
  transition: background 150ms, color 150ms;
}}
.detail-close:hover {{ background: var(--bg-elevated); color: var(--text-primary); }}
.detail-body {{ flex: 1; overflow-y: auto; padding: 20px; }}
.detail-entry {{
  padding: 16px 0;
  border-bottom: 1px solid var(--border-subtle);
}}
.detail-entry:last-child {{ border-bottom: none; padding-bottom: 0; }}
.detail-entry:first-child {{ padding-top: 0; }}
.detail-entry-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
.detail-type-badge {{
  display: inline-block;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background: var(--badge-color, var(--accent));
  color: var(--bg-base);
}}
.detail-stats {{
  display: flex; gap: 18px; flex-wrap: wrap;
  font-family: 'Geist Mono', monospace;
  font-size: 13px;
  color: var(--text-secondary);
}}
.detail-stat-val {{ color: var(--text-primary); font-weight: 600; }}
.detail-race-info {{
  margin: 12px 0 0;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--race) 12%, transparent);
  border-left: 3px solid var(--race);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
}}
.detail-race-info strong {{ color: var(--text-primary); font-weight: 600; }}
.detail-comments {{
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}}
.detail-extras {{
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
}}
.detail-empty {{
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  padding: 60px 20px;
}}
.race-card[data-date] {{ cursor: pointer; transition: border-color 150ms, background 150ms; }}
.race-card[data-date]:hover {{ border-color: var(--accent); background: var(--accent-dim); }}
.race-card[data-date]:focus {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.hm-cell[data-date] {{ cursor: pointer; }}

/* PR cards */
.pr-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}}
.pr-card {{
  position: relative;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 18px 20px;
  overflow: hidden;
}}
.pr-card::after {{
  content: '';
  position: absolute; top: 0; right: 0; bottom: 0;
  width: 4px; background: var(--pr-color);
}}
.pr-label {{
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 8px;
}}
.pr-time {{
  font-family: 'Geist Mono', monospace;
  font-size: 30px; font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--text-primary);
  line-height: 1;
}}
.pr-season {{
  margin-top: 6px;
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--text-tertiary);
}}


/* Race tabs + cards */
.race-tabs {{
  display: inline-flex; gap: 2px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 3px;
  margin-bottom: 16px;
}}
.race-tab {{
  background: none; border: none;
  color: var(--text-secondary);
  font-family: 'Geist', sans-serif;
  font-size: 12px; font-weight: 500;
  padding: 7px 14px;
  border-radius: 7px;
  cursor: pointer;
  transition: all 120ms;
  display: inline-flex; align-items: center; gap: 8px;
}}
.race-tab:hover {{ color: var(--text-primary); }}
.race-tab.active {{
  background: var(--bg-glass);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.25);
}}
.tab-count {{
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  background: var(--bg-elevated);
  padding: 2px 6px; border-radius: 4px;
  color: var(--text-tertiary);
}}
.race-tab.active .tab-count {{ background: var(--bg-base); color: var(--text-secondary); }}

.race-list {{ display: flex; flex-direction: column; gap: 8px; }}

/* Race controls (search / sort / filter) */
.race-controls {{
  display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  margin-bottom: 14px;
}}
.race-search {{
  position: relative;
  flex: 1 1 240px; min-width: 200px;
}}
.race-search input {{
  width: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  padding: 8px 30px 8px 12px;
  transition: border-color 120ms;
}}
.race-search input:focus {{ outline: none; border-color: var(--accent); }}
.race-search button {{
  position: absolute; top: 50%; right: 6px; transform: translateY(-50%);
  background: none; border: none;
  color: var(--text-tertiary);
  font-size: 16px; line-height: 1;
  cursor: pointer; padding: 4px 6px;
}}
.race-control-group {{
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--text-secondary);
}}
.race-control-label {{
  text-transform: uppercase; letter-spacing: 0.06em;
  font-weight: 600;
}}
.race-controls select {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: 'Geist', sans-serif;
  font-size: 12px;
  padding: 6px 10px;
  cursor: pointer;
}}
.race-controls select:focus {{ outline: none; border-color: var(--accent); }}
.race-pr-toggle {{
  cursor: pointer;
  user-select: none;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
}}
.race-pr-toggle input {{ accent-color: var(--accent); margin: 0; }}
.race-empty {{
  padding: 30px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  background: var(--bg-elevated);
  border: 1px dashed var(--border-subtle);
  border-radius: 10px;
}}
.race-card {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 14px 18px;
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: 14px; align-items: center;
  transition: border-color 120ms;
}}
.race-card:hover {{ border-color: var(--border); }}
.race-type-badge {{
  font-size: 9px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 3px 8px; border-radius: 4px;
  background: color-mix(in srgb, var(--badge-color) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--badge-color) 30%, transparent);
  color: var(--badge-color);
}}
.race-name {{
  font-size: 13px; font-weight: 500;
  color: var(--text-primary);
  line-height: 1.3;
}}
.race-sub {{
  margin-top: 3px;
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--text-tertiary);
}}
.race-time {{
  font-family: 'Geist Mono', monospace;
  font-size: 16px; font-weight: 600;
  color: var(--text-primary);
}}
.relay-tag {{
  font-family: 'Geist', sans-serif;
  font-size: 9px; font-weight: 500;
  color: var(--text-tertiary);
  margin-left: 6px;
  text-transform: lowercase;
}}
.pr-badge {{
  background: color-mix(in srgb, var(--race) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--race) 30%, transparent);
  color: var(--race);
  font-size: 9px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 2px 7px; border-radius: 4px;
}}
.race-summary {{
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--accent-dim);
  border: 1px solid color-mix(in srgb, var(--accent) 20%, transparent);
  border-radius: 8px;
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--text-secondary);
}}

/* Workout mix */
.type-stat-grid {{
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
  margin-bottom: 20px;
}}
.type-stat-card {{
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px 18px;
  position: relative;
}}
.type-swatch {{
  width: 8px; height: 8px; border-radius: 2px;
  background: var(--ts-color);
  display: inline-block; margin-bottom: 8px;
}}
.type-num {{
  font-family: 'Geist Mono', monospace;
  font-size: 24px; font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.03em;
}}
.type-label {{
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 4px;
}}

/* Sparklines — vertically stacked rows */
.spark-grid {{
  display: flex; flex-direction: column;
  gap: 10px;
}}
.spark-card {{
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 12px 16px;
  display: grid;
  grid-template-columns: 80px 110px 1fr;
  align-items: center;
  gap: 16px;
}}
.spark-label {{
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
}}
.spark-stat {{ display: flex; align-items: baseline; gap: 6px; }}
.spark-num {{
  font-family: 'Geist Mono', monospace;
  font-size: 22px; font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  line-height: 1;
}}
.spark-sub {{
  font-size: 10px;
  color: var(--text-tertiary);
  white-space: nowrap;
}}
.spark-chart {{ min-width: 0; }}
.spark-chart .plotly-graph-div {{ width: 100% !important; }}


/* Patterns */
.patterns-grid {{
  display: flex; flex-direction: column; gap: 20px;
  margin-bottom: 20px;
}}
.patterns-grid .card {{ margin-bottom: 0; }}
.patterns-grid .plotly-graph-div {{ width: 100% !important; }}

.streak-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;
  text-align: left;
}}
.streak-num {{
  font-family: 'Geist Mono', monospace;
  font-size: 32px; font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--text-primary);
  line-height: 1;
}}
.streak-label {{
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.04em;
}}

/* ── Responsive / mobile (kept last so overrides win by source order) ── */
@media (max-width: 900px) {{
  .stat-grid {{ grid-template-columns: repeat(3, 1fr); }}
  .pr-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .type-stat-grid {{ grid-template-columns: repeat(3, 1fr); }}
}}
@media (max-width: 640px) {{
  .stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .type-stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .spark-card {{ grid-template-columns: 70px 1fr; row-gap: 6px; }}
  .spark-card .spark-chart {{ grid-column: 1 / -1; }}
  main {{ padding: 20px 14px 60px; }}
  .theme-toggle button {{ width: 36px; height: 36px; }}
  .tab {{ min-height: 44px; }}
  .hm-toggle {{ min-height: 40px; padding: 6px 12px; }}
  .race-tab {{ min-height: 40px; }}
  .filter-pill {{ min-height: 40px; padding: 6px 14px; }}
  .chart-toggle button {{ min-height: 40px; padding: 6px 12px; }}
  .js-plotly-plot {{ max-width: 100%; }}

  /* #1 Topnav: stack title over date, compact switch button */
  .topnav-row {{ padding: 0 14px; }}
  .topnav-row.row1 {{ height: auto; min-height: 48px; padding-top: 8px; padding-bottom: 8px; }}
  .wordmark {{ flex-direction: column; align-items: flex-start; gap: 1px; }}
  .wordmark-name {{ font-size: clamp(17px, 5vw, 24px); }}
  .wordmark-meta {{ font-size: 11px; }}
  .strava-btn {{ white-space: nowrap; font-size: 10px; padding: 5px 9px; }}

  /* #5 Caption must not ride up into the (shorter) mobile plot */
  .chart-caption {{ margin-top: 0; }}

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


JS = r"""
// ─── Tab nav ────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.view;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + target).classList.add('active');
    history.replaceState(null, '', '#' + target);
    tab.scrollIntoView({behavior: 'smooth', block: 'nearest', inline: 'center'});
    // Trigger Plotly redraw on visible charts (in case sizes were 0)
    document.querySelectorAll('#view-' + target + ' .js-plotly-plot').forEach(el => {
      window.Plotly && window.Plotly.Plots.resize(el);
    });
    // Thin crowded axes now that the view's charts have real width.
    if (window.__thinTicks) window.__thinTicks();
  });
});
const initialHash = (location.hash || '#overview').slice(1);
const initialTab = document.querySelector('[data-view="' + initialHash + '"]') ||
                   document.querySelector('[data-view="overview"]');
if (initialTab) initialTab.click();

// ─── Races: search / sort / filter ─────────────────────────────────────────
(function() {
  const dataEl = document.getElementById('races-data');
  if (!dataEl) return;
  const races  = JSON.parse(dataEl.textContent);
  const list   = document.getElementById('race-list');
  const summary= document.getElementById('race-summary');
  const queryEl   = document.getElementById('race-query');
  const clearEl   = document.getElementById('race-clear');
  const sortEl    = document.getElementById('race-sort');
  const distEl    = document.getElementById('race-distance');
  const prOnlyEl  = document.getElementById('race-pr-only');
  const tabs      = document.querySelectorAll('.race-tab');

  let activeCat = 'all';

  const BUCKET_ORDER = {"800m":1, "Mile":2, "1500m":3, "3k":4, "3k steeple":5, "5k":6, "6k":7};

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function highlight(s, q) {
    if (!q) return esc(s);
    const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    return esc(s).replace(re, m => '<mark>' + m + '</mark>');
  }

  function renderCard(r, q) {
    const relay = r.is_relay ? '<span class="relay-tag">relay</span>' : '';
    const pr    = r.pr ? '<span class="pr-badge">PR</span>' : '';
    return `<div class="race-card" data-date="${esc(r.date)}" tabindex="0" role="button">
      <span class="race-type-badge" style="--badge-color: ${r.type_color}">${esc(r.type_label)}</span>
      <div class="race-meta">
        <div class="race-name">${highlight(r.race, q)}</div>
        <div class="race-sub">${esc(r.season)} · ${highlight(r.distance, q)}</div>
      </div>
      <div class="race-time">${esc(r.time)}${relay}</div>
      ${pr}
    </div>`;
  }

  function render() {
    const q = queryEl.value.trim();
    const ql = q.toLowerCase();
    const dist = distEl.value;
    const prOnly = prOnlyEl.checked;
    const sort = sortEl.value;

    let filtered = races.filter(r => {
      if (activeCat !== 'all' && r.category !== activeCat) return false;
      if (dist && r.bucket !== dist) return false;
      if (prOnly && !r.pr) return false;
      if (ql) {
        const hay = (r.race + ' ' + r.distance).toLowerCase();
        if (!hay.includes(ql)) return false;
      }
      return true;
    });

    filtered.sort((a, b) => {
      switch (sort) {
        case 'date-asc':  return a.date.localeCompare(b.date);
        case 'date-desc': return b.date.localeCompare(a.date);
        case 'time-asc':
          if (a.time_seconds == null) return 1;
          if (b.time_seconds == null) return -1;
          return a.time_seconds - b.time_seconds;
        case 'distance': {
          const ao = BUCKET_ORDER[a.bucket] || 99;
          const bo = BUCKET_ORDER[b.bucket] || 99;
          return ao - bo || a.date.localeCompare(b.date);
        }
        case 'pr':
          return (b.pr - a.pr) || b.date.localeCompare(a.date);
        default: return 0;
      }
    });

    list.innerHTML = filtered.map(r => renderCard(r, q)).join('') ||
                     '<div class="race-empty">No races match the current filters.</div>';
    const prCount = filtered.reduce((n, r) => n + (r.pr ? 1 : 0), 0);
    summary.textContent = filtered.length === 0
      ? ''
      : `${prCount} PR${prCount === 1 ? '' : 's'} across ${filtered.length} race${filtered.length === 1 ? '' : 's'}`;
    clearEl.hidden = !q;

    // Wire up the click-to-detail handler on the newly rendered cards
    list.querySelectorAll('.race-card[data-date]').forEach(card => {
      card.addEventListener('click', () => window.__openRaceDetail && window.__openRaceDetail(card.dataset.date));
      card.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          window.__openRaceDetail && window.__openRaceDetail(card.dataset.date);
        }
      });
    });
  }

  tabs.forEach(tab => tab.addEventListener('click', () => {
    activeCat = tab.dataset.tab;
    tabs.forEach(t => t.classList.toggle('active', t === tab));
    render();
  }));
  queryEl.addEventListener('input', render);
  clearEl.addEventListener('click', () => { queryEl.value = ''; render(); queryEl.focus(); });
  sortEl.addEventListener('change', render);
  distEl.addEventListener('change', render);
  prOnlyEl.addEventListener('change', render);

  render();
})();

// ─── Heatmap mode toggle ────────────────────────────────────────────────────
function accentColor() {
  return getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#58a6ff';
}
document.querySelectorAll('.hm-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.mode;
    document.querySelectorAll('.hm-toggle').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const accent = accentColor();
    document.querySelectorAll('.hm-cell').forEach(cell => {
      if (cell.classList.contains('hm-rest')) return;
      const tcol = cell.dataset.typeColor;
      const top  = cell.dataset.typeOp;
      const iop  = cell.dataset.intOp;
      if (mode === 'type') {
        cell.setAttribute('fill', tcol);
        cell.setAttribute('fill-opacity', top);
      } else {
        cell.setAttribute('fill', accent);
        cell.setAttribute('fill-opacity', iop);
      }
    });
    document.querySelectorAll('.hm-legend').forEach(l => {
      l.hidden = (l.dataset.mode !== mode);
    });
  });
});

// ─── Note row → highlight calendar cell ─────────────────────────────────────
function flashHeatmapCell(dateStr) {
  if (!dateStr) return;
  const cell = document.querySelector('.hm-cell[data-date="' + dateStr + '"]');
  if (!cell) return;
  // Scroll the heatmap card so the cell is visible
  const card = cell.closest('.heatmap-card');
  if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  cell.classList.remove('hm-flash');
  void cell.getBoundingClientRect();  // force reflow so the animation can replay
  cell.classList.add('hm-flash');
  setTimeout(() => cell.classList.remove('hm-flash'), 1600);
}

// ─── Notes search ───────────────────────────────────────────────────────────
(function() {
  const dataEl = document.getElementById('notes-data');
  if (!dataEl) return;
  const notes = JSON.parse(dataEl.textContent);
  const list  = document.getElementById('notes-list');
  const count = document.getElementById('notes-count');
  const input = document.getElementById('notes-query');
  const clear = document.getElementById('notes-clear');
  let activeFilter = 'all';
  const TYPE_LABELS = {easy:'Easy', long:'Long', tempo:'Tempo', workout:'Workout', race:'Race'};
  const TYPE_COLORS = {easy:'#2dd4bf', long:'#a78bfa', tempo:'#f59e0b', workout:'#60a5fa', race:'#f87171'};

  function escape(s) { return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function highlight(s, q) {
    if (!q) return escape(s);
    const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    return escape(s).replace(re, m => '<mark>' + m + '</mark>');
  }

  function render() {
    const q = input.value.trim();
    const ql = q.toLowerCase();
    const filtered = notes.filter(n =>
      (activeFilter === 'all' || n.type === activeFilter) &&
      (!ql || n.note.toLowerCase().includes(ql) || (n.race_name || '').toLowerCase().includes(ql))
    );
    count.textContent = filtered.length + (filtered.length === 1 ? ' note' : ' notes');
    list.innerHTML = filtered.map((n, i) => {
      const milesText = n.miles ? n.miles.toFixed(1) + ' mi' : (n.race ? 'race' : '—');
      const typeColor = TYPE_COLORS[n.type] || '#58a6ff';
      return `<div class="note-row" data-i="${i}">
        <span class="type-badge" style="--badge-color:${typeColor}">${TYPE_LABELS[n.type]}</span>
        <span class="note-date">${n.date}</span>
        <span class="note-miles">${milesText}</span>
        <span class="note-text">${highlight(n.note, q)}</span>
        <span class="chev">▾</span>
      </div>`;
    }).join('');
    list.querySelectorAll('.note-row').forEach(row => {
      row.addEventListener('click', () => {
        row.classList.toggle('expanded');
        const dateEl = row.querySelector('.note-date');
        if (dateEl) flashHeatmapCell(dateEl.textContent.trim());
      });
    });
    clear.hidden = !q;
  }

  input.addEventListener('input', render);
  clear.addEventListener('click', () => { input.value = ''; render(); input.focus(); });
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      activeFilter = pill.dataset.type;
      render();
    });
  });
  render();
})();

// ─── Cross-chart date sync ──────────────────────────────────────────────────
var DATE_CHART_IDS = ["chart-cumulative","chart-weekly","chart-easy-pace","chart-pace-timeline","chart-pr-800m","chart-pr-mile","chart-pr-3k-steeple","chart-pr-5k-track","chart-pr-5k-xc"];
var syncing = false;
function syncDateRange(sourceId, eventdata) {
  if (syncing) return;
  var x0 = eventdata['xaxis.range[0]'];
  var x1 = eventdata['xaxis.range[1]'];
  var autorange = eventdata['xaxis.autorange'];
  if (x0 === undefined && x1 === undefined && !autorange) return;
  syncing = true;
  var promises = DATE_CHART_IDS.filter(id => id !== sourceId).map(id => {
    var el = document.getElementById(id);
    if (!el || !el._fullLayout) return Promise.resolve();
    if (autorange) return Plotly.relayout(el, {'xaxis.autorange': true});
    var upd = {};
    if (x0 !== undefined) upd['xaxis.range[0]'] = x0;
    if (x1 !== undefined) upd['xaxis.range[1]'] = x1;
    return Plotly.relayout(el, upd);
  });
  Promise.all(promises).finally(() => { syncing = false; });
}
DATE_CHART_IDS.forEach(id => {
  var el = document.getElementById(id);
  if (el && el.on) el.on('plotly_relayout', ev => syncDateRange(id, ev));
});

// ─── Click-to-detail panel ──────────────────────────────────────────────────
(function() {
  var dataEl = document.getElementById('day-index');
  var DAY_INDEX = dataEl ? JSON.parse(dataEl.textContent) : {};
  var TYPE_COLORS_D = {easy:'#2dd4bf', long:'#a78bfa', tempo:'#f59e0b', workout:'#60a5fa', race:'#f87171'};
  var TYPE_LABELS_D = {easy:'Easy', long:'Long', tempo:'Tempo', workout:'Workout', race:'Race'};

  var panel = document.getElementById('detail-panel');
  var backdrop = document.getElementById('detail-backdrop');
  var dateEl = document.getElementById('detail-date');
  var body = document.getElementById('detail-body');
  if (!panel) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function fmtPace(p) {
    var f = parseFloat(p);
    if (!f || isNaN(f)) return '';
    var m = Math.floor(f);
    var s = Math.round((f - m) * 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
  }
  function fmtLongDate(ds) {
    var d = new Date(ds + 'T00:00:00');
    if (isNaN(d.getTime())) return ds;
    return d.toLocaleDateString('en-US', {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'});
  }
  function renderEntry(e) {
    var color = TYPE_COLORS_D[e.type] || '#58a6ff';
    var label = TYPE_LABELS_D[e.type] || (e.type_raw || 'Workout');
    var statsBits = [];
    if (e.miles)   statsBits.push('<span><span class="detail-stat-val">' + e.miles.toFixed(1) + '</span> mi</span>');
    if (e.pace)    statsBits.push('<span><span class="detail-stat-val">' + fmtPace(e.pace) + '</span> /mi</span>');
    if (e.minutes) statsBits.push('<span><span class="detail-stat-val">' + Math.round(e.minutes) + '</span> min</span>');
    var stats = statsBits.length ? '<div class="detail-stats">' + statsBits.join('') + '</div>' : '';
    var race = '';
    if (e.is_race) {
      var parts = [];
      if (e.race)      parts.push('<strong>' + esc(e.race) + '</strong>');
      if (e.race_dist) parts.push(esc(e.race_dist));
      if (e.race_time) parts.push(esc(e.race_time));
      race = '<div class="detail-race-info">' + parts.join(' · ') + '</div>';
    }
    var typeRawDiff = e.type_raw && e.type_raw.toLowerCase() !== label.toLowerCase()
      ? '<span style="color:var(--text-tertiary);font-size:12px;font-family:\'Geist Mono\',monospace">' + esc(e.type_raw) + '</span>'
      : '';
    return (
      '<div class="detail-entry">' +
        '<div class="detail-entry-head">' +
          '<span class="detail-type-badge" style="--badge-color:' + color + '">' + esc(label) + '</span>' +
          typeRawDiff +
        '</div>' +
        stats + race +
        (e.comments ? '<div class="detail-comments">' + esc(e.comments) + '</div>' : '') +
        (e.extras ? '<div class="detail-extras">Extras: ' + esc(e.extras) + '</div>' : '') +
      '</div>'
    );
  }
  function openDetail(dateStr) {
    if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return;
    var entries = DAY_INDEX[dateStr] || [];
    dateEl.textContent = fmtLongDate(dateStr);
    body.innerHTML = entries.length
      ? entries.map(renderEntry).join('')
      : '<div class="detail-empty">No entry recorded for this day.</div>';
    panel.classList.add('open');
    panel.setAttribute('aria-hidden', 'false');
    backdrop.classList.add('open');
  }
  function closeDetail() {
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden', 'true');
    backdrop.classList.remove('open');
  }

  document.getElementById('detail-close').addEventListener('click', closeDetail);
  backdrop.addEventListener('click', closeDetail);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

  // Plotly chart points → detail panel
  ['chart-cumulative','chart-easy-pace','chart-pace-timeline','chart-pr-800m','chart-pr-mile','chart-pr-3k-steeple','chart-pr-5k-track','chart-pr-5k-xc'].forEach(id => {
    var el = document.getElementById(id);
    if (el && el.on) {
      el.on('plotly_click', ev => {
        if (!ev.points || !ev.points.length) return;
        var pt = ev.points[0];
        var x = typeof pt.x === 'string' ? pt.x : null;
        if (x && /^\d{4}-\d{2}-\d{2}$/.test(x)) openDetail(x);
      });
    }
  });

  // Heatmap cells (rest days are excluded by [data-date] selector)
  document.querySelectorAll('.hm-cell[data-date]').forEach(cell => {
    cell.addEventListener('click', () => openDetail(cell.dataset.date));
  });

  // Race cards are rendered client-side; expose openDetail so the Races
  // module can wire each card after each re-render.
  window.__openRaceDetail = openDetail;

  // Bottom-sheet swipe-to-dismiss (mobile only)
  (function() {
    var sy = 0, drag = false;
    panel.addEventListener('touchstart', function(e) {
      if (!window.matchMedia('(max-width:640px)').matches) return;
      sy = e.touches[0].clientY; drag = true;
    }, {passive: true});
    panel.addEventListener('touchmove', function(e) {
      if (!drag) return;
      var dy = e.touches[0].clientY - sy;
      if (dy > 0) panel.style.transform = 'translateY(' + dy + 'px)';
    }, {passive: true});
    panel.addEventListener('touchend', function(e) {
      if (!drag) return;
      drag = false;
      var dy = e.changedTouches[0].clientY - sy;
      if (dy > 80) {
        panel.style.transform = 'translateY(100%)';
        setTimeout(function() { panel.style.transform = ''; closeDetail(); }, 240);
      } else {
        panel.style.transform = '';
      }
    });
  })();
})();

// ─── Chart toggle (per-chart y-data switcher) ──────────────────────────────
(function() {
  function applyToggle(toggle, mode) {
    var target = toggle.dataset.toggleTarget;
    var gd = document.getElementById(target);
    if (!gd || !window.Plotly) return;
    var key = mode === 'pct' ? 'pct' : 'miles';
    var ys = JSON.parse(toggle.dataset[key]);
    Plotly.restyle(gd, { y: ys });
    Plotly.relayout(gd, {
      'yaxis.title.text': key === 'pct' ? '% of Season Miles' : 'Miles',
    });
    toggle.querySelectorAll('button').forEach(function(b) {
      b.classList.toggle('active', b.dataset.mode === key);
    });
  }
  document.querySelectorAll('.chart-toggle').forEach(function(toggle) {
    toggle.querySelectorAll('button').forEach(function(b) {
      b.addEventListener('click', function() { applyToggle(toggle, b.dataset.mode); });
    });
  });
})();

// ─── Theme toggle (light / dark / system) ───────────────────────────────────
(function() {
  var root = document.documentElement;
  var mq = window.matchMedia('(prefers-color-scheme: light)');
  var STORAGE_KEY = 'theme';

  function getStoredMode() {
    var v = localStorage.getItem(STORAGE_KEY);
    return (v === 'light' || v === 'dark' || v === 'system') ? v : 'system';
  }
  function effectiveTheme(mode) {
    if (mode === 'system') return mq.matches ? 'light' : 'dark';
    return mode;
  }
  function cssVar(name) {
    return getComputedStyle(root).getPropertyValue(name).trim();
  }
  function applyChartTheme() {
    var textPrimary   = cssVar('--text-primary');
    var textSecondary = cssVar('--text-secondary');
    var textTertiary  = cssVar('--text-tertiary');
    var grid          = cssVar('--grid');
    var bgElevated    = cssVar('--bg-elevated');
    var border        = cssVar('--border');
    var upd = {
      'xaxis.tickfont.color': textTertiary,
      'yaxis.tickfont.color': textTertiary,
      'xaxis.title.font.color': textSecondary,
      'yaxis.title.font.color': textSecondary,
      'xaxis.gridcolor': grid,
      'yaxis.gridcolor': grid,
      'xaxis.zerolinecolor': grid,
      'yaxis.zerolinecolor': grid,
      'font.color': textSecondary,
      'legend.font.color': textSecondary,
      'hoverlabel.font.color': textPrimary,
      'hoverlabel.bgcolor': bgElevated,
      'hoverlabel.bordercolor': border,
    };
    document.querySelectorAll('.plotly-graph-div').forEach(function(el) {
      if (el && el._fullLayout && window.Plotly) {
        try { Plotly.relayout(el, upd); } catch (e) { /* chart may not be ready */ }
      }
    });
  }
  function setActiveButton(mode) {
    document.querySelectorAll('.theme-toggle button').forEach(function(b) {
      b.classList.toggle('active', b.dataset.theme === mode);
    });
  }
  function applyTheme(mode) {
    var eff = effectiveTheme(mode);
    root.classList.toggle('light', eff === 'light');
    setActiveButton(mode);
    applyChartTheme();
  }

  var current = getStoredMode();
  applyTheme(current);

  document.querySelectorAll('.theme-toggle button').forEach(function(b) {
    b.addEventListener('click', function() {
      current = b.dataset.theme;
      localStorage.setItem(STORAGE_KEY, current);
      applyTheme(current);
    });
  });

  mq.addEventListener('change', function() {
    if (current === 'system') applyTheme('system');
  });
})();

// ─── Mobile: re-fit charts, thin crowded axes, simplify ─────────────────────
(function() {
  var mq = window.matchMedia('(max-width:640px)');
  // Dense time/numeric charts: thin ticks to ~1 per 100px (x) / 80px (y).
  // Categorical charts (mix-by-season, monthly-by-year) are excluded — nticks
  // can drop their category labels.
  var DENSE = ['chart-cumulative', 'chart-weekly', 'chart-easy-pace',
               'chart-pace-timeline', 'chart-5k-prog'];
  function thinTicks() {
    if (!window.Plotly) return;
    var mobile = mq.matches;
    DENSE.forEach(function(id) {
      var el = document.getElementById(id);
      if (!el || !el._fullLayout) return;
      var w = el.clientWidth || 0, h = el.clientHeight || 0;
      if (w === 0) return;  // hidden view — recomputed on activation
      var nx = mobile ? Math.max(2, Math.floor(w / 100)) : 0;  // 0 = auto
      var ny = mobile ? Math.max(2, Math.floor(h / 80)) : 0;
      Plotly.relayout(el, {'xaxis.nticks': nx, 'yaxis.nticks': ny});
    });
  }
  window.__thinTicks = thinTicks;
  function simplify(mobile) {
    if (!window.Plotly) return;
    var pt = document.getElementById('chart-pace-timeline');
    if (pt && pt._fullLayout) Plotly.relayout(pt, {'showlegend': !mobile});
    var mby = document.getElementById('chart-monthly-by-year');
    if (mby && mby._fullLayout) Plotly.relayout(mby, {'showlegend': !mobile});
    var mix = document.getElementById('chart-mix-by-season');
    if (mix && mix._fullLayout) Plotly.relayout(mix, {'xaxis.nticks': mobile ? 6 : 0});
  }
  function applyMobile() { simplify(mq.matches); thinTicks(); }
  // Debounced resize → re-fit active charts, then re-thin ticks for new width.
  var t;
  function onResize() {
    clearTimeout(t);
    t = setTimeout(function() {
      if (!window.Plotly) return;
      document.querySelectorAll('.view.active .js-plotly-plot').forEach(function(el) {
        Plotly.Plots.resize(el);
      });
      thinTicks();
    }, 150);
  }
  window.addEventListener('resize', onResize);
  if (window.visualViewport) window.visualViewport.addEventListener('resize', onResize);
  mq.addEventListener('change', applyMobile);
  applyMobile();
})();
"""
