"""Exploratory proofs for a calendar-year activity art piece (2025).

Standalone, like poster_40for40.py: reads strava-data/data/ directly, imports
nothing from feed/ or dashboard/. Writes four candidate concepts as one HTML
proof sheet under Project Docs/Plans/strava-data/year-art/.
"""
import csv, math, os, calendar
from collections import defaultdict
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "strava-data", "data")
OUT = os.path.join(ROOT, "Project Docs", "Plans", "strava-data", "year-art")
YEAR = 2025

# six families, same logic as the poster: colour must stay meaningful
FAMILY = {
    "Run": "run", "TrailRun": "run",
    "MountainBikeRide": "mtb", "Ride": "mtb", "EBikeRide": "mtb",
    "Hike": "foot", "Walk": "foot",
    "AlpineSki": "downhill", "Snowboard": "downhill",
    "NordicSki": "nordic", "IceSkate": "nordic",
    "RockClimbing": "other", "WeightTraining": "other", "Workout": "other",
    "Pickleball": "other", "StandUpPaddling": "other",
}
COLOR = {"run": "#2dd4bf", "mtb": "#f59e0b", "foot": "#a3e635",
         "downhill": "#60a5fa", "nordic": "#c084fc", "other": "#f472b6"}
BG = "#0b0f14"


