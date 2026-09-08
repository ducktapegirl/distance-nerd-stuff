"""The "Years in motion" piece: a year clock standing on a bloom of routes.

Canonical home for the artwork. It lives in the dashboard package because the
Art tab renders it; `tools/proof_year_art.py` imports from here for its
exploration proof sheet rather than keeping a second copy -- the duplication
between `feed/places.py` and the dashboard's place boxes is exactly the trap
worth not repeating.

Deliberately imports nothing else from `dashboard/` except `config` (for the
data paths). No plotly, no MapTiler: this is hand-built SVG at absolute user
units, and it must stay cheap enough for the standalone tool to import.

Every id and global it emits is prefixed `art-` / `ART_`, because it is
embedded in a page that already defines things like `ACT`.
"""

import calendar
import csv
import json
import math
import os
from collections import defaultdict
from datetime import date, datetime

from .config import DATA_DIR, STREAMS_DIR

# Five families. The poster keeps six and splits snow by direction of travel
# (downhill against nordic); here all snow is one family, and skating -- which
# the poster groups with nordic -- sits in "other", so a color is not spent on
# a handful of activities across three years.
FAMILY = {
    "Run": "run", "TrailRun": "run",
    "MountainBikeRide": "mtb", "Ride": "mtb", "EBikeRide": "mtb",
    "Hike": "foot", "Walk": "foot",
    "AlpineSki": "snow", "Snowboard": "snow", "NordicSki": "snow",
    "IceSkate": "other", "RockClimbing": "other", "WeightTraining": "other",
    "Workout": "other", "Pickleball": "other", "StandUpPaddling": "other",
    "Pilates": "other",
}
# Which activity wins when two share a calendar day and therefore an angle.
# Higher paints later, so it ends up on top and is what the pointer reaches.
PRIORITY = {"run": 3, "mtb": 3, "foot": 2, "snow": 2, "other": 1}

COLOR = {"run": "#2dd4bf", "mtb": "#f59e0b", "foot": "#a3e635",
         "snow": "#60a5fa", "other": "#f472b6"}
FAM_LABEL = {"run": "run", "mtb": "bike", "foot": "hike / walk",
             "snow": "snow", "other": "other"}


def paint(key, interactive):
    """A family color: themed via --art-<key> when interactive, literal for
    the static/print path (rasterizers don't implement var())."""
    return "var(--art-%s, %s)" % (key, COLOR[key]) if interactive else COLOR[key]


def ink(token, literal, interactive):
    """A non-family color (ground, ink, line) behind the same gate."""
    return "var(--%s, %s)" % (token, literal) if interactive else literal


# ART_BG is the dark literal: the ground and every halo/scrim stop on the
# static/print path, which stays literal because rasterizers (cairosvg, resvg,
# Inkscape) don't implement var(). On the interactive path it is the dark
# value of --art-bg, themed by ART_CSS via paint()/ink() at each call site.
ART_BG = "#0b0f14"

S = 900             # viewBox, square
C = S / 2
R0, R1 = 168, 402   # inner ring, outer reach of the longest spoke

UNMAPPED = set()


# ─── data ─────────────────────────────────────────────────────────────────────

def prepare(rows):
    """Enrich raw activity rows (as load_activities returns them)."""
    acts = []
    for r in rows:
        r = dict(r)
        r["dt"] = datetime.strptime(r["start_date_local"], "%Y-%m-%d %H:%M:%S")
        if r["sport_type"] not in FAMILY:
            UNMAPPED.add(r["sport_type"])
        r["fam"] = FAMILY.get(r["sport_type"], "other")
        r["km"] = float(r["distance_km"] or 0)
        r["min"] = float(r["moving_time_min"] or 0)
        r["yr"] = r["dt"].year
        acts.append(r)
    acts.sort(key=lambda r: r["dt"])
    return acts


def load(year=None):
    """Read activities.csv directly -- for the standalone proof tool."""
    with open(os.path.join(DATA_DIR, "activities.csv"), encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f)
                if year is None or r["start_date_local"].startswith(str(year))]
    return prepare(rows)


