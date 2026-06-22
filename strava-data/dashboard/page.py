"""Orchestrates a full dashboard build: build_page() composes data, charts, and
HTML shell into the final `Running Log/strava.html` string."""

import json

from .charts_exploratory import (
    chart_x_archetypes, chart_x_cadence, chart_x_cardiac, chart_x_heat,
    chart_x_load, chart_x_metronome, chart_x_mirage, chart_x_seasonal,
)
from .charts_production import (
    _seg_effort_points, chart_calendar, chart_elevation, chart_heartrate,
    chart_map, chart_pace, chart_run_hr_vs_temp, chart_run_pace_vs_hr,
    chart_run_seg_hr_vs_grade, chart_run_seg_pace_vs_grade,
    chart_run_seg_pace_vs_tortuosity, chart_mtb_seg_hr_vs_grade,
    chart_mtb_seg_pace_vs_grade, chart_mtb_seg_pace_vs_tortuosity,
    chart_segment_prs, chart_volume,
)
from .config import KM_TO_MI, MTB_EMOJI, M_TO_FT, PLOTLY_CDN, RUN_EMOJI
from .data import (
    activity_dict, fmt_pace, fmt_time, load_segment_efforts, mf,
    sport_category,
)
from .geometry_stats import compute_tortuosity_map
from .rollups_cards import (
    _cons_card_html, chart_seg_grade_vs_time, compute_seg_rollups,
    compute_stats, fast_seg_card, seg_consistency_picks, seg_fastest_picks,
    seg_overlap_pairs, stat_card,
)
from .template import CSS, THEME_TOGGLE_SVGS, build_js
from .theme import fig_html


def _activity_detail_json(rows):
    """Display info for the click-through detail panel, keyed by activity ID."""
    act_by_id = {}
    for r in rows:
        km    = mf(r["distance_km"]) or 0
        hr    = mf(r["average_heartrate"])
        elev  = (mf(r["total_elevation_gain_m"]) or 0) * M_TO_FT
        etime = mf(r["elapsed_time_min"]) or 0
        speed = mf(r["average_speed_kmh"])
        cat   = sport_category(r["sport_type"])
        pace_str = ""
        if speed and speed > 0:
            pace_str = (fmt_pace(60.0 / (speed * KM_TO_MI)) + " /mi") if cat == "Running" else f"{speed * KM_TO_MI:.1f} mph"
        act_by_id[str(r["id"])] = {
            "name":    r["name"],
            "date":    r["start_date_local"][:10],
            "sport":   r["sport_type"],
            "dist_mi": round(km * KM_TO_MI, 2),
            "hr":      round(hr) if hr else None,
            "elev_ft": round(elev),
            "elapsed": fmt_time(etime),
            "pace":    pace_str,
            "desc":    (r.get("description") or "").strip(),
        }
    return json.dumps(act_by_id, ensure_ascii=False)


def _build_main_charts(rows, segs):
    print("  calendar...")
    cal, cal_max_mi = chart_calendar(rows)
    print("    calendar data-driven max_mi=%.2f mi" % cal_max_mi)
    print("  volume...")
    vol    = chart_volume(rows)
    print("  heart rate...")
    hr_c   = chart_heartrate(rows)
    print("  pace...")
    pac    = chart_pace(rows)
    print("  elevation...")
    elev_c = chart_elevation(rows)
    print("  segments...")
    segs_c = chart_segment_prs(segs)
    print("  map...")
    mp     = chart_map(rows)
    return cal, vol, hr_c, pac, elev_c, segs_c, mp