def load():
    acts = []
    with open(os.path.join(DATA, "activities.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if not r["start_date_local"].startswith(str(YEAR)):
                continue
            r["dt"] = datetime.strptime(r["start_date_local"], "%Y-%m-%d %H:%M:%S")
            r["fam"] = FAMILY.get(r["sport_type"], "other")
            r["km"] = float(r["distance_km"] or 0)
            r["min"] = float(r["moving_time_min"] or 0)
            acts.append(r)
    acts.sort(key=lambda r: r["dt"])
    return acts


def track(aid, step=6):
    """Lat/lng track projected to local metres, recentred on its own origin."""
    p = os.path.join(DATA, "streams", str(aid) + ".csv")
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


def path(pts):
    return "M" + "L".join("%.1f %.1f" % (x, y) for x, y in pts)


# ---------------------------------------------------------------- concept A
def concept_grid(acts, tracks):
    """12 rows x 31 columns. One cell per day; route drawn at true relative
    scale within the month so a long day visibly dwarfs a short one."""
    CW, CH, GAP = 34, 34, 3
    W = 31 * (CW + GAP) + 90
    H = 12 * (CH + GAP) + 60
    by_day = defaultdict(list)
    for a in acts:
        by_day[a["dt"].date()].append(a)
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG)]
    for m in range(1, 13):
        y0 = 34 + (m - 1) * (CH + GAP)
        out.append('<text x="8" y="%.1f" fill="#64748b" font-family="system-ui" '
                   'font-size="11">%s</text>' % (y0 + CH / 2 + 4, calendar.month_abbr[m]))
        span = 1.0  # common scale for the month: the biggest day sets it
        for d in range(1, 32):
            try:
                dd = date(YEAR, m, d)
            except ValueError:
                continue
            for a in by_day.get(dd, []):
                t = tracks.get(a["id"])
                if t:
                    span = max(span,
                               max(p[0] for p in t) - min(p[0] for p in t),
                               max(p[1] for p in t) - min(p[1] for p in t))
        for d in range(1, 32):
            try:
                dd = date(YEAR, m, d)
            except ValueError:
                continue
            x0 = 60 + (d - 1) * (CW + GAP)
            out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="#12181f" '
                       'stroke="#1c2530" stroke-width="0.7"/>' % (x0, y0, CW, CH))
            for a in by_day.get(dd, []):
                t = tracks.get(a["id"])
                c = COLOR[a["fam"]]
                if not t:  # no GPS: a ring sized by duration
                    r = 2 + min(a["min"], 120) / 40
                    out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" '
                               'stroke="%s" stroke-width="1.4"/>'
                               % (x0 + CW / 2, y0 + CH / 2, r, c))
                    continue
                s = (CW * 0.84) / span
                cx = sum(p[0] for p in t) / len(t)
                cy = sum(p[1] for p in t) / len(t)
                pp = [((x - cx) * s + x0 + CW / 2, (y - cy) * s + y0 + CH / 2) for x, y in t]
                out.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.9" '
                           'stroke-linejoin="round" opacity="0.95"/>' % (path(pp), c))
    for d in range(1, 32):
        out.append('<text x="%.1f" y="24" fill="#475569" text-anchor="middle" '
                   'font-family="system-ui" font-size="9">%d</text>'
                   % (60 + (d - 1) * (CW + GAP) + CW / 2, d))
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- concept B
def concept_spiral(acts, tracks):
    """A year-clock: 365 days around a ring, each activity a radial bar whose
    length is distance and whose width is duration. Sport by colour."""
    S = 820
    C = S / 2
    R0, R1 = 150, 380
    mx = max(a["km"] for a in acts) or 1
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (S, S),
           '<rect width="%d" height="%d" fill="%s"/>' % (S, S, BG)]
    for m in range(12):
        deg = (date(YEAR, m + 1, 1).timetuple().tm_yday - 1) / 365 * 360 - 90
        a = math.radians(deg)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#1e293b" '
                   'stroke-width="1"/>' % (C + R0 * math.cos(a), C + R0 * math.sin(a),
                                           C + (R1 + 16) * math.cos(a),
                                           C + (R1 + 16) * math.sin(a)))
        am = math.radians(deg + 15)
        out.append('<text x="%.1f" y="%.1f" fill="#475569" font-family="system-ui" '
                   'font-size="13" text-anchor="middle">%s</text>'
                   % (C + (R1 + 34) * math.cos(am), C + (R1 + 34) * math.sin(am),
                      calendar.month_abbr[m + 1]))
    out.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="none" stroke="#1e293b"/>' % (C, C, R0))
    for a in acts:
        ang = math.radians((a["dt"].timetuple().tm_yday - 1) / 365 * 360 - 90)
        ln = R0 + (R1 - R0) * math.sqrt(a["km"] / mx)
        w = 1.2 + min(a["min"], 240) / 60
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="%.1f" stroke-linecap="round" opacity="0.85"/>'
                   % (C + R0 * math.cos(ang), C + R0 * math.sin(ang),
                      C + ln * math.cos(ang), C + ln * math.sin(ang), COLOR[a["fam"]], w))
    tot = sum(a["km"] for a in acts) * 0.621371
    out.append('<text x="%.1f" y="%.1f" fill="#e2e8f0" font-family="system-ui" '
               'font-size="44" text-anchor="middle">%d</text>' % (C, C - 6, YEAR))
    out.append('<text x="%.1f" y="%.1f" fill="#64748b" font-family="system-ui" '
               'font-size="15" text-anchor="middle">%d activities &#183; %s mi</text>'
               % (C, C + 26, len(acts), format(int(round(tot)), ",")))
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- concept C
def concept_bloom(acts, tracks):
    """Every route of the year overlaid from a common origin, rotated by its
    day-of-year. The year becomes one organism rather than 194 pictures."""
    S = 860
    C = S / 2
    keep = [(a, tracks[a["id"]]) for a in acts if tracks.get(a["id"])]
    ext = max(max(max(abs(x), abs(y)) for x, y in t) for _, t in keep)
    s = (S * 0.46) / ext
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (S, S),
           '<rect width="%d" height="%d" fill="%s"/>' % (S, S, BG)]
    for a, t in keep:
        th = (a["dt"].timetuple().tm_yday - 1) / 365 * 2 * math.pi
        ct, st = math.cos(th), math.sin(th)
        pp = [(C + (x * ct - y * st) * s, C + (x * st + y * ct) * s) for x, y in t]
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.8" '
                   'opacity="0.5" stroke-linejoin="round"/>' % (path(pp), COLOR[a["fam"]]))
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- concept D
def concept_clock(acts, tracks):
    """Time-of-day tapestry: x = day of year, y = clock time. Each activity is
    a bar at the hour it actually happened, thickness = distance."""
    W, H = 1100, 460
    L, T = 46, 24
    pw, ph = W - L - 16, H - T - 30
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG)]
    for hr in range(0, 25, 3):
        y = T + hr / 24 * ph
        out.append('<line x1="%d" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#1a222c"/>'
                   % (L, y, L + pw, y))
        out.append('<text x="%d" y="%.1f" fill="#475569" text-anchor="end" '
                   'font-family="system-ui" font-size="10">%02d:00</text>' % (L - 8, y + 4, hr))
    for m in range(1, 13):
        x = L + (date(YEAR, m, 1).timetuple().tm_yday - 1) / 365 * pw
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%.1f" stroke="#1a222c"/>'
                   % (x, T, x, T + ph))
        out.append('<text x="%.1f" y="%d" fill="#475569" font-family="system-ui" '
                   'font-size="10">%s</text>' % (x + 4, H - 10, calendar.month_abbr[m]))
    for a in acts:
        x = L + (a["dt"].timetuple().tm_yday - 1) / 365 * pw
        y0 = T + (a["dt"].hour + a["dt"].minute / 60) / 24 * ph
        y1 = y0 + max(a["min"], 8) / 60 / 24 * ph
        w = 1.4 + min(a["km"], 25) / 6
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="%.1f" stroke-linecap="round" opacity="0.8"/>'
                   % (x, y0, x, y1, COLOR[a["fam"]], w))
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------ the piece (B+C)
def concept_year(acts, tracks, interactive=False):
    """The chosen composition: the year clock (B) standing on the bloom (C).

    The bloom is the ground -- every track of the year from a shared origin,
    rotated by day-of-year -- held far back in tone so it reads as texture, not
    as data. The clock is the figure. A radial scrim between the two layers
    keeps the ring band and the centre type legible over whatever the bloom
    happens to be doing underneath.

    With interactive=True every spoke and its own bloom trace carry a shared
    data-id, so hovering one can light the other -- the whole point of stacking
    these two views rather than showing them side by side. It also emits fat
    transparent hit lines (a spoke is ~2px wide and a day is ~7px of arc, so the
    drawn geometry is not a usable target) and a second centre readout group for
    the JS to swap in.
    """
    S = 900
    C = S / 2
    R0, R1 = 168, 402
    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (S, S),
           '<defs>',
           # scrim: transparent at the rim, opaque toward the middle
           # scrim: a tight disc behind the centre type only. It must not reach
           # the ring band, or it erases the bloom exactly where the bloom is
           # densest (every track shares an origin, so the core is the middle).
           '<radialGradient id="scrim">'
           '<stop offset="0" stop-color="%s" stop-opacity="0.93"/>'
           '<stop offset="0.62" stop-color="%s" stop-opacity="0.86"/>'
           '<stop offset="1" stop-color="%s" stop-opacity="0"/>'
           '</radialGradient>' % (BG, BG, BG),
           '</defs>',
           '<rect width="%d" height="%d" fill="%s"/>' % (S, S, BG)]

    # --- ground: the bloom, scaled so a typical route fills the frame. The
    # handful of travel days deliberately run off-canvas rather than shrinking
    # everything else to fit them.
    keep = [(a, tracks[a["id"]]) for a in acts if tracks.get(a["id"])]
    exts = sorted(max(max(abs(x), abs(y)) for x, y in t) for _, t in keep)
    ext = exts[int(len(exts) * 0.85)]
    s = (S * 0.46) / ext
    out.append('<g id="bloom" stroke-linejoin="round" fill="none">')
    for a, t in keep:
        th = (a["dt"].timetuple().tm_yday - 1) / 365 * 2 * math.pi
        ct, st = math.cos(th), math.sin(th)
        pp = [(C + (x * ct - y * st) * s, C + (x * st + y * ct) * s) for x, y in t]
        tag = ('class="trace fam-%s" data-id="%s" ' % (a["fam"], a["id"])) if interactive else ""
        out.append('<path %sd="%s" stroke="%s" stroke-width="0.9" opacity="0.38"/>'
                   % (tag, path(pp), COLOR[a["fam"]]))
    out.append('</g>')
    out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#scrim)"/>'
               % (C, C, R0 * 1.04))

    # --- figure: the year clock
    mx = max(a["km"] for a in acts) or 1
    for m in range(12):
        deg = (date(YEAR, m + 1, 1).timetuple().tm_yday - 1) / 365 * 360 - 90
        a = math.radians(deg)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#243244" '
                   'stroke-width="1"/>' % (C + R0 * math.cos(a), C + R0 * math.sin(a),
                                           C + (R1 + 16) * math.cos(a),
                                           C + (R1 + 16) * math.sin(a)))
        am = math.radians(deg + 15)
        out.append('<text x="%.1f" y="%.1f" fill="#7c8ba1" font-family="system-ui" '
                   'font-size="14" letter-spacing="1.5" text-anchor="middle" '
                   'paint-order="stroke" stroke="%s" stroke-width="5" '
                   'stroke-linejoin="round">%s</text>'
                   % (C + (R1 + 36) * math.cos(am), C + (R1 + 36) * math.sin(am), BG,
                      calendar.month_abbr[m + 1].upper()))
    out.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="none" stroke="#243244"/>'
               % (C, C, R0))
    out.append('<g id="spokes">')
    for a in acts:
        ang = math.radians((a["dt"].timetuple().tm_yday - 1) / 365 * 360 - 90)
        ln = R0 + (R1 - R0) * math.sqrt(a["km"] / mx)
        w = 1.2 + min(a["min"], 240) / 60
        tag = ('class="spoke fam-%s" data-id="%s" ' % (a["fam"], a["id"])) if interactive else ""
        out.append('<line %sx1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="%.1f" stroke-linecap="round" opacity="0.9"/>'
                   % (tag, C + R0 * math.cos(ang), C + R0 * math.sin(ang),
                      C + ln * math.cos(ang), C + ln * math.sin(ang), COLOR[a["fam"]], w))
    out.append('</g>')

    tot = sum(a["km"] for a in acts) * 0.621371
    days = len(set(a["dt"].date() for a in acts))
    out.append('<g id="rd-default">')
    out.append('<text x="%.1f" y="%.1f" fill="#e2e8f0" font-family="system-ui" '
               'font-size="52" letter-spacing="4" text-anchor="middle" paint-order="stroke" '
               'stroke="%s" stroke-width="7" stroke-linejoin="round">%d</text>'
               % (C, C - 4, BG, YEAR))
    out.append('<text x="%.1f" y="%.1f" fill="#64748b" font-family="system-ui" '
               'font-size="14" letter-spacing="1" text-anchor="middle" paint-order="stroke" '
               'stroke="%s" stroke-width="5" stroke-linejoin="round">'
               '%d activities &#183; %d days &#183; %s mi</text>'
               % (C, C + 28, BG, len(acts), days, format(int(round(tot)), ",")))
    out.append('</g>')

    if interactive:
        # readout that replaces the default block while an activity is selected
        halo = 'paint-order="stroke" stroke="%s" stroke-width="5" stroke-linejoin="round"' % BG
        out.append('<g id="rd-detail" style="display:none">')
        out.append('<text id="rd-date" x="%.1f" y="%.1f" fill="#64748b" '
                   'font-family="system-ui" font-size="13" letter-spacing="1.5" '
                   'text-anchor="middle" %s></text>' % (C, C - 40, halo))
        out.append('<text id="rd-name" x="%.1f" y="%.1f" fill="#e2e8f0" '
                   'font-family="system-ui" font-size="21" text-anchor="middle" '
                   '%s></text>' % (C, C - 8, halo))
        out.append('<text id="rd-stat" x="%.1f" y="%.1f" fill="#94a3b8" '
                   'font-family="system-ui" font-size="15" letter-spacing="0.5" '
                   'text-anchor="middle" %s></text>' % (C, C + 24, halo))
        out.append('<text id="rd-sport" x="%.1f" y="%.1f" fill="#64748b" '
                   'font-family="system-ui" font-size="12" letter-spacing="1.5" '
                   'text-anchor="middle" %s></text>' % (C, C + 50, halo))
        out.append('</g>')
        # hit targets last so they sit on top; full-length so a short spoke is
        # no harder to reach than a long one
        out.append('<g id="hits" fill="none" stroke="transparent" stroke-width="13" '
                   'stroke-linecap="round" pointer-events="stroke">')
        for a in acts:
            ang = math.radians((a["dt"].timetuple().tm_yday - 1) / 365 * 360 - 90)
            out.append('<line class="hit" data-id="%s" x1="%.1f" y1="%.1f" '
                       'x2="%.1f" y2="%.1f"/>'
                       % (a["id"], C + R0 * math.cos(ang), C + R0 * math.sin(ang),
                          C + (R1 + 8) * math.cos(ang), C + (R1 + 8) * math.sin(ang)))
        out.append('</g>')

    out.append("</svg>")
    return "\n".join(out)


