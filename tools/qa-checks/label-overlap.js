(function() {
  function ix(a, b) {
    var x = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
    var y = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    return x * y;
  }
  var results = [];
  document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
    if (el.offsetParent === null) return;            // skip charts on hidden tabs
    var id = el.id || 'unnamed';

    // 1. data-mark rects: scatter/box/bar points...
    var marks = [];
    el.querySelectorAll('.scatterlayer .point, .barlayer .point, .boxlayer .point, .violinlayer path.violin')
      .forEach(function(p) {
        var r = p.getBoundingClientRect();
        if (r.width || r.height) marks.push(r);
      });
    // ...plus points sampled along line traces
    el.querySelectorAll('.scatterlayer .js-line').forEach(function(path) {
      var L = path.getTotalLength ? path.getTotalLength() : 0;
      var m = path.getScreenCTM();
      if (!L || !m) return;
      var step = Math.max(6, L / 150);
      for (var d = 0; d <= L; d += step) {
        var pt = path.getPointAtLength(d);
        var sx = m.a * pt.x + m.c * pt.y + m.e;
        var sy = m.b * pt.x + m.d * pt.y + m.f;
        marks.push({left: sx - 2, right: sx + 2, top: sy - 2, bottom: sy + 2});
      }
    });

    // 2. label rects: legend + every annotation
    var labels = [];
    var lg = el.querySelector('.legend');
    if (lg) labels.push({kind: 'legend', r: lg.getBoundingClientRect()});
    el.querySelectorAll('.infolayer .annotation').forEach(function(a, i) {
      labels.push({
        kind: 'annotation[' + i + '] "' + a.textContent.trim().slice(0, 40) + '"',
        r: a.getBoundingClientRect()
      });
    });

    // 2b. tick-label collisions, tracked separately from the legend/annotation
    // verdict: crowded ticks collide with each other long before anything
    // touches the legend, and a wall of tick rows would bury that signal. This
    // is what thinTicks()/DENSE in template.py exist to prevent, and nothing
    // verified their result until now.
    //
    // A bounding-box test is WRONG here. Plotly auto-rotates crowded ticks (30
    // degrees is common) and getBoundingClientRect returns the AXIS-ALIGNED box
    // of rotated text, which hugely overstates overlap: 30-degree "Jul 2003" /
    // "Jan 2004" labels 22px apart report 47x34 boxes "52% overlapping" while
    // reading perfectly. Rotation is the FIX for crowding, so an AABB test
    // flags every fix as a defect.
    //
    // Model tick labels as what they are -- parallel text runs along one axis:
    //   unrotated: collide when along-axis extents overlap
    //   rotated:   adjacent baselines sit (spacing * |sin angle|) apart
    //              perpendicular to the text, so collide when that gap drops
    //              below the line height
    var tickTick = [];
    function rotOf(t) {
      var m = /rotate\(\s*(-?[\d.]+)/.exec(t.getAttribute('transform') || '');
      return m ? parseFloat(m[1]) : 0;
    }
    function tickRun(sel, kind, axis) {
      var items = [];
      el.querySelectorAll(sel).forEach(function (t, i) {
        var r = t.getBoundingClientRect();
        var txt = (t.textContent || '').trim();
        if ((!r.width && !r.height) || !txt) return;
        var fs = parseFloat(getComputedStyle(t).fontSize) || 10;
        items.push({
          label: kind + '[' + i + '] "' + txt.slice(0, 20) + '"',
          c: axis === 'x' ? r.left + r.width / 2 : r.top + r.height / 2,
          extent: axis === 'x' ? r.width : r.height,
          lineH: fs * 1.15,
          angle: Math.abs(rotOf(t)) % 180
        });
      });
      items.sort(function (a, b) { return a.c - b.c; });
      for (var k = 0; k + 1 < items.length; k++) {
        var A = items[k], B = items[k + 1];
        var d = Math.abs(B.c - A.c);
        var hit = null;
        if (A.angle < 5 || A.angle > 175) {
          var need = (A.extent + B.extent) / 2;
          if (d < need * 0.85)
            hit = {gapPx: +d.toFixed(1), needPx: +need.toFixed(1), rotated: false,
                   frac: +(1 - d / Math.max(1, need)).toFixed(2)};
        } else {
          var perp = d * Math.abs(Math.sin(A.angle * Math.PI / 180));
          if (perp < A.lineH * 0.85)
            hit = {gapPx: +perp.toFixed(1), needPx: +A.lineH.toFixed(1),
                   rotated: true, angle: +A.angle.toFixed(0),
                   frac: +(1 - perp / Math.max(1, A.lineH)).toFixed(2)};
        }
        if (hit) { hit.a = A.label; hit.b = B.label; tickTick.push(hit); }
      }
      return items.length;
    }
    var nTicks = tickRun('.xtick text', 'xtick', 'x') +
                 tickRun('.ytick text', 'ytick', 'y');

    // 3. label-vs-data and label-vs-label intersections
    var labelData = [], labelLabel = [];
    labels.forEach(function(lab) {
      var hits = 0, px = 0;
      marks.forEach(function(mr) { var o = ix(lab.r, mr); if (o > 0) { hits++; px += o; } });
      if (hits > 0) labelData.push({label: lab.kind, marksHit: hits, overlapPx: Math.round(px)});
    });
    for (var i = 0; i < labels.length; i++)
      for (var j = i + 1; j < labels.length; j++) {
        var o = ix(labels[i].r, labels[j].r);
        if (o > 25) labelLabel.push({a: labels[i].kind, b: labels[j].kind, overlapPx: Math.round(o)});
      }

    results.push({
      id: id,
      labelData: labelData,
      labelLabel: labelLabel,
      tickTick: tickTick.slice(0, 8),
      tickCount: nTicks,
      status: (labelData.some(function(d) { return d.marksHit >= 3 || d.overlapPx > 200; })
               || labelLabel.length > 0) ? 'CHECK' : 'OK',
      tickStatus: tickTick.length ? 'CHECK' : 'OK'
    });
  });
  return JSON.stringify(results, null, 2);
})()
