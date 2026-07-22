"""Hand-rolled HTML/SVG components: stat/PR/race cards, the SVG heatmap calendar,
the per-date detail index, and the training-notes search panel."""

import html
import json
from collections import defaultdict
from datetime import date, timedelta

from dashboard.config import (
    ACCENT, LONG_COLOR, MONTH_ABBR, TEMPO_COLOR, TEXT_TERTIARY, TYPE_COLORS,
    TYPE_LABELS, WORKOUT_COLOR,
)
from dashboard.data import map_type, maybe_float


def stat_card_html(label, value):
    return f"""
    <div class="stat-card">
      <div class="stat-num">{value}</div>
      <div class="stat-label">{label}</div>
    </div>"""


def pr_card_html(card):
    return f"""
    <div class="pr-card" style="--pr-color: {card['color']}">
      <div class="pr-label">{card['label']}</div>
      <div class="pr-time">{html.escape(card['time'])}</div>
      <div class="pr-season">{html.escape(card['season'])}</div>
    </div>"""


def race_card_html(race):
    type_color = LONG_COLOR if race["category"] == "crossCountry" else (
        WORKOUT_COLOR if race["category"] == "indoorTrack" else TEMPO_COLOR
    )
    type_label = {"crossCountry":"XC", "indoorTrack":"Indoor", "outdoorTrack":"Outdoor"}[race["category"]]
    pr_badge = '<span class="pr-badge">PR</span>' if race.get("pr") else ""
    relay = '<span class="relay-tag">relay</span>' if race["is_relay"] else ""
    return f"""
    <div class="race-card" data-date="{race['date']}" tabindex="0" role="button">
      <span class="race-type-badge" style="--badge-color: {type_color}">{type_label}</span>
      <div class="race-meta">
        <div class="race-name">{html.escape(race['race'])}</div>
        <div class="race-sub">{html.escape(race['season'])} · {html.escape(race['distance'])}</div>
      </div>
      <div class="race-time">{html.escape(race['time'])}{relay}</div>
      {pr_badge}
    </div>"""


def heatmap_html(rows):
    """Hand-rolled SVG calendar heatmap, year-rows × (weeks × 7 days), with two
    color modes (Workout Type / Miles Intensity). Mode toggle is a JS click."""

    # Bucket miles + type per date
    by_date = {}
    for r in rows:
        if not r["date"]:
            continue
        miles = maybe_float(r["miles"]) or 0
        if miles <= 0 and r["is_race"] != "1":
            continue
        t = map_type(r["workout_type"], r["is_race"] == "1")
        prev = by_date.get(r["date"])
        if prev is None or miles > prev["miles"]:
            by_date[r["date"]] = {"miles": miles, "type": t}

    if not by_date:
        return "<div class='heatmap-empty'>No data</div>"

    years = sorted({int(d.split("-")[0]) for d in by_date})

    cell    = 11
    gap     = 2
    label_w = 28
    week_w  = cell + gap

    # Map a date to its column-day index, where 0 = Sunday … 6 = Saturday.
    def sun_dow(d):
        return (d.weekday() + 1) % 7

    rows_html = []
    for year in years:
        # All Sundays from the year's first week to year's last
        start = date(year, 1, 1)
        # Roll back to the Sunday on/before Jan 1
        start -= timedelta(days=sun_dow(start))
        end   = date(year, 12, 31)
        end   += timedelta(days=(6 - sun_dow(end)))   # roll forward to Saturday

        n_weeks = ((end - start).days + 1) // 7
        svg_w = label_w + n_weeks * week_w + 8
        svg_h = 7 * (cell + gap) + 22  # +22 for month labels

        cells = []
        month_labels = []
        last_month_label_x = -100
        for w in range(n_weeks):
            for dow in range(7):
                cur = start + timedelta(weeks=w, days=dow)
                if cur.year != year:
                    continue
                ds = cur.isoformat()
                rec = by_date.get(ds)
                x = label_w + w * week_w
                y = 14 + dow * (cell + gap)
                if rec:
                    miles = rec["miles"]
                    type_color = TYPE_COLORS[rec["type"]]
                    type_op    = min(1.0, 0.30 + (miles / 14) * 0.70)
                    # Discrete intensity bins (GitHub-style) for stronger contrast
                    if   miles >= 12: intens_op = 1.00
                    elif miles >=  8: intens_op = 0.78
                    elif miles >=  4: intens_op = 0.55
                    else:             intens_op = 0.32
                    title = f"{ds}: {miles:.1f} mi · {TYPE_LABELS[rec['type']]}"
                    cells.append(
                        f'<rect class="hm-cell" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                        f'data-date="{ds}" '
                        f'data-type-color="{type_color}" data-type-op="{type_op:.2f}" '
                        f'data-int-op="{intens_op:.2f}" '
                        f'fill="{ACCENT}" fill-opacity="{intens_op:.2f}">'
                        f'<title>{title}</title></rect>'
                    )
                else:
                    cells.append(
                        f'<rect class="hm-cell hm-rest" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                        f'fill="{TEXT_TERTIARY}" fill-opacity="0.10"></rect>'
                    )
            # Month label: print when crossing into a new month
            mid_date = start + timedelta(weeks=w, days=3)
            if mid_date.year == year and mid_date.day <= 7:
                if x - last_month_label_x > 30:
                    month_labels.append(
                        f'<text x="{x}" y="10" class="hm-month">{MONTH_ABBR[mid_date.month-1]}</text>'
                    )
                    last_month_label_x = x

        dow_labels = []
        for i, lbl in enumerate(("S","M","T","W","T","F","S")):
            dow_labels.append(
                f'<text x="0" y="{14 + i*(cell+gap) + 9}" class="hm-dow">{lbl}</text>'
            )

        rows_html.append(f"""
          <div class="hm-year-row">
            <div class="hm-year">{year}</div>
            <svg viewBox="0 0 {svg_w} {svg_h}" width="100%" preserveAspectRatio="xMinYMid meet">
              {"".join(month_labels)}
              {"".join(dow_labels)}
              {"".join(cells)}
            </svg>
          </div>""")

    legend_type = " ".join(
        f'<span class="hm-legend-item"><span class="swatch" style="background:{TYPE_COLORS[k]}"></span>{TYPE_LABELS[k]}</span>'
        for k in ("easy","long","tempo","workout","race")
    )
    legend_intensity = (
        '<span class="hm-legend-meta">0 mi</span>'
        '<span class="hm-legend-grad" title="Miles per day"></span>'
        '<span class="hm-legend-meta">12+ mi</span>'
    )

    return f"""
    <div class="card heatmap-card">
      <div class="card-header">
        <div class="card-title">Training Calendar</div>
        <div class="hm-mode-toggle">
          <button class="hm-toggle" data-mode="type">Workout Type</button>
          <button class="hm-toggle active" data-mode="intensity">Miles Intensity</button>
        </div>
      </div>
      <div class="hm-legend hm-legend-type" data-mode="type" hidden>{legend_type}</div>
      <div class="hm-legend hm-legend-intensity" data-mode="intensity">{legend_intensity}</div>
      <div class="hm-grid">{"".join(rows_html)}</div>
    </div>"""


