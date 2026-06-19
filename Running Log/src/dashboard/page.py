"""Top-level HTML assembler: stats/race-records/day-index prep, the six
page sections, and the final page template."""

import json

from dashboard.config import PLOTLY_CDN
from dashboard.components import build_day_index
from dashboard.sections import (
    section_overview, section_patterns, section_performance, section_races,
    section_volume, section_workout_mix,
)
from dashboard.stats import build_race_records, compute_stats
from dashboard.template import CSS, JS


def _compute_page_data(rows):
    stats = compute_stats(rows)
    races_by_cat = build_race_records(rows)
    day_index_json = json.dumps(build_day_index(rows)).replace("</", "<\\/")
    return stats, races_by_cat, day_index_json


def _build_sections(rows, stats, races_by_cat):
    return (
        section_overview(rows, stats)
        + section_volume(rows)
        + section_workout_mix(rows, races_by_cat)
        + section_performance(rows, races_by_cat)
        + section_races(races_by_cat)
        + section_patterns(rows, stats)
    )


def _assemble_html(rows, sections, day_index_json):
    dates_sorted = sorted(r["date"] for r in rows if r["date"])
    first_year = dates_sorted[0][:4] if dates_sorted else ""
    last_year  = dates_sorted[-1][:4] if dates_sorted else ""
    date_range = f"{first_year}–{last_year}"

    strava_chevron = (
        '<svg viewBox="0 0 24 24"><path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172'
        'h-3.066m-7.008-5.599l2.836 5.599h4.172L10.463 0l-7 13.828h4.169"/></svg>'
    )

    tabs = """
      <button class="tab" data-view="overview">Overview</button>
      <button class="tab" data-view="volume">Volume</button>
      <button class="tab" data-view="mix">Workout Mix</button>
      <button class="tab" data-view="performance">Performance</button>
      <button class="tab" data-view="races">Races</button>
      <button class="tab" data-view="patterns">Patterns</button>
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>College Running Log — Strava Before Strava</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  {PLOTLY_CDN}
  <style>{CSS}</style>
  <script data-goatcounter="https://ducktapegirl.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</head>
<body>
  <div class="shell">
    <nav class="topnav">
      <div class="topnav-row row1">
        <div class="wordmark">
          <span class="wordmark-name">College Running Log</span>
          <span class="wordmark-meta">{date_range}</span>
        </div>
        <div class="topnav-actions">
          <div class="theme-toggle" role="group" aria-label="Theme">
            <button type="button" data-theme="light" title="Light" aria-label="Light theme">
              <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
            </button>
            <button type="button" data-theme="dark" title="Dark" aria-label="Dark theme">
              <svg viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/></svg>
            </button>
            <button type="button" data-theme="system" title="System" aria-label="Use system theme">
              <svg viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 21h8M12 18v3"/></svg>
            </button>
          </div>
          <a class="strava-btn" href="strava.html">
            {strava_chevron}<span>My Strava Dashboard</span>
          </a>
        </div>
      </div>
      <div class="topnav-row row2">
        <div class="tabnav">{tabs}</div>
      </div>
    </nav>
    <main>
      {sections}
    </main>
    <footer class="dash-footer">
      This dashboard was created using Claude Code. <a href="running_log_story.html">See how I did it.</a>
    </footer>
  </div>
  <aside class="detail-panel" id="detail-panel" aria-hidden="true" role="complementary">
    <div class="detail-header">
      <div class="detail-date" id="detail-date"></div>
      <button class="detail-close" id="detail-close" aria-label="Close detail panel">×</button>
    </div>
    <div class="detail-body" id="detail-body"></div>
  </aside>
  <div class="detail-backdrop" id="detail-backdrop"></div>
  <script id="day-index" type="application/json">{day_index_json}</script>
  <script>{JS}</script>
</body>
</html>
"""


def build_html(rows):
    stats, races_by_cat, day_index_json = _compute_page_data(rows)
    sections = _build_sections(rows, stats, races_by_cat)
    return _assemble_html(rows, sections, day_index_json)
