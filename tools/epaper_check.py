"""Verify the built e-paper feed against the panel's hard constraints.

The reTerminal Sticky's limits are not preferences: below 26 px text is
physically invisible at 235 PPI, below 3 px a stroke does not survive e-ink,
and the panel neither scrolls nor runs JavaScript. Those are cheap to check and
expensive to discover on the device, so this checks them for every card.

Three groups:

1. **feed.xml** - well-formed, enough items, unique GUIDs, and no metric or
   Celsius units leaking into a title or description (the repo's display-units
   policy: miles, feet, min/mi, mph, degrees F).
2. **Every page** - ``epaper.html`` and each ``epaper/<id>.html`` at an
   800x480 viewport: no scroll in either axis, exactly one ``<svg>``, every
   ``<text>`` at 26 px or more, every stroke at 3 px or more once the element's
   own transform scale is applied, no two text boxes overlapping, nothing
   drawn outside the panel, and a clean console. The overlap check is the
   important one: the cards are hand-placed at absolute user units with no
   reflow, so a longer name or an extra row lands one label on top of another
   without tripping any other check. Ellipsized labels are counted and
   reported but do not fail - truncating a description is a legitimate choice,
   truncating a headline is not, and only a human can tell which happened.
3. **Screenshots** - one PNG per page under ``tools/preview-output/epaper/``,
   so a human can look at what the numbers passed.

Same ``--probe`` convention as ``tools/mobile_preview.py`` (exit 0 usable, 2
not, with a JSON ``reason``), and the same Chromium fallback. Unlike that
script this needs **no network at all** - the cards carry no CDN, no webfonts
and no JavaScript - so it runs anywhere Chromium does.

Setup (once):
    uv add --dev playwright
    uv run playwright install chromium

Examples:
    uv run python tools/epaper_check.py --probe
    uv run python tools/epaper_check.py
    uv run python tools/epaper_check.py --only latest,haiku,wildlife
    uv run python tools/epaper_check.py --no-screenshots
"""

import argparse
import glob
import json
import os
import re
import socket
import sys
import threading
import xml.etree.ElementTree as ET
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(_REPO, "running-log")
SHOT_DIR = os.path.join(_REPO, "tools", "preview-output", "epaper")

W, H = 800, 480
MIN_TEXT = 26
MIN_STROKE = 3
MIN_ITEMS = 17          # the rotation's size; the catalogue is far larger

# Display-units policy. Word-boundary matched so "5km" is caught but
# "Kilometre Road" as a segment name is not mistaken for a unit.
BANNED_UNITS = re.compile(r"\b\d+(\.\d+)?\s*(km|km/h|kph)\b|\b\d+\s*°\s*C\b|\bkm/h\b", re.I)

