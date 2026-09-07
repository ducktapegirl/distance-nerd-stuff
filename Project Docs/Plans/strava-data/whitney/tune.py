"""Build a layout editor for D4 — drag and resize each piece, then feed the result back.

Writes layout.html beside itself: the real proof, with every piece of it movable and
resizable over an inch ruler and grid. Nothing about the design is duplicated here — the
pieces come from proofs_d.d4_parts(), so the thing being dragged is exactly the thing that
prints.

    uv run python "Project Docs/Plans/strava-data/whitney/tune.py"          # write layout.html
    uv run python "Project Docs/Plans/strava-data/whitney/tune.py" --layout layout.json

The round trip:

    1. open layout.html, move things
    2. Copy JSON (or I read window.LAYOUT() straight out of the browser)
    3. save it as layout.json
    4. uv run python ".../proofs_d.py" --layout layout.json --png     # see it rendered
    5. the numbers then get wired into the constants in proofs_d.design_d4 by hand

Step 5 matters: a layout file is a pile of transforms, which renders correctly but leaves the
source saying one thing and the picture showing another. It is the staging post, not the
destination.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proofs as P                                    # noqa: E402
import proofs_d as PD                                 # noqa: E402
from proofs import BG, INK, esc, write                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>Mt. Whitney — D4 layout</title>
<style>
  :root {
    --ink:#2b2a28; --ground:#f5f0e6; --chrome:#e7e2d8; --line:#c9c2b4;
    --accent:#1f6f78; --panel:#fbf9f4;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--chrome); color:var(--ink);
         font:13px/1.45 -apple-system, "Segoe UI", Helvetica, sans-serif; overflow:hidden; }
  #app { display:grid; grid-template-columns:1fr 320px; height:100vh; }
  #left { display:grid; grid-template-columns:26px 1fr; grid-template-rows:26px 1fr;
          overflow:hidden; padding:14px; gap:0; }
  #corner { background:var(--panel); border-right:1px solid var(--line);
            border-bottom:1px solid var(--line); }
  #rtop, #rleft { background:var(--panel); overflow:hidden; }
  #rtop { border-bottom:1px solid var(--line); }
  #rleft { border-right:1px solid var(--line); }
  #stage { overflow:auto; display:flex; align-items:flex-start; }
  #sheet { background:var(--ground); box-shadow:0 6px 26px rgba(0,0,0,.22); display:block;
           touch-action:none; }
  aside { background:var(--panel); border-left:1px solid var(--line); overflow-y:auto;
          padding:16px 16px 40px; }
  h1 { font-size:14px; font-weight:600; margin:0 0 2px; }
  .sub { color:#7d7668; margin:0 0 14px; font-size:12px; }
  h2 { font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:#7d7668;
       margin:18px 0 7px; font-weight:600; }
  .row { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
  button { font:inherit; padding:5px 9px; border:1px solid var(--line); background:#fff;
           border-radius:5px; cursor:pointer; color:var(--ink); }
  button:hover { border-color:#8d8578; }
  button.on { background:var(--ink); color:var(--ground); border-color:var(--ink); }
  select { font:inherit; padding:4px 6px; border:1px solid var(--line); border-radius:5px;
           background:#fff; }
  ul.els { list-style:none; margin:0; padding:0; }
  ul.els li { display:flex; align-items:center; gap:8px; padding:5px 7px; border-radius:5px;
              cursor:pointer; }
  ul.els li:hover { background:#efeade; }
  ul.els li.sel { background:var(--ink); color:var(--ground); }
  ul.els li .dot { width:7px; height:7px; border-radius:50%; background:transparent;
                   border:1px solid currentColor; flex:none; }
  ul.els li.moved .dot { background:currentColor; }
  ul.els li .m { margin-left:auto; font-size:10px; opacity:.6; letter-spacing:.05em; }
  .grid4 { display:grid; grid-template-columns:auto 1fr auto 1fr; gap:6px 8px;
           align-items:center; }
  .grid4 label { font-size:11px; color:#7d7668; }
  input[type=number] { width:100%; font:inherit; padding:4px 6px; border:1px solid var(--line);
                       border-radius:5px; background:#fff; }
  textarea { width:100%; height:150px; font:11px/1.4 ui-monospace, Menlo, Consolas, monospace;
             border:1px solid var(--line); border-radius:6px; padding:8px; background:#fff;
             resize:vertical; }
  .hint { color:#7d7668; font-size:11px; margin:8px 0 0; }
  kbd { font:11px ui-monospace, Menlo, Consolas, monospace; background:#efeade;
        border:1px solid var(--line); border-radius:3px; padding:0 4px; }
</style>

<div id="app">
  <div id="left">
    <div id="corner"></div>
    <div id="rtop"><svg id="rulerTop"></svg></div>
    <div id="rleft"><svg id="rulerLeft"></svg></div>
    <div id="stage"><svg id="sheet" xmlns="http://www.w3.org/2000/svg">
      <g id="grid"></g><g id="ghost"></g>
      <g id="content">__GROUPS__</g>
      <g id="over"></g>
    </svg></div>
  </div>

  <aside>
    <h1>D4 layout</h1>
    <p class="sub">11 &times; 14 in &middot; 100 units per inch. Drag to move, corners to
      resize. <kbd>&larr;&uarr;&darr;&rarr;</kbd> nudge 0.01&Prime;, <kbd>Shift</kbd> 0.1&Prime;.</p>

    <h2>View</h2>
    <div class="row">
      <button id="bGrid" class="on">Grid</button>
      <button id="bGhost" class="on">Ghosts</button>
      <select id="zoom"></select>
      <select id="snap">
        <option value="0">No snap</option>
        <option value="6.25">Snap 1/16&Prime;</option>
        <option value="12.5" selected>Snap 1/8&Prime;</option>
        <option value="25">Snap 1/4&Prime;</option>
      </select>
    </div>

    <h2>Elements</h2>
    <ul class="els" id="list"></ul>

    <h2 id="selName">Nothing selected</h2>
    <div class="grid4" id="numbers">
      <label for="nx">X</label><input type="number" id="nx" step="0.01" disabled>
      <label for="ny">Y</label><input type="number" id="ny" step="0.01" disabled>
      <label for="nw">W</label><input type="number" id="nw" step="0.01" disabled>
      <label for="nh">H</label><input type="number" id="nh" step="0.01" disabled>
    </div>
    <p class="hint">Inches from the top-left of the sheet.</p>
    <div class="row" style="margin-top:8px">
      <button id="bResetOne">Reset this</button>
      <button id="bResetAll">Reset all</button>
    </div>

    <h2>Layout JSON</h2>
    <div class="row"><button id="bCopy">Copy</button><button id="bAll">Include unmoved</button></div>
    <textarea id="out" readonly spellcheck="false"></textarea>
    <p class="hint">Save as <code>layout.json</code>, then<br>
      <code>proofs_d.py --layout layout.json</code></p>
  </aside>
</div>

<script>
const SHEET = {w: __W__, h: __H__};
const META = __META__;
const PRESET = __LAYOUT__;
const U = 100;                                  // user units per inch

const sheet = document.getElementById('sheet');
const NS = 'http://www.w3.org/2000/svg';
const mk = (n, a) => { const e = document.createElementNS(NS, n);
                       for (const k in a) e.setAttribute(k, a[k]); return e; };

// ---------------------------------------------------------------- layers
// The pieces are written straight into this <svg> by tune.py rather than stashed in a
// <template> and injected: template contents are parsed as HTML, where <path/> does not
// self-close, so every path after the first ends up nested inside it and never renders.
sheet.setAttribute('viewBox', `0 0 ${SHEET.w} ${SHEET.h}`);
const gGrid = document.getElementById('grid');
const gGhost = document.getElementById('ghost');
const gContent = document.getElementById('content');
const gOver = document.getElementById('over');

// Measure each piece BEFORE giving it a hit target, or the target defines the box it is
// supposed to describe. The hit rect then lives inside the group so it inherits the same
// transform, which is what makes the whole bounding box draggable rather than just the
// hairlines that happen to fall under the cursor.
const els = [];
for (const m of META) {
  const g = gContent.querySelector(`[data-el="${m.key}"]`);
  const b = g.getBBox();
  // a rule is a line, so its box has no height at all: pad any degenerate axis, or the
  // scale factor is a divide-by-zero and the hit target is ungrabbable
  const PAD = 8;
  let x0 = b.x, y0 = b.y, w0 = b.width, h0 = b.height;
  if (w0 < PAD) { x0 -= (PAD - w0) / 2; w0 = PAD; }
  if (h0 < PAD) { y0 -= (PAD - h0) / 2; h0 = PAD; }
  const e = {...m, g, x0, y0, w0, h0, x: x0, y: y0, w: w0, h: h0};
  if (PRESET && PRESET[m.key]) Object.assign(e, {
    x: PRESET[m.key].x, y: PRESET[m.key].y, w: PRESET[m.key].w, h: PRESET[m.key].h});
  g.appendChild(mk('rect', {x: x0, y: y0, width: w0, height: h0,
                            fill: 'transparent', 'pointer-events': 'all',
                            style: 'cursor:move'}));
  g.addEventListener('pointerdown', ev => startDrag(ev, e, null));
  els.push(e);
}
const byKey = Object.fromEntries(els.map(e => [e.key, e]));
let sel = null, Z = 0.5, snap = 12.5, showGhost = true;

const moved = e => Math.abs(e.x - e.x0) > .01 || Math.abs(e.y - e.y0) > .01 ||
                   Math.abs(e.w - e.w0) > .01 || Math.abs(e.h - e.h0) > .01;

function apply(e) {
  const sx = e.w0 ? e.w / e.w0 : 1, sy = e.h0 ? e.h / e.h0 : 1;
  e.g.setAttribute('transform',
    `translate(${e.x.toFixed(3)} ${e.y.toFixed(3)}) scale(${sx.toFixed(6)} ${sy.toFixed(6)}) ` +
    `translate(${(-e.x0).toFixed(3)} ${(-e.y0).toFixed(3)})`);
}

// ------------------------------------------------------------------- grid + rulers
function drawGrid() {
  gGrid.innerHTML = '';
  if (!gridOn) return;
  const fine = Z > 0.42;
  for (let x = 0; x <= SHEET.w; x += 25) {
    if (!fine && x % 100) continue;
    gGrid.appendChild(mk('line', {x1: x, y1: 0, x2: x, y2: SHEET.h,
      stroke: x % 100 ? '#ded7c7' : '#cdc4b0', 'stroke-width': 1,
      'vector-effect': 'non-scaling-stroke'}));
  }
  for (let y = 0; y <= SHEET.h; y += 25) {
    if (!fine && y % 100) continue;
    gGrid.appendChild(mk('line', {x1: 0, y1: y, x2: SHEET.w, y2: y,
      stroke: y % 100 ? '#ded7c7' : '#cdc4b0', 'stroke-width': 1,
      'vector-effect': 'non-scaling-stroke'}));
  }
}

function drawRulers() {
  const rt = document.getElementById('rulerTop');
  const rl = document.getElementById('rulerLeft');
  const W = SHEET.w * Z, H = SHEET.h * Z;
  rt.setAttribute('width', W); rt.setAttribute('height', 26);
  rl.setAttribute('width', 26); rl.setAttribute('height', H);
  rt.innerHTML = ''; rl.innerHTML = '';
  for (let u = 0; u <= SHEET.w; u += 25) {
    const p = u * Z, inch = u / U, major = u % 100 === 0, half = u % 50 === 0;
    rt.appendChild(mk('line', {x1: p, x2: p, y1: major ? 8 : (half ? 14 : 18), y2: 26,
                               stroke: '#9a9283', 'stroke-width': 1}));
    if (major) rt.appendChild(mk('text', {x: p + 3, y: 12, fill: '#6f6858',
      'font-size': 10, 'font-family': 'inherit'})).textContent = inch;
  }
  for (let u = 0; u <= SHEET.h; u += 25) {
    const p = u * Z, inch = u / U, major = u % 100 === 0, half = u % 50 === 0;
    rl.appendChild(mk('line', {y1: p, y2: p, x1: major ? 8 : (half ? 14 : 18), x2: 26,
                               stroke: '#9a9283', 'stroke-width': 1}));
    if (major) rl.appendChild(mk('text', {x: 3, y: p + 11, fill: '#6f6858',
      'font-size': 10, 'font-family': 'inherit'})).textContent = inch;
  }
}

function setZoom(z) {
  Z = z;
  sheet.setAttribute('width', SHEET.w * Z);
  sheet.setAttribute('height', SHEET.h * Z);
  drawGrid(); drawRulers(); drawOverlay();
}

document.getElementById('stage').addEventListener('scroll', ev => {
  document.getElementById('rtop').scrollLeft = ev.target.scrollLeft;
  document.getElementById('rleft').scrollTop = ev.target.scrollTop;
});

// ------------------------------------------------------------------- selection UI
const HANDLES = [['nw',0,0],['n',.5,0],['ne',1,0],['e',1,.5],
                 ['se',1,1],['s',.5,1],['sw',0,1],['w',0,.5]];

function drawOverlay() {
  gOver.innerHTML = '';
  gGhost.innerHTML = '';
  if (showGhost) for (const e of els) {
    if (!moved(e)) continue;
    gGhost.appendChild(mk('rect', {x: e.x0, y: e.y0, width: e.w0, height: e.h0,
      fill: 'none', stroke: '#b9b1a0', 'stroke-width': 1, 'stroke-dasharray': '4 4',
      'vector-effect': 'non-scaling-stroke'}));
  }
  if (!sel) return;
  gOver.appendChild(mk('rect', {x: sel.x, y: sel.y, width: sel.w, height: sel.h,
    fill: 'none', stroke: '#1f6f78', 'stroke-width': 1.5,
    'vector-effect': 'non-scaling-stroke'}));
  const r = 4.5 / Z;                            // constant on screen, whatever the zoom
  for (const [name, fx, fy] of HANDLES) {
    if (sel.mode === 'lock' && name.length === 1) continue;   // aspect-locked: corners only
    if (sel.mode === 'wide' && name !== 'e' && name !== 'w') continue;   // a rule: width only
    const hx = sel.x + fx * sel.w, hy = sel.y + fy * sel.h;
    const h = mk('rect', {x: hx - r, y: hy - r, width: r * 2, height: r * 2,
      fill: '#fff', stroke: '#1f6f78', 'stroke-width': 1.5,
      'vector-effect': 'non-scaling-stroke',
      style: `cursor:${name.length === 2 ? name + '-resize' : name + '-resize'}`});
    h.addEventListener('pointerdown', ev => startDrag(ev, sel, name));
    gOver.appendChild(h);
  }
}

function select(e) {
  sel = e;
  for (const li of document.querySelectorAll('ul.els li'))
    li.classList.toggle('sel', li.dataset.k === (e && e.key));
  document.getElementById('selName').textContent = e ? e.label : 'Nothing selected';
  for (const id of ['nx','ny','nw','nh']) document.getElementById(id).disabled = !e;
  syncNumbers(); drawOverlay();
}

function syncNumbers() {
  if (!sel) { for (const id of ['nx','ny','nw','nh']) document.getElementById(id).value = '';
              return; }
  document.getElementById('nx').value = (sel.x / U).toFixed(2);
  document.getElementById('ny').value = (sel.y / U).toFixed(2);
  document.getElementById('nw').value = (sel.w / U).toFixed(2);
  document.getElementById('nh').value = (sel.h / U).toFixed(2);
}

// ------------------------------------------------------------------------ dragging
const pt = sheet.createSVGPoint();
const toSheet = ev => { pt.x = ev.clientX; pt.y = ev.clientY;
                        return pt.matrixTransform(sheet.getScreenCTM().inverse()); };
const sn = v => snap ? Math.round(v / snap) * snap : v;
let drag = null;

function startDrag(ev, e, handle) {
  ev.preventDefault(); ev.stopPropagation();
  select(e);
  drag = {e, handle, p0: toSheet(ev), s: {x: e.x, y: e.y, w: e.w, h: e.h}};
  sheet.setPointerCapture(ev.pointerId);
}

sheet.addEventListener('pointermove', ev => {
  if (!drag) return;
  const p = toSheet(ev), {e, handle, s} = drag;
  if (!handle) {
    e.x = sn(s.x + p.x - drag.p0.x);
    e.y = sn(s.y + p.y - drag.p0.y);
  } else {
    let x = s.x, y = s.y, w = s.w, h = s.h;
    if (handle.includes('w')) { const nx = sn(p.x); w = s.x + s.w - nx; x = nx; }
    if (handle.includes('e')) { w = sn(p.x) - s.x; }
    if (handle.includes('n')) { const ny = sn(p.y); h = s.y + s.h - ny; y = ny; }
    if (handle.includes('s')) { h = sn(p.y) - s.y; }
    w = Math.max(w, 8); h = Math.max(h, 8);
    if (e.mode === 'lock') {
      // average the two ratios so a diagonal drag feels natural, then re-pin whichever
      // corner the drag is anchored to
      const k = (w / s.w + h / s.h) / 2;
      w = s.w * k; h = s.h * k;
      x = handle.includes('w') ? s.x + s.w - w : s.x;
      y = handle.includes('n') ? s.y + s.h - h : s.y;
    }
    Object.assign(e, {x, y, w, h});
  }
  apply(e); syncNumbers(); drawOverlay(); refreshList();
});

const endDrag = ev => { if (drag) { drag = null; emit(); } };
sheet.addEventListener('pointerup', endDrag);
sheet.addEventListener('pointercancel', endDrag);
sheet.addEventListener('pointerdown', ev => { if (ev.target === sheet) select(null); });

window.addEventListener('keydown', ev => {
  if (!sel || document.activeElement.tagName === 'INPUT') return;
  const d = {ArrowLeft: [-1,0], ArrowRight: [1,0], ArrowUp: [0,-1], ArrowDown: [0,1]}[ev.key];
  if (!d) return;
  ev.preventDefault();
  const step = ev.shiftKey ? 10 : 1;
  sel.x += d[0] * step; sel.y += d[1] * step;
  apply(sel); syncNumbers(); drawOverlay(); refreshList(); emit();
});

for (const [id, prop] of [['nx','x'],['ny','y'],['nw','w'],['nh','h']]) {
  document.getElementById(id).addEventListener('input', ev => {
    if (!sel) return;
    const v = parseFloat(ev.target.value);
    if (!isFinite(v)) return;
    if ((prop === 'w' || prop === 'h') && v <= 0) return;
    if (sel.mode === 'lock' && prop === 'w') sel.h = sel.h0 * (v * U) / sel.w0;
    if (sel.mode === 'lock' && prop === 'h') sel.w = sel.w0 * (v * U) / sel.h0;
    sel[prop] = v * U;
    apply(sel); drawOverlay(); refreshList(); emit();
    if (sel.mode === 'lock') syncNumbers();
  });
}

// ---------------------------------------------------------------------- list + out
const list = document.getElementById('list');
for (const e of els) {
  const li = document.createElement('li');
  li.dataset.k = e.key;
  li.innerHTML = `<span class="dot"></span><span>${e.label}</span>` +
                 `<span class="m">${e.mode === 'lock' ? 'aspect' : 'free'}</span>`;
  li.addEventListener('click', () => select(e));
  list.appendChild(li);
}
const refreshList = () => {
  for (const li of list.children) li.classList.toggle('moved', moved(byKey[li.dataset.k]));
};

let includeAll = false;
function payload() {
  const o = {};
  for (const e of els) {
    if (!includeAll && !moved(e)) continue;
    o[e.key] = {x: +e.x.toFixed(2), y: +e.y.toFixed(2),
                w: +e.w.toFixed(2), h: +e.h.toFixed(2),
                x0: +e.x0.toFixed(2), y0: +e.y0.toFixed(2),
                w0: +e.w0.toFixed(2), h0: +e.h0.toFixed(2)};
  }
  return o;
}
function emit() { document.getElementById('out').value = JSON.stringify(payload(), null, 1); }

// read straight out of the page instead of copy-pasting
window.LAYOUT = () => payload();
window.LAYOUT_INCHES = () => Object.fromEntries(els.map(e => [e.key,
  {label: e.label, moved: moved(e),
   x: +(e.x / U).toFixed(3), y: +(e.y / U).toFixed(3),
   w: +(e.w / U).toFixed(3), h: +(e.h / U).toFixed(3),
   dx: +((e.x - e.x0) / U).toFixed(3), dy: +((e.y - e.y0) / U).toFixed(3),
   scale: +(e.w / e.w0).toFixed(4)}]));

// --------------------------------------------------------------------- chrome wiring
let gridOn = true;
document.getElementById('bGrid').onclick = ev => {
  gridOn = !gridOn; ev.target.classList.toggle('on', gridOn); drawGrid(); };
document.getElementById('bGhost').onclick = ev => {
  showGhost = !showGhost; ev.target.classList.toggle('on', showGhost); drawOverlay(); };
document.getElementById('snap').onchange = ev => snap = parseFloat(ev.target.value);
document.getElementById('bResetOne').onclick = () => {
  if (!sel) return;
  Object.assign(sel, {x: sel.x0, y: sel.y0, w: sel.w0, h: sel.h0});
  apply(sel); syncNumbers(); drawOverlay(); refreshList(); emit(); };
document.getElementById('bResetAll').onclick = () => {
  for (const e of els) { Object.assign(e, {x: e.x0, y: e.y0, w: e.w0, h: e.h0}); apply(e); }
  syncNumbers(); drawOverlay(); refreshList(); emit(); };
document.getElementById('bAll').onclick = ev => {
  includeAll = !includeAll; ev.target.classList.toggle('on', includeAll); emit(); };
document.getElementById('bCopy').onclick = async ev => {
  const ta = document.getElementById('out');
  try { await navigator.clipboard.writeText(ta.value); }
  catch (_) { ta.select(); document.execCommand('copy'); }
  ev.target.textContent = 'Copied'; setTimeout(() => ev.target.textContent = 'Copy', 1200); };

const zsel = document.getElementById('zoom');
for (const z of ['fit', 0.35, 0.45, 0.55, 0.7, 1]) {
  const o = document.createElement('option');
  o.value = z; o.textContent = z === 'fit' ? 'Fit' : Math.round(z * 100) + '%';
  zsel.appendChild(o);
}
function fit() {
  const box = document.getElementById('stage').getBoundingClientRect();
  return Math.min((box.height - 6) / SHEET.h, (box.width - 6) / SHEET.w);
}
zsel.onchange = () => setZoom(zsel.value === 'fit' ? fit() : parseFloat(zsel.value));
window.addEventListener('resize', () => { if (zsel.value === 'fit') setZoom(fit()); });

for (const e of els) apply(e);
setZoom(fit());
refreshList(); emit();
</script>
"""


def build(act, layout=None):
    parts = PD.d4_parts(act)
    groups = "".join(
        f'<g class="el" data-el="{esc(k)}">{svg}</g>' for k, label, mode, svg in parts)
    meta = [{"key": k, "label": label, "mode": mode} for k, label, mode, _ in parts]
    return (PAGE.replace("__W__", str(PD.W)).replace("__H__", str(PD.H))
                .replace("__META__", json.dumps(meta))
                .replace("__LAYOUT__", json.dumps(layout) if layout else "null")
                .replace("__GROUPS__", groups))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layout", help="preload a saved layout.json so you can carry on")
    ap.add_argument("--out", default=os.path.join(HERE, "layout.html"))
    args = ap.parse_args()

    layout = None
    if args.layout:
        with open(args.layout, encoding="utf-8") as f:
            layout = json.load(f)

    act = P.load()
    write(args.out, build(act, layout))
    n = len(PD.d4_parts(act))
    print(f"wrote {args.out}  ({n} movable pieces)", file=sys.stderr)
    for k, label, mode, _ in PD.d4_parts(act):
        print(f"  {k:10s} {label:20s} {mode}", file=sys.stderr)


if __name__ == "__main__":
    main()
