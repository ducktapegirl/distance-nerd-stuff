"""
Strava Dashboard — static QA script
Run: uv run python strava-data/qa.py  (from repo root)
Exit 0 = all pass, 1 = any fail

Static regression guards only — no browser, no rendering. For dynamic/rendered
issues (camera animation, timing races), see
tools/qa-checks/places-hero-dynamic.py instead.
"""
import re
import sys
from pathlib import Path

from dashboard.config import OUT_HTML
from dashboard.data import load_activities
from dashboard.charts_places import _passport_data, _away_clusters

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HTML_PATH = Path(OUT_HTML)

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# GROUP A — Places hero: HTML/JS structure
# ---------------------------------------------------------------------------

def check_places_no_duplicate_route(rows, html):
    """
    drawGlow()'s canvas route pass must stay gated behind `if(!curActivity){`,
    or the 2D canvas overlay and the GL terrain route layer both draw the same
    track -- two overlapping lines in the activity's sport color plus the GL
    layer's accent color (fixed in d2b2fba). Regressing this means deleting
    or loosening that guard, which is a straight text match, not a rendering
    question -- no browser needed to catch it.
    """
    m = re.search(r'function drawGlow\(\)\s*\{', html)
    if m is None:
        return False, 'drawGlow() function not found in HTML'
    # Scan forward from drawGlow() to the guard, then confirm the guard
    # actually wraps the TRACKS-drawing loop (not just present somewhere later
    # in the file).
    fn_region = html[m.end(): m.end() + 4000]
    guard_m = re.search(r'if\s*\(\s*!\s*curActivity\s*\)\s*\{', fn_region)
    if guard_m is None:
        return False, 'drawGlow() no longer gates its route pass on !curActivity'
    tracks_m = re.search(r'for\s*\(\s*var\s+ti\s*=\s*0\s*;\s*ti\s*<\s*TRACKS\.length', fn_region)
    if tracks_m is None:
        return False, 'TRACKS drawing loop not found in drawGlow()'
    if tracks_m.start() < guard_m.start():
        return False, 'TRACKS loop is not inside the !curActivity guard'
    return True, 'drawGlow() route pass still gated on !curActivity'


def check_places_terrain_pitch_baked_into_fit(rows, html):
    """
    frameBounds() must set `pitch` inside the `opts` object it builds for its
    own immediate fitBounds() call, not defer to a separate easeTo() after the
    fit lands -- a standalone pitch easeTo calls stop() internally and kills
    an in-flight framing move (the "two clicks to zoom in" bug, fixed by
    folding pitch into the fit itself). Regressing this means reintroducing a
    second camera animation that races the first.

    Scoped specifically to the `var opts = {...}` object literal (not
    "somewhere in the function body") -- frameBounds() also re-sets `pitch`
    on a *held* framing move replayed later via onStyleSettled(), and a
    sabotage test showed that occurrence alone is enough to pass a looser
    "pitch: appears somewhere in this function" check even when the primary
    immediate-fit path has been broken.
    """
    m = re.search(r'function frameBounds\([^)]*\)\s*\{', html)
    if m is None:
        return False, 'frameBounds() function not found in HTML'
    fn_region = html[m.end(): m.end() + 1500]
    opts_m = re.search(r'var\s+opts\s*=\s*\{(.*?)\}\s*;', fn_region, re.DOTALL)
    if opts_m is None:
        return False, 'frameBounds() no longer builds a var opts = {...} literal'
    if not re.search(r'\bpitch\s*:', opts_m.group(1)):
        return False, 'frameBounds()\'s opts object no longer sets pitch'
    return True, 'frameBounds() bakes pitch into its opts object'


# ---------------------------------------------------------------------------
# GROUP B — Places hero: multi-day trip data integrity
# ---------------------------------------------------------------------------

# curated trip signature -> expected day count. Ground-truthed against the
# live CSV (strava-data/data/activities.csv) at the time this test was
# written: Maine Hut Trail is 3 separate day activities; Stanley Park is 2
# same-day activities (a run + a bike ride). If the roster of Strava
# activities changes (new trip days added, re-titled, etc.) these numbers
# may need updating -- that's expected drift, not a false positive.
_EXPECTED_TRIP_DAYS = {
    "Maine Hut": 3,
    "Stanley Park": 2,
}


