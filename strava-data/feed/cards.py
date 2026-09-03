"""One function per e-paper card. Each returns a ``svg.Card``.

A card is a whole 800x480 screen carrying *one* idea - the Sticky is a fridge
magnet glanced at in passing, not a dashboard you sit in front of. The RSS
title and summary live on the same object so the two transports can never
drift apart.
"""

import math
from datetime import date

from nerd_common.format import mmss

from . import metrics as M
from . import svg as S
from .config import BLACK, DARK, H, LIGHT, PAD, W, WHITE
from .journey import BIKE_LADDER, RUN_LADDER, leg

TOP_RULE = 74
BOT_RULE = H - 62
CX = W / 2


def _chrome(card, kicker, asof):
    """Masthead + footer rules shared by every card."""
    # Reserve the right-hand date slot; a long kicker shrinks/ellipsizes
    # rather than running into it.
    ktext, ksize = S.fit_text(kicker.upper(), 26, W - 2 * PAD - 210, ratio=0.68)
    card.add(
        S.text(PAD, 46, ktext, ksize, "bold", tracking=3),
        S.text(W - PAD, 46, asof.strftime("%-d %b %Y").upper(), 26,
               anchor="end", fill=DARK, tracking=2),
        S.line(PAD, TOP_RULE, W - PAD, TOP_RULE, sw=4),
        S.line(PAD, BOT_RULE, W - PAD, BOT_RULE, stroke=LIGHT, sw=3),
    )
    return card


def _footer(card, s, size=26):
    s, size = S.fit_text(s, size, W - 2 * PAD)
    return card.add(S.text(PAD, H - 22, s, size, fill=DARK, tracking=1))


# --- A. right now --------------------------------------------------------

def card_load(b):
    """Idea 1 - ACWR on a four-band dial."""
    a = M.acwr(b["acts"], b["asof"])
    ratio = a["ratio"]
    c = S.Card(
        "load",
        f"Training load {ratio:.2f} — {a['band']}" if ratio else "Training load — no data",
        (f"Acute:chronic workload ratio is {ratio:.2f} ({a['band']}): the last 7 days of "
         f"suffer score against the 28-day average." if ratio else
         "Not enough recent suffer-score data to compute a load ratio."),
    )
    _chrome(c, "training load", b["asof"])
    if ratio is None:
        return _footer(c.add(S.text(CX, 280, "NO DATA", 90, "bold", anchor="middle")), "")

    cx, cy, r = CX, 298, 142
    # 0..2.0 across the top half-circle, so 1.0 sits straight up.
    def ang(v):
        return 180 + 180 * max(0.0, min(2.0, v)) / 2.0

    # Bands get monotonically more ink as risk rises - on a grey panel that
    # reads as a gradient of concern without needing a colour key.
    bands = [(0.0, 0.8, 0.25), (0.8, 1.3, 0.45), (1.3, 1.5, 0.7), (1.5, 2.0, 1.0)]
    for lo, hi, level in bands:
        c.add(S.arc(cx, cy, r, ang(lo), ang(hi), stroke=S.tone(level), sw=34))
    c.add(S.arc(cx, cy, r, 180, 360, stroke=BLACK, sw=3))

    # Boundary ticks, labelled just outside the arc.
    for v in (0.8, 1.3, 1.5):
        rad = math.radians(ang(v))
        c.add(S.line(cx + (r - 17) * math.cos(rad), cy + (r - 17) * math.sin(rad),
                     cx + (r + 17) * math.cos(rad), cy + (r + 17) * math.sin(rad),
                     stroke=BLACK, sw=3))
        lx, ly = cx + (r + 46) * math.cos(rad), cy + (r + 46) * math.sin(rad)
        c.add(S.text(lx, ly + 9, f"{v:g}", 26, fill=DARK, anchor="middle"))

    # Needle stops well short of the rim so it never crosses the readout.
    th = math.radians(ang(ratio))
    c.add(
        S.line(cx, cy, cx + (r * 0.60) * math.cos(th), cy + (r * 0.60) * math.sin(th),
               sw=9, cap="round"),
        S.circle(cx, cy, 14, fill=BLACK),
        S.text(cx, cy + 72, f"{ratio:.2f}", 84, "bold", anchor="middle"),
        S.text(cx, cy + 108, a["band"].upper(), 28, "bold", anchor="middle", tracking=5),
    )
    return _footer(c, f"7-day {a['acute']:.0f} vs 28-day average {a['chronic']:.0f}")


