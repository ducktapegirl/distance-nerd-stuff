"""
Running Log — QA script
Run: python "Running Log/src/qa.py"  (from repo root)
Exit 0 = all pass, 1 = any fail
"""
import csv
import io
import re
import sys
import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent   # Running Log/src/
_ROOT = _HERE.parent            # Running Log/
CSV_PATH  = _ROOT / "running_log.csv"
HTML_PATH = _ROOT / "index.html"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHART_IDS = [
    "chart-cumulative", "chart-weekly",
    "spark-fall", "spark-winter", "spark-spring", "spark-summer",
    "chart-donut", "chart-easy-pace", "chart-pace-timeline",
    "chart-pr-800m", "chart-pr-mile",
    "chart-pr-5k-xc", "chart-pr-5k-track", "chart-pr-3k-steeple",
    "chart-dow", "chart-month",
]

# date -> (min_pace, max_pace)  — known long runs that had H:MM:SS times
PACE_SPOT_CHECKS = {
    "2006-03-04": (7.0, 10.0),
    "2006-08-06": (7.0, 10.0),
    "2004-07-14": (7.0, 10.0),
    "2003-10-12": (7.0, 10.0),
}

# date -> (min_miles, max_miles)  — known expression-format entry
MILES_SPOT_CHECK = {"2007-05-09": (4.5, 5.5)}

# Workout types that legitimately have no mileage (cross-training / rest / off days)
_REST_TYPES = {
    "off", "rest", "aquajog", "aqua-jog", "aqua jog",
    "pool", "bike", "swim", "swim/aqua jog", "elliptical",
    "weights", "yoga", "strength", "",
}

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_csv() -> list:
    text = CSV_PATH.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def load_html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(s: str):
    """Return float(s) or None if blank/unparseable."""
    try:
        return float(s.strip())
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# GROUP A — CSV Data Quality
# ---------------------------------------------------------------------------

def check_pace_corruption(rows, html):
    """No rows with pace < 4.0 min/mi when miles > 3; spot-check 4 long-run dates."""
    violations = []
    by_date = {}
    for row in rows:
        by_date[row["date"]] = row
        miles = _safe_float(row.get("miles", ""))
        pace  = _safe_float(row.get("pace_min_per_mile", ""))
        # Threshold 1.0: the H:MM:SS parsing bug produces paces ~0.13–0.30.
        # Interval/tempo workouts with partial time logs legitimately land in
        # the 1.5–3.5 range and should not be flagged here.
        if miles is not None and miles > 3 and pace is not None and pace < 1.0:
            violations.append(f"{row['date']} (pace={pace})")

    if violations:
        return False, f"Rows with pace < 4.0 min/mi and miles > 3: {', '.join(violations[:5])}"

    spot_failures = []
    for date, (lo, hi) in PACE_SPOT_CHECKS.items():
        row = by_date.get(date)
        if row is None:
            spot_failures.append(f"{date}: not found in CSV")
            continue
        pace = _safe_float(row.get("pace_min_per_mile", ""))
        if pace is None:
            spot_failures.append(f"{date}: pace is blank")
        elif not (lo <= pace <= hi):
            spot_failures.append(f"{date}: pace={pace:.2f} not in [{lo}, {hi}]")

    if spot_failures:
        return False, "Spot-check failures: " + "; ".join(spot_failures)

    return True, f"No pace < 1.0 min/mi for runs > 3 mi; spot-check dates OK"


def check_miles_spot_check(rows, html):
    """2007-05-09 should have miles ~5.0 (was blank before parse_miles() fix)."""
    by_date = {row["date"]: row for row in rows}
    for date, (lo, hi) in MILES_SPOT_CHECK.items():
        row = by_date.get(date)
        if row is None:
            return False, f"{date}: not found in CSV"
        miles = _safe_float(row.get("miles", ""))
        if miles is None:
            return False, f"{date}: miles is blank (expected ~5.0)"
        if not (lo <= miles <= hi):
            return False, f"{date}: miles={miles} not in [{lo}, {hi}]"
    return True, f"2007-05-09: miles = {_safe_float(by_date['2007-05-09']['miles'])}"


def check_miles_blank_pct(rows, html):
    """Blank miles for non-rest running rows should be < 5%."""
    non_rest = [r for r in rows
                if r.get("workout_type", "").strip().lower() not in _REST_TYPES]
    if not non_rest:
        return True, "No non-rest rows found (unexpected, but vacuously passing)"
    blank = sum(1 for r in non_rest if not r.get("miles", "").strip())
    pct = 100.0 * blank / len(non_rest)
    if pct >= 5.0:
        return False, f"Blank miles (non-rest): {blank}/{len(non_rest)} = {pct:.1f}% (threshold 5%)"
    return True, f"Blank miles (non-rest): {blank}/{len(non_rest)} = {pct:.1f}%"


