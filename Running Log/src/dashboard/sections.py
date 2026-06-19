"""The six page-section assemblers (Overview, Volume, Workout Mix, Performance,
Races, Patterns) that combine charts, cards, and components into HTML."""

import json
from collections import defaultdict

from dashboard.config import LONG_COLOR, TEMPO_COLOR, TYPE_COLORS, TYPE_LABELS, WORKOUT_COLOR
from dashboard.charts import (
    PR_PROGRESSION_SPECS, chart_cumulative, chart_dow, chart_easy_pace,
    chart_monthly_avg, chart_monthly_mileage_by_year, chart_pace_timeline,
    chart_pr_progression, chart_seasonal_sparklines, chart_weekly,
    chart_workout_donut, chart_workout_mix_by_season,
)
from dashboard.components import heatmap_html, notes_search_html, pr_card_html, stat_card_html
from dashboard.data import map_type, maybe_float
from dashboard.stats import compute_pr_cards
from dashboard.theme import fig_html


def section_overview(rows, stats):
    cards = [
        stat_card_html("Total Miles", f"{stats['totalMiles']:,}"),
        stat_card_html("Avg Mi/Week", stats["avgMilesPerWeek"]),
        stat_card_html("Peak Week", stats["peakWeekMiles"]),
        stat_card_html("Races", stats["totalRaces"]),
        stat_card_html("Longest Streak", f"{stats['longestStreak']}d"),
        stat_card_html("Active Days", f"{stats['activeDayPercentage']}%"),
    ]
    return f"""
    <section id="view-overview" class="view active">
      <div class="page-header">
        <div class="eyebrow">DASHBOARD</div>
        <h1>Overview</h1>
      </div>
      <div class="stat-grid">{"".join(cards)}</div>
      {notes_search_html(rows)}
      {heatmap_html(rows)}
      <div class="card">
        <div class="card-title">Cumulative Mileage</div>
        {fig_html(chart_cumulative(rows), height=280, div_id="chart-cumulative")}
      </div>
    </section>"""


def section_volume(rows):
    sparks = chart_seasonal_sparklines(rows)
    spark_cards = ""
    for season in ["fall", "winter", "spring", "summer"]:
        avg, html_div = sparks[season]
        spark_cards += f"""
        <div class="spark-card">
          <div class="spark-label">{season.capitalize()}</div>
          <div class="spark-stat">
            <span class="spark-num">{avg}</span>
            <span class="spark-sub">avg mi/wk</span>
          </div>
          <div class="spark-chart">{html_div}</div>
        </div>"""
    return f"""
    <section id="view-volume" class="view">
      <div class="page-header">
        <div class="eyebrow">TRAINING</div>
        <h1>Volume</h1>
      </div>
      <div class="card">
        <div class="card-title">Weekly Mileage</div>
        {fig_html(chart_weekly(rows), height=320, div_id="chart-weekly")}
      </div>
      <div class="card">
        <div class="card-title">Average Weekly Mileage by Season</div>
        <div class="spark-grid">{spark_cards}</div>
      </div>
      <div class="card">
        <div class="card-title">Monthly Mileage by Year</div>
        {fig_html(chart_monthly_mileage_by_year(rows), height=340, div_id="chart-monthly-by-year")}
      </div>
    </section>"""


def section_workout_mix(rows, races_by_cat):
    counts = defaultdict(int)
    for r in rows:
        if r["is_race"] == "1":
            continue
        if maybe_float(r["miles"]):
            counts[map_type(r["workout_type"], False)] += 1
    # Use the same race tally as the Races tab so the two views agree
    counts["race"] = sum(len(races_by_cat[c]) for c in races_by_cat)

    type_cards = "".join(f"""
        <div class="type-stat-card" style="--ts-color: {TYPE_COLORS[k]}">
          <div class="type-swatch"></div>
          <div class="type-num">{counts.get(k, 0)}</div>
          <div class="type-label">{TYPE_LABELS[k]}{'s' if k == 'race' else ' runs'}</div>
        </div>""" for k in ("easy", "long", "tempo", "workout", "race"))

    return f"""
    <section id="view-mix" class="view">
      <div class="page-header">
        <div class="eyebrow">TRAINING</div>
        <h1>Workout Mix</h1>
      </div>
      <div class="card">
        <div class="card-title">Distribution by Type</div>
        {fig_html(chart_workout_donut(rows, races_by_cat), height=300, div_id="chart-donut")}
      </div>
      <div class="type-stat-grid">{type_cards}</div>
      {(lambda res: f'''<div class="card">
        <div class="card-title-row">
          <div class="card-title">Miles by Workout Type per Season</div>
          <div class="chart-toggle" data-toggle-target="chart-mix-by-season"
               data-miles='{json.dumps(res[1])}'
               data-pct='{json.dumps(res[2])}'>
            <button class="active" data-mode="miles">Miles</button>
            <button data-mode="pct">% of Total</button>
          </div>
        </div>
        {fig_html(res[0], height=440, div_id="chart-mix-by-season")}
      </div>''')(chart_workout_mix_by_season(rows))}
      <div class="card">
        <div class="card-title">Easy Run Pace Over Time</div>
        {fig_html(chart_easy_pace(rows), height=300, div_id="chart-easy-pace")}
      </div>
    </section>"""


