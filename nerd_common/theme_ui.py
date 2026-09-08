"""The light/dark/system theme control, shared by every page on the site.

The three pages (landing, college log, Strava) must agree on the localStorage
key or a visitor's theme choice evaporates as they navigate between them, so
the key and the pre-paint script live here rather than in any one page's
template.

`THEME_INIT_JS` is verbatim what both dashboards already inline in their
`<head>`; the toggle markup, CSS and click handler below are the landing page's
copies of the same three pieces. The dashboards still carry their own — theirs
are entangled with `applyChartTheme()`, which retints Plotly figures and has no
business here — and should adopt these when that untangling is worth doing.

Stdlib-only, like the rest of nerd_common.
"""

# Key read and written by all three pages. Changing it silently resets everyone.
STORAGE_KEY = "dns-theme"

# Runs synchronously in <head>, before first paint, so a light-theme visitor
# never sees a dark flash.
THEME_INIT_JS = """<script>
(function () {
  try {
    var K = 'dns-theme';
    var v = localStorage.getItem(K);
    if (v == null) {
      // Migrate from the old per-dashboard keys (same origin, shared storage).
      var old = localStorage.getItem('strava-theme') || localStorage.getItem('theme');
      if (old === 'light' || old === 'dark' || old === 'system') { v = old; localStorage.setItem(K, v); }
    }
    var mode = (v === 'light' || v === 'dark' || v === 'system') ? v : 'system';
    var light = mode === 'light' ||
      (mode === 'system' && window.matchMedia('(prefers-color-scheme: light)').matches);
    document.documentElement.classList.toggle('light', light);
  } catch (e) {}
})();
</script>"""

# The three-button segmented control. Identical glyphs to the dashboards' so the
# control doesn't visibly change shape as you move between pages.
THEME_TOGGLE_HTML = """<div class="theme-toggle" role="group" aria-label="Theme">
  <button type="button" data-theme="light" title="Light" aria-label="Light theme">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
  </button>
  <button type="button" data-theme="dark" title="Dark" aria-label="Dark theme">
    <svg viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/></svg>
  </button>
  <button type="button" data-theme="system" title="System" aria-label="Use system theme">
    <svg viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 21h8M12 18v3"/></svg>
  </button>
</div>"""

THEME_TOGGLE_CSS = """
.theme-toggle {
  display: inline-flex; align-items: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 2px;
  gap: 0;
}
.theme-toggle button {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 22px;
  background: transparent; border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 5px;
  padding: 0;
  transition: all 120ms cubic-bezier(0.16, 1, 0.3, 1);
}
.theme-toggle button:hover { color: var(--text-primary); }
.theme-toggle button.active { background: var(--accent-dim); color: var(--accent); }
.theme-toggle button svg {
  width: 13px; height: 13px; stroke: currentColor; fill: none;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}
@media (max-width: 640px) {
  .theme-toggle button { width: 36px; height: 36px; }
}
"""

# The dashboards' handler additionally calls applyChartTheme(); this one has no
# Plotly to retint, so it stops at the root class and the active-button state.
THEME_TOGGLE_JS = """
(function () {
  var root = document.documentElement;
  var mq = window.matchMedia('(prefers-color-scheme: light)');
  var STORAGE_KEY = 'dns-theme';

  function getStoredMode() {
    var v = localStorage.getItem(STORAGE_KEY);
    return (v === 'light' || v === 'dark' || v === 'system') ? v : 'system';
  }
  function effectiveTheme(mode) {
    if (mode === 'system') return mq.matches ? 'light' : 'dark';
    return mode;
  }
  function setActiveButton(mode) {
    document.querySelectorAll('.theme-toggle button').forEach(function (b) {
      b.classList.toggle('active', b.dataset.theme === mode);
    });
  }
  function applyTheme(mode) {
    root.classList.toggle('light', effectiveTheme(mode) === 'light');
    setActiveButton(mode);
  }

  var current = getStoredMode();
  applyTheme(current);

  document.querySelectorAll('.theme-toggle button').forEach(function (b) {
    b.addEventListener('click', function () {
      current = b.dataset.theme;
      try { localStorage.setItem(STORAGE_KEY, current); } catch (e) {}
      applyTheme(current);
    });
  });

  mq.addEventListener('change', function () {
    if (current === 'system') applyTheme('system');
  });
})();
"""