def _build_trend_and_segment_scatter_charts(rows):
    print("  loading segment efforts...")
    seg_efforts = load_segment_efforts()
    act_by_id   = activity_dict(rows)

    print("  run pace vs HR...")
    run_pace_hr   = chart_run_pace_vs_hr(rows)
    print("  run HR vs temp...")
    run_hr_temp, run_hr_temp_meta = chart_run_hr_vs_temp(rows)

    print("  computing tortuosity...")
    tort_map = compute_tortuosity_map(seg_efforts, act_by_id)

    print("  building run segment data...")
    run_seg_data = _seg_effort_points(
        seg_efforts, act_by_id, tort_map,
        sport_filter=("Run", "TrailRun"),
    )
    print("  building MTB segment data...")
    mtb_seg_data = _seg_effort_points(
        seg_efforts, act_by_id, tort_map,
        sport_filter=("MountainBikeRide",),
        exclude_sports=("EBikeRide",),
    )

    print("  run seg pace vs tortuosity...")
    run_pace_tort = chart_run_seg_pace_vs_tortuosity(run_seg_data)
    print("  run seg pace vs grade...")
    run_pace_grade = chart_run_seg_pace_vs_grade(run_seg_data)
    print("  run seg HR vs grade...")
    run_hr_grade  = chart_run_seg_hr_vs_grade(run_seg_data)
    print("  MTB seg pace vs tortuosity...")
    mtb_pace_tort = chart_mtb_seg_pace_vs_tortuosity(mtb_seg_data)
    print("  MTB seg pace vs grade...")
    mtb_pace_grade = chart_mtb_seg_pace_vs_grade(mtb_seg_data)
    print("  MTB seg HR vs grade...")
    mtb_hr_grade  = chart_mtb_seg_hr_vs_grade(mtb_seg_data)

    scatter_charts = (
        run_pace_hr, run_hr_temp, run_pace_tort, run_pace_grade, run_hr_grade,
        mtb_pace_tort, mtb_pace_grade, mtb_hr_grade,
    )
    return seg_efforts, act_by_id, scatter_charts, run_hr_temp_meta


def _build_segment_rollup_section(seg_efforts, act_by_id):
    """Consistency, fastest, and grade-vs-pace overlap views for the Segments tab."""
    print("  building segment rollups...")
    seg_roll = compute_seg_rollups(seg_efforts, act_by_id)

    print("  segment pace consistency...")
    cons_run_most, cons_run_least = seg_consistency_picks(seg_roll, "Running")
    cons_mtb_most, cons_mtb_least = seg_consistency_picks(seg_roll, "MTB")
    for tag, pk in (("run most", cons_run_most), ("run least", cons_run_least),
                    ("mtb most", cons_mtb_most), ("mtb least", cons_mtb_least)):
        if pk:
            cvv, _sid, s = pk
            print("    %-9s CV=%.4f n=%2d '%s'" % (tag, cvv, len(s["metric"]), s["name"]))

    print("  fastest segments by avg pace...")
    fast_run = seg_fastest_picks(seg_roll, "Running")
    fast_mtb = seg_fastest_picks(seg_roll, "MTB")
    for tag, rows_ in (("run", fast_run), ("mtb", fast_mtb)):
        for avg, _sid, s in rows_:
            print("    %-3s avg=%.2f grade=%s '%s'" % (tag, avg, s["grade"], s["name"]))

    print("  segment grade-vs-pace overlap (run vs MTB)...")
    ov_pairs = seg_overlap_pairs(seg_roll)
    grade_time_fig, gt_info, gt_ok = chart_seg_grade_vs_time(ov_pairs)
    print("    overlap pairs=%d run_segs=%d mtb_segs=%d build=%s crossover=%s"
          % (len(ov_pairs), gt_info["n_run"], gt_info["n_mtb"], gt_ok,
             ("%.2f%%" % gt_info["cross"]) if gt_info.get("cross") is not None else "n/a"))

    cons_cards_html = (
        '<div class="section-anchor" style="margin-top:32px">Segment Pace Consistency</div>'
        '<div class="seg-cons-grid">'
        + _cons_card_html(cons_run_most,  "Running", "Most",  "chart-seg-cons-run-most")
        + _cons_card_html(cons_run_least, "Running", "Least", "chart-seg-cons-run-least")
        + _cons_card_html(cons_mtb_most,  "MTB",     "Most",  "chart-seg-cons-mtb-most")
        + _cons_card_html(cons_mtb_least, "MTB",     "Least", "chart-seg-cons-mtb-least")
        + '</div>')

    fast_cards_html = (
        f'<div class="section-anchor" style="margin-top:32px">{RUN_EMOJI} Running &middot; '
        'Fastest 3 Segments</div><div class="fast-grid">'
        + "".join(fast_seg_card(i + 1, "Running", avg, s)
                  for i, (avg, _sid, s) in enumerate(fast_run))
        + '</div>'
        f'<div class="section-anchor" style="margin-top:24px">{MTB_EMOJI} MTB &middot; '
        'Fastest 3 Segments</div><div class="fast-grid">'
        + "".join(fast_seg_card(i + 1, "MTB", avg, s)
                  for i, (avg, _sid, s) in enumerate(fast_mtb))
        + '</div>')

    if gt_ok:
        cross = gt_info["cross"]
        cap = (
            "Strava segments are sport-specific, so to compare running against "
            "mountain biking on the same dirt I matched run and MTB segments whose "
            "start points fall within 60&nbsp;m of each other, whose lengths are "
            "within ~10%, and whose average grades are within 3&nbsp;points of "
            "each other (to rule out matches run in opposite directions) &mdash; "
            "the same trails, run and ridden. Each dot is one such "
            "segment, placed by its grade (x) and its average pace per mile "
            "(y, faster&nbsp;=&nbsp;up); using pace per mile normalizes the different "
            "segment lengths so the run-vs-bike comparison is fair. The dashed lines "
            "are linear fits per sport.")
        if cross is not None:
            cap += (
                f" They cross near <strong>{cross:.1f}% grade</strong>: on flatter or "
                "downhill terrain (left) the bike is faster, but on climbs steeper than "
                f"that, running overtakes mountain biking (shaded) &mdash; grinding a bike "
                "uphill costs more than it saves.")
        grade_time_html = (
            '<div class="section-anchor" style="margin-top:32px">Running vs MTB &middot; '
            'Speed by Grade</div>'
            '<div class="card">'
            '<div class="card-title">Where Running Overtakes Mountain Biking</div>'
            + fig_html(grade_time_fig, 460, "chart-seg-grade-time")
            + f'<p class="plot-caption">{cap}</p>'
            '</div>')
    else:
        grade_time_html = ""

    return cons_cards_html, fast_cards_html, grade_time_html