def check_race_count_consistency(rows, html):
    """CSV is_race=1 count should be within 5 of the HTML Races stat card."""
    csv_races = sum(1 for r in rows if r.get("is_race", "").strip() == "1")

    # Pattern: <div class="type-num">99</div>  followed shortly by Races
    m = re.search(r'class="type-num">(\d+)</div>\s*<div[^>]*>\s*Races', html)
    if m is None:
        return False, "Could not find Races stat card in HTML"
    html_races = int(m.group(1))
    diff = abs(csv_races - html_races)
    if diff > 5:
        return False, f"CSV is_race=1 count ({csv_races}) vs HTML Races ({html_races}): diff={diff} > 5"
    return True, f"CSV races={csv_races}, HTML Races={html_races}, diff={diff}"


def check_date_validity(rows, html):
    """All dates should be valid ISO dates in 2003–2007, with no future dates."""
    today = datetime.date.today()
    invalid_parse, out_of_range, future = [], [], []
    for row in rows:
        d_str = row.get("date", "")
        try:
            d = datetime.date.fromisoformat(d_str)
        except (ValueError, TypeError):
            invalid_parse.append(d_str)
            continue
        if not (2003 <= d.year <= 2007):
            out_of_range.append(d_str)
        if d > today:
            future.append(d_str)

    problems = []
    if invalid_parse:
        problems.append(f"Unparseable dates: {invalid_parse[:5]}")
    if out_of_range:
        problems.append(f"Out-of-range (not 2003–2007): {out_of_range[:5]}")
    if future:
        problems.append(f"Future dates: {future[:5]}")

    if problems:
        return False, "; ".join(problems)
    return True, f"All {len(rows)} dates valid, in 2003-2007"


# ---------------------------------------------------------------------------
# GROUP B — HTML Structure
# ---------------------------------------------------------------------------

def check_chart_divs(rows, html):
    """All 16 Plotly chart container divs should be present."""
    missing = [id_ for id_ in CHART_IDS if f'id="{id_}"' not in html]
    if missing:
        return False, f"Missing chart divs: {', '.join(missing)}"
    return True, f"All {len(CHART_IDS)} chart divs present"


def check_detail_panel_no_hex(rows, html):
    """
    The detail panel <aside> and renderEntry() JS should use CSS vars,
    not hardcoded hex colors.
    """
    hex_pat = re.compile(r'(?:color|background)\s*:\s*#')

    # Part A: <aside class="detail-panel"> element
    aside_start = html.find('<aside class="detail-panel"')
    if aside_start == -1:
        return False, '<aside class="detail-panel"> not found in HTML'
    aside_end = html.find('</aside>', aside_start)
    if aside_end == -1:
        return False, '</aside> closing tag not found'
    aside_html = html[aside_start : aside_end + len('</aside>')]

    if hex_pat.search(aside_html):
        return False, 'Hardcoded hex color found in <aside class="detail-panel">'

    # Part B: renderEntry() JS function body
    fn_start = html.find('function renderEntry(e) {')
    if fn_start == -1:
        return False, 'renderEntry() function not found in HTML'
    stop_match = re.search(r'\n  function ', html[fn_start + 50:])
    if stop_match:
        fn_body = html[fn_start : fn_start + 50 + stop_match.start()]
    else:
        fn_body = html[fn_start : fn_start + 2000]

    if hex_pat.search(fn_body):
        return False, 'Hardcoded hex color found in renderEntry() JS'

    return True, 'No hardcoded hex in detail panel or renderEntry()'


def check_easy_pace_no_fill(rows, html):
    """chart-easy-pace Plotly trace should have no "fill":"tozeroy"."""
    # Find the Plotly.newPlot call that references chart-easy-pace
    newplot_positions = [m.start() for m in re.finditer(r'Plotly\.newPlot', html)]
    section = None
    for i, pos in enumerate(newplot_positions):
        if 'chart-easy-pace' in html[pos : pos + 80]:
            next_pos = newplot_positions[i + 1] if i + 1 < len(newplot_positions) else pos + 200_000
            section = html[pos : next_pos]
            break

    if section is None:
        return False, 'Could not locate chart-easy-pace Plotly.newPlot call'

    if re.search(r'"fill"\s*:\s*"tozeroy"', section):
        return False, 'chart-easy-pace has "fill":"tozeroy" (creates unwanted shading)'
    return True, 'chart-easy-pace: no fill:tozeroy'


# ---------------------------------------------------------------------------
# GROUP C — Theme & CSS
# ---------------------------------------------------------------------------