def section_performance(rows, races_by_cat):
    pr_cards = compute_pr_cards(races_by_cat)
    pr_html  = "".join(pr_card_html(c) for c in pr_cards)

    prog_cards = ""
    for i, (label, buckets, cats, color) in enumerate(PR_PROGRESSION_SPECS):
        slug = label.lower().replace(" ", "-")
        prog_cards += f"""
        <div class="card">
          <div class="card-title">{label} — PR Progression</div>
          {fig_html(chart_pr_progression(races_by_cat, label, buckets, cats, color),
                    height=260, div_id=f"chart-pr-{slug}")}
        </div>"""

    return f"""
    <section id="view-performance" class="view">
      <div class="page-header">
        <div class="eyebrow">RACING</div>
        <h1>Performance</h1>
      </div>
      <div class="pr-grid">{pr_html}</div>
      <div class="card">
        <div class="card-title">Race Pace Over Time</div>
        <div class="chart-caption">★ all-time PR &nbsp;·&nbsp; ◆ relay split &nbsp;·&nbsp; dotted line = season-best trend</div>
        {fig_html(chart_pace_timeline(races_by_cat), height=360, div_id="chart-pace-timeline")}
      </div>
      {prog_cards}
    </section>"""


def section_races(races_by_cat):
    cat_labels  = {"crossCountry": "XC", "indoorTrack": "Indoor", "outdoorTrack": "Outdoor"}
    cat_colors  = {"crossCountry": LONG_COLOR, "indoorTrack": WORKOUT_COLOR, "outdoorTrack": TEMPO_COLOR}

    # Flatten all races into a single JSON blob (rendered client-side)
    all_races = []
    for cat, races in races_by_cat.items():
        for r in races:
            all_races.append({
                "date":      r["date"],
                "race":      r["race"],
                "distance":  r["distance"],
                "bucket":    r["bucket"] or "",
                "time":      r["time"],
                "time_seconds": r["time_seconds"],
                "season":    r["season"],
                "is_relay":  bool(r.get("is_relay")),
                "pr":        bool(r.get("pr")),
                "category":  cat,
                "type_label": cat_labels[cat],
                "type_color": cat_colors[cat],
            })
    races_json = json.dumps(all_races).replace("</", "<\\/")

    # Distinct buckets (ordered) for the distance filter
    bucket_order = ["800m", "Mile", "1500m", "3k", "3k steeple", "5k", "6k"]
    seen_buckets = {r["bucket"] for r in all_races if r["bucket"]}
    bucket_opts  = "".join(
        f'<option value="{b}">{b}</option>' for b in bucket_order if b in seen_buckets
    )

    xc_n = len(races_by_cat["crossCountry"])
    in_n = len(races_by_cat["indoorTrack"])
    ou_n = len(races_by_cat["outdoorTrack"])
    total_n = xc_n + in_n + ou_n

    return f"""
    <section id="view-races" class="view">
      <div class="page-header">
        <div class="eyebrow">RACING</div>
        <h1>Races</h1>
      </div>
      <div class="race-tabs" role="tablist">
        <button class="race-tab active" data-tab="all">All <span class="tab-count">{total_n}</span></button>
        <button class="race-tab"        data-tab="crossCountry">Cross Country <span class="tab-count">{xc_n}</span></button>
        <button class="race-tab"        data-tab="indoorTrack">Indoor Track <span class="tab-count">{in_n}</span></button>
        <button class="race-tab"        data-tab="outdoorTrack">Outdoor Track <span class="tab-count">{ou_n}</span></button>
      </div>
      <div class="race-controls">
        <div class="race-search">
          <input type="text" id="race-query" placeholder="Search by race or distance…" autocomplete="off"/>
          <button id="race-clear" hidden>×</button>
        </div>
        <label class="race-control-group">
          <span class="race-control-label">Sort</span>
          <select id="race-sort">
            <option value="date-desc">Date (newest)</option>
            <option value="date-asc">Date (oldest)</option>
            <option value="time-asc">Time (fastest)</option>
            <option value="distance">Distance</option>
            <option value="pr">PRs first</option>
          </select>
        </label>
        <label class="race-control-group">
          <span class="race-control-label">Distance</span>
          <select id="race-distance">
            <option value="">All</option>{bucket_opts}
          </select>
        </label>
        <label class="race-control-group race-pr-toggle">
          <input type="checkbox" id="race-pr-only"/>
          <span>PRs only</span>
        </label>
      </div>
      <div class="race-list" id="race-list"></div>
      <div class="race-summary" id="race-summary"></div>
      <script id="races-data" type="application/json">{races_json}</script>
    </section>"""


def section_patterns(rows, stats):
    return f"""
    <section id="view-patterns" class="view">
      <div class="page-header">
        <div class="eyebrow">TRAINING</div>
        <h1>Patterns</h1>
      </div>
      <div class="patterns-grid">
        <div class="card">
          <div class="card-title">Avg Miles by Day of Week</div>
          {fig_html(chart_dow(rows), height=260, div_id="chart-dow")}
        </div>
        <div class="card">
          <div class="card-title">Avg Weekly Miles by Month</div>
          {fig_html(chart_monthly_avg(rows), height=260, div_id="chart-month")}
        </div>
      </div>
      <div class="card streak-card">
        <div class="card-title">Streak Analysis</div>
        <div class="streak-grid">
          <div class="streak-item">
            <div class="streak-num">{stats['longestStreak']}</div>
            <div class="streak-label">Longest streak (days)</div>
          </div>
          <div class="streak-item">
            <div class="streak-num">{stats['activeDayPercentage']}%</div>
            <div class="streak-label">Active days</div>
          </div>
          <div class="streak-item">
            <div class="streak-num">{stats['totalMiles']:,}</div>
            <div class="streak-label">Total miles</div>
          </div>
        </div>
      </div>
    </section>"""