def card_route(b, ordinal):
    """Idea 36 - route of the day, one activity's GPS path filling the card."""
    r = M.route_of_day(b["acts"], ordinal)
    if r is None:
        return None
    act, path = r["act"], r["path"]
    c = S.Card(
        "route",
        f"Route of the day — {act['name']}",
        (f"{act['_mi']:.1f} mi, {act['_ft']:.0f} ft of climbing, "
         f"{act['_date'].strftime('%-d %b %Y')}."),
    )
    _chrome(c, "route of the day", b["asof"])

    # Fit the route to the right-hand rectangle, preserving aspect.
    rx, ry, rw, rh = 372, TOP_RULE + 18, W - PAD - 372, BOT_RULE - TOP_RULE - 36
    k = min(rw / r["w"], rh / r["h"])
    ox = rx + (rw - r["w"] * k) / 2
    oy = ry + (rh - r["h"] * k) / 2
    pts = [(ox + x * k, oy + y * k) for x, y in path]
    c.add(S.polyline(pts, sw=4))
    c.add(S.circle(pts[0][0], pts[0][1], 9, fill=WHITE, stroke=BLACK, sw=4))

    name, size = S.fit_text(act["name"], 38, 300)
    c.add(
        S.text(PAD, TOP_RULE + 74, name, size, "bold"),
        S.text(PAD, TOP_RULE + 134, f"{act['_mi']:.1f} mi", 54, "bold"),
        S.text(PAD, TOP_RULE + 180, f"{act['_ft']:.0f} ft climbed", 28, fill=DARK),
        S.text(PAD, TOP_RULE + 220, act["sport_type"], 28, fill=DARK),
    )
    return _footer(c, act["_date"].strftime("%A %-d %B %Y"))


# --- B. streaks ----------------------------------------------------------

def card_strip(b):
    """Idea 9 - the last 30 days as a dot strip you can read at arm's length."""
    days = M.last_30_strip(b["acts"], b["asof"])
    n = sum(days)
    st = M.streaks(b["acts"], b["asof"])
    c = S.Card(
        "strip",
        f"{n} active days in the last 30",
        (f"{n} of the last 30 days had an activity. Longest streak ever: "
         f"{st['longest']} days; {st['active_days']} active days out of {st['span_days']}."),
    )
    _chrome(c, "last 30 days", b["asof"])

    # Two rows of 15 rather than one row of 30: at 800 px across, a single
    # row forces 20 px cells (~2 mm on this panel) that vanish at arm's length.
    per_row, cell, gap = 15, 40, 8
    total = per_row * cell + (per_row - 1) * gap
    x0, y0 = CX - total / 2, 232
    for i, on in enumerate(days):
        row, col = divmod(i, per_row)
        c.add(S.rect(x0 + col * (cell + gap), y0 + row * (cell + 10), cell, cell,
                     fill=BLACK if on else WHITE, stroke=None if on else LIGHT, sw=3))
    c.add(
        S.text(CX, 190, f"{n} / 30", 92, "bold", anchor="middle"),
        S.text(x0, y0 + 2 * cell + 44, "30 DAYS AGO", 26, fill=DARK, tracking=2),
        S.text(x0 + total, y0 + 2 * cell + 44, "TODAY", 26, anchor="end",
               fill=DARK, tracking=2),
    )
    return _footer(c, f"longest streak ever {st['longest']} days · "
                      f"{st['active_days']} active of {st['span_days']}")


# --- C. volume & progress ------------------------------------------------

