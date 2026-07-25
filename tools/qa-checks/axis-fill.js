// V6 - axis-range blowout, plot-area fill, and legend presence.
//
// Catches the failure CLAUDE.md documents under "Plotly charts - mobile-safe
// authoring": chart chrome anchored in DATA coordinates (direct labels,
// add_vrect annotation pills, any xref="x" annotation whose text runs past the
// data) forces Plotly's autorange to widen the axis so the text stays on
// canvas. On a ~300px mobile plot the widening is proportionally huge -- a
// 2003-2007 x-axis silently stretched to ~2010, a category axis stretched from
// [-0.5, 11.5] to [-0.5, 17.35] -- compressing the data into the left ~60% of
// the card while looking fine on desktop.
//
// V4 (width-fill) does NOT catch this: the figure still fills its card at 100%.
// The defect is inside the figure, in the axis range, so it has to be measured
// against the actual data extent.
//
// Only AUTORANGED axes can FAIL here. Pinning an explicit `range=` is the
// prescribed fix for this bug, and several charts legitimately pin a range
// WIDER than their own data so a set of small-multiples shares one x-axis
// (running-log's PR charts share _PR_X_RANGE for exactly that reason). Flagging
// those would flag the fix as the defect, so a pinned axis reports "PINNED"
// with its numbers for information and never fails.
//
// Returns one row per visible chart. Charts with no cartesian x-axis (donuts,
// sparklines, heatmaps, maps) report axis:"n/a" and are skipped, not failed.
(function () {
  var TOL_FRAC = 0.15;   // date/linear: allowed padding past the data, as a
                         // fraction of the data span (Plotly's own default
                         // padding is well under this)
  var TOL_CAT = 0.6;     // category: allowed slack beyond [-0.5, n-0.5]
  // Plot-area floor, calibrated against both dashboards at 375px rather than
  // guessed: a labelled mobile chart bottoms out around 0.59 (a ~65px left
  // margin for "5:30"-style tick text on a ~297px figure is unavoidable), and
  // typical charts sit at 0.70-0.76. 0.55 therefore flags only charts paying
  // for something extra -- the dual-axis (secondary_y) case where a wide
  // margin.r squeezes the plot -- instead of warning on every mobile chart.
  var MIN_PLOT_FRAC = 0.55;

  function num(v) {
    if (v === null || v === undefined) return null;
    if (typeof v === 'number') return isFinite(v) ? v : null;
    var t = Date.parse(v);
    if (!isNaN(t)) return t;
    var f = parseFloat(v);
    return isNaN(f) ? null : f;
  }

  // Collapse the three independent verdicts into one, worst-first. PINNED is
  // informational (a deliberate author choice), so it ranks below WARN.
  var RANK = {OK: 0, PINNED: 1, WARN: 2, FAIL: 3};
  function finish(row, notes) {
    var worst = 'OK';
    [row.axisStatus, row.plotStatus, row.legendStatus].forEach(function (s) {
      if (RANK[s] > RANK[worst]) worst = s;
    });
    row.status = worst;
    if (notes.length) row.why = notes.join('; ');
    out.push(row);
  }

  var out = [];
  document.querySelectorAll('.js-plotly-plot').forEach(function (el) {
    if (el.offsetParent === null) return;              // visible charts only
    var fl = el._fullLayout;
    if (!fl) { out.push({chart: el.id, status: 'FAIL', why: 'not-rendered'}); return; }

    var xa = fl.xaxis;
    // Three independent verdicts. Keeping them separate matters: a plot-area
    // warning must not mask an axis finding on the same chart (or vice versa).
    // `status` is the worst of the three.
    var row = {chart: el.id, axisStatus: 'OK', plotStatus: 'OK', legendStatus: 'OK'};
    var notes = [];

    // ---- plot-area fill: margins eating the card -------------------------
    var size = fl._size;
    if (size && fl.width) {
      row.figurePx = Math.round(fl.width);
      row.plotPx = Math.round(size.w);
      row.plotFrac = +(size.w / fl.width).toFixed(3);
      row.margins = {l: size.l, r: size.r, t: size.t, b: size.b};
      if (row.plotFrac < MIN_PLOT_FRAC) {
        row.plotStatus = 'WARN';
        notes.push('plot area only ' + Math.round(row.plotFrac * 100) +
                   '% of figure width (margins l=' + size.l + ' r=' + size.r +
                   '); on a dual-axis chart set automargin=True rather than a ' +
                   'wide fixed margin.r');
      }
    }

    // ---- legend presence -------------------------------------------------
    // Catches the stale-simplify() failure: page JS forcing showlegend off for
    // a chart whose redesign now needs its legend.
    row.showlegend = !!fl.showlegend;
    row.legendInDom = !!el.querySelector('.legend');
    if (fl.showlegend && !row.legendInDom) {
      row.legendStatus = 'FAIL';
      notes.push('showlegend true but no .legend node rendered');
    }

    // ---- axis range vs data extent --------------------------------------
    if (!xa || !xa.range) { row.axis = 'n/a'; finish(row, notes); return; }
    row.axis = xa.type || 'unknown';
    row.xRange = xa.range;
    // autorange false => the author pinned the range on purpose.
    row.autoranged = xa.autorange !== false;

    if (xa.type === 'category' || xa.type === 'multicategory') {
      var ncats = (xa._categories && xa._categories.length) ||
                  (xa.categoryarray && xa.categoryarray.length) || 0;
      if (!ncats) { finish(row, notes); return; }
      row.nCategories = ncats;
      var lo = num(xa.range[0]), hi = num(xa.range[1]);
      row.expected = [-0.5, ncats - 0.5];
      if (lo === null || hi === null) { finish(row, notes); return; }
      var over = Math.max(lo - (-0.5) < 0 ? -0.5 - lo : 0, hi - (ncats - 0.5));
      row.overrun = +over.toFixed(2);
      if (over > TOL_CAT) {
        if (row.autoranged) {
          row.axisStatus = 'FAIL';
          notes.push('category axis widened ' + over.toFixed(2) +
                    ' beyond [-0.5,' + (ncats - 0.5) + '] - data compressed into ' +
                    Math.round(ncats / (hi - lo) * 100) + '% of the plot');
        } else {
          row.axisStatus = 'PINNED';
          notes.push('explicit range wider than data (deliberate); overrun ' +
                     over.toFixed(2));
        }
      }
      finish(row, notes);
      return;
    }

    // date / linear: compare against the plotted data extent
    var dmin = null, dmax = null;
    (el.data || []).forEach(function (tr) {
      if (tr.visible === false || tr.visible === 'legendonly') return;
      var xs = tr.x;
      if (!xs || !xs.length) return;
      for (var i = 0; i < xs.length; i++) {
        var v = num(xs[i]);
        if (v === null) continue;
        if (dmin === null || v < dmin) dmin = v;
        if (dmax === null || v > dmax) dmax = v;
      }
    });
    if (dmin === null || dmax === null) { row.axis += ' (no x data)'; finish(row, notes); return; }

    var r0 = num(xa.range[0]), r1 = num(xa.range[1]);
    if (r0 === null || r1 === null) { finish(row, notes); return; }
    if (r1 < r0) { var t = r0; r0 = r1; r1 = t; }        // reversed axes (pace)

    // Guard divide-by-zero WITHOUT clamping to 1. A hard Math.max(1, span)
    // silently corrupts every sub-unit axis -- a partial-R^2 chart ranging
    // [0, 0.036] would report padFrac 0.002 instead of 0.081 and sail past the
    // tolerance, i.e. a false negative exactly where a blowout is subtlest.
    // Date axes (ms epoch, ~1e12) never noticed; small linear axes do.
    var span = (dmax - dmin) || Math.max(Math.abs(dmax), 1e-9);
    var axisSpan = (r1 - r0) || Math.max(Math.abs(r1), 1e-9);
    var padLo = (dmin - r0) / span;
    var padHi = (r1 - dmax) / span;
    row.dataExtent = [dmin, dmax];
    row.padFrac = {low: +padLo.toFixed(3), high: +padHi.toFixed(3)};
    row.dataFillFrac = +((dmax - dmin) / axisSpan).toFixed(3);

    if (padLo > TOL_FRAC || padHi > TOL_FRAC) {
      if (row.autoranged) {
        row.axisStatus = 'FAIL';
        notes.push('AUTORANGE BLOWOUT: axis overruns data by ' +
                  Math.round(Math.max(padLo, padHi) * 100) + '% of span - data ' +
                  'occupies only ' + Math.round(row.dataFillFrac * 100) +
                  '% of the axis. Move data-coordinate chart chrome to ' +
                  'xref="paper" and pin an explicit range=.');
      } else {
        row.axisStatus = 'PINNED';
        notes.push('explicit range wider than this chart\'s data (deliberate, ' +
                   'e.g. a shared range across small-multiples); data occupies ' +
                   Math.round(row.dataFillFrac * 100) + '% of the axis');
      }
    }
    finish(row, notes);
  });

  function count(s) {
    return out.filter(function (r) { return r.status === s; }).length;
  }
  return JSON.stringify({
    checked: out.length, fail: count('FAIL'), warn: count('WARN'),
    pinned: count('PINNED'), rows: out
  }, null, 1);
})()