# Measure the rendered SVG in the page. Returns every violation rather than
# the first, so one run reports the whole card.
_MEASURE_JS = r"""() => {
  const out = {texts: [], strokes: [], svgs: document.querySelectorAll('svg').length,
               scrollW: document.documentElement.scrollWidth,
               scrollH: document.documentElement.scrollHeight};
  const scaleOf = el => {
    // A glyph is drawn in a 100-unit box and scaled down by its <g>, so the
    // authored stroke-width is not the effective one. Walk up and multiply.
    let s = 1, node = el;
    while (node && node.getAttribute) {
      const t = node.getAttribute('transform') || '';
      const m = t.match(/scale\(\s*([-\d.]+)/);
      if (m) s *= parseFloat(m[1]);
      node = node.parentNode;
    }
    return s;
  };
  for (const t of document.querySelectorAll('text')) {
    const size = parseFloat(getComputedStyle(t).fontSize) * scaleOf(t);
    if (size < 25.5) out.texts.push({size: +size.toFixed(2),
                                     text: (t.textContent || '').slice(0, 40)});
  }
  for (const el of document.querySelectorAll('[stroke-width]')) {
    if ((el.getAttribute('stroke') || 'none') === 'none') continue;
    const w = parseFloat(el.getAttribute('stroke-width')) * scaleOf(el);
    if (w < 2.95) out.strokes.push({w: +w.toFixed(2), tag: el.tagName});
  }
  // Overlap and clipping. Every layout here is hand-placed at absolute user
  // units with no reflow, so a card that gains a longer name or a second row
  // silently draws one label on top of another - invisible to a font-size
  // check and easy to miss in a screenshot.
  // getBoundingClientRect on <text> returns the em box, which carries ascent
  // and descent space well above and below the visible glyphs. Comparing em
  // boxes flags every ordinary number-over-label pairing. Inset vertically to
  // roughly the cap-to-baseline band so only real collisions register.
  const texts = [...document.querySelectorAll('text')]
    .map(el => {
      const r = el.getBoundingClientRect();
      const inset = parseFloat(getComputedStyle(el).fontSize) * scaleOf(el) * 0.2;
      return {t: (el.textContent || '').slice(0, 30), raw: r,
              b: {left: r.left, right: r.right,
                  top: r.top + inset, bottom: r.bottom - inset}};
    })
    .filter(o => o.raw.width > 0 && o.raw.height > 0);
  out.overlaps = [];
  for (let i = 0; i < texts.length; i++)
    for (let j = i + 1; j < texts.length; j++) {
      const a = texts[i].b, c = texts[j].b;
      const ox = Math.min(a.right, c.right) - Math.max(a.left, c.left);
      const oy = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top);
      // A couple of px is antialiasing slop, not a collision.
      if (ox > 2 && oy > 2)
        out.overlaps.push({a: texts[i].t, b: texts[j].t,
                           w: +ox.toFixed(0), h: +oy.toFixed(0)});
    }
  out.clipped = texts.filter(o => o.raw.left < -1 || o.raw.right > 801 ||
                                  o.raw.top < -1 || o.raw.bottom > 481)
                     .map(o => o.t);
  // Ellipsis is legitimate for a name or a description, but never for the
  // headline slot, which exists to carry the fact itself.
  out.ellipsized = texts.filter(o => o.t.includes('…')).map(o => o.t);
  return out;
}"""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(directory: str, port: int) -> ThreadingHTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _discover_chromium() -> str:
    """Find a Chromium when Playwright's pinned build is not the one present.

    Same fallback as tools/mobile_preview.py, for the same reason: the web and
    remote containers ship a different build number under
    PLAYWRIGHT_BROWSERS_PATH than the installed Playwright expects.
    """
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "", "/opt/pw-browsers"]
    patterns = [
        "chromium",
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


def _fail(reason: str, detail: str = "", hint: str = "") -> int:
    """Structured transport failure, exit 2 - the --probe contract."""
    json.dump({"transport": "epaper", "ok": False, "reason": reason,
               "detail": detail, "hint": hint}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 2


# ── group 1: the feed ─────────────────────────────────────────────────────

def check_feed(path):
    """Structural and units checks on feed.xml. Returns a list of failures."""
    bad = []
    if not os.path.exists(path):
        return [f"feed.xml missing: {path}"]
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"feed.xml is not well-formed: {exc}"]

    items = root.findall("./channel/item")
    if len(items) < MIN_ITEMS:
        bad.append(f"only {len(items)} items, expected at least {MIN_ITEMS}")

    guids = [(i.findtext("guid") or "").strip() for i in items]
    dupes = {g for g in guids if guids.count(g) > 1}
    if dupes:
        bad.append(f"duplicate GUIDs: {sorted(dupes)[:3]}")
    if any(not g for g in guids):
        bad.append("some items have no GUID")

    for item in items:
        for tag in ("title", "description"):
            text = item.findtext(tag) or ""
            hit = BANNED_UNITS.search(text)
            if hit:
                bad.append(f"metric unit {hit.group(0)!r} in <{tag}>: {text[:60]}")
    return bad


# ── group 2 + 3: the pages ────────────────────────────────────────────────

def check_pages(page, urls, shot_dir):
    """Load each page at panel size, measure it, and screenshot it."""
    results = []
    for name, url in urls:
        errors = []
        console = []
        handler = lambda m: (console.append(m.text)
                             if m.type in ("error", "warning") else None)
        page.on("console", handler)
        page.on("pageerror", lambda e: console.append(str(e)))
        page.goto(url, wait_until="load")

        m = page.evaluate(_MEASURE_JS)
        if m["scrollW"] != W or m["scrollH"] != H:
            errors.append(f"page is {m['scrollW']}x{m['scrollH']}, not {W}x{H}")
        if m["svgs"] != 1:
            errors.append(f"{m['svgs']} <svg> elements, expected exactly 1")
        for t in m["texts"][:4]:
            errors.append(f"text {t['size']}px < {MIN_TEXT}: {t['text']!r}")
        if len(m["texts"]) > 4:
            errors.append(f"...and {len(m['texts']) - 4} more undersized texts")
        for s in m["strokes"][:4]:
            errors.append(f"{s['tag']} stroke {s['w']}px < {MIN_STROKE}")
        if len(m["strokes"]) > 4:
            errors.append(f"...and {len(m['strokes']) - 4} more thin strokes")
        for ov in m["overlaps"][:4]:
            errors.append(f"overlap {ov['w']}x{ov['h']}px: "
                          f"{ov['a']!r} on {ov['b']!r}")
        if len(m["overlaps"]) > 4:
            errors.append(f"...and {len(m['overlaps']) - 4} more overlaps")
        for t in m["clipped"][:4]:
            errors.append(f"text outside the panel: {t!r}")
        for c in console[:3]:
            errors.append(f"console: {c[:80]}")

        if shot_dir:
            page.screenshot(path=os.path.join(shot_dir, f"{name}.png"))
        page.remove_listener("console", handler)
        results.append((name, errors, m["ellipsized"]))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=DEFAULT_DIR,
                    help="directory to serve (default: running-log/)")
    ap.add_argument("--probe", action="store_true",
                    help="report whether this transport is usable here, then exit")
    ap.add_argument("--only", default="",
                    help="comma-separated card ids to check instead of all")
    ap.add_argument("--no-screenshots", action="store_true")
    ap.add_argument("--shot-dir", default=SHOT_DIR)
    args = ap.parse_args()

    # Card titles carry em dashes and some carry emoji; a cp1252 Windows
    # console raises UnicodeEncodeError on the first failing card, which would
    # look like a crash in the page under test rather than in the report.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return _fail("playwright-not-installed", str(exc),
                     "uv add --dev playwright && uv run playwright install chromium")

    card_dir = os.path.join(args.dir, "epaper")
    device_page = os.path.join(args.dir, "epaper.html")
    if not os.path.exists(device_page) or not os.path.isdir(card_dir):
        return _fail("feed-not-built", f"missing {device_page} or {card_dir}",
                     "uv run python strava-data/build_feed.py")

    wanted = {s.strip() for s in args.only.split(",") if s.strip()}
    cards = sorted(os.path.basename(p)[:-5]
                   for p in glob.glob(os.path.join(card_dir, "*.html")))
    if wanted:
        missing = wanted - set(cards)
        if missing:
            return _fail("unknown-card", f"no page for {sorted(missing)}")
        cards = [c for c in cards if c in wanted]

    shot_dir = "" if args.no_screenshots else args.shot_dir
    if shot_dir:
        os.makedirs(shot_dir, exist_ok=True)

    port = _free_port()
    httpd = _serve(args.dir, port)
    base = f"http://127.0.0.1:{port}"
    urls = ([("epaper", f"{base}/epaper.html")] if not wanted else []) + \
           [(c, f"{base}/epaper/{c}.html") for c in cards]

    try:
        with sync_playwright() as p:
            override = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or ""
            try:
                browser = p.chromium.launch(executable_path=override or None)
            except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                found = "" if override else _discover_chromium()
                if not found:
                    return _fail("chromium-not-launchable", str(exc)[:500],
                                 "uv run playwright install chromium, or set "
                                 "PLAYWRIGHT_CHROMIUM_PATH")
                browser = p.chromium.launch(executable_path=found)

            if args.probe:
                json.dump({"transport": "epaper", "ok": True,
                           "chromium": browser.version, "cards": len(cards)},
                          sys.stdout, indent=2)
                sys.stdout.write("\n")
                browser.close()
                return 0

            ctx = browser.new_context(viewport={"width": W, "height": H},
                                      device_scale_factor=1)
            page = ctx.new_page()
            results = check_pages(page, urls, shot_dir)
            browser.close()
    finally:
        httpd.shutdown()

    feed_bad = check_feed(os.path.join(args.dir, "feed.xml"))

    print(f"feed.xml   {'FAIL' if feed_bad else 'pass'}")
    for b in feed_bad:
        print(f"           - {b}")
    print()
    failed = [r for r in results if r[1]]
    for name, errors, cut in results:
        note = f"   ({len(cut)} ellipsized)" if cut else ""
        print(f"{'FAIL' if errors else 'pass'}  {name}{note}")
        for e in errors:
            print(f"        - {e}")
    print(f"\n{len(results) - len(failed)}/{len(results)} pages pass"
          + (f", {len(feed_bad)} feed problem(s)" if feed_bad else ""))
    if shot_dir:
        print(f"screenshots -> {os.path.relpath(shot_dir, _REPO)}")
    return 1 if (failed or feed_bad) else 0


if __name__ == "__main__":
    sys.exit(main())