def track(aid, step=6):
    """Lat/lng track projected to local meters, recentered on its own origin."""
    p = os.path.join(STREAMS_DIR, str(aid) + ".csv")
    if not os.path.exists(p):
        return []
    pts = []
    with open(p, encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i % step or not row.get("lat"):
                continue
            try:
                pts.append((float(row["lat"]), float(row["lng"])))
            except ValueError:
                pass
    if len(pts) < 4:
        return []
    lat0 = sum(p[0] for p in pts) / len(pts)
    k = math.cos(math.radians(lat0))
    return [((lng - pts[0][1]) * k * 111320.0, -(lat - pts[0][0]) * 110540.0)
            for lat, lng in pts]


def load_tracks(acts):
    out = {}
    for a in acts:
        t = track(a["id"])
        if t:
            out[a["id"]] = t
    return out


def ndays(year):
    """366 in a leap year. The angle denominator has to follow it, or Dec 31
    lands in a different place in 2024 than in 2025 and the years stop being
    comparable under the picker."""
    return 366 if calendar.isleap(year) else 365


def scale_of(all_acts, all_tracks):
    """One scale shared by every year. Per-year normalization would make a
    5-mile run in a thin year draw as long as a 13-mile hike in a heavy one --
    which is exactly the comparison the year picker invites."""
    exts = sorted(max(max(abs(x), abs(y)) for x, y in t) for t in all_tracks.values())
    return {"mx": max(a["km"] for a in all_acts) or 1.0,
            "ext": exts[int(len(exts) * 0.85)] if exts else 1.0}


def by_year(acts):
    out = defaultdict(list)
    for a in acts:
        out[a["yr"]].append(a)
    return dict(out)


# ─── drawing ──────────────────────────────────────────────────────────────────

# Douglas-Peucker tolerance, in SVG user units. The viewBox is 900 units wide
# and renders at 720 CSS px, so 1 unit is ~0.8 px and this is ~0.4 px -- still
# sub-pixel at 2x zoom. It drops the bloom from 110,718 points to 40,361 with
# nothing visible to lose: the traces draw at 0.9px stroke and 0.38 opacity.
# A tolerance of 1.0 would save a further ~0.15 MB, which is not worth twice
# the deviation.
SIMPLIFY_EPS = 0.5


def simplify(pts, eps=SIMPLIFY_EPS):
    """Douglas-Peucker, iterative so a long track cannot blow the stack.

    Must run on points already projected into user units -- a tolerance in
    meters means nothing until the points are in the space they are drawn in.
    """
    n = len(pts)
    if n < 3 or eps <= 0:
        return pts
    keep = [False] * n
    keep[0] = keep[n - 1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        x1, y1 = pts[i]
        x2, y2 = pts[j]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-9
        far, fi = -1.0, -1
        for k in range(i + 1, j):
            x, y = pts[k]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
            if d > far:
                far, fi = d, k
        if far > eps:
            keep[fi] = True
            stack.append((i, fi))
            stack.append((fi, j))
    return [p for p, k in zip(pts, keep) if k]


def path(pts):
    return "M" + "L".join("%.1f %.1f" % (x, y) for x, y in pts)


def fmt_day(d):
    return "%d %s" % (d.day, calendar.month_abbr[d.month])


def summary_lines(acts, year):
    """The center subtitle. A partial year must say so -- an unqualified
    "51 activities" next to another year's 194 reads as a collapse in fitness
    rather than a short window of data."""
    tot = sum(a["km"] for a in acts) * 0.621371
    days = len(set(a["dt"].date() for a in acts))
    first, last = acts[0]["dt"].date(), acts[-1]["dt"].date()
    lines = ["%d activities &#183; %d days &#183; %s mi"
             % (len(acts), days, format(int(round(tot)), ","))]
    if first > date(year, 1, 7) or last < date(year, 12, 24):
        lines.append("%s &#8211; %s &#183; partial year"
                     % (fmt_day(first), fmt_day(last)))
    return lines


def year_layer(acts, tracks, year, scale, interactive=True, visible=False):
    """One year as a <g>, so several can share an SVG and the picker can swap
    them without the armature moving."""
    nd = ndays(year)
    mx, ext = scale["mx"], scale["ext"]
    out = ['<g class="art-year" data-year="%d"%s>'
           % (year, "" if visible else ' style="display:none"')]

    # ground: the bloom, scaled so a typical route fills the frame. The handful
    # of travel days deliberately run off-canvas rather than shrinking
    # everything else to fit them.
    s = (S * 0.46) / ext
    out.append('<g class="art-bloom" stroke-linejoin="round" fill="none">')
    for a in acts:
        t = tracks.get(a["id"])
        if not t:
            continue
        th = (a["dt"].timetuple().tm_yday - 1) / nd * 2 * math.pi
        ct, st = math.cos(th), math.sin(th)
        pp = simplify([(C + (x * ct - y * st) * s, C + (x * st + y * ct) * s)
                       for x, y in t])
        tag = ('class="art-trace art-fam-%s" data-id="%s" ' % (a["fam"], a["id"])) \
            if interactive else ""
        out.append('<path %sd="%s" stroke="%s" stroke-width="0.9" opacity="0.38"/>'
                   % (tag, path(pp), paint(a["fam"], interactive)))
    out.append('</g>')
    # a tight scrim behind the center type only -- every track shares an origin,
    # so a wide one erases the bloom exactly where it is densest
    out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#art-scrim)"/>'
               % (C, C, R0 * 1.04))

    # figure: the year clock
    line_color = ink("art-line", "#243244", interactive)
    bg_color = ink("art-bg", ART_BG, interactive)
    mon_class = 'class="art-mon" ' if interactive else ""
    for m in range(12):
        deg = (date(year, m + 1, 1).timetuple().tm_yday - 1) / nd * 360 - 90
        a = math.radians(deg)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="1"/>' % (C + R0 * math.cos(a), C + R0 * math.sin(a),
                                           C + (R1 + 16) * math.cos(a),
                                           C + (R1 + 16) * math.sin(a), line_color))
        am = math.radians(deg + 15)
        out.append('<text %sx="%.1f" y="%.1f" fill="%s" font-family="system-ui" '
                   'font-size="14" letter-spacing="1.5" text-anchor="middle" '
                   'paint-order="stroke" stroke="%s" stroke-width="5" '
                   'stroke-linejoin="round">%s</text>'
                   % (mon_class, C + (R1 + 36) * math.cos(am), C + (R1 + 36) * math.sin(am),
                      ink("art-month", "#7c8ba1", interactive), bg_color,
                      calendar.month_abbr[m + 1].upper()))
    ring_class = 'class="art-ring" ' if interactive else ""
    out.append('<circle %scx="%.1f" cy="%.1f" r="%d" fill="none" stroke="%s"/>'
               % (ring_class, C, C, R0, line_color))

    # Same-day activities land on the identical angle and overlap exactly, so
    # paint order decides which is visible and reachable. Least "serious" first.
    drawn = sorted(acts, key=lambda a: (a["dt"].date(), PRIORITY[a["fam"]], a["km"]))

    out.append('<g class="art-spokes">')
    for a in drawn:
        ang = math.radians((a["dt"].timetuple().tm_yday - 1) / nd * 360 - 90)
        w = 1.2 + min(a["min"], 240) / 60
        tag = ('class="art-spoke art-fam-%s" data-id="%s" ' % (a["fam"], a["id"])) \
            if interactive else ""
        if a["km"] <= 0:
            # No distance recorded (climbing, weights). A spoke would be exactly
            # zero units long and not appear at all, though it is still counted
            # in the subtitle -- so these get a tick inside the ring instead.
            r0, r1 = R0 - 13, R0 - 4
        else:
            ln = R0 + (R1 - R0) * math.sqrt(min(a["km"] / mx, 1.0))
            r0, r1 = R0, max(ln, R0 + 4)   # a real but tiny distance stays visible
        out.append('<line %sx1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="%.1f" stroke-linecap="round" opacity="0.9"/>'
                   % (tag, C + r0 * math.cos(ang), C + r0 * math.sin(ang),
                      C + r1 * math.cos(ang), C + r1 * math.sin(ang),
                      paint(a["fam"], interactive), w))
    out.append('</g>')

    out.append('<g class="art-rd-default">')
    out.append('<text x="%.1f" y="%.1f" fill="%s" font-family="system-ui" '
               'font-size="52" letter-spacing="4" text-anchor="middle" '
               'paint-order="stroke" stroke="%s" stroke-width="7" '
               'stroke-linejoin="round">%d</text>'
               % (C, C - 4, ink("art-num", "#e2e8f0", interactive), bg_color, year))
    for i, line in enumerate(summary_lines(acts, year)):
        out.append('<text x="%.1f" y="%.1f" fill="%s" font-family="system-ui" '
                   'font-size="14" letter-spacing="1" text-anchor="middle" '
                   'paint-order="stroke" stroke="%s" stroke-width="5" '
                   'stroke-linejoin="round">%s</text>'
                   % (C, C + 28 + i * 21, ink("art-sub", "#64748b", interactive),
                      bg_color, line))
    out.append('</g>')

    if interactive:
        # hit targets last so they sit on top, full-length so a short spoke is
        # no harder to reach than a long one, and in the same paint order so the
        # pointer reaches whatever is visually on top
        out.append('<g class="art-hits" fill="none" stroke="transparent" '
                   'stroke-width="13" stroke-linecap="round" pointer-events="stroke">')
        for a in drawn:
            ang = math.radians((a["dt"].timetuple().tm_yday - 1) / nd * 360 - 90)
            hr0 = R0 - 15   # far enough in to cover an inner-ring tick
            out.append('<line class="art-hit" data-id="%s" x1="%.1f" y1="%.1f" '
                       'x2="%.1f" y2="%.1f"/>'
                       % (a["id"], C + hr0 * math.cos(ang), C + hr0 * math.sin(ang),
                          C + (R1 + 8) * math.cos(ang), C + (R1 + 8) * math.sin(ang)))
        out.append('</g>')

    out.append('</g>')
    return "\n".join(out)