CONCEPTS = [
    ("year", "The piece &#183; year clock on the bloom",
     "B standing on C: every 2025 track from a shared origin, rotated by day of "
     "year, held back as ground; the year clock as figure. Bar length = distance, "
     "thickness = duration, colour = sport family.", concept_year),
    ("grid", "A &#183; Calendar grid",
     "12&#215;31 cells, one route per day at true relative scale within its month. "
     "Rest days are the negative space.", concept_grid),
    ("spiral", "B &#183; Year clock",
     "365 days around a ring; bar length = distance, thickness = duration. "
     "Reads as a single object at any size.", concept_spiral),
    ("bloom", "C &#183; Bloom",
     "Every GPS track overlaid from a shared origin, rotated by day of year. "
     "The shape of a year&#8217;s movement, not a map.", concept_bloom),
    ("clock", "D &#183; Time-of-day tapestry",
     "x = day of year, y = wall clock. Shows when you move, and how the season "
     "pushes it around.", concept_clock),
]


FAM_LABEL = {"run": "run", "mtb": "bike", "foot": "hike / walk",
             "downhill": "downhill", "nordic": "nordic / skate", "other": "other"}

PAGE_CSS = """
html,body{height:100%;margin:0;background:BGCOL;
  font:15px/1.5 system-ui,-apple-system,sans-serif;color:#94a3b8}
body{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
#art{width:min(94vw,82vh);height:auto;display:block;touch-action:none;
  -webkit-tap-highlight-color:transparent}
/* selection: the spoke and its own bloom trace light together */
#art.sel .spoke:not(.on){opacity:.24}
#art.sel .trace:not(.on){opacity:.13}
.spoke.on{opacity:1;filter:drop-shadow(0 0 5px currentColor)}
.trace.on{opacity:1;stroke-width:2.4}
.spoke,.trace{transition:opacity .12s}
/* family filter */
.spoke.off,.trace.off{opacity:.04}
#art.sel .spoke.off,#art.sel .trace.off{opacity:.04}
.hit{cursor:crosshair}
.hit.off{pointer-events:none}
#legend{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;max-width:min(94vw,82vh)}
#legend button{display:flex;align-items:center;gap:7px;background:none;border:1px solid #1e293b;
  border-radius:999px;padding:5px 12px;color:#94a3b8;font:inherit;font-size:13px;cursor:pointer}
#legend button:hover{border-color:#334155;color:#cbd5e1}
#legend button[aria-pressed=false]{opacity:.36}
#legend i{width:10px;height:10px;border-radius:2px;display:block}
#hint{font-size:12px;color:#475569;min-height:1.2em}
"""

