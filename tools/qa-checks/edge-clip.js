(function() {
  var out = [];
  document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
    if (el.offsetParent === null) return;                 // visible charts only
    var svg = el.querySelector('svg.main-svg'); if (!svg) return;
    var sv = svg.getBoundingClientRect();                 // the clip viewport
    el.querySelectorAll('.infolayer .annotation').forEach(function(a, i) {
      var t = a.querySelector('text');
      var txt = (t ? t.textContent : a.textContent).trim();
      var r = a.getBoundingClientRect(); if (!r.width && !r.height) return;
      var over = {left: Math.round(sv.left - r.left), right: Math.round(r.right - sv.right),
                  top: Math.round(sv.top - r.top),    bottom: Math.round(r.bottom - sv.bottom)};
      var sides = Object.keys(over).filter(function(k) { return over[k] > 2; }); // >2px = clipped
      if (sides.length) {
        var vl = Math.max(r.left, sv.left), vr = Math.min(r.right, sv.right),
            vt = Math.max(r.top, sv.top),   vb = Math.min(r.bottom, sv.bottom);
        var hidden = Math.round((1 - (Math.max(0, vr - vl) * Math.max(0, vb - vt)) /
                                 (r.width * r.height)) * 100);
        out.push({chart: el.id, ann: i, text: txt.slice(0, 45),
                  clippedSides: sides, overflowPx: over, hiddenPct: hidden});
      }
    });
  });
  return JSON.stringify({clippedCount: out.length, items: out}, null, 2);
})()