def _build_exploratory_charts(rows):
    print("  exploratory V1 temperature mirage...")
    v1, v1m = chart_x_mirage(rows)
    print("    V1 n=%d bins=%d raw_r=%.3f raw_p=%.3f air_adj_r=%.3f air_adj_p=%.3f "
          "app_adj_r=%.3f app_adj_p=%.3f n_app=%d"
          % (v1m["n"], v1m["bins"], v1m["raw_r"], v1m["raw_p"],
             v1m["air_adj_r"], v1m["air_adj_p"], v1m["app_adj_r"], v1m["app_adj_p"],
             v1m["n_app"]))
    print("  exploratory V2 archetypes...")
    v2, v2m = chart_x_archetypes(rows)
    print("    V2 n=%d EVR PC1=%.1f%% PC2=%.1f%% scale=%.3f inertia=%.2f sizes=%s"
          % (v2m["n"], v2m["evr1"], v2m["evr2"], v2m["scale"], v2m["inertia"],
             {k: v2m["sizes"][k] for k in sorted(v2m["sizes"])}))
    print("  exploratory V3 cardiac...")
    v3, v3m = chart_x_cardiac(rows)
    print("    V3 welch t=%.3f df=%.2f p=%.3e n_run=%d n_mtb=%d"
          % (v3m["t"], v3m["df"], v3m["p"], v3m["n_run"], v3m["n_mtb"]))
    print("  exploratory V4 heat...")
    v4, v4m = chart_x_heat(rows)
    for _vk in ("air", "app"):
        _v = v4m[_vk]
        print("    V4 %s welch t=%.3f p=%.5f hrflat(t=%.3f,p=%.4f) HR=%s n=%d/%d/%d/%d total=%d"
              % (_vk, _v["t"], _v["p"], _v["hrt"], _v["hrp"],
                 ["%.2f" % h for h in _v["hr_means"]],
                 _v["n"][0], _v["n"][1], _v["n"][2], _v["n"][3], _v["n_total"]))
    print("  exploratory V5 seasonal handoff...")
    v5, v5m = chart_x_seasonal(rows)
    print("    V5 total_run_mi=%.1f total_mtb=%d sep_mi=%.1f jul_mtb=%d"
          % (v5m["total_run"], v5m["total_mtb"], v5m["sep_mi"], v5m["jul_mtb"]))
    print("  exploratory V6 cadence...")
    v6, v6m = chart_x_cadence(rows)
    print("    V6 slope=%.4f intercept=%.4f r=%.4f n=%d"
          % (v6m["slope"], v6m["intercept"], v6m["r"], v6m["n"]))
    print("  exploratory V7 metronome...")
    v7, v7m = chart_x_metronome(rows)
    print("    V7 run p10=%.3f p50=%.3f p90=%.3f tail_n=%d mtb_p50=%.3f"
          % (v7m["p10"], v7m["p50"], v7m["p90"], v7m["tail_n"], v7m["mtb_p50"]))
    print("  exploratory V8 load...")
    v8, v8m = chart_x_load(rows)
    print("    V8 peak=%.0f on %s spike_days=%d median_acwr=%.3f days=%d total_suffer=%.0f"
          % (v8m["peak"], v8m["peak_date"], v8m["spike_days"], v8m["median_acwr"],
             v8m["days"], v8m["total_suffer"]))
    return (v1, v2, v3, v4, v5, v6, v7, v8,
            v4m["air_text"], v4m["app_text"],
            v1m["mirage_air_text"], v1m["mirage_app_text"])