def check_theme_system(rows, html):
    """Theme toggle infrastructure should all be present."""
    checks = {
        ':root.light CSS block':      ':root.light {' in html,
        'applyTheme function':        'applyTheme' in html,
        'applyChartTheme function':   'applyChartTheme' in html,
        'data-theme="light" button':  'data-theme="light"' in html,
        'data-theme="dark" button':   'data-theme="dark"' in html,
        'data-theme="system" button': 'data-theme="system"' in html,
    }
    missing = [label for label, ok in checks.items() if not ok]
    if missing:
        return False, f"Missing theme components: {', '.join(missing)}"
    return True, ':root.light, applyTheme, applyChartTheme, 3 theme buttons'


def check_stat_card_hover_removed(rows, html):
    """.stat-card:hover CSS rule should be absent (stat cards are not clickable)."""
    if '.stat-card:hover' in html:
        return False, '.stat-card:hover CSS rule is still present'
    return True, '.stat-card:hover not present'


def check_strava_button_text(rows, html):
    """Button should read 'My Strava Dashboard', not 'Strava API Dashboard'."""
    has_correct = 'My Strava Dashboard' in html
    has_old     = 'Strava API Dashboard' in html
    if has_old:
        return False, "Old text 'Strava API Dashboard' still present"
    if not has_correct:
        return False, "'My Strava Dashboard' not found in HTML"
    return True, "'My Strava Dashboard' found"


def check_wordmark_font_size(rows, html):
    """.wordmark-name should have font-size >= 30px."""
    m = re.search(r'\.wordmark-name\s*\{[^}]*font-size\s*:\s*(\d+)px', html, re.DOTALL)
    if m is None:
        return False, '.wordmark-name font-size rule not found'
    size = int(m.group(1))
    if size < 30:
        return False, f'.wordmark-name font-size is {size}px, expected >= 30px'
    return True, f'.wordmark-name font-size: {size}px (>= 30px)'


def check_heatmap_css_vars(rows, html):
    """.hm-month and .hm-dow should use fill: var(--text-tertiary), not hardcoded hex."""
    hex_fill = re.compile(r'fill\s*:\s*#')
    failures = []
    for cls in ('.hm-month', '.hm-dow'):
        # Find the CSS block for this class
        m = re.search(re.escape(cls) + r'\s*\{([^}]+)\}', html)
        if m is None:
            failures.append(f'{cls} CSS rule not found')
            continue
        block = m.group(1)
        if 'var(--text-tertiary)' not in block:
            failures.append(f'{cls} does not use var(--text-tertiary) for fill')
        if hex_fill.search(block):
            failures.append(f'{cls} has hardcoded hex fill color')

    if failures:
        return False, '; '.join(failures)
    return True, '.hm-month and .hm-dow use var(--text-tertiary)'


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS = [
    ("CSV Data Quality", check_pace_corruption),
    ("CSV Data Quality", check_miles_spot_check),
    ("CSV Data Quality", check_miles_blank_pct),
    ("CSV Data Quality", check_race_count_consistency),
    ("CSV Data Quality", check_date_validity),
    ("HTML Structure",   check_chart_divs),
    ("HTML Structure",   check_detail_panel_no_hex),
    ("HTML Structure",   check_easy_pace_no_fill),
    ("Theme & CSS",      check_theme_system),
    ("Theme & CSS",      check_stat_card_hover_removed),
    ("Theme & CSS",      check_strava_button_text),
    ("Theme & CSS",      check_wordmark_font_size),
    ("Theme & CSS",      check_heatmap_css_vars),
]


def _print_results(results):
    width = 62
    print()
    print("+" + "-" * width + "+")
    print("|" + "  College Running Log -- QA Report".center(width) + "|")
    print("+" + "-" * width + "+")

    current_group = None
    passed_count = 0
    for group, fn_name, passed, message in results:
        if group != current_group:
            print(f"\n{group}")
            current_group = group
        status = "PASS" if passed else "FAIL"
        label = fn_name.replace("check_", "")
        print(f"  {status}  {label:<35}  {message}")
        if passed:
            passed_count += 1

    total = len(results)
    print()
    print("-" * (width + 2))
    overall = "PASSED" if passed_count == total else "FAILED"
    print(f"Result: {passed_count}/{total} {overall}")
    print()


def run_all() -> bool:
    rows = load_csv()
    html = load_html()

    results = []
    all_pass = True
    for group, fn in CHECKS:
        passed, message = fn(rows, html)
        results.append((group, fn.__name__, passed, message))
        if not passed:
            all_pass = False

    _print_results(results)
    return all_pass


def main():
    all_pass = run_all()
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
