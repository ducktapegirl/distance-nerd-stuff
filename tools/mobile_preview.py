"""Reliable host-side browser preview for the static dashboards ("T2").

Serves a directory from an in-process server bound to ``127.0.0.1`` and drives
a Playwright Chromium against it in the *same* host process, so the browser,
the server, and the plotly CDN are all reachable. This is transport **T2** of
the QA visual suite (``.claude/qa-visual-suite.md``); the Claude Preview MCP is
T1. Which one is available depends on the environment — on some machines the
Preview MCP's Chromium cannot reach a local server and lands on
``chrome-error://``, which is what this script exists to work around — so the
suite probes rather than assumes. Use ``--probe`` to report usability.

Mobile emulation (touch, DPR 2, 375x812) is the default because that is where
the rendering bugs live. Pass ``--desktop`` for a true desktop render
(1440x900, no touch, DPR 1) — a wide viewport alone is *not* a desktop render.

Run it **un-sandboxed** — the page loads ``plotly.js`` from ``cdn.plot.ly`` and
needs real internet to render charts.

Setup (once):
    uv add --dev playwright
    uv run playwright install chromium

Examples:
    # Is this transport usable here? exit 0 = yes, 2 = no (JSON says why).
    uv run python tools/mobile_preview.py --probe

    # Diagnose: load overview, click the Exploratory tab, measure the chart at
    # each stage (hidden -> after click -> after a simulated resize) + shot.
    uv run python tools/mobile_preview.py \
        --click '.tab[data-view="exploratory"]' \
        --measure chart-x-seasonal --resize-probe \
        --screenshot tools/preview-output/seasonal-mobile.png

    # Run a QA suite check file at mobile width, then at desktop width:
    uv run python tools/mobile_preview.py --eval @tools/qa-checks/width-fill.js
    uv run python tools/mobile_preview.py --desktop \
        --eval @tools/qa-checks/width-fill.js

    # Light-mode theme audit of the running-log dashboard:
    uv run python tools/mobile_preview.py --page /index.html --theme light \
        --eval @tools/qa-checks/contrast.js

    # Verify against production instead of the local build:
    uv run python tools/mobile_preview.py \
        --url https://ducktapegirl.github.io/distance-nerd-stuff/strava.html \
        --click '.tab[data-view="exploratory"]' --measure chart-x-seasonal

    # Arbitrary JS probe:
    uv run python tools/mobile_preview.py --eval 'document.title'
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import socket
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(REPO_ROOT, "running-log")

# Builtin measurement: everything needed to tell whether a Plotly chart fills
# its card and has sane axis ranges. Returned as a JSON-able dict.
MEASURE_JS = r"""
(id) => {
  const el = document.getElementById(id);
  const out = {id, found: !!el};
  if (!el) return out;
  const card = el.closest('.card');
  const view = el.closest('.view');
  const svg = el.querySelector('svg.main-svg');
  out.viewId = view && view.id;
  out.viewActive = view ? view.classList.contains('active') : null;
  out.cardW = card ? card.clientWidth : null;
  out.elW = el.clientWidth;
  out.svgW = svg ? Math.round(svg.getBoundingClientRect().width) : null;
  const f = el._fullLayout;
  out.ready = !!f;
  if (f) {
    out.flW = f.width;
    out.flH = f.height;
    out.size = f._size;
    out.autosize = f.autosize;
    out.xRange = f.xaxis && f.xaxis.range;
    out.yRange = f.yaxis && f.yaxis.range;
    out.y2Range = f.yaxis2 ? f.yaxis2.range : null;
  }
  // overfilled = SVG wider than its card (clipped by .card{overflow:hidden});
  // underfilled = SVG noticeably narrower than the card.
  if (out.svgW != null && out.cardW) {
    out.overflowPx = out.svgW - out.cardW;
    out.fillRatio = +(out.svgW / out.cardW).toFixed(3);
  }
  return out;
}
"""


def _discover_chromium() -> str:
    """Find a usable Chromium when Playwright's own lookup comes up empty.

    Playwright resolves a browser build number pinned to its package version,
    so an environment that ships a *different* build (the web/remote containers
    provide 1194 under PLAYWRIGHT_BROWSERS_PATH while a newer Playwright wants
    1223) fails to launch even though a perfectly good Chromium is sitting
    right there. Prefer the convenience symlink those images provide, then any
    versioned build, newest first. Returns "" when nothing is found.
    """
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "", "/opt/pw-browsers"]
    patterns = [
        "chromium",                                                   # symlink
        "chromium-*/chrome-linux/chrome",
        "chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
        "chromium-*/chrome-win/chrome.exe",
        "chromium_headless_shell-*/chrome-linux/headless_shell",
    ]
    for root in roots:
        if not root:
            continue
        for pat in patterns:
            for cand in sorted(glob.glob(os.path.join(root, pat)), reverse=True):
                if os.path.exists(cand) and os.access(cand, os.X_OK):
                    return cand
    return ""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(directory: str, port: int) -> ThreadingHTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _resolve_eval(value: str) -> str:
    """--eval accepts a raw JS expression or '@path/to/file.js'."""
    if value.startswith("@"):
        with open(value[1:], encoding="utf-8") as fh:
            return fh.read()
    return value


def _fail(reason: str, detail: str = "", hint: str = "") -> int:
    """Emit a structured transport failure and exit 2.

    The QA visual suite's V0 probe keys off this shape, so the failure must
    name *which* piece is missing rather than dumping a traceback: an absent
    Playwright package, an unresolvable Chromium, and a blocked CDN each call
    for a different fix, and only the caller can tell them apart.
    """
    json.dump({"transport": "T2", "ok": False, "reason": reason,
               "detail": detail, "hint": hint}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=DEFAULT_DIR,
                    help="directory to serve (default: 'running-log')")
    ap.add_argument("--page", default="/strava.html",
                    help="path under the served dir (default: /strava.html)")
    ap.add_argument("--hash", default="",
                    help="optional URL #fragment (e.g. 'exploratory')")
    ap.add_argument("--url", default="",
                    help="absolute URL to load instead of the local server "
                         "(e.g. the deployed site)")
    ap.add_argument("--width", type=int, default=None,
                    help="viewport width (default 375, or 1440 with --desktop)")
    ap.add_argument("--height", type=int, default=None,
                    help="viewport height (default 812, or 900 with --desktop)")
    ap.add_argument("--desktop", action="store_true",
                    help="run WITHOUT mobile emulation (no touch, DPR 1) and "
                         "default the viewport to 1440x900 -- required for the "
                         "QA suite's desktop pass, which is otherwise still "
                         "mobile-emulated")
    ap.add_argument("--theme", choices=["light", "dark", "system"], default="",
                    help="click the page's theme toggle after load and settle")
    ap.add_argument("--click", action="append", default=[],
                    help="CSS selector to click (repeatable)")
    ap.add_argument("--measure", default="",
                    help="element id to measure (Plotly chart div)")
    ap.add_argument("--resize-probe", action="store_true",
                    help="after measuring, dispatch a window resize and re-measure")
    ap.add_argument("--eval", default="",
                    help="arbitrary JS expression or @file to evaluate")
    ap.add_argument("--screenshot", default="",
                    help="path to save a PNG (full active viewport)")
    ap.add_argument("--settle", type=int, default=450,
                    help="ms to wait after load / each click (default 450)")
    ap.add_argument("--plotly-timeout", type=int, default=15000,
                    help="ms to wait for window.Plotly (default 15000). Lower "
                         "it in environments where the plotly CDN is known to "
                         "be blocked, so DOM/theme checks don't pay the full "
                         "wait on every invocation")
    ap.add_argument("--headed", action="store_true", help="show the browser")
    ap.add_argument("--probe", action="store_true",
                    help="report whether this transport is usable (browser "
                         "launches, page loads, Plotly renders) and exit; "
                         "exit 0 = usable, 2 = not")
    args = ap.parse_args()

    # Mobile is the default because that is where the rendering bugs live; the
    # desktop pass has to opt out of emulation explicitly.
    width = args.width if args.width is not None else (1440 if args.desktop else 375)
    height = args.height if args.height is not None else (900 if args.desktop else 812)
    mobile = not args.desktop

    httpd = None
    if args.url:
        url = args.url + (f"#{args.hash}" if args.hash else "")
    else:
        port = _free_port()
        httpd = _serve(args.dir, port)
        frag = f"#{args.hash}" if args.hash else ""
        url = f"http://127.0.0.1:{port}{args.page}{frag}"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        if httpd is not None:
            httpd.shutdown()
        return _fail("playwright-not-installed", str(exc),
                     "uv add --dev playwright && uv run playwright install chromium")

    report: dict = {
        "transport": "T2", "url": url, "viewport": [width, height],
        "emulation": "mobile" if mobile else "desktop",
    }
    try:
        with sync_playwright() as p:
            # Resolve Chromium in whichever environment this is running in.
            # PLAYWRIGHT_CHROMIUM_PATH is an explicit per-machine override;
            # otherwise defer to Playwright, which honours
            # PLAYWRIGHT_BROWSERS_PATH (set to /opt/pw-browsers in the web /
            # remote containers) and falls back to its own install location.
            override = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or ""
            try:
                browser = p.chromium.launch(headless=not args.headed,
                                            executable_path=override or None)
                report["chromium_path"] = override or "playwright-default"
            except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                # Playwright's pinned build may not be the one this environment
                # ships; fall back to whatever Chromium is actually present.
                found = "" if override else _discover_chromium()
                if not found:
                    return _fail(
                        "chromium-not-launchable", str(exc)[:500],
                        "uv run playwright install chromium, or set "
                        "PLAYWRIGHT_CHROMIUM_PATH to an existing Chromium binary",
                    )
                try:
                    browser = p.chromium.launch(headless=not args.headed,
                                                executable_path=found)
                except Exception as exc2:  # noqa: BLE001
                    return _fail(
                        "chromium-not-launchable", str(exc2)[:500],
                        f"discovered {found} but it failed to launch; "
                        "set PLAYWRIGHT_CHROMIUM_PATH to a working binary",
                    )
                report["chromium_path"] = found
                report["chromium_note"] = (
                    "Playwright's pinned build was unavailable; fell back to a "
                    "Chromium found in this environment"
                )
            report["chromium"] = browser.version
            # is_mobile drives touch events and the visual viewport, so the
            # desktop pass must turn it off -- a 1440px viewport under mobile
            # emulation is not a desktop render.
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2 if mobile else 1,
                is_mobile=mobile, has_touch=mobile,
            )
            page = context.new_page()
            console_errors: list = []
            page.on("console", lambda m: console_errors.append(m.text)
                    if m.type == "error" else None)
            page.goto(url, wait_until="load")
            # Wait for Plotly + the init JS (runs on window 'load') to settle.
            plotly_ok = True
            try:
                page.wait_for_function("() => !!window.Plotly",
                                       timeout=args.plotly_timeout)
            except Exception:
                plotly_ok = False
                report["warning"] = (
                    "window.Plotly never appeared - the page pulls plotly.js "
                    "from cdn.plot.ly, so the browser reached the page but not "
                    "the CDN. Charts cannot render without it, so chart-level "
                    "checks are unavailable; DOM/theme checks still work."
                )
            page.wait_for_timeout(args.settle)

            if args.probe:
                report["ok"] = plotly_ok
                report["plotly"] = plotly_ok
                if not plotly_ok:
                    report["reason"] = "plotly-cdn-unreachable"
                    report["hint"] = (
                        "re-run un-sandboxed; if that fails too, this "
                        "environment's network policy blocks cdn.plot.ly and "
                        "T2 can only serve DOM/theme checks here"
                    )
                browser.close()
                json.dump(report, sys.stdout, indent=2)
                sys.stdout.write("\n")
                return 0 if plotly_ok else 2

            if args.theme:
                sel = f'.theme-toggle button[data-theme="{args.theme}"]'
                try:
                    page.click(sel, timeout=5000)
                    page.wait_for_timeout(args.settle)
                    report["theme"] = args.theme
                except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                    report["theme_error"] = f"{sel} not clickable: {str(exc)[:200]}"

            if args.measure and args.click:
                report["before_click"] = page.evaluate(MEASURE_JS, args.measure)

            for sel in args.click:
                page.click(sel, timeout=10000)
                page.wait_for_timeout(args.settle)

            if args.measure:
                key = "after_click" if args.click else "initial"
                report[key] = page.evaluate(MEASURE_JS, args.measure)

            if args.measure and args.resize_probe:
                # Trigger the page's debounced window-resize handler, then wait
                # out the 150ms debounce before re-measuring.
                page.evaluate("() => window.dispatchEvent(new Event('resize'))")
                page.wait_for_timeout(max(args.settle, 400))
                report["after_resize"] = page.evaluate(MEASURE_JS, args.measure)

            if args.eval:
                report["eval"] = page.evaluate(_resolve_eval(args.eval))

            if args.screenshot:
                os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)),
                            exist_ok=True)
                page.screenshot(path=args.screenshot)
                report["screenshot"] = args.screenshot

            if console_errors:
                report["console_errors"] = console_errors[:20]

            browser.close()
    finally:
        if httpd is not None:
            httpd.shutdown()

    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