# ─── page fragment ────────────────────────────────────────────────────────────

ART_CSS = """
:root{
  --art-run:#2dd4bf;--art-mtb:#f59e0b;--art-foot:#a3e635;--art-snow:#60a5fa;--art-other:#f472b6;
  --art-bg:#0b0f14;--art-line:#243244;--art-month:#7c8ba1;--art-num:#e2e8f0;--art-stat:#94a3b8;
  --art-sub:#64748b;--art-partial:#f59e0b;
  --art-trace-op:.38;--art-spoke-op:.9;--art-dim-spoke:.24;--art-dim-trace:.13;--art-off:.04;
  --art-glow:drop-shadow(0 0 5px currentColor);
}
:root.light{
  --art-run:#0d9488;--art-mtb:#b45309;--art-foot:#4d7c0f;--art-snow:#1d4ed8;--art-other:#be185d;
  --art-bg:#ffffff;--art-line:#cbd5e1;--art-month:#64748b;--art-num:#0f172a;--art-stat:#475569;
  --art-sub:#64748b;--art-partial:#c2710c;
  --art-trace-op:.30;--art-spoke-op:1;--art-dim-spoke:.18;--art-dim-trace:.09;--art-off:.05;
  --art-glow:none;
}
/* The piece is square, so at full card width it becomes ~1150px tall and the
   card turns into a scroll. Cap it and center it -- it reads as a framed print
   rather than a chart that should fill the column. */
/* plain max-width: width:100% already caps it at the container, so min() adds
   nothing here */
#art-svg{width:100%;max-width:720px;height:auto;display:block;
  margin:0 auto;background:var(--art-bg);border-radius:10px;
  touch-action:none;-webkit-tap-highlight-color:transparent}
#art-svg #art-scrim stop{stop-color:var(--art-bg)}
.art-trace{opacity:var(--art-trace-op)}
.art-spoke{opacity:var(--art-spoke-op)}
#art-svg.sel .art-spoke:not(.on){opacity:var(--art-dim-spoke)}
#art-svg.sel .art-trace:not(.on){opacity:var(--art-dim-trace)}
.art-spoke.on{opacity:1;filter:var(--art-glow)}
.art-trace.on{opacity:1;stroke-width:2.4}
.art-spoke,.art-trace{transition:opacity .12s}
.art-spoke.off,.art-trace.off{opacity:var(--art-off)}
#art-svg.sel .art-spoke.off,#art-svg.sel .art-trace.off{opacity:var(--art-off)}
.art-hit{cursor:crosshair}
.art-hit.off{pointer-events:none}
.art-bar{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-top:14px}
.art-bar button{display:flex;align-items:center;gap:7px;background:none;
  border:1px solid var(--border-subtle);border-radius:999px;padding:5px 12px;
  color:var(--text-secondary);font:inherit;font-size:13px;cursor:pointer}
.art-bar button:hover{border-color:var(--border);color:var(--text-primary)}
#art-legend button[aria-pressed=false]{opacity:.4}
.art-sw{width:10px;height:10px;border-radius:2px;display:block}
.art-sw.art-fam-run{background:var(--art-run)}
.art-sw.art-fam-mtb{background:var(--art-mtb)}
.art-sw.art-fam-foot{background:var(--art-foot)}
.art-sw.art-fam-snow{background:var(--art-snow)}
.art-sw.art-fam-other{background:var(--art-other)}
#art-years{gap:0;border:1px solid var(--border-subtle);border-radius:999px;
  overflow:hidden;padding:2px;width:max-content;margin-left:auto;margin-right:auto}
#art-years button{border:none;border-radius:999px;padding:7px 20px;font-size:15px;
  letter-spacing:1px}
#art-years button[aria-pressed=true]{background:var(--border-subtle);
  color:var(--text-primary)}
#art-years button.partial::after{content:'\\2022';color:var(--art-partial);font-size:15px;
  line-height:0}
#art-hint{font-size:12px;color:var(--text-secondary);opacity:.8;min-height:1.2em;
  text-align:center;margin-top:8px}
"""