def _build_stats_panel(rows, stats):
    dates = sorted(r["start_date_local"][:10] for r in rows)
    date_range = f"{dates[0]} – {dates[-1]}" if dates else "—"

    stats_html = (
        '<div class="stat-grid">'
        + stat_card(stats["total_acts"], "Total Activities")
        + stat_card(f"{stats['run_dist']:,.0f} mi", "Running")
        + stat_card(f"{stats['mtb_dist']:,.0f} mi", "Mountain Bike")
        + stat_card(f"{stats['total_elev']:,.0f} ft", "Total Elevation")
        + stat_card(f"{stats['longest_run']:.1f} mi", "Longest Run")
        + stat_card(f"{stats['longest_mtb']:.1f} mi", "Longest MTB")
        + "</div>"
    )

    nav_links = "".join(
        f'<button class="tab" data-view="{v}">{l}</button>'
        for v, l in [
            ("overview",  "Overview"),
            ("volume",    "Volume"),
            ("trends",    "Trends"),
            ("segments",  "Segments"),
            ("map",       "Map"),
            ("exploratory", "Exploratory"),
        ]
    )

    theme_buttons = "".join(
        f'<button type="button" data-theme="{mode}" title="{title}" aria-label="{aria}">{svg}</button>'
        for mode, title, aria, svg in [
            ("light",  "Light",  "Light theme",       THEME_TOGGLE_SVGS["light"]),
            ("dark",   "Dark",   "Dark theme",        THEME_TOGGLE_SVGS["dark"]),
            ("system", "System", "Use system theme",  THEME_TOGGLE_SVGS["system"]),
        ]
    )

    return date_range, stats_html, nav_links, theme_buttons


def _assemble_html(*, date_range, stats_html, nav_links, theme_buttons, js,
                    cal, vol, hr_c, pac, elev_c, segs_c, mp,
                    run_pace_hr, run_hr_temp, run_pace_tort, run_pace_grade,
                    run_hr_grade, mtb_pace_tort, mtb_pace_grade, mtb_hr_grade,
                    cons_cards_html, fast_cards_html, grade_time_html,
                    v1, v2, v3, v4, v5, v6, v7, v8):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Strava Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;700&family=Geist+Mono:wght@400;600&display=swap" rel="stylesheet">
  {PLOTLY_CDN}
  <style>{CSS}</style>
  <script data-goatcounter="https://ducktapegirl.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</head>
<body>

<div class="shell">

<header class="topnav">
  <div class="topnav-row row1">
    <div class="wordmark">
      <span class="wordmark-name">Strava Dashboard</span>
      <span class="wordmark-meta">{date_range}</span>
    </div>
    <div class="topnav-actions">
      <a class="back-link" href="index.html" title="College Running Log">
        <span>←</span><span>College Running Log</span>
      </a>
      <div class="theme-toggle" role="group" aria-label="Theme">{theme_buttons}</div>
    </div>
  </div>
  <div class="topnav-row row2">
    <nav class="tabnav">{nav_links}</nav>
  </div>
</header>

<main>

<section id="view-overview" class="view active">
  <div class="page-header">
    <h1>Overview</h1>
    <div class="date-range">{date_range}</div>
  </div>
  {stats_html}
  <div class="card">
    <div class="card-title">Activity Calendar</div>
    {cal}
  </div>
</section>