PAGE_JS = """
(function(){
  var art=document.getElementById('art'), hint=document.getElementById('hint');
  var def=document.getElementById('rd-default'), det=document.getElementById('rd-detail');
  var fDate=document.getElementById('rd-date'), fName=document.getElementById('rd-name');
  var fStat=document.getElementById('rd-stat'), fSport=document.getElementById('rd-sport');
  var spokes={}, traces={}, hits={};
  function index(sel,map){
    Array.prototype.forEach.call(art.querySelectorAll(sel),function(el){
      map[el.getAttribute('data-id')]=el; });
  }
  index('.spoke',spokes); index('.trace',traces); index('.hit',hits);
  var off={}, cur=null;

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
    if(!id){ art.classList.remove('sel'); def.style.display=''; det.style.display='none';
             hint.textContent=HINT; return; }
    var a=ACT[id];
    if(spokes[id]) spokes[id].classList.add('on');
    if(traces[id]) traces[id].classList.add('on');
    art.classList.add('sel'); def.style.display='none'; det.style.display='';
    fDate.textContent=a.d.toUpperCase();
    setName(a.n);
    fStat.textContent=a.mi.toFixed(1)+' mi \\u00b7 '+dur(a.t)+
      (a.ft>50 ? ' \\u00b7 '+Math.round(a.ft).toLocaleString()+' ft' : '');
    hint.textContent = traces[id] ? '' : 'no GPS for this one \\u2014 nothing in the ground layer';
    fSport.textContent=a.sp.toUpperCase();
  }

  // desktop: point at a spoke
  art.addEventListener('pointerover',function(e){
    var h=e.target.closest && e.target.closest('.hit');
    if(h) select(h.getAttribute('data-id'));
  });
  art.addEventListener('pointerleave',function(){ if(!drag) select(null); });

  // touch (and mouse-drag): scrub a hand around the year. A day is ~7px of arc
  // at the rim, so tapping individual spokes is not viable on a phone.
  var drag=false;
  function scrub(e){
    var r=art.getBoundingClientRect();
    var x=e.clientX-(r.left+r.width/2), y=e.clientY-(r.top+r.height/2);
    if(Math.sqrt(x*x+y*y) < r.width*0.12) { select(null); return; }
    var deg=(Math.atan2(y,x)*180/Math.PI+90+360)%360;
    var day=deg/360*365, best=null, bd=1e9;
    for(var id in ACT){
      if(off[ACT[id].f]) continue;
      var d=Math.abs(ACT[id].y-day); if(d>182.5) d=365-d;
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

  // family filter
  Array.prototype.forEach.call(document.querySelectorAll('#legend button'),function(b){
    b.addEventListener('click',function(){
      var f=b.getAttribute('data-fam');
      off[f]=!off[f];
      b.setAttribute('aria-pressed', off[f] ? 'false' : 'true');
      Array.prototype.forEach.call(art.querySelectorAll('.fam-'+f),function(el){
        el.classList.toggle('off', !!off[f]); });
      Array.prototype.forEach.call(art.querySelectorAll('.hit'),function(el){
        el.classList.toggle('off', !!off[ACT[el.getAttribute('data-id')].f]); });
      if(cur && off[ACT[cur].f]) select(null);
    });
  });
  hint.textContent=HINT;
})();
"""