def card_odometer(b):
    """Idea 16 - rolling 12-month mileage as a mechanical odometer."""
    yr = M.totals(M.window(b["acts"], b["asof"], 365))
    digits = f"{yr['mi']:,.0f}"
    c = S.Card(
        "odometer",
        f"{digits} mi in the last 12 months",
        (f"{yr['mi']:,.0f} miles, {yr['ft']:,.0f} feet of climbing and "
         f"{yr['hours']:.0f} moving hours across {yr['n']} activities in the last 365 days."),
    )
    _chrome(c, "rolling 12 months", b["asof"])

    box_w, box_h, gap = 84, 130, 10
    chars = [ch for ch in digits]
    total = sum(box_w if ch.isdigit() else 34 for ch in chars) + gap * (len(chars) - 1)
    x, y = CX - total / 2, 150
    for ch in chars:
        w = box_w if ch.isdigit() else 34
        if ch.isdigit():
            c.add(S.rect(x, y, w, box_h, fill=WHITE, stroke=BLACK, sw=4),
                  S.text(x + w / 2, y + 100, ch, 96, "bold", anchor="middle"))
        else:
            c.add(S.text(x + w / 2, y + 100, ch, 96, "bold", anchor="middle", fill=DARK))
        x += w + gap
    c.add(S.text(CX, y + box_h + 52, "MILES · LAST 365 DAYS", 30, "bold",
                 anchor="middle", tracking=4))
    return _footer(c, f"{yr['n']} activities · {yr['ft']:,.0f} ft · {yr['hours']:.0f} moving hours")


def card_everest(b):
    """Idea 18 - all-time elevation as a stack of Everests."""
    e = M.everest(b["acts"])
    whole, frac = int(e["multiple"]), e["multiple"] - int(e["multiple"])
    c = S.Card(
        "everest",
        f"{e['ft']:,.0f} ft climbed — {e['multiple']:.1f} × Everest",
        (f"All-time elevation gain is {e['ft']:,.0f} feet, or {e['multiple']:.1f} times the "
         f"29,032-foot height of Everest."),
    )
    _chrome(c, "total elevation", b["asof"])

    size, gap = 138, 10
    shown = min(whole, 5)
    total = (shown + 1) * size + shown * gap
    x, y = CX - total / 2, 196
    for _ in range(shown):
        c.add(S.glyph_mountain(x, y, size, filled=True))
        x += size + gap
    # The partial Everest: same silhouette, hollow, filled from the base to
    # the fraction of a summit you are into.
    c.add(S.glyph_mountain(x, y, size, fill_frac=frac, fill_colour=S.tone(0.45)))

    c.add(
        S.text(PAD, 160, f"{e['ft']:,.0f} FT", 76, "bold"),
        S.text(W - PAD, 160, f"{e['multiple']:.1f}× EVEREST", 34, "bold",
               anchor="end", tracking=2),
    )
    return _footer(c, "Everest is 29,032 ft" + ("" if whole <= 5 else f" · {whole} summits, 5 drawn"))


def card_journey(b, group):
    """Idea 19 - the Journey ladder. ``group`` is 'run' or 'bike'."""
    if group == "run":
        total = M.totals(b["acts"], M.is_run)["mi"]
        ladder, glyph, label = RUN_LADDER, S.glyph_runner, "running"
    else:
        total = M.totals(b["acts"], M.is_bike)["mi"]
        ladder, glyph, label = BIKE_LADDER, S.glyph_bike, "riding"

    j = leg(total, ladder)
    ahead_city = j["ahead"][0]
    behind_city = j["behind"][0] if j["behind"] else "home (92129)"

    if j["lapped"]:
        title = f"{label.title()} · {total:,.0f} mi — {j['laps']:.1f}× the road to {ahead_city}"
        summary = (f"{total:,.0f} miles of {label} is {j['laps']:.1f} times the driving "
                   f"distance from 92129 to {ahead_city}.")
    else:
        title = f"{label.title()} · {total:,.0f} mi — {j['remaining_mi']:,.0f} mi short of {ahead_city}"
        summary = (f"Measured as a road trip out of 92129, {total:,.0f} miles of {label} puts you "
                   f"past {behind_city} and {j['frac'] * 100:.0f}% of the way on to {ahead_city} "
                   f"— {j['remaining_mi']:,.0f} miles to go.")

    c = S.Card(f"journey-{group}", title, summary)
    _chrome(c, f"{label} · out of 92129", b["asof"])

    c.add(
        S.text(PAD, 168, f"{total:,.0f}", 108, "bold"),
        S.text(_num_w(total), 168, "MI", 44, "bold", fill=DARK),
        glyph(W - PAD - 106, 74, 106),
    )

    # The whole route at a glance: every rung as a tick, filled to where you
    # are. Gives the leg ribbon below it some context without crowding it.
    final_city, final_mi = ladder[-1]
    bx0, bx1, by = PAD + 12, W - PAD - 12, 236
    span = bx1 - bx0
    done = span * min(1.0, total / final_mi)
    c.add(
        S.text(bx0, by - 14, "THE WHOLE ROUTE", 26, "bold", fill=DARK, tracking=2),
        S.text(bx1, by - 14, f"{final_city.upper()} · {final_mi:,} MI", 26,
               anchor="end", fill=DARK, tracking=2),
        S.rect(bx0, by, span, 14, fill=WHITE, stroke=DARK, sw=3),
        S.rect(bx0 + 2, by + 2, max(done - 4, 0), 10, fill=BLACK),
    )
    for _, rung_mi in ladder[:-1]:
        tx = bx0 + span * (rung_mi / final_mi)
        c.add(S.line(tx, by - 6, tx, by, stroke=DARK, sw=3))

    # The current leg: travelled behind you in solid black, the road ahead dashed.
    y = 322
    x0, x1 = PAD + 12, W - PAD - 12
    px = x0 + (x1 - x0) * j["frac"]
    c.add(
        S.line(x0, y, px, y, sw=6),
        S.line(px, y, x1, y, stroke=DARK, sw=5, dash="10 10"),
        S.circle(x0, y, 12, fill=BLACK),
        S.circle(x1, y, 12, fill=WHITE, stroke=BLACK, sw=5),
        glyph(px - 28, y - 62, 56),
    )
    bname, bsize = S.fit_text(behind_city.upper(), 28, 320)
    aname, asize = S.fit_text(ahead_city.upper(), 28, 320)
    c.add(
        S.text(x0, y + 46, bname, bsize, "bold", tracking=2),
        S.text(x1, y + 46, aname, asize, "bold", anchor="end", tracking=2),
    )
    if not j["behind"]:
        c.add(S.text(x0, y + 78, "START", 26, fill=DARK, tracking=2))

    if j["lapped"]:
        return _footer(c, f"{j['laps']:.1f} laps of the full route")
    return _footer(c, f"{j['remaining_mi']:,.0f} MI TO {ahead_city.upper()} · "
                      f"{j['frac'] * 100:.0f}% OF THIS LEG")


