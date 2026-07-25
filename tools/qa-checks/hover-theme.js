// V7 - hover/datatip theme mismatch.
//
// The contrast audit (V5) CANNOT catch this class of bug. A dark hover pill
// surviving into light mode holds LIGHT text on a DARK background, which scores
// high contrast and passes V5 cleanly while looking obviously wrong. The defect
// is a theme *mismatch*, not a legibility failure, so it needs a different
// instrument: compare each surface's background luminance against the page's.
//
// It also needs a hover to exist at all. Plotly builds .hoverlayer .hovertext
// only in response to a hover, so nothing in the DOM reveals this at rest --
// which is why both QA agents missed it entirely. Hover is triggered through
// Plotly.Fx.hover() rather than a synthetic mousemove: Plotly listens on its
// drag layer and a dispatched event is unreliable, especially under touch
// emulation.
//
// Run once per theme. Async: returns a Promise, so it needs a transport that
// awaits (mobile_preview.py / page.evaluate does; check before using on T1).
(async function () {
  function lum(c) {
    var m = (c || '').match(/rgba?\(([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s]+([\d.]+))?/);
    if (!m) return null;
    if (m[4] !== undefined && parseFloat(m[4]) === 0) return null;   // transparent
    var f = [m[1], m[2], m[3]].map(function (v) {
      v = parseFloat(v) / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
  }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  var pageLum = lum(getComputedStyle(document.body).backgroundColor);
  var theme = document.documentElement.classList.contains('light') ? 'light' : 'dark';
  // A surface is "inverted" when it sits on the wrong side of mid-grey for the
  // current theme: a dark pill on a light page, or vice versa.
  var MID = 0.18;
  function verdict(surfaceLum) {
    if (surfaceLum === null || pageLum === null) return null;
    if (theme === 'light' && pageLum > 0.3 && surfaceLum < MID) return 'DARK-IN-LIGHT';
    if (theme === 'dark' && pageLum < 0.3 && surfaceLum > 0.5) return 'LIGHT-IN-DARK';
    return null;
  }

  var rows = [];
  var charts = [].slice.call(document.querySelectorAll('.js-plotly-plot'))
                 .filter(function (el) { return el.offsetParent !== null && el._fullLayout; });

  for (var i = 0; i < charts.length; i++) {
    var el = charts[i];
    var row = {chart: el.id, theme: theme, status: 'OK'};

    // --- hover pill -----------------------------------------------------
    var hovered = false;
    try {
      var tr = (el.data || []).find(function (t) {
        return t.visible !== false && t.visible !== 'legendonly' &&
               ((t.x && t.x.length) || (t.values && t.values.length));
      });
      if (tr && window.Plotly && Plotly.Fx) {
        var ci = (el.data || []).indexOf(tr);
        var pn = Math.min(1, (tr.x ? tr.x.length : 1) - 1);
        Plotly.Fx.hover(el, [{curveNumber: ci, pointNumber: Math.max(0, pn)}]);
        hovered = true;
      }
    } catch (e) { row.hoverError = String(e).slice(0, 120); }

    if (hovered) {
      await sleep(90);
      var ht = el.querySelector('.hoverlayer .hovertext');
      if (ht) {
        var pill = ht.querySelector('path, rect');
        var txt = ht.querySelector('text');
        var pl = pill ? lum(getComputedStyle(pill).fill) : null;
        var tl = txt ? lum(getComputedStyle(txt).fill) : null;
        row.hoverPillFill = pill ? getComputedStyle(pill).fill : null;
        row.hoverTextFill = txt ? getComputedStyle(txt).fill : null;
        row.hoverPillLum = pl === null ? null : +pl.toFixed(3);
        var v = verdict(pl);
        if (v) {
          row.status = 'FAIL';
          row.why = 'datatip background is ' + v + ' (pill lum ' +
                    (pl === null ? '?' : pl.toFixed(3)) + ' vs page ' +
                    pageLum.toFixed(3) + ') - applyChartTheme() is not ' +
                    'restyling hoverlabel for this chart';
        }
      } else {
        row.hoverPillFill = null;
        row.note = 'no .hovertext produced (chart may not support hover)';
      }
      try { Plotly.Fx.unhover(el); } catch (e) { /* best effort */ }
    }

    // --- annotation pills + chart title: same failure mode ---------------
    var others = [];
    el.querySelectorAll('.infolayer .annotation rect.bg').forEach(function (r) {
      var l = lum(getComputedStyle(r).fill);
      var v = verdict(l);
      if (v) others.push({kind: 'annotation-pill', lum: +l.toFixed(3), verdict: v});
    });
    var title = el.querySelector('.infolayer .g-gtitle text, .gtitle');
    if (title) {
      var tlum = lum(getComputedStyle(title).fill);
      // A title is text, not a surface: it must CONTRAST the page, so the
      // inverted test is reversed - a dark title on a dark page is the bug.
      if (tlum !== null && pageLum !== null) {
        var same = (theme === 'dark' && tlum < 0.1) || (theme === 'light' && tlum > 0.6);
        if (same) others.push({kind: 'chart-title', lum: +tlum.toFixed(3),
                               verdict: 'TITLE-MATCHES-BACKGROUND'});
      }
    }
    if (others.length) {
      row.status = 'FAIL';
      row.others = others;
      row.why = (row.why ? row.why + '; ' : '') +
                others.length + ' non-hover surface(s) mis-themed';
    }

    rows.push(row);
  }

  return JSON.stringify({
    theme: theme, pageLum: pageLum === null ? null : +pageLum.toFixed(3),
    checked: rows.length,
    fail: rows.filter(function (r) { return r.status === 'FAIL'; }).length,
    hovered: rows.filter(function (r) { return r.hoverPillFill; }).length,
    rows: rows
  }, null, 1);
})()
