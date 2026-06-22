"""Reliable host-side mobile preview for the static dashboards.

The Claude Preview MCP cannot reach a local ``http.server`` on this machine
(its Chromium lands on ``chrome-error://`` and the server is unreachable even
un-sandboxed), so visual/mobile verification goes through this script instead.
It serves a directory from an in-process server bound to ``127.0.0.1`` and
drives a mobile-emulated Playwright Chromium against it in the *same* host
process, so the browser, the server, and the plotly CDN are all reachable.

Run it **un-sandboxed** — the page loads ``plotly.js`` from ``cdn.plot.ly`` and
needs real internet to render charts.

Setup (once):
    uv add --dev playwright
    uv run playwright install chromium

Examples:
    # Diagnose: load overview, click the Exploratory tab, measure the chart at
    # each stage (hidden -> after click -> after a simulated resize) + shot.
    uv run python tools/mobile_preview.py \
        --click '.tab[data-view="exploratory"]' \
        --measure chart-x-seasonal --resize-probe \
        --screenshot out/seasonal-mobile.png

    # Verify against production instead of the local build:
    uv run python tools/mobile_preview.py \
        --url https://ducktapegirl.github.io/strava.html \
        --click '.tab[data-view="exploratory"]' --measure chart-x-seasonal

    # Arbitrary JS probe:
    uv run python tools/mobile_preview.py --eval 'document.title'
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(REPO_ROOT, "Running Log")

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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=DEFAULT_DIR,
                    help="directory to serve (default: 'Running Log')")
    ap.add_argument("--page", default="/strava.html",
                    help="path under the served dir (default: /strava.html)")
    ap.add_argument("--hash", default="",
                    help="optional URL #fragment (e.g. 'exploratory')")
    ap.add_argument("--url", default="",
                    help="absolute URL to load instead of the local server "
                         "(e.g. the deployed site)")
    ap.add_argument("--width", type=int, default=375)
    ap.add_argument("--height", type=int, default=812)
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
    ap.add_argument("--headed", action="store_true", help="show the browser")
    args = ap.parse_args()

    httpd = None
    if args.url:
        url = args.url + (f"#{args.hash}" if args.hash else "")
    else:
        port = _free_port()
        httpd = _serve(args.dir, port)
        frag = f"#{args.hash}" if args.hash else ""
        url = f"http://127.0.0.1:{port}{args.page}{frag}"

    from playwright.sync_api import sync_playwright

    report: dict = {"url": url, "viewport": [args.width, args.height]}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headed)
            context = browser.new_context(
                viewport={"width": args.width, "height": args.height},
                device_scale_factor=2, is_mobile=True, has_touch=True,
            )
            page = context.new_page()
            page.goto(url, wait_until="load")
            # Wait for Plotly + the init JS (runs on window 'load') to settle.
            try:
                page.wait_for_function("() => !!window.Plotly", timeout=15000)
            except Exception:
                report["warning"] = "window.Plotly never appeared"
            page.wait_for_timeout(args.settle)

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

            browser.close()
    finally:
        if httpd is not None:
            httpd.shutdown()

    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
