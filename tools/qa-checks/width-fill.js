(function() {
  var out = [];
  document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
    if (el.offsetParent === null) return;                 // visible charts only
    var svg = el.querySelector('svg.main-svg'); if (!svg) return;
    var card = el.closest('.card');                        // the chart's container
    var host = card || el.parentElement;
    var cs = getComputedStyle(host);
    var inner = host.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    var chartW = svg.getBoundingClientRect().width;
    var fill = inner > 0 ? +(chartW / inner * 100).toFixed(1) : null;
    out.push({chart: el.id, chartPx: Math.round(chartW), cardPx: Math.round(inner),
              fillPct: fill, status: (fill !== null && fill < 90) ? 'FAIL' : 'OK'});
  });
  return JSON.stringify(out, null, 2);
})()