def build_page(acts, tracks):
    """The interactive piece: hover/scrub links a spoke to its own bloom trace,
    the centre well becomes the readout, and the legend filters by family."""
    import json

    meta = {}
    for a in acts:
        meta[str(a["id"])] = {
            "n": a["name"], "d": a["dt"].strftime("%d %b").lstrip("0"),
            "y": a["dt"].timetuple().tm_yday - 1,
            "mi": round(a["km"] * 0.621371, 2), "t": round(a["min"], 1),
            "ft": round(float(a.get("total_elevation_gain_m") or 0) * 3.28084),
            "f": a["fam"], "sp": a["sport_type"],
        }
    legend = "".join(
        '<button data-fam="%s" aria-pressed="true"><i style="background:%s"></i>%s</button>'
        % (k, COLOR[k], FAM_LABEL[k]) for k in COLOR)
    hint = ("point at a spoke to light its route in the ground layer "
            "· drag to scrub the year")
    return ("<!doctype html><meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<title>" + str(YEAR) + " in motion</title>\n"
            "<style>" + PAGE_CSS.replace("BGCOL", BG) + "</style>\n"
            + concept_year(acts, tracks, interactive=True).replace(
                "<svg ", "<svg id=\"art\" ", 1) + "\n"
            "<div id=\"legend\">" + legend + "</div>\n"
            "<div id=\"hint\"></div>\n"
            "<script>\nvar ACT=" + json.dumps(meta, ensure_ascii=False) + ";\n"
            "var HINT=" + json.dumps(hint) + ";\n"
            + PAGE_JS + "</script>\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    acts = load()
    tracks = {}
    for a in acts:
        t = track(a["id"])
        if t:
            tracks[a["id"]] = t
    print("%d activities, %d with usable GPS" % (len(acts), len(tracks)))

    cards = []
    for slug, title, blurb, fn in CONCEPTS:
        svg = fn(acts, tracks)
        with open(os.path.join(OUT, slug + ".svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        cards.append('<section><h2>%s</h2><p>%s</p><div class="art">%s</div></section>'
                     % (title, blurb, svg))
        print("wrote", slug + ".svg")

    legend = " ".join('<span><i style="background:%s"></i>%s</span>' % (c, k)
                      for k, c in COLOR.items())
    html = """<!doctype html><meta charset="utf-8"><title>%d year-art proofs</title>
<style>
body{background:#070a0e;color:#cbd5e1;font:15px/1.6 system-ui,sans-serif;margin:0;padding:40px}
h1{font-weight:600;font-size:26px;margin:0 0 4px}
h2{font-size:17px;font-weight:600;color:#e2e8f0;margin:0 0 4px}
p{margin:0 0 14px;color:#64748b;max-width:70ch}
section{max-width:1180px;margin:0 auto 56px}
.art{background:%s;border:1px solid #1c2530;border-radius:10px;padding:10px}
.art svg{width:100%%;height:auto;display:block}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:0 auto 40px;max-width:1180px;color:#94a3b8;font-size:13px}
.legend span{display:flex;align-items:center;gap:6px}
.legend i{width:11px;height:11px;border-radius:2px;display:block}
</style>
<section><h1>%d in motion &#8212; proofs</h1>
<p>%d activities, %d with GPS. Four directions for a calendar-year piece.</p></section>
<div class="legend">%s</div>
%s
""" % (YEAR, BG, YEAR, len(acts), len(tracks), legend, "".join(cards))
    p = os.path.join(OUT, "proofs.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", p)

    p = os.path.join(OUT, "year.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(build_page(acts, tracks))
    print("wrote", p)


if __name__ == "__main__":
    main()