def build_day_index(rows):
    """Per-date map of all log entries, used by the click-to-detail panel."""
    idx = defaultdict(list)
    for r in rows:
        if not r["date"]:
            continue
        is_race = r["is_race"] == "1"
        idx[r["date"]].append({
            "type":      map_type(r["workout_type"], is_race),
            "type_raw":  r["workout_type"] or "",
            "miles":     maybe_float(r["miles"]),
            "minutes":   maybe_float(r["minutes"]),
            "pace":      r["pace_min_per_mile"] or "",
            "comments":  r["comments"] or "",
            "extras":    r["extras"] or "",
            "is_race":   is_race,
            "race":      r["race_name"] or "",
            "race_dist": r["race_distance"] or "",
            "race_time": r["race_time"] or "",
        })
    return dict(idx)


def notes_search_html(rows):
    """Renders the search input + filter pills + scrollable note list. JS does
    the live filtering on the client."""

    notes = []
    for r in rows:
        c = (r["comments"] or "").strip()
        if not c:
            continue
        t = map_type(r["workout_type"], r["is_race"] == "1")
        notes.append({
            "date":  r["date"],
            "miles": maybe_float(r["miles"]) or 0,
            "type":  t,
            "note":  c,
            "race":  r["is_race"] == "1",
            "race_name": r["race_name"] or "",
        })
    notes.sort(key=lambda n: n["date"], reverse=True)

    rows_json = json.dumps(notes)

    pills = "".join(
        f'<button class="filter-pill" data-type="{k}" style="--pill-color: {TYPE_COLORS[k]}">{TYPE_LABELS[k]}</button>'
        for k in ("easy","long","tempo","workout","race")
    )

    return f"""
    <div class="card notes-card">
      <div class="card-header">
        <div class="card-title">Training Notes</div>
        <div class="notes-count" id="notes-count"></div>
      </div>
      <div class="notes-search">
        <input type="text" id="notes-query" placeholder="Search notes…" autocomplete="off"/>
        <button id="notes-clear" hidden>×</button>
      </div>
      <div class="filter-pills">
        <button class="filter-pill active" data-type="all">All</button>
        {pills}
      </div>
      <div class="notes-list" id="notes-list"></div>
      <script id="notes-data" type="application/json">{rows_json}</script>
    </div>"""