def _num_w(total):
    """Where the "MI" unit sits: past the big numeral, whose advance width we
    approximate rather than measure (no text metrics at build time)."""
    return PAD + len(f"{total:,.0f}") * 108 * 0.60 + 14


# --- D. segments ---------------------------------------------------------

def card_pr(b):
    """Idea 22 - the most recent segment PR, with its effort count as tallies."""
    pr = M.latest_pr(b["segs"], b["asof"])
    if pr is None:
        return None
    c = S.Card(
        "pr",
        f"PR — {pr['name']} in {mmss(pr['best_s'])}",
        (f"Latest segment PR: {pr['name']}, {mmss(pr['best_s'])} on effort "
         f"{pr['efforts']}. That is {pr['counts'][30]} PRs in 30 days and "
         f"{pr['counts'][365]} in the last year."),
    )
    _chrome(c, "latest segment pr", b["asof"])

    name, size = S.fit_text(pr["name"], 44, W - 2 * PAD)
    c.add(
        S.text(PAD, 138, name, size, "bold"),
        S.text(PAD, 234, mmss(pr["best_s"]), 92, "bold"),
        S.text(PAD + 250, 234, f"on effort {pr['efforts']}", 30, fill=DARK),
        S.text(PAD + 250, 196, pr["date"].strftime("%-d %b %Y").upper(), 26, fill=DARK, tracking=2),
    )

    # Effort count as tally marks - five-bar gates, capped so a 36x segment
    # does not run off the card.
    x, y = PAD, 300
    for i in range(min(pr["efforts"], 40)):
        gate, within = divmod(i, 5)
        gx = x + gate * 46
        if within < 4:
            c.add(S.line(gx + within * 9, y, gx + within * 9, y + 46, sw=4))
        else:
            c.add(S.line(gx - 4, y + 40, gx + 32, y + 6, sw=4))
    c.add(S.text(PAD, 388, f"{pr['efforts']} EFFORTS", 26, "bold", tracking=2))

    return _footer(c, f"{pr['counts'][30]} PRs in 30 days · {pr['counts'][90]} in 90 · "
                      f"{pr['counts'][365]} in a year")


# --- E. gear -------------------------------------------------------------