ART_JS = """
(function(){
  var D=window.ART_DATA, ACT=D.act;
  var art=document.getElementById('art-svg'), hint=document.getElementById('art-hint');
  var det=document.getElementById('art-rd-detail');
  var fDate=document.getElementById('art-rd-date'), fName=document.getElementById('art-rd-name');
  var fStat=document.getElementById('art-rd-stat'), fSport=document.getElementById('art-rd-sport');
  if(!art) return;
  var layers={}, off={}, cur=null, yr=null, spokes={}, traces={}, def=null;

  Array.prototype.forEach.call(art.querySelectorAll('.art-year'),function(g){
    layers[g.getAttribute('data-year')]=g; });

  function dur(m){
    var h=Math.floor(m/60), r=Math.round(m-h*60);
    return h ? h+'h '+(r<10?'0':'')+r+'m' : Math.round(m)+' min';
  }
  // the readout well is ~300 user units wide; step the size down before
  // resorting to an ellipsis so long names stay readable
  function setName(s){
    var px = s.length<=20 ? 21 : s.length<=30 ? 17 : 14;
    if(s.length>46) s=s.slice(0,45)+'\\u2026';
    fName.setAttribute('font-size',px); fName.textContent=s;
  }

  function select(id){
    if(id===cur) return;
    if(cur){
      if(spokes[cur]) spokes[cur].classList.remove('on');
      if(traces[cur]) traces[cur].classList.remove('on');
    }
    cur=id;
    if(!id){ art.classList.remove('sel'); if(def) def.style.display='';
             det.style.display='none'; hint.textContent=D.hint; return; }
    var a=ACT[id];
    if(spokes[id]) spokes[id].classList.add('on');
    if(traces[id]) traces[id].classList.add('on');
    art.classList.add('sel'); if(def) def.style.display='none'; det.style.display='';
    fDate.textContent=(a.d+' '+a.yr).toUpperCase();
    setName(a.n);
    // no distance recorded (gym, climbing): "0.0 mi" is worse than nothing
    var bits=[];
    if(a.mi>=0.05) bits.push(a.mi.toFixed(1)+' mi');
    bits.push(dur(a.t));
    if(a.ft>50) bits.push(Math.round(a.ft).toLocaleString()+' ft');
    fStat.textContent=bits.join(' \\u00b7 ');
    fSport.textContent=a.sp.toUpperCase();
    hint.textContent = traces[id] ? '' : 'no GPS for this one \\u2014 nothing in the ground layer';
  }

  function setYear(y){
    y=String(y);
    if(!layers[y] || y===yr) return;
    select(null);
    for(var k in layers) layers[k].style.display = (k===y) ? '' : 'none';
    yr=y;
    var g=layers[y];
    spokes={}; traces={}; def=g.querySelector('.art-rd-default');
    Array.prototype.forEach.call(g.querySelectorAll('.art-spoke'),function(el){
      spokes[el.getAttribute('data-id')]=el; });
    Array.prototype.forEach.call(g.querySelectorAll('.art-trace'),function(el){
      traces[el.getAttribute('data-id')]=el; });
    applyFilter();   // a family switched off stays off across years
    Array.prototype.forEach.call(document.querySelectorAll('#art-years button'),function(b){
      b.setAttribute('aria-pressed', b.getAttribute('data-year')===y ? 'true':'false'); });
    hint.textContent=D.hint;
  }

  function applyFilter(){
    var g=layers[yr];
    Array.prototype.forEach.call(g.querySelectorAll('[data-id]'),function(el){
      el.classList.toggle('off', !!off[ACT[el.getAttribute('data-id')].f]); });
    if(cur && off[ACT[cur].f]) select(null);
  }

  art.addEventListener('pointerover',function(e){
    var h=e.target.closest && e.target.closest('.art-hit');
    if(h) select(h.getAttribute('data-id'));
  });
  art.addEventListener('pointerleave',function(){ if(!drag) select(null); });

  // touch (and mouse-drag): scrub a hand around the year. A day is ~7px of arc
  // at the rim, so tapping individual spokes is not viable on a phone.
  var drag=false;
  function scrub(e){
    var r=art.getBoundingClientRect();
    if(!r.width) return;
    var x=e.clientX-(r.left+r.width/2), y=e.clientY-(r.top+r.height/2);
    if(Math.sqrt(x*x+y*y) < r.width*0.12){ select(null); return; }
    var nd=D.ndays[yr];
    var deg=(Math.atan2(y,x)*180/Math.PI+90+360)%360;
    var day=deg/360*nd, best=null, bd=1e9;
    for(var id in spokes){
      var a=ACT[id];
      if(off[a.f]) continue;
      var d=Math.abs(a.y-day); if(d>nd/2) d=nd-d;
      if(d<bd){ bd=d; best=id; }
    }
    if(best) select(best);
  }
  art.addEventListener('pointerdown',function(e){
    drag=true;
    try{ art.setPointerCapture(e.pointerId); }catch(err){}
    scrub(e); e.preventDefault(); });
  art.addEventListener('pointermove',function(e){ if(drag) scrub(e); });
  art.addEventListener('pointerup',function(){ drag=false; });
  art.addEventListener('pointercancel',function(){ drag=false; });

  Array.prototype.forEach.call(document.querySelectorAll('#art-legend button'),function(b){
    b.addEventListener('click',function(){
      var f=b.getAttribute('data-fam');
      off[f]=!off[f];
      b.setAttribute('aria-pressed', off[f] ? 'false' : 'true');
      applyFilter();
    });
  });
  Array.prototype.forEach.call(document.querySelectorAll('#art-years button'),function(b){
    b.addEventListener('click',function(){ setYear(b.getAttribute('data-year')); });
  });

  // Arrow keys change year, but only while the Art view is the active one --
  // a document-level handler would otherwise eat left/right on every tab.
  document.addEventListener('keydown',function(e){
    if(e.key!=='ArrowLeft' && e.key!=='ArrowRight') return;
    if(document.documentElement.getAttribute('data-view')!=='art') return;
    var ys=D.years, i=ys.indexOf(Number(yr)) + (e.key==='ArrowRight'?1:-1);
    if(i>=0 && i<ys.length){ setYear(ys[i]); e.preventDefault(); }
  });

  setYear(D.start);
})();
"""