<section id="view-volume" class="view">
  <div class="section-anchor">Volume</div>
  <div class="card">
    <div class="card-title">Weekly Volume</div>
    {fig_html(vol, 440, div_id="chart-volume")}
  </div>
  <div class="card">
    <div class="card-title">Weekly Elevation Gain</div>
    {fig_html(elev_c, 360, div_id="chart-elev")}
  </div>
</section>

<section id="view-trends" class="view">
  <div class="section-anchor">Trends</div>
  <div class="card">
    <div class="card-title">Heart Rate</div>
    {fig_html(hr_c, 420, div_id="chart-hr")}
  </div>
  <div class="card">
    <div class="card-title">Pace / Speed</div>
    {fig_html(pac, 440, div_id="chart-pace")}
  </div>

  <div class="section-anchor" style="margin-top:32px">Running · Activity Trends</div>
  <div class="card">
    <div class="card-title">Pace vs Heart Rate</div>
    {fig_html(run_pace_hr, 420, div_id="chart-run-pace-hr")}
  </div>
  <div class="card">
    <div class="card-title">Heart Rate vs Temperature</div>
    <div class="seg-filter">
      <button class="seg-btn active" onclick="toggleHrTemp('air',this)">Air temp</button>
      <button class="seg-btn" onclick="toggleHrTemp('app',this)">Apparent temp</button>
    </div>
    {fig_html(run_hr_temp, 420, div_id="chart-run-hr-temp")}
    <p class="plot-caption">Each dot is a run, placed by the day's temperature (x) and average heart rate (y); the dashed line is a per-sport linear fit with its R&sup2;. The toggle switches the x-axis between air temperature and apparent temperature (heat index, which folds in humidity) so the two can be compared 1:1 on a shared axis. Apparent temp has lower backfill coverage, so its view uses fewer runs &mdash; the exact shortfall is noted at the bottom of that view.</p>
  </div>

  <div class="section-anchor" style="margin-top:32px">Running · Segment Scatter</div>
  <div class="card">
    <div class="card-title">Pace vs Tortuosity</div>
    {fig_html(run_pace_tort, 420, div_id="chart-run-seg-pace-tort")}
  </div>
  <div class="card">
    <div class="card-title">Pace vs Grade</div>
    {fig_html(run_pace_grade, 420, div_id="chart-run-seg-pace-grade")}
  </div>
  <div class="card">
    <div class="card-title">Heart Rate vs Grade</div>
    {fig_html(run_hr_grade, 420, div_id="chart-run-seg-hr-grade")}
  </div>

  <div class="section-anchor" style="margin-top:32px">MTB · Segment Scatter</div>
  <div class="card">
    <div class="card-title">Speed vs Tortuosity</div>
    {fig_html(mtb_pace_tort, 420, div_id="chart-mtb-seg-pace-tort")}
  </div>
  <div class="card">
    <div class="card-title">Speed vs Grade</div>
    {fig_html(mtb_pace_grade, 420, div_id="chart-mtb-seg-pace-grade")}
  </div>
  <div class="card">
    <div class="card-title">Heart Rate vs Grade</div>
    {fig_html(mtb_hr_grade, 420, div_id="chart-mtb-seg-hr-grade")}
  </div>
</section>

<section id="view-segments" class="view">
  <div class="section-anchor">Segments</div>
  <div class="card">
    <div class="card-title">Top 20 Segments by Effort Count</div>
    <div class="seg-filter">
      <button class="seg-btn active" onclick="filterSegs('all',this)">All</button>
      <button class="seg-btn" onclick="filterSegs('run',this)">🏃‍♀️ Running</button>
      <button class="seg-btn" onclick="filterSegs('mtb',this)">🚵‍♀️ MTB</button>
    </div>
    {fig_html(segs_c, 540, div_id="chart-segs")}
  </div>
  {cons_cards_html}
  {fast_cards_html}
  {grade_time_html}
</section>

<section id="view-map" class="view">
  <div class="section-anchor">Map</div>
  <div class="card">
    <div class="card-title">Activity Locations</div>
    {fig_html(mp, 520, div_id="chart-map")}
  </div>
</section>

