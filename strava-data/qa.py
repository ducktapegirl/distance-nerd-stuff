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
from dashboard.charts_places import _passport_data, _away_clusters, _peaks_data
from dashboard.art_year import prepare as _art_prepare, scale_of as _art_scale_of, year_layer as _art_year_layer

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
def _trip_cluster_for(clusters, act_id):
    """The _away_clusters() cluster containing a passport slot's signature id."""
    for c in clusters:
        if any(str(r["id"]) == str(act_id) for _, _, r in c):
            return c
    return None


def check_multiday_trip_day_counts(rows, html):
    """
    A featured stamp's "days" must cover EVERY member of its _away_clusters()
    cluster -- the cluster is the trip. `sig` selects the signature activity
    whose GPS drives the thumbnail; it must never filter the route set.

    97addbf filtered days by sig, which only ever worked for Maine Hut (whose
    activities happen to be named "Maine Hut Trail Day 1/2/3"). Every other
    trip drew a subset of the ground its own camera box, date span and sport
    tags claim -- Whitney drew 1 day of 3, Stanley Park 2 of 6 (both the same
    calendar day), so a "Sep 29 - Oct 2" trip rendered as a single morning.

    Checked against the cluster rather than hardcoded per-trip counts so the
    guard keeps working as data grows; the pinned counts below are a second,
    coarser tripwire for the specific trips in the bug report.
    """
    featured, brief, pc, n_states, n_prov = _passport_data(rows)
    clusters = _away_clusters(rows)

    failures, seen = [], {}
    for f in featured:
        p = pc.get(f["slot"], {})
        days = p.get("days", [])
        caption = f.get("caption") or f["slot"]
        c = _trip_cluster_for(clusters, p.get("id"))
        if c is None:
            failures.append(f'{caption!r}: signature activity is in no away-cluster')
            continue
        seen[caption] = len(days)
        if len(days) != len(c):
            failures.append(f'{caption!r}: days={len(days)}, cluster has {len(c)} '
                            f'members -- the whole cluster is the trip')

    # Coarser tripwire for the two trips this regression was reported against.
    for sig, expected in (("Whitney", 3), ("Stanley Park", 6), ("Maine Hut", 3)):
        hit = [n for cap, n in seen.items() if sig.lower() in cap.lower()]
        if not hit:
            failures.append(f'{sig!r}: trip not found in featured passport stamps')
        elif hit[0] != expected:
            failures.append(f'{sig!r}: days={hit[0]}, expected {expected}')

    if failures:
        return False, '; '.join(failures)
    return True, f'{len(seen)} trips, every day of every cluster drawn'


def check_trip_fly_box_contains_route(rows, html):
    """
    A stamp's camera box must contain every line the hero draws for it.

    The box used to be built from activity START points, which are one END of a
    route -- so a trip could clip its own line (Whitney's route reaches
    -118.2970W; its start-point box stopped at -118.2903W). Combined with the
    sig filter this is what made the bug read as "the route didn't render":
    geometry framed off-screen looks identical to geometry that is missing.
    """
    featured, brief, pc, n_states, n_prov = _passport_data(rows)
    failures = []
    for f in featured:
        p = pc.get(f["slot"], {})
        fly, days = p.get("fly"), p.get("days", [])
        if not fly or not days:
            continue
        lats, lngs = [], []
        for d in days:
            c = d["c"]
            lngs += c[0::2]
            lats += c[1::2]
        if not lats:
            continue
        if not (fly["lat0"] <= min(lats) and fly["lat1"] >= max(lats)
                and fly["lng0"] <= min(lngs) and fly["lng1"] >= max(lngs)):
            failures.append(
                f'{(f.get("caption") or f["slot"])!r}: route lat '
                f'[{min(lats):.4f},{max(lats):.4f}] lng [{min(lngs):.4f},{max(lngs):.4f}] '
                f'escapes fly box {fly}')
    if failures:
        return False, '; '.join(failures)
    return True, f'{len(featured)} trip boxes each contain their whole route'


