// V8 - page-level element overlap, horizontal overflow, and tap-target size.
//
// Everything in V2-V7 is scoped to the inside of a chart's SVG. Nothing checked
// the PAGE: cards colliding, a stat tile running under the theme toggle, the
// tab strip overlapping content, or the document scrolling sideways. Those are
// the failures a narrow viewport produces first, and they were invisible to
// both QA agents.
//
// Overlap is judged between RENDERED SIBLINGS ONLY. Nesting is normal (a card
// contains its heading), and deliberate overlays (the detail sheet and its
// backdrop) are stacked on purpose, so both are excluded -- otherwise the
// output is a wall of true-but-useless intersections.
(function () {
  var GROUPS = [
    '.card', '.stat-card', '.pr-card', '.race-card',
    '.tab', '.theme-toggle', '.hm-toggle', '.race-tab',
    '.spark-card', '.section-head', '.wordmark'
  ];
  // Intentionally stacked / floating: never report these as collisions.
  var OVERLAY = ['#detail-panel', '.backdrop', '.sheet-backdrop', '.modal',
                 '.tooltip', '.hoverlayer'];
  var MIN_TAP = 40;          // px, per the mobile redesign plan
  var OVERLAP_PX = 24;       // ignore hairline touching from rounding

  function visible(el) {
    if (!el || el.offsetParent === null) return false;
    var cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' ||
        parseFloat(cs.opacity) === 0) return false;
    var r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  }
  function inOverlay(el) {
    for (var i = 0; i < OVERLAY.length; i++) if (el.closest(OVERLAY[i])) return true;
    return false;
  }
  function ix(a, b) {
    var x = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
    var y = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    return x * y;
  }
  function label(el) {
    return (el.tagName.toLowerCase() +
            (el.id ? '#' + el.id : '') +
            (el.className && typeof el.className === 'string'
              ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.')
              : '')).slice(0, 48);
  }

  var els = [];
  document.querySelectorAll(GROUPS.join(',')).forEach(function (el) {
    if (!visible(el) || inOverlay(el)) return;
    els.push({el: el, r: el.getBoundingClientRect()});
  });

  // --- pairwise overlap, siblings only ---------------------------------
  var overlaps = [];
  for (var i = 0; i < els.length; i++) {
    for (var j = i + 1; j < els.length; j++) {
      var A = els[i], B = els[j];
      if (A.el.contains(B.el) || B.el.contains(A.el)) continue;   // nesting is fine
      var o = ix(A.r, B.r);
      if (o <= OVERLAP_PX) continue;
      var smaller = Math.min(A.r.width * A.r.height, B.r.width * B.r.height);
      overlaps.push({a: label(A.el), b: label(B.el), overlapPx: Math.round(o),
                     fracOfSmaller: +(o / Math.max(1, smaller)).toFixed(3)});
    }
  }

  // --- horizontal overflow ---------------------------------------------
  var de = document.documentElement;
  var scrollW = de.scrollWidth, innerW = window.innerWidth;
  var overflow = {scrollWidth: scrollW, innerWidth: innerW,
                  overflowPx: scrollW - innerW};
  overflow.status = (scrollW - innerW) > 2 ? 'FAIL' : 'OK';
  // Name the widest offenders so the finding is actionable, not just "something".
  if (overflow.status === 'FAIL') {
    var wide = [];
    document.querySelectorAll('body *').forEach(function (el) {
      if (!visible(el)) return;
      var r = el.getBoundingClientRect();
      if (r.right > innerW + 2) wide.push({el: label(el), right: Math.round(r.right)});
    });
    wide.sort(function (x, y) { return y.right - x.right; });
    overflow.widest = wide.slice(0, 6);
  }

  // --- tap targets ------------------------------------------------------
  // Only meaningful where the pointer is a finger. Run it at desktop and every
  // dense toolbar button reports "too small", which is true and irrelevant --
  // noise that buries the real mobile findings. Gate on the mobile tier.
  var isMobileTier = innerW <= 640 || window.matchMedia('(pointer: coarse)').matches;
  var small = [];
  if (isMobileTier) {
    document.querySelectorAll('.tab, .hm-toggle, .race-tab, .theme-toggle button, button, a.btn')
      .forEach(function (el) {
        if (!visible(el) || inOverlay(el)) return;
        var r = el.getBoundingClientRect();
        if (r.height < MIN_TAP || r.width < MIN_TAP) {
          small.push({el: label(el), w: Math.round(r.width), h: Math.round(r.height)});
        }
      });
  }

  return JSON.stringify({
    viewport: [innerW, window.innerHeight],
    elementsChecked: els.length,
    overlap: {count: overlaps.length,
              status: overlaps.length ? 'CHECK' : 'OK',
              items: overlaps.slice(0, 10)},
    horizontalOverflow: overflow,
    tapTargets: {belowMin: small.length, minPx: MIN_TAP,
                 status: !isMobileTier ? 'N/A (desktop pointer)'
                                       : (small.length ? 'WARN' : 'OK'),
                 items: small.slice(0, 10)}
  }, null, 1);
})()