<section id="view-exploratory" class="view">
  <div class="section-anchor">Exploratory</div>
  <div class="card">
    <div class="card-title">About This Section</div>
    <p class="attribution">This section was created entirely by Claude — Anthropic's <strong>Claude Fable 5</strong> model (<code>claude-fable-5</code>) acting as orchestrator, dispatching the strava-data-analyst, strava-creativity, strava-viz-design, strava-developer, and strava-qa subagents.</p>
  </div>
  <div class="card">
    <div class="card-title">The Temperature Mirage</div>
    <div class="seg-filter">
      <button class="seg-btn active" onclick="toggleMirage('air',this)">Air temp</button>
      <button class="seg-btn" onclick="toggleMirage('app',this)">Apparent temp</button>
    </div>
    {fig_html(v1,460,"chart-x-mirage")}
    <p class="plot-caption">When the weather cools down, runners often feel like they're getting fitter — but is that real? This chart tracks aerobic efficiency (pace per heartbeat) over time: the dashed line is the raw trend, the solid line adjusts for temperature using a statistical technique called OLS regression. The annotation in the top-right corner shows two correlation values (r) and their p-values — one before and one after the temperature correction. If the adjusted r is smaller or less significant, some of your apparent fitness gains were weather-driven, not true fitness gains. The toggle re-runs the temperature correction against apparent temperature (heat index) instead of air temperature; the raw trend stays put since it doesn't use temperature at all.</p>
  </div>
  <div class="card">
    <div class="card-title">Athlete Archetypes</div>
    {fig_html(v2,520,"chart-x-archetypes")}
    <p class="plot-caption">A technique called PCA compresses 8 workout metrics — distance, elevation, pace, heart rate, calories, and more — into two summary axes, then k-means clustering groups activities into 3 natural archetypes. Think of it as a map where nearby dots are workouts with similar effort profiles. The arrows show which original metrics pull in each direction; longer arrows mean that metric has more influence on the layout. The convex hull outlines and legend show how many activities fall into each cluster.</p>
  </div>
  <div class="card">
    <div class="card-title">Two Cardiac Worlds</div>
    {fig_html(v3,420,"chart-x-cardiac")}
    <p class="plot-caption">These overlapping histograms compare average heart rate across all runs (teal) vs. mountain bike rides (amber). The vertical dashed lines mark the mean heart rate for each sport. The annotation box shows the gap (Δ bpm) between those means plus a Welch t-test result — a statistical check that confirms whether the difference is real or could be random chance (p &lt; 0.05 means it's real). The triangle markers at the top track max heart rate: despite the sustained intensity gap, your cardiovascular ceiling is nearly identical across both sports.</p>
  </div>
  <div class="card">
    <div class="card-title">She Pays Pace, Not Heart, for Heat</div>
    <div class="seg-filter">
      <button class="seg-btn active" onclick="toggleHeat('air',this)">Air temp</button>
      <button class="seg-btn" onclick="toggleHeat('app',this)">Apparent temp</button>
    </div>
    {fig_html(v4,460,"chart-x-heat")}
    <p class="plot-caption">Each violin shape shows the spread of run paces across four fixed temperature bands — cool, mild, warm, and hot. Wider = more spread in that band; the box inside marks the middle 50% of runs. The teal line (right axis) tracks average heart rate across those same bands. The toggle above switches the whole chart between air temperature and apparent temperature (heat index, which folds in humidity) so the two can be compared 1:1. The bottom annotation gives the exact average pace for the coolest and warmest conditions, plus two p-values: one confirming pace does change significantly with temperature, and one showing heart rate does not — meaning in the heat you move slower without working cardiovascularly harder.</p>
  </div>
  <div class="card">
    <div class="card-title">The Seasonal Handoff</div>
    {fig_html(v5,440,"chart-x-seasonal")}
    <p class="plot-caption">The teal filled area shows total running distance per month; the amber bars show MTB ride counts; the faint dot-dash line is average temperature. Where one sport rises, the other falls. The shaded "MTB blackout" annotation marks a stretch where ride counts dropped to near zero — the label inside it shows how few MTB rides occurred that month, likely due to trail conditions rather than preference.</p>
  </div>
  <div class="card">
    <div class="card-title">Cadence Is the Gearbox</div>
    {fig_html(v6,460,"chart-x-cadence")}
    <p class="plot-caption">Each dot is a run, colored by heart rate intensity (darker teal = higher HR). The dashed trendline shows the OLS-fitted relationship between cadence and pace. The annotation box in the top-left reports two correlations: cadence→pace (r and p-value) and cadence→heart rate (r and p-value). A strong cadence–pace r with a weak cadence–HR r means cadence functions like a mechanical gear ratio — spinning faster makes you go faster without necessarily driving your heart harder. The vertical dotted line marks the median cadence.</p>
  </div>
  <div class="card">
    <div class="card-title">The Metronome and Its Tail</div>
    {fig_html(v7,420,"chart-x-metronome")}
    <p class="plot-caption">Two side-by-side distributions: run pace in min/mi (left) and mountain bike speed in mph (right). The shaded band on the left covers the middle 80% of runs (p10 to p90 — the 10th and 90th percentiles); the vertical dashed lines on the right mark the same percentile boundaries for MTB. The annotation on the left's slow tail identifies what those outlier runs actually are — trail workouts with heavy elevation gain, or group social runs where pace takes a back seat.</p>
  </div>
  <div class="card">
    <div class="card-title">Load, Monotony &amp; the Spike Zone</div>
    {fig_html(v8,480,"chart-x-load")}
    <p class="plot-caption">The violet line (left axis) is your 7-day rolling suffer score — a Strava-derived measure of cumulative training stress. The gray line (right axis) is the ACWR ratio: your current week's training divided by your 4-week rolling average. A ratio near 1.0 means you're training consistently; the colored bands show risk zones — teal is the sweet spot, amber is elevated risk, and red is the spike zone (&gt;1.5) where injury risk rises sharply. The labeled arrow marks your highest single-week training peak; the counter at the top shows how many days you spent in the spike zone.</p>
  </div>
</section>

</main>

</div>

<!-- Detail panel -->
<div id="detail-backdrop" class="detail-backdrop"></div>
<aside id="detail-panel" class="detail-panel" role="complementary">
  <div class="detail-header">
    <span class="detail-title">Activity Details</span>
    <button class="detail-close" onclick="closeDetail()" aria-label="Close">×</button>
  </div>
  <div class="detail-body" id="detail-body">
    <div class="d-hint">Click any point on the Heart Rate, Pace, or Map charts to see activity details.</div>
  </div>
</aside>

<script>{js}</script>
</body>
</html>"""


def build_page(rows, segs):
    stats = compute_stats(rows)
    act_json = _activity_detail_json(rows)

    cal, vol, hr_c, pac, elev_c, segs_c, mp = _build_main_charts(rows, segs)

    (seg_efforts, act_by_id, scatter_charts,
     run_hr_temp_meta) = _build_trend_and_segment_scatter_charts(rows)
    (run_pace_hr, run_hr_temp, run_pace_tort, run_pace_grade, run_hr_grade,
     mtb_pace_tort, mtb_pace_grade, mtb_hr_grade) = scatter_charts

    cons_cards_html, fast_cards_html, grade_time_html = _build_segment_rollup_section(
        seg_efforts, act_by_id)

    (v1, v2, v3, v4, v5, v6, v7, v8,
     heat_air_text, heat_app_text,
     mirage_air_text, mirage_app_text) = _build_exploratory_charts(rows)

    date_range, stats_html, nav_links, theme_buttons = _build_stats_panel(rows, stats)

    SYNC_IDS  = ["chart-volume", "chart-hr", "chart-pace", "chart-elev"]
    CLICK_IDS = ["chart-hr", "chart-pace", "chart-map"]
    js = build_js(act_json, SYNC_IDS, CLICK_IDS, heat_air_text, heat_app_text,
                  mirage_air_text, mirage_app_text, run_hr_temp_meta)

    return _assemble_html(
        date_range=date_range, stats_html=stats_html, nav_links=nav_links,
        theme_buttons=theme_buttons, js=js,
        cal=cal, vol=vol, hr_c=hr_c, pac=pac, elev_c=elev_c, segs_c=segs_c, mp=mp,
        run_pace_hr=run_pace_hr, run_hr_temp=run_hr_temp,
        run_pace_tort=run_pace_tort, run_pace_grade=run_pace_grade,
        run_hr_grade=run_hr_grade, mtb_pace_tort=mtb_pace_tort,
        mtb_pace_grade=mtb_pace_grade, mtb_hr_grade=mtb_hr_grade,
        cons_cards_html=cons_cards_html, fast_cards_html=fast_cards_html,
        grade_time_html=grade_time_html,
        v1=v1, v2=v2, v3=v3, v4=v4, v5=v5, v6=v6, v7=v7, v8=v8,
    )