def check_peaks_do_not_clobber_trip_fly_box(rows, html):
    """
    Passport and peaks publish into ONE id-keyed window.placesFlyTargets and do
    collide (Mt. Whitney is both a 3-day trip and two peak rows). Peaks is
    emitted second (page.py), so before `flypri` it silently won -- a
    '#places?a=<whitney>' deep link framed the summit day alone and left the
    trip's other two days drawn but off-screen.

    Guards both halves: the payload carries a priority, and the publish loop
    actually honors it rather than last-writer-wins.
    """
    _f, _b, pc, _s, _p = _passport_data(rows)
    _pk, pd = _peaks_data(rows)

    trip_pri = {str(v["id"]): v for v in pc.values() if v.get("id") and v.get("fly")}
    peak_pri = {str(v["id"]): v for v in pd.values() if v.get("id") and v.get("fly")}
    shared = sorted(set(trip_pri) & set(peak_pri))
    if not shared:
        return False, ('No id appears in both the passport and peaks payloads -- this '
                       'guard\'s fixture assumption no longer holds; re-check against '
                       'current data rather than deleting it')

    failures = []
    for aid in shared:
        t, k = trip_pri[aid], peak_pri[aid]
        if not t.get("flypri", 0) > k.get("flypri", 0):
            failures.append(f'{aid}: passport flypri={t.get("flypri")} does not beat '
                            f'peaks flypri={k.get("flypri")}')

    if "window.placesFlyPri" not in html:
        failures.append("publish loop is not priority-gated (no window.placesFlyPri)")
    if re.search(r"var e = PC\[s\];\s*if\(e && e\.id && e\.fly\)\{\s*window\.placesFlyTargets",
                 html):
        failures.append("publish loop still does last-writer-wins on placesFlyTargets")

    if failures:
        return False, '; '.join(failures)
    return True, (f'{len(shared)} colliding id(s) ({", ".join(shared)}); '
                  f'trip box wins, loop priority-gated')


