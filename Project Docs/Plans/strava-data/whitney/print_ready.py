"""Turn D4 into files a print shop can actually take.

    uv run python "Project Docs/Plans/strava-data/whitney/print_ready.py"

Writes, beside itself:

    whitney_11x14.pdf   the deliverable — 11x14 in exactly, fonts embedded, no background
    whitney_11x14.svg   the same artwork as vector, for a designer to open
    whitney_11x14.png   300 dpi backup, correctly tagged so it opens at 11x14 and not 45x58

Three things separate these from the proof, and each is a real failure mode rather than a
tidy-up:

1.  NO BACKGROUND RECT. The piece prints as one ink on cream stock, so the cream is the paper.
    Leaving the #F5F0E6 rect in would have the shop lay down a flat ground and turn a
    one-colour job into a four-colour one — and then it would need bleed, which it does not
    otherwise need, because no ink comes within half an inch of the trim.

2.  STROKES BAKED. The drawings are placed inside a scale() and rely on
    vector-effect="non-scaling-stroke" to keep their weight. Chromium honours it; plenty of
    RIPs and converters do not, and the hikers sit at scale 0.094 — so if it is dropped their
    0.61 mm stroke renders at 0.06 mm, eleven times too light, and disappears on press. Here
    the width is divided by the scale and the attribute removed, so the file no longer
    depends on anyone supporting it.

3.  FONTS EMBEDDED, via the PDF. The artwork asks for "Helvetica Neue", Helvetica, Arial —
    and Helvetica Neue is not installed on the machine this was designed on, so every sans
    element has in fact been set in ARIAL throughout. A Mac at the print shop would have
    Helvetica Neue, take the first branch, and reflow every right-anchored elevation in the
    legend. Embedding the fonts that were actually used is what makes the page deterministic.
    The SVG cannot do that; it is supplied for editing, not for output.
"""

import argparse
import os
import re
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proofs as P                                    # noqa: E402
import proofs_d as PD                                 # noqa: E402
from proofs import write                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = PD.W, PD.H
INCH = 100.0

# art_at() emits exactly this shape; the scale is group 1 and the width group 2.
_ART = re.compile(
    r'(<g transform="translate\([-\d.]+,[-\d.]+\) scale\(([\d.]+)\)" fill="none" '
    r'stroke="[^"]*" stroke-width=")([\d.]+)("[^>]*?) vector-effect="non-scaling-stroke"')


def bake_strokes(svg):
    """Fold each art group's scale into its stroke-width and drop non-scaling-stroke."""
    n = 0

    def sub(m):
        nonlocal n
        n += 1
        return m.group(1) + f"{float(m.group(3)) / float(m.group(2)):.4f}" + m.group(4)

    return _ART.sub(sub, svg), n


def tag_png_dpi(path, dpi=300):
    """Insert a pHYs chunk. Without one the file has no physical size at all, so a shop
    opening 3300x4200 sees 45.8 x 58.3 in at the 72 dpi default."""
    d = open(path, "rb").read()
    if b"pHYs" in d[:200]:
        return False
    ppm = int(round(dpi / 0.0254))
    body = b"pHYs" + struct.pack(">IIB", ppm, ppm, 1)
    chunk = struct.pack(">I", 9) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    ihdr_len = struct.unpack(">I", d[8:12])[0]
    end = 8 + 12 + ihdr_len                       # insert straight after IHDR
    with open(path, "wb") as f:
        f.write(d[:end] + chunk + d[end:])
    return True


def artwork(act):
    """The D4 sheet with no background rect and no non-scaling-stroke."""
    body = PD.place_parts(PD.d4_parts(act))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W / INCH}in" height="{H / INCH}in">{body}</svg>')
    return bake_strokes(svg)


def render(svg, pdf_path, png_path, dpi):
    from playwright.sync_api import sync_playwright
    page_html = (
        "<!doctype html><meta charset=utf-8><style>"
        f"@page{{size:{W / INCH}in {H / INCH}in;margin:0}}"
        "html,body{margin:0;padding:0;background:#fff}"
        f"svg{{display:block;width:{W / INCH}in;height:{H / INCH}in}}</style>" + svg)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(page_html, wait_until="load")
        pg.pdf(path=pdf_path, width=f"{W / INCH}in", height=f"{H / INCH}in",
               print_background=False,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        pg.close()
        # the raster backup renders on white; the cream is the paper, not the file
        pg = b.new_page(viewport={"width": W, "height": H},
                        device_scale_factor=dpi / INCH)
        pg.set_content(f"<style>html,body{{margin:0;background:#fff}}</style>{svg}",
                       wait_until="load")
        pg.screenshot(path=png_path)
        b.close()


def check(pdf_path, png_path):
    """Report what actually came out, rather than what was asked for."""
    d = open(pdf_path, "rb").read()
    boxes = {tuple(round(float(v), 1) for v in m)
             for m in re.findall(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+"
                                 rb"([\d.]+)\s+([\d.]+)\s*\]", d)}
    fonts = sorted({m.decode("latin1") for m in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+#-]+)", d)})
    embedded = len(re.findall(rb"/FontFile2?3?", d))
    print(f"  PDF   pages MediaBox {boxes}  (72 pt = 1 in)", file=sys.stderr)
    for b_ in boxes:
        print(f"        -> {b_[2] / 72:.2f} x {b_[3] / 72:.2f} in", file=sys.stderr)
    print(f"  PDF   fonts {fonts}  ({embedded} embedded font files)", file=sys.stderr)

    p_ = open(png_path, "rb").read()
    w, h = struct.unpack(">II", p_[16:24])
    i, ppm = 8, None
    while i < len(p_):
        ln = struct.unpack(">I", p_[i:i + 4])[0]
        if p_[i + 4:i + 8] == b"pHYs":
            ppm = struct.unpack(">I", p_[i + 8:i + 12])[0]
            break
        if p_[i + 4:i + 8] == b"IDAT":
            break
        i += 12 + ln
    dpi = round(ppm * 0.0254) if ppm else None
    print(f"  PNG   {w} x {h} px, {dpi} dpi -> {w / dpi:.2f} x {h / dpi:.2f} in"
          if dpi else f"  PNG   {w} x {h} px, NO pHYs", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()

    act = P.load()
    svg, n = artwork(act)
    base = os.path.join(args.out, "whitney_11x14")
    write(base + ".svg", svg)
    render(svg, base + ".pdf", base + ".png", args.dpi)
    tag_png_dpi(base + ".png", args.dpi)

    print(f"  baked {n} art groups; background rect omitted (cream = the paper)",
          file=sys.stderr)
    check(base + ".pdf", base + ".png")
    print("  wrote " + base + ".{pdf,svg,png}", file=sys.stderr)


if __name__ == "__main__":
    main()