def static_svg(acts, tracks, year, scale):
    """The piece as a standalone, non-interactive SVG -- for the proof sheet and
    for anything that wants a print-ready file."""
    return (
        '<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (S, S)
        + '<defs><radialGradient id="art-scrim">'
          '<stop offset="0" stop-color="%s" stop-opacity="0.93"/>'
          '<stop offset="0.62" stop-color="%s" stop-opacity="0.86"/>'
          '<stop offset="1" stop-color="%s" stop-opacity="0"/>'
          '</radialGradient></defs>' % (ART_BG, ART_BG, ART_BG)
        + '<rect width="%d" height="%d" fill="%s"/>' % (S, S, ART_BG)
        + year_layer(acts, tracks, year, scale, interactive=False, visible=True)
        + "</svg>")


def _js_json(obj):
    """JSON safe to inline in a <script>: an activity named "</script>" would
    otherwise end the block early."""
    return (json.dumps(obj, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e"))


def art_fragment(rows):
    """The whole piece as one self-contained HTML fragment: style, svg,
    controls, script. Returns "" if there is nothing to draw."""
    acts = prepare(rows)
    if not acts:
        return ""
    tracks = load_tracks(acts)
    years = by_year(acts)
    scale = scale_of(acts, tracks)

    meta, ndays_map, picker = {}, {}, []
    for y in sorted(years):
        ndays_map[str(y)] = ndays(y)
        ys = years[y]
        first, last = ys[0]["dt"].date(), ys[-1]["dt"].date()
        partial = first > date(y, 1, 7) or last < date(y, 12, 24)
        picker.append('<button type="button" data-year="%d" aria-pressed="false"%s>%d</button>'
                      % (y, ' class="partial" title="partial year: %s &#8211; %s"'
                         % (fmt_day(first), fmt_day(last)) if partial else "", y))
        for a in ys:
            meta[str(a["id"])] = {
                "n": a["name"], "d": a["dt"].strftime("%d %b").lstrip("0"),
                "yr": y, "y": a["dt"].timetuple().tm_yday - 1,
                "mi": round(a["km"] * 0.621371, 2), "t": round(a["min"], 1),
                "ft": round(float(a.get("total_elevation_gain_m") or 0) * 3.28084),
                "f": a["fam"], "sp": a["sport_type"],
            }

    layers = "\n".join(year_layer(years[y], tracks, y, scale) for y in sorted(years))
    halo = ('paint-order="stroke" stroke="%s" stroke-width="5" stroke-linejoin="round"'
            % ink("art-bg", ART_BG, True))
    detail = ('<g id="art-rd-detail" pointer-events="none" style="display:none">'
              '<text id="art-rd-date" x="%.1f" y="%.1f" fill="%s" '
              'font-family="system-ui" font-size="13" letter-spacing="1.5" '
              'text-anchor="middle" %s></text>'
              '<text id="art-rd-name" x="%.1f" y="%.1f" fill="%s" '
              'font-family="system-ui" font-size="21" text-anchor="middle" %s></text>'
              '<text id="art-rd-stat" x="%.1f" y="%.1f" fill="%s" '
              'font-family="system-ui" font-size="15" letter-spacing="0.5" '
              'text-anchor="middle" %s></text>'
              '<text id="art-rd-sport" x="%.1f" y="%.1f" fill="%s" '
              'font-family="system-ui" font-size="12" letter-spacing="1.5" '
              'text-anchor="middle" %s></text></g>'
              % (C, C - 40, ink("art-sub", "#64748b", True), halo,
                 C, C - 8, ink("art-num", "#e2e8f0", True), halo,
                 C, C + 24, ink("art-stat", "#94a3b8", True), halo,
                 C, C + 50, ink("art-sub", "#64748b", True), halo))

    legend = "".join(
        '<button type="button" data-fam="%s" aria-pressed="true">'
        '<i class="art-sw art-fam-%s"></i>%s</button>' % (k, k, FAM_LABEL[k])
        for k in COLOR)
    # set via textContent, so this needs real characters -- HTML entities would
    # render literally
    hint = ("point at a spoke to light its route in the ground layer "
            "· drag to scrub the year")
    start = max(years, key=lambda y: len(years[y]))   # the fullest year lands first

    data = {"act": meta, "ndays": ndays_map, "start": str(start), "hint": hint,
            "years": sorted(years)}
    scrim_color = ink("art-bg", ART_BG, True)
    return (
        "<style>" + ART_CSS + "</style>\n"
        '<svg id="art-svg" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">\n' % (S, S)
        + '<defs><radialGradient id="art-scrim">'
          '<stop offset="0" stop-color="%s" stop-opacity="0.93"/>'
          '<stop offset="0.62" stop-color="%s" stop-opacity="0.86"/>'
          '<stop offset="1" stop-color="%s" stop-opacity="0"/>'
          '</radialGradient></defs>\n' % (scrim_color, scrim_color, scrim_color)
        + '<rect width="%d" height="%d" fill="%s"/>\n' % (S, S, scrim_color)
        + layers + "\n" + detail + "\n</svg>\n"
        '<div class="art-bar" id="art-legend">' + legend + "</div>\n"
        '<div class="art-bar" id="art-years">' + "".join(picker) + "</div>\n"
        '<div id="art-hint"></div>\n'
        "<script>\nwindow.ART_DATA=" + _js_json(data) + ";\n" + ART_JS + "</script>\n")
