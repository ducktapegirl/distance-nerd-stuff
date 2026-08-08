"""
Places Hero -- dynamic (rendered) regression tests
Run: uv run python tools/qa-checks/places-hero-dynamic.py [--url URL]
Exit 0 = all pass, 1 = any fail

For issues that only exist as a function of real camera animation timing in a
real browser -- can't be caught by a text/regex check against the built HTML,
since the code path is correct on paper and only breaks at runtime. Static
checks (JS source guards, data-assembly correctness) live in
strava-data/qa.py instead; add there first if a regex check can prove it.

Tests:
- First activity click after a fresh page load zooms to that activity, not
  the aggregate view (setStyle() was destroying the in-flight fitBounds)
- Deep-link ?a=<id>&b=terrain opens already framed on that activity

Requires Playwright (uv add --dev playwright; uv run playwright install chromium).
Runs headless via tools/mobile_preview.py (transport T2).
"""
import sys
import json
import subprocess
import tempfile
import argparse
from pathlib import Path


HERE = Path(__file__).parent.parent  # tools/
REPO_ROOT = HERE.parent
MOBILE_PREVIEW = HERE / "mobile_preview.py"


def run_mobile_preview(url: str, hash_frag: str, eval_js: str) -> dict:
    """
    Run JavaScript on a page via tools/mobile_preview.py.
    Returns the eval result dict, or raises on failure.
    """
    if not MOBILE_PREVIEW.exists():
        raise FileNotFoundError(f"mobile_preview.py not found at {MOBILE_PREVIEW}")

    # Write eval JS to temp file (more reliable than shell quoting)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(eval_js)
        temp_js = f.name

    try:
        result = subprocess.run(
            [sys.executable, str(MOBILE_PREVIEW),
             "--desktop", "--url", url, "--hash", hash_frag,
             "--settle", "4000", "--eval", f"@{temp_js}"],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            raise RuntimeError(f"mobile_preview.py failed:\n{result.stderr}")

        # Parse JSON output. The output may have server logs on stderr and partial
        # output before the JSON. Find the complete JSON object.
        text = result.stdout.strip()
        if not text:
            raise RuntimeError(f"No output from mobile_preview:\n{result.stderr}")

        # Search for the JSON start and extract it carefully
        start_idx = text.find('{')
        if start_idx == -1:
            raise RuntimeError(f"No JSON in output:\n{text[:500]}")

        # Extract from '{' to the last '}'
        json_text = text[start_idx:]
        # Find the last '}' to complete the JSON
        end_idx = json_text.rfind('}')
        if end_idx == -1:
            raise RuntimeError(f"Malformed JSON (no closing brace):\n{json_text[:500]}")

        json_text = json_text[:end_idx + 1]
        data = json.loads(json_text)
        if 'eval' not in data:
            raise RuntimeError(f"No 'eval' key in output: {data}")
        return data['eval']
    finally:
        Path(temp_js).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test 1: First activity click zooms to the activity (not aggregate view)
# ---------------------------------------------------------------------------

TEST_FIRST_CLICK_JS = """
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let M = null;
  const P = maplibregl.Map.prototype;
  const cid = m => { try { const c = m.getContainer(); return c ? c.id : '?'; } catch (e) { return '!'; } };
  ['fitBounds', 'easeTo', 'jumpTo', 'flyTo'].forEach(n => {
    const o = P[n];
    P[n] = function () { if (cid(this) === 'places-map' && !M) M = this; return o.apply(this, arguments); };
  });
  window.dispatchEvent(new Event('resize'));
  await sleep(500);

  const stamps = [...document.querySelectorAll('[data-stamp]')].filter(e => e.tagName !== 'CANVAS');
  stamps[0].click();
  await sleep(8000);

  const id = (location.hash.match(/[?&]a=([^&]+)/) || [])[1] || null;
  const box = id && window.placesFlyTargets ? window.placesFlyTargets[id] : null;
  const c = M ? [+M.getCenter().lng.toFixed(4), +M.getCenter().lat.toFixed(4)] : null;
  const inBox = box ? (c && c[0] > box.lng0 - 0.4 && c[0] < box.lng1 + 0.4 &&
                             c[1] > box.lat0 - 0.4 && c[1] < box.lat1 + 0.4) : null;
  return {
    id, inBox,
    z: M ? +M.getZoom().toFixed(3) : null,
    p: M ? +M.getPitch().toFixed(1) : null,
    terrain: M ? !!M.getTerrain() : null,
    route: M ? !!M.getLayer('places-activity-route-line') : null,
    stuck: M ? M.isMoving() : null,
    PASS: !!(inBox && M && M.getZoom() > 8 && M.getPitch() > 55 && M.getTerrain() && !M.isMoving())
  };
})()
"""

def check_first_click_zoom(url: str) -> tuple[bool, str]:
    """
    First activity click after a fresh load should zoom to the activity,
    not stay on the aggregate view. This was the main bug: z≈3.5 instead of z≈11.
    """
    try:
        result = run_mobile_preview(url, "places", TEST_FIRST_CLICK_JS)
        if not result.get('PASS'):
            z = result.get('z')
            inBox = result.get('inBox')
            if z and z < 5:
                return False, f'First click stuck at z={z} (aggregate view), not framed on activity'
            return False, f'First click: z={z}, pitch={result.get("p")}, inBox={inBox}, terrain={result.get("terrain")}'
        return True, f'First click zooms to activity: z={result.get("z")}, pitch={result.get("p")}, route visible'
    except Exception as e:
        return False, f'Test failed: {e}'


# ---------------------------------------------------------------------------
# Test 2: Deep-link ?a=<id>&b=terrain opens correctly framed
# ---------------------------------------------------------------------------

TEST_DEEPLINK_JS = """
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let M = null;
  const P = maplibregl.Map.prototype;
  const cid = m => { try { const c = m.getContainer(); return c ? c.id : '?'; } catch (e) { return '!'; } };
  ['resize','fitBounds', 'easeTo', 'flyTo'].forEach(n => {
    const o = P[n];
    P[n] = function () { if (cid(this) === 'places-map' && !M) M = this; return o.apply(this, arguments); };
  });
  window.dispatchEvent(new Event('resize'));
  await sleep(8000);

  const id = (location.hash.match(/[?&]a=([^&]+)/) || [])[1] || null;
  const box = id && window.placesFlyTargets ? window.placesFlyTargets[id] : null;
  const c = M ? [+M.getCenter().lng.toFixed(4), +M.getCenter().lat.toFixed(4)] : null;
  const inBox = box ? (c && c[0] > box.lng0 - 0.4 && c[0] < box.lng1 + 0.4 &&
                             c[1] > box.lat0 - 0.4 && c[1] < box.lat1 + 0.4) : null;
  return {
    id, inBox,
    z: M ? +M.getZoom().toFixed(3) : null,
    p: M ? +M.getPitch().toFixed(1) : null,
    terrain: M ? !!M.getTerrain() : null,
    route: M ? !!M.getLayer('places-activity-route-line') : null,
    PASS: !!(inBox && M && M.getZoom() > 8 && M.getPitch() > 55)
  };
})()
"""

def check_deeplink_terrain(url: str) -> tuple[bool, str]:
    """
    Deep-linking with ?a=<id>&b=terrain should open framed on that activity
    in 3D Terrain mode. This tests the alternative entry path (boot-time framing).
    """
    # Use a real activity ID from the page
    try:
        result = run_mobile_preview(url, "places?a=16005045227&b=terrain", TEST_DEEPLINK_JS)
        if not result.get('PASS'):
            return False, f'Deep-link ?a=...&b=terrain: z={result.get("z")}, pitch={result.get("p")}, inBox={result.get("inBox")}'
        return True, f'Deep-link terrain opens framed: z={result.get("z")}, pitch={result.get("p")}'
    except Exception as e:
        return False, f'Test failed: {e}'


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

CHECKS = [
    ("Places Camera", check_first_click_zoom),
    ("Places Camera", check_deeplink_terrain),
]


def _print_results(results: list[tuple[str, str, bool, str]]):
    width = 62
    print()
    print("+" + "-" * width + "+")
    print("|" + "  Places Hero Camera Tests".center(width) + "|")
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765/strava.html",
                        help="URL of the Strava dashboard (default: local dev server)")
    args = parser.parse_args()

    print(f"Testing {args.url}")
    print("(This requires Playwright and tools/mobile_preview.py)")

    results = []
    all_pass = True
    for group, fn in CHECKS:
        passed, message = fn(args.url)
        results.append((group, fn.__name__, passed, message))
        if not passed:
            all_pass = False

    _print_results(results)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