def card_shoes(b):
    """Ideas 30 & 31 - shoe mileage bars, and the retire-me alert."""
    sh = M.shoes(b["gear"], b["acts"])
    if not sh:
        return None
    over = [s for s in sh if s["over"]]
    c = S.Card(
        "shoes",
        (f"Retire the {over[0]['name']} — {over[0]['mi']:.0f} mi"
         if over else f"Shoes: {sh[0]['name']} at {sh[0]['mi']:.0f} mi"),
        (f"{over[0]['name']} is at {over[0]['mi']:.0f} miles against a "
         f"{over[0]['limit_mi']:.0f}-mile replacement threshold."
         if over else
         f"No shoe is past its replacement threshold; {sh[0]['name']} leads at "
         f"{sh[0]['mi']:.0f} of {sh[0]['limit_mi']:.0f} miles."),
    )
    _chrome(c, "shoe mileage", b["asof"])

    rows = sh[:3]
    y = 118
    for s in rows:
        c.add(S.glyph_shoe(PAD, y - 6, 78, fill_frac=min(s["frac"], 1.0)))
        name, size = S.fit_text(s["name"], 32, 440)
        c.add(S.text(PAD + 96, y + 26, name, size, "bold"))

        bx, bw, by, bh = PAD + 96, W - PAD - (PAD + 96), y + 42, 38
        c.add(S.rect(bx, by, bw, bh, fill=WHITE, stroke=BLACK, sw=3))
        c.add(S.rect(bx + 3, by + 3, (bw - 6) * min(s["frac"], 1.0), bh - 6,
                     fill=BLACK if s["over"] else S.tone(0.7)))
        c.add(S.text(W - PAD, y + 26, f"{s['mi']:.0f} / {s['limit_mi']:.0f} mi",
                     28, "bold", anchor="end", fill=DARK))
        if s["over"]:
            # Reversed out of the full black bar, so the alert needs no extra
            # row height and cannot collide with the shoe below it.
            c.add(S.text(bx + 16, by + 29, "RETIRE ME", 26, "bold",
                         fill=WHITE, tracking=3))
        y += 108

    return _footer(c, "threshold: Strava's own reminder, else 400 mi")


# --- J. voice ------------------------------------------------------------

def card_title(b, ordinal):
    """Idea 51 - an activity title and its description, typographically."""
    act = M.title_of_day(b["acts"], ordinal)
    if act is None:
        return None
    desc = (act.get("description") or "").strip()
    c = S.Card(
        "title",
        f"“{act['name']}”",
        desc or f"{act['_mi']:.1f} mi of {act['sport_type']} on "
                f"{act['_date'].strftime('%-d %b %Y')}.",
    )
    _chrome(c, "from the logbook", b["asof"])

    name, size = S.fit_text(act["name"], 62, W - 2 * PAD)
    c.add(S.text(PAD, 158, name, size, "bold"))

    # Wrap the description by character budget - there is no text measurement
    # at build time, so we approximate and cap at three lines.
    y = 222
    if desc:
        budget = int((W - 2 * PAD) / (30 * 0.55))
        words, lineno, cur = desc.split(), 0, ""
        for word in words:
            trial = f"{cur} {word}".strip()
            if len(trial) > budget:
                c.add(S.text(PAD, y, cur, 30, fill=DARK))
                y += 42
                lineno += 1
                cur = word
                if lineno == 2:
                    break
            else:
                cur = trial
        if lineno < 3 and cur:
            c.add(S.text(PAD, y, cur if lineno < 2 else cur[:budget - 1] + "…", 30, fill=DARK))

    c.add(S.text(PAD, BOT_RULE - 18,
                 f"{act['_mi']:.1f} MI · {act['sport_type'].upper()}", 28, "bold", tracking=2))
    return _footer(c, act["_date"].strftime("%A %-d %B %Y"))


# --- assembly ------------------------------------------------------------

def build_cards(bundle, today=None):
    """Every card, in feed order. Cards that lack data drop out silently."""
    today = today or date.today()
    ordinal = today.toordinal()
    cards = [
        card_journey(bundle, "run"),
        card_journey(bundle, "bike"),
        card_load(bundle),
        card_shoes(bundle),
        card_odometer(bundle),
        card_everest(bundle),
        card_strip(bundle),
        card_pr(bundle),
        card_route(bundle, ordinal),
        card_title(bundle, ordinal),
    ]
    return [c for c in cards if c is not None]


def card_of_the_day(cards, today=None):
    """Deterministic daily rotation - no device-side state, no scheduler."""
    today = today or date.today()
    return cards[today.toordinal() % len(cards)]