def check_multiday_trip_day_counts(rows, html):
    """
    _passport_data()'s "days" field for a curated multi-day trip must cover
    exactly that trip's own activities, filtered by its curated name
    substring (spec["sig"]) -- not the whole _away_clusters() cluster, which
    merges any away activity within a 5-day gap into one cluster regardless
    of geography (97addbf: Maine Hut Trail showed only 1 of 3 days; the
    Stanley Park cluster separately pulls in an unrelated Bellevue/Seattle/
    Nanaimo leg that must NOT end up in Stanley Park's route).

    This is a pure data-assembly bug, not a rendering bug -- the JS
    (MultiLineString-vs-LineString branch) was always correct, so this is
    tested by calling the Python data function directly rather than via a
    browser.
    """
    featured, brief, pc, n_states, n_prov = _passport_data(rows)
    by_caption_sig = {}
    for f in featured:
        p = pc.get(f["slot"], {})
        for sig in _EXPECTED_TRIP_DAYS:
            if sig.lower() in (f.get("caption") or "").lower():
                by_caption_sig[sig] = p.get("days", [])

    failures = []
    for sig, expected in _EXPECTED_TRIP_DAYS.items():
        days = by_caption_sig.get(sig)
        if days is None:
            failures.append(f'{sig!r}: trip not found in featured passport stamps')
            continue
        if len(days) != expected:
            failures.append(f'{sig!r}: days={len(days)}, expected {expected}')

    if failures:
        return False, '; '.join(failures)
    return True, ', '.join(f'{s}={_EXPECTED_TRIP_DAYS[s]}' for s in _EXPECTED_TRIP_DAYS)


def check_stanley_park_excludes_unrelated_leg(rows, html):
    """
    Direct regression guard for the exact scenario the handoff describes: the
    Stanley Park _away_clusters() cluster (pre-sig-filter) is larger than the
    Stanley Park trip itself, because unrelated Seattle/Nanaimo activities
    fall inside the same 5-day-gap window. If _passport_data() ever filters
    by the whole cluster instead of sig-matched members again, this would
    silently pass check_multiday_trip_day_counts() too (a bigger cluster can
    coincidentally sum to the same day count) -- so this checks the actual
    activity names, not just a count.
    """
    clusters = _away_clusters(rows)
    stanley_cluster = None
    for c in clusters:
        names = [(r.get("name") or "") for _, _, r in c]
        if any("stanley park" in n.lower() for n in names):
            stanley_cluster = c
            break
    if stanley_cluster is None:
        return False, 'No away-cluster contains a "Stanley Park" activity'
    if len(stanley_cluster) < 3:
        return False, (f'Stanley Park cluster only has {len(stanley_cluster)} members -- '
                        f'test fixture assumption (an unrelated leg in the same cluster) no '
                        f'longer holds; update this test against current data')

    featured, brief, pc, n_states, n_prov = _passport_data(rows)
    stanley_days = None
    for f in featured:
        if "stanley park" in (f.get("caption") or "").lower():
            stanley_days = pc.get(f["slot"], {}).get("days", [])
            break
    if stanley_days is None:
        return False, 'Stanley Park trip not found in featured passport stamps'
    if len(stanley_days) >= len(stanley_cluster):
        return False, (f'Stanley Park days ({len(stanley_days)}) includes the whole '
                        f'{len(stanley_cluster)}-member cluster -- sig filter is not '
                        f'excluding the unrelated leg')
    return True, (f'Stanley Park days={len(stanley_days)} '
                  f'< cluster size={len(stanley_cluster)} (unrelated leg excluded)')


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS = [
    ("Places Hero -- HTML/JS",   check_places_no_duplicate_route),
    ("Places Hero -- HTML/JS",   check_places_terrain_pitch_baked_into_fit),
    ("Places Hero -- Trip Data", check_multiday_trip_day_counts),
    ("Places Hero -- Trip Data", check_stanley_park_excludes_unrelated_leg),
]


def _print_results(results):
    width = 62
    print()
    print("+" + "-" * width + "+")
    print("|" + "  Strava Dashboard -- QA Report".center(width) + "|")
    print("+" + "-" * width + "+")

    current_group = None
    passed_count = 0
    for group, fn_name, passed, message in results:
        if group != current_group:
            print(f"\n{group}")
            current_group = group
        status = "PASS" if passed else "FAIL"
        label = fn_name.replace("check_", "")
        print(f"  {status}  {label:<38}  {message}")
        if passed:
            passed_count += 1

    total = len(results)
    print()
    print("-" * (width + 2))
    overall = "PASSED" if passed_count == total else "FAILED"
    print(f"Result: {passed_count}/{total} {overall}")
    print()


def run_all() -> bool:
    rows = load_activities()
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