def check_art_theme_vars(rows, html):
    """
    The Art tab's year clock is themed by CSS custom properties (--art-*)
    cascading into an inline SVG, not by applyChartTheme() -- see
    dashboard-spec.md "Art tab" > Rules this view has that the others do not.
    A literal hex slipping back into the interactive path renders as black,
    which is nearly invisible next to the dark ground in a screenshot but
    obvious in the source, so this guards the source directly: no literal
    color attributes inside #art-svg, both theme blocks declare the same
    --art-* names (a token added to one and forgotten in the other is
    invisible in a single-theme screenshot), and the static/print path (which
    must stay literal -- rasterizers don't implement var()) never emits var(.
    """
    svg_m = re.search(r'<svg id="art-svg".*?</svg>', html, re.DOTALL)
    if not svg_m:
        return False, 'no <svg id="art-svg"> found in built HTML'
    svg = svg_m.group(0)

    style_m = re.search(r'<style>(.*?--art-run.*?)</style>', html, re.DOTALL)
    if not style_m:
        return False, 'no art <style> block found (no --art-run in any <style>)'
    style = style_m.group(1)

    failures = []

    literal = sorted(set(re.findall(r'(?:stroke|fill|stop-color)="(#[0-9a-fA-F]+)"', svg)))
    if literal:
        failures.append(f"literal hex color(s) in #art-svg: {literal}")

    if "--art-" not in svg:
        failures.append("no --art-* custom property referenced inside #art-svg")

    root_m = re.search(r':root\{([^}]*)\}', style)
    light_m = re.search(r':root\.light\{([^}]*)\}', style)
    root_names = set()
    if not root_m or not light_m:
        failures.append("could not find both :root and :root.light token blocks")
    else:
        root_names = set(re.findall(r'(--art-[\w-]+)\s*:', root_m.group(1)))
        light_names = set(re.findall(r'(--art-[\w-]+)\s*:', light_m.group(1)))
        if root_names != light_names:
            failures.append(
                f":root and :root.light --art-* sets differ -- "
                f"only in :root: {sorted(root_names - light_names)}, "
                f"only in :root.light: {sorted(light_names - root_names)}")

    if "ARTBG" in html:
        failures.append('"ARTBG" placeholder leaked into the built HTML')
    if "background:var(--art-bg)" not in html:
        failures.append("#art-svg background is not background:var(--art-bg)")

    legend_m = re.search(r'<div class="art-bar" id="art-legend">(.*?)</div>', html, re.DOTALL)
    if legend_m and 'style="background:#' in legend_m.group(1):
        failures.append("legend swatch still uses an inline literal background")

    acts = _art_prepare(list(rows))
    if not acts:
        failures.append("no activities to exercise the static year_layer() path")
    else:
        year = acts[0]["yr"]
        year_acts = [a for a in acts if a["yr"] == year]
        static = _art_year_layer(year_acts, {}, year, _art_scale_of(year_acts, {}),
                                 interactive=False, visible=True)
        if "var(" in static:
            failures.append("year_layer(interactive=False) leaked var( into its output")

    if failures:
        return False, '; '.join(failures)
    return True, f'{len(root_names)} --art-* tokens, equal in :root and :root.light'


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def check_new_art_theme_vars(rows, html):
    """
    The same both-themes guard as check_art_theme_vars, for the three pieces
    added alongside the year clock: Contour Field (--co-*), Signature Route
    (--sg-*) and Tangle (--tg-*).

    Each ships its own <style> carrying a :root / :root.light pair. A token
    declared in only one of them is invisible in a single-theme screenshot and
    ships the light theme broken, which is exactly the failure this catches.
    Every piece must also actually reference its own custom properties in the
    SVG rather than falling back to literals.
    """
    failures = []
    for prefix, svg_id in (("co", "co-svg"), ("sg", "sg-svg"), ("tg", "tg-svg")):
        probe = "--%s-" % prefix
        style_m = re.search(r"<style>([^<]*?%s[\w-]+\s*:.*?)</style>" % probe,
                            html, re.DOTALL)
        if not style_m:
            failures.append("no <style> block declaring %s* tokens" % probe)
            continue
        style = style_m.group(1)
        root_m = re.search(r":root \{([^}]*)\}", style)
        light_m = re.search(r":root\.light \{([^}]*)\}", style)
        if not root_m or not light_m:
            failures.append("%s: missing :root or :root.light block" % prefix)
            continue
        pat = r"(--%s-[\w-]+)\s*:" % prefix
        root_names = set(re.findall(pat, root_m.group(1)))
        light_names = set(re.findall(pat, light_m.group(1)))
        if root_names != light_names:
            failures.append(
                "%s: :root and :root.light token sets differ -- "
                "only in :root: %s, only in :root.light: %s"
                % (prefix, sorted(root_names - light_names),
                   sorted(light_names - root_names)))
        if not re.search(r'<svg id="%s"' % svg_id, html):
            failures.append("no <svg id=\"%s\"> in the built HTML" % svg_id)
        elif probe not in html:
            failures.append("%s never referenced in the page" % probe)

    if failures:
        return False, "; ".join(failures)
    return True, "co/sg/tg tokens declared in both :root and :root.light"


CHECKS = [
    ("Places Hero -- HTML/JS",   check_places_no_duplicate_route),
    ("Places Hero -- HTML/JS",   check_places_terrain_pitch_baked_into_fit),
    ("Places Hero -- Trip Data", check_multiday_trip_day_counts),
    ("Places Hero -- Trip Data", check_trip_fly_box_contains_route),
    ("Places Hero -- Trip Data", check_peaks_do_not_clobber_trip_fly_box),
    ("Art -- Theme",             check_art_theme_vars),
    ("Art -- Theme",             check_new_art_theme_vars),
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
